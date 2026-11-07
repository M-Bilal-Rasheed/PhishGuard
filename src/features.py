"""PhishGuard URL feature extraction.

Every feature is computed from the URL text only, so prediction is instant,
works offline and never opens the (possibly malicious) page.
The same code is used for training and by all three apps.
"""
import ipaddress
import math
import re
from collections import Counter
from urllib.parse import urlparse

import pandas as pd
import tldextract
from sklearn.base import BaseEstimator, TransformerMixin

# Offline public-suffix snapshot, so the apps never need the network for this.
_extract = tldextract.TLDExtract(suffix_list_urls=())

SUSPICIOUS_WORDS = (
    "login", "log-in", "signin", "sign-in", "verify", "verification", "account", "update",
    "secure", "security", "bank", "banking", "confirm", "password", "wallet", "billing",
    "invoice", "payment", "suspend", "unlock", "support", "webscr", "ebayisapi", "free", "bonus",
)
BRANDS = (
    "paypal", "apple", "microsoft", "office365", "outlook", "google", "facebook", "instagram",
    "whatsapp", "netflix", "amazon", "ebay", "dhl", "fedex", "usps", "chase", "wellsfargo",
    "allegro", "binance", "coinbase", "metamask", "jazzcash", "easypaisa", "hbl", "meezan", "daraz",
)
SHORTENERS = {
    "bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly", "rebrand.ly",
    "cutt.ly", "shorturl.at", "rb.gy", "t.ly", "tiny.cc", "s.id", "bit.do",
}
FREE_HOSTING = {
    "000webhostapp.com", "weebly.com", "wixsite.com", "blogspot.com", "github.io", "pages.dev",
    "workers.dev", "netlify.app", "vercel.app", "firebaseapp.com", "web.app", "herokuapp.com",
    "glitch.me", "repl.co", "godaddysites.com", "square.site", "webflow.io", "ngrok.io",
    "sites.google.com", "r2.dev", "myftp.org", "duckdns.org",
}
SUSPICIOUS_TLDS = {
    "xyz", "top", "tk", "ml", "ga", "cf", "gq", "buzz", "icu", "click", "link", "rest", "cyou",
    "sbs", "shop", "online", "site", "live", "support", "info", "work", "fit", "monster", "cfd",
}

NUMERIC_FEATURES = [
    "url_length", "hostname_length", "path_length", "query_length", "num_dots", "num_hyphens",
    "num_underscores", "num_slashes", "num_digits", "digit_ratio", "letter_ratio",
    "num_special_chars", "num_percent_encoded", "num_query_params", "num_subdomains",
    "path_depth", "longest_token_length", "url_entropy", "hostname_entropy",
    "suspicious_word_count", "is_https", "has_ip_host", "has_port", "has_at_symbol",
    "has_double_slash_in_path", "hyphen_in_domain", "brand_outside_domain", "is_shortener",
    "is_free_hosting", "suspicious_tld",
]
CATEGORICAL_FEATURES = ["tld"]
FEATURE_NAMES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return bool(re.fullmatch(r"0x[0-9a-f]+|\d{8,10}", host))  # hex / decimal encoded IPs


def extract_features(url: str) -> dict:
    url = str(url).strip()
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "http://" + url
    p = urlparse(url)
    host = (p.hostname or "").lower()
    ext = _extract(host)
    registered = ext.top_domain_under_public_suffix or host
    path, query = p.path or "", p.query or ""
    low = url.lower()
    rest = low.replace(registered, "", 1)  # URL without the real registered domain
    letters = sum(ch.isalpha() for ch in url)
    digits = sum(ch.isdigit() for ch in url)
    tokens = [t for t in re.split(r"[/\.\-_?=&:@~%+]", low) if t]
    try:
        has_port = p.port is not None
    except ValueError:
        has_port = True

    return {
        "url_length": len(url),
        "hostname_length": len(host),
        "path_length": len(path),
        "query_length": len(query),
        "num_dots": url.count("."),
        "num_hyphens": url.count("-"),
        "num_underscores": url.count("_"),
        "num_slashes": url.count("/"),
        "num_digits": digits,
        "digit_ratio": digits / len(url),
        "letter_ratio": letters / len(url),
        "num_special_chars": sum(url.count(c) for c in "@~!$*,;=&?+"),
        "num_percent_encoded": len(re.findall(r"%[0-9a-f]{2}", low)),
        "num_query_params": len([q for q in query.split("&") if q]),
        "num_subdomains": len([s for s in ext.subdomain.split(".") if s and s != "www"]),
        "path_depth": len([s for s in path.split("/") if s]),
        "longest_token_length": max((len(t) for t in tokens), default=0),
        "url_entropy": _entropy(low),
        "hostname_entropy": _entropy(host),
        "suspicious_word_count": sum(w in low for w in SUSPICIOUS_WORDS),
        "is_https": int(p.scheme.lower() == "https"),
        "has_ip_host": int(_is_ip(host)),
        "has_port": int(has_port),
        "has_at_symbol": int("@" in url),
        "has_double_slash_in_path": int("//" in path),
        "hyphen_in_domain": int("-" in registered),
        "brand_outside_domain": int(any(b in rest for b in BRANDS)),
        "is_shortener": int(registered in SHORTENERS or host in SHORTENERS),
        "is_free_hosting": int(registered in FREE_HOSTING or host in FREE_HOSTING
                               or any(host.endswith("." + h) for h in FREE_HOSTING)),
        "suspicious_tld": int(ext.suffix.split(".")[-1] in SUSPICIOUS_TLDS),
        "tld": ext.suffix.split(".")[-1] if ext.suffix else "none",
    }


class URLFeatureExtractor(BaseEstimator, TransformerMixin):
    """First pipeline step: raw URL strings in, feature DataFrame out."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        urls = X.iloc[:, 0] if isinstance(X, pd.DataFrame) else X
        return pd.DataFrame([extract_features(u) for u in urls], columns=FEATURE_NAMES)

    def get_feature_names_out(self, input_features=None):
        return FEATURE_NAMES
