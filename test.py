import os
import random
import time
import argparse
import requests

# ----------------------------
# Config
# ----------------------------
API_URL = "http://localhost:6767/api/jobs"
FILE_FIELD_NAME = "file"
DELAY_SECONDS = 1

# Supported image extensions
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def get_image_files(directory):
    return [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(IMAGE_EXTENSIONS)
    ]


def upload_file(filepath: str, token: str) -> None:
    headers = {
        "Authorization": f"Bearer {token}"
    }

    filename = os.path.basename(filepath)

    with open(filepath, "rb") as f:
        files = {
            FILE_FIELD_NAME: (filename, f, "image/png")
        }

        try:
            response = requests.post(API_URL, headers=headers, files=files, timeout=120)

            print(f"\n--- Upload: {filename} ---")
            print(f"Status: {response.status_code}")

            try:
                print("Response JSON:")
                print(response.json())
            except Exception:
                print("Response Text:")
                print(response.text)

        except requests.RequestException as e:
            print(f"\n--- Upload: {filename} ---")
            print(f"Request failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Random image uploader test.")
    parser.add_argument("--token", required=True, help="Bearer token for API auth")
    parser.add_argument(
        "--dir",
        default=".",
        help="Directory to pull images from (default: current directory)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=12,
        help="Number of random images to upload (default: 12)"
    )

    args = parser.parse_args()
    token = args.token
    image_dir = args.dir
    count = args.count

    if not os.path.exists(image_dir):
        print(f"Directory does not exist: {image_dir}")
        return

    image_files = get_image_files(image_dir)

    if len(image_files) < count:
        print(f"Not enough images in {image_dir}. Found {len(image_files)}, need {count}.")
        return

    selected_files = random.sample(image_files, count)

    print("Randomized upload set:")
    for f in selected_files:
        print(f"  - {os.path.basename(f)}")

    for filepath in selected_files:
        upload_file(filepath, token)
        time.sleep(DELAY_SECONDS)


if __name__ == "__main__":
    main()