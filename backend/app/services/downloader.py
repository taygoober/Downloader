"""yt-dlp based downloader service with anti-detection measures."""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import random
import re
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from app.utils.platform import detect_platform

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = Path(os.environ.get("DOWNLOADS_DIR", "/app/downloads"))

# Quality map: human-friendly label -> yt-dlp format selector
# Note: [ext=mp4] is intentionally omitted from bestvideo selectors because
# YouTube serves 1080p+ streams primarily as WebM/VP9, not MP4.  ffmpeg
# (installed in the container) merges the separate video+audio streams and
# merge_output_format="mp4" ensures the final file is always an MP4.
_QUALITY_MAP = {
    "best": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "worst": "worstvideo+worstaudio/worst",
    "audio": "bestaudio/best",
}

# Per-platform tweaks
_PLATFORM_OPTIONS: dict[str, dict] = {
    "youtube": {
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        "sleep_interval_requests": 1,
        # android_vr provides full 1080p/4K format lists without requiring a
        # JS runtime (unlike the "web" client).  "android" is kept as a
        # secondary fallback for non-VR capable regions.
        "extractor_args": {"youtube": {"player_client": ["android_vr", "android"]}},
    },
    "instagram": {
        "sleep_interval": 3,
        "max_sleep_interval": 8,
    },
    "tiktok": {
        "sleep_interval": 2,
        "max_sleep_interval": 6,
    },
}


def _jitter(base: float = 1.0, spread: float = 2.0) -> None:
    """Sleep for base + random(0, spread) seconds to mimic human timing."""
    time.sleep(base + random.uniform(0, spread))


def _build_ydl_opts(
    job_id: str,
    quality: str,
    audio_only: bool,
    platform: Optional[str],
    cookies_content: Optional[str],
    progress_hook: Callable,
) -> dict:
    """Build a yt-dlp options dictionary."""
    output_dir = DOWNLOADS_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    fmt = "bestaudio[ext=m4a]/bestaudio" if audio_only else _QUALITY_MAP.get(quality, _QUALITY_MAP["best"])

    opts: dict = {
        "format": fmt,
        "outtmpl": str(output_dir / "%(title)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
        "retries": 5,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "extractor_retries": 3,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "merge_output_format": "mp4",
        "writethumbnail": False,
        "writeinfojson": False,
        "noplaylist": True,
    }

    # Add postprocessors for audio-only mode
    if audio_only:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "192",
            }
        ]

    # Platform-specific overrides
    if platform and platform in _PLATFORM_OPTIONS:
        opts.update(_PLATFORM_OPTIONS[platform])

    # Cookies: decode base64 content and write to a temp file
    if cookies_content:
        try:
            decoded = base64.b64decode(cookies_content).decode("utf-8")
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, prefix="cookies_"
            )
            tmp.write(decoded)
            tmp.close()
            opts["cookiefile"] = tmp.name
        except Exception as exc:
            logger.warning("Failed to decode cookies: %s", exc)

    return opts


async def download_video(
    job_id: str,
    url: str,
    quality: str = "best",
    audio_only: bool = False,
    cookies: Optional[str] = None,
    on_progress: Optional[Callable[[float], None]] = None,
) -> dict:
    """
    Download a video using yt-dlp.

    Returns a dict with keys: filename, file_path, file_size, platform.
    Raises on failure.
    """
    platform = detect_platform(url)
    logger.info("Starting download job=%s platform=%s url=%s", job_id, platform, url)

    # Small random jitter before we start (reduces bot-like pattern)
    await asyncio.sleep(random.uniform(0.5, 2.0))

    progress_data: dict = {"value": 0.0}

    def _progress_hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            if total:
                pct = min(downloaded / total * 100, 99.0)
                progress_data["value"] = pct
                if on_progress:
                    on_progress(pct)
        elif d.get("status") == "finished":
            progress_data["value"] = 99.0
            if on_progress:
                on_progress(99.0)

    opts = _build_ydl_opts(
        job_id=job_id,
        quality=quality,
        audio_only=audio_only,
        platform=platform,
        cookies_content=cookies,
        progress_hook=_progress_hook,
    )

    loop = asyncio.get_event_loop()

    def _run_download() -> dict:
        cookie_file: Optional[str] = opts.get("cookiefile")
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise RuntimeError("yt-dlp returned no info for URL")

                # Resolve the actual output file
                output_dir = DOWNLOADS_DIR / job_id
                files = list(output_dir.iterdir()) if output_dir.exists() else []
                if not files:
                    raise RuntimeError("Download completed but no file found")

                # Pick the largest file (avoids stray .part or thumbnail files)
                output_file = max(files, key=lambda f: f.stat().st_size)
                return {
                    "filename": output_file.name,
                    "file_path": str(output_file),
                    "file_size": output_file.stat().st_size,
                    "platform": platform,
                }
        finally:
            # Clean up temp cookie file
            if cookie_file and os.path.exists(cookie_file):
                try:
                    os.unlink(cookie_file)
                except OSError:
                    pass

    try:
        result = await loop.run_in_executor(None, _run_download)
        logger.info(
            "Download complete job=%s file=%s size=%d",
            job_id,
            result["filename"],
            result["file_size"],
        )
        return result
    except Exception as exc:
        logger.error("Download failed job=%s error=%s", job_id, exc)
        raise
