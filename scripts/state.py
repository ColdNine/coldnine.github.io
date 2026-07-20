"""Tracks processed article IDs to prevent duplicate post generation across runs."""

import json
import logging
import os
import shutil
from datetime import datetime, timezone, timedelta
from typing import List

logger = logging.getLogger(__name__)

DEFAULT_STATE_FILE = "data/processed_articles.json"
KST = timezone(timedelta(hours=9))


def _empty_state() -> dict:
    return {"processed_ids": [], "last_run_at": None}


def load_state(state_file: str = DEFAULT_STATE_FILE) -> dict:
    """Load the state file, initializing or recovering it if missing/corrupt."""
    if not os.path.exists(state_file):
        logger.info("No state file at %s, initializing fresh state", state_file)
        return _empty_state()

    try:
        with open(state_file, encoding="utf-8") as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("State file %s is corrupt (%s), backing up and resetting", state_file, exc)
        backup_path = f"{state_file}.corrupt.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            shutil.copy(state_file, backup_path)
        except OSError:
            logger.warning("Could not back up corrupt state file %s", state_file)
        return _empty_state()

    if "processed_ids" not in state or not isinstance(state["processed_ids"], list):
        logger.warning("State file %s missing/invalid 'processed_ids', resetting", state_file)
        return _empty_state()

    return state


def save_state(state: dict, state_file: str = DEFAULT_STATE_FILE) -> None:
    """Persist the state dict to `state_file`, creating parent directories as needed."""
    os.makedirs(os.path.dirname(state_file) or ".", exist_ok=True)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def is_processed(article_id: str, state: dict) -> bool:
    """Return True if `article_id` has already been processed."""
    return article_id in state.get("processed_ids", [])


def mark_processed(article_id: str, state: dict) -> dict:
    """Add `article_id` to the state's processed_ids (idempotent) and return the state."""
    if not is_processed(article_id, state):
        state.setdefault("processed_ids", []).append(article_id)
    return state


def touch_last_run(state: dict) -> dict:
    """Update the state's last_run_at timestamp to now (KST) and return the state."""
    state["last_run_at"] = datetime.now(KST).isoformat()
    return state


def filter_unprocessed(articles: List, state: dict) -> List:
    """Return only the articles from `articles` whose `.id` is not yet processed."""
    return [a for a in articles if not is_processed(a.id, state)]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    test_file = "/tmp/state_test.json"
    state = load_state(test_file)
    print("initial:", state)
    mark_processed("20260719000026", state)
    touch_last_run(state)
    save_state(state, test_file)
    reloaded = load_state(test_file)
    print("reloaded:", reloaded)
    print("is_processed known:", is_processed("20260719000026", reloaded))
    print("is_processed unknown:", is_processed("99999999999999", reloaded))
