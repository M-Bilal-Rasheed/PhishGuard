"""One prediction function shared by all three apps (Streamlit, Hugging Face, FastAPI).

Two layers, like real browser filters:
1. Allowlist: the registered domain is a Tranco top-2,000 site that is not a hosting platform
   or shortener and never appears in our phishing feeds  ->  legitimate.
2. Otherwise the ML pipeline gives P(phishing), compared with the threshold in metadata.json.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import joblib

from features import FREE_HOSTING, _extract

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
INVALID = re.compile(r"[\s<>\"{}|\\^`]")
MAX_LENGTH = 2000


class InvalidURL(ValueError):
    pass


def normalize_url(url: str) -> str:
    """Same formatting as training (data/scripts/build_dataset.py), so the model sees familiar input."""
    url = str(url).strip()
    if not url:
        raise InvalidURL("URL is empty")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "http://" + url
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        port = p.port
    except ValueError as e:
        raise InvalidURL(f"could not parse URL: {e}") from None
    if p.scheme.lower() not in ("http", "https"):
        raise InvalidURL("only http and https URLs are supported")
    if not host or "." not in host:
        raise InvalidURL("URL has no valid host name")
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = p.path.rstrip("/") if not p.query else p.path
    url = urlunparse((p.scheme.lower(), netloc, path, p.params, p.query, ""))
    if len(url) > MAX_LENGTH:
        raise InvalidURL(f"URL is longer than {MAX_LENGTH} characters")
    if INVALID.search(url):
        raise InvalidURL("URL contains spaces or characters that are not allowed")
    return url


def load_allowlist(path=MODELS_DIR / "allowlist.txt") -> set:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def allowlisted(url: str, allowlist: set) -> bool:
    host = (urlparse(url).hostname or "").lower()
    domain = _extract(host).top_domain_under_public_suffix
    # On hosting platforms the page owner is the subdomain, not the platform.
    if domain in FREE_HOSTING or any(host == h or host.endswith("." + h) for h in FREE_HOSTING):
        return False
    return domain in allowlist


class PhishGuard:
    def __init__(self, models_dir=MODELS_DIR):
        models_dir = Path(models_dir)
        self.pipeline = joblib.load(models_dir / "phishguard_pipeline.joblib")
        self.meta = json.loads((models_dir / "metadata.json").read_text())
        self.threshold = float(self.meta["threshold"])
        self.allowlist = load_allowlist(models_dir / "allowlist.txt")

    def model_probability(self, url: str) -> float:
        return float(self.pipeline.predict_proba([normalize_url(url)])[0, 1])

    def predict(self, url: str) -> dict:
        """Raises InvalidURL for bad input; otherwise returns the verdict and why."""
        clean = normalize_url(url)
        prob = float(self.pipeline.predict_proba([clean])[0, 1])
        if allowlisted(clean, self.allowlist):
            return {"url": clean, "label": "legitimate", "is_phishing": False, "probability": prob,
                    "threshold": self.threshold,
                    "reason": "trusted domain (top 2,000 site, never seen in phishing feeds)"}
        phishing = prob >= self.threshold
        return {"url": clean, "label": "phishing" if phishing else "legitimate", "is_phishing": phishing,
                "probability": prob, "threshold": self.threshold, "reason": "machine-learning model"}
