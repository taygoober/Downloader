"""Download management routes."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from app.models.schemas import DownloadRequest, JobResponse, JobStatus
from app.services.job_manager import job_manager

logger = logging.getLogger(__name__)
router = APIRouter()


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.post("/jobs", response_model=JobResponse, status_code=202, tags=["Downloads"])
async def create_download_job(body: DownloadRequest, request: Request) -> JobResponse:
    """
    Submit a URL for download.

    Returns a job object immediately with status **pending**.
    Poll `GET /jobs/{job_id}` to track progress.
    """
    quality = "audio" if body.audio_only else (body.quality or "best")
    job = job_manager.create_job(
        url=body.url,
        quality=quality,
        audio_only=body.audio_only,
        cookies=body.cookies,
    )
    await job_manager.start_job(job)
    return JobResponse(**job.to_dict(_base_url(request)))


@router.get("/jobs", response_model=List[JobResponse], tags=["Downloads"])
async def list_jobs(request: Request) -> List[JobResponse]:
    """List all download jobs."""
    base = _base_url(request)
    return [JobResponse(**j.to_dict(base)) for j in job_manager.list_jobs()]


@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Downloads"])
async def get_job(job_id: str, request: Request) -> JobResponse:
    """Get the status of a specific download job."""
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return JobResponse(**job.to_dict(_base_url(request)))


@router.get("/jobs/{job_id}/file", tags=["Downloads"])
async def download_file(job_id: str) -> FileResponse:
    """
    Download the finished file for a completed job.

    Returns the file with `Content-Disposition: attachment`.
    """
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"Job is not completed yet (status: {job.status})",
        )
    if not job.file_path or not Path(job.file_path).exists():
        raise HTTPException(status_code=404, detail="File not found on server")

    media_type = "audio/mp4" if job.audio_only else "video/mp4"
    return FileResponse(
        path=job.file_path,
        filename=job.filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{job.filename}"'},
    )


@router.delete("/jobs/{job_id}", status_code=204, response_class=Response, response_model=None, tags=["Downloads"])
async def delete_job(job_id: str) -> None:
    """Delete a job and its downloaded file."""
    deleted = job_manager.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
