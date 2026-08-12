"""
Dumps the full raw content of the most recent Lambda log stream to a file,
replacing carriage returns so nothing gets visually overwritten/lost.
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
OUTPUT_FILE = "lambda_debug_output.txt"

streams = logs.describe_log_streams(
    logGroupName=LOG_GROUP, orderBy="LastEventTime", descending=True
)["logStreams"]

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    if not streams:
        f.write("No log streams found.\n")
    else:
        stream = streams[0]
        f.write(f"Stream: {stream['logStreamName']}\n\n")
        events = logs.get_log_events(
            logGroupName=LOG_GROUP, logStreamName=stream["logStreamName"]
        )["events"]
        for e in events:
            # Replace \r with \n so nothing gets overwritten when displayed
            msg = e["message"].replace("\r", "\n")
            f.write(msg + "\n")

print(f"Wrote full log output to {OUTPUT_FILE}")
print("Open it with: notepad lambda_debug_output.txt")