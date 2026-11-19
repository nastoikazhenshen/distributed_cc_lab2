# Laboratory Work 5 — NoSQL, Fault Tolerance and Load Balancing

**Course:** Distributed & Cloud Computing  
**Student:** Ivaikina Darya  
**Group:** 202610:ICT4401-ENG-1  
**Test dates:** November 19–20, 2026 (Asia/Almaty, UTC+05:00)  
**Environment:** macOS, Docker Compose, MongoDB 7, nginx 1.27, Flask on Python 3.12 containers, pytest 9.2.0, Locust 2.47.0 (host Python 3.14.0).

## 1. Purpose

This laboratory extends the REST service built in earlier labs to investigate **replication, load balancing, failure recovery and performance under concurrent load**. The system uses three MongoDB nodes as a replica set (`rs0`), three Flask application instances, and an nginx reverse proxy. The work was performed locally; AWS was not required.

## 2. System architecture

```text
Client / pytest / Locust / probe
              |
       127.0.0.1:8080
              |
            nginx
              |
      +-------+-------+
      |       |       |
    api1    api2    api3        (Flask, port 5000 inside Docker)
      |       |       |
      +-------+-------+
              |
     MongoDB replica set rs0
      mongo1 mongo2 mongo3      (port 27017 inside Docker)
```

- `nginx.conf` defines the three API upstreams and failover/retry settings.
- `docker-compose.yml` defines seven containers and the MongoDB data volumes.
- `init-replica.js` initializes the three-member replica set.
- `app/app.py` provides JSON REST endpoints; `/records` uses MongoDB with majority-acknowledged writes.
- `/time` returns `server_time` and `served_by`, making replica distribution observable.
- The legacy `/jobs` endpoint remains **replica-local** because it uses a file-based queue. It is not a distributed persistence workflow and cannot guarantee cross-replica job retrieval.
- The nginx port is bound locally; MongoDB ports are not published to the host.

## 3. Implemented API

| Method | Endpoint | Description | Main statuses |
|---|---|---|---|
| POST | `/echo` | Echo validated nonempty text up to 1,000 characters | 200, 400 |
| GET | `/time` | Show server time and answering API replica | 200 |
| POST | `/jobs` | Submit a legacy replica-local job | 202, 400 |
| GET | `/jobs/{job_id}` | Check legacy job status | 200, 404 |
| POST | `/records` | Save a new MongoDB record | 201, 400, 503 |
| GET | `/records/{rec_id}` | Read a record by ID | 200, 404, 503 |

Unknown routes and unsupported methods return JSON errors. The formal functional and quantitative requirements are in `spec.md` **version 4** (R1–R11, N1–N6).

## 4. Setup and reproduction

From the `Lab5` directory, with Docker Desktop running:

```bash
docker compose up -d mongo1 mongo2 mongo3
docker compose exec mongo1 mongosh --quiet /scripts/init-replica.js
docker compose exec mongo1 mongosh --quiet --eval "rs.status().members.map(m => m.name + ' ' + m.stateStr)"
docker compose up -d --build
docker compose ps
docker compose exec nginx nginx -t
curl -i http://127.0.0.1:8080/time
```

**Important:** Run `rs.initiate` only for a fresh, uninitialized MongoDB replica set. When using existing Docker data volumes, check `rs.status()` instead. No AWS credentials or public database ports are needed.

Create and read a record (replace `<id>` with the ID actually returned):

```bash
curl -i -X POST http://127.0.0.1:8080/records \
  -H 'Content-Type: application/json' -d '{"text":"Lab 5 MongoDB test"}'
curl -i http://127.0.0.1:8080/records/<id>
```

Host test dependencies are listed in the root `requirements.txt`. With a Python virtual environment active:

```bash
python -m pip install -r requirements.txt
python -m pytest tests/test_api.py -v
```

## 5. Part A — MongoDB replica set and records

The initial cluster status was **mongo1 PRIMARY, mongo2 SECONDARY, mongo3 SECONDARY**. `POST /records` returned **201**, and `GET /records/{id}` returned **200** with the same record, even when different API copies served the requests. A nonexistent record returned **404**. When all MongoDB nodes were stopped, record creation returned **503** with `{"error":"storage unavailable"}`. After restoring MongoDB, record creation again returned **201**.

Evidence: `screenshots/A1_replica_set.png`, `A2_record_roundtrip.png`, `A2_storage_503.png`.

## 6. Part B — Three API copies and nginx

The nginx syntax check passed and Docker Compose showed **seven running containers**. Thirty requests to `/time` produced the following distribution:

| Replica | Responses |
|---|---:|
| api1 | 10 |
| api2 | 10 |
| api3 | 10 |

This satisfies the requirement to observe at least two distinct serving copies.

Evidence: `screenshots/B2_compose_ps.png`, `B3_distribution.png`.

## 7. Part C1 — Functional tests

Run:

```bash
python -m pytest tests/test_api.py -v
```

**Observed result:** **10 passed in 1.31 seconds**, including negative and boundary tests. The tests cover `/echo`, `/time`, JSON errors, MongoDB record creation/retrieval, and basic legacy job validation. Additional manual tests cover 503 responses and replica distribution.

Evidence: `tests/test_api.py`, `screenshots/C1_pytest.png`. The full requirement-to-test mapping appears in `test_report.md`.

## 8. Part C2 — Load testing

The workload in `tests/locustfile.py` calls `GET /time` and `POST /records`. Each scenario ran for 60 seconds through nginx:

```bash
locust -f tests/locustfile.py --headless -u 10 -r 5 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_10
locust -f tests/locustfile.py --headless -u 50 -r 10 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_50
locust -f tests/locustfile.py --headless -u 100 -r 20 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_100
```

| Users | Requests | Failures | Throughput (RPS) | Median | p95 |
|---:|---:|---:|---:|---:|---:|
| 10 | 1,906 | 0 | 32.21 | 7 ms | 15 ms |
| 50 | 9,180 | 0 | 154.85 | 5 ms | 14 ms |
| 100 | 17,150 | 0 | 289.14 | 8 ms | 140 ms |

All runs met the corresponding quantitative targets in `spec.md`. At 100 users the p95 response time rose notably, but a true throughput saturation point was **not conclusively located**.

Evidence: `logs/locust_10_*`, `locust_50_*`, `locust_100_*` CSV files and `screenshots/C2_locust_10.png`, `C2_locust_50.png`, `C2_locust_100.png`.

## 9. Part C3 — Failure experiments

### Scenario 1: one API copy fails

A probe sent repeated `POST /records` requests through nginx while `api2` was stopped. With `api2` unavailable, a separate 30-request `/time` distribution returned **api1: 15, api3: 15, api2: 0**. No 500/502/503/ERROR responses were counted in the probe log of this scenario. `api2` was restarted successfully.

Reproduction commands (run the probe in a **separate terminal**):

```bash
python -u tests/probe.py | tee logs/probe_api_down.txt
# in another terminal:
docker compose stop api2
# observe and check distribution, then:
docker compose start api2
# stop probe using Ctrl+C
```

### Scenario 2: MongoDB PRIMARY fails

Before the experiment, **mongo2** was PRIMARY. The `mongo2` stop/die Docker event occurred at **00:09:03** on November 20, 2026 (UTC+05:00). The remaining nodes elected **mongo1** as the new PRIMARY. The probe log contains **277 HTTP 201 responses**, **zero observed 503 errors**, and a maximum request latency of **432.6 ms** (at 00:09:00.259). `mongo2` was started again at **00:14:31** and rejoined as SECONDARY. The final state was **mongo1 PRIMARY, mongo2 SECONDARY, mongo3 SECONDARY**.

The **exact PRIMARY-election duration was not independently captured**. The old node's restart time is not the client's recovery time, and the absence of observed errors is not proof of zero interruption for every workload.

Reproduction approach: run `python -u tests/probe.py | tee logs/probe_primary_down.txt`; determine the active PRIMARY using `db.hello().primary`; stop that specific container; observe probe results and the new PRIMARY; restart the stopped container; verify `rs.status()`.

Evidence: `logs/probe_api_down.txt`, `logs/probe_primary_down.txt`, `logs/mongo2_events.txt`, `screenshots/C3_api_down.png`, `C3_primary_down.png`, `C3_new_primary.png`.

## 10. Conclusions and recommendations

1. The three Flask API copies were load-balanced correctly, and stopping one API copy did not produce observed probe errors.
2. MongoDB successfully elected a new PRIMARY when the old node failed. For majority-acknowledged writes, consistency constraints may temporarily limit write availability during failure/election. No 503 errors appeared in this particular recorded probe.
3. With 100 users, p95 rose to 140 ms compared with 14 ms at 50 users. This is increased tail latency; without CPU/memory/database measurements, the actual bottleneck remains undetermined.
4. **Recommendation 1:** compare the Flask development server with a production WSGI server and measure per-container CPU, memory and latency.
5. **Recommendation 2:** add precise event and request timing plus MongoDB election observability; rerun failover tests and verify read-after-write behavior.

## 11. Files and submission

| Path | Purpose |
|---|---|
| `docker-compose.yml`, `nginx.conf`, `init-replica.js` | Deployment and configuration |
| `app/` | Flask application, Dockerfile, runtime dependencies |
| `tests/` | Functional tests, Locust workload, probe and distribution script |
| `spec.md` | Version 4 specification and performance targets |
| `test_report.md` | Required detailed test report with expected/actual results, failure timeline and recommendations |
| `logs/` | Probe logs, Docker event log and Locust CSV exports |
| `screenshots/` | Evidence from the real local test runs |
| `Ivaikina_Darya_Lab5_Report.pdf` | Supplemental narrative report and answers to all four reflection questions |

The lab handout requires the source/configuration, `spec.md`, `test_report.md`, logs and screenshots in a single ZIP named **`Ivaikina_Darya_Lab5.zip`**. The PDF report and this README are additional documentation. Do **not** include `.venv/`, `.idea/`, `__pycache__/`, `.pytest_cache/`, or local temporary files. The repository was not modified or pushed by the assistant.
