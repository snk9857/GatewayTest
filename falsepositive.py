import os
import csv
import time
import argparse
from pathlib import Path

import requests

# ---- HARDCODED CONFIG ----
API_URL = "http://localhost:6767/api/jobs"
CSV_FILE = "false_positive_results.csv"

# ---- HELPERS ----
def collect_pngs(folder):
    return [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".png"]

def classify(status_code, body):
    body_lower = body.lower()

    if status_code in (200, 201, 202):
        return "allowed"

    if status_code == 429:
        return "rate_limited"

    if "similar" in body_lower or "duplicate" in body_lower:
        return "possible_similarity_block"

    return "other_error"

def upload(file_path, token):
    headers = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/png")}
        response = requests.post(API_URL, headers=headers, files=files)
    latency = round((time.perf_counter() - start) * 1000, 2)

    return response.status_code, latency, response.text.strip()

# ---- MAIN ----
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Folder with PNG files")
    parser.add_argument("--token", required=True, help="Bearer token")
    args = parser.parse_args()

    folder = Path(args.dir)
    files = collect_pngs(folder)

    if len(files) == 0:
        print("No PNG files found")
        return

    print(f"Testing {len(files)} files...\n")

    allowed = 0
    rate_limited = 0
    similarity = 0
    errors = 0

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "file",
            "status_code",
            "latency_ms",
            "classification",
            "response"
        ])

        for file_path in files:
            try:
                status, latency, body = upload(file_path, args.token)
                result = classify(status, body)
            except Exception as e:
                status = -1
                latency = -1
                body = str(e)
                result = "request_error"

            writer.writerow([file_path.name, status, latency, result, body])

            if result == "allowed":
                allowed += 1
            elif result == "rate_limited":
                rate_limited += 1
            elif result == "possible_similarity_block":
                similarity += 1
            else:
                errors += 1

            print(f"{file_path.name:20} | {status:>3} | {latency:>6} ms | {result}")

    print("\n--- SUMMARY ---")
    print(f"Allowed: {allowed}")
    print(f"Rate Limited: {rate_limited}")
    print(f"Similarity Blocks: {similarity}")
    print(f"Other Errors: {errors}")
    print(f"\nResults saved to: {CSV_FILE}")

    if similarity == 0 and rate_limited == 0 and errors == 0:
        print("\n✅ No false positives detected")
    else:
        print("\n⚠️ Review results for potential issues")

if __name__ == "__main__":
    main()