import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

BUCKETS = ["raw-logs", "processed-logs"]

for bucket in BUCKETS:
    try:
        s3.create_bucket(Bucket=bucket)
        print(f"Created bucket: {bucket}")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket already exists: {bucket}")

print("\nCurrent buckets:")
for b in s3.list_buckets()["Buckets"]:
    print(f" - {b['Name']}")