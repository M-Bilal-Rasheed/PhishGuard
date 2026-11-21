"""Compute the 31 URL features for every row of the final dataset.

Usage: python src/build_features.py  ->  data/processed/features.csv
Rows keep the same order as urls.csv (train.py and the notebooks rely on that).
"""
from pathlib import Path

import pandas as pd

from features import FEATURE_NAMES, extract_features

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
KEEP = ["url", "label", "source", "domain", "first_seen"]


def build(urls: pd.DataFrame) -> pd.DataFrame:
    feats = pd.DataFrame([extract_features(u) for u in urls["url"]], columns=FEATURE_NAMES)
    return pd.concat([urls[KEEP].reset_index(drop=True), feats], axis=1)


if __name__ == "__main__":
    urls = pd.read_csv(PROCESSED / "urls.csv")
    out = build(urls)
    out.to_csv(PROCESSED / "features.csv", index=False)
    print(f"{len(out):,} rows x {len(FEATURE_NAMES)} features -> {PROCESSED / 'features.csv'}")
