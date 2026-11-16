# Lab 4 — Data Storage and Replication (local RustFS, no AWS)

This directory is ready for local development in **PyCharm on macOS**. The actual experiment outcomes, screenshots and PDF report must be produced from your own runs. **Nothing needs to be pushed to GitHub.**

## 1. Open the project

Put this `Lab4` directory next to `Lab3` inside `distributed_cc_lab2` (do not overwrite Lab3). Open the repository as a project in PyCharm; open its terminal and run:

```bash
cd Lab4
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If PyCharm does not select the environment automatically, select `Lab4/.venv/bin/python` as Project Interpreter.

## 2. Start Docker Desktop and stores

```bash
docker compose up -d
docker compose ps
```

RustFS console: http://127.0.0.1:9001 (or http://127.0.0.1:9001/rustfs/console/); username `lab4user`, password `lab4password` (training-only).

## 3. Start Flask (keep this terminal open)

```bash
source .venv/bin/activate
source ./setup_env.sh
python app.py
```

**Important:** `source ./setup_env.sh` must run in the same terminal as `python app.py`, since environment variables are terminal-local. Use a second PyCharm terminal for the commands below. Flask: http://127.0.0.1:5000/time.

## 4. Part A — object storage tests

In the second terminal:

```bash
curl -i -X POST http://127.0.0.1:5000/files -H 'Content-Type: application/json' -d '{"content":"Hello from Lab 4"}'
```

Copy the **actual** `file_id` from the returned JSON and replace `YOUR_FILE_ID` below:

```bash
curl -i http://127.0.0.1:5000/files/YOUR_FILE_ID
curl -i http://127.0.0.1:5000/files/00000000-0000-4000-8000-000000000000
```

Take screenshots of successful upload (`201`), read (`200`), missing file (`404`) and the object in the RustFS web console. Stop Flask (`Control+C`), restart with `python app.py`, and read the **same** file. Then, in the second terminal:

```bash
docker compose up -d --force-recreate s3
```

Wait for storage startup and read the **same** file again. Capture the evidence. **Do not run `docker compose down -v`**; it deletes the persistent volume.

## 5. Part B1 — check Redis replication

```bash
docker compose exec redis-primary redis-cli info replication
docker compose exec redis-replica redis-cli info replication
```

Expected after the connection stabilizes: primary `role:master` and `connected_slaves:1`; replica `role:slave` and `master_link_status:up`. Capture screenshots.

## 6. E1 — normal mode

From a second PyCharm terminal in `Lab4`, with the virtual environment activated:

```bash
python experiment_e1.py | tee logs/E1.txt
```

Capture `screenshots/E1.png`. Even **zero** stale reads is valid locally; record the measured number.

## 7. E2 — detached replica and eventual catch-up

```bash
{
  docker compose exec redis-replica redis-cli REPLICAOF 127.0.0.1 1
  curl -s 'http://127.0.0.1:5000/counter?from=replica'; echo
  for i in {1..10}; do curl -s -X POST http://127.0.0.1:5000/counter/increment; echo; done
  curl -s 'http://127.0.0.1:5000/counter?from=primary'; echo
  curl -s 'http://127.0.0.1:5000/counter?from=replica'; echo
} | tee logs/E2.txt
```

These commands use macOS zsh/bash (the `{1..10}` loop is shell brace expansion). Record primary/replica values. Restore replication and observe catch-up:

```bash
docker compose exec redis-replica redis-cli REPLICAOF redis-primary 6379
python measure_recovery.py | tee logs/E2_recovery.txt
docker compose exec redis-replica redis-cli info replication
```

Capture before/after screenshots. The script's time begins **after** you start it, not when Redis reconnect began; describe it as approximate observation time.

## 8. E3 — read-your-own-write

```bash
docker compose exec redis-replica redis-cli REPLICAOF 127.0.0.1 1
python experiment_e3.py | tee logs/E3.txt
docker compose exec redis-replica redis-cli REPLICAOF redis-primary 6379
```

Capture `screenshots/E3.png`. Wait for the replica link to return to `up` before E4.

## 9. E4 — manual failover

Run the commands below **one at a time**, capturing command output and screenshots:

```bash
docker compose stop redis-primary
curl -i -X POST http://127.0.0.1:5000/counter/increment  # expect 503
curl -i 'http://127.0.0.1:5000/counter?from=replica'  # read may work
docker compose exec redis-replica redis-cli REPLICAOF NO ONE
docker compose exec redis-replica redis-cli info replication
```

**In the terminal running Flask:** stop with `Control+C`, then switch **only** its primary port and restart:

```bash
export REDIS_PRIMARY_PORT=6380
python app.py
```

Now from the second terminal:

```bash
curl -i -X POST http://127.0.0.1:5000/counter/increment  # expect 200
curl -i 'http://127.0.0.1:5000/counter?from=primary'
docker compose start redis-primary
docker compose exec redis-primary redis-cli info replication
docker compose exec redis-replica redis-cli info replication
docker compose exec redis-primary redis-cli GET counter
docker compose exec redis-replica redis-cli GET counter
```

Record the two `role:master` outputs and counter values **before repair**. To bring the old primary under the promoted node and avoid two independent masters:

```bash
docker compose exec redis-primary redis-cli REPLICAOF redis-replica 6379
docker compose exec redis-primary redis-cli info replication
docker compose exec redis-replica redis-cli info replication
```

**Caution:** rejoining the old primary as a replica may replace its local dataset. This is a deliberately manual educational failover; `docker-compose.yml` still has its original initial-role configuration for fresh deployments.

Save real outputs for E4 in `logs/E4.txt` (you may copy terminal text into that file) and take screenshots.

## 10. Deliverables after completing experiments

- `app.py`, `requirements.txt`, `docker-compose.yml`, `spec.md` (already supplied).
- `logs/`: actual E1–E4 outputs (currently empty).
- `screenshots/`: your actual evidence (currently empty).
- `report.pdf`: 1–2 pages with the measured E1–E4 table plus answers to the four reflection questions in the assignment (not supplied, because results do not exist yet).

From the `Lab4` directory **after** creating the report:

```bash
zip -r ../Ivaikina_Darya_Lab4.zip app.py requirements.txt docker-compose.yml spec.md logs screenshots report.pdf
```

Do not include `.venv`, real credentials, or pretend experiment results. Experiment helper scripts can remain local (the required submission list does not require them).
