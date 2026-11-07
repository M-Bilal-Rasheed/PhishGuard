"""Shared paths and HTTP settings for the data collection scripts."""
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)

USER_AGENT = "PhishGuard-student-research/1.0 (CT-378 ML course project)"


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
