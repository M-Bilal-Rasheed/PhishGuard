# PhishGuard Roadmap

Team **Link Lockers** · CT-378 Machine Learning · Fall 2026
Goal: classify a URL as phishing (1) or legitimate (0), deployed three ways, demo in Week 15.

## Pipeline at a glance

```
 Collect ──► Merge & clean ──► Features ──► EDA ──► Split ──► Pipeline + models ──► Tune ──► Evaluate ──► Save ──► Deploy x3 ──► Report + viva
 (Phase 1)    (Phase 2)        (Phase 3)   (P4)     (P5)        (Phase 6)          (P7)      (P8)        (P9)     (Phase 10)     (Phase 11)
```

## Phase 1: Data collection
| Step | Source | Script | Output |
|---|---|---|---|
| 1.1 | PhishTank verified feed (phishing) | `data/scripts/fetch_phishing.py` | `data/raw/phishtank.csv` |
| 1.2 | OpenPhish feed history from its GitHub repo, Aug–Nov 2026, each URL dated (phishing) | `data/scripts/collect_openphish_history.py` (+ `collect_openphish.py` for live top-ups) | `data/raw/openphish.csv` |
| 1.3 | PhiUSIIL, phishing rows only (label 0 = phishing there) | `data/scripts/fetch_phishing.py` | `data/raw/phiusiil_phish.csv` |
| 1.4 | Tranco top-1M, sampled across rank bands + all `.pk` | `data/scripts/fetch_legit.py` | `data/raw/tranco_sample.csv` |
| 1.5 | Real page URLs of those domains: own homepage crawler (main), Wayback Machine (fallback) | `data/scripts/fetch_legit.py` | `data/raw/legit_urls.csv` |
| 1.6a | Legitimate bare homepages from other Tranco domains | `data/scripts/fetch_legit_homepages.py` | `data/raw/legit_homepages.csv` |
| 1.6 | Record source, method, licence and date for each file | | `data/SOURCES.md` |

Safety rule: phishing URLs are only stored as text. They are never opened.

## Phase 2: Merge and clean (`data/scripts/build_dataset.py`)
1. Bring every source to the same columns: `url, label, source, collected_date`.
2. Normalize: trim spaces, add a missing scheme, lowercase the host, drop the default port (`:80`, `:443`), drop the trailing `/` and the `#fragment`.
3. Drop invalid URLs (no host, non-http schemes, broken text like `'+icon+'`).
4. Remove duplicates within and across sources.
5. Resolve conflicts: a URL in both classes is dropped; shared hosting domains (e.g. `sites.google.com`) are listed and checked.
6. Cap URLs per domain (about 20) so a few big sites don't dominate.
7. Sample a balanced final dataset of **50,000 rows: 25,000 phishing and 25,000 legitimate**. Phishing: OpenPhish 10k, PhishTank 7.5k, PhiUSIIL 7.5k. Both classes get the same mix: 75% deep links, 25% bare homepages, so "has a path" can't become a shortcut.
8. Output: `data/processed/urls.csv`.

## Phase 3: Feature engineering (`src/features.py`)
- One function, `extract_features(url)`, returning 20+ lexical features computed only from the URL text.
- Wrapped as `URLFeatureExtractor`, an sklearn transformer, so the saved pipeline takes raw URLs.
- The same file is used by the notebooks and all three apps.
- Output for EDA: `data/processed/features.csv`.

## Phase 4: EDA (`notebooks/01_eda.ipynb`), at least 5 plots
1. Class balance (bar chart).
2. URL length distribution per class (histogram / KDE).
3. Boxplots of key counts per class (outliers).
4. Correlation heatmap of the numeric features.
5. Top TLDs per class.
6. Suspicious-keyword rate per class.
7. Missing values table (expected near zero for lexical features; documented anyway).

## Phase 5: Split (`notebooks/02_modeling.ipynb`)
- 70 / 15 / 15 train / validation / test, stratified on the label.
- **Grouped by registered domain** (`GroupShuffleSplit`), so no domain appears in two splits.
- Time-based test: the newest OpenPhish URLs (late Oct–Nov 2026) are held out as "future" phishing; train only on older ones.
- Hand-made hard test set: about 50 tricky URLs (shorteners, long Google Docs links, phishing on free hosting).

## Phase 6: Preprocessing pipeline and models
```
Pipeline([
  ("features", URLFeatureExtractor()),
  ("prep", ColumnTransformer([
      ("num", Pipeline([SimpleImputer(median), StandardScaler()]), numeric_cols),
      ("cat", Pipeline([SimpleImputer(most_frequent), OneHotEncoder(handle_unknown="ignore", min_frequency=...)]), ["tld"]),
  ])),
  ("model", <estimator>),
])
```
Fitted on training data only. Models:
| Model | Role |
|---|---|
| `DummyClassifier` | Baseline |
| Rule-based detector (IP, `@`, many subdomains, suspicious TLD) | Common-sense baseline |
| Logistic Regression | Linear model |
| KNN | Distance-based model |
| Random Forest | Tree ensemble |
| Gradient Boosting (`HistGradientBoostingClassifier`) | Boosting |

## Phase 7: Tuning
- `RandomizedSearchCV` (or `GridSearchCV` for small grids) with **5-fold `StratifiedGroupKFold`** grouped by domain.
- Scoring: F1. Also record ROC-AUC and PR-AUC.
- Choose the decision threshold on the validation set to reach phishing recall ≥ 0.95.

## Phase 8: Evaluation (test set used once)
- Accuracy, precision, recall, F1, ROC-AUC, PR-AUC, false-positive rate, confusion matrix.
- Model comparison table and ROC / PR curves.
- Overfitting check: training vs. CV vs. test scores, and a learning curve.
- Error analysis: 10–20 misclassified URLs with explanations.
- Feature importance (permutation importance) to catch shortcut features.
- Separate results on the "future" OpenPhish set and the hard test set.
- Success targets: F1 ≥ 0.90, recall ≥ 0.95, false-positive rate < 5%.

## Phase 9: Save
- `models/phishguard_pipeline.joblib` (the full pipeline) and `models/metadata.json` (threshold, metrics, versions).
- `requirements.txt` with pinned versions.

## Phase 10: Deployment (all three, all loading the same pipeline and `src/features.py`)
| Platform | What to build |
|---|---|
| Streamlit Community Cloud | URL input, verdict + probability, feature contribution chart, public URL |
| Hugging Face | Model + model card on the Hub, Gradio Space |
| Local FastAPI | `POST /predict`, HTML front end, input validation, clear error messages |

## Phase 11: Report, demo and viva
- Report (3–4 pages, PDF): Abstract, Problem and motivation, Data collection, EDA, Methodology, Results, Deployment screenshots, Limitations and future work, References, Individual contribution table.
- GitHub repo: `data/` (scripts), `notebooks/`, `src/`, `app/`, `models/`, `requirements.txt`, README with the three links.
- Demo plan: 3 min problem and data, 4 min live apps, 3 min results. Every member rehearses viva questions on all parts.

## Folder structure
```
ML Project/
├── data/
│   ├── raw/            downloaded and collected files
│   ├── processed/      urls.csv, features.csv
│   ├── scripts/        fetch_*.py, collect_openphish.py, build_dataset.py
│   └── SOURCES.md      source, method, licence, date
├── notebooks/          01_eda, 02_modeling
├── src/features.py     shared feature extraction
├── app/                streamlit/, gradio/, fastapi/
├── models/             saved pipeline + metadata
├── reports/figures/    plots for the report
├── requirements.txt
└── README.md
```

## Suggested timeline (adjust to your weeks)
| When | Work |
|---|---|
| Week 12 | Proposal submitted, Phase 1 done (7 Nov 2026) |
| Week 13 | Phases 2–5: clean dataset, features, EDA |
| Week 13–14 | Phases 6–9: models, tuning, evaluation, saved pipeline |
| Week 14 | Phase 10: the three deployments |
| Week 15 | Phase 11: report, rehearsal, demo and viva |
