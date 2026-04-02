# Downloader

Self-hosted video downloader backend — designed to work with an iOS Shortcut.

Downloads videos from YouTube, Instagram, TikTok, and 1000+ other sites via **yt-dlp**.

## Quick Start

```bash
# Requires Docker & Docker Compose
docker compose up -d

# Server is available at http://localhost:8000
# API docs:  http://localhost:8000/docs
```

## Features

- **Wide platform support** — YouTube, Instagram, TikTok, Twitter/X, Reddit, Facebook, Vimeo, Twitch, and 1000+ more sites via yt-dlp
- **Quality selection** — best, 1080p, 720p, 480p, 360p, worst, or audio-only
- **Async job queue** — submit a URL and poll for progress; no blocking
- **Anti-detection** — user-agent rotation, per-request jitter, platform-specific sleep intervals
- **Cookie support** — pass base64-encoded Netscape cookies for private/age-gated content
- **REST API** — JSON in/out; compatible with iOS Shortcuts, curl, and any HTTP client
- **Rate limiting** — 60 requests/minute per IP (server-side, via slowapi)

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/jobs` | Submit a URL for download |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Get job status / progress |
| `GET` | `/jobs/{id}/file` | Download the finished file |
| `DELETE` | `/jobs/{id}` | Delete a job and its file |

## iOS Shortcut

See [`docs/API.md`](docs/API.md) for the complete technical documentation including a step-by-step iOS Shortcut integration guide.

## Development

```bash
cd backend
pip install -r requirements.txt
# ffmpeg must be installed: brew install ffmpeg  /  apt install ffmpeg
DOWNLOADS_DIR=/tmp/downloads uvicorn app.main:app --reload
```

## Tests

```bash
python -m pytest tests/ -v
```

## Configuration

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | Listening port |
| `DOWNLOADS_DIR` | `/app/downloads` | Download storage path |
| `ALLOWED_ORIGINS` | `*` | CORS origins |
