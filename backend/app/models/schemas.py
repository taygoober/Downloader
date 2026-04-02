"""Pydantic schemas for request/response models."""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl, field_validator


class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadRequest(BaseModel):
    url: str
    quality: Optional[str] = "best"
    audio_only: bool = False
    cookies: Optional[str] = None  # Netscape cookie file contents (base64 encoded)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("quality")
    @classmethod
    def validate_quality(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"best", "worst", "1080p", "720p", "480p", "360p", "audio"}
        if v and v not in allowed:
            raise ValueError(f"quality must be one of {allowed}")
        return v


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    url: str
    quality: str
    audio_only: bool
    progress: Optional[float] = None  # 0.0 – 100.0
    filename: Optional[str] = None
    file_size: Optional[int] = None  # bytes
    error: Optional[str] = None
    download_url: Optional[str] = None  # URL to fetch the finished file
    platform: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    yt_dlp_version: str
