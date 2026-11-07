# Data sources

All data was collected on **7 Nov 2026** with the scripts in `data/scripts/`.
Only URL text is stored. Phishing URLs were never opened. URLs contain no personal identifiers.

| # | Source | Class | Collection method | Rows (raw) | Licence / terms | Reference |
|---|---|---|---|---|---|---|
| 1 | PhishTank verified online feed | Phishing | `fetch_phishing.py` downloads `online-valid.csv` | 48,986 | Free to use with attribution (PhishTank, operated by Cisco Talos) | https://phishtank.org |
| 2 | OpenPhish community feed | Phishing | `collect_openphish_history.py` replays the feed's GitHub history (197 snapshots, 1 Aug – 6 Nov 2026); each URL keeps the date it first appeared | 46,519 | Free community feed, non-commercial use | https://openphish.com |
| 3 | PhiUSIIL Phishing URL Dataset (UCI) | Phishing | `fetch_phishing.py`; only rows with `label = 0` (phishing in PhiUSIIL) are kept, labels flipped to our convention | 100,945 | CC BY 4.0 | Prasad, A. & Chandra, S. (2024). PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and incremental learning. *Computers & Security*, 136. doi:10.1016/j.cose.2023.103545 |
| 4 | Tranco top-1M list (list ID `K9YYW`) | Legitimate (domains) | `fetch_legit.py` samples 600 domains from each rank band (1–10k, 10k–100k, 100k–1M) plus 400 `.pk` domains | 2,200 domains | Free for research | Le Pochat, V. et al. (2019). Tranco: A Research-Oriented Top Sites Ranking Hardened Against Manipulation. NDSS. https://tranco-list.eu/list/K9YYW |
| 5 | Own homepage crawler | Legitimate (URLs) | `fetch_legit.py` fetches each sampled homepage once (only if `robots.txt` allows) and keeps same-site links | 37,165 | Publicly linked URLs; robots.txt respected | — |
| 6 | Internet Archive Wayback Machine CDX API | Legitimate (URLs) | `fetch_legit.py` fallback for domains with fewer than 10 crawled links | 3,858 | Internet Archive terms of use | https://web.archive.org |
| 7 | Tranco homepages (list ID `Q2VV4`) | Legitimate (URLs) | `fetch_legit_homepages.py`: bare homepage URLs of 5,600 other Tranco domains (1,700 per rank band + 500 `.pk`; half with `www.`) | 5,600 | As source 4 | https://tranco-list.eu/list/Q2VV4 |

Common Crawl's URL index was tested as a source but was unreliable (frequent 504 timeouts), so sources 5 and 6 replace it.

## Processing
`build_dataset.py` normalizes all URLs the same way, removes invalid URLs, duplicates and URLs that appear in both classes, caps each host at 25 URLs, and samples a balanced dataset. `.pk` URLs are capped at 5% of the legitimate class, and every `.pk` phishing URL is kept.

| Step | Phishing | Legitimate |
|---|---|---|
| Raw | 196,450 | 46,623 |
| After normalization and invalid removal | 196,413 | 46,522 |
| After duplicates and label conflicts | 190,954 | 46,220 |
| After cap of 25 URLs per host | 158,747 | 34,931 |
| **Final (`processed/urls.csv`)** | **25,000** (OpenPhish 10,000, PhishTank 7,500, PhiUSIIL 7,500) | **25,000** (crawler 18,091, homepages 4,846, Wayback 2,063) |

Both classes have the same mix: 75% deep links and 25% bare homepages. `.pk` URLs: 1,250 legitimate, 99 phishing.

Final dataset: 50,000 URLs from 16,302 registered domains. Features: `processed/features.csv` (31 features from `src/features.py`).
