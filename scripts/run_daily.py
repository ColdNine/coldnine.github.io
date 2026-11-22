"""Main entry point: crawl every configured news source, extract, generate posts, track state.

Sources and their sections come from config.yml's `sources:` block (ETNews, ZDNet Korea,
Digital Times, Digital Daily, DailySecu, BoanNews). A failure in one source is logged and
the others still run; the process only exits non-zero if *every* selected source failed.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from config import load_config
from crawl import Article, crawl_etnews_section
from extract import extract_keywords_tfidf, summarize_textrank
from generate_post import generate_post, prune_expired_posts
from sources import crawl_source_section
from state import load_state, save_state, mark_processed, filter_unprocessed, touch_last_run

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure root logging to print INFO+ messages to stdout (visible in Actions logs)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )


def _actions_warning(message: str) -> None:
    """Surface `message` as a GitHub Actions warning annotation (no-op locally)."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::warning::{message}", flush=True)


def _within_lookback(article, lookback_days: int) -> bool:
    """Return True if `article.published_at` is within the lookback window (or unparseable)."""
    try:
        published = datetime.strptime(article.published_at.strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return True  # don't drop articles we can't confidently date-filter
    return datetime.now() - published <= timedelta(days=lookback_days)


def _section_page_url(section: dict) -> str:
    """Human-facing section page for post attribution (listing URL with page 1 if templated)."""
    return section.get("page_url") or section["url"].replace("{page}", "1")


def crawl_section(source_key: str, section: dict, crawler_cfg: dict, skip_ids: set) -> List[Article]:
    """Crawl one configured section of one source."""
    if source_key == "etnews":
        return crawl_etnews_section(
            section["url"], lookback_days=crawler_cfg["lookback_days"], skip_ids=skip_ids,
        )
    return crawl_source_section(
        source_key,
        section["url"],
        lookback_days=crawler_cfg["lookback_days"],
        skip_ids=skip_ids,
        max_pages=crawler_cfg["max_pages"],
        request_timeout=crawler_cfg["request_timeout"],
        max_retries=crawler_cfg["max_retries"],
    )


def crawl_source(source_key: str, source: dict, crawler_cfg: dict, state: dict) -> List[Article]:
    """Crawl every section of a source, tagging articles with source/section metadata.

    An article listed in several sections is kept once, under the first section listed
    in config.yml. Raises RuntimeError only if every section of the source failed.
    """
    skip_ids = set(state.get("processed_ids", []))
    articles: List[Article] = []
    seen_ids: set = set()
    failed_sections = []

    for section in source["sections"]:
        try:
            crawled = crawl_section(source_key, section, crawler_cfg, skip_ids | seen_ids)
        except Exception as exc:
            logger.error("[%s/%s] Crawl failed: %s", source_key, section["slug"], exc)
            _actions_warning(f"{source_key}/{section['slug']} crawl failed: {exc}")
            failed_sections.append(section["slug"])
            continue

        for article in crawled:
            if article.id in seen_ids:
                continue
            seen_ids.add(article.id)
            article.source = source_key
            article.source_label = source.get("label", source_key)
            article.section = section["name"]
            article.section_slug = section["slug"]
            article.section_url = _section_page_url(section)
            articles.append(article)
        logger.info("[%s/%s] %d new article(s)", source_key, section["slug"], len(crawled))

    if len(failed_sections) == len(source["sections"]):
        raise RuntimeError(f"all sections failed ({', '.join(failed_sections)})")
    return articles


def process_articles(articles: List[Article], config: dict, state: dict, dry_run: bool) -> tuple:
    """Extract keywords/summary and write a post for each article. Returns (processed, failed)."""
    keyword_count = config["extraction"]["keyword_count"]
    summary_sentences = config["extraction"]["summary_sentences"]
    layout = config["post"]["layout"]
    processed = failed = 0

    for article in articles:
        try:
            keywords = extract_keywords_tfidf(article.raw_text, n_keywords=keyword_count)
            summary = summarize_textrank(article.raw_text, sentence_count=summary_sentences)

            if dry_run:
                logger.info(
                    "[dry-run] Would generate post for %s: title=%r keywords=%s summary_len=%d",
                    article.id, article.title, keywords, len(summary),
                )
            else:
                generate_post(article, keywords, summary, layout=layout)
                mark_processed(article.id, state)
            processed += 1
        except Exception as exc:
            logger.error("Failed to process article %s: %s", article.id, exc)
            failed += 1
    return processed, failed


def _select_sources(
    sources: dict, only: Optional[Iterable[str]], exclude: Optional[Iterable[str]]
) -> dict:
    only, exclude = set(only or ()), set(exclude or ())
    unknown = (only | exclude) - set(sources)
    if unknown:
        raise ValueError(
            f"Unknown/disabled source(s) {sorted(unknown)} (configured: {sorted(sources)})"
        )
    return {
        key: src for key, src in sources.items()
        if (not only or key in only) and key not in exclude
    }


def run(
    dry_run: bool = False,
    only_sources: Optional[Iterable[str]] = None,
    exclude_sources: Optional[Iterable[str]] = None,
) -> int:
    """Run the full pipeline once. Returns 0 if at least one source succeeded, 1 otherwise."""
    config = load_config()
    state_file = config["state"]["file_path"]
    state = load_state(state_file)
    crawler_cfg = config["crawler"]
    lookback_days = crawler_cfg["lookback_days"]

    sources = _select_sources(config["sources"], only_sources, exclude_sources)

    # Rolling retention: drop auto-generated posts whose article date has aged out.
    # Runs before crawling and independently of crawl success, so it still happens on
    # days when a source is down. Already-processed IDs stay in the state file, so a
    # pruned article can never be re-posted.
    prune_expired_posts(config["post"]["retention_days"] or 0, dry_run=dry_run)

    logger.info("Sources to crawl: %s", ", ".join(sources) or "(none)")

    succeeded, failed_sources = [], []
    total_processed = total_failed = 0

    for source_key, source in sources.items():
        try:
            articles = crawl_source(source_key, source, crawler_cfg, state)
        except Exception as exc:
            logger.critical("[%s] Crawl failed entirely: %s", source_key, exc)
            _actions_warning(f"{source_key} crawl failed entirely: {exc}")
            failed_sources.append(source_key)
            continue
        succeeded.append(source_key)

        articles = [a for a in articles if _within_lookback(a, lookback_days)]
        new_articles = filter_unprocessed(articles, state)
        logger.info("[%s] %d new article(s) to process", source_key, len(new_articles))
        if not new_articles:
            continue

        processed, failed = process_articles(new_articles, config, state, dry_run)
        total_processed += processed
        total_failed += failed
        if not dry_run:
            save_state(state, state_file)  # persist per source so one crash can't lose others

    if not dry_run and succeeded:
        touch_last_run(state)
        save_state(state, state_file)

    logger.info(
        "Pipeline %s: sources ok=%s failed=%s, articles processed=%d failed=%d",
        "dry run complete" if dry_run else "completed",
        succeeded or "none", failed_sources or "none", total_processed, total_failed,
    )
    if sources and not succeeded:
        return 1
    return 0


def main() -> int:
    """CLI entry point: parse args, set up logging, and run the pipeline once."""
    parser = argparse.ArgumentParser(
        description="Crawl the configured IT news sources and generate daily digest posts"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run the full pipeline without writing post files or updating state",
    )
    parser.add_argument(
        "--source", action="append", metavar="KEY",
        help="Only crawl this source key (repeatable), e.g. --source zdnet",
    )
    parser.add_argument(
        "--exclude-source", action="append", metavar="KEY",
        help="Skip this source key (repeatable), e.g. --exclude-source etnews",
    )
    args = parser.parse_args()

    setup_logging()
    return run(dry_run=args.dry_run, only_sources=args.source, exclude_sources=args.exclude_source)


if __name__ == "__main__":
    sys.exit(main())
