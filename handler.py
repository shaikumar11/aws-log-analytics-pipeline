"""
Lambda handler: triggered by S3 PutObject events on the raw-logs bucket.

For the service_name/date of the file that triggered this invocation, it:
  1. Lists and reads ALL raw log files for that service_name/date
     (re-aggregating on every new file keeps the summary always up to date)
  2. Computes total_requests, error_count, avg_latency_ms, p95_latency_ms
  3. Writes the summary to processed-logs/{service_name}/{date}/summary.json
"""

import json
import os
import statistics
from urllib.parse import unquote_plus

import boto3

RAW_BUCKET = "raw-logs"
PROCESSED_BUCKET = "processed-logs"


def get_s3_client():
    hostname = os.environ.get("LOCALSTACK_HOSTNAME", "localhost")
    port = os.environ.get("EDGE_PORT", "4566")
    endpoint_url = f"http://{hostname}:{port}"

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )


def compute_summary(service_name: str, date: str, log_events: list) -> dict:
    total_requests = len(log_events)
    error_count = sum(1 for e in log_events if e.get("level") == "ERROR")
    latencies = sorted(e["latency_ms"] for e in log_events if "latency_ms" in e)

    avg_latency_ms = round(statistics.mean(latencies), 2) if latencies else 0
    if latencies:
        p95_index = min(int(len(latencies) * 0.95), len(latencies) - 1)
        p95_latency_ms = round(latencies[p95_index], 2)
    else:
        p95_latency_ms = 0

    return {
        "service_name": service_name,
        "date": date,
        "total_requests": total_requests,
        "error_count": error_count,
        "avg_latency_ms": avg_latency_ms,
        "p95_latency_ms": p95_latency_ms,
    }


def lambda_handler(event, context):
    s3 = get_s3_client()
    results = []

    for record in event.get("Records", []):
        key = unquote_plus(record["s3"]["object"]["key"])
        parts = key.split("/")
        if len(parts) < 3:
            print(f"Skipping unexpected key format: {key}")
            continue

        service_name, date = parts[0], parts[1]
        prefix = f"{service_name}/{date}/"

        paginator = s3.get_paginator("list_objects_v2")
        log_events = []
        for page in paginator.paginate(Bucket=RAW_BUCKET, Prefix=prefix):
            for obj in page.get("Contents", []):
                body = s3.get_object(Bucket=RAW_BUCKET, Key=obj["Key"])["Body"].read()
                try:
                    log_events.append(json.loads(body))
                except json.JSONDecodeError:
                    print(f"Skipping malformed log: {obj['Key']}")

        summary = compute_summary(service_name, date, log_events)

        summary_key = f"{service_name}/{date}/summary.json"
        s3.put_object(
            Bucket=PROCESSED_BUCKET,
            Key=summary_key,
            Body=json.dumps(summary).encode("utf-8"),
            ContentType="application/json",
        )

        print(f"Wrote summary: {summary_key} -> {summary}")
        results.append(summary)

    return {"statusCode": 200, "body": json.dumps(results)}