"""Lab 5: Lab 3 REST service extended with a replicated MongoDB record store."""
import json
import os
import socket
import uuid
from datetime import datetime

from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.write_concern import WriteConcern

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MAX_MESSAGE_LEN = 1000
os.makedirs(QUEUE_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

app = Flask(__name__)
client = MongoClient(
    os.environ.get("MONGO_URI", "mongodb://localhost:27017/?replicaSet=rs0"),
    serverSelectionTimeoutMS=3000,
    connectTimeoutMS=2000,
    socketTimeoutMS=5000,
    retryWrites=False,  # keep transient failover errors visible to the probe
)
records = client["lab5"].get_collection(
    "records", write_concern=WriteConcern(w="majority", wtimeout=5000)
)


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


@app.route("/echo", methods=["POST"])
def echo():
    message, error = get_message_or_error()
    if error:
        return error
    return jsonify({"reply": message}), 200


@app.route("/time", methods=["GET"])
def get_time():
    return jsonify({
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "served_by": socket.gethostname(),
    }), 200


# Previous lab's file-based jobs routes are preserved for API compatibility.
# They are NOT a shared queue across replicas; use /records for distributed tests.
@app.route("/jobs", methods=["POST"])
def submit_job():
    message, error = get_message_or_error()
    if error:
        return error
    job_id = str(uuid.uuid4())
    temporary = os.path.join(QUEUE_DIR, f"{job_id}.tmp")
    destination = os.path.join(QUEUE_DIR, f"{job_id}.json")
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump({"job_id": job_id, "message": message,
                   "submitted_at": datetime.now().isoformat(timespec="seconds")}, f)
    os.replace(temporary, destination)
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
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)
        return jsonify({"job_id": job_id, "status": "done", "result": result}), 200
    if os.path.exists(queue_path):
        return jsonify({"job_id": job_id, "status": "queued"}), 200
    return jsonify({"error": "job not found"}), 404


@app.route("/records", methods=["POST"])
def create_record():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str) or not data["text"].strip():
        return jsonify({"error": "field 'text' must be a non-empty string"}), 400
    rec = {"_id": str(uuid.uuid4()), "text": data["text"]}
    try:
        records.insert_one(rec)
    except PyMongoError:
        return jsonify({"error": "storage unavailable"}), 503
    return jsonify({"id": rec["_id"], "text": rec["text"],
                    "served_by": socket.gethostname()}), 201


@app.route("/records/<rec_id>", methods=["GET"])
def get_record(rec_id):
    try:
        rec = records.find_one({"_id": rec_id})
    except PyMongoError:
        return jsonify({"error": "storage unavailable"}), 503
    if rec is None:
        return jsonify({"error": "record not found"}), 404
    return jsonify({"id": rec["_id"], "text": rec["text"],
                    "served_by": socket.gethostname()}), 200


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "method not allowed"}), 405


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
