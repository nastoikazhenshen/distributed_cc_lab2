# Service Specification - Lab 2

Author: Ivaikina Darya (Ивайкина Дарья)      Version: 1

## 1. Purpose

This is a small web service for the Distributed and Cloud Computing course. It can repeat a message back to the user, tell the current server time, and accept text jobs that are too slow to handle inside a request. Such jobs are placed in a queue and handled later by a separate worker program.

## 2. Endpoints

| No | Method | Path | Input (JSON) | Output (JSON) | Response codes |
|----|--------|------|--------------|---------------|----------------|
| R1 | POST | /echo | `{"message": "string"}` (not empty, at most 1000 characters) | `{"reply": "string"}` | 200 on success; 400 if the body is not a JSON object, or `message` is missing, is not a string, is empty, or is longer than 1000 characters |
| R2 | GET | /time | none | `{"server_time": "YYYY-MM-DDTHH:MM:SS"}` | 200 |
| R3 | POST | /jobs | `{"message": "string"}` (same rules as in R1) | `{"job_id": "<uuid>", "status": "queued"}` | 202 (accepted, the work is not done yet); 400 for invalid input |
| R4 | GET | /jobs/{job_id} | none (`job_id` is part of the path) | if waiting: `{"job_id", "status": "queued"}`; if finished: `{"job_id", "status": "done", "result": {"original", "uppercase", "processed_at"}}` | 200; 404 if `job_id` is not a valid UUID or the job does not exist |
| R5 | any | any other path or a wrong method | any | `{"error": "..."}` (always JSON, never an HTML page) | 404 for an unknown path; 405 for a wrong method |

Edge cases:
- If the body is valid JSON but not an object (for example `5` or `[]`), the service answers 400 and does not crash.
- While the worker is still processing a job, its status stays `queued`. It changes to `done` only when the result file exists.
- A correct UUID that was never submitted gives 404.

## 3. Queue message format

Every job is stored as one file `queue/<job_id>.json`:

| Field | Type | Meaning |
|-------|------|---------|
| job_id | string (UUID v4) | the job identifier; it is also the file name |
| message | string | the text that must be processed |
| submitted_at | string (ISO 8601) | the time when the API accepted the job |

When a job is finished, the worker writes `results/<job_id>.json` with the fields `original` (string), `uppercase` (string) and `processed_at` (string, ISO 8601).

Malformed messages: if a file in `queue/` is not valid JSON, has no `message` string, or its name is not a UUID, the worker moves it to the `failed/` folder and goes on with the next job. A bad file therefore never blocks the queue and never stops the worker.

## 4. Constraints

- Protocol and data format: HTTP/1.1; requests and responses use JSON (`Content-Type: application/json`).
- Address: `127.0.0.1`, port 5000.
- Python 3.9 or newer and Flask; all packages are listed in `requirements.txt`.
- Queue service: **variant C-2, a file-based queue**. Waiting jobs are in `queue/`, finished results in `results/`, broken jobs in `failed/`. AWS is not used, so there are no keys or other secrets.
- A new file is first written under a temporary name and then renamed with `os.replace`. This way the worker can never read a half-written job. Result files are written in the same way.
- The worker deletes the job file only after the result has been saved.
- How to run: start `python app.py` in one terminal and `python worker.py` in another, both from the project folder.

## 5. Non-functional requirements (with numbers)

- N1: `/echo` and `/time` respond in less than 150 ms (95th percentile) when 10 clients send requests at the same time. How to check: a Python script sends 100 requests from 10 threads and measures the time of each response.
- N2: `POST /jobs` returns 202 in less than 50 ms, even when the worker is busy (a job takes at least 2 seconds). How to check: measure the response time of one request while the worker is processing another job.
- N3: if the queue is empty and the worker is running, a new job gets the status `done` within 4 seconds after submission (2 seconds of work plus up to 1 second of waiting for the next check). How to check: submit a job, ask `/jobs/{id}` every 0.5 seconds and write down when `done` appears.
- N4 (security): a `job_id` from the client is always checked as a UUID before it is used in a file path; the service listens only on `127.0.0.1`; a message cannot be longer than 1000 characters; no passwords or keys are stored in the code.

## 6. Assumptions

- A1: Only one worker is running at any moment. Risk: if two workers start, both may take the same job and process it twice. Nothing is lost in this case, because the second worker writes the same result again.
- A2: The API and the worker run on the same computer and use the same disk. Risk: if they are moved to different machines (for example to the cloud), they stop sharing the folder and the queue no longer works. A network queue such as Amazon SQS would then be needed.
- A3: The disk can be written to and has free space. Risk: if it does not, writing a job fails and the API answers with an error, so a job is never accepted and then silently lost.
- A4: The users are trusted people working on the same computer, so no login is required. Risk: anybody who can reach the port could send jobs. That is why the service listens only on 127.0.0.1.
- A5: The worker may be switched off for a while. Result: the jobs wait in `queue/` with the status `queued` and are processed when the worker starts again.
- A6: The worker may crash in the middle of a job. Result: the job file is still in `queue/`, so the job is processed again after the restart (it may run twice, but it is not lost).