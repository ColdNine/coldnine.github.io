"""Main entry point: crawl ETNews AI/SW, extract, generate posts, track state."""

import argparse
import logging
import sys
from datetime import datetime, timedelta

from config import load_config
from crawl import crawl_etnews_section
from extract import extract_keywords_tfidf, summarize_textrank
from generate_post import generate_post
from state import load_state, save_state, mark_processed, filter_unprocessed, touch_last_run

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure root logging to print INFO+ messages to stdout (visible in Actions logs)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )


def _within_lookback(article, lookback_days: int) -> bool:
    """Return True if `article.published_at` is within the lookback window (or unparseable)."""
    try:
        published = datetime.strptime(article.published_at.strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        return True  # don't drop articles we can't confidently date-filter
    return datetime.now() - published <= timedelta(days=lookback_days)


def run(dry_run: bool = False) -> int:
    """Run the full pipeline once. Returns a process exit code (0 success, 1 critical failure)."""
    config = load_config()
    state = load_state(config["state"]["file_path"])

    try:
        articles = crawl_etnews_section(config["crawler"]["section_url"])
    except Exception as exc:
        logger.critical("Crawl failed entirely: %s", exc)
        return 1

    logger.info("Crawled %d articles", len(articles))
    if not articles:
        logger.critical("No articles found in crawl - possible site structure change or network issue")
        return 1

    lookback_days = config["crawler"]["lookback_days"]
    articles = [a for a in articles if _within_lookback(a, lookback_days)]

    new_articles = filter_unprocessed(articles, state)
    logger.info("%d new article(s) to process (%d already processed)", len(new_articles), len(articles) - len(new_articles))

    if not new_articles:
        logger.info("No new articles, exiting")
        return 0

    processed_count = 0
    failed_count = 0
    keyword_count = config["extraction"]["keyword_count"]
    summary_sentences = config["extraction"]["summary_sentences"]
    categories = config["post"]["categories"]
    layout = config["post"]["layout"]

    for article in new_articles:
        try:
            keywords = extract_keywords_tfidf(article.raw_text, n_keywords=keyword_count)
            summary = summarize_textrank(article.raw_text, sentence_count=summary_sentences)

            if dry_run:
                logger.info(
                    "[dry-run] Would generate post for %s: keywords=%s summary_len=%d",
                    article.id, keywords, len(summary),
                )
            else:
                generate_post(article, keywords, summary, categories=categories, layout=layout)
                mark_processed(article.id, state)

            processed_count += 1
        except Exception as exc:
            logger.error("Failed to process article %s: %s", article.id, exc)
            failed_count += 1
            continue

    if dry_run:
        logger.info(
            "Dry run complete: %d would be processed, %d failed", processed_count, failed_count
        )
        return 0

    touch_last_run(state)
    save_state(state, config["state"]["file_path"])
    logger.info(
        "Pipeline completed: crawled=%d processed=%d skipped=%d failed=%d",
        len(articles), processed_count, len(articles) - len(new_articles), failed_count,
    )
    return 0


def main() -> int:
    """CLI entry point: parse args, set up logging, and run the pipeline once."""
    parser = argparse.ArgumentParser(description="Crawl ETNews AI/SW and generate daily digest posts")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run the full pipeline without writing post files or updating state",
    )
    args = parser.parse_args()

    setup_logging()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
