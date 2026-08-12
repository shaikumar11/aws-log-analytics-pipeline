\# AWS Log Analytics Pipeline (LocalStack)



A log analytics pipeline built with real AWS SDK (`boto3`) code and real

Lambda/S3 event-trigger patterns, running against \*\*LocalStack\*\* instead of

live AWS. DuckDB queries the processed data directly from S3 with SQL,

standing in for Athena.



\## Architecture



```

generate\_logs.py                deploy\_lambda.py (one-time)

&#x20;       |                               |

&#x20;       v                               v

&#x20; raw-logs/{service}/{date}/{uuid}.json --(S3 event)--> Lambda (handler.py)

&#x20;                                                             |

&#x20;                                                             v

&#x20;                                           processed-logs/{service}/{date}/summary.json

&#x20;                                                             |

&#x20;                             +-------------------------------+-------------------------------+

&#x20;                             v                                                                 v

&#x20;                   query\_duckdb.py (SQL over S3,                                  publish\_metrics.py

&#x20;                    replaces Athena)                                          (CloudWatch custom metrics)

```



\*\*Data model\*\*



Raw log event: `timestamp`, `service\_name`, `level` (INFO/WARN/ERROR), `latency\_ms`, `message`



Processed summary: `service\_name`, `date`, `total\_requests`, `error\_count`, `avg\_latency\_ms`, `p95\_latency\_ms`



\## Prerequisites



\- Docker Desktop

\- Python 3.11+

\- A free LocalStack account + auth token (https://app.localstack.cloud -> Settings -> Auth Tokens).

&#x20; LocalStack requires a token to start, even for community/non-commercial use.



\## Setup



1\. Create and activate a virtual environment:

&#x20;  ```cmd

&#x20;  python -m venv venv

&#x20;  venv\\Scripts\\activate

&#x20;  ```



2\. Install dependencies:

&#x20;  ```cmd

&#x20;  pip install -r requirements.txt

&#x20;  ```



3\. Start LocalStack with Docker-socket access (needed for Lambda) and persistence enabled:

&#x20;  ```cmd

&#x20;  docker run -d --name localstack -p 4566:4566 ^

&#x20;    -e LOCALSTACK\_AUTH\_TOKEN=your\_token\_here ^

&#x20;    -e PERSISTENCE=1 ^

&#x20;    -v //var/run/docker.sock:/var/run/docker.sock ^

&#x20;    -v localstack\_data:/var/lib/localstack ^

&#x20;    localstack/localstack

&#x20;  ```



4\. Verify it's healthy:

&#x20;  ```cmd

&#x20;  curl http://localhost:4566/\_localstack/health

&#x20;  ```

&#x20;  Look for `"s3"`, `"lambda"`, and `"cloudwatch"` as `"available"` or `"running"`.



\## Running the pipeline



Run these in order (or use `run\_pipeline.py` to do it all at once):



```cmd

python setup\_buckets.py       # creates raw-logs and processed-logs buckets

python deploy\_lambda.py       # zips handler.py, deploys the Lambda, wires the S3 trigger

python generate\_logs.py --count 40   # generates + uploads logs, which auto-triggers the Lambda

python query\_duckdb.py        # SQL queries over the processed S3 data

python publish\_metrics.py     # pushes CloudWatch custom metrics per service

python view\_metrics.py        # reads the metrics back to confirm

```



\## Example Output



A real end-to-end run via `python run\_pipeline.py --skip-deploy --count 20`:



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



This confirms the full loop working: raw logs uploaded → S3 event automatically

triggers the Lambda → Lambda aggregates and writes summaries → DuckDB queries

those summaries with SQL → CloudWatch custom metrics are published and readable

back, exactly as a production observability pipeline would behave.



\## Files



| File | Purpose |

|---|---|

| `setup\_buckets.py` | Creates the `raw-logs` and `processed-logs` S3 buckets |

| `generate\_logs.py` | Generates synthetic structured logs and uploads them to `raw-logs` |

| `handler.py` | The Lambda function: aggregates raw logs into a summary per service/date |

| `deploy\_lambda.py` | Zips `handler.py`, creates/updates the Lambda, wires the S3 event trigger |

| `query\_duckdb.py` | Runs SQL queries directly against `processed-logs` via DuckDB's `httpfs` |

| `publish\_metrics.py` | Publishes CloudWatch custom metrics from the processed summaries |

| `view\_metrics.py` | Reads back the published CloudWatch metrics |

| `run\_pipeline.py` | Runs the whole pipeline end-to-end in one command |

| Debug helpers | `check\_function\_info.py`, `dump\_lambda\_log.py`, `inspect\_zip.py` -- for troubleshooting Lambda deploys |



\## Notes / gotchas



\- LocalStack Lambda containers can't reach `localhost:4566` internally -- `handler.py` builds

&#x20; the S3 endpoint from `LOCALSTACK\_HOSTNAME`/`EDGE\_PORT`, which LocalStack injects automatically.

\- The Lambda re-aggregates \*\*all\*\* raw logs for a given `service\_name/date` on every invocation

&#x20; (not just the file that triggered it), so `processed-logs` summaries are always fully up to date.

\- Without `PERSISTENCE=1` and a named volume, all LocalStack state (buckets, functions, triggers)

&#x20; is wiped every time the container restarts.

