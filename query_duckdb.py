"""
Queries the processed-logs S3 bucket directly with DuckDB SQL --
no data copied locally, DuckDB reads straight from S3 (LocalStack).

This plays the role Athena would play in a real AWS setup: SQL-over-S3.
"""

import duckdb

con = duckdb.connect()

# Install and load the httpfs extension (lets DuckDB read s3:// paths)
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

# Point DuckDB's S3 config at LocalStack instead of real AWS
con.execute("""
    SET s3_endpoint='localhost:4566';
    SET s3_access_key_id='test';
    SET s3_secret_access_key='test';
    SET s3_region='us-east-1';
    SET s3_use_ssl=false;
    SET s3_url_style='path';
""")

print("=== All processed summaries ===")
result = con.execute("""
    SELECT *
    FROM read_json_auto('s3://processed-logs/*/*/summary.json')
    ORDER BY service_name, date
""").fetchdf()
print(result.to_string(index=False))

print("\n=== Services ranked by error count ===")
result = con.execute("""
    SELECT service_name, date, total_requests, error_count,
           ROUND(100.0 * error_count / total_requests, 2) AS error_rate_pct
    FROM read_json_auto('s3://processed-logs/*/*/summary.json')
    ORDER BY error_count DESC
""").fetchdf()
print(result.to_string(index=False))

print("\n=== Services ranked by avg latency ===")
result = con.execute("""
    SELECT service_name, date, avg_latency_ms, p95_latency_ms
    FROM read_json_auto('s3://processed-logs/*/*/summary.json')
    ORDER BY avg_latency_ms DESC
""").fetchdf()
print(result.to_string(index=False))

print("\n=== Total request volume across all services ===")
result = con.execute("""
    SELECT SUM(total_requests) AS total_requests_all_services,
           SUM(error_count) AS total_errors_all_services
    FROM read_json_auto('s3://processed-logs/*/*/summary.json')
""").fetchdf()
print(result.to_string(index=False))