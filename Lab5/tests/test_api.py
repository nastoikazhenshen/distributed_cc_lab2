"""Repeatable functional/negative/edge tests mapped to spec.md v4."""
import uuid
import requests

BASE = "http://127.0.0.1:8080"
TIMEOUT = 15


def test_r1_echo_success():
    response = requests.post(f"{BASE}/echo", json={"message": "Lab 5"}, timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["reply"] == "Lab 5"


def test_r1_echo_empty_negative():
    response = requests.post(f"{BASE}/echo", json={"message": ""}, timeout=TIMEOUT)
    assert response.status_code == 400


def test_r1_echo_max_length_edge():
    response = requests.post(f"{BASE}/echo", json={"message": "x" * 1000}, timeout=TIMEOUT)
    assert response.status_code == 200
    response = requests.post(f"{BASE}/echo", json={"message": "x" * 1001}, timeout=TIMEOUT)
    assert response.status_code == 400


def test_r2_time_contains_served_by():
    response = requests.get(f"{BASE}/time", timeout=TIMEOUT)
    assert response.status_code == 200
    assert response.json()["served_by"] in {"api1", "api2", "api3"}
    assert "server_time" in response.json()


def test_r5_unknown_path_returns_json_404():
    response = requests.get(f"{BASE}/missing-route", timeout=TIMEOUT)
    assert response.status_code == 404
    assert "error" in response.json()


def test_r6_create_and_r7_read_record():
    response = requests.post(f"{BASE}/records", json={"text": "replica set test"}, timeout=TIMEOUT)
    assert response.status_code == 201, response.text
    record_id = response.json()["id"]
    assert str(uuid.UUID(record_id)) == record_id
    fetched = requests.get(f"{BASE}/records/{record_id}", timeout=TIMEOUT)
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["text"] == "replica set test"
    assert fetched.json()["id"] == record_id


def test_r6_missing_text_negative():
    response = requests.post(f"{BASE}/records", json={}, timeout=TIMEOUT)
    assert response.status_code == 400


def test_r6_non_object_json_edge():
    response = requests.post(f"{BASE}/records", json=[1, 2], timeout=TIMEOUT)
    assert response.status_code == 400


def test_r7_unknown_record_negative():
    response = requests.get(f"{BASE}/records/{uuid.uuid4()}", timeout=TIMEOUT)
    assert response.status_code == 404


def test_r3_job_accepted_and_r4_invalid_id():
    response = requests.post(f"{BASE}/jobs", json={"message": "hello"}, timeout=TIMEOUT)
    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    invalid = requests.get(f"{BASE}/jobs/not-a-uuid", timeout=TIMEOUT)
    assert invalid.status_code == 404
