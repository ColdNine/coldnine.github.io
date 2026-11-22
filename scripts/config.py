"""Loads and validates config.yml, the pipeline's centralized tunable parameters."""

import copy
import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yml"

# Source keys that have a crawler implementation (etnews in crawl.py, the rest in sources.py).
KNOWN_SOURCES = {"etnews", "zdnet", "dtimes", "ddaily", "dailysecu", "boannews"}

DEFAULTS: Dict[str, Any] = {
    "crawler": {
        "lookback_days": 7,
        "request_timeout": 15,
        "max_retries": 3,
        "max_pages": 3,
    },
    "sources": {
        "etnews": {
            "label": "ETNews",
            "sections": [
                {"name": "AI·SW", "slug": "ai-sw",
                 "url": "https://m.etnews.com/news/section.html?id1=04"},
            ],
        },
    },
    "extraction": {
        "keyword_method": "tfidf",
        "keyword_count": 7,
        "summarization_method": "textrank",
        "summary_sentences": 4,
    },
    "post": {
        "output_mode": "per_article",
        "layout": "single",
    },
    "state": {
        "file_path": "data/processed_articles.json",
    },
}

VALID_KEYWORD_METHODS = {"tfidf", "keybert", "llm"}
VALID_SUMMARIZATION_METHODS = {"textrank", "llm"}
VALID_OUTPUT_MODES = {"per_article", "daily_digest"}


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge `override` into a copy of `base`, recursing into nested dicts."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate_sources(sources: dict) -> None:
    if not isinstance(sources, dict) or not sources:
        raise ValueError("sources must be a non-empty mapping of source key -> settings")
    for key, source in sources.items():
        if key not in KNOWN_SOURCES:
            raise ValueError(
                f"Unknown source {key!r} (expected one of {sorted(KNOWN_SOURCES)})"
            )
        sections = (source or {}).get("sections")
        if not isinstance(sections, list) or not sections:
            raise ValueError(f"sources.{key}.sections must be a non-empty list")
        for i, section in enumerate(sections):
            for field in ("name", "slug", "url"):
                if not section.get(field):
                    raise ValueError(f"sources.{key}.sections[{i}] is missing {field!r}")


def _validate(config: dict) -> None:
    """Raise ValueError if config contains invalid values."""
    keyword_method = config["extraction"]["keyword_method"]
    if keyword_method not in VALID_KEYWORD_METHODS:
        raise ValueError(
            f"Invalid extraction.keyword_method: {keyword_method!r} "
            f"(expected one of {sorted(VALID_KEYWORD_METHODS)})"
        )

    summarization_method = config["extraction"]["summarization_method"]
    if summarization_method not in VALID_SUMMARIZATION_METHODS:
        raise ValueError(
            f"Invalid extraction.summarization_method: {summarization_method!r} "
            f"(expected one of {sorted(VALID_SUMMARIZATION_METHODS)})"
        )

    output_mode = config["post"]["output_mode"]
    if output_mode not in VALID_OUTPUT_MODES:
        raise ValueError(
            f"Invalid post.output_mode: {output_mode!r} "
            f"(expected one of {sorted(VALID_OUTPUT_MODES)})"
        )

    if config["extraction"]["keyword_count"] < 1:
        raise ValueError("extraction.keyword_count must be >= 1")
    if config["extraction"]["summary_sentences"] < 1:
        raise ValueError("extraction.summary_sentences must be >= 1")
    if config["crawler"]["lookback_days"] < 1:
        raise ValueError("crawler.lookback_days must be >= 1")
    if config["crawler"]["max_pages"] < 1:
        raise ValueError("crawler.max_pages must be >= 1")

    _validate_sources(config["sources"])


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load config.yml, merging it over defaults. Falls back to defaults if missing.

    `sources` is taken wholesale from the file when present (not deep-merged), so
    removing a source from config.yml really disables it. Sources with
    `enabled: false` are dropped. Raises ValueError on invalid values.
    """
    if not os.path.exists(path):
        logger.warning("Config file %s not found, using defaults", path)
        user_config: dict = {}
    else:
        with open(path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}

    user_sources = user_config.pop("sources", None)
    config = _deep_merge(DEFAULTS, user_config)

    if user_sources is not None:
        config["sources"] = user_sources
    elif config["crawler"].get("section_url"):
        # Legacy single-source config (pre multi-source): crawler.section_url = ETNews section.
        config["sources"]["etnews"]["sections"][0]["url"] = config["crawler"]["section_url"]

    if isinstance(config["sources"], dict):
        config["sources"] = {
            key: source for key, source in config["sources"].items()
            if (source or {}).get("enabled", True)
        }

    _validate(config)
    return config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(load_config())
