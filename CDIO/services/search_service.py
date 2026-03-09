"""
services/search_service.py
==========================
Điều phối toàn bộ luồng tìm kiếm:
  1. Kiểm tra cache DB
  2. Scrape song song 6 cửa hàng
  3. Lọc 3 lớp (blacklist → model match → price range)
  4. Lưu DB
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Scrapers ─────────────────────────────────────────────────────────
from scrapers.clickbuy_scraper   import scrape_clickbuy
from scrapers.cellphones_scraper import scrape_cellphones
from scrapers.didong3a_scraper   import scrape_didong3a
from scrapers.smartviets_scraper import scrape_smartviets
from scrapers.bachlong_scraper   import scrape_bachlong
from scrapers.tientran_scraper   import scrape_tientran

# ── Helpers ───────────────────────────────────────────────────────────
from database.db           import get_data_from_db, save_to_db
from utils.price_parser    import is_valid_price
from services.filter_service import apply_all_filters


# ════════════════════════════════════════════════════════════════════
# REGISTRY — chỉ cần thêm 1 dòng khi có store mới
# ════════════════════════════════════════════════════════════════════
SCRAPER_REGISTRY: dict = {
    "Clickbuy":         scrape_clickbuy,
    "CellphoneS":       scrape_cellphones,
    "Di Động 3A":       scrape_didong3a,
    "Smart Việt":       scrape_smartviets,
    "Bạch Long Store":  scrape_bachlong,
    "Tiến Trần Mobile": scrape_tientran,
}


def search_all_stores(keyword: str) -> tuple:
    """
    Tìm kiếm sản phẩm trên tất cả cửa hàng trong SCRAPER_REGISTRY.

    Flow:
      1. Kiểm tra cache DB  → nếu có: trả về ngay (fast load)
      2. Scrape song song   → gom kết quả từ tất cả stores
      3. Lọc 3 lớp          → loại rác, sai model, giá bất thường
      4. Lưu vào DB         → cache cho lần sau

    Returns:
      (products: list[dict], is_fast_load: bool)
    """
    # ── Bước 1: Cache ────────────────────────────────────────────────
    cached = get_data_from_db(keyword)
    if cached:
        return cached, True

    # ── Bước 2: Scrape song song ─────────────────────────────────────
    raw_products = []

    with ThreadPoolExecutor(max_workers=len(SCRAPER_REGISTRY)) as executor:
        future_map = {
            executor.submit(fn, keyword): store_name
            for store_name, fn in SCRAPER_REGISTRY.items()
        }

        for future in as_completed(future_map):
            store_name = future_map[future]
            try:
                results = future.result()
                raw_products.extend(results)
                print(f"[scraper:{store_name}] {len(results)} sản phẩm")
            except Exception as e:
                print(f"[scraper:{store_name}] Lỗi: {e}")

    # ── Bước 3: Tiền lọc giá hợp lệ ─────────────────────────────────
    raw_products = [
        p for p in raw_products
        if is_valid_price(p.get('raw_price'))
    ]

    # ── Bước 4: Áp dụng 3 lớp lọc ───────────────────────────────────
    #   Lớp 1: Blacklist từ phụ kiện + kiểm tra liên quan keyword
    #   Lớp 2: Exact model match (iphone 15 ≠ iphone 16)
    #   Lớp 3: Price range (loại giá lệch quá xa median)
    filtered_products = apply_all_filters(raw_products, keyword)

    print(f"[search] {len(raw_products)} thô → {len(filtered_products)} sau lọc")

    # ── Bước 5: Lưu DB ───────────────────────────────────────────────
    save_to_db(keyword, filtered_products)

    return filtered_products, False