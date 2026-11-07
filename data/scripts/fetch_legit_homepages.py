"""Legitimate homepage URLs (no path) from the Tranco list.

Real users also visit bare homepages like https://www.hbl.com, so the legitimate
class needs some, just as the phishing class has bare-domain URLs.
Uses domains not already sampled by fetch_legit.py, spread across rank bands.
Usage: python data/scripts/fetch_legit_homepages.py
"""
import pandas as pd

from common import RAW, now_iso, session
from fetch_legit import BANDS, load_tranco

SEED = 7
PER_BAND = 1_700
PK = 500

if __name__ == "__main__":
    list_id, tranco = load_tranco(session())
    used = set(pd.read_csv(RAW / "tranco_sample.csv")["domain"])
    tranco = tranco[~tranco["domain"].isin(used)]

    parts = [tranco[(tranco["rank"] >= lo) & (tranco["rank"] <= hi)].sample(PER_BAND, random_state=SEED)
             for lo, hi, _ in BANDS]
    pk = tranco[tranco["domain"].str.endswith(".pk")]
    parts.append(pk.sample(min(PK, len(pk)), random_state=SEED))
    domains = pd.concat(parts)["domain"].reset_index(drop=True)
    # Half with "www." and half without, so "www." can't become a shortcut feature.
    prefix = pd.Series(["https://www.", "https://"]).sample(len(domains), replace=True, random_state=SEED)

    out = pd.DataFrame({"url": prefix.values + domains, "label": 0, "source": "tranco+homepage",
                        "collected_date": now_iso(), "first_seen": "", "domain": domains})
    out.to_csv(RAW / "legit_homepages.csv", index=False)
    print(f"Tranco list {list_id}: {len(out):,} homepage URLs ({len(pk):,} .pk domains available)")
