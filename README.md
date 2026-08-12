\# AWS Log Analytics Pipeline



!\[Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python\&logoColor=white)

!\[AWS](https://img.shields.io/badge/AWS-S3%20%7C%20Lambda%20%7C%20CloudWatch-orange?logo=amazonaws\&logoColor=white)

!\[LocalStack](https://img.shields.io/badge/LocalStack-Cloud%20Emulation-6C4CE0?logo=localstack\&logoColor=white)

!\[DuckDB](https://img.shields.io/badge/DuckDB-SQL%20over%20S3-FFF000?logo=duckdb\&logoColor=black)

!\[License](https://img.shields.io/badge/license-MIT-green)



A log analytics pipeline built with \*\*real AWS SDK code\*\* (`boto3`) and real

S3-event-triggered Lambda patterns, running against \*\*LocalStack\*\* as a

local, cost-free stand-in for AWS. \*\*DuckDB\*\* queries the processed data

directly from S3 with plain SQL, playing the role Athena would play in a

live AWS deployment.



> LocalStack simulates the AWS API surface — the code itself (`boto3` calls,

> the Lambda handler, the S3 event trigger) is exactly what you'd write

> against real AWS. Only the endpoint changes.



\---



\## Table of Contents



\- \[Architecture](#architecture)

\- \[Data Model](#data-model)

\- \[Prerequisites](#prerequisites)

\- \[Setup](#setup)

\- \[Running the Pipeline](#running-the-pipeline)

\- \[Example Output](#example-output)

\- \[Project Files](#project-files)

\- \[Notes \& Gotchas](#notes--gotchas)



\---



\## Architecture



```

&#x20;generate\_logs.py                          deploy\_lambda.py  (one-time setup)

&#x20;       |                                          |

&#x20;       v                                          v

&#x20;raw-logs/{service}/{date}/{uuid}.json --(S3 event)--> Lambda (handler.py)

&#x20;                                                       |

&#x20;                                                       v

&#x20;                               processed-logs/{service}/{date}/summary.json

&#x20;                                                       |

&#x20;                       +---------------------------------+---------------------------------+

&#x20;                       v                                                                     v

&#x20;             query\_duckdb.py                                                  publish\_metrics.py

&#x20;         (SQL over S3 - replaces Athena)                                (CloudWatch custom metrics)

```



\*\*Flow:\*\* logs are generated and uploaded to a `raw-logs` S3 bucket -> an S3

event automatically triggers a Lambda function -> the Lambda aggregates all

logs for that service/date and writes a summary to `processed-logs` -> DuckDB

queries that summary data directly with SQL -> key metrics are published to

CloudWatch as custom metrics.



\## Data Model



| Raw log event | Processed summary |

|---|---|

| `timestamp` | `service\_name` |

| `service\_name` | `date` |

| `level` (INFO / WARN / ERROR) | `total\_requests` |

| `latency\_ms` | `error\_count` |

| `message` | `avg\_latency\_ms` |

| | `p95\_latency\_ms` |



\## Prerequisites



\- Docker Desktop

\- Python 3.11+

\- A free LocalStack account + auth token -- \[app.localstack.cloud](https://app.localstack.cloud) -> Settings -> Auth Tokens

&#x20; (LocalStack requires a token to start, even for non-commercial/community use)



\## Setup



\*\*1. Create and activate a virtual environment\*\*



```bash

python -m venv venv

venv\\Scripts\\activate

```



\*\*2. Install dependencies\*\*



```bash

pip install -r requirements.txt

```



\*\*3. Start LocalStack\*\* (Docker-socket access is required for Lambda; persistence keeps state across restarts)



```bash

docker run -d --name localstack -p 4566:4566 ^

&#x20; -e LOCALSTACK\_AUTH\_TOKEN=your\_token\_here ^

&#x20; -e PERSISTENCE=1 ^

&#x20; -v //var/run/docker.sock:/var/run/docker.sock ^

&#x20; -v localstack\_data:/var/lib/localstack ^

&#x20; localstack/localstack

```



\*\*4. Verify it's healthy\*\*



```bash

curl http://localhost:4566/\_localstack/health

```



Look for `"s3"`, `"lambda"`, and `"cloudwatch"` as `"available"` or `"running"`.



\## Running the Pipeline



Run the steps individually, or use `run\_pipeline.py` to run them all at once.



```bash

python setup\_buckets.py              # create raw-logs / processed-logs buckets

python deploy\_lambda.py              # deploy the Lambda + wire the S3 trigger

python generate\_logs.py --count 40   # generate + upload logs (auto-triggers the Lambda)

python query\_duckdb.py               # SQL queries over the processed S3 data

python publish\_metrics.py            # push CloudWatch custom metrics

python view\_metrics.py               # read the metrics back to confirm

```



Or, all at once:



```bash

python run\_pipeline.py --count 40

```



\## Example Output



<details>

<summary><strong>Click to expand a full end-to-end run</strong></summary>



```

Generating 20 log events across 4 services...

...

Done. Uploaded 20 logs to s3://raw-logs/



=== All processed summaries ===

&#x20;    service\_name       date  total\_requests  error\_count  avg\_latency\_ms  p95\_latency\_ms

&#x20;    auth-service 2026-08-12              14            1          203.39          489.39

&#x20;checkout-service 2026-08-12              23            0           90.87          197.03

inventory-service 2026-08-12              20            1          144.69          760.39

&#x20;payments-service 2026-08-12              21            1          111.66          294.44



=== Services ranked by error count ===

&#x20;    service\_name       date  total\_requests  error\_count  error\_rate\_pct

inventory-service 2026-08-12              20            1            5.00

&#x20;    auth-service 2026-08-12              14            1            7.14

&#x20;payments-service 2026-08-12              21            1            4.76

&#x20;checkout-service 2026-08-12              23            0            0.00



=== Services ranked by avg latency ===

&#x20;    service\_name       date  avg\_latency\_ms  p95\_latency\_ms

&#x20;    auth-service 2026-08-12          203.39          489.39

inventory-service 2026-08-12          144.69          760.39

&#x20;payments-service 2026-08-12          111.66          294.44

&#x20;checkout-service 2026-08-12           90.87          197.03



=== Total request volume across all services ===

&#x20;total\_requests\_all\_services  total\_errors\_all\_services

&#x20;                       78.0                        3.0

```



```

STEP: Publish CloudWatch custom metrics

Published metrics for auth-service: requests=14, errors=1, avg\_latency=203.39ms

Published metrics for checkout-service: requests=23, errors=0, avg\_latency=90.87ms

Published metrics for inventory-service: requests=20, errors=1, avg\_latency=144.69ms

Published metrics for payments-service: requests=21, errors=1, avg\_latency=111.66ms



STEP: View published metrics

=== Metrics registered under LogPipeline/ServiceMetrics ===

&#x20; AvgLatencyMs    \[ServiceName=auth-service]

&#x20; ErrorCount      \[ServiceName=auth-service]

&#x20; P95LatencyMs    \[ServiceName=auth-service]

&#x20; RequestVolume   \[ServiceName=auth-service]

&#x20; ... (same 4 metrics x 4 services)



=== Sample: ErrorCount stats for auth-service (last hour) ===

&#x20; Sum=2.0  Avg=1.0  Max=1.0  Time=2026-08-12 10:05:09+05:30



Pipeline complete.

```



</details>



This confirms the full loop working: raw logs uploaded -> S3 event

automatically triggers the Lambda -> Lambda aggregates and writes summaries ->

DuckDB queries those summaries with SQL -> CloudWatch custom metrics are

published and readable back -- exactly how a production observability

pipeline behaves.



\## Project Files



| File | Purpose |

|---|---|

| `setup\_buckets.py` | Creates the `raw-logs` and `processed-logs` S3 buckets |

| `generate\_logs.py` | Generates synthetic structured logs and uploads them to `raw-logs` |

| `handler.py` | The Lambda function -- aggregates raw logs into a summary per service/date |

| `deploy\_lambda.py` | Zips `handler.py`, creates/updates the Lambda, wires the S3 event trigger |

| `query\_duckdb.py` | Runs SQL queries directly against `processed-logs` via DuckDB's `httpfs` |

| `publish\_metrics.py` | Publishes CloudWatch custom metrics from the processed summaries |

| `view\_metrics.py` | Reads back the published CloudWatch metrics |

| `run\_pipeline.py` | Runs the whole pipeline end-to-end in one command |

| `check\_function\_info.py`, `dump\_lambda\_log.py`, `inspect\_zip.py` | Debug helpers used while troubleshooting Lambda deploys |



\## Notes \& Gotchas



\- LocalStack Lambda containers can't reach `localhost:4566` internally --

&#x20; `handler.py` builds the S3 endpoint from `LOCALSTACK\_HOSTNAME` / `EDGE\_PORT`,

&#x20; which LocalStack injects automatically into the Lambda's environment.

\- The Lambda re-aggregates \*\*all\*\* raw logs for a given `service\_name/date`

&#x20; on every invocation (not just the file that triggered it), so

&#x20; `processed-logs` summaries are always fully up to date.

\- Without `PERSISTENCE=1` and a named volume, all LocalStack state (buckets,

&#x20; functions, triggers) is wiped every time the container restarts.



\---



<p align="center">Built as a portfolio project demonstrating real AWS SDK patterns -- S3 event triggers, Lambda, and SQL-over-data-lake analytics -- without AWS billing.</p>

