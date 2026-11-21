"""Preprocessing, baselines, models and tuning spaces for PhishGuard.

Every preprocessing step lives inside a scikit-learn Pipeline, so it is fitted on
training data only (no leakage) and saved together with the model.
"""
import numpy as np
from scipy.stats import loguniform
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, URLFeatureExtractor

SEED = 42

# Ratios and entropies are already on a small scale; everything else is a count or length
# with a long right tail, so it gets log1p first (EDA section 4).
SCALE_ONLY = ["digit_ratio", "letter_ratio", "url_entropy", "hostname_entropy"]
BINARY = ["is_https", "has_ip_host", "has_port", "has_at_symbol", "has_double_slash_in_path",
          "hyphen_in_domain", "brand_outside_domain", "is_shortener", "is_free_hosting", "suspicious_tld"]
LOG_SCALE = [c for c in NUMERIC_FEATURES if c not in SCALE_ONLY + BINARY]


def build_preprocessor(use_tld: bool = True) -> ColumnTransformer:
    parts = [
        ("log_scale", Pipeline([("impute", SimpleImputer(strategy="median")),
                                ("log1p", FunctionTransformer(np.log1p, feature_names_out="one-to-one")),
                                ("scale", StandardScaler())]), LOG_SCALE),
        ("scale", Pipeline([("impute", SimpleImputer(strategy="median")),
                            ("scale", StandardScaler())]), SCALE_ONLY),
        ("binary", SimpleImputer(strategy="most_frequent"), BINARY),
    ]
    if use_tld:
        parts.append(("tld", Pipeline([
            ("impute", SimpleImputer(strategy="constant", fill_value="none")),
            ("onehot", OneHotEncoder(min_frequency=20, handle_unknown="infrequent_if_exist", sparse_output=False)),
        ]), CATEGORICAL_FEATURES))
    return ColumnTransformer(parts, remainder="drop", verbose_feature_names_out=False)


def build_pipeline(model, use_tld: bool = True, with_extractor: bool = False) -> Pipeline:
    """Feature extraction is stateless (fit learns nothing), so during tuning we pass
    pre-computed features to save time; the saved model includes the extractor."""
    steps = [("features", URLFeatureExtractor())] if with_extractor else []
    steps += [("prep", build_preprocessor(use_tld)), ("model", model)]
    return Pipeline(steps)


class RuleBasedDetector(BaseEstimator, ClassifierMixin):
    """Common-sense baseline: flag a URL if any classic phishing sign is present.
    If ML can't beat this, ML isn't adding value."""

    RULES = ["has_ip_host", "has_at_symbol", "is_shortener", "is_free_hosting",
             "suspicious_tld", "brand_outside_domain"]

    def fit(self, X, y=None):
        self.classes_ = np.array([0, 1])
        return self

    def _score(self, X):
        hits = X[self.RULES].sum(axis=1) + (X["num_subdomains"] >= 3)
        return hits.to_numpy()

    def predict(self, X):
        return (self._score(X) > 0).astype(int)

    def predict_proba(self, X):
        p = np.clip(self._score(X) / 2, 0, 1)
        return np.column_stack([1 - p, p])


# name -> (estimator, search space, search type)
MODELS = {
    "logistic_regression": (
        LogisticRegression(max_iter=3000, random_state=SEED),
        {"model__C": [0.001, 0.01, 0.1, 1, 10, 100]},
        "grid",
    ),
    "knn": (
        KNeighborsClassifier(n_jobs=2),
        {"model__n_neighbors": [5, 15, 31, 51], "model__weights": ["uniform", "distance"], "model__p": [1, 2]},
        "grid",
    ),
    "random_forest": (
        RandomForestClassifier(n_jobs=2, random_state=SEED),
        {"model__n_estimators": [200, 400], "model__max_depth": [None, 20, 30],
         "model__min_samples_leaf": [1, 2, 4], "model__max_features": ["sqrt", 0.3, 0.5]},
        "random",
    ),
    "gradient_boosting": (
        HistGradientBoostingClassifier(random_state=SEED),
        {"model__learning_rate": loguniform(0.02, 0.3), "model__max_iter": [200, 400, 800],
         "model__max_leaf_nodes": [15, 31, 63, 127], "model__min_samples_leaf": [20, 50, 100],
         "model__l2_regularization": loguniform(1e-4, 10)},
        "random",
    ),
}

BASELINES = {
    "dummy_most_frequent": DummyClassifier(strategy="most_frequent"),
    "rule_based": RuleBasedDetector(),
}
