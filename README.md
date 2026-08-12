# AWS Log Analytics Pipeline

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-S3%20%7C%20Lambda%20%7C%20CloudWatch-orange?logo=amazonaws&logoColor=white)
![LocalStack](https://img.shields.io/badge/LocalStack-Cloud%20Emulation-6C4CE0?logo=localstack&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-SQL%20over%20S3-FFF000?logo=duckdb&logoColor=black)
![License](https://img.shields.io/badge/license-MIT-green)

A log analytics pipeline built with **real AWS SDK code** (`boto3`) and real
S3-event-triggered Lambda patterns, running against **LocalStack** as a
local, cost-free stand-in for AWS. **DuckDB** queries the processed data
directly from S3 with plain SQL, playing the role Athena would play in a
live AWS deployment.

> LocalStack simulates the AWS API surface — the code itself (`boto3` calls,
> the Lambda handler, the S3 event trigger) is exactly what you'd write
> against real AWS. Only the endpoint changes.

---

## Table of Contents

- [Architecture](#architecture)
- [Data Model](#data-model)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Pipeline](#running-the-pipeline)
- [Example Output](#example-output)
- [Project Files](#project-files)
- [Notes & Gotchas](#notes--gotchas)

---

## Architecture

```
 generate_logs.py                          deploy_lambda.py  (one-time setup)
        |                                          |
        v                                          v
 raw-logs/{service}/{date}/{uuid}.json --(S3 event)--> Lambda (handler.py)
                                                        |
                                                        v
                                processed-logs/{service}/{date}/summary.json
                                                        |
                        +---------------------------------+---------------------------------+
                        v                                                                     v
              query_duckdb.py                                                  publish_metrics.py
          (SQL over S3 - replaces Athena)                                (CloudWatch custom metrics)
```

**Flow:** logs are generated and uploaded to a `raw-logs` S3 bucket -> an S3
event automatically triggers a Lambda function -> the Lambda aggregates all
logs for that service/date and writes a summary to `processed-logs` -> DuckDB
queries that summary data directly with SQL -> key metrics are published to
CloudWatch as custom metrics.

## Data Model

| Raw log event | Processed summary |
|---|---|
| `timestamp` | `service_name` |
| `service_name` | `date` |
| `level` (INFO / WARN / ERROR) | `total_requests` |
| `latency_ms` | `error_count` |
| `message` | `avg_latency_ms` |
| | `p95_latency_ms` |

## Prerequisites

- Docker Desktop
- Python 3.11+
- A free LocalStack account + auth token -- [app.localstack.cloud](https://app.localstack.cloud) -> Settings -> Auth Tokens
  (LocalStack requires a token to start, even for non-commercial/community use)

## Setup

**1. Create and activate a virtual environment**

```bash
python -m venv venv
venv\Scripts\activate
```

**2. Install dependencies**

```bash
pip install -r requirements.txt
```

**3. Start LocalStack** (Docker-socket access is required for Lambda; persistence keeps state across restarts)

```bash
docker run -d --name localstack -p 4566:4566 ^
  -e LOCALSTACK_AUTH_TOKEN=your_token_here ^
  -e PERSISTENCE=1 ^
  -v //var/run/docker.sock:/var/run/docker.sock ^
  -v localstack_data:/var/lib/localstack ^
  localstack/localstack
```

**4. Verify it's healthy**

```bash
curl http://localhost:4566/_localstack/health
```

Look for `"s3"`, `"lambda"`, and `"cloudwatch"` as `"available"` or `"running"`.

## Running the Pipeline

Run the steps individually, or use `run_pipeline.py` to run them all at once.

```bash
python setup_buckets.py              # create raw-logs / processed-logs buckets
python deploy_lambda.py              # deploy the Lambda + wire the S3 trigger
python generate_logs.py --count 40   # generate + upload logs (auto-triggers the Lambda)
python query_duckdb.py               # SQL queries over the processed S3 data
python publish_metrics.py            # push CloudWatch custom metrics
python view_metrics.py               # read the metrics back to confirm
```

Or, all at once:

```bash
python run_pipeline.py --count 40
```

## Example Output

<details>
<summary><strong>Click to expand a full end-to-end run</strong></summary>

```
Generating 20 log events across 4 services...
...
Done. Uploaded 20 logs to s3://raw-logs/

=== All processed summaries ===
     service_name       date  total_requests  error_count  avg_latency_ms  p95_latency_ms
     auth-service 2026-08-12              14            1          203.39          489.39
 checkout-service 2026-08-12              23            0           90.87          197.03
inventory-service 2026-08-12              20            1          144.69          760.39
 payments-service 2026-08-12              21            1          111.66          294.44

=== Services ranked by error count ===
     service_name       date  total_requests  error_count  error_rate_pct
inventory-service 2026-08-12              20            1            5.00
     auth-service 2026-08-12              14            1            7.14
 payments-service 2026-08-12              21            1            4.76
 checkout-service 2026-08-12              23            0            0.00

=== Services ranked by avg latency ===
     service_name       date  avg_latency_ms  p95_latency_ms
     auth-service 2026-08-12          203.39          489.39
inventory-service 2026-08-12          144.69          760.39
 payments-service 2026-08-12          111.66          294.44
 checkout-service 2026-08-12           90.87          197.03

=== Total request volume across all services ===
 total_requests_all_services  total_errors_all_services
                        78.0                        3.0
```

```
STEP: Publish CloudWatch custom metrics
Published metrics for auth-service: requests=14, errors=1, avg_latency=203.39ms
Published metrics for checkout-service: requests=23, errors=0, avg_latency=90.87ms
Published metrics for inventory-service: requests=20, errors=1, avg_latency=144.69ms
Published metrics for payments-service: requests=21, errors=1, avg_latency=111.66ms

STEP: View published metrics
=== Metrics registered under LogPipeline/ServiceMetrics ===
  AvgLatencyMs    [ServiceName=auth-service]
  ErrorCount      [ServiceName=auth-service]
  P95LatencyMs    [ServiceName=auth-service]
  RequestVolume   [ServiceName=auth-service]
  ... (same 4 metrics x 4 services)

=== Sample: ErrorCount stats for auth-service (last hour) ===
  Sum=2.0  Avg=1.0  Max=1.0  Time=2026-08-12 10:05:09+05:30

Pipeline complete.
```

</details>

This confirms the full loop working: raw logs uploaded -> S3 event
automatically triggers the Lambda -> Lambda aggregates and writes summaries ->
DuckDB queries those summaries with SQL -> CloudWatch custom metrics are
published and readable back -- exactly how a production observability
pipeline behaves.

## Project Files

| File | Purpose |
|---|---|
| `setup_buckets.py` | Creates the `raw-logs` and `processed-logs` S3 buckets |
| `generate_logs.py` | Generates synthetic structured logs and uploads them to `raw-logs` |
| `handler.py` | The Lambda function -- aggregates raw logs into a summary per service/date |
| `deploy_lambda.py` | Zips `handler.py`, creates/updates the Lambda, wires the S3 event trigger |
| `query_duckdb.py` | Runs SQL queries directly against `processed-logs` via DuckDB's `httpfs` |
| `publish_metrics.py` | Publishes CloudWatch custom metrics from the processed summaries |
| `view_metrics.py` | Reads back the published CloudWatch metrics |
| `run_pipeline.py` | Runs the whole pipeline end-to-end in one command |
| `check_function_info.py`, `dump_lambda_log.py`, `inspect_zip.py` | Debug helpers used while troubleshooting Lambda deploys |

## Notes & Gotchas

- LocalStack Lambda containers can't reach `localhost:4566` internally --
  `handler.py` builds the S3 endpoint from `LOCALSTACK_HOSTNAME` / `EDGE_PORT`,
  which LocalStack injects automatically into the Lambda's environment.
- The Lambda re-aggregates **all** raw logs for a given `service_name/date`
  on every invocation (not just the file that triggered it), so
  `processed-logs` summaries are always fully up to date.
- Without `PERSISTENCE=1` and a named volume, all LocalStack state (buckets,
  functions, triggers) is wiped every time the container restarts.

---

<p align="center">Built as a portfolio project demonstrating real AWS SDK patterns -- S3 event triggers, Lambda, and SQL-over-data-lake analytics -- without AWS billing.</p>
