from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def get_time(self):
        self.client.get("/time", name="GET /time", timeout=15)

    @task(1)
    def create_record(self):
        with self.client.post("/records", json={"text": "load"}, name="POST /records", timeout=15, catch_response=True) as response:
            if response.status_code != 201:
                response.failure(f"expected 201, got {response.status_code}")
