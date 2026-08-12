"""
Runs the entire log analytics pipeline end-to-end, in order:

  1. setup_buckets.py   - create raw-logs / processed-logs buckets
  2. deploy_lambda.py   - deploy the Lambda + wire the S3 trigger
  3. generate_logs.py   - generate + upload synthetic logs (triggers the Lambda)
  4. query_duckdb.py    - run SQL queries over the processed S3 data
  5. publish_metrics.py - push CloudWatch custom metrics
  6. view_metrics.py    - read the metrics back to confirm

Assumes LocalStack is already running and healthy (see README.md).

Run:
    python run_pipeline.py
    python run_pipeline.py --count 100   # override log volume
"""

import argparse
import subprocess
import sys
import time


def run_step(description: str, command: list):
    print(f"\n{'=' * 70}")
    print(f"STEP: {description}")
    print('=' * 70)
    result = subprocess.run([sys.executable] + command)
    if result.returncode != 0:
        print(f"\nStep failed: {description} (exit code {result.returncode})")
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="Run the full log analytics pipeline.")
    parser.add_argument("--count", type=int, default=40, help="Number of log events to generate")
    parser.add_argument("--skip-deploy", action="store_true",
                         help="Skip bucket creation and Lambda deploy (use if already deployed)")
    args = parser.parse_args()

    if not args.skip_deploy:
        run_step("Create S3 buckets", ["setup_buckets.py"])
        run_step("Deploy Lambda + wire S3 trigger", ["deploy_lambda.py"])

    run_step("Generate and upload logs", ["generate_logs.py", "--count", str(args.count)])

    # Give the Lambda a moment to finish processing the last batch of S3 events
    print("\nWaiting a few seconds for the Lambda to finish processing...")
    time.sleep(5)

    run_step("Query processed data with DuckDB", ["query_duckdb.py"])
    run_step("Publish CloudWatch custom metrics", ["publish_metrics.py"])
    run_step("View published metrics", ["view_metrics.py"])

    print(f"\n{'=' * 70}")
    print("Pipeline complete.")
    print('=' * 70)


if __name__ == "__main__":
    main()