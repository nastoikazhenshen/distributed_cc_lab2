# Test Report — Laboratory Work 5

**Student:** Ivaikina Darya  
**Group:** 202610:ICT4401-ENG-1  
**Test dates:** November 19–20, 2026 (Asia/Almaty, UTC+05:00)  
**Tested service:** Flask REST API with nginx and a three-member MongoDB replica set  
**Environment:** Local macOS computer; Python 3.14.0 in the host virtual environment; Python 3.12 in the API Docker images; Docker Compose; MongoDB 7; nginx 1.27; Locust 2.47.0; pytest 9.2.0.  
**Deployment:** `api1`, `api2`, `api3`, `nginx`, `mongo1`, `mongo2`, `mongo3` (seven containers). The nginx endpoint is `http://127.0.0.1:8080`.

## 1. Test cases

The ten automated test cases were run using:

```bash
python -m pytest tests/test_api.py -v
```

**Observed result:** `10 passed in 1.31s` (November 19, 2026). Each row corresponds to an actual named pytest case and a requirement in `spec.md` version 4.

| # | Requirement (spec.md) | Type | Input / procedure | Expected | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| 1 | R1 | Functional | `POST /echo`, `{"message":"Lab 5"}` | 200, matching reply | Correct 200 response and reply; pytest passed | PASS |
| 2 | R1 | Negative | `POST /echo`, empty message | 400 | 400; pytest passed | PASS |
| 3 | R1 | Boundary / edge | `POST /echo` with 1,000 and 1,001 characters | 200 for 1,000; 400 for 1,001 | Both assertions passed | PASS |
| 4 | R2 | Functional | `GET /time` | 200 with `server_time` and `served_by` | Both present; pytest passed | PASS |
| 5 | R5 | Negative | `GET /missing-route` | JSON error, 404 | 404 with JSON error; pytest passed | PASS |
| 6 | R6, R7 | Functional | `POST /records`, then `GET /records/{id}` | 201, then 200, with matching UUID and text | All assertions passed | PASS |
| 7 | R6 | Negative | `POST /records`, JSON `{}` | 400 | 400; pytest passed | PASS |
| 8 | R6 | Edge / invalid type | `POST /records`, JSON array | 400 | 400; pytest passed | PASS |
| 9 | R7 | Negative | `GET /records/{random-uuid}` | 404 | 404; pytest passed | PASS |
| 10 | R3, R4 | Functional + negative | Valid `POST /jobs`; invalid UUID to `GET /jobs/{id}` | 202 queued; then 404 | Both assertions passed | PASS |

**Additional manual and fault tests:**

| # | Requirement | Type | Input / procedure | Expected | Actual | Pass/Fail |
|---|---|---|---|---|---|---|
| 11 | R8 | Failure / negative | Stop all three MongoDB nodes; `POST /records` | JSON 503, no application crash | 503 `{"error":"storage unavailable"}` | PASS |
| 12 | R9, N1 | Load balancing | 30 `GET /time` requests with all replicas running | At least two distinct `served_by` values | `api1=10`, `api2=10`, `api3=10` | PASS |
| 13 | R10 | Fault tolerance | Stop `api2`; send 30 `GET /time` requests; probe record writes | Stopped replica absent; surviving API copies respond | `api1=15`, `api2=0`, `api3=15`; 0 errors in probe log | PASS |
| 14 | R11, N5 | Failover observation | Stop MongoDB PRIMARY `mongo2` while probing `POST /records` | Writes recover after election; transient 503 may occur, but is not required for a successful recovery | `mongo1` became PRIMARY; 277 logged responses were 201; 0 observed 503; max measured latency 432.6 ms | PASS for observed recovery; no 503 observed |

The file-based `/jobs` workflow is replica-local; the test checks acceptance and invalid UUID handling, **not** cross-replica job retrieval. The observed 0-error failover does not establish a precise election or unavailability duration.

**Evidence:** `screenshots/C1_pytest.png`, `screenshots/A2_record_roundtrip.png`, `screenshots/A2_storage_503.png`, `screenshots/B3_distribution.png`, `logs/probe_api_down.txt`, `logs/probe_primary_down.txt`.

## 2. Load tests

**Tool and workload:** Locust 2.47.0 in headless mode, through nginx. Locust tasks use `GET /time` (weight 3) and `POST /records` (weight 1), with 0.1–0.5 s user wait. Three runs used 10, 50, and 100 concurrent users for 60 seconds each. The following commands are reproducible:

```bash
locust -f tests/locustfile.py --headless -u 10 -r 5 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_10
locust -f tests/locustfile.py --headless -u 50 -r 10 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_50
locust -f tests/locustfile.py --headless -u 100 -r 20 -t 60s --host http://127.0.0.1:8080 --csv logs/locust_100
```

The following values are taken from the final **Aggregated** Locust results supplied after each real run. Errors (%) = failure count / request count × 100.

| Users | Duration | Request Count | Failure Count | RPS | Median, ms | p95, ms | Errors, % | Target from spec.md | Pass/Fail |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 10 | 60 s | 1,906 | 0 | 32.21 | 7 | 15 | 0.00 | N2: ≤1% failures; p95 ≤500 ms | PASS |
| 50 | 60 s | 9,180 | 0 | 154.85 | 5 | 14 | 0.00 | N3: ≤2% failures; p95 ≤1,000 ms | PASS |
| 100 | 60 s | 17,150 | 0 | 289.14 | 8 | 140 | 0.00 | N4: ≤5% failures; p95 ≤2,000 ms | PASS |

**Additional endpoint-level observations at 100 users:** `GET /time` had 12,914 requests, 0 failures, median 6 ms and p95 130 ms; `POST /records` had 4,236 requests, 0 failures, median 13 ms and p95 160 ms.

**Saturation analysis:** Throughput increased from 32.21 to 154.85 to 289.14 RPS, with no observed HTTP failures. The first clear sign of performance pressure occurred at 100 users: aggregate p95 rose from 14 ms at 50 users to 140 ms at 100 users (10×). This indicates increased tail latency at the highest tested level, but it does **not** prove that maximum throughput or a true saturation point was reached. CPU, memory, queue depth and per-component timings were not separately measured, so the exact bottleneck cannot be conclusively assigned to nginx, Flask, or MongoDB.

**Evidence:** `logs/locust_10_stats.csv`, `logs/locust_50_stats.csv`, `logs/locust_100_stats.csv`, associated `*_stats_history.csv`, `screenshots/C2_locust_10.png`, `screenshots/C2_locust_50.png`, `screenshots/C2_locust_100.png`.

## 3. Fault tolerance & load balancing

### Normal request distribution

Thirty sequential requests through nginx reached `api1=10`, `api2=10`, `api3=10`; thus **all three copies** responded and N1/R9 passed. Evidence: `screenshots/B3_distribution.png`.

### Scenario 1 — one API replica stopped

The `api2` container was stopped using `docker compose stop api2`; the operator's recorded initiation time was **November 20, 2026, 00:02:14 +05:00**. `docker compose ps` showed `api1` and `api3` running with `api2` absent. Repeating the 30-request distribution yielded `api1=15`, `api2=0`, `api3=15`. While `api2` was stopped, the separate probe logged successful `POST /records` calls, with **0 counted 500/502/503/ERROR responses**. The replica was restarted with `docker compose start api2`, and the final `docker compose ps` showed all seven containers running.

**Interpretation:** nginx successfully routed around the stopped API copy in this test, preserving the externally accessible service. The exact API shutdown-completion and restart times were not captured to subsecond precision. Evidence: `screenshots/C3_api_down.png` and `logs/probe_api_down.txt`.

### Scenario 2 — MongoDB PRIMARY stopped

Before failure, `db.hello().primary` returned `mongo2:27017`. The probe sent repeated writes to `POST /records` while `mongo2` was stopped. Docker container events were inspected and saved.

| Event | Time (Asia/Almaty, UTC+05:00) |
|---|---|
| `mongo2` termination initiated (`kill` event) | 2026-11-20 00:08:59 |
| `mongo2` `stop` / `die` event | 2026-11-20 00:09:03 |
| First HTTP 503 in probe | **Not observed** |
| Total HTTP 503 errors | **0** |
| Other 500/502/504/ERROR entries | **0** |
| First shown successful `201` in probe after the recorded stop second | 2026-11-20 00:09:03.281 (+05:00; logged timestamp) |
| Highest observed request latency | **432.6 ms**, on logged request at 00:09:00.259 |
| New PRIMARY observed | `mongo1:27017` (exact election timestamp not captured) |
| Stopped `mongo2` container restarted | 2026-11-20 00:14:31 |
| Final replica-set state | `mongo1` PRIMARY; `mongo2` and `mongo3` SECONDARY |

The probe log contains **277 requests, all with response 201**, and no logged 503 or transport errors. Since the probe logged a successful response around the stop event, and `mongo1` became PRIMARY, successful failover is supported. The logged first success is **not** a direct measurement of the election duration: the exact moment of the new PRIMARY election was not captured, and timestamp semantics may refer to request start rather than response completion. Restarting the old node at 00:14:31 is also **not** the client recovery time. The supported conclusion is **no client-visible failed writes were observed in this run**, with maximum observed request latency 432.6 ms.

**CAP interpretation:** A MongoDB replica set elects a writable PRIMARY, and the application uses a majority write concern (`w=majority`). When the PRIMARY disappears, acknowledged writes require a majority-supported writable PRIMARY; the system may briefly delay or reject writes rather than permit conflicting acknowledged writes. This is a trade-off favoring consistency of majority-acknowledged writes under relevant partitions and failover conditions. Here no 503 occurred: the election and/or driver retry behavior made the interruption invisible to the 0.5-second probe. These results do not prove universal availability, a zero-duration election, or anything about secondary-read consistency, since secondary reads were not separately tested.

**Evidence:** `logs/probe_primary_down.txt`, `logs/mongo2_events.txt`, `screenshots/C3_primary_down.png` and `screenshots/C3_new_primary.png` (post-recovery replica-set state). The PRIMARY change is supported by the before/after `db.hello().primary` outputs and the recorded Docker events.

## 4. Conclusions & recommendations

**Conclusions.** All 10 automated pytest cases passed, and the additional manual 503 test confirmed graceful handling of full database unavailability. With all replicas healthy, nginx distributed 30 requests evenly (10/10/10). With `api2` stopped, remaining replicas answered 15/15 with no counted probe errors. During the MongoDB PRIMARY failure, the system elected `mongo1`; the probe logged 277 successful writes with 0 failures. All three 60-second load levels met the defined p95 and failure-rate targets. The dominant observed performance concern is the increase in aggregate p95 from 14 ms (50 users) to 140 ms (100 users), although throughput continued to increase.

**Bottleneck hypothesis:** Higher concurrency increases tail latency; likely contributing factors may include the Flask development servers, database write acknowledgement, and local host resource contention. The specific limiting component **was not measured** and therefore is a hypothesis, not a proven cause.

1. **Priority 1 — improve API serving and instrumentation.** Replace Flask's development server with a production-capable WSGI server (for example Gunicorn) in a later controlled comparison; collect per-container CPU/memory utilization and per-endpoint latency. **Expected impact:** improved concurrent request handling and visibility into the cause of tail-latency growth. Verify rather than assume any performance gain.
2. **Priority 2 — strengthen fault observability and resilience validation.** Record precise Docker stop/election events and continuous write/read probes together; add a separate, controlled read-after-write check and repeat primary failover several times. **Expected impact:** reliable measurement of election/recovery windows and clearer evidence about data consistency and transient failures. A test using more frequent probes or forced failover may reveal issues not seen in this run.

**Retest plan:** Repeat the same 10/50/100 user, 60-second Locust runs using identical workload parameters; compare aggregate RPS, median, p95 and failure rate with this baseline. If resources permit, add a higher-concurrency level to locate actual saturation while recording host/container utilization. Re-run API replica failure and MongoDB PRIMARY failure at least three times; log event timestamps, failure count, first recovered success and, if observable, precise election duration.

**Limitations:** Results are from one local machine and are not a production capacity guarantee. The legacy `/jobs` queue is local to each API replica and is not safe as a shared distributed queue. MongoDB runs without authentication and internal database ports are not published, as required for this local educational exercise. No separate read-from-secondary experiment or resource utilization monitoring was performed.

**Evidence index:** `screenshots/` contains screenshots of replica-set state, record round-trip, storage error, Compose services, normal distribution, pytest, three Locust results and both fault scenarios; `logs/` contains three Locust CSV result groups, the two probe files and `mongo2_events.txt`.
