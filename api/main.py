"""Private migration API. Bind to localhost until per-user auth is implemented."""
import os
import secrets
from urllib.parse import urlparse, parse_qs

import requests
from fastapi import FastAPI, Header, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.youtube_client import get_video_details

app = FastAPI(title="Stratify Evidence API", version="0.1.0")


def require_service_token(authorization: str | None = Header(default=None)):
    expected = os.getenv("STRATIFY_SERVICE_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(503, "Analysis service is not configured.")
    supplied = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not secrets.compare_digest(expected, supplied):
        raise HTTPException(401, "Authentication required.")


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def youtube_only(cls, value):
        import re
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port:
            raise ValueError("Use an HTTPS YouTube video URL.")
        if parsed.hostname in {"youtu.be", "www.youtu.be"}:
            video_id = parsed.path.strip("/")
        elif parsed.hostname in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                video_id = parse_qs(parsed.query).get("v", [""])[0]
            elif parsed.path.startswith(("/shorts/", "/embed/")):
                video_id = parsed.path.split("/")[-1]
            else:
                video_id = ""
        else:
            video_id = ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Enter a supported YouTube video URL.")
        return f"https://www.youtube.com/watch?v={video_id}"


class Metadata(BaseModel):
    video_id: str
    title: str
    channel_title: str
    published_at: str
    views: int = Field(ge=0)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)


class AnalysisResponse(BaseModel):
    status: str = "partial"
    evidence_level: str = "metadata_only"
    source_url: str
    video: Metadata
    limitations: list[str]
    recommendation: str | None = None


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/v1/intro-evidence", dependencies=[Depends(require_service_token)])
async def intro_evidence(file: UploadFile = File(...), owned: bool = Form(False)):
    import tempfile
    from pathlib import Path
    from starlette.concurrency import run_in_threadpool
    from api.local_evidence import analyze_owned_intro
    if os.getenv("STRATIFY_LOCAL_MEDIA_ENABLED") != "1":
        raise HTTPException(503, "Local video analysis is not enabled.")
    if not owned:
        raise HTTPException(422, "Confirm that you own or have permission to analyze this video.")
    try:
        with tempfile.TemporaryDirectory(prefix="stratify-intro-") as directory:
            root = Path(directory)
            path = root / "asset.mp4"
            total = 0
            with path.open("wb") as output:
                while chunk := await file.read(1024 * 1024):
                    total += len(chunk)
                    if total > 20 * 1024 * 1024:
                        raise HTTPException(413, "Upload a video smaller than 20 MB.")
                    output.write(chunk)
            if not total:
                raise HTTPException(422, "Upload a readable video file.")
            try:
                return await run_in_threadpool(analyze_owned_intro, path, root / "frames")
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            except Exception:
                raise HTTPException(500, "Intro analysis could not complete. Try a different clip.") from None
    finally:
        await file.close()


@app.post("/v1/analyses", response_model=AnalysisResponse,
          dependencies=[Depends(require_service_token)])
def analyze(payload: AnalysisRequest):
    try:
        video = get_video_details(payload.url)
    except ValueError:
        raise HTTPException(503, "YouTube integration is not configured.") from None
    except requests.Timeout:
        raise HTTPException(504, "YouTube took too long. Try again.") from None
    except (requests.RequestException, RuntimeError):
        raise HTTPException(502, "YouTube metadata is temporarily unavailable.") from None
    if not video:
        raise HTTPException(404, "Video not found or unavailable.")
    return AnalysisResponse(
        source_url=payload.url,
        video=Metadata(**{key: video[key] for key in Metadata.model_fields}),
        limitations=[
            "Only public metadata was retrieved; intro frames and retention were not observed.",
            "View counts do not establish which intro choices caused performance.",
            "No experiment is recommended until comparable observational evidence is available.",
        ],
    )
