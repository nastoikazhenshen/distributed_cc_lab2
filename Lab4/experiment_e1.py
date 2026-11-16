"""E1: perform 100 writes and compare reads from primary and replica."""
import requests

BASE = "http://127.0.0.1:5000"
stale = 0

for i in range(1, 101):
    write = requests.post(f"{BASE}/counter/increment", timeout=5)
    write.raise_for_status()
    primary_resp = requests.get(f"{BASE}/counter", params={"from": "primary"}, timeout=5)
    replica_resp = requests.get(f"{BASE}/counter", params={"from": "replica"}, timeout=5)
    primary_resp.raise_for_status()
    replica_resp.raise_for_status()
    a = primary_resp.json()["value"]
    b = replica_resp.json()["value"]
    if a != b:
        stale += 1
        print(f"Write {i}: primary={a}, replica={b} (stale)")

print(f"Stale reads from the replica: {stale} out of 100")
