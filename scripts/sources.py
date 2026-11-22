"""Generic crawler for the non-ETNews sources (ZDNet Korea, Digital Times, Digital Daily,
DailySecu, BoanNews).

Each site is described by a SiteProfile: how to find article links on a section listing
(an HTML page or an RSS feed), how to build an article's canonical URL from its native ID,
and where the article body lives. Title and publish date are read from the standard
`og:title` / `article:published_time` meta tags that all of these sites emit, with
per-site fallbacks.

ETNews keeps its dedicated crawler in crawl.py (it uses a site-specific AJAX listing
endpoint), and run_daily.py dispatches between the two.

Article IDs produced here are namespaced as "<source>-<native id>" (e.g.
"zdnet-20261121072639") so they can never collide with each other or with the bare
ETNews IDs already stored in data/processed_articles.json.
"""

import html
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup

from crawl import Article, USER_AGENT

logger = logging.getLogger(__name__)

DETAIL_FETCH_DELAY = 0.3  # seconds between article fetches, to stay polite to each site
OLD_STREAK_TO_STOP = 2  # consecutive past-lookback articles that end a listing crawl

# "2026-11-22T08:55:57+09:00", "2026-11-22 [07:27:57]", "2026.11.21 15:15", ...
_DATE_PATTERN = re.compile(r"(\d{4})[-./](\d{1,2})[-./](\d{1,2})\D{1,4}(\d{1,2}):(\d{2})")


@dataclass(frozen=True)
class SiteProfile:
    """Site-specific parsing rules for one news source."""

    key: str
    listing: str  # "html" (section listing page) or "rss" (feed)
    id_pattern: str  # regex applied to article hrefs; group(1) is the native article ID
    article_url: str  # format string with {id} -> canonical article URL
    body_selectors: Tuple[str, ...]
    # CSS selector scoping the section's main article list, so sidebar widgets
    # ("많이 본 기사", "최신뉴스" carousels, ...) on the listing page are ignored.
    # If it matches several elements, the last one is used.
    list_selector: str = ""
    title_suffixes: Tuple[str, ...] = ()
    date_meta: Tuple[str, ...] = ("article:published_time", "og:article:published_time", "pubDate")
    strip_selectors: Tuple[str, ...] = (
        "script", "style", "figure", "figcaption", "iframe", "ins", "table",
        "noscript", "button", ".ad", "[class*='banner']",
    )


PROFILES = {
    "zdnet": SiteProfile(
        key="zdnet",
        listing="html",
        list_selector=".news_box",
        id_pattern=r"/view/\?no=(\d+)",
        article_url="https://zdnet.co.kr/view/?no={id}",
        body_selectors=("#articleBody", "div[id^='content-']", ".view_cont"),
    ),
    "dtimes": SiteProfile(
        key="dtimes",
        listing="html",
        list_selector=".section-news-middle .left-area",
        id_pattern=r"/article/(\d+)",
        article_url="https://www.dt.co.kr/article/{id}",
        body_selectors=("#article-body", ".article-body", ".view"),
    ),
    "ddaily": SiteProfile(
        key="ddaily",
        listing="html",
        list_selector="#section_list",
        id_pattern=r"/page/view/(\d+)",
        article_url="https://www.ddaily.co.kr/page/view/{id}",
        body_selectors=(".article_content", "#article_content"),
    ),
    "dailysecu": SiteProfile(
        key="dailysecu",
        listing="html",
        list_selector="ul.altlist-webzine",
        id_pattern=r"articleView\.html\?idxno=(\d+)",
        article_url="https://www.dailysecu.com/news/articleView.html?idxno={id}",
        body_selectors=("#article-view-content-div",),
        title_suffixes=(" - 데일리시큐",),
    ),
    # BoanNews' HTML listing ignores both the section and page query parameters
    # (always returns the same "전체" snapshot), so its per-section RSS feeds are used.
    "boannews": SiteProfile(
        key="boannews",
        listing="rss",
        id_pattern=r"articleView\.html\?idxno=(\d+)",
        article_url="https://www.boannews.com/news/articleView.html?idxno={id}",
        body_selectors=("#article-view-content-div",),
        title_suffixes=(" - 보안뉴스",),
    ),
}


@dataclass
class HttpClient:
    """requests.Session wrapper with timeout + exponential-backoff retries."""

    timeout: float = 15
    max_retries: int = 3
    session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self):
        self.session.headers.update({"User-Agent": USER_AGENT})

    def get(self, url: str) -> requests.Response:
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_exc = exc
                wait = 2 ** attempt
                logger.warning(
                    "Request failed (attempt %d/%d) for %s: %s. Retrying in %ds.",
                    attempt + 1, self.max_retries, url, exc, wait,
                )
                time.sleep(wait)
        raise last_exc


def normalize_date(value: str) -> str:
    """Normalize any "YYYY-MM-DD..HH:MM"-ish string to "YYYY-MM-DD HH:MM" ("" if unparseable)."""
    match = _DATE_PATTERN.search(value or "")
    if not match:
        return ""
    year, month, day, hour, minute = (int(g) for g in match.groups())
    try:
        return datetime(year, month, day, hour, minute).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return ""


def _is_older_than(published_at: str, cutoff: datetime) -> bool:
    try:
        return datetime.strptime(published_at, "%Y-%m-%d %H:%M") < cutoff
    except ValueError:
        return False  # unparseable: don't let it end pagination


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", property=name) or soup.find("meta", attrs={"name": name})
    return (tag.get("content") or "").strip() if tag else ""


def extract_listing_ids(profile: SiteProfile, html_text: str) -> List[str]:
    """Return native article IDs from a section listing page, in page order, deduplicated."""
    soup = BeautifulSoup(html_text, "lxml")
    # Last match wins: e.g. ZDNet's page 1 has a "인기뉴스" .news_box before the
    # "최신 뉴스" one that holds the real chronological listing.
    matches = soup.select(profile.list_selector) if profile.list_selector else [soup]
    scope = matches[-1] if matches else None
    if scope is None:
        logger.warning("[%s] list container %r not found on listing page", profile.key, profile.list_selector)
        return []
    pattern = re.compile(profile.id_pattern)
    ids: List[str] = []
    for a in scope.find_all("a", href=True):
        match = pattern.search(a["href"])
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def extract_rss_items(profile: SiteProfile, xml_text: str) -> List[Tuple[str, str]]:
    """Return (native article ID, normalized pubDate) tuples from an RSS feed, in feed order."""
    soup = BeautifulSoup(xml_text, "xml")
    pattern = re.compile(profile.id_pattern)
    items: List[Tuple[str, str]] = []
    for item in soup.find_all("item"):
        link = item.find("link")
        match = pattern.search(link.get_text(strip=True) if link else "")
        if not match:
            continue
        pub = item.find("pubDate")
        items.append((match.group(1), normalize_date(pub.get_text() if pub else "")))
    return items


def parse_article(profile: SiteProfile, html_content, native_id: str) -> Article:
    """Parse an article detail page into an Article (source/section fields filled by caller)."""
    soup = BeautifulSoup(html_content, "lxml")

    title = html.unescape(_meta(soup, "og:title"))
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    for suffix in profile.title_suffixes:
        if title.endswith(suffix):
            title = title[: -len(suffix)]
    title = title.strip()

    published_at = ""
    for name in profile.date_meta:
        published_at = normalize_date(_meta(soup, name))
        if published_at:
            break

    raw_text = ""
    for selector in profile.body_selectors:
        body = soup.select_one(selector)
        if body is None:
            continue
        for tag in body.select(", ".join(profile.strip_selectors)):
            tag.decompose()
        raw_text = body.get_text(separator="\n", strip=True)
        if raw_text:
            break

    return Article(
        id=f"{profile.key}-{native_id}",
        url=profile.article_url.format(id=native_id),
        title=title,
        published_at=published_at,
        raw_text=raw_text,
        source=profile.key,
    )


def _fetch_article(client: HttpClient, profile: SiteProfile, native_id: str) -> Optional[Article]:
    url = profile.article_url.format(id=native_id)
    try:
        response = client.get(url)
    except requests.RequestException as exc:
        logger.error("[%s] Failed to fetch article %s: %s", profile.key, url, exc)
        return None
    finally:
        time.sleep(DETAIL_FETCH_DELAY)
    article = parse_article(profile, response.content, native_id)
    if not article.title or not article.raw_text:
        logger.warning(
            "[%s] Article %s parsed without %s - skipping (possible layout change)",
            profile.key, url, "title" if not article.title else "body text",
        )
        return None
    logger.info("[%s] Parsed article %s: %s", profile.key, article.id, article.title)
    return article


def _crawl_html_listing(
    client: HttpClient, profile: SiteProfile, listing_url: str, cutoff: datetime,
    skip_ids: set, max_pages: int,
) -> List[Article]:
    paginated = "{page}" in listing_url
    seen: set = set()
    articles: List[Article] = []

    for page in range(1, (max_pages if paginated else 1) + 1):
        url = listing_url.format(page=page) if paginated else listing_url
        response = client.get(url)
        native_ids = extract_listing_ids(profile, response.content)

        if not native_ids:
            if page == 1:
                raise RuntimeError(
                    f"No articles found on {url} - possible site structure change or network issue"
                )
            logger.info("[%s] No items at listing page %d, stopping pagination", profile.key, page)
            break

        new_ids = [
            n for n in native_ids
            if n not in seen and f"{profile.key}-{n}" not in skip_ids
        ]
        seen.update(native_ids)
        if not new_ids:
            logger.info("[%s] Listing page %d has no unprocessed articles, caught up", profile.key, page)
            break

        # Listings are newest-first, so after OLD_STREAK_TO_STOP consecutive articles
        # past the lookback window everything further down (and on deeper pages) is
        # older still - stop instead of re-fetching the same stale articles every day.
        # (A streak rather than the first hit, so one pinned/featured old story at the
        # top of a listing doesn't end the crawl.)
        old_streak = 0
        for native_id in new_ids:
            article = _fetch_article(client, profile, native_id)
            if article is None:
                continue
            if _is_older_than(article.published_at, cutoff):
                old_streak += 1
                if old_streak >= OLD_STREAK_TO_STOP:
                    break
                continue
            old_streak = 0
            articles.append(article)

        if old_streak >= OLD_STREAK_TO_STOP:
            logger.info("[%s] Reached lookback cutoff at listing page %d", profile.key, page)
            break
    else:
        if paginated:
            logger.info("[%s] Stopped at max_pages=%d", profile.key, max_pages)

    return articles


def _crawl_rss(
    client: HttpClient, profile: SiteProfile, feed_url: str, cutoff: datetime, skip_ids: set,
) -> List[Article]:
    response = client.get(feed_url)
    items = extract_rss_items(profile, response.content)
    if not items:
        raise RuntimeError(f"No items in RSS feed {feed_url} - possible feed change or network issue")

    articles: List[Article] = []
    for native_id, published_at in items:
        if f"{profile.key}-{native_id}" in skip_ids or _is_older_than(published_at, cutoff):
            continue
        article = _fetch_article(client, profile, native_id)
        if article:
            article.published_at = article.published_at or published_at
            articles.append(article)
    return articles


def crawl_source_section(
    source_key: str,
    listing_url: str,
    lookback_days: int = 7,
    skip_ids: Optional[Sequence[str]] = None,
    max_pages: int = 3,
    request_timeout: float = 15,
    max_retries: int = 3,
) -> List[Article]:
    """Crawl one section of a non-ETNews source and return its not-yet-processed articles.

    `listing_url` is either an HTML section listing (with an optional `{page}`
    placeholder for pagination) or an RSS feed URL, depending on the source's profile.
    Raises RuntimeError if the listing yields no articles at all (likely breakage).
    """
    if source_key not in PROFILES:
        raise ValueError(f"Unknown source {source_key!r} (known: {sorted(PROFILES)})")
    profile = PROFILES[source_key]
    client = HttpClient(timeout=request_timeout, max_retries=max_retries)
    cutoff = datetime.now() - timedelta(days=lookback_days)
    skip = set(skip_ids or ())

    if profile.listing == "rss":
        return _crawl_rss(client, profile, listing_url, cutoff, skip)
    return _crawl_html_listing(client, profile, listing_url, cutoff, skip, max_pages)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    key, url = sys.argv[1], sys.argv[2]
    result = crawl_source_section(key, url, lookback_days=1, max_pages=1)
    print(f"Crawled {len(result)} articles")
    for a in result[:5]:
        print(f"- [{a.id}] {a.title} ({a.published_at}) -> {len(a.raw_text)} chars")
