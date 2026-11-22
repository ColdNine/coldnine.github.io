"""Generate Jekyll-compatible Markdown posts from crawled articles."""

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import yaml
from slugify import slugify

from crawl import Article

logger = logging.getLogger(__name__)

MAX_SLUG_LENGTH = 50
TIMEZONE_OFFSET = "+0900"  # matches _config.yml `timezone: Asia/Seoul`


def _parse_published_at(published_at: str) -> datetime:
    """Parse an article's `published_at` string ("YYYY-MM-DD HH:MM") into a datetime."""
    try:
        return datetime.strptime(published_at.strip(), "%Y-%m-%d %H:%M")
    except (ValueError, AttributeError):
        logger.warning(
            "Could not parse published_at %r, falling back to current time", published_at
        )
        return datetime.now()


def build_filename(article: Article) -> str:
    """Build the Jekyll post filename: YYYY-MM-DD-<slug>.md."""
    date = _parse_published_at(article.published_at)
    slug = slugify(article.title, max_length=MAX_SLUG_LENGTH)
    if not slug:
        slug = article.id
    return f"{date.strftime('%Y-%m-%d')}-{slug}.md"


def _unique_filepath(output_dir: str, filename: str, article: Article) -> str:
    """Return a path for `filename` that won't clobber a *different* article's post.

    Two sources can publish the same headline (e.g. a syndicated press release) on the
    same day, which would slugify to the same filename. If the existing file is for the
    same source URL it's simply overwritten (re-run of the same article); otherwise a
    source-key suffix (and, if still taken, the article ID) is appended.
    """
    stem, ext = os.path.splitext(filename)
    candidates = [filename, f"{stem}-{article.source}{ext}", f"{stem}-{article.id}{ext}"]
    for candidate in candidates:
        path = os.path.join(output_dir, candidate)
        if not os.path.exists(path):
            return path
        with open(path, encoding="utf-8") as f:
            if f"source_url: {article.url}\n" in f.read():
                return path
    return os.path.join(output_dir, candidates[-1])


def build_front_matter(
    article: Article,
    keywords: List[str],
    categories: Optional[List[str]] = None,
    layout: str = "single",
) -> str:
    """Build the YAML front matter block for a post.

    Categories default to [<source key>, <section slug>], e.g. [zdnet, computing].
    """
    if categories is None:
        categories = [article.source, article.section_slug]
    date = _parse_published_at(article.published_at)
    data = {
        "layout": layout,
        "title": article.title,
        "date": f"{date.strftime('%Y-%m-%d %H:%M:%S')} {TIMEZONE_OFFSET}",
        "categories": list(categories),
        "tags": keywords,
        "source_url": article.url,
        "auto_generated": True,
    }
    yaml_body = yaml.safe_dump(
        data, allow_unicode=True, sort_keys=False, default_flow_style=None
    ).strip()
    return f"---\n{yaml_body}\n---\n"


def build_body(
    keywords: List[str], summary: str, source_url: str, section_url: str,
    source_label: str = "ETNews", section_name: str = "AI·SW",
) -> str:
    """Build the Markdown body: keywords, summary, and source attribution."""
    keyword_line = ", ".join(keywords)
    return (
        f"## Keywords\n{keyword_line}\n\n"
        f"## Summary\n{summary}\n\n"
        "---\n"
        f"*This post was automatically generated from [{source_label} {section_name} section]"
        f"({section_url}). [Read original article →]({source_url})*\n"
    )


def generate_post(
    article: Article,
    keywords: List[str],
    summary: str,
    output_dir: str = "_posts",
    categories: Optional[List[str]] = None,
    layout: str = "single",
    section_url: Optional[str] = None,
) -> str:
    """Generate a Jekyll Markdown post file for `article` and return its path.

    `categories` and `section_url` default to the article's own source/section fields.
    """
    os.makedirs(output_dir, exist_ok=True)

    filepath = _unique_filepath(output_dir, build_filename(article), article)

    content = build_front_matter(article, keywords, categories, layout) + "\n" + build_body(
        keywords, summary, article.url, section_url or article.section_url,
        source_label=article.source_label, section_name=article.section,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Generated post: %s", filepath)
    return filepath


_FRONT_MATTER_DATE = re.compile(
    r"^date:\s*['\"]?(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2})(?::\d{2})?)?\s*(?:([+-]\d{2}):?(\d{2}))?",
    re.MULTILINE,
)
_FILENAME_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
_AUTO_GENERATED = re.compile(r"^auto_generated:\s*true\s*$", re.MULTILINE | re.IGNORECASE)
_KST = timezone(timedelta(hours=9))


def _post_date(filename: str, text: str) -> Optional[datetime]:
    """Return a post's (timezone-aware) date from its front matter, else from its filename."""
    match = _FRONT_MATTER_DATE.search(text)
    if match:
        day, hm, tz_h, tz_m = match.groups()
        tz = _KST
        if tz_h:
            sign = -1 if tz_h.startswith("-") else 1
            tz = timezone(sign * timedelta(hours=abs(int(tz_h)), minutes=int(tz_m or 0)))
        try:
            return datetime.strptime(f"{day} {hm or '00:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=tz)
        except ValueError:
            pass
    match = _FILENAME_DATE.match(filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=_KST)
        except ValueError:
            pass
    return None


def prune_expired_posts(
    retention_days: int, output_dir: str = "_posts", dry_run: bool = False
) -> List[str]:
    """Delete auto-generated posts whose article date is older than `retention_days`.

    The age is measured from the post's own `date:` (the original article's publish
    date), so every source keeps a rolling window of the last `retention_days` days.
    Only files with `auto_generated: true` are ever deleted - hand-written posts are
    left alone. `retention_days <= 0` disables pruning. Returns the affected paths.
    """
    if retention_days <= 0 or not os.path.isdir(output_dir):
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    expired: List[str] = []
    for filename in sorted(os.listdir(output_dir)):
        if not filename.endswith((".md", ".markdown")):
            continue
        path = os.path.join(output_dir, filename)
        with open(path, encoding="utf-8") as f:
            head = f.read(4096)  # front matter is at the top
        if not _AUTO_GENERATED.search(head):
            continue
        date = _post_date(filename, head)
        if date is None:
            logger.warning("Could not determine date of %s, keeping it", path)
            continue
        if date < cutoff:
            expired.append(path)
            if not dry_run:
                os.remove(path)

    if expired:
        logger.info(
            "%s %d post(s) older than %d day(s) (before %s)",
            "[dry-run] Would delete" if dry_run else "Deleted",
            len(expired), retention_days, cutoff.astimezone(_KST).strftime("%Y-%m-%d %H:%M KST"),
        )
    return expired


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sample_article = Article(
        id="20260719000026",
        url="https://etnews.com/20260719000026",
        title="기업 성장 사다리 된 '서울형 R&D', 사업화까지 잇는다",
        published_at="2026-07-19 09:57",
        raw_text="(원문 생략)",
    )
    path = generate_post(
        sample_article,
        keywords=["서울", "기업", "지원", "사업", "기술"],
        summary="서울형 R&D는 기업 성장과 투자, 실증, 사업화를 연결하는 개방형 혁신 플랫폼으로 진화하고 있다.",
        output_dir="/tmp/generate_post_test",
        section_url="https://m.etnews.com/news/section.html?id1=04",
    )
    print(path)
    with open(path, encoding="utf-8") as f:
        print(f.read())
