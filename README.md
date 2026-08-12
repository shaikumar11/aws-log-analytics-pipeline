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

