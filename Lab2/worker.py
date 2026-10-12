import glob
import json
import os
import shutil
import time
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
FAILED_DIR = os.path.join(BASE_DIR, "failed")

for d in (QUEUE_DIR, RESULTS_DIR, FAILED_DIR):
    os.makedirs(d, exist_ok=True)

print("[WORKER] Started, watching queue/ ...")

while True:
    files = sorted(glob.glob(os.path.join(QUEUE_DIR, "*.json")), key=os.path.getmtime)
    if not files:
        time.sleep(1)
        continue

    path = files[0]
    try:
        job_id = str(uuid.UUID(os.path.splitext(os.path.basename(path))[0]))
        with open(path, encoding="utf-8") as f:
            body = json.load(f)
        message = body["message"]
        if not isinstance(message, str):
            raise ValueError("message is not a string")
    except (ValueError, KeyError, TypeError, OSError):
        # malformed job: move it aside so it does not block the queue
        print(f"[WORKER] Malformed job {os.path.basename(path)} -> moved to failed/")
        shutil.move(path, os.path.join(FAILED_DIR, os.path.basename(path)))
        continue

    print(f"[WORKER] Processing job {job_id} ...")
    time.sleep(2)  # imitate slow work

    result = {
        "original": message,
        "uppercase": message.upper(),
        "processed_at": datetime.now().isoformat(timespec="seconds"),
    }
    tmp_path = os.path.join(RESULTS_DIR, f"{job_id}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(result, f)
    os.replace(tmp_path, os.path.join(RESULTS_DIR, f"{job_id}.json"))

    os.remove(path)  
    print(f"[WORKER] Done {job_id}")
