"""Tune every model with 5-fold grouped cross-validation on the training split.

Usage: python src/train.py [model_name ...]   (default: all models)
Saves models/tuning/<name>.joblib with the best pipeline (refitted on train) and the CV table.
"""
import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedGroupKFold

from features import FEATURE_NAMES
from model_setup import MODELS, SEED, build_pipeline

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "models" / "tuning"
SCORING = {"f1": "f1", "roc_auc": "roc_auc", "pr_auc": "average_precision",
           "precision": "precision", "recall": "recall"}


def load_split(name):
    feats = pd.read_csv(PROCESSED / "features.csv")
    splits = pd.read_csv(PROCESSED / "splits.csv")
    assert (feats["url"] == splits["url"]).all(), "features.csv and splits.csv are out of sync"
    mask = splits["split"] == name
    return feats.loc[mask, FEATURE_NAMES], feats.loc[mask, "label"], splits.loc[mask, "group"]


def tune(name, X, y, groups):
    estimator, space, kind = MODELS[name]
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    common = dict(scoring=SCORING, refit="f1", cv=cv, n_jobs=1 if name in ("random_forest", "knn") else -1,
                  return_train_score=True, verbose=1)
    if kind == "grid":
        search = GridSearchCV(build_pipeline(estimator), space, **common)
    else:
        search = RandomizedSearchCV(build_pipeline(estimator), space, n_iter=20, random_state=SEED, **common)

    start = time.time()
    search.fit(X, y, groups=groups)
    minutes = (time.time() - start) / 60

    cols = ["params"] + [f"{s}_{m}" for m in SCORING for s in ("mean_test", "std_test")] + ["mean_train_f1", "rank_test_f1"]
    table = pd.DataFrame(search.cv_results_)[cols].sort_values("rank_test_f1")
    best = table.iloc[0]
    summary = {"model": name, "best_params": {k: (v if isinstance(v, (int, float, str, type(None))) else str(v))
                                              for k, v in search.best_params_.items()},
               "cv_f1": round(best["mean_test_f1"], 4), "cv_f1_std": round(best["std_test_f1"], 4),
               "cv_roc_auc": round(best["mean_test_roc_auc"], 4), "cv_pr_auc": round(best["mean_test_pr_auc"], 4),
               "cv_precision": round(best["mean_test_precision"], 4), "cv_recall": round(best["mean_test_recall"], 4),
               "train_f1": round(best["mean_train_f1"], 4), "settings_tried": len(table), "minutes": round(minutes, 1)}
    # Save the best settings as an UNFITTED pipeline: a fitted random forest is ~170 MB (too big for
    # GitHub), and with fixed seeds refitting it in the notebook gives exactly the same model.
    joblib.dump({"pipeline": clone(search.best_estimator_), "cv_results": table, "summary": summary},
                OUT / f"{name}.joblib")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    X, y, groups = load_split("train")
    print(f"training rows: {len(X):,}, websites: {groups.nunique():,}", flush=True)
    for name in sys.argv[1:] or MODELS:
        tune(name, X, y, groups)
