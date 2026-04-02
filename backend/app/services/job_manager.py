"""In-memory job manager for download tasks."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models.schemas import JobStatus
from app.services.downloader import download_video

logger = logging.getLogger(__name__)


class Job:
    __slots__ = (
        "job_id",
        "url",
        "quality",
        "audio_only",
        "cookies",
        "status",
        "progress",
        "filename",
        "file_path",
        "file_size",
        "error",
        "platform",
        "created_at",
        "updated_at",
    )

    def __init__(
        self,
        url: str,
        quality: str,
        audio_only: bool,
        cookies: Optional[str],
    ) -> None:
        self.job_id: str = str(uuid.uuid4())
        self.url = url
        self.quality = quality
        self.audio_only = audio_only
        self.cookies = cookies
        self.status: JobStatus = JobStatus.PENDING
        self.progress: float = 0.0
        self.filename: Optional[str] = None
        self.file_path: Optional[str] = None
        self.file_size: Optional[int] = None
        self.error: Optional[str] = None
        self.platform: Optional[str] = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = self.created_at

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self, base_url: str = "") -> dict:
        download_url: Optional[str] = None
        if self.status == JobStatus.COMPLETED and self.filename:
            download_url = f"{base_url}/jobs/{self.job_id}/file"
        return {
            "job_id": self.job_id,
            "status": self.status,
            "url": self.url,
            "quality": self.quality,
            "audio_only": self.audio_only,
            "progress": round(self.progress, 1),
            "filename": self.filename,
            "file_size": self.file_size,
            "error": self.error,
            "platform": self.platform,
            "download_url": download_url,
        }


class JobManager:
    """Stores jobs in memory and runs downloads asynchronously."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}

    def create_job(
        self,
        url: str,
        quality: str,
        audio_only: bool,
        cookies: Optional[str],
    ) -> Job:
        job = Job(url=url, quality=quality, audio_only=audio_only, cookies=cookies)
        self._jobs[job.job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        return list(self._jobs.values())

    def delete_job(self, job_id: str) -> bool:
        job = self._jobs.pop(job_id, None)
        if job is None:
            return False
        # Remove downloaded files
        if job.file_path:
            import shutil
            from pathlib import Path

            job_dir = Path(job.file_path).parent
            try:
                shutil.rmtree(job_dir, ignore_errors=True)
            except Exception:
                pass
        return True

    async def start_job(self, job: Job) -> None:
        """Launch the download as a background asyncio task."""
        asyncio.create_task(self._run(job))

    async def _run(self, job: Job) -> None:
        job.status = JobStatus.DOWNLOADING
        job._touch()

        def _on_progress(pct: float) -> None:
            job.progress = pct
            job._touch()

        try:
            result = await download_video(
                job_id=job.job_id,
                url=job.url,
                quality=job.quality,
                audio_only=job.audio_only,
                cookies=job.cookies,
                on_progress=_on_progress,
            )
            job.filename = result["filename"]
            job.file_path = result["file_path"]
            job.file_size = result["file_size"]
            job.platform = result["platform"]
            job.progress = 100.0
            job.status = JobStatus.COMPLETED
        except Exception as exc:
            job.error = str(exc)
            job.status = JobStatus.FAILED
            logger.error("Job %s failed: %s", job.job_id, exc)
        finally:
            job._touch()


# Module-level singleton — shared across the application lifetime
job_manager = JobManager()
