"""Build the trusted-domain allowlist used by the apps (not by the model).

Trusted = in the Tranco top 2,000, AND not a free-hosting platform or URL shortener,
AND never seen in any of our collected phishing feeds (196k URLs). Big platforms where
users can publish pages (Google Forms, AWS, Azure, Jotform...) appear in the feeds and
are therefore excluded, so the allowlist can't wave through a scam hosted on them.

Usage: python data/scripts/build_allowlist.py  ->  models/allowlist.txt
"""
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from common import RAW, ROOT, session  # noqa: E402
from fetch_legit import load_tranco, registered_domain  # noqa: E402
from features import FREE_HOSTING, SHORTENERS  # noqa: E402

TOP_N = 2_000
OUT = ROOT / "models" / "allowlist.txt"
PHISH_FILES = ("phishtank.csv", "phiusiil_phish.csv", "openphish.csv")


def url_domain(url: str):
    url = str(url).strip()
    try:
        host = urlparse(url if "://" in url else "http://" + url).hostname or ""
    except ValueError:
        return None
    return registered_domain(host.lower()) or None


def phishing_domains(frame: pd.DataFrame) -> set:
    return set(frame["url"].map(url_domain).dropna())


def load_raw_phishing() -> pd.DataFrame:
    return pd.concat([pd.read_csv(RAW / f) for f in PHISH_FILES], ignore_index=True)


def main():
    list_id, tranco = load_tranco(session())
    top = set(tranco.loc[tranco["rank"] <= TOP_N, "domain"].map(registered_domain).dropna())
    raw = load_raw_phishing()
    abused = phishing_domains(raw)
    hosting = {d for d in top if d in FREE_HOSTING or d in SHORTENERS}
    domains = sorted(top - hosting - abused)
    # Candidates are kept so the notebook can rebuild a "past" allowlist for the time-based check.
    pd.DataFrame({"domain": sorted(top - hosting)}).to_csv(ROOT / "data" / "processed" / "allowlist_candidates.csv", index=False)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# PhishGuard allowlist: Tranco list {list_id}, top {TOP_N:,}, minus free hosting/shorteners "
              f"and minus domains seen in {len(raw):,} collected phishing URLs\n")
    OUT.write_text(header + "\n".join(domains) + "\n", encoding="utf-8")
    print(f"Tranco list {list_id}: top {TOP_N:,} -> {len(top):,} registered domains")
    print(f"removed {len(hosting)} hosting/shorteners, {len(top & abused)} seen in phishing feeds")
    print(f"allowlist: {len(domains):,} domains")


if __name__ == "__main__":
    main()
