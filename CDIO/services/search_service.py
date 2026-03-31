"""
services/search_service.py
==========================
Search orchestration with:
  - Keyword normalization
  - Stale-While-Revalidate (SWR) caching
  - Parallel scraping
  - 3-layer filtering
  - Price-alert triggering after refresh
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from scrapers.clickbuy_scraper   import scrape_clickbuy
from scrapers.cellphones_scraper import scrape_cellphones
from scrapers.didong3a_scraper   import scrape_didong3a
from scrapers.smartviets_scraper import scrape_smartviets
from scrapers.bachlong_scraper   import scrape_bachlong
from scrapers.tientran_scraper   import scrape_tientran

from database.db              import (get_data_from_db, get_stale_data_from_db,
                                      save_to_db, log_keyword_search)
from utils.price_parser       import is_valid_price
from services.filter_service  import apply_all_filters
from services.keyword_normalizer import normalize_keyword
from config.config            import CACHE_TTL_SECONDS

# ════════════════════════════════════════════════════════════════════
# SCRAPER REGISTRY
# ════════════════════════════════════════════════════════════════════
SCRAPER_REGISTRY: dict = {
    "Clickbuy":         scrape_clickbuy,
    "CellphoneS":       scrape_cellphones,
    "Di Động 3A":       scrape_didong3a,
    "Smart Việt":       scrape_smartviets,
    "Bạch Long Store":  scrape_bachlong,
    "Tiến Trần Mobile": scrape_tientran,
}


# ════════════════════════════════════════════════════════════════════
# CORE SCRAPE PIPELINE (reusable)
# ════════════════════════════════════════════════════════════════════

def _scrape_and_save(keyword: str, user_id: int = None) -> list:
    """
    Full scrape → filter → save pipeline.
    Called both synchronously (first search) and from background threads (SWR refresh).
    """
    raw_products: list = []

    with ThreadPoolExecutor(max_workers=len(SCRAPER_REGISTRY)) as executor:
        future_map = {
            executor.submit(fn, keyword): name
            for name, fn in SCRAPER_REGISTRY.items()
        }
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                results = future.result() or []
                raw_products.extend(results)
                print(f"[scraper:{name}] {len(results)} products")
            except Exception as exc:
                print(f"[scraper:{name}] Error: {exc}")

    # Pre-filter: valid prices only
    raw_products = [p for p in raw_products if is_valid_price(p.get("raw_price"))]

    # 3-layer filter
    filtered = apply_all_filters(raw_products, keyword)
    print(f"[search] '{keyword}' → {len(raw_products)} raw / {len(filtered)} filtered")

    # Persist
    save_to_db(keyword, filtered, user_id)

    # Trigger price alerts in background (non-blocking)
    threading.Thread(
        target=_run_price_alerts, args=(keyword, filtered), daemon=True
    ).start()

    return filtered


def _run_price_alerts(keyword: str, products: list):
    """Safely run price-alert check without blocking the search response."""
    try:
        from services.price_alert_service import check_and_trigger_alerts
        check_and_trigger_alerts(keyword, products)
    except Exception as e:
        print(f"[price_alert] Error: {e}")


# ════════════════════════════════════════════════════════════════════
# PUBLIC SEARCH API
# ════════════════════════════════════════════════════════════════════

def search_all_stores(keyword: str, user_id: int = None) -> tuple:
    """
    Stale-While-Revalidate search.

    Returns: (products, is_from_cache, is_stale)

    Flow:
      1. Normalize keyword
      2. Fresh cache hit   → return immediately              (from_cache=True,  stale=False)
      3. Stale cache hit   → return old data + bg refresh    (from_cache=True,  stale=True)
      4. No cache at all   → scrape now, block               (from_cache=False, stale=False)
    """
    # ── Step 1: Normalize ────────────────────────────────────────
    normalized = normalize_keyword(keyword)
    if normalized != keyword.lower().strip():
        print(f"[normalize] '{keyword}' → '{normalized}'")

    # ── Step 2: Fresh cache? ─────────────────────────────────────
    fresh = get_data_from_db(normalized, ttl=CACHE_TTL_SECONDS)
    if fresh:
        log_keyword_search(normalized)  # update suggestion count
        return list(fresh), True, False

    # ── Step 3: Stale cache? ─────────────────────────────────────
    stale = get_stale_data_from_db(normalized)
    if stale:
        # Kick off background refresh — caller gets old data instantly
        threading.Thread(
            target=_scrape_and_save,
            args=(normalized, user_id),
            daemon=True,
            name=f"swr-refresh-{normalized[:20]}",
        ).start()
        log_keyword_search(normalized)
        return list(stale), True, True  # is_stale=True signals UI to poll

    # ── Step 4: No cache — scrape synchronously ──────────────────
    products = _scrape_and_save(normalized, user_id)
    return products, False, False