"""Private migration API. Bind to localhost until per-user auth is implemented."""
import os
import secrets
from urllib.parse import urlparse, parse_qs

import requests
from fastapi import FastAPI, Header, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.youtube_client import get_video_details
from api.creator_memory import dashboard as memory_dashboard
from api.creator_memory import reopen_analysis as memory_reopen_analysis
from api.creator_memory import save_profile as memory_save_profile
from api.creator_memory import save_uploaded_analysis as memory_save_uploaded_analysis
from api.creator_memory import update_experiment as memory_update_experiment

app = FastAPI(title="Stratify Evidence API", version="0.2.0")


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


class MemoryProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str = Field(min_length=1, max_length=120)
    channel_name: str = Field(min_length=1, max_length=160)
    niche: str | None = Field(default=None, max_length=120)


class MemorySaveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    report: dict
    upload_name: str = Field(min_length=1, max_length=255)
    content_digest: str = Field(pattern=r"^[a-f0-9]{64}$")


class ExperimentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str | None = Field(default=None, pattern=r"^(suggested|planned|running|completed|rejected|archived)$")
    creator_notes: str | None = Field(default=None, max_length=2000)
    result_summary: str | None = Field(default=None, max_length=2000)


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
                result = await run_in_threadpool(analyze_owned_intro, path, root / "frames")
                result["upload_name"] = file.filename or "owned-video.mp4"
                return result
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            except Exception:
                raise HTTPException(500, "Intro analysis could not complete. Try a different clip.") from None
    finally:
        await file.close()


@app.get("/v1/memory", dependencies=[Depends(require_service_token)])
def creator_memory_dashboard():
    return memory_dashboard()


@app.post("/v1/memory/profile", dependencies=[Depends(require_service_token)])
def creator_memory_profile(payload: MemoryProfileRequest):
    try:
        return memory_save_profile(payload.display_name, payload.channel_name, payload.niche)
    except (ValueError, OSError):
        raise HTTPException(422, "Creator Memory profile could not be saved.") from None


@app.post("/v1/memory/analyses", dependencies=[Depends(require_service_token)])
def creator_memory_save(payload: MemorySaveRequest):
    creator = payload.report.get("creator_report") if isinstance(payload.report, dict) else None
    if not isinstance(creator, dict):
        raise HTTPException(422, "A completed Creator Report is required.")
    try:
        return memory_save_uploaded_analysis(
            payload.report, payload.upload_name, payload.content_digest
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    except (OSError, TypeError):
        raise HTTPException(422, "This analysis could not be saved to Creator Memory.") from None


@app.get("/v1/memory/analyses/{analysis_id}", dependencies=[Depends(require_service_token)])
def creator_memory_reopen(analysis_id: str):
    result = memory_reopen_analysis(analysis_id)
    if result.get("status") == "fallback" and result.get("diagnostics", {}).get("error") == "missing_analysis":
        raise HTTPException(404, "Saved analysis not found.")
    return result


@app.patch("/v1/memory/experiments/{experiment_id}", dependencies=[Depends(require_service_token)])
def creator_memory_experiment(experiment_id: str, payload: ExperimentUpdateRequest):
    if payload.status is None and payload.creator_notes is None and payload.result_summary is None:
        raise HTTPException(422, "Provide an experiment update.")
    try:
        return memory_update_experiment(
            experiment_id, status=payload.status, creator_notes=payload.creator_notes,
            result_summary=payload.result_summary,
        )
    except (ValueError, OSError):
        raise HTTPException(422, "Experiment could not be updated.") from None


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

class ChannelWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: str = Field(min_length=1, max_length=2048)
    concern: str = Field(min_length=1, max_length=2000)

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, value):
        from core.channel_workspace import channel_selector
        channel_selector(value)
        return value.strip()

    @field_validator("concern")
    @classmethod
    def valid_concern(cls, value):
        if not value.strip():
            raise ValueError("Tell us what you would like help understanding.")
        return value.strip()


@app.post("/v1/channel-workspace", dependencies=[Depends(require_service_token)])
def channel_workspace(payload: ChannelWorkspaceRequest):
    from core.channel_workspace import collect_channel_workspace
    try:
        result = collect_channel_workspace(payload.channel, payload.concern)
    except ValueError:
        raise HTTPException(503, "YouTube integration is not configured.") from None
    except requests.Timeout:
        raise HTTPException(504, "YouTube took too long. Try again.") from None
    except (requests.RequestException, RuntimeError):
        raise HTTPException(502, "Channel facts are temporarily unavailable.") from None
    if result is None:
        raise HTTPException(404, "Channel not found or unavailable.")
    return result
