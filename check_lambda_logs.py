"""
Fetches the most recent CloudWatch log stream for the log-processor Lambda
and prints all log messages. Use this to debug why processed-logs isn't
getting populated.
"""

import boto3

logs = boto3.client(
    "logs",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

LOG_GROUP = "/aws/lambda/log-processor"

streams = logs.describe_log_streams(
    logGroupName=LOG_GROUP, orderBy="LastEventTime", descending=True
)["logStreams"]

if not streams:
    print("No log streams found — Lambda was never invoked.")
else:
    print(f"Found {len(streams)} log stream(s). Showing the most recent 3:\n")
    for stream in streams[:3]:
        print(f"--- Stream: {stream['logStreamName']} ---")
        events = logs.get_log_events(
            logGroupName=LOG_GROUP, logStreamName=stream["logStreamName"]
        )["events"]
        for e in events:
            print(e["message"].rstrip())
        print()