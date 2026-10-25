# Service Specification — Lab 3

Author: Ivaikina Darya
Version: 2

## Purpose
Flask REST API from Lab 2, packaged with Docker and deployed to Kubernetes.

## Endpoints
- POST /echo — accepts a non-empty JSON message up to 1000 characters, returns reply (200) or validation error (400).
- GET /time — returns server_time in ISO format and served_by containing the container/pod hostname (200).
- POST /jobs — creates a file-based queued job (202) or returns validation error (400).
- GET /jobs/{job_id} — returns queued/done status (200) or not found (404).
- Unknown routes return JSON 404; unsupported methods return JSON 405.

Example /time response:
```json
{"server_time": "2026-10-25T15:30:00", "served_by": "my-api-example-pod"}
```

## Container configuration
Python 3.12-slim; Flask; bind 0.0.0.0:5000; run python app.py.
Compose exposes host port 5000 to container port 5000.

## Kubernetes configuration
Deployment my-api maintains 3 replicas, selecting app: my-api.
NodePort Service my-api forwards service port 80 to container port 5000.
The local image my-api:lab3 is loaded using minikube image load.

## Limitations
Lab 2 file-based queue endpoints are retained, but the worker is not deployed or tested in Lab 3. Each pod has its own filesystem, so /jobs is not a distributed queue. Use /time and /echo for Kubernetes demonstrations.
