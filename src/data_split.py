"""Train / validation / test / future split for PhishGuard.

- "future": OpenPhish phishing first seen on or after FUTURE_CUTOFF, from sites that
  never appear in the older data. Tests whether the model catches newer scams.
- The rest is split 70 / 15 / 15, grouped by website so no site is in two splits,
  and stratified so each split stays ~50/50.

Usage: python src/data_split.py  ->  data/processed/splits.csv
"""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from features import FREE_HOSTING

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
FUTURE_CUTOFF = pd.Timestamp("2026-10-23", tz="UTC")
SEED = 42


def group_key(row) -> str:
    """The 'website' a URL belongs to.

    On hosting platforms (pages.dev, github.io, ...) every subdomain is a different
    site owned by a different person, so the full host is the group. Elsewhere the
    registered domain is the group (mail.hbl.com and www.hbl.com are one site).
    """
    if row["domain"] in FREE_HOSTING:
        return row["host"]
    return row["domain"]


def make_splits(df: pd.DataFrame) -> pd.Series:
    df = df.copy()
    df["group"] = df.apply(group_key, axis=1)
    seen = pd.to_datetime(df["first_seen"], errors="coerce", utc=True, format="ISO8601")

    split = pd.Series("", index=df.index, dtype=object)
    is_new = (df["source"] == "openphish") & (seen >= FUTURE_CUTOFF)
    old_groups = set(df.loc[~is_new, "group"])
    future = is_new & ~df["group"].isin(old_groups)
    split[future] = "future"
    # New URLs from sites already seen earlier are dropped: they wouldn't be a fair "new scam" test,
    # and keeping them in training would leak newer data into the past.
    split[is_new & ~future] = "dropped"

    rest = df[split == ""]
    # 20 stratified group folds: 14 -> train (70%), 3 -> validation (15%), 3 -> test (15%)
    folds = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=SEED)
    for i, (_, idx) in enumerate(folds.split(rest, rest["label"], rest["group"])):
        split[rest.index[idx]] = "train" if i < 14 else "val" if i < 17 else "test"
    return split, df["group"]


if __name__ == "__main__":
    df = pd.read_csv(PROCESSED / "urls.csv")
    df["split"], df["group"] = make_splits(df)
    df[["url", "label", "source", "domain", "group", "first_seen", "split"]].to_csv(PROCESSED / "splits.csv", index=False)

    summary = df.groupby(["split", "label"]).size().unstack(fill_value=0)
    summary["total"] = summary.sum(axis=1)
    summary["phishing_share"] = (summary[1] / summary["total"]).round(3)
    print(summary.to_string())
    for a in ("train", "val", "test"):
        for b in ("train", "val", "test", "future"):
            if a < b:
                shared = set(df.loc[df.split == a, "group"]) & set(df.loc[df.split == b, "group"])
                print(f"websites shared between {a} and {b}: {len(shared)}")
