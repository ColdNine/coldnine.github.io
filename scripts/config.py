"""Loads and validates config.yml, the pipeline's centralized tunable parameters."""

import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yml"

DEFAULTS: Dict[str, Any] = {
    "crawler": {
        "section_url": "https://m.etnews.com/news/section.html?id1=04",
        "lookback_days": 7,
        "request_timeout": 15,
        "max_retries": 3,
    },
    "extraction": {
        "keyword_method": "tfidf",
        "keyword_count": 7,
        "summarization_method": "textrank",
        "summary_sentences": 4,
    },
    "post": {
        "output_mode": "per_article",
        "categories": ["etnews", "ai-sw"],
        "layout": "post",
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
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _validate(config: dict) -> None:
    """Raise ValueError if config contains invalid enum values."""
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


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """Load config.yml, merging it over defaults. Falls back to defaults if missing.

    Raises ValueError if the (merged) config contains invalid enum values.
    """
    if not os.path.exists(path):
        logger.warning("Config file %s not found, using defaults", path)
        config = dict(DEFAULTS)
    else:
        with open(path, encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        config = _deep_merge(DEFAULTS, user_config)

    _validate(config)
    return config


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(load_config())
