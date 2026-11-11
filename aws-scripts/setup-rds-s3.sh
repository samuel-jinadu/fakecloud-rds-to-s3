#!/bin/bash
ENV_FILE=${1:-./environments/fakecloud.env}
source "$ENV_FILE"

# S3 bucket (handle if it already exists)
echo "Creating S3 bucket..."
aws s3 mb s3://data-lake 2>/dev/null || echo "Bucket data-lake already exists."

# RDS PostgreSQL
echo "Checking RDS instance..."
if aws rds describe-db-instances --db-instance-identifier my-postgres-db >/dev/null 2>&1; then
    echo "RDS instance already exists."
else
    echo "Creating RDS instance..."
    aws rds create-db-instance \
        --db-instance-identifier my-postgres-db \
        --db-instance-class db.t3.micro \
        --engine postgres \
        --master-username admin \
        --master-user-password password123 \
        --allocated-storage 20
fi

# Wait for the instance to be ready
echo "Waiting for RDS instance to become available..."
aws rds wait db-instance-available \
    --db-instance-identifier my-postgres-db

# Get the endpoint address and port
ENDPOINT_JSON=$(aws rds describe-db-instances \
    --db-instance-identifier my-postgres-db \
    --query 'DBInstances[0].Endpoint')

DB_HOST=$(echo "$ENDPOINT_JSON" | jq -r '.Address')
DB_PORT=$(echo "$ENDPOINT_JSON" | jq -r '.Port')

echo "Database running at $DB_HOST:$DB_PORT"

# Execute the SQL file
echo "Seeding database..."
PGPASSWORD=password123 psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U admin \
    -d postgres \
    -f "$(dirname "$0")/data-lake.sql"