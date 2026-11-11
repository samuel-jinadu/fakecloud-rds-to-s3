import boto3
import psycopg2
import os
import pandas as pd
from io import StringIO

# env
ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASS = os.getenv("DB_PASS", "password123")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_INSTANCE_ID = os.getenv("DB_INSTANCE_ID", "my-postgres-db")
S3_BUCKET = os.getenv("S3_BUCKET", "data-lake")
S3_PREFIX = os.getenv("S3_PREFIX", "exports")

def list_tables(conn) -> list[str]:
    """Return every base table in the public schema."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        return [row[0] for row in cur.fetchall()]

def table_to_csv(conn, table: str) -> str:
    """Read a table into a DataFrame and render it as CSV."""
    df = pd.read_sql_query(f'SELECT * FROM "{table}";', conn)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def main():
    # Setup AWS clients
    client_kwargs = {"endpoint_url": ENDPOINT_URL} if ENDPOINT_URL else {}
    rds = boto3.client("rds", **client_kwargs)
    s3 = boto3.client("s3", **client_kwargs)

    # Dynamically discover the RDS endpoint
    print(f"Discovering endpoint for RDS instance: {DB_INSTANCE_ID}...")
    db_instance = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)['DBInstances'][0]
    db_host = db_instance['Endpoint']['Address']
    db_port = db_instance['Endpoint']['Port']
    print(f"Found DB at {db_host}:{db_port}")

    # Connect and process
    with psycopg2.connect(
        host=db_host, port=db_port, dbname=DB_NAME, user=DB_USER, password=DB_PASS
    ) as conn:
        tables = list_tables(conn)
        for table in tables:
            print(f"Processing table: {table}")
            key = f"{S3_PREFIX}/{table}.csv"
            csv_data = table_to_csv(conn, table)
            
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=csv_data,
                ContentType="text/csv",
            )
            print(f"Uploaded to s3://{S3_BUCKET}/{key}")

if __name__ == "__main__":
    main()