# PhishGuard: Viva Preparation

Team **Link Lockers** · CT-378 Machine Learning · Fall 2026

This file explains **what** we did at every step, **why** we did it, and the **exact numbers**. It is updated after every phase. Every team member should be able to answer any question in it.

| Phase | Status | Section |
|---|---|---|
| 0. Problem and project choice | ✅ Done | [§1](#1-the-project-in-one-minute) |
| 1. Data collection | ✅ Done (7 Nov 2026) | [§3](#3-data-collection) |
| 2. Merge and clean | ✅ Done (7 Nov 2026) | [§4](#4-merging-and-cleaning) |
| 3. Feature engineering | ✅ Done (7 Nov 2026) | [§6](#6-feature-engineering) |
| 4. EDA | ✅ Done (7 Nov 2026) | [§7](#7-exploratory-data-analysis-eda) |
| 5–9. Split, models, tuning, evaluation, save | ⏳ Next | — |
| 10. Deployment (Streamlit, Hugging Face, FastAPI) | ⏳ Pending | — |
| 11. Report and demo | ⏳ Pending | — |

---

## 1. The project in one minute

**Problem.** People in Pakistan receive scam links by SMS, WhatsApp and email (fake bank, courier, BISP, JazzCash and Daraz pages). Most people can't tell a fake link from a real one.

**Solution.** PhishGuard: the user pastes a URL, and a machine learning model says **phishing or legitimate**, with a probability and a chart explaining why.

**ML task.** Binary classification. Target `is_phishing`: 1 = phishing, 0 = legitimate.

**Key design decision.** The model looks **only at the URL text**. It never opens the page.

Why:
- **Safety:** opening a phishing page could harm the server or the user.
- **Speed:** the prediction is instant.
- **Reliability:** it works offline, so it can't fail during the live demo. A failed deployment scores 0.
- **No leakage:** see the WHOIS answer in §9.

**Why this topic** (and not the other ideas):
- No other group in the class chose cybersecurity. Topics are first-come, first-served, and duplicates aren't allowed.
- The guidelines prefer data you collect yourselves. Here we really wrote our own collection scripts and our own feature extraction.
- The problem is real in Pakistan and has a clear user.
- It makes a strong live demo: paste a link and get an instant answer.

---

## 2. Requirements from the guidelines and how we meet them

| Requirement | How we meet it |
|---|---|
| Classification / regression / clustering / time-series task with a clear user | Binary classification; users are everyday internet users and fraud-awareness teams |
| Collect it yourselves, or combine at least two public sources | We combine **7 sources** and wrote our own collection scripts (including our own crawler) |
| Minimum 5,000 rows and 15 features | **50,000 rows** and **31 features** |
| Document source, method, licence and date; remove personal identifiers | `data/SOURCES.md`. URLs contain no personal data |
| Not allowed: Iris, Titanic, MNIST, Boston Housing | Our dataset is new and built by us |

---

## 3. Data collection

**Date of collection:** 7 Nov 2026. **Scripts:** `data/scripts/`.

### 3.1 Phishing URLs (label 1)

| Source | What it is | How we got it | Rows we got |
|---|---|---|---|
| **PhishTank** | Community site where people report phishing and others verify it | `fetch_phishing.py` downloads the verified-online CSV | **48,986** (dates from 2011 to 2026) |
| **OpenPhish** | Automatic phishing feed, updated twice a day | `collect_openphish_history.py` replays the feed's GitHub history | **46,519** unique URLs (197 snapshots, 1 Aug – 6 Nov 2026) |
| **PhiUSIIL** (UCI ML Repository, 2024) | Published research dataset of 235,795 URLs | `fetch_phishing.py`, phishing rows only | **100,945** |

**Why three phishing sources and not one?**
- **Variety.** Each source catches different kinds of phishing. PhishTank is reported by humans, OpenPhish is detected automatically, and PhiUSIIL is a curated research set. One source alone would give the model a narrow view.
- **Dates.** PhishTank and OpenPhish give a date for each URL, which lets us test on newer phishing than we trained on (time-based test).
- **Credibility.** PhiUSIIL is peer-reviewed and published, which supports the report.

**Why only the phishing rows of PhiUSIIL?**
- We checked its legitimate URLs: **100% of them are bare homepages** (like `https://www.uni-mainz.de`), with no path.
- Its phishing URLs do have paths. A model trained on this would learn "has a path = phishing", which is wrong in real life.
- **Watch out:** PhiUSIIL uses the opposite labels to ours (**0 = phishing, 1 = legitimate**). We flipped them.

**Why OpenPhish from GitHub history instead of collecting live for 2 weeks?**
- OpenPhish stores its public feed in a GitHub repository, so every past update is saved as a commit.
- Replaying the 197 commits gives the **date each URL first appeared**, just like collecting live for 3 months, in one minute.
- We kept the live collector (`collect_openphish.py`) for top-ups.

**Safety rule.** We store phishing URLs as **text only**. We never open them.

### 3.2 Legitimate URLs (label 0)

| Source | What it is | How we got it | Rows we got |
|---|---|---|---|
| **Tranco list** (ID `K9YYW`) | Research ranking of the world's top 1 million websites (domain names only) | Sampled **2,200 domains**: 600 from rank 1–10k, 600 from 10k–100k, 600 from 100k–1M, plus 400 `.pk` domains | 2,200 domains |
| **Our own crawler** | Downloads each sampled homepage once and keeps links to pages on the same website | `fetch_legit.py` | **37,165** URLs |
| **Wayback Machine** (Internet Archive) | Archive of old web pages, with an index of page URLs | `fetch_legit.py`, fallback for websites where the crawler found fewer than 10 links | **3,858** URLs |
| **Tranco homepages** (list ID `Q2VV4`) | Bare homepage URLs of 5,600 other Tranco domains: 1,700 per rank band + 500 `.pk` (half with `www.`, half without) | `fetch_legit_homepages.py` | **5,600** URLs |

Crawler results for the 2,200 domains:
- **1,334** succeeded.
- **783** were unreachable. Many Tranco domains are infrastructure (CDNs, APIs) with no website.
- **83** were blocked by `robots.txt`.
- Total from crawler plus Wayback: **41,023 URLs from 1,424 websites** (at most 40 per website).

**Why Tranco?**
- It's a research-grade list of real, popular websites. A domain in the top 1M is very unlikely to be a phishing site.
- It's designed to resist manipulation, unlike older lists such as Alexa, which has been discontinued.

**Why sample across rank bands, and not just the top 1,000?**
- Very popular sites (google.com, amazon.com) have short, clean URLs.
- Ordinary small websites have messier URLs that look more like phishing.
- If we only used famous sites, the model would learn "clean URL = safe" and flag every small business website. Sampling all bands makes the legitimate class realistic.

**Why 400 `.pk` domains?** Our users are Pakistani. The model must know what real Pakistani sites look like: banks, government, news, shops. (Later we found this was **too many** and capped `.pk` at 5% of the legitimate class; see §5, the `.pk` fix.)

**Why crawl real pages instead of using only domain names?** Tranco gives only `daraz.pk`, but real links look like `https://www.daraz.pk/products/...`. Phishing URLs have paths too, so the legitimate class must have them as well. Otherwise length or path becomes a fake shortcut.

**Why the Wayback Machine as a fallback?** Some websites block crawlers or failed to load. The Wayback Machine has archived page URLs for many of them. It's a second, independent method.

**Why add bare homepages?** See §5 (the path-bias fix).

**Ethics of crawling.**
- We read `robots.txt` first and skip a site if it disallows us.
- We download only **one page (the homepage) per site**.
- We send an honest User-Agent naming the project.

**What about Common Crawl?** We tested its URL index (a free archive of billions of web pages), but it returned frequent 504 timeouts. Our own crawler and the Wayback Machine replaced it.

### 3.3 Total collected

| | Phishing | Legitimate |
|---|---|---|
| Raw total | **196,450** | **46,623** |

---

## 4. Merging and cleaning

Script: `data/scripts/build_dataset.py`. Every step is applied **the same way to both classes**.

| Step | What | Why | Phishing left | Legitimate left |
|---|---|---|---|---|
| 0 | Load all 7 sources into the same columns: `url, label, source, collected_date, first_seen` | Sources have different formats | 196,450 | 46,623 |
| 1 | **Normalize**: add a missing `http://`, lowercase the host, remove default ports (`:80`, `:443`), remove `#fragments` and trailing `/` | Different sources format URLs differently (e.g. trailing slashes). If one class always ended in `/`, the model would learn the formatting, not phishing | | |
| 2 | **Remove invalid URLs**: no host, not http/https, broken text (quotes, spaces, `<>`), longer than 2,000 characters | Wayback returns some junk such as script text in URLs | 196,413 | 46,522 |
| 3 | **Remove duplicates**, and drop any URL that appears in **both** classes | Duplicates inflate scores (the same URL could end up in both train and test). A URL in both classes has an unreliable label | 190,954 | 46,220 |
| 4 | **Cap of 25 URLs per host** | Some sites have thousands of URLs. Without a cap the model memorizes a few sites instead of learning general patterns | 158,747 | 34,931 |
| 5 | **Balanced sampling** to 25,000 + 25,000, with the same deep-link mix in both classes, `.pk` capped at 5% of legitimate, and all `.pk` phishing kept (§5) | See §5 | **25,000** | **25,000** |

**Domains present in both classes: 111.** We kept them on purpose. These are mostly hosting platforms or hacked legitimate sites, and that happens in real life too.

**Missing values:** none. Every feature can be computed from any valid URL. The pipeline will still include an imputer in case of strange inputs in the app.

---

## 5. Final dataset: why 50,000 rows, why 50/50, and the path-bias fix

### Final dataset (`data/processed/urls.csv`)

| Class | Total | Breakdown |
|---|---|---|
| Phishing | 25,000 | OpenPhish 10,000 · PhishTank 7,500 · PhiUSIIL 7,500 |
| Legitimate | 25,000 | Crawler 18,091 · Homepages 4,846 · Wayback 2,063 |
| **Total** | **50,000** | From **16,302 different registered domains** |

### Why 50,000 rows?
- **10× the minimum** of 5,000 in the guidelines.
- **Limited by the legitimate class.** After cleaning we had 34,931 legitimate URLs. With the `.pk` cap (5%) and the 75/25 path mix, about 25,000 is the most we can use cleanly. The teacher allows more (e.g. 60k), but that would need another crawl or unbalanced classes, so we decide based on the learning curve in modelling.
- **Enough for reliable results.** The test set (15%) will have 7,500 URLs. With that many, a measured score is accurate to about ±1%.
- **Fast enough.** 5-fold cross-validation with grid search trains each model many times. KNN and SVM get slow on very large data. 50k keeps tuning to minutes, not hours.
- **Small enough to deploy.** The saved model stays small for Streamlit Cloud and Hugging Face.
- **We will prove it's enough.** A learning curve in the modelling phase will show whether more data would still help.

### Why 50% phishing and 50% legitimate?
- With equal classes, the model learns both equally and accuracy isn't misleading.
- In real life phishing is rarer than legitimate links. We handle that by:
  - reporting precision, recall, F1, PR-AUC and the false-positive rate, not only accuracy;
  - choosing the decision threshold on the validation set.
- This goes in the report's limitations section.

### Why OpenPhish 10,000 and the others 7,500?
- OpenPhish URLs are the **newest** (Aug–Nov 2026) and have exact dates.
- We need enough of them to hold out the newest ones as a "future phishing" test set.

### The path-bias problem and how we fixed it
**What we found** after the first build:

| | URLs with a path (deep links) |
|---|---|
| Legitimate | **91.5%** |
| Phishing | **32.5%** |

**Why that's dangerous.** The model can take a shortcut: "no path → phishing". It would score high in testing but call `https://www.hbl.com` phishing in the live demo.

**Why more phishing data doesn't fix it.** More of the same data has the same imbalance. The problem is the **composition** of the data, not the amount.

**The fix:**
1. We had about 158k phishing URLs but needed only 25k, so we **chose more phishing URLs that have a path**.
2. We **added real legitimate homepages** (5,600 collected), because real users do visit `hbl.com` directly.
3. **Result: both classes are now exactly 75% deep links and 25% bare homepages.**
4. We added homepages **half with `www.` and half without**, so "has www" can't become a new shortcut.

### The `.pk` bias and how we fixed it
**What the EDA found** in the first version of the dataset:

| | `.pk` legitimate | `.pk` phishing |
|---|---|---|
| First build | **5,774** (23% of all legitimate) | **20** |

**Why that's dangerous.** The model could learn ".pk = always safe". Then a phishing page on a hacked Pakistani site would be called safe, and Pakistani users are exactly our target users.

**Root cause.** We **over-sampled** Pakistani sites. 23% of our legitimate URLs were `.pk`, but in the real Tranco top-1M list `.pk` is only about **0.2%**. Also, phishing feeds contain very few `.pk` URLs.

**How much `.pk` phishing exists?** We searched **all 196k raw phishing URLs**: only **99 `.pk` phishing URLs** exist (87 different sites), and the first build had sampled just 20 of them. Most are **hacked Pakistani sites**, e.g. `tusdec.org.pk` and `wapdacityfsd.pk/confirmation/...` (`.com.pk` 37, `.edu.pk` 7, `.org.pk` 6). So `.pk` phishing is real.

**The fix:**
1. **Keep all 99 `.pk` phishing URLs** (instead of 20).
2. **Cap `.pk` legitimate URLs at 5%** of the legitimate class (1,250 URLs). That's still enough for the model to learn what Pakistani sites look like, without dominating.
3. Fill the freed space with non-`.pk` legitimate URLs. We collected 600 more homepages for this (1,700 instead of 1,500 per rank band).

| | `.pk` legitimate | `.pk` phishing | Ratio |
|---|---|---|---|
| Before | 5,774 | 20 | **289 : 1** |
| After | 1,250 | 99 | **12.6 : 1** |

**Why not make it 1 : 1?** Only 99 `.pk` phishing URLs exist in our sources. Making up fake ones would create data that isn't real. In reality `.pk` sites are mostly legitimate, so a moderate lean towards legitimate is correct. "Always safe" is what we must avoid.

**What's still left (for modelling):**
- Compare the model **with and without the `tld` feature**.
- Test it on **hand-made `.pk` phishing examples**.
- Tune the decision threshold.
- After the fix, a hand-made `https://tusdec.org.pk/wp-admin/hbl/verify-account.php` scores **0.44** in the quick model. That's suspicious, but just under 0.5, so this is a known weak spot to report honestly.

---

## 6. Feature engineering

File: `src/features.py`. **31 features**: 30 numeric and 1 categorical, all computed from the URL text alone.

| # | Feature | Meaning | Why it helps detect phishing |
|---|---|---|---|
| 1 | `url_length` | Length of the whole URL | Phishing URLs are often long, to hide the real domain |
| 2 | `hostname_length` | Length of the host part | Fake hosts are long, e.g. `secure-login-hbl-verify.xyz` |
| 3 | `path_length` | Length of the path | Deep, random paths are common in phishing kits |
| 4 | `query_length` | Length of the `?…` part | Tracking or redirect parameters |
| 5 | `num_dots` | Number of `.` | Many dots means many subdomains, e.g. `paypal.com.login.evil.xyz` |
| 6 | `num_hyphens` | Number of `-` | Phishers join words: `hbl-secure-login` |
| 7 | `num_underscores` | Number of `_` | Unusual in real domains |
| 8 | `num_slashes` | Number of `/` | Deep or odd paths |
| 9 | `num_digits` | Number of digits | Random-looking hosts and IDs |
| 10 | `digit_ratio` | Digits ÷ length | Generated domains have many digits |
| 11 | `letter_ratio` | Letters ÷ length | Real URLs are mostly readable words |
| 12 | `num_special_chars` | Count of `@ ~ ! $ * , ; = & ? +` | Tricks like `@` and many parameters |
| 13 | `num_percent_encoded` | Count of `%xx` codes | Encoding is used to hide text |
| 14 | `num_query_params` | Number of `key=value` pairs | Redirect and tracking tricks |
| 15 | `num_subdomains` | Subdomains (ignoring `www`) | Brand names placed in subdomains to fool users |
| 16 | `path_depth` | Number of folders in the path | Structure of the link |
| 17 | `longest_token_length` | Longest word between separators | Random strings and long fake words |
| 18 | `url_entropy` | Randomness of the characters | Randomly generated URLs have high entropy |
| 19 | `hostname_entropy` | Randomness of the host | Generated domains like `x7k2q9.top` |
| 20 | `suspicious_word_count` | Words like login, verify, account, secure, bank, password, bonus | Phishing pages imitate login and payment pages |
| 21 | `is_https` | Uses HTTPS (1/0) | Older phishing used plain http (but many phishers use HTTPS now) |
| 22 | `has_ip_host` | Host is an IP address | Real sites use domain names |
| 23 | `has_port` | Explicit port number | Unusual for normal sites |
| 24 | `has_at_symbol` | Contains `@` | The browser ignores everything before `@`, a classic trick |
| 25 | `has_double_slash_in_path` | `//` inside the path | Used for redirects |
| 26 | `hyphen_in_domain` | Hyphen in the registered domain | `hbl-verify.com` style fakes |
| 27 | `brand_outside_domain` | A brand name (paypal, hbl, jazzcash, daraz…) appears but isn't the real domain | `paypal.com.secure-check.xyz`: the brand is fake |
| 28 | `is_shortener` | bit.ly, tinyurl, etc. | Hides the real destination |
| 29 | `is_free_hosting` | pages.dev, weebly, 000webhostapp, firebaseapp… | Free, anonymous hosting is popular with phishers |
| 30 | `suspicious_tld` | .xyz, .top, .tk, .icu… | Cheap domain endings used heavily for phishing |
| 31 | `tld` (categorical) | The ending: com, pk, xyz… | Will be one-hot encoded |

**Why only URL-text (lexical) features, and not WHOIS or page content?**
- **Leakage risk.** Phishing sites are taken down within days. If we looked up the domain age (WHOIS) for old phishing URLs, the lookup would fail, and the model would learn "lookup failed = phishing". That reflects our collection timing, not real phishing.
- **Demo reliability.** WHOIS is slow and rate-limited. It could time out live.
- **Safety.** Fetching page content means visiting malicious pages.

**Why one shared file (`features.py`)?**
- The same code runs in training and in all three apps.
- It's wrapped as an sklearn transformer (`URLFeatureExtractor`) as the first step of the pipeline, so the saved model takes a raw URL directly.
- This means there can never be a mismatch between how features are computed in training and in the app.

**Why `tldextract` with an offline list?** It correctly splits `hbl.com.pk` into domain `hbl` and suffix `com.pk`. We use its built-in list so the app doesn't need the internet.

**Note:** `has_port` is very rare (30 URLs), but the EDA showed it is almost always phishing, so we keep it (see §7).

### Class averages after the bias fixes
| Feature | Legitimate | Phishing |
|---|---|---|
| `url_length` | 48.7 | 62.3 |
| `path_length` | 21.6 | 15.8 |
| `path_depth` | 1.48 | 1.30 |
| `is_https` | 0.95 | 0.75 |
| `num_subdomains` | 0.08 | 0.76 |
| `is_free_hosting` | 0.00 | 0.29 |
| `suspicious_tld` | 0.02 | 0.10 |

Path length and depth are now close between the classes. The differences that remain (subdomains, free hosting, TLDs) are **real phishing signs**.

### Quick sanity check (not the final model)
- **Setup:** an untuned Random Forest, tested on websites it never saw in training (split by domain).

| Result | Path fix only | Path + `.pk` fix (current) |
|---|---|---|
| F1 | 0.867 | **0.901** |
| Recall | 0.876 | **0.914** |
| False-positive rate | 12.5% | **12.8%** |

- **Most important features:** subdomain count, HTTPS, suspicious TLD, free hosting, hostname length. These are real phishing signals, not dataset artefacts.
- **Why the score isn't 99%.** Before the path fix, the task was artificially easy (about 99%) because of the shortcut. Now the score is **honest**. The `.pk` fix also improved it: the data is more representative, so the model generalizes better to unseen websites.
- **The false-positive rate (12.8%) is still too high** compared with our target (< 5%). Tuning, boosting and threshold selection in the modelling phase must bring it down.
- **Known weaknesses, for error analysis:**
  - `https://docs.google.com/document/d/.../edit` gets a phishing probability of 0.80 (false alarm). Long random IDs on legitimate platforms look like phishing.
  - Hand-made `.pk` phishing gets only 0.44 (see the `.pk` fix).

---

## 7. Exploratory Data Analysis (EDA)

**Notebook:** `notebooks/01_eda.ipynb` (run on the project venv, with all outputs saved). **Figures:** `reports/figures/01_…` to `09_…`.

**Why EDA before modelling?** EDA lets us check data quality, understand which features separate the classes, find outliers and redundant features, and catch bias **before** training. Every preprocessing choice in the pipeline comes from a finding here. The guidelines require at least 5 plots; **we made 9**.

### 7.1 Data quality
| Check | Result | Decision and why |
|---|---|---|
| Missing values | **0** in all 31 features | Still put a `SimpleImputer` in the pipeline. The app can receive strange input, and the pipeline must never crash |
| Duplicate URLs | **0** | Removed during cleaning |
| Constant features | **None** | — |
| Rare binary flags | `has_ip_host` 163, `has_port` 30, `has_at_symbol` 402, `has_double_slash_in_path` 89, `is_shortener` 130 URLs | **Keep them.** They're rare but almost only phishing (e.g. all 163 IP-host URLs and 25 of the 30 port URLs are phishing, like `rnfzd3.com:8989/register.html`) |

### 7.2 Class balance (figure 01)
- **Exactly 25,000 vs 25,000.** Why that matters: accuracy isn't distorted and no resampling (SMOTE or class weights) is needed.
- **Sources:** phishing from OpenPhish 10,000, PhishTank 7,500 and PhiUSIIL 7,500; legitimate from crawler 18,091, homepages 4,846 and Wayback 2,063.

### 7.3 Distributions (figure 02)
| Feature | Legitimate (median) | Phishing (median) | Meaning |
|---|---|---|---|
| `hostname_length` | 15 | 23 | Fake hosts are longer |
| `num_subdomains` | 0 | 1 | Brand names hidden in subdomains |
| `num_digits` | 0 | 2 | Random IDs and generated domains |
| `hostname_entropy` | 3.25 | 3.69 | Fake hosts look random |
| `path_length` | 15 | 10 | Overlaps a lot, as expected after the path-bias fix |

**Interesting detail (a good viva point):** hyphens have a median of 0 for legitimate and 1 for phishing (`hbl-secure-login`), but the **mean** is higher for legitimate (1.54 vs 1.26). News and shop pages use long hyphenated slugs (`/news/budget-2026-explained`). So the same character means different things in the domain and in the path. That's why we also have `hyphen_in_domain`.

### 7.4 Outliers (figure 03)
- **What:** all length and count features are strongly right-skewed. For example, the skewness of `url_length` is 8.1, and the maximum URL is 1,436 characters (the 99th percentile is 271).
- **What the outliers are:** we inspected the longest URLs. They're real phishing links: SendGrid e-mail redirect links that hide the phishing destination, a fake login page with a long token, and a fake Cloudflare Access login.
- **Decision: keep the outliers.** Why:
  1. They're **real data, not errors**.
  2. Long, encoded, parameter-heavy URLs are a phishing pattern, so removing them would throw away signal.
  3. The app will receive such URLs, so the model must have seen them.
- **How we handle them instead:** `log1p` and then `StandardScaler` for Logistic Regression and KNN, because huge values would dominate distances and weights. Tree models (Random Forest, Gradient Boosting) split on thresholds, so outliers and scale don't affect them.

### 7.5 Binary indicators (figure 04)
| Indicator | Legitimate | Phishing |
|---|---|---|
| `is_free_hosting` | 0.0% | **28.6%** |
| `suspicious_tld` | 1.7% | **10.4%** |
| `brand_outside_domain` | 0.4% | **8.4%** (about 20×) |
| `hyphen_in_domain` | 7.6% | 10.9% |
| `has_at_symbol` | 0.1% | 1.5% |
| `is_https` | **95.1%** | 74.6% |

- **HTTPS is not proof of safety:** 74% of phishing URLs use HTTPS, because free certificates (e.g. Let's Encrypt) are easy to get.
- **Limitation:** free hosting is 0% in our legitimate class, but real legitimate sites on `github.io` or `blogspot.com` exist. The model may over-trust this feature. We'll check this in error analysis.

### 7.6 TLDs (figure 05)
- **392 different TLDs**; 236 of them are used by fewer than 20 URLs.
- `.com` is common in both classes (10,960 legitimate vs 8,632 phishing), so the TLD alone can't decide.
- Phishing-leaning: `.dev` (2,448 vs 40), `.app` (2,009 vs 69), `.io`, `.top`, `.co`. Free hosting platforms like `pages.dev` and `vercel.app` use these endings.
- Legitimate-leaning: `.net`, `.org`, `.de`, `.jp`, `.uk`, `.fr`.
- **⚠️ Bias found and fixed: `.pk`.** The first EDA run showed 5,774 legitimate vs 20 phishing `.pk` URLs. We rebuilt the dataset (§5, the `.pk` fix), and it's now **1,250 vs 99**.
  - `.pk` still leans legitimate, which matches reality, but it's no longer "always safe".
  - Remaining plan: compare the model with and without `tld`, test hand-made `.pk` phishing, and mention it in limitations.
- **Encoding decision:** `OneHotEncoder(min_frequency=…, handle_unknown="ignore")`. Rare TLDs are grouped together so we don't get hundreds of nearly empty columns, and an unseen TLD in the app won't crash the model.

### 7.7 Correlations (figure 06)
We used **Spearman** correlation, not Pearson. Why: our features are skewed and many are counts. Spearman uses ranks, so it is robust to outliers and captures any monotonic relationship.

Highly correlated pairs (|r| ≥ 0.8):
| Pair | r |
|---|---|
| `num_query_params` – `query_length` | 0.998 |
| `digit_ratio` – `num_digits` | 0.985 |
| `num_query_params` – `num_special_chars` | 0.965 |
| `num_special_chars` – `query_length` | 0.963 |
| `path_depth` – `num_slashes` | 0.963 |
| `path_depth` – `path_length` | 0.875 |
| `hostname_entropy` – `hostname_length` | 0.873 |
| `num_slashes` – `path_length` | 0.852 |
| `url_entropy` – `url_length` | 0.822 |

**Decision: keep all features for now.** Why:
- Tree models aren't hurt by redundant features.
- For Logistic Regression, L2 regularization spreads the weight across correlated features.
- In modelling, permutation importance will show which features add nothing, and those can be dropped then.
- Dropping features now, before seeing the model, would be guesswork.

### 7.8 Most informative features (figure 07, mutual information)
| Rank | Feature | Mutual information |
|---|---|---|
| 1 | `hostname_entropy` | 0.235 |
| 2 | `num_subdomains` | 0.192 |
| 3 | `hostname_length` | 0.167 |
| 4 | `is_free_hosting` | 0.110 |
| 5 | `url_entropy` | 0.090 |

- **What mutual information is:** how much knowing a feature reduces uncertainty about the label. 0 means it's useless. The maximum for two balanced classes is ln 2 ≈ 0.69.
- **Why we used it:** unlike correlation, it also captures non-linear relationships and works for binary features.
- **Finding:** the best feature reaches only 0.235, far below 0.69. **No single feature can decide on its own**, so the model has to combine several. This shows the task isn't trivially easy now that the shortcut is gone.
- The top features are **real phishing signs** (how the hostname looks), not collection artefacts.

### 7.9 Bias check (figure 08)
- Deep-link share: **Legitimate 75.0%, Phishing 75.0%**. The path-bias fix holds.
- The path-depth distributions of the two classes nearly overlap, so path depth can't act as a shortcut.

### 7.10 Time coverage (figure 09)
- OpenPhish URLs run from **1 Aug to 6 Nov 2026**, about 600–850 per week.
- **Cut-off for the newest 15%: 23 Oct 2026.** URLs first seen after that date become the **time-based "future phishing" test**.
- PhishTank dates run from 2013 to 2026, and 47% are from 2026.

### 7.11 Decisions passed to the pipeline
| Finding | Decision |
|---|---|
| No missing values | Keep `SimpleImputer` for safety in the apps |
| Skewed counts and real outliers | Keep the rows; `log1p` + `StandardScaler` for LR and KNN; raw values for trees |
| 389 TLDs, many rare | One-hot with `min_frequency` and `handle_unknown="ignore"` |
| Correlated features | Keep; L2 regularization; review with permutation importance |
| Balanced classes | No resampling; F1, recall, PR-AUC and false-positive rate |
| `.pk` bias (5,774 vs 20) | **Fixed in the data** (now 1,250 vs 99); still test with and without `tld` and with hand-made `.pk` phishing |
| Free hosting 0% in legitimate | Check in error analysis; limitation |
| Dated OpenPhish URLs | Newest 15% (after 23 Oct 2026) as the time-based test |

### 7.12 EDA viva questions
**Q: Why didn't you remove outliers?**
A: They're real URLs. We inspected the longest ones and they're actual phishing redirect links. Removing them would delete exactly the kind of phishing we want to catch. We reduce their effect with `log1p` and scaling for LR and KNN, and trees aren't affected.

**Q: Why Spearman and not Pearson correlation?**
A: Our features are skewed counts with outliers. Spearman works on ranks, so it isn't dominated by extreme values and detects any monotonic relationship.

**Q: You have features with correlation 0.99. Why keep both?**
A: They only hurt linear models, and L2 regularization handles that. Trees don't care. We'll use permutation importance in modelling to decide what to drop, based on evidence rather than guessing.

**Q: What is mutual information, and what did it tell you?**
A: It measures how much a feature tells us about the label, including non-linear effects. The best feature reaches 0.235 out of a maximum of 0.69, so no single feature is enough. The model must combine signals, which also shows there's no shortcut.

**Q: Your data has no missing values. Why have an imputer?**
A: The deployed apps receive arbitrary user input. The imputer makes the pipeline robust and costs nothing.

**Q: What bias did EDA reveal?**
A: Two things. First, `.pk` was almost only legitimate (5,774 vs 20), because we over-sampled Pakistani sites (23% vs about 0.2% in reality). We fixed it in the data: we kept all 99 `.pk` phishing URLs and capped `.pk` legitimate at 5%, giving 1,250 vs 99. Second, free hosting is 0% legitimate. That one remains a known limitation, checked in error analysis.

**Q: Is HTTPS a good sign of a safe website?**
A: Not on its own. 74% of our phishing URLs use HTTPS. It's only a weak signal.

---

## 8. Plan for the next steps (with reasons)

| Step | Plan | Why |
|---|---|---|
| Split | 70/15/15, **grouped by domain** | If the same website is in train and test, the model memorizes the website and the test score is fake |
| Time-based test | Hold out the newest OpenPhish URLs | Shows the model works on future, unseen phishing |
| Pipeline | Feature extractor → imputer → scaler / one-hot → model, all in one sklearn `Pipeline` fitted on training data only | Prevents data leakage (the guidelines require it) |
| Models | Dummy baseline, rule-based baseline, Logistic Regression, KNN, Random Forest, Gradient Boosting | Guidelines require a baseline + 3 algorithms. The rule baseline proves ML adds value |
| Tuning | 5-fold `StratifiedGroupKFold` + `RandomizedSearchCV` / `GridSearchCV` | Required by the guidelines. Grouping keeps websites from leaking across folds |
| Metrics | F1, recall, false-positive rate, ROC-AUC, PR-AUC, confusion matrix | Accuracy alone hides how many scams we miss |
| Threshold | Chosen on the validation set for high phishing recall | Missing a scam is worse than a false alarm |

Success targets (from the proposal): **F1 ≥ 0.90, phishing recall ≥ 0.95, false-positive rate < 5%.**

---

## 9. Likely viva questions and answers

**Q: Why didn't you use a ready-made Kaggle phishing dataset?**
A: The guidelines ask us to collect data ourselves or combine at least two sources, and ready-made datasets often have hidden bias. PhiUSIIL's legitimate URLs, for example, are all homepages. We built our own from 7 sources with our own scripts.

**Q: How many sources did you use and why?**
A: Seven. Three phishing sources (PhishTank, OpenPhish, PhiUSIIL) give variety and dates. Four legitimate sources (Tranco, our crawler, the Wayback Machine, Tranco homepages) give realistic real-world URLs.

**Q: How much data did you collect, and how much did you use?**
A: We collected 196,450 phishing and 46,623 legitimate URLs. After cleaning we had 158,747 and 34,931. We used a balanced 25,000 + 25,000 = 50,000.

**Q: Why not use all 158k phishing URLs?**
A: The classes would be very unbalanced (about 5:1), and legitimate data is the limit. Using more rows also makes training slower without much gain. We'll confirm that with a learning curve.

**Q: How do you know the labels are correct?**
A: PhishTank URLs are verified by multiple people. OpenPhish is a professional feed. PhiUSIIL is peer-reviewed. Legitimate URLs come from the Tranco top-1M websites. We also removed every URL that appeared in both classes.

**Q: Isn't a legitimate site sometimes hacked and used for phishing?**
A: Yes. That's why we kept the 95 domains that appear in both classes, because that happens in reality. It's also a limitation we mention.

**Q: What is data leakage, and how did you avoid it?**
A: Leakage is when information that wouldn't be available in real use gets into training, which makes scores look better than they really are. We avoid it in four ways:
1. Features come only from the URL text, never from the source or the date.
2. The whole preprocessing is in an sklearn Pipeline fitted on training data only.
3. Splits are grouped by domain.
4. We don't use WHOIS, because failed lookups on dead phishing sites would reveal the label.

**Q: What is the path bias you found?**
A: 91.5% of legitimate URLs had a path versus 32.5% of phishing. The model could learn "no path = phishing". We fixed it by sampling both classes to the same 75/25 mix of deep links and homepages.

**Q: Why are your scores lower than the 99% in many papers?**
A: Many papers have shortcuts like the one we removed, or they split by row, so the same website appears in train and test. Our split is by website, so our score is honest.

**Q: Why should the user trust a 50/50 model when phishing is rare in reality?**
A: We don't report accuracy alone. We report precision, recall, the false-positive rate and PR-AUC, and we choose the threshold for the real use case. The class balance is listed as a limitation.

**Q: Why is HTTPS not proof of safety?**
A: 74% of our phishing URLs use HTTPS, because free certificates are easy to get. HTTPS is one weak signal among 31.

**Q: Did you break any website rules when crawling?**
A: No. We followed `robots.txt`, downloaded only one homepage per site, and used an honest User-Agent. Phishing URLs were never opened.

**Q: What is Tranco?**
A: A research ranking of the top 1 million websites (Le Pochat et al., NDSS 2019). It averages several rankings so it's hard to manipulate. We cite list ID `K9YYW`.

**Q: How did you get 3 months of OpenPhish data in one day?**
A: OpenPhish stores its public feed in a GitHub repository, and each update is a commit. We replayed the 197 commits and recorded the first date each URL appeared.

**Q: Why are there so few `.pk` phishing URLs? Doesn't that make your model weak for Pakistan?**
A: We searched all 196k phishing URLs: only 99 are `.pk`. Most scams aimed at Pakistanis use non-`.pk` domains (free hosting, cheap TLDs), and our model learns those patterns. To make sure `.pk` isn't treated as "always safe", we kept all 99 `.pk` phishing URLs, capped `.pk` legitimate at 5%, and we test with hand-made `.pk` phishing. It remains a stated limitation.

**Q: Why didn't you generate fake `.pk` phishing URLs to balance it?**
A: Synthetic URLs aren't real data. The model would learn our invented patterns, and the guidelines require documented, real sources. A moderate lean of `.pk` towards legitimate is also realistic.

**Q: Why cap 25 URLs per host?**
A: So a few huge websites don't dominate and the model learns general patterns instead of memorizing specific sites.

**Q: Why did you remove PhiUSIIL's 54 ready-made features?**
A: Some depend on page content we can't compute in our app, and some (like its similarity index) are suspected to leak the label. Computing our own features from the URL keeps training and the app consistent.

---

## 10. Glossary

| Term | Meaning |
|---|---|
| Phishing | A fake website or link that tricks people into giving passwords, card numbers or money |
| URL | A web address, e.g. `https://www.hbl.com/personal/cards` |
| Host / hostname | The website part: `www.hbl.com` |
| Registered domain | The part you buy: `hbl.com` |
| Subdomain | The part before it: `www`, `mail`, `secure-login` |
| TLD | The ending: `.com`, `.pk`, `.xyz` |
| Path | Everything after the host: `/personal/cards` |
| Lexical features | Features computed from the URL text only |
| Data leakage | Information in training that wouldn't exist in real use, making scores look too good |
| Shortcut learning | The model learns an accidental pattern in the data instead of the real concept |
| Grouped split | Splitting so all URLs of one website stay in the same set |
| `robots.txt` | A file where a website states what crawlers may access |
| Entropy | A measure of randomness in text |

---

## 11. Files reference

| File | Purpose |
|---|---|
| `ROADMAP.md` | All phases of the project |
| `data/SOURCES.md` | Source, method, licence, date and citation for every dataset |
| `data/scripts/fetch_phishing.py` | PhishTank + PhiUSIIL |
| `data/scripts/collect_openphish_history.py` | OpenPhish history from GitHub |
| `data/scripts/collect_openphish.py` | Live OpenPhish top-up |
| `data/scripts/fetch_legit.py` | Tranco sample + our crawler + Wayback fallback |
| `data/scripts/fetch_legit_homepages.py` | Legitimate homepages |
| `data/scripts/build_dataset.py` | Merge, clean and balance |
| `data/processed/urls.csv` | Final 50,000 URLs |
| `data/processed/features.csv` | The 31 features for every URL |
| `notebooks/01_eda.ipynb` | EDA notebook (all outputs saved) |
| `reports/figures/` | EDA figures for the report |
| `src/features.py` | Feature extraction, shared by training and all apps |
