import time
import random
import requests

BROKER_URL = "http://127.0.0.1:6000"
TOPIC = "orders"

print(f'[CONSUMER] Starting, polling {BROKER_URL}/queue/{TOPIC}')

while True:
    response = requests.get(f"{BROKER_URL}/queue/{TOPIC}")

    if response.status_code == 204:
        print('[CONSUMER] Queue empty, waiting...')
        time.sleep(2)
        continue

    message = response.json()
    print(f'[CONSUMER] Got order: {message}')
    processing_time = random.uniform(2, 3)
    time.sleep(processing_time)
    print(f'[CONSUMER] Finished processing order #{message.get("order_id")} '
          f'in {processing_time:.1f}s')
