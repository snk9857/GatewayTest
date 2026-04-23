import os
import time
import csv
import random
from locust import HttpUser, task, between, events

# ---- CONFIG ----
HOST = "http://localhost:6767"
API_PATH = "/api/jobs"

AUTH_TOKEN = None  # set via CLI

# ---- CLI ARG ----
@events.init.add_listener
def init_parser(environment, **kwargs):
    environment.parsed_options.add_argument(
        "--token",
        type=str,
        required=True,
        help="Authorization token"
    )

@events.test_start.add_listener
def load_token(environment, **kwargs):
    global AUTH_TOKEN
    AUTH_TOKEN = environment.parsed_options.token
    print(f"[INFO] Using token: {AUTH_TOKEN[:10]}...")

# ---- FILE SELECTION (.png ONLY) ----
ALL_FILES = [
    f for f in os.listdir(".")
    if os.path.isfile(f) and f.lower().endswith(".png")
]

if len(ALL_FILES) < 10:
    raise Exception("Need at least 10 PNG files in the current directory")

TEST_FILES = random.sample(ALL_FILES, 10)

print("Using test files:")
for f in TEST_FILES:
    print(f" - {f}")

# ---- CSV LOGGING ----
CSV_FILE = "detailed_results.csv"

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp",
            "file",
            "status_code",
            "latency_ms",
            "response_size"
        ])

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, **kwargs):
    file_used = context.get("file", "unknown") if context else "unknown"

    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            time.time(),
            file_used,
            response.status_code if response else "N/A",
            round(response_time, 2),
            response_length
        ])

# ---- USER BEHAVIOR ----
class UploadUser(HttpUser):
    host = HOST
    wait_time = between(0.02, 0.05)

    @task
    def upload_job(self):
        file_path = random.choice(TEST_FILES)

        headers = {
            "Authorization": f"Bearer {AUTH_TOKEN}"
        }

        with open(file_path, "rb") as f:
            files = {
                "file": (os.path.basename(file_path), f, "image/png")
            }

            response = self.client.post(
                API_PATH,
                headers=headers,
                files=files,
                name="POST /api/jobs",
                context={"file": file_path}
            )

            # Rate limiting detection
            if response.status_code == 429:
                response.failure("Rate limited (429)")

            elif response.status_code >= 500:
                response.failure(f"Server error {response.status_code}")