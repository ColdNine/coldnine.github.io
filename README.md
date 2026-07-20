# coldnine.github.io — Daily ETNews AI/SW Digest

A Jekyll blog (GitHub Pages) that automatically publishes a daily keyword +
summary digest of Korean IT news from [ETNews](https://m.etnews.com)'s AI/SW
section. A scheduled GitHub Actions workflow crawls new articles, extracts
keywords and a summary, and commits generated Markdown posts — no manual
intervention required.

## Architecture

```
GitHub Actions (daily cron)
        │
        ▼
scripts/run_daily.py  (orchestrator)
        │
        ├─► scripts/crawl.py         crawl ETNews AI/SW section listing + article pages
        ├─► scripts/state.py         filter out already-processed article IDs
        ├─► scripts/extract.py       TF-IDF keywords (KoNLPy) + TextRank summary (sumy)
        ├─► scripts/generate_post.py write Jekyll post to _posts/YYYY-MM-DD-<slug>.md
        └─► scripts/state.py         record processed IDs, update data/processed_articles.json
        │
        ▼
git commit + push  →  GitHub Pages rebuilds the site automatically
```

All tunable parameters (keyword count, summary length, crawl lookback, etc.)
live in [`config.yml`](config.yml).

## Setup

**Prerequisites:**
- Python 3.11+
- A JDK (Java 9+) — required by [KoNLPy](https://konlpy.org/)'s Korean tokenizer
- Ruby + Bundler (for local Jekyll preview)

**Install:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

bundle install  # for local Jekyll preview
```

**Configuration:** edit [`config.yml`](config.yml) to change the crawl target,
keyword/summary tuning, or post metadata — see the
[Configuration Reference](#configuration-reference) below.

## Local Testing

Run the full pipeline (crawls live ETNews, writes real posts, updates state):

```bash
python scripts/run_daily.py
```

Dry run — crawls and extracts, but writes no files and doesn't touch state:

```bash
python scripts/run_daily.py --dry-run
```

Preview the site with any generated posts:

```bash
bundle exec jekyll serve
```

> **Note:** comments (Talkyard) only render when `jekyll.environment == 'production'`
> (a minimal-mistakes theme condition). Local `serve`/`build` runs in `development`
> mode by default, so comments won't show up unless you build with:
> ```bash
> JEKYLL_ENV=production bundle exec jekyll build
> ```
> The production GitHub Actions deploy already sets this, so comments work fine live.

Run twice in a row to confirm deduplication: the second run should log
`0 new article(s) to process` since [`data/processed_articles.json`](data/processed_articles.json)
tracks already-processed article IDs.

## GitHub Actions

[`​.github/workflows/daily-post.yml`](.github/workflows/daily-post.yml) runs the
pipeline automatically:

- **Schedule:** daily at 0 UTC (9 AM KST)
- **Manual trigger:** GitHub repo → Actions tab → "Daily ETNews Digest" → **Run workflow**
- **Logs:** each run's steps (crawl, extract, generate, commit) are visible under Actions → the run → job logs
- The workflow only commits when there are actual changes (`git diff --staged --quiet`)
- Because the commit is pushed using the default `GITHUB_TOKEN`, it won't trigger
  [`pages-deploy.yml`](.github/workflows/pages-deploy.yml) on its own — GitHub blocks
  `GITHUB_TOKEN`-authored pushes from cascading into other workflow runs, as an
  anti-recursion safeguard. `workflow_dispatch` calls are exempt from that rule, so
  after a successful commit the job explicitly dispatches the deploy workflow itself
  (`gh workflow run pages-deploy.yml`), which needs the `actions: write` permission
  granted in the job

### Network access via Cloudflare WARP

ETNews blocks requests from GitHub-hosted runners at the network level (a raw TCP
connect timeout, not an HTTP error) — almost certainly because GitHub-hosted runners
share Microsoft Azure's public IP ranges (7,000+ CIDR blocks, published at
[`api.github.com/meta`](https://api.github.com/meta) under `"actions"`), and sites
that geo/cloud-fence tend to block that whole range rather than individual addresses.
Retrying or re-running the job doesn't help, since every run lands somewhere in that
same blocked range.

To work around this, the "Set up Cloudflare WARP" step in `daily-post.yml` installs
and connects to [Cloudflare WARP](https://developers.cloudflare.com/warp-client/) — a
free consumer VPN (WireGuard-based, no account or payment required) — right before the
crawl step, giving it a non-Azure exit IP. It logs the Cloudflare trace (`warp=on`
check), the new egress IP, and a live reachability probe against the exact ETNews
endpoint that previously timed out, so a failed run makes it obvious whether WARP
itself failed to connect or connected fine but was blocked anyway. WARP is
disconnected again immediately after the crawl (`if: always()`), so later steps (git
push, the `gh workflow run` dispatch) keep using the runner's normal network path.

**Known limitation:** the free WARP tier doesn't support picking an exit region, so
traffic doesn't necessarily route through Korea, and Cloudflare's IP range could
itself eventually get flagged by ETNews the same way Azure's was. If crawls start
timing out again with `warp=on` and a real Cloudflare egress IP in the log, that's the
likely cause — see [Troubleshooting](#troubleshooting).

## Configuration Reference

| Key | Description | Default |
|---|---|---|
| `crawler.section_url` | ETNews section listing URL to crawl | AI/SW section |
| `crawler.lookback_days` | How far back (in days) the crawler paginates the section listing; articles older than this are skipped. Also the depth the crawler walks back on each run, so late/backlogged articles from prior days are never missed regardless of publishing volume | `7` |
| `crawler.request_timeout` | HTTP request timeout (seconds) | `15` |
| `crawler.max_retries` | Retry attempts per HTTP request | `3` |
| `extraction.keyword_method` | Keyword extraction method (`tfidf`; `keybert`/`llm` reserved for future use) | `tfidf` |
| `extraction.keyword_count` | Number of keywords per post | `7` |
| `extraction.summarization_method` | Summarization method (`textrank`; `llm` reserved for future use) | `textrank` |
| `extraction.summary_sentences` | Number of sentences in the summary | `4` |
| `post.output_mode` | `per_article` (one post per article); `daily_digest` reserved for future use | `per_article` |
| `post.categories` | Jekyll post categories | `[etnews, ai-sw]` |
| `post.layout` | Jekyll layout name | `post` |
| `state.file_path` | Path to the processed-article-ID tracking file | `data/processed_articles.json` |

If `config.yml` is missing, the pipeline falls back to these defaults. Invalid
values (e.g. an unrecognized `keyword_method`) raise a clear error at startup.

## PWA

The site is installable as a Progressive Web App (Add to Home Screen / desktop install):

- `manifest.webmanifest` — app name, icons, theme color. `_config.yml`'s `pwa_short_name`
  controls the home-screen label (keep it short, ~12 characters).
- `sw.js` — service worker: network-first for pages (with `offline.html` as the fallback
  when there's no cached copy and no connection), cache-first for static assets.
- `assets/icons/` — placeholder app icons (192/512/512-maskable/apple-touch). Swap these
  for real branding whenever you have a logo — same filenames, same sizes.
- Both files have `layout: null` in front matter so they render as raw JSON/JS instead
  of getting wrapped in the theme's page template (which the site's `defaults:` scope
  would otherwise apply to any page-like file).
- Bump `CACHE_VERSION` in `sw.js` after any change to precached assets so returning
  visitors' browsers drop the old cache instead of serving stale files.

## Troubleshooting

**KoNLPy / JVM errors** (`RuntimeError: Failed to initialize KoNLPy Okt tokenizer`):
KoNLPy needs a JDK with Java 9+. Java 8 is too old and will fail with
`Java version too old`. Install a newer JDK and make sure it's first on `PATH`
(check with `java -version`).

**Crawl / network failures:** `scripts/crawl.py` retries each request up to
`crawler.max_retries` times with exponential backoff. If ETNews' page
structure changes, the crawler may return 0 articles — `run_daily.py` treats
an entirely empty crawl as a critical failure (exit code 1) so this is visible
in the Actions run rather than silently producing nothing.

**Crawl times out only in GitHub Actions, works locally:** ETNews is blocking
GitHub's Azure IP range, not rejecting the request at the HTTP level (see
[Network access via Cloudflare WARP](#network-access-via-cloudflare-warp)). Check the
"Set up Cloudflare WARP" step's log:
- If `warp=on` never appears or the egress IP check fails, WARP itself failed to
  connect — check the `warp-cli status` output printed just above it for the reason.
- If `warp=on` and a real Cloudflare IP show up but the ETNews reachability check still
  times out, ETNews is now blocking Cloudflare's range too, and WARP's free tier can't
  route around it (no exit-region selection without a paid plan). At that point the
  only remaining fix is a self-hosted runner on a non-cloud-datacenter IP.

**State file corruption:** `scripts/state.py` detects invalid JSON in
`data/processed_articles.json`, backs up the corrupt file alongside it
(`*.corrupt.<timestamp>`), and starts fresh rather than crashing the pipeline.

## Future Enhancements

- `extraction.keyword_method: keybert` — embedding-based keyword extraction as an alternative to TF-IDF
- `extraction.summarization_method: llm` / `keyword_method: llm` — LLM-based extraction as a selectable alternative
- `post.output_mode: daily_digest` — one combined post per day instead of one per article
