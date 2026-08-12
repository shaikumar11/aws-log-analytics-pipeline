"""
Log generator: creates structured JSON log events and uploads them to the
raw-logs S3 bucket (LocalStack), one file per event, at:

    raw-logs/{service_name}/{date}/{uuid}.json

Run:
    python generate_logs.py                # generates 20 logs across all services
    python generate_logs.py --count 100     # generate a specific number
"""

import argparse
import json
import random
import uuid
from datetime import datetime, timezone

import boto3

BUCKET = "raw-logs"

SERVICES = ["auth-service", "payments-service", "checkout-service", "inventory-service"]
LEVELS = ["INFO", "WARN", "ERROR"]
LEVEL_WEIGHTS = [0.75, 0.15, 0.10]  # mostly INFO, some WARN, few ERROR

MESSAGES = {
    "INFO": [
        "Request processed successfully",
        "User authenticated",
        "Cache hit for key",
        "Health check passed",
    ],
    "WARN": [
        "Retrying downstream call",
        "Response time above threshold",
        "Cache miss, falling back to DB",
    ],
    "ERROR": [
        "Downstream service timeout",
        "Database connection failed",
        "Unhandled exception in handler",
        "Rate limit exceeded",
    ],
}


def make_log_event(service_name: str) -> dict:
    level = random.choices(LEVELS, weights=LEVEL_WEIGHTS, k=1)[0]
    # ERROR logs tend to have higher latency
    base_latency = {"INFO": (10, 150), "WARN": (150, 400), "ERROR": (400, 1200)}[level]
    latency_ms = round(random.uniform(*base_latency), 2)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service_name": service_name,
        "level": level,
        "latency_ms": latency_ms,
        "message": random.choice(MESSAGES[level]),
    }


def upload_log(s3_client, log_event: dict) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"{log_event['service_name']}/{date_str}/{uuid.uuid4()}.json"

    s3_client.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(log_event).encode("utf-8"),
        ContentType="application/json",
    )
    return key


def main():
    parser = argparse.ArgumentParser(description="Generate and upload structured logs to LocalStack S3.")
    parser.add_argument("--count", type=int, default=20, help="Number of log events to generate")
    args = parser.parse_args()

    s3 = boto3.client(
        "s3",
        endpoint_url="http://localhost:4566",
        aws_access_key_id="test",
        aws_secret_access_key="test",
        region_name="us-east-1",
    )

    print(f"Generating {args.count} log events across {len(SERVICES)} services...\n")

    for i in range(args.count):
        service = random.choice(SERVICES)
        event = make_log_event(service)
        key = upload_log(s3, event)
        print(f"[{i+1}/{args.count}] {event['level']:5s} | {service:20s} | {key}")

    print(f"\nDone. Uploaded {args.count} logs to s3://{BUCKET}/")


if __name__ == "__main__":
    main()