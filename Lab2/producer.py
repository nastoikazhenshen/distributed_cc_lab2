import time
import random
import requests
from datetime import datetime

BROKER_URL = "http://127.0.0.1:6000"
TOPIC = "orders"

order_number = 1

print(f'[PRODUCER] Starting, sending to {BROKER_URL}/queue/{TOPIC}')

while True:
    order = {
        "order_id": order_number,
        "created_at": str(datetime.now()),
        "amount": round(random.uniform(10, 500), 2),
    }

    response = requests.post(f"{BROKER_URL}/queue/{TOPIC}", json=order)
    print(f'[PRODUCER] Sent order #{order_number} -> status {response.status_code}')

    order_number += 1
    time.sleep(random.uniform(1, 2))
