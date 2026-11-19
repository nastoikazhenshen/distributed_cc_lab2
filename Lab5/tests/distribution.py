from collections import Counter
import requests

counts = Counter()
for _ in range(30):
    response = requests.get("http://127.0.0.1:8080/time", timeout=10)
    response.raise_for_status()
    counts[response.json()["served_by"]] += 1
print("Distribution from 30 requests:")
for name in sorted(counts):
    print(f"{name}: {counts[name]}")
print("Total:", sum(counts.values()))
