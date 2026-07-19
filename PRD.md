<context>
# Overview
This project turns the existing Jekyll blog (coldnine.github.io, hosted on GitHub Pages) into a fully automated daily news digest. Each day, a GitHub Actions workflow crawls the AI/SW section of Korean IT outlet ETNews (m.etnews.com), extracts the core keywords and a short summary for each new article, and commits a generated Markdown post back to the repo. GitHub Pages then rebuilds the site automatically, so the blog stays up to date with zero manual intervention.

**Problem it solves**: Manually reading and curating daily IT/AI news is time-consuming. This automates discovery, extraction, and publishing of a condensed keyword+summary digest.

**Who it's for**: The blog owner (coldnine), and readers who want a fast daily scan of Korean AI/SW industry news without reading full articles.

**Why it's valuable**: Removes manual content-creation effort entirely, produces a consistent daily archive of posts, and demonstrates a small, self-contained end-to-end automation (crawl → NLP → publish → deploy) built entirely on free infrastructure (GitHub Actions + GitHub Pages).

# Core Features

## 1. ETNews AI/SW Article Crawler
- **What it does**: Fetches the article list from the ETNews AI/SW section (`https://m.etnews.com/news/section.html?id1=04`), identifies articles published since the last run, and retrieves the full text/title/publish date/URL for each new article.
- **Why it's important**: This is the data source for everything downstream; without reliable, deduplicated crawling, the pipeline has nothing to summarize.
- **How it works at a high level**: A Python script requests the section listing page, parses article links matching the ETNews URL pattern (`https://etnews.com/YYYYMMDD000000`), filters out articles already processed (tracked via a state file or by checking existing post front matter/IDs in the repo), then fetches and parses each article's detail page for its body text.

## 2. Keyword & Summary Extraction Engine
- **What it does**: For each crawled article, extracts a ranked list of core keywords and a short (2-5 sentence) summary of the article content.
- **Why it's important**: This is the core value-add that turns a raw article into a scannable digest entry.
- **How it works at a high level**: A pluggable extraction layer supports multiple selectable methods, chosen via config:
  - Keyword extraction: KeyBERT (embedding-based) and/or KoNLPy (Korean morphological analysis + frequency/TF-IDF).
  - Summarization: TextRank (extractive, unsupervised) and/or an LLM API call (e.g., using an existing API key already configured for Task Master).
  - The active method(s) are selected via a config file (e.g., `config.yml` or `.env`) so the approach can be swapped without code changes.

## 3. Markdown Post Generator
- **What it does**: Converts each article's extracted keywords + summary (+ original title, source URL, publish date) into a Jekyll-compatible Markdown post with correct YAML front matter and filename convention (`_posts/YYYY-MM-DD-<slug>.md`).
- **Why it's important**: Ensures generated content renders correctly on the existing Jekyll/minima theme and integrates with the blog's existing structure (as seen in the previously used `_posts/YYYY-MM-DD-growth-log-N.md` naming pattern).
- **How it works at a high level**: A templated Markdown generator fills in front matter (title, date, categories/tags, layout) and body (keyword list, summary, link to original article), one file per article (or one combined digest file per day — configurable).

## 4. Daily Scheduling & Publishing Pipeline (GitHub Actions)
- **What it does**: Runs the crawl → extract → generate → commit/push sequence once per day on a schedule, fully unattended.
- **Why it's important**: This is what makes the whole system "automatic" — no local execution or manual trigger needed.
- **How it works at a high level**: A GitHub Actions workflow (`.github/workflows/daily-post.yml`) triggered by a `schedule` (cron) event (and optionally `workflow_dispatch` for manual runs) sets up Python, installs dependencies, runs the crawler+extractor+generator script, then commits any new Markdown files and pushes to the default branch. GitHub Pages' existing build hook then republishes the site automatically.

## 5. Configurable Pipeline Settings
- **What it does**: Centralizes tunable parameters — which extraction method to use, how many keywords to extract, crawl lookback window, target section URL, dedup state location — in one config file.
- **Why it's important**: Lets the method (KeyBERT vs KoNLPy vs LLM vs TextRank) be swapped or tuned without touching pipeline code, per the TODO's "make it to be selectable in config" requirement.
- **How it works at a high level**: A single YAML/JSON/`.env`-based config read at the start of the script run, validated with sensible defaults.

# User Experience

## User Personas
- **Blog owner (coldnine)**: Wants a hands-off, reliable daily post without maintaining infrastructure beyond GitHub. Occasionally wants to tweak extraction method or keyword count.
- **Casual reader**: Visits the GitHub Pages site to skim daily AI/SW keyword digests instead of reading full ETNews articles.

## Key User Flows
- **Automated flow (primary)**: GitHub Actions cron fires daily → crawler finds new articles → extraction runs → Markdown post(s) generated → committed/pushed → GitHub Pages rebuilds → reader visits site and sees the new post(s).
- **Manual/debug flow**: Blog owner manually triggers the workflow (`workflow_dispatch`) or runs the script locally to test changes before merging.
- **Configuration flow**: Blog owner edits the pipeline config to change extraction method or parameters, commits the change, and the next scheduled run picks it up.

## UI/UX Considerations
- No custom UI is built; the "interface" is the existing Jekyll/minima blog theme rendering standard posts.
- Each generated post should be readable at a glance: title, date, source link, keyword tags/list, and summary — consistent formatting across all auto-generated posts.
- Posts should clearly indicate they are auto-generated digests (e.g., a footer note/link back to the original ETNews article) for transparency and to respect source attribution.
</context>
<PRD>
# Technical Architecture

## System Components
- **Crawler module** (`scripts/crawl.py` or similar): HTTP client (`requests`/`httpx`) + HTML parser (`BeautifulSoup`) targeting ETNews' mobile section listing and article detail pages.
- **Extraction module** (`scripts/extract.py`): Wraps keyword extraction (KeyBERT, KoNLPy-based TF-IDF) and summarization (TextRank via `sumy` or similar, and/or LLM API call) behind a common interface, selected by config.
- **Post generator module** (`scripts/generate_post.py`): Builds Jekyll front matter + body from a templated string/Jinja2 template, writes into `_posts/`.
- **Orchestrator/entrypoint script** (`scripts/run_daily.py`): Ties crawler → extractor → generator together, handles dedup/state, logging, and error handling for a single run.
- **State/dedup store**: A lightweight tracking mechanism (e.g., a JSON file like `data/processed_articles.json`, or simply scanning existing `_posts/` filenames/front matter for already-processed article IDs) committed to the repo so re-runs don't duplicate posts.
- **GitHub Actions workflow** (`.github/workflows/daily-post.yml`): Scheduled CI job that installs Python deps, runs the orchestrator, and commits/pushes results.
- **Config file** (`config.yml` or `.env` + `config.py`): Central place for section URL, extraction method choice, keyword count, summary length, crawl lookback, output mode (per-article vs digest).
- **Existing Jekyll site**: Unmodified core (uses `remote_theme: jekyll/minima`); only `_posts/` gains new files.

## Data Models
- **Article record**: `{ id, url, title, published_at, raw_text, section }`
- **Extraction result**: `{ article_id, keywords: [string], summary: string, method: string }`
- **Post front matter**: `{ layout, title, date, categories, tags, source_url }`
- **Processed-articles state**: `{ processed_ids: [string], last_run_at: timestamp }`

## APIs and Integrations
- ETNews public web pages (no official API — HTML scraping of `m.etnews.com`).
- Optional LLM API (reuse existing configured provider/key, e.g., Anthropic/OpenAI/Perplexity, similar to those already set up for Task Master) for the summary/keyword path when config selects "LLM" mode.
- KeyBERT / KoNLPy / sumy (TextRank) as local, API-free fallback methods requiring no external network calls beyond model downloads.
- GitHub Actions (`actions/checkout`, `actions/setup-python`, and a commit/push step, e.g., via `git` commands or a commit-action).
- GitHub Pages (implicit — no integration code needed, triggered automatically by pushes to the publishing branch).

## Infrastructure Requirements
- GitHub repository with Actions enabled (already true) and Pages enabled from the current branch/`_site` build.
- Python 3.x runtime in CI (no external servers/hosting needed — everything runs inside the Actions runner).
- Secrets: any LLM API key needed for the optional LLM extraction path, stored as a GitHub Actions secret (not committed).
- No database; all state is file-based and version-controlled.

# Development Roadmap

## Phase 1 — MVP: Manual, Single-Method Pipeline
- Build the crawler for the ETNews AI/SW section: fetch listing, parse article links matching the `etnews.com/YYYYMMDD000000` pattern, fetch article detail HTML, extract title/body/date/URL.
- Implement one keyword extraction method (TF-IDF via KoNLPy, the simplest to stand up without external API dependency) and one summarization method (TextRank).
- Implement the Markdown post generator producing valid Jekyll front matter and a consistent body template (title, date, source link, keyword list, summary).
- Implement a basic dedup mechanism (state file of processed article IDs).
- Script is runnable locally end-to-end (crawl → extract → generate) producing one or more `_posts/*.md` files.
- Manually verify output renders correctly with `bundle exec jekyll serve`.

## Phase 2 — Automation via GitHub Actions
- Add `.github/workflows/daily-post.yml` with a `schedule` (cron) trigger and a `workflow_dispatch` manual trigger.
- Workflow installs Python + dependencies, runs the Phase 1 script, and commits/pushes any newly generated post(s) and updated state file using a bot commit identity.
- Add basic failure handling/logging so a crawl failure or zero-new-articles day doesn't break the workflow or produce empty/broken commits.
- Confirm GitHub Pages rebuilds and publishes automatically after the workflow's push.

## Phase 3 — Configurable Extraction Methods
- Introduce a config file (`config.yml`) exposing: extraction method selector (`tfidf` / `keybert` / `llm`), summarization method selector (`textrank` / `llm`), number of keywords, summary length/sentence count, crawl lookback window, output mode (one post per article vs. one combined daily digest post).
- Implement KeyBERT as an alternative embedding-based keyword extraction method.
- Implement an LLM-based extraction/summarization path (single API call returning both keywords and summary) as a selectable alternative, using a securely stored API key.
- Refactor extraction module into a common interface so all methods are interchangeable via config only (no code changes to swap).

## Phase 4 — Quality, Robustness & Presentation Enhancements
- Improve dedup robustness (handle site structure changes, retries/backoff on request failures, handle articles with missing/partial content gracefully).
- Add richer post presentation: tag/category pages, keyword-based tagging across posts, "related articles" or archive/index views.
- Add lightweight tests for the crawler (HTML fixture-based parsing tests) and extraction module (known-input/expected-keyword tests).
- Add monitoring/notification on repeated pipeline failures (e.g., workflow failure produces a GitHub Issue or notification).

# Logical Dependency Chain

1. **Foundation — Crawler**: Nothing else can be built or tested without reliably fetching and parsing ETNews articles first. This must work standalone before any extraction logic is written.
2. **Fastest path to visible output — Single-method extraction + Markdown generator**: As soon as the crawler returns article text, wire up the simplest possible keyword+summary method (TF-IDF/TextRank, no external API dependency) directly into the Markdown generator. This gets a real, visible blog post rendering locally as early as possible, validating the entire content shape (front matter, template, dedup) before investing in fancier NLP methods.
3. **Dedup/state tracking**: Must exist before automation is turned on (Phase 2), otherwise scheduled runs will duplicate posts. Build it right after the generator, test it via repeated local runs.
4. **Automation — GitHub Actions workflow**: Once the local script reliably produces correct, deduplicated posts, wrap it in a scheduled workflow. This is the point where the project becomes "hands-off," matching the core TODO requirement.
5. **Config-driven method selection**: Only after the pipeline is fully working end-to-end (locally and in CI) should the extraction methods be made pluggable/configurable — swapping in KeyBERT and/or an LLM path. This is additive and doesn't block earlier phases.
6. **Robustness & presentation polish**: Last, since it improves an already-working system rather than being required for it to function at all.

Each phase is atomic (independently testable/runnable) while building directly on the previous phase's output, so the project has a working, deployable pipeline from the end of Phase 2 onward, with later phases purely enhancing quality and flexibility.

# Risks and Mitigations

## Technical Challenges
- **Site structure changes / scraping fragility**: ETNews may change HTML structure, breaking selectors. Mitigation: isolate parsing logic behind clear functions, add fixture-based tests (Phase 4), fail loudly (workflow failure/notification) rather than silently producing empty/garbage posts.
- **Korean NLP tooling setup complexity**: KoNLPy requires a JVM and Korean dictionary data, which can be finicky in CI. Mitigation: pin exact package versions, cache CI dependencies, and keep a non-JVM fallback (TF-IDF via simple tokenization, or the LLM path) available if KoNLPy setup proves unreliable.
- **Duplicate or missed articles**: Timing/pagination issues could cause missed or duplicate articles across runs. Mitigation: maintain an explicit processed-ID state file committed to the repo (source of truth, human-inspectable, diffable) rather than relying on date-window heuristics alone.
- **LLM API cost/availability** (optional path): Adds an external dependency and cost. Mitigation: keep it strictly optional/config-selectable, with the free local methods (TF-IDF/TextRank/KeyBERT) as the default and always-available fallback.

## Figuring Out the MVP
- Risk of over-building the extraction pipeline before confirming the end-to-end flow (crawl → post → deploy) actually works. Mitigation: Phase 1 deliberately picks the simplest extraction method first, deferring KeyBERT/LLM selection to Phase 3, so the full pipeline is proven early with minimal investment.

## Resource Constraints
- **GitHub Actions minutes**: Daily scheduled runs are lightweight (single script, small HTML fetches) and well within free-tier Actions minutes for a public repo.
- **Solo maintainer**: As a single-owner project, prioritize simplicity and low maintenance burden (file-based state, no external database/server) over more "scalable" but heavier architectures.

# Appendix

## Research Findings / References (from TODO.md)
- Keyword extraction candidates: KeyBERT, KoNLPy.
- Summarization candidates: TextRank (e.g., via `sumy`), or TF-IDF-based extraction.
- Static site generator: Jekyll (existing site uses `remote_theme: jekyll/minima`).
- ETNews article URL format: `https://etnews.com/YYYYMMDD000000` (6 digits following as an id).
- ETNews AI/SW section listing: `https://m.etnews.com/news/section.html?id1=04`.

## Technical Specifications
- Existing repo is a Jekyll site (`_config.yml`, `_posts/`, `_layouts/`, `_includes/`, Gemfile) deployed via GitHub Pages.
- No existing crawler/automation code or GitHub Actions workflows currently present in the repo — this is a greenfield build within an established blog project.
- Previous manually-authored posts (`_posts/2024-05-30-growth-log-1.md` through `2025-08-03-growth-log-32.md`) have been removed from the working tree, clearing the way for the new auto-generated post series.
</PRD>
