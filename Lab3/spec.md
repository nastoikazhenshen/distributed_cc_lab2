# Service Specification — Lab 3

**Author:** Ivaikina Darya  
**Version:** 2  
**Based on:** Laboratory Work 2 REST API

## 1. Purpose

The Flask API from Lab 2 is containerized with Docker and deployed to a local Kubernetes cluster with three replicas. The lab demonstrates service discovery, request distribution, self-healing, and scaling.

## 2. API endpoints

| Method | Path | Input | Response | Codes |
|---|---|---|---|---|
| POST | `/echo` | JSON `{"message":"text"}` | `{"reply":"text"}` | 200, 400 |
| GET | `/time` | None | `server_time`, `served_by` | 200 |
| POST | `/jobs` | JSON `{"message":"text"}` | `job_id`, `status: queued` | 202, 400 |
| GET | `/jobs/{job_id}` | UUID in path | Queued/done status or error | 200, 404 |

Messages must be non-empty strings with a maximum length of 1000 characters. Unknown paths return JSON 404; unsupported methods return JSON 405.

### GET /time — Version 2

Example response (illustrative pod name and time):

```json
{
  "server_time": "2026-10-26T13:00:00",
  "served_by": "my-api-7d9f8c6b5f-abc12"
}
```

The `served_by` field uses `socket.gethostname()` to identify the container or pod that answered.

## 3. Docker configuration

- Base image: `python:3.12-slim`
- Python dependency: Flask (`flask>=3.0`)
- Application bind address: `0.0.0.0`
- Flask application port **inside the container: 5000**
- Startup command: `python app.py`
- Docker and Compose port mapping: **host 5000 → container 5000**

The Dockerfile installs dependencies before copying application code to reuse cached layers.

## 4. Kubernetes configuration

- Deployment: `my-api`; image: `my-api:lab3`
- Initial replicas: **3**; scale-up target: **5**; scale-down target: **3**
- Pod labels and Service selector: `app: my-api`
- Service name: `my-api`; type: `NodePort`
- Service port: **80**; target container port: **5000**
- Image loaded into Minikube using `minikube image load my-api:lab3`

### Local access and port 50584

During the user's Minikube test session, `minikube service my-api --url` provided:

```text
http://127.0.0.1:50584
```

Thus the test endpoint was `http://127.0.0.1:50584/time`.

**50584 is the local forwarded/tunnel port, not the Flask container port or the fixed Kubernetes Service port.** It is allocated dynamically and can change when Minikube's service tunnel is restarted. Always use the URL currently printed by `minikube service my-api --url`; keep that terminal open when required.

## 5. Experiments

**Request distribution:** Send 30 separate HTTP requests to `/time` through the Service and group the `served_by` values. At least two distinct pod names are required for the lab.

**Self-healing:** Delete one Deployment-managed pod and observe a replacement pod being created. Repeat requests during deletion to assess continued availability.

**Scaling:** Change the Deployment replica count from 3 to 5, confirm five running pods, then return to 3.

## 6. Limitations

The Lab 2 file-based `/jobs` endpoints are retained for compatibility but are not tested in Lab 3. No worker is deployed, and each pod has an independent filesystem. A shared external queue/storage would be required for reliable distributed job processing.

The Flask development server is used for this educational exercise, not a production deployment. No AWS services or secrets are needed.
