# Laboratory Work 3 — Docker and Kubernetes

**Student:** Ivaikina Darya  
**Course:** Distributed & Cloud Computing  
**Lab:** 3 — Docker and Kubernetes

## Overview

This laboratory work extends the Flask REST API from Lab 2. The API is packaged as a Docker image, started with Docker Compose, and deployed to a local Kubernetes cluster using Minikube. The experiments demonstrate multiple replicas, request distribution, self-healing, and scaling.

## Project structure

```text
Lab3/
├── app/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── k8s/
│   ├── deployment.yaml
│   └── service.yaml
├── screenshots/
├── spec.md
└── DCC_lab3_Ivaykina.pdf
```

## Technology

Python 3.12, Flask, Docker Desktop, Docker Compose, Kubernetes, Minikube, and kubectl. Experiments were performed on macOS (Intel).

## Part A — Docker and Compose

The application listens on `0.0.0.0:5000`. The `GET /time` response includes `served_by` to identify the container or pod that handled the request.

From the `Lab3` directory:

```bash
docker build -t my-api:lab3 ./app
docker run --rm -p 5000:5000 my-api:lab3
```

Test in another terminal: `curl http://127.0.0.1:5000/time`. Stop the foreground container before starting Compose.

```bash
docker compose up --build -d
docker compose ps
docker compose down
```

## Part B — Kubernetes

```bash
minikube start --driver=docker --cpus=2 --memory=2048
minikube image load my-api:lab3
kubectl apply -f k8s/deployment.yaml -f k8s/service.yaml
kubectl get pods
minikube service my-api --url
```

The Deployment targets three replicas. The NodePort Service selects pods with the label `app: my-api`.

**Observed local Minikube tunnel port:** `50584`, giving the session URL `http://127.0.0.1:50584`. This is a dynamically assigned local tunnel port and may change when the command is restarted. The Flask container still listens on port `5000`; the Kubernetes Service uses port `80`.

To test distribution, keep `minikube service my-api --url` running and send 30 separate requests to `/time`, grouping responses by `served_by`.

## Part C — Self-healing and scaling

```bash
kubectl get pods -w
kubectl delete pod <actual-pod-name>
kubectl scale deployment my-api --replicas=5
kubectl get pods
kubectl scale deployment my-api --replicas=3
kubectl get pods
```

The Deployment replaces a deleted pod to maintain the requested replica count. Scaling increases the target from three to five and returns it to three. Repeated requests to `/time` can be used to observe availability during replacement.

## Limitations and evidence

Only the API is deployed. The file-based `/jobs` workflow from Lab 2 requires a separate worker and shared queue/storage to work across replicas, so it is not part of these tests.

The `screenshots/` directory contains experiment evidence; the PDF report contains answers to the reflection questions. See [spec.md](spec.md) for API and deployment details.
