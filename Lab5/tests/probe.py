import argparse
import datetime
import time
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://127.0.0.1:8080/records")
args = parser.parse_args()

while True:
    start = time.perf_counter()
    now = datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")
    try:
        response = requests.post(args.url, json={"text": "probe"}, timeout=12)
        print(now, response.status_code, f"latency_ms={1000 * (time.perf_counter() - start):.1f}", flush=True)
    except requests.RequestException as exc:
        print(now, "ERROR", type(exc).__name__, f"latency_ms={1000 * (time.perf_counter() - start):.1f}", flush=True)
    time.sleep(0.5)
