# AWS Data Pipeline (Local with FakeCloud)

A local development environment that emulates an **AWS data pipeline**: provision an RDS PostgreSQL database and S3 bucket, seed the database with sample data, then export every table as CSV into S3 — all running against [FakeCloud](https://github.com/faiscadev/fakecloud) locally.

---

## Overview

This project spins up three Docker services:

| Service | Purpose |
|---------|---------|
| **fakecloud** | Local AWS emulator exposing S3, RDS, Elasticache, CloudFormation, and more at `http://localhost:4566`. |
| **cloud-script** | One-shot container that creates the S3 bucket, provisions an RDS PostgreSQL instance, waits for it to be available, and seeds it with sample data. |
| **app** | One-shot container that discovers the RDS endpoint dynamically, reads every table, and exports each as a CSV object into the S3 bucket. |

The pipeline runs sequentially thanks to `depends_on` conditions:

```
fakecloud (healthy) → cloud-script (completed) → app
```

---

## Directory Layout

```
.
├── compose.yaml                     # Top-level orchestration
├── aws-scripts/                     # AWS provisioning + DB seeding
│   ├── Dockerfile
│   ├── setup-rds-s3.sh              # Creates bucket, RDS instance, waits, seeds
│   ├── data-lake.sql                # Sample schema + data
│   └── environments/
│       ├── aws.env                  # Real AWS credentials/region
│       └── fakecloud.env            # FakeCloud endpoint + dummy creds
├── python/                          # Export job
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── rds-to-s3.py                 # Reads tables → writes CSV to S3
│   └── uv.lock
├── fakecloud/                       # Persistent FakeCloud state (volume)
│   ├── s3/
│   ├── cloudformation/
│   ├── elasticache/
│   ├── logs/
│   └── data-volume-scope
├── helper-scripts/
│   ├── pack-proj.sh                 # Dumps project snapshot to proj.txt
│   └── push.sh
├── .devcontainer/
│   └── devcontainer.json
└── proj.txt                         # Auto-generated project snapshot
```

---

## Prerequisites

- **Docker** (with Compose v2)
- **Docker socket access** (FakeCloud requires `/var/run/docker.sock` to emulate RDS/Elasticache)
- *(Optional)* **VS Code + Dev Containers extension** — a ready-to-use `.devcontainer` is included

---

## Quick Start

From the project root:

```bash
docker compose up --build
```

This will:

1. Start **fakecloud** and wait for its healthcheck.
2. Build and run **cloud-script**, which:
   - Creates the `data-lake` S3 bucket (idempotent).
   - Creates the `my-postgres-db` RDS instance (idempotent).
   - Waits until the instance is available.
   - Seeds the database from `aws-scripts/data-lake.sql`.
3. Build and run **app**, which:
   - Discovers the RDS endpoint via `rds.describe_db_instances`.
   - Connects with `psycopg2`.
   - Lists all base tables in `public`.
   - Exports each table to `s3://data-lake/exports/<table>.csv`.

On success you'll see output similar to:

```
Discovering endpoint for RDS instance: my-postgres-db...
Found DB at my-postgres-db.xxxx.rds.fakecloud:5432
Processing table: customers
Uploaded to s3://data-lake/exports/customers.csv
```

---

## Configuration

### Environment variables

The `app` service honors these (with defaults shown):

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_ENDPOINT_URL` | `""` | FakeCloud endpoint; empty means real AWS |
| `DB_USER` | `admin` | PostgreSQL user |
| `DB_PASS` | `password123` | PostgreSQL password |
| `DB_NAME` | `postgres` | PostgreSQL database |
| `DB_INSTANCE_ID` | `my-postgres-db` | RDS instance identifier |
| `S3_BUCKET` | `data-lake` | Destination bucket |
| `S3_PREFIX` | `exports` | Key prefix for exported CSVs |

### FakeCloud

- Endpoint: `http://localhost:4566`
- Storage mode: **persistent** (state lives in `./fakecloud`)
- Dummy credentials accepted via `AWS_ACCESS_KEY_ID=test` / `AWS_SECRET_ACCESS_KEY=test`

### Targeting real AWS

`aws-scripts/environments/aws.env` unsets `AWS_ENDPOINT_URL`, resolves the caller's `ACCOUNT_ID` via STS, and uses your configured AWS credentials. To use it:

```bash
cd aws-scripts
./setup-rds-s3.sh ./environments/aws.env
```

> ⚠️ This will create real, billable AWS resources. Use with caution.

---

## Resetting State

Because FakeCloud persists to `./fakecloud`, previous buckets/RDS instances will still exist across runs. To start fresh:

```bash
docker compose down
rm -rf fakecloud/s3/* fakecloud/cloudformation/* fakecloud/elasticache/* fakecloud/logs/*
docker compose up --build
```

> Keep `fakecloud/.gitkeep` and `fakecloud/data-volume-scope` if you want FakeCloud to reuse the same volume scope.


---

## Development Container

If you open the project in VS Code with the Dev Containers extension, `.devcontainer/devcontainer.json` will bootstrap a Python 3.12 environment with:

- Docker-in-Docker
- AWS CLI
- Python, Docker, and AWS Toolkit extensions
- Port `4566` forwarded automatically

---

## Tech Stack

- **[FakeCloud](https://github.com/faiscadev/fakecloud)** — local AWS emulator
- **Docker Compose** — orchestration
- **Python 3.12** + **[uv](https://github.com/astral-sh/uv)** — packaging/runtime
- **boto3**, **psycopg2**, **pandas** — AWS SDK, Postgres driver, CSV rendering
- **PostgreSQL** — emulated RDS backend
- **AWS CLI v2** — provisioning in the setup container
