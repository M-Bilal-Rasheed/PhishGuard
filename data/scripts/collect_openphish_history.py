"""Rebuild past OpenPhish feeds from the feed's GitHub history.

The public feed is a git repository, and each commit is one feed snapshot.
Walking the commits gives every URL with the date it first appeared, so we
get months of dated phishing URLs without waiting to collect them live.
Usage: python data/scripts/collect_openphish_history.py [--since 2026-08-01]
"""
import argparse
import subprocess

import pandas as pd

from common import RAW, now_iso

REPO_URL = "https://github.com/openphish/public_feed.git"
REPO_DIR = RAW / "openphish_repo"
OUT = RAW / "openphish.csv"


def git(*args):
    return subprocess.run(["git", "-C", str(REPO_DIR), *args], check=True,
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-08-01")
    args = ap.parse_args()

    if not REPO_DIR.exists():
        subprocess.run(["git", "clone", "-q", f"--shallow-since={args.since}", REPO_URL, str(REPO_DIR)], check=True)

    first_seen = {}
    commits = git("log", "--reverse", "--format=%H %cI", "--", "feed.txt").split("\n")
    for line in filter(None, commits):
        sha, date = line.split()
        for url in git("show", f"{sha}:feed.txt").split():
            if url.startswith("http"):
                first_seen.setdefault(url, date)

    df = pd.DataFrame({"url": list(first_seen), "label": 1, "source": "openphish",
                       "collected_date": now_iso(), "first_seen": list(first_seen.values())})
    if OUT.exists():  # keep URLs from live runs of collect_openphish.py too
        old = pd.read_csv(OUT)
        df = pd.concat([df, old[~old["url"].isin(df["url"])]])
    df.to_csv(OUT, index=False)
    print(f"OpenPhish history: {len(commits)} snapshots, {len(df):,} unique URLs, "
          f"{df['first_seen'].min()[:10]} to {df['first_seen'].max()[:10]}")
