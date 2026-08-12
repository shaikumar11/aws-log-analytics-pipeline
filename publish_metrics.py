"""
Reads the processed summaries from S3 and publishes them as CloudWatch
custom metrics (simulated by LocalStack) under a custom namespace.

This is the step that would back a real dashboard or alarm in production AWS.

Run:
    python publish_metrics.py
"""

import json

import boto3

NAMESPACE = "LogPipeline/ServiceMetrics"

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

cloudwatch = boto3.client(
    "cloudwatch",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)


def get_all_summaries():
    summaries = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket="processed-logs"):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith("summary.json"):
                body = s3.get_object(Bucket="processed-logs", Key=obj["Key"])["Body"].read()
                summaries.append(json.loads(body))
    return summaries


def publish_metrics(summary: dict):
    service_name = summary["service_name"]
    dimensions = [{"Name": "ServiceName", "Value": service_name}]

    cloudwatch.put_metric_data(
        Namespace=NAMESPACE,
        MetricData=[
            {
                "MetricName": "RequestVolume",
                "Dimensions": dimensions,
                "Value": summary["total_requests"],
                "Unit": "Count",
            },
            {
                "MetricName": "ErrorCount",
                "Dimensions": dimensions,
                "Value": summary["error_count"],
                "Unit": "Count",
            },
            {
                "MetricName": "AvgLatencyMs",
                "Dimensions": dimensions,
                "Value": summary["avg_latency_ms"],
                "Unit": "Milliseconds",
            },
            {
                "MetricName": "P95LatencyMs",
                "Dimensions": dimensions,
                "Value": summary["p95_latency_ms"],
                "Unit": "Milliseconds",
            },
        ],
    )
    print(f"Published metrics for {service_name}: "
          f"requests={summary['total_requests']}, errors={summary['error_count']}, "
          f"avg_latency={summary['avg_latency_ms']}ms")


def main():
    summaries = get_all_summaries()
    if not summaries:
        print("No summaries found in processed-logs. Run the pipeline first.")
        return

    for summary in summaries:
        publish_metrics(summary)

    print(f"\nDone. Published metrics to CloudWatch namespace: {NAMESPACE}")


if __name__ == "__main__":
    main()