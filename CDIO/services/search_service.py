from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta # Thêm để check thời gian

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
# ════════════════════════════════════════════════════════════─═══════
SCRAPER_REGISTRY: dict = {
    "Clickbuy":         scrape_clickbuy,
    "CellphoneS":       scrape_cellphones,
    "Di Động 3A":       scrape_didong3a,
    "Smart Việt":       scrape_smartviets,
    "Bạch Long Store":  scrape_bachlong,
    "Tiến Trần Mobile": scrape_tientran,
}

def search_all_stores(keyword: str, user_id=None) -> tuple:
    """
    Tìm kiếm sản phẩm trên tất cả cửa hàng.
    FIX: Thêm user_id và logic kiểm tra cập nhật giá theo thời gian.
    """
    
    # ── Bước 1: Cache & Freshness Check ──────────────────────────────
    cached = get_data_from_db(keyword)
    if cached:
        # Lấy thời gian cào của bản ghi gần nhất
        last_updated = cached[0].get('created_at')
        
        # LOGIC: Nếu dữ liệu mới cào trong vòng 30 phút -> Dùng luôn (Fast Load)
        # Giúp giảm tải cho server và tránh bị store block IP
        if last_updated:
            now = datetime.now()
            # Tính khoảng cách thời gian
            time_diff = now - last_updated
            if time_diff < timedelta(minutes=30):
                print(f"⚡ [Fast Load] Trả về kết quả từ DB (Cập nhật {time_diff.seconds // 60} phút trước)")
                return cached, True

    # ── Bước 2: Scrape song song (Nếu DB trống hoặc dữ liệu quá cũ) ────
    print(f"🔄 [Scraping] Đang cào dữ liệu mới cho từ khóa: {keyword}...")
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

    # ── Bước 4: Áp dụng 3 lớp lọc (Blacklist, Model Match, Price Range) ─
    filtered_products = apply_all_filters(raw_products, keyword)

    print(f"[search] {len(raw_products)} thô → {len(filtered_products)} sau lọc")

    # ── Bước 5: Lưu DB (Kèm theo user_id của người tìm) ───────────────
    # Hàm save_to_db bây giờ sẽ nhận thêm user_id để lưu vào lịch sử
    save_to_db(keyword, filtered_products, user_id=user_id)

    return filtered_products, False