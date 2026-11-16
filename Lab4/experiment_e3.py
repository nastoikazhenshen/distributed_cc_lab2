"""E3: with replica detached, compare three read-after-write results."""
import requests

BASE = "http://127.0.0.1:5000"
for i in range(1, 4):
    write = requests.post(f"{BASE}/counter/increment", timeout=5)
    write.raise_for_status()
    a_resp = requests.get(f"{BASE}/counter", params={"from": "primary"}, timeout=5)
    b_resp = requests.get(f"{BASE}/counter", params={"from": "replica"}, timeout=5)
    a_resp.raise_for_status()
    b_resp.raise_for_status()
    print(f"Write {i}: primary={a_resp.json()['value']}, replica={b_resp.json()['value']}")
