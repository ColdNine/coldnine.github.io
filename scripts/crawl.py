"""Crawler for ETNews AI/SW section articles.

Discovers article IDs by paginating through the section's AJAX listing
endpoint (the same one the site's own "더보기"/load-more button uses), then
retrieves full article content (title, published date, body text) for each.
Paginating rather than reading only the single visible listing snapshot
ensures articles aren't missed on high-volume days, when older not-yet-processed
articles could otherwise be pushed off that snapshot before the next crawl.
"""

import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE_URL = "https://m.etnews.com"
LISTING_AJAX_URL = f"{BASE_URL}/static/php/ajax_content.php"
ARTICLE_ID_PATTERN = re.compile(r"^(\d{8})(\d{6})$")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15
MAX_LISTING_PAGES = 20  # safety cap on pagination depth regardless of lookback_days


@dataclass
class Article:
    """A single crawled ETNews article: metadata plus full body text."""

    id: str
    url: str
    title: str
    published_at: str
    raw_text: str
    section: str = "AI/SW"


def _request_with_retry(
    session: requests.Session, method: str, url: str, **kwargs
) -> requests.Response:
    """Make an HTTP request with exponential backoff retry on failure."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = session.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            wait = 2 ** attempt
            logger.warning(
                "Request failed (attempt %d/%d) for %s: %s. Retrying in %ds.",
                attempt + 1, MAX_RETRIES, url, exc, wait,
            )
            time.sleep(wait)
    raise last_exc


def _get_with_retry(session: requests.Session, url: str) -> requests.Response:
    """GET a URL with exponential backoff retry on failure."""
    return _request_with_retry(session, "GET", url)


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _extract_section_id(section_url: str) -> str:
    """Extract the `id1` query parameter (section code, e.g. "04") from a section URL."""
    query = parse_qs(urlparse(section_url).query)
    values = query.get("id1")
    if not values:
        raise ValueError(f"Could not find id1= section parameter in {section_url!r}")
    return values[0]


def _fetch_listing_page(
    session: requests.Session, section_id: str, page: int
) -> List[Tuple[str, str]]:
    """Fetch one page of the section listing via the site's load-more AJAX endpoint.

    Returns a list of (article_id, published_at) tuples for that page, newest first.
    """
    response = _request_with_retry(
        session, "POST", LISTING_AJAX_URL,
        data={"kwd": "", "page": page, "id1": section_id, "serial": "", "id": "", "sort": "1"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    soup = BeautifulSoup(response.text, "xml")
    results = []
    for item in soup.find_all("item"):
        art_code = item.find("art_code")
        publish_date = item.find("publish_date")
        if art_code and art_code.text and ARTICLE_ID_PATTERN.match(art_code.text.strip()):
            results.append((art_code.text.strip(), (publish_date.text.strip() if publish_date else "")))
    return results


def _discover_article_ids(
    session: requests.Session, section_id: str, lookback_days: int
) -> List[str]:
    """Paginate the listing endpoint, collecting article IDs within the lookback window."""
    cutoff = datetime.now() - timedelta(days=lookback_days)
    article_ids: List[str] = []
    seen = set()

    for page in range(1, MAX_LISTING_PAGES + 1):
        try:
            page_items = _fetch_listing_page(session, section_id, page)
        except requests.RequestException as exc:
            logger.error("Failed to fetch listing page %d: %s", page, exc)
            break

        if not page_items:
            logger.info("No more items at page %d, stopping pagination", page)
            break

        reached_cutoff = False
        for article_id, published_at in page_items:
            if article_id in seen:
                continue
            seen.add(article_id)
            article_ids.append(article_id)

            try:
                if datetime.strptime(published_at, "%Y-%m-%d %H:%M") < cutoff:
                    reached_cutoff = True
            except ValueError:
                pass  # unparseable date: keep the article, don't use it to end pagination

        if reached_cutoff:
            logger.info("Reached %d-day lookback cutoff at listing page %d", lookback_days, page)
            break
    else:
        logger.warning(
            "Hit MAX_LISTING_PAGES=%d cap before reaching lookback cutoff", MAX_LISTING_PAGES
        )

    return article_ids


def _parse_article_detail(html: str, article_id: str) -> Article:
    """Parse an article detail page into an Article record."""
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find(id="article_title_h2")
    if title_tag is None:
        og_title = soup.find("meta", property="og:title")
        title = og_title["content"].strip() if og_title else ""
    else:
        title = title_tag.get_text(strip=True)

    published_at = ""
    time_tags = soup.select(".timewrap .time time")
    for tag in time_tags:
        text = tag.get_text(strip=True)
        if "발행일" in text:
            published_at = text.split(":", 1)[-1].strip()
            break
    if not published_at and time_tags:
        published_at = time_tags[0].get_text(strip=True).split(":", 1)[-1].strip()

    body_div = soup.find(id="articleBody")
    raw_text = ""
    if body_div is not None:
        for tag in body_div.find_all(["script", "style", "figure", "iframe", "ins"]):
            tag.decompose()
        raw_text = body_div.get_text(separator="\n", strip=True)

    return Article(
        id=article_id,
        url=urljoin(BASE_URL, f"/{article_id}"),
        title=title,
        published_at=published_at,
        raw_text=raw_text,
    )


def crawl_etnews_section(
    section_url: str, lookback_days: int = 7, skip_ids: Optional[set] = None
) -> List[Article]:
    """Crawl the given ETNews section URL and return all discovered articles.

    Paginates the listing until articles older than `lookback_days` are reached
    (or MAX_LISTING_PAGES is hit), so articles aren't missed on high-volume days.
    IDs in `skip_ids` (e.g. already-processed articles) are skipped before the
    detail-page fetch, so repeat daily runs don't re-fetch known articles.
    """
    session = _make_session()
    section_id = _extract_section_id(section_url)

    logger.info("Discovering articles for section id1=%s (lookback=%dd)", section_id, lookback_days)
    article_ids = _discover_article_ids(session, section_id, lookback_days)
    logger.info("Found %d article(s) within lookback window", len(article_ids))

    if not article_ids:
        raise RuntimeError(
            "No articles discovered in listing - possible site structure change or network issue"
        )

    if skip_ids:
        before = len(article_ids)
        article_ids = [a for a in article_ids if a not in skip_ids]
        logger.info("Skipping %d already-processed article(s)", before - len(article_ids))

    articles: List[Article] = []
    for article_id in article_ids:
        detail_url = urljoin(BASE_URL, f"/{article_id}")
        try:
            detail_response = _get_with_retry(session, detail_url)
        except requests.RequestException as exc:
            logger.error("Failed to fetch article %s: %s", article_id, exc)
            continue
        article = _parse_article_detail(detail_response.text, article_id)
        logger.info("Parsed article %s: %s", article_id, article.title)
        articles.append(article)

    return articles


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    section = f"{BASE_URL}/news/section.html?id1=04"
    result = crawl_etnews_section(section)
    print(f"Crawled {len(result)} articles")
    for a in result[:3]:
        print(f"- [{a.id}] {a.title} ({a.published_at}) -> {len(a.raw_text)} chars")
