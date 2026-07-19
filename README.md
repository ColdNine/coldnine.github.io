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

Run twice in a row to confirm deduplication: the second run should log
`0 new article(s) to process` since [`data/processed_articles.json`](data/processed_articles.json)
tracks already-processed article IDs.

## GitHub Actions

[`​.github/workflows/daily-post.yml`](.github/workflows/daily-post.yml) runs the
pipeline automatically:

- **Schedule:** daily at 1 AM UTC (10 AM KST)
- **Manual trigger:** GitHub repo → Actions tab → "Daily ETNews Digest" → **Run workflow**
- **Logs:** each run's steps (crawl, extract, generate, commit) are visible under Actions → the run → job logs
- The workflow only commits when there are actual changes (`git diff --staged --quiet`), and the commit message includes `[skip ci]` to avoid re-triggering itself

## Configuration Reference

| Key | Description | Default |
|---|---|---|
| `crawler.section_url` | ETNews section listing URL to crawl | AI/SW section |
| `crawler.lookback_days` | Skip articles older than this many days | `7` |
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

**State file corruption:** `scripts/state.py` detects invalid JSON in
`data/processed_articles.json`, backs up the corrupt file alongside it
(`*.corrupt.<timestamp>`), and starts fresh rather than crashing the pipeline.

## Future Enhancements

- `extraction.keyword_method: keybert` — embedding-based keyword extraction as an alternative to TF-IDF
- `extraction.summarization_method: llm` / `keyword_method: llm` — LLM-based extraction as a selectable alternative
- `post.output_mode: daily_digest` — one combined post per day instead of one per article
