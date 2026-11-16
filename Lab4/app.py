"""Lab 4 Flask API: local RustFS (S3-compatible) + Redis replication."""
import json
import os
import socket
import uuid
from datetime import datetime

import boto3
import redis
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from flask import Flask, jsonify, request

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MAX_MESSAGE_LEN = 1000
MAX_FILE_BYTES = 1024 * 1024

# Lab 2 / 3 compatibility: jobs are local only and need a separate worker.
os.makedirs(QUEUE_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

BUCKET = os.environ.get("BUCKET", "lab4-files")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "http://127.0.0.1:9000")
# These are training credentials injected through environment variables.
s3 = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    endpoint_url=S3_ENDPOINT,
    config=Config(s3={"addressing_style": "path"}) if S3_ENDPOINT else None,
)

REDIS_HOST = os.environ.get("REDIS_HOST", "127.0.0.1")
primary = redis.Redis(
    host=REDIS_HOST,
    port=int(os.environ.get("REDIS_PRIMARY_PORT", "6379")),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)
replica = redis.Redis(
    host=REDIS_HOST,
    port=int(os.environ.get("REDIS_REPLICA_PORT", "6380")),
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def ensure_bucket():
    try:
        s3.head_bucket(Bucket=BUCKET)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchBucket", "NotFound"):
            s3.create_bucket(Bucket=BUCKET)
        else:
            raise


def get_message_or_error():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "message" not in data:
        return None, (jsonify({"error": "field 'message' is required"}), 400)
    message = data["message"]
    if not isinstance(message, str) or not message.strip():
        return None, (jsonify({"error": "field 'message' must be a non-empty string"}), 400)
    if len(message) > MAX_MESSAGE_LEN:
        return None, (jsonify({"error": f"field 'message' must be at most {MAX_MESSAGE_LEN} characters"}), 400)
    return message, None


# R1
@app.route("/echo", methods=["POST"])
def echo():
    message, error = get_message_or_error()
    if error:
        return error
    return jsonify({"reply": message}), 200


# R2 (Lab 3 version)
@app.route("/time", methods=["GET"])
def get_time():
    return jsonify({"server_time": datetime.now().isoformat(timespec="seconds"),
                    "served_by": socket.gethostname()}), 200


# R3/R4 preserved for backwards compatibility; worker not used in Lab 4.
@app.route("/jobs", methods=["POST"])
def submit_job():
    message, error = get_message_or_error()
    if error:
        return error
    job_id = str(uuid.uuid4())
    tmp_path = os.path.join(QUEUE_DIR, f"{job_id}.tmp")
    final_path = os.path.join(QUEUE_DIR, f"{job_id}.json")
    with open(tmp_path, "w", encoding="utf-8") as stream:
        json.dump({"job_id": job_id, "message": message,
                   "submitted_at": datetime.now().isoformat(timespec="seconds")}, stream)
    os.replace(tmp_path, final_path)
    return jsonify({"job_id": job_id, "status": "queued"}), 202


@app.route("/jobs/<job_id>", methods=["GET"])
def job_status(job_id):
    try:
        job_id = str(uuid.UUID(job_id))
    except ValueError:
        return jsonify({"error": "job not found"}), 404
    result_path = os.path.join(RESULTS_DIR, f"{job_id}.json")
    queue_path = os.path.join(QUEUE_DIR, f"{job_id}.json")
    if os.path.exists(result_path):
        with open(result_path, encoding="utf-8") as stream:
            result = json.load(stream)
        return jsonify({"job_id": job_id, "status": "done", "result": result}), 200
    if os.path.exists(queue_path):
        return jsonify({"job_id": job_id, "status": "queued"}), 200
    return jsonify({"error": "job not found"}), 404


# R6
@app.route("/files", methods=["POST"])
def save_file():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("content"), str):
        return jsonify({"error": "content must be a string"}), 400
    body = data["content"].encode("utf-8")
    if len(body) > MAX_FILE_BYTES:
        return jsonify({"error": "file exceeds 1 MiB"}), 400
    file_id = str(uuid.uuid4())
    try:
        ensure_bucket()
        s3.put_object(Bucket=BUCKET, Key=f"files/{file_id}.txt", Body=body,
                      ContentType="text/plain; charset=utf-8")
    except (ClientError, BotoCoreError, OSError):
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"file_id": file_id}), 201


# R7
@app.route("/files/<file_id>", methods=["GET"])
def read_file(file_id):
    try:
        file_id = str(uuid.UUID(file_id))
    except ValueError:
        return jsonify({"error": "file not found"}), 404
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=f"files/{file_id}.txt")
        content = obj["Body"].read().decode("utf-8")
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in ("NoSuchKey", "404", "NotFound"):
            return jsonify({"error": "file not found"}), 404
        return jsonify({"error": "storage unavailable"}), 503
    except (BotoCoreError, OSError, UnicodeError):
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"file_id": file_id, "content": content}), 200


# R8
@app.route("/counter/increment", methods=["POST"])
def increment_counter():
    try:
        value = primary.incr("counter")
    except redis.exceptions.RedisError:
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"value": value, "source": "primary"}), 200


# R9
@app.route("/counter", methods=["GET"])
def read_counter():
    source = request.args.get("from", "primary")
    if source not in ("primary", "replica"):
        return jsonify({"error": "source must be primary or replica"}), 400
    client = replica if source == "replica" else primary
    try:
        value = client.get("counter")
    except redis.exceptions.RedisError:
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"value": int(value or 0), "source": source}), 200


# R5
@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "method not allowed"}), 405


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
