# Service Specification — Lab 4

**Author:** Ivaikina Darya  
**Version:** 3  
**Based on:** Laboratory Works 2 and 3

## Purpose

A Flask API for basic request handling, external object storage and primary/replica Redis experiments. The API runs locally and its storage services run in Docker Compose.

## Requirements

| ID | Method | Path | Input | Output | HTTP status |
|---|---|---|---|---|---|
| R1 | POST | `/echo` | JSON `{"message":"text"}` | `{"reply":"text"}` | 200, 400 |
| R2 | GET | `/time` | — | `server_time`, `served_by` | 200 |
| R3 | POST | `/jobs` | JSON `{"message":"text"}` | `job_id`, `status=queued` | 202, 400 |
| R4 | GET | `/jobs/{job_id}` | UUID in URL | job status and optional result | 200, 404 |
| R5 | any | unknown path / unsupported method | — | JSON error | 404, 405 |
| R6 | POST | `/files` | JSON `{"content":"text"}` | `{"file_id":"UUID"}` | 201, 400, 503 |
| R7 | GET | `/files/{file_id}` | UUID in URL | `file_id`, `content` | 200, 404, 503 |
| R8 | POST | `/counter/increment` | — | `value`, `source=primary` | 200, 503 |
| R9 | GET | `/counter?from=primary` or `?from=replica` | `from` parameter (defaults to primary) | `value`, `source` | 200, 400, 503 |

## Input validation

- R1/R3 require a nonempty `message` string, at most 1000 characters.
- R6 requires a JSON object with `content` as a string (empty text is allowed), at most 1 MiB = 1,048,576 bytes in UTF-8.
- R7 accepts only a valid UUID and returns 404 for unknown files.
- R9 accepts only `primary` or `replica` for `from`.
- Storage/network errors produce HTTP 503 without exposing credentials.

## Storage

- Local RustFS is S3 compatible and accepts normal boto3 commands on `http://127.0.0.1:9000`.
- Bucket name: `lab4-files` (configured through `BUCKET`).
- Keys use `files/{uuid}.txt`; content is UTF-8 text.
- Named Docker volume `s3-data` preserves objects after app restart and container recreation.
- AWS-shaped environment variable names are used for local training credentials, not for AWS access.

## Redis and consistency assumptions

- Starting roles: primary on host port 6379 and replica on host port 6380.
- `POST /counter/increment` writes only to the configured primary.
- `GET /counter` can read either store.
- Replication is asynchronous: a read from the replica can return stale data (replication lag).
- Once connectivity resumes, a healthy replica eventually catches up (eventual consistency).
- Read-your-own-write is not guaranteed for replica reads; read from primary when freshness is required.
- Primary node addresses come from `REDIS_PRIMARY_PORT`, `REDIS_REPLICA_PORT`, and `REDIS_HOST` environment variables.
- Failover is manual: promote a replica using `REPLICAOF NO ONE`, restart API with the new primary port, rejoin old node as replica. Two independent masters risk diverging writes.

## Compatibility and limitations

- R1–R4 preserve the Lab 2/3 API behavior and R5 preserves JSON errors.
- `/time` includes `served_by` from Lab 3.
- The `/jobs` workflow remains file-based for compatibility. There is no worker in Lab 4, and it is not a distributed queue; it is not the storage persistence experiment.
- Flask's built-in server is for local coursework only.
