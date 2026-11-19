# Service Specification — Lab 5

**Author:** Ivaikina Darya  
**Version:** 4  
**Based on:** Laboratory Works 2, 3, and 4

## 1. Purpose and architecture

This version tests a local stateless record-storage path through nginx and three Flask API copies, backed by a MongoDB replica set with three nodes. Previous /echo, /time and /jobs endpoints are preserved for demonstration/compatibility. **Only /records is a distributed persisted workflow.** The file-based /jobs queue remains replica-local and is not suitable for cross-replica workflows.

## 2. Functional requirements

| ID | Endpoint or behavior | Expected response | HTTP code |
|---|---|---|---|
| R1 | POST `/echo`, JSON `message`: non-empty string, max 1000 chars | `reply` equals message; invalid input rejected | 200 / 400 |
| R2 | GET `/time` | JSON `server_time` and `served_by` (api1/api2/api3) | 200 |
| R3 | POST `/jobs`, valid `message` as for R1 | UUID `job_id`, `queued` (replica-local legacy queue) | 202 / 400 |
| R4 | GET `/jobs/{job_id}` | queued/done if found on this replica, otherwise JSON error; invalid UUID rejected | 200 / 404 |
| R5 | Unknown path / unsupported method | JSON error, not HTML | 404 / 405 |
| R6 | POST `/records`, JSON object with nonempty string `text` | UUID `id`, `text`, `served_by`; durable majority-acknowledged MongoDB write | 201 / 400 / 503 |
| R7 | GET `/records/{rec_id}` | matching `id`, `text`, `served_by`; unknown id gives JSON error | 200 / 404 / 503 |
| R8 | MongoDB unavailable / no writable primary | record storage endpoints return JSON `storage unavailable` without process crash | 503 |
| R9 | nginx balancing to three healthy copies | at least two distinct `served_by` in 30 GET `/time` requests | 200 |
| R10 | Stop one API replica | nginx routes requests to surviving replicas; stopped replica absent in distribution | 200 expected on `/time` |
| R11 | Stop MongoDB primary | probe records write interruption/errors and recovery after election | 201 and transient 503 |

## 3. Quantitative nonfunctional requirements (test targets, not measured results)

- **N1:** 30 sequential `/time` requests through nginx must reach at least **2** different API copies.
- **N2:** Under 10 concurrent Locust users for 60 seconds, HTTP failure rate should be at most **1%** and aggregate p95 at most **500 ms**.
- **N3:** Under 50 concurrent Locust users for 60 seconds, failure rate should be at most **2%** and aggregate p95 at most **1000 ms**.
- **N4:** Under 100 concurrent Locust users for 60 seconds, failure rate should be at most **5%** and aggregate p95 at most **2000 ms**. The main goal is to locate load saturation; failure to meet a target is reported, not concealed.
- **N5:** For an unavailable MongoDB primary, a record operation must return a bounded response (503, or 201 after re-election) rather than hang indefinitely; MongoClient selection timeout **3000 ms**, socket timeout **5000 ms**, majority write timeout **5000 ms**. Transient proxy/client errors, if observed, are also logged.
- **N6:** MongoDB writes use **w=majority**; this 3-node replica set needs acknowledgement from 2 voting nodes. Replica node internal ports are not exposed to host. Host nginx port is 127.0.0.1:8080.

## 4. Data & environment

- MongoDB 7, three members: mongo1, mongo2, mongo3; replica set rs0; database lab5, collection records.
- HTTP service: Python 3.12, Flask, PyMongo; Docker internal port 5000.
- Three API replicas api1/api2/api3 with hostname identification.
- nginx upstream round-robin on local port 8080, with upstream failure retry for safe request types as configured.
- No authentication: strictly local educational demo. Do not expose MongoDB or application publicly.
- This setup prioritizes acknowledged replicated writes during failover; CAP choices should be discussed with reference to observed write interruption, election and majority, rather than a blanket claim about all MongoDB operations.

## 5. How to verify

- pytest tests/test_api.py -v
- python tests/distribution.py before and after stopping api2
- locust -f tests/locustfile.py --headless -u 10 -r 5 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_10 (repeat for 50 and 100)
- python -u tests/probe.py | tee logs/probe_api_down.txt (stop/restart api2)
- python -u tests/probe.py | tee logs/probe_primary_down.txt (stop/restart current MongoDB primary)
