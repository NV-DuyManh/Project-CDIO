"""
services/prewarm_service.py
============================
Background pre-warmer for HOT_KEYWORDS.
Runs as a daemon thread; cycles through keywords,
re-scraping those with stale or missing cache.
"""
import threading
import time

from config.config import HOT_KEYWORDS, CACHE_TTL_SECONDS
from database.db   import get_data_from_db, get_stale_data_from_db


def _needs_refresh(keyword: str) -> bool:
    """Return True if keyword has no fresh cache."""
    fresh = get_data_from_db(keyword, ttl=CACHE_TTL_SECONDS)
    return not fresh  # True when empty (stale or missing)


def _prewarm_keyword(keyword: str):
    """Scrape a single keyword if its cache is missing or stale."""
    try:
        if not _needs_refresh(keyword):
            print(f"[prewarm] ✓ cache ok: '{keyword}'")
            return
        print(f"[prewarm] ↻ refreshing: '{keyword}'")
        from services.search_service import _scrape_and_save
        results = _scrape_and_save(keyword)
        print(f"[prewarm] ✓ done: '{keyword}' ({len(results)} products)")
    except Exception as exc:
        print(f"[prewarm] ✗ error '{keyword}': {exc}")


def _worker_loop():
    """
    Main prewarm loop.
    Cycle interval = max(30 min, CACHE_TTL // 2) to avoid redundant scraping.
    A 5-second gap between each keyword avoids rate-limit bans.
    """
    cycle_interval = max(1800, CACHE_TTL_SECONDS // 2)
    print(f"[prewarm] Worker started — {len(HOT_KEYWORDS)} keywords, "
          f"cycle every {cycle_interval // 60} min")

    while True:
        for kw in HOT_KEYWORDS:
            _prewarm_keyword(kw)
            time.sleep(5)          # polite gap between sites
        print(f"[prewarm] Cycle complete. Sleeping {cycle_interval}s…")
        time.sleep(cycle_interval)


def start_prewarm_scheduler():
    """Start the daemon thread. Call once from app entry-point."""
    t = threading.Thread(target=_worker_loop, daemon=True, name="prewarm-worker")
    t.start()