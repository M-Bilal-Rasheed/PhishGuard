"""Append the current OpenPhish community feed to data/raw/openphish.csv.

Run every 6 hours for about 2 weeks (Windows Task Scheduler), e.g.:
  schtasks /Create /SC HOURLY /MO 6 /TN PhishGuard-OpenPhish ^
    /TR "\"<project>\\.venv\\Scripts\\python.exe\" \"<project>\\data\\scripts\\collect_openphish.py\""
Only the URL text is stored. The URLs are never opened.
"""
import pandas as pd

from common import RAW, now_iso, session

FEED_URL = "https://raw.githubusercontent.com/openphish/public_feed/refs/heads/main/feed.txt"
OUT = RAW / "openphish.csv"

if __name__ == "__main__":
    r = session().get(FEED_URL, timeout=60)
    r.raise_for_status()
    urls = [u.strip() for u in r.text.splitlines() if u.strip().startswith("http")]
    batch = pd.DataFrame({"url": urls, "label": 1, "source": "openphish",
                          "collected_date": now_iso(), "first_seen": now_iso()})

    if OUT.exists():
        old = pd.read_csv(OUT)
        batch = batch[~batch["url"].isin(old["url"])]  # keep the first time we saw each URL
    batch.to_csv(OUT, mode="a", header=not OUT.exists(), index=False)
    total = len(pd.read_csv(OUT))
    print(f"OpenPhish: {len(urls)} in feed, {len(batch)} new, {total:,} collected so far")
