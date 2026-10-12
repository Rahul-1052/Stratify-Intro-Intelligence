"""Run from the repository root after npm ci. Uses only a generated owned clip."""
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import requests


def main():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, STRATIFY_SERVICE_TOKEN=secrets.token_urlsafe(32),
               STRATIFY_LOCAL_MEDIA_ENABLED="1", STRATIFY_API_URL="http://127.0.0.1:8005",
               STRATIFY_WEB_ORIGIN="http://127.0.0.1:3005", NEXT_TELEMETRY_DISABLED="1")
    with tempfile.TemporaryFile() as logs:
        api = subprocess.Popen(["python", "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8005"], cwd=root, env=env, stdout=logs, stderr=logs)
        web = subprocess.Popen(["node", "node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1", "--port", "3005"], cwd=root / "web", env=env, stdout=logs, stderr=logs)
        try:
            for _ in range(100):
                try:
                    if requests.get("http://127.0.0.1:8005/healthz", timeout=1).ok and requests.get("http://127.0.0.1:3005", timeout=2).ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(0.2)
            else:
                raise RuntimeError("Development services did not start")
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "owned.mp4"
                writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
                assert writer.isOpened()
                for index in range(30):
                    writer.write(np.full((120, 160, 3), 25 if index < 10 else 220, dtype=np.uint8))
                writer.release()
                with path.open("rb") as file:
                    response = requests.post("http://127.0.0.1:3005/api/intro-evidence", headers={"Origin": env["STRATIFY_WEB_ORIGIN"]}, files={"file": ("owned.mp4", file, "video/mp4")}, data={"owned": "true"}, timeout=60)
                assert response.status_code == 200, response.text
                report = response.json()
                assert report["sample_count"] == 6 and report["recommendation"] is None
                print("Next.js → FastAPI → recovered observer: PASS, 6 frames from real MP4")
            response = requests.post("http://127.0.0.1:3005/api/intro-evidence", headers={"Origin": "https://untrusted.example"}, timeout=10)
            assert response.status_code == 403
            print("Cross-origin upload rejection: PASS")
        finally:
            api.terminate()
            web.terminate()
            api.wait(timeout=10)
            web.wait(timeout=10)


if __name__ == "__main__":
    main()
