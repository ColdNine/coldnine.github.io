"""Generate Jekyll-compatible Markdown posts from crawled articles."""

import logging
import os
from datetime import datetime
from typing import List

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


def build_front_matter(
    article: Article,
    keywords: List[str],
    categories: List[str] = ("etnews", "ai-sw"),
    layout: str = "single",
) -> str:
    """Build the YAML front matter block for a post."""
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


def build_body(keywords: List[str], summary: str, source_url: str) -> str:
    """Build the Markdown body: keywords, summary, and source attribution."""
    keyword_line = ", ".join(keywords)
    return (
        f"## Keywords\n{keyword_line}\n\n"
        f"## Summary\n{summary}\n\n"
        "---\n"
        f"*This post was automatically generated from [ETNews AI/SW section]"
        f"({source_url}). [Read original article →]({source_url})*\n"
    )


def generate_post(
    article: Article,
    keywords: List[str],
    summary: str,
    output_dir: str = "_posts",
    categories: List[str] = ("etnews", "ai-sw"),
    layout: str = "single",
) -> str:
    """Generate a Jekyll Markdown post file for `article` and return its path."""
    os.makedirs(output_dir, exist_ok=True)

    filename = build_filename(article)
    filepath = os.path.join(output_dir, filename)

    content = build_front_matter(article, keywords, categories, layout) + "\n" + build_body(
        keywords, summary, article.url
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("Generated post: %s", filepath)
    return filepath


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
    )
    print(path)
    with open(path, encoding="utf-8") as f:
        print(f.read())
