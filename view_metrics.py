"""
Reads back the custom CloudWatch metrics we published, to confirm they
landed correctly. Lists metrics in the namespace and fetches recent
statistics for one as a sanity check.

Run:
    python view_metrics.py
"""

import boto3
from datetime import datetime, timedelta, timezone

NAMESPACE = "LogPipeline/ServiceMetrics"

cloudwatch = boto3.client(
    "cloudwatch",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)


def list_metrics():
    print(f"=== Metrics registered under {NAMESPACE} ===")
    paginator = cloudwatch.get_paginator("list_metrics")
    for page in paginator.paginate(Namespace=NAMESPACE):
        for metric in page.get("Metrics", []):
            dims = ", ".join(f"{d['Name']}={d['Value']}" for d in metric.get("Dimensions", []))
            print(f"  {metric['MetricName']:15s} [{dims}]")


def get_stats_for_metric(metric_name: str, service_name: str):
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)

    response = cloudwatch.get_metric_statistics(
        Namespace=NAMESPACE,
        MetricName=metric_name,
        Dimensions=[{"Name": "ServiceName", "Value": service_name}],
        StartTime=start,
        EndTime=end,
        Period=3600,
        Statistics=["Average", "Maximum", "Sum"],
    )
    return response.get("Datapoints", [])


def main():
    list_metrics()

    print(f"\n=== Sample: ErrorCount stats for auth-service (last hour) ===")
    datapoints = get_stats_for_metric("ErrorCount", "auth-service")
    if datapoints:
        for dp in datapoints:
            print(f"  Sum={dp['Sum']}  Avg={dp['Average']}  Max={dp['Maximum']}  Time={dp['Timestamp']}")
    else:
        print("  No datapoints returned (LocalStack's metric stats can lag a moment after publish).")


if __name__ == "__main__":
    main()