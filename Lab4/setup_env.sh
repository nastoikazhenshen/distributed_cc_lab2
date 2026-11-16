#!/bin/sh
# Run with: source ./setup_env.sh  (do not use sh setup_env.sh)
# Local RustFS lab credentials ONLY; not real AWS credentials.
export BUCKET=lab4-files
export S3_ENDPOINT=http://127.0.0.1:9000
export AWS_ACCESS_KEY_ID=lab4user
export AWS_SECRET_ACCESS_KEY=lab4password
export AWS_REGION=us-east-1
export REDIS_HOST=127.0.0.1
export REDIS_PRIMARY_PORT=6379
export REDIS_REPLICA_PORT=6380
