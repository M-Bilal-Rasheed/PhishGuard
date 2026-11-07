"""Merge, clean and balance all raw sources into data/processed/urls.csv.

Usage: python data/scripts/build_dataset.py
"""
import re
from urllib.parse import urlparse, urlunparse

import pandas as pd
import tldextract

from common import PROCESSED, RAW

SEED = 42
PER_CLASS = 25_000
MAX_PER_HOST = 25
PATH_SHARE = 0.75  # same share of deep links vs. bare homepages in both classes
PHISH_QUOTA = {"openphish": 10_000, "phishtank": 7_500, "phiusiil": 7_500}
# .pk sites were over-sampled during collection (23% of legitimate URLs, vs ~0.2% of
# the Tranco top-1M). Cap them, so the model can't learn ".pk = always safe".
PK_LEGIT_SHARE = 0.05
INVALID = re.compile(r"""[\s'"<>{}\\^`|]""")
extract = tldextract.TLDExtract(suffix_list_urls=())


def normalize(url):
    """Apply the same formatting to every source, so formatting can't leak the label."""
    url = str(url).strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "http://" + url
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        port = p.port
    except ValueError:
        return None
    if p.scheme.lower() not in ("http", "https") or not host or "." not in host:
        return None
    netloc = host if port in (None, 80, 443) else f"{host}:{port}"
    path = p.path.rstrip("/") if not p.query else p.path
    url = urlunparse((p.scheme.lower(), netloc, path, p.params, p.query, ""))
    if len(url) > 2000 or INVALID.search(url):
        return None
    return url


def load_raw():
    frames = [pd.read_csv(RAW / f) for f in
              ("phishtank.csv", "phiusiil_phish.csv", "openphish.csv",
               "legit_urls.csv", "legit_homepages.csv")]
    df = pd.concat(frames, ignore_index=True)
    return df[["url", "label", "source", "collected_date", "first_seen"]]


def has_path(url):
    p = urlparse(url)
    return bool(p.path.strip("/") or p.query)


def sample_mix(frame, n, seed=SEED):
    """Sample n rows with PATH_SHARE deep links and the rest bare homepages."""
    n_path = round(n * PATH_SHARE)
    deep, bare = frame[frame["has_path"]], frame[~frame["has_path"]]
    return pd.concat([deep.sample(n_path, random_state=seed), bare.sample(n - n_path, random_state=seed)])


def report(step, df):
    counts = df["label"].value_counts().reindex([1, 0], fill_value=0)
    print(f"{step:<34} phishing {counts[1]:>8,}   legitimate {counts[0]:>8,}")


if __name__ == "__main__":
    df = load_raw()
    report("raw", df)

    df["url"] = df["url"].map(normalize)
    df = df.dropna(subset=["url"])
    report("after normalize + invalid removal", df)

    df = df.drop_duplicates(["url", "label"])
    both = df.groupby("url")["label"].nunique()
    df = df[~df["url"].isin(both[both > 1].index)]
    report("after duplicates + label conflicts", df)

    df["host"] = df["url"].map(lambda u: urlparse(u).hostname)
    df["domain"] = df["host"].map(lambda h: extract(h).top_domain_under_public_suffix or h)
    shared = set(df.loc[df.label == 1, "domain"]) & set(df.loc[df.label == 0, "domain"])
    print(f"domains present in both classes (kept, e.g. hosting platforms): {len(shared)}")

    df = df.sample(frac=1, random_state=SEED).groupby(["label", "host"]).head(MAX_PER_HOST)
    report(f"after cap of {MAX_PER_HOST} URLs per host", df)

    # Both classes get the same deep-link / homepage mix, so "has a path"
    # can't become a shortcut. OpenPhish has the newest, dated URLs, used later
    # for the time-based "future phishing" test.
    df["has_path"] = df["url"].map(has_path)
    df["is_pk"] = df["host"].str.endswith(".pk")

    # Phishing: every .pk phishing URL is kept (they are rare), the rest is sampled.
    phish = []
    for src, n in PHISH_QUOTA.items():
        pool = df[(df.label == 1) & (df.source == src)]
        phish += [pool[pool.is_pk], sample_mix(pool[~pool.is_pk], n - pool.is_pk.sum())]
    phish = pd.concat(phish)

    legit_pool = df[df.label == 0]
    n_pk = round(PER_CLASS * PK_LEGIT_SHARE)
    legit = pd.concat([sample_mix(legit_pool[legit_pool.is_pk], n_pk),
                       sample_mix(legit_pool[~legit_pool.is_pk], PER_CLASS - n_pk)])

    final = pd.concat([phish, legit]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    final.to_csv(PROCESSED / "urls.csv", index=False)
    report("final dataset", final)
    print(final["source"].value_counts().to_string())
    print(final.groupby("label")["has_path"].mean().rename("deep-link share").round(3).to_string())
    print(final.groupby("label")["is_pk"].sum().rename(".pk URLs").to_string())
    print(f"unique domains: {final['domain'].nunique():,}")
