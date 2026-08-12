"""
Deploys the log-processor Lambda to LocalStack and wires up an S3 event
trigger so it fires automatically whenever a new object lands in raw-logs.

Run this AFTER setup_buckets.py and AFTER handler.py exists in the same folder.

Run:
    python deploy_lambda.py
"""

import io
import json
import time
import zipfile

import boto3

ENDPOINT = "http://localhost:4566"
REGION = "us-east-1"
CREDS = dict(aws_access_key_id="test", aws_secret_access_key="test", region_name=REGION)

FUNCTION_NAME = "log-processor"
RAW_BUCKET = "raw-logs"
ROLE_NAME = "lambda-log-processor-role"
ROLE_ARN = f"arn:aws:iam::000000000000:role/{ROLE_NAME}"


def client(service):
    return boto3.client(service, endpoint_url=ENDPOINT, **CREDS)


def zip_handler() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write("handler.py")
    buf.seek(0)
    return buf.read()


def ensure_iam_role():
    iam = client("iam")
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }
    try:
        iam.create_role(RoleName=ROLE_NAME, AssumeRolePolicyDocument=json.dumps(trust_policy))
        print(f"Created IAM role: {ROLE_NAME}")
    except iam.exceptions.EntityAlreadyExistsException:
        print(f"IAM role already exists: {ROLE_NAME}")

    iam.attach_role_policy(
        RoleName=ROLE_NAME,
        PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess",  # fine for local dev only
    )


def deploy_function():
    lam = client("lambda")
    zip_bytes = zip_handler()

    try:
        lam.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime="python3.12",
            Role=ROLE_ARN,
            Handler="handler.lambda_handler",
            Code={"ZipFile": zip_bytes},
            Timeout=30,
            MemorySize=256,
        )
        print(f"Created Lambda function: {FUNCTION_NAME}")
    except lam.exceptions.ResourceConflictException:
        lam.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
        print(f"Function already existed, updated code: {FUNCTION_NAME}")

    # Wait for the function to become Active before wiring triggers
    print("Waiting for function to become active...")
    for _ in range(30):
        state = lam.get_function(FunctionName=FUNCTION_NAME)["Configuration"]["State"]
        if state == "Active":
            print("Function is active.")
            break
        time.sleep(2)
    else:
        print("Warning: function did not become active in time, continuing anyway.")

    return lam.get_function(FunctionName=FUNCTION_NAME)["Configuration"]["FunctionArn"]


def add_s3_invoke_permission(lam, function_arn):
    try:
        lam.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId="AllowS3Invoke",
            Action="lambda:InvokeFunction",
            Principal="s3.amazonaws.com",
            SourceArn=f"arn:aws:s3:::{RAW_BUCKET}",
        )
        print("Granted S3 permission to invoke Lambda.")
    except lam.exceptions.ResourceConflictException:
        print("S3 invoke permission already granted.")


def wire_s3_trigger(function_arn):
    s3 = client("s3")
    s3.put_bucket_notification_configuration(
        Bucket=RAW_BUCKET,
        NotificationConfiguration={
            "LambdaFunctionConfigurations": [
                {
                    "LambdaFunctionArn": function_arn,
                    "Events": ["s3:ObjectCreated:*"],
                }
            ]
        },
    )
    print(f"Wired S3 trigger: {RAW_BUCKET} -> {FUNCTION_NAME}")


def main():
    ensure_iam_role()
    function_arn = deploy_function()
    add_s3_invoke_permission(client("lambda"), function_arn)
    wire_s3_trigger(function_arn)
    print("\nDeployment complete. New uploads to raw-logs will now trigger the Lambda.")


if __name__ == "__main__":
    main()