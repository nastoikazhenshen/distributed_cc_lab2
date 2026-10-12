import json
import os
import uuid
from datetime import datetime

from flask import Flask, request, jsonify

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_DIR = os.path.join(BASE_DIR, "queue")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
MAX_MESSAGE_LEN = 1000

os.makedirs(QUEUE_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

app = Flask(__name__)


def get_message_or_error():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "message" not in data:
        return None, (jsonify({"error": "field 'message' is required"}), 400)
    message = data["message"]
    if not isinstance(message, str) or message.strip() == "":
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


# R2
@app.route("/time", methods=["GET"])
def get_time():
    return jsonify({"server_time": datetime.now().isoformat(timespec="seconds")}), 200


# R3
@app.route("/jobs", methods=["POST"])
def submit_job():
    message, error = get_message_or_error()
    if error:
        return error

    job_id = str(uuid.uuid4())
    tmp_path = os.path.join(QUEUE_DIR, f"{job_id}.tmp")
    final_path = os.path.join(QUEUE_DIR, f"{job_id}.json")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({"job_id": job_id, "message": message,
                   "submitted_at": datetime.now().isoformat(timespec="seconds")}, f)
    os.replace(tmp_path, final_path)  # atomic: the worker never sees a half-written file

    return jsonify({"job_id": job_id, "status": "queued"}), 202


# R4
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


# R5: errors are always JSON, never HTML
@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "not found"}), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"error": "method not allowed"}), 405


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
