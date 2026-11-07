"""Download phishing URLs from PhishTank and PhiUSIIL (UCI).

Only the URL text is stored. The URLs are never opened.
Usage: python data/scripts/fetch_phishing.py
"""
import io
import zipfile

import pandas as pd

from common import RAW, now_iso, session

PHISHTANK_URL = "https://data.phishtank.com/data/online-valid.csv"
PHIUSIIL_URL = "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip"


def fetch_phishtank(s):
    r = s.get(PHISHTANK_URL, timeout=180)  # redirects to a signed CDN link
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    out = pd.DataFrame({
        "url": df["url"],
        "label": 1,
        "source": "phishtank",
        "collected_date": now_iso(),
        "first_seen": df["submission_time"],
    })
    out.to_csv(RAW / "phishtank.csv", index=False)
    print(f"PhishTank: {len(out):,} URLs")


def fetch_phiusiil(s):
    r = s.get(PHIUSIIL_URL, timeout=300)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df = pd.read_csv(z.open("PhiUSIIL_Phishing_URL_Dataset.csv"), usecols=["URL", "label"])
    # In PhiUSIIL, label 0 = phishing and 1 = legitimate. Its legitimate URLs are
    # homepages only (no paths), which would bias the model, so we keep phishing only.
    phish = df[df["label"] == 0]
    out = pd.DataFrame({
        "url": phish["URL"],
        "label": 1,
        "source": "phiusiil",
        "collected_date": now_iso(),
        "first_seen": "",
    })
    out.to_csv(RAW / "phiusiil_phish.csv", index=False)
    print(f"PhiUSIIL: {len(out):,} phishing URLs (of {len(df):,} total rows)")


if __name__ == "__main__":
    s = session()
    fetch_phishtank(s)
    fetch_phiusiil(s)
