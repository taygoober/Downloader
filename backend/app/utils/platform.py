"""Platform detection helpers."""
from __future__ import annotations

import re
from typing import Optional


_PLATFORM_PATTERNS = [
    (re.compile(r"(youtube\.com|youtu\.be)", re.I), "youtube"),
    (re.compile(r"(instagram\.com)", re.I), "instagram"),
    (re.compile(r"(tiktok\.com|vm\.tiktok\.com)", re.I), "tiktok"),
    (re.compile(r"(twitter\.com|x\.com|t\.co)", re.I), "twitter"),
    (re.compile(r"(reddit\.com|redd\.it)", re.I), "reddit"),
    (re.compile(r"(facebook\.com|fb\.watch)", re.I), "facebook"),
    (re.compile(r"(vimeo\.com)", re.I), "vimeo"),
    (re.compile(r"(twitch\.tv)", re.I), "twitch"),
    (re.compile(r"(dailymotion\.com)", re.I), "dailymotion"),
    (re.compile(r"(pinterest\.com)", re.I), "pinterest"),
    (re.compile(r"(snapchat\.com)", re.I), "snapchat"),
    (re.compile(r"(bilibili\.com)", re.I), "bilibili"),
]


def detect_platform(url: str) -> Optional[str]:
    """Return a lowercase platform name for a given URL, or None if unknown."""
    for pattern, name in _PLATFORM_PATTERNS:
        if pattern.search(url):
            return name
    return None
