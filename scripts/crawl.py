"""Crawler for ETNews AI/SW section articles.

Fetches the section listing page, discovers article links, and retrieves
full article content (title, published date, body text) for each one.
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
BASE_URL = "https://m.etnews.com"
ARTICLE_ID_PATTERN = re.compile(r"^(\d{8})(\d{6})$")
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15


@dataclass
class Article:
    """A single crawled ETNews article: metadata plus full body text."""

    id: str
    url: str
    title: str
    published_at: str
    raw_text: str
    section: str = "AI/SW"


def _get_with_retry(session: requests.Session, url: str) -> requests.Response:
    """GET a URL with exponential backoff retry on failure."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
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


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _extract_article_id(href: str) -> str | None:
    """Return the article ID if href matches the YYYYMMDD + 6-digit pattern."""
    path = href.strip().split("?")[0].rstrip("/")
    candidate = path.rsplit("/", 1)[-1]
    if ARTICLE_ID_PATTERN.match(candidate):
        return candidate
    return None


def _parse_section_listing(html: str) -> List[str]:
    """Parse the section listing page and return unique article IDs found."""
    soup = BeautifulSoup(html, "lxml")
    container = soup.find("ul", id="contents_list") or soup
    ids: List[str] = []
    seen = set()
    for anchor in container.find_all("a", href=True):
        article_id = _extract_article_id(anchor["href"])
        if article_id and article_id not in seen:
            seen.add(article_id)
            ids.append(article_id)
    return ids


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


def crawl_etnews_section(section_url: str) -> List[Article]:
    """Crawl the given ETNews section URL and return all discovered articles."""
    session = _make_session()

    logger.info("Fetching section listing: %s", section_url)
    listing_response = _get_with_retry(session, section_url)
    article_ids = _parse_section_listing(listing_response.text)
    logger.info("Found %d article(s) in section listing", len(article_ids))

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
