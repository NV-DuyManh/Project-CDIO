from concurrent.futures import ThreadPoolExecutor

from scrapers.clickbuy_scraper import scrape_clickbuy
from scrapers.cellphones_scraper import scrape_cellphones
from database.db import get_data_from_db, save_to_db
from utils.price_parser import is_valid_price


def search_all_stores(keyword):
    """
    Tìm kiếm sản phẩm trên tất cả cửa hàng.

    Flow:
      1. Kiểm tra cache trong DB
      2. Nếu có → trả về ngay (fast load)
      3. Nếu không → scrape song song tất cả stores → lưu DB → trả về

    Returns:
      (products: list, is_fast_load: bool)
    """
    # Bước 1: Kiểm tra cache
    cached = get_data_from_db(keyword)
    if cached:
        return cached, True

    # Bước 2: Scrape song song
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_cb = executor.submit(scrape_clickbuy, keyword)
        future_cp = executor.submit(scrape_cellphones, keyword)
        all_products = future_cb.result() + future_cp.result()

    # Bước 3: Lọc và sort theo giá
    all_products = [p for p in all_products if is_valid_price(p.get('raw_price'))]
    all_products.sort(key=lambda x: x['raw_price'])

    # Bước 4: Lưu vào DB
    save_to_db(keyword, all_products)

    return all_products, False
