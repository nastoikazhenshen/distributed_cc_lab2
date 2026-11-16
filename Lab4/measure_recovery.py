"""E2: observe when values agree after REPLICAOF is restored.

Run immediately after reconnecting the replica. This measures time from
starting this script, NOT total time since issuing the Redis command.
"""
import time
import requests

BASE = "http://127.0.0.1:5000"
start = time.monotonic()
while time.monotonic() - start < 30:
    p = requests.get(f"{BASE}/counter", params={"from": "primary"}, timeout=5)
    r = requests.get(f"{BASE}/counter", params={"from": "replica"}, timeout=5)
    p.raise_for_status()
    r.raise_for_status()
    a, b = p.json()["value"], r.json()["value"]
    if a == b:
        print(f"Primary: {a}; replica: {b}")
        print(f"Catch-up observed {time.monotonic() - start:.4f} seconds after monitoring began")
        break
    time.sleep(0.05)
else:
    print("Values did not converge within 30 seconds")
