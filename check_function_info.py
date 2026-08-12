"""
Prints the currently deployed Lambda function's metadata directly from
LocalStack, so we can confirm whether our latest code update actually
took effect.
"""

import boto3

lam = boto3.client(
    "lambda",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

config = lam.get_function(FunctionName="log-processor")["Configuration"]

print("FunctionName:", config["FunctionName"])
print("Handler:", config["Handler"])
print("State:", config["State"])
print("LastModified:", config["LastModified"])
print("CodeSha256:", config["CodeSha256"])
print("Runtime:", config["Runtime"])