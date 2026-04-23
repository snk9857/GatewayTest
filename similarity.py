import csv
import time
import argparse
from pathlib import Path
from typing import Optional

import requests

# ---- HARDCODED CONFIG ----
API_URL = "http://localhost:6767/api/jobs"
CSV_FILE = "similarity_tradeoff_results.csv"


def collect_pngs(folder: Path):
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".png"])


def parse_brightness_from_name(filename: str) -> Optional[float]:
    if "brightness_" not in filename:
        return None
    try:
        return float(filename.split("brightness_")[1].replace(".png", ""))
    except:
        return None


def classify_result(status_code: int, body: str) -> str:
    body_lower = body.lower()

    if status_code in (200, 201, 202):
        return "allowed"

    if status_code == 409:
        return "similarity_block"

    if status_code == 429:
        return "rate_limited"

    if status_code == 403:
        return "ip_blocked"

    if "similar" in body_lower:
        return "similarity_block"

    return "other_error"


def upload_file(file_path: Path, token: str):
    headers = {"Authorization": f"Bearer {token}"}

    start = time.perf_counter()
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "image/png")}
        response = requests.post(API_URL, headers=headers, files=files, timeout=60)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    return response.status_code, latency_ms, response.text.strip()


def main():
    parser = argparse.ArgumentParser(description="Similarity trade-off test")
    parser.add_argument("--dir", required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--pause", type=float, default=5)
    args = parser.parse_args()

    folder = Path(args.dir)
    files = collect_pngs(folder)

    print(f"Testing {len(files)} files...\n")

    allowed = 0
    similarity = 0
    rate_limited = 0
    ip_blocked = 0
    other = 0

    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "filename",
            "brightness",
            "status_code",
            "latency_ms",
            "classification",
            "response"
        ])

        for file_path in files:
            brightness = parse_brightness_from_name(file_path.name)

            try:
                status, latency, body = upload_file(file_path, args.token)
                result = classify_result(status, body)
            except Exception as e:
                status = -1
                latency = -1
                body = str(e)
                result = "request_error"

            writer.writerow([file_path.name, brightness, status, latency, result, body])

            if result == "allowed":
                allowed += 1
            elif result == "similarity_block":
                similarity += 1
            elif result == "rate_limited":
                rate_limited += 1
            elif result == "ip_blocked":
                ip_blocked += 1
            else:
                other += 1

            print(
                f"{file_path.name:35} | "
                f"{brightness if brightness is not None else 'N/A':>6} | "
                f"{status:>3} | {latency:>6} ms | {result}"
            )

            time.sleep(args.pause)

    print("\n--- SUMMARY ---")
    print(f"Allowed: {allowed}")
    print(f"Similarity Blocks (409): {similarity}")
    print(f"Rate Limited (429): {rate_limited}")
    print(f"IP Blocked (403): {ip_blocked}")
    print(f"Other Errors: {other}")
    print(f"\nSaved to: {CSV_FILE}")


if __name__ == "__main__":
    main()