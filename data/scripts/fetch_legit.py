"""Collect legitimate page URLs.

1. Download the Tranco top-1M list and sample domains across rank bands, plus .pk domains.
2. Main method: fetch each domain's homepage once (if robots.txt allows) and keep
   links that point to the same site. These are real deep URLs with paths.
3. Fallback: for domains that gave fewer than MIN_LINKS links, ask the Wayback
   Machine's CDX index for archived page URLs of that domain.

Usage: python data/scripts/fetch_legit.py
"""
import io
import random
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urldefrag, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import tldextract
from tqdm import tqdm

from common import RAW, USER_AGENT, now_iso, session

SEED = 42
BANDS = [(1, 10_000, 600), (10_001, 100_000, 600), (100_001, 1_000_000, 600)]
MAX_PK = 400
MAX_LINKS = 40   # per domain, so no single site dominates
MIN_LINKS = 10   # below this, try the Wayback fallback
SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|ico|css|js|pdf|zip|mp4|mp3|woff2?|ttf|xml|json)(\?|$)", re.I)

# Offline public-suffix snapshot, so no network call is needed at runtime.
extract = tldextract.TLDExtract(suffix_list_urls=())


def registered_domain(host: str) -> str:
    return extract(host).top_domain_under_public_suffix


def load_tranco(s):
    list_id = s.get("https://tranco-list.eu/top-1m-id", timeout=60).text.strip()
    r = s.get("https://tranco-list.eu/top-1m.csv.zip", timeout=300)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df = pd.read_csv(z.open("top-1m.csv"), names=["rank", "domain"])
    return list_id, df


def sample_domains(tranco):
    rng = random.Random(SEED)
    parts = []
    for lo, hi, n in BANDS:
        band = tranco[(tranco["rank"] >= lo) & (tranco["rank"] <= hi)]
        parts.append(band.sample(n=n, random_state=rng.randint(0, 10**6)).assign(band=f"{lo}-{hi}"))
    pk = tranco[tranco["domain"].str.endswith(".pk")].head(MAX_PK).assign(band="pk")
    parts.append(pk)
    return pd.concat(parts).drop_duplicates("domain").reset_index(drop=True)


def same_site_links(base_url, html, reg):
    links = set()
    for href in re.findall(r"""href\s*=\s*["']([^"'#][^"']*)["']""", html, re.I):
        url, _ = urldefrag(urljoin(base_url, href.strip()))
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc or SKIP_EXT.search(p.path):
            continue
        if registered_domain(p.hostname or "") == reg:
            links.add(url)
    return links


def crawl_homepage(domain):
    s = session()
    for base in (f"https://{domain}/", f"https://www.{domain}/"):
        try:
            robots = RobotFileParser()
            rr = s.get(urljoin(base, "/robots.txt"), timeout=10)
            robots.parse(rr.text.splitlines() if rr.status_code == 200 else [])
            if not robots.can_fetch(USER_AGENT, base):
                return domain, [], "robots-disallow"
            r = s.get(base, timeout=12)
            if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
                continue
            links = same_site_links(r.url, r.text[:3_000_000], registered_domain(domain))
            links.add(r.url)
            return domain, sorted(links), "ok"
        except Exception:
            continue
    return domain, [], "unreachable"


def wayback_urls(domain):
    s = session()
    try:
        r = s.get("https://web.archive.org/cdx/search/cdx", timeout=60, params={
            "url": f"{domain}/*", "output": "json", "fl": "original", "collapse": "urlkey",
            "filter": ["statuscode:200", "mimetype:text/html"], "limit": 300,
        })
        rows = r.json()[1:] if r.status_code == 200 and r.text.strip() else []
    except Exception:
        return domain, []
    urls = []
    for (u,) in rows:
        # Wayback keeps some junk captures, e.g. script text inside URLs.
        if re.search(r"""['"+\s<>{}]|%20\+|\.\.\.""", u) or SKIP_EXT.search(u):
            continue
        urls.append(u.replace(":80/", "/").replace(":443/", "/"))
    return domain, sorted(set(urls))


def run_parallel(fn, items, workers, desc):
    out = {}
    with ThreadPoolExecutor(workers) as pool:
        futures = [pool.submit(fn, x) for x in items]
        for f in tqdm(as_completed(futures), total=len(futures), desc=desc, mininterval=10):
            res = f.result()
            out[res[0]] = res[1:]
    return out


if __name__ == "__main__":
    rng = random.Random(SEED)
    list_id, tranco = load_tranco(session())
    domains = sample_domains(tranco)
    print(f"Tranco list {list_id}: sampled {len(domains):,} domains")

    crawled = run_parallel(crawl_homepage, domains["domain"], 32, "homepages")
    domains["crawl_status"] = domains["domain"].map(lambda d: crawled[d][1])
    domains["crawl_links"] = domains["domain"].map(lambda d: len(crawled[d][0]))

    weak = domains.loc[domains["crawl_links"] < MIN_LINKS, "domain"]
    archived = run_parallel(wayback_urls, weak, 6, "wayback")
    domains["wayback_links"] = domains["domain"].map(lambda d: len(archived.get(d, ([],))[0]))

    rows, today = [], now_iso()
    for d in domains["domain"]:
        found = [(u, "crawler") for u in crawled[d][0]]
        if d in archived:
            found += [(u, "wayback") for u in archived[d][0] if u not in crawled[d][0]]
        rng.shuffle(found)
        rows += [(u, 0, f"tranco+{m}", today, d) for u, m in found[:MAX_LINKS]]

    legit = pd.DataFrame(rows, columns=["url", "label", "source", "collected_date", "domain"])
    legit.to_csv(RAW / "legit_urls.csv", index=False)
    domains.assign(tranco_list_id=list_id).to_csv(RAW / "tranco_sample.csv", index=False)

    print(domains["crawl_status"].value_counts().to_string())
    print(f"Legitimate URLs: {len(legit):,} from {legit['domain'].nunique():,} domains")
    print(legit["source"].value_counts().to_string())
