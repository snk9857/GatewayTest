import csv
import io
import time
import random
import argparse
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageFilter


def mutate_image(img: Image.Image, step: int) -> tuple[Image.Image, str]:
    """
    Create a small, realistic mutation to simulate query-based probing.
    Rotates through several transformation types.
    """
    mode = step % 5

    if mode == 0:
        factor = 1.0 + random.uniform(0.02, 0.08)
        out = ImageEnhance.Brightness(img).enhance(factor)
        return out, f"brightness_{factor:.3f}"

    if mode == 1:
        factor = 1.0 + random.uniform(0.02, 0.08)
        out = ImageEnhance.Contrast(img).enhance(factor)
        return out, f"contrast_{factor:.3f}"

    if mode == 2:
        w, h = img.size
        scale = random.uniform(0.90, 0.98)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        small = img.resize((nw, nh), Image.Resampling.LANCZOS)
        out = small.resize((w, h), Image.Resampling.LANCZOS)
        return out, f"resize_{scale:.3f}"

    if mode == 3:
        crop_pct = random.uniform(0.01, 0.05)
        w, h = img.size
        keep_w = int(w * (1.0 - crop_pct))
        keep_h = int(h * (1.0 - crop_pct))
        left = (w - keep_w) // 2
        top = (h - keep_h) // 2
        cropped = img.crop((left, top, left + keep_w, top + keep_h))
        out = cropped.resize((w, h), Image.Resampling.LANCZOS)
        return out, f"crop_{crop_pct:.3f}"

    radius = random.uniform(0.2, 0.8)
    out = img.filter(ImageFilter.GaussianBlur(radius=radius))
    return out, f"blur_{radius:.3f}"


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def classify_status(status_code: int) -> str:
    if status_code in (200, 201, 202):
        return "allowed"
    if status_code == 409:
        return "similarity_block"
    if status_code == 429:
        return "rate_limited"
    if status_code == 403:
        return "ip_blocked"
    if status_code == 401:
        return "auth_error"
    if status_code >= 500:
        return "server_error"
    return "other"


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline red teaming script for raw backend vs defended gateway")
    parser.add_argument("--input", required=True, help="Base image file")
    parser.add_argument("--token", required=True, help="Bearer token")
    parser.add_argument("--url", required=True, help="Target URL, e.g. http://localhost:5000/api/jobs or http://localhost:6767/api/jobs")
    parser.add_argument("--queries", type=int, default=50, help="Number of attack queries to send")
    parser.add_argument("--pause", type=float, default=0.25, help="Seconds between queries")
    parser.add_argument("--csv", default="baseline_redteam_results.csv", help="Output CSV filename")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    base_img = Image.open(input_path).convert("RGB")
    headers = {"Authorization": f"Bearer {args.token}"}

    allowed = 0
    similarity = 0
    rate_limited = 0
    ip_blocked = 0
    auth_error = 0
    other = 0

    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "query_num",
            "mutation",
            "status_code",
            "classification",
            "latency_ms",
            "response_body"
        ])

        for i in range(1, args.queries + 1):
            mutated, mutation_label = mutate_image(base_img, i)
            payload = image_to_png_bytes(mutated)

            start = time.perf_counter()
            try:
                response = requests.post(
                    args.url,
                    headers=headers,
                    files={"file": (f"query_{i:03d}.png", io.BytesIO(payload), "image/png")},
                    timeout=60,
                )
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                body = response.text.strip()
                status = response.status_code
                classification = classify_status(status)
            except requests.RequestException as e:
                latency_ms = -1
                body = str(e)
                status = -1
                classification = "request_error"

            writer.writerow([
                i,
                mutation_label,
                status,
                classification,
                latency_ms,
                body
            ])

            if classification == "allowed":
                allowed += 1
            elif classification == "similarity_block":
                similarity += 1
            elif classification == "rate_limited":
                rate_limited += 1
            elif classification == "ip_blocked":
                ip_blocked += 1
            elif classification == "auth_error":
                auth_error += 1
            else:
                other += 1

            print(
                f"Q{i:03d} | {mutation_label:20} | "
                f"{status:>3} | {classification:16} | {latency_ms:>7} ms"
            )

            # If the client has been IP blocked, continuing is usually pointless
            if classification == "ip_blocked":
                print("\nIP block detected. Stopping early.")
                break

            time.sleep(args.pause)

    print("\n--- SUMMARY ---")
    print(f"Allowed: {allowed}")
    print(f"Similarity Blocks (409): {similarity}")
    print(f"Rate Limited (429): {rate_limited}")
    print(f"IP Blocked (403): {ip_blocked}")
    print(f"Auth Errors (401): {auth_error}")
    print(f"Other / Errors: {other}")
    print(f"\nResults saved to: {args.csv}")


if __name__ == "__main__":
    main()