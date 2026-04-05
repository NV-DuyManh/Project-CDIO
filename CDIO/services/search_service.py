import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

# ── Scrapers ─────────────────────────────────────────────────────────
from scrapers.clickbuy_scraper   import scrape_clickbuy
from scrapers.cellphones_scraper import scrape_cellphones
from scrapers.didong3a_scraper   import scrape_didong3a
from scrapers.smartviets_scraper import scrape_smartviets
from scrapers.bachlong_scraper   import scrape_bachlong
from scrapers.tientran_scraper   import scrape_tientran

# ── Helpers ───────────────────────────────────────────────────────────
from database.db             import get_data_from_db, save_to_db
from utils.price_parser      import is_valid_price
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

# ════════════════════════════════════════════════════════════════════
# NORMALIZER V5 — CỖ MÁY "HỦY DIỆT" LỖI CHÍNH TẢ (Hỗ trợ 9 hãng ĐT)
# ════════════════════════════════════════════════════════════════════
def normalize_keyword(keyword: str) -> str:
    kw = keyword.lower().strip()

    # 1. FIX SAI TÊN HÃNG (BRAND TYPOS)
    brand_fixes = {
        # Apple
        r'\b(iphon|iphne|ipone|ifone|iphonee+|iphonr|iphoen|ihpone|ipho|ipne|iphe|ipon|ipgine|iphkne|ipyone|ipbne|ipjone|ip|iph|i)\b(?=\s*\d|\b)': 'iphone',
        # Samsung
        r'\b(samsumg|samsng|sam sung|samsun|samusng|samsugn|samdung|samxung|ss|sam)\b': 'samsung',
        # Xiaomi / Redmi
        r'\b(xaiomi|xiomi|xioami|shaomi|xaomi|xm|mi)\b': 'xiaomi',
        r'\b(realmi|realm|rm)\b': 'redmi', # Gõ nhầm rm thành redmi
        # Oppo
        r'\b(opo|op)\b': 'oppo',
        # Vivo
        r'\b(vibo|vvio)\b': 'vivo',
        # Realme
        r'\b(realme|realmi|realm)\b': 'realme',
        # Google
        r'\b(goolge|gogle)\b': 'google',
        # OnePlus
        r'\b(onepluss|one plus|1plus)\b': 'oneplus',
        # Honor
        r'\b(honer|honnor)\b': 'honor'
    }
    for pattern, rep in brand_fixes.items():
        kw = re.sub(pattern, rep, kw)

    # 2. FIX SAI TÊN DÒNG MÁY (SERIES TYPOS)
    series_fixes = {
        r'\b(not|notee)\b': 'note',
        r'\b(renoo|renno|rneo)\b': 'reno',
        r'\b(pixle|pexel)\b': 'pixel',
        r'\b(magci|magc)\b': 'magic',
        r'\b(zf|zfold)\b': 'z fold',
        r'\b(zflip)\b': 'z flip',
    }
    for pattern, rep in series_fixes.items():
        kw = re.sub(pattern, rep, kw)

    # 3. TÁCH CHỮ VÀ SỐ DÍNH LIỀN (VD: iphone15 -> iphone 15, s24 -> s 24)
    kw = re.sub(r'\b([a-z]+)(\d+)\b', r'\1 \2', kw)

    # 4. FIX KHOẢNG TRẮNG GIỮA SỐ (VD: 1 5 -> 15, 2 3 -> 23)
    kw = re.sub(r'\b(\d)\s+(\d)\b', r'\1\2', kw)

    # 5. FIX ĐẢO SỐ, NHẦM CHỮ (LOGIC THÔNG MINH)
    # Chữ l/i thành số 1 (l5 -> 15)
    kw = re.sub(r'(iphone\s*)(l|i)(\d)\b', r'\g<1>1\3', kw)
    # iPhone đảo số (51 -> 15, 41 -> 14, 31 -> 13)
    kw = re.sub(r'(iphone\s*)([1-6])1\b', r'\g<1>1\2', kw)
    # Samsung đảo số (32 -> 23, 42 -> 24)
    kw = re.sub(r'(s|a|m|note)\s*32\b', r'\1 23', kw)
    kw = re.sub(r'(s|a|m|note)\s*42\b', r'\1 24', kw)
    # Xiaomi đảo số (21 -> 12)
    kw = re.sub(r'(note)\s*21\b', r'\1 12', kw)
    
    # 6. XÓA KÝ TỰ RÁC DÍNH VÀO SỐ (VD: 15e, 15r, 23t, 23y)
    # Xóa các chữ cái linh tinh sau số có 2 chữ số (ngoại trừ các từ khóa chuẩn như s, c, u)
    kw = re.sub(r'(\b\d{2})[ertyiopadfghjklzxvbnm]\b', r'\1', kw)

    # 7. TÁCH HẬU TỐ BỊ DÍNH VÀO SỐ (VD: 15prm -> 15 prm, 24u -> 24 u)
    kw = re.sub(r'(\d+)(pm|prm|pr|pl|u|ul|fe|pro|plus|promax|ultra)\b', r'\1 \2', kw)

    # 8. MAPPING HẬU TỐ (PHIÊN BẢN)
    suffix_map = {
        r'\bprm\b': 'pro max',
        r'\bpm\b': 'pro max',
        r'\bpromax\b': 'pro max',
        r'\bpr\b': 'pro',
        r'\bpl\b': 'plus',
        r'\bu\b': 'ultra',
        r'\bul\b': 'ultra',
    }
    for pattern, rep in suffix_map.items():
        kw = re.sub(pattern, rep, kw)

    # 9. TỰ ĐỘNG THÊM "GALAXY" CHO SAMSUNG
    if 'samsung' in kw and 'galaxy' not in kw:
        kw = kw.replace('samsung', 'samsung galaxy')

    # 10. DỌN DẸP LỖI LẶP TỪ DO USER GÕ THỪA
    kw = re.sub(r'\bgalaxy\s+galaxy\b', 'galaxy', kw)
    kw = re.sub(r'\bsamsung\s+samsung\b', 'samsung', kw)
    kw = re.sub(r'\biphone\s+iphone\b', 'iphone', kw)

    # 11. ĐỊNH DẠNG TITLE CASE VÀ NỐI SỐ CHO CÁC SÀN DỄ TÌM
    kw = re.sub(r'\s+', ' ', kw).strip()
    kw = kw.title()
    
    # Nối "S 24" -> "S24", "Y 36" -> "Y36", "C 55" -> "C55"
    kw = re.sub(r'(Galaxy S|Galaxy A|Galaxy M|Note|Z Fold|Z Flip|Reno|Y|C|Pixel)\s+(\d+)', r'\1\2', kw, flags=re.IGNORECASE)

    # Ép chuẩn định dạng thương hiệu
    kw = kw.replace('Iphone', 'iPhone')
    kw = kw.replace('Macbook', 'MacBook')
    kw = kw.replace('Ipad', 'iPad')
    kw = kw.replace('Oneplus', 'OnePlus')
    
    return kw

# ════════════════════════════════════════════════════════════════════
# CORE SEARCH ENGINE
# ════════════════════════════════════════════════════════════════════
def search_all_stores(keyword: str, user_id=None) -> tuple:
    """
    Tìm kiếm sản phẩm trên tất cả cửa hàng.
    Flow: Normalize -> Check Cache -> Scrape -> Filter -> Save -> Return
    """
    # ── Bước 0: Chuẩn hóa từ khóa ────────────────────────────────────
    normalized_kw = normalize_keyword(keyword)
    
    if normalized_kw.lower() != keyword.lower():
        print(f"🪄 [Normalize] Fix lỗi gõ sai: '{keyword}' ➔ '{normalized_kw}'")
    else:
        print(f"🔎 [Search] Đang xử lý: '{normalized_kw}'")

    # ── Bước 1: Cache & Freshness Check ──────────────────────────────
    cached = get_data_from_db(normalized_kw)
    if cached:
        last_updated = cached[0].get('created_at')
        if last_updated:
            now = datetime.now()
            time_diff = now - last_updated
            if time_diff < timedelta(minutes=30):
                print(f"⚡ [Fast Load] Trả về {len(cached)} kết quả từ DB cho '{normalized_kw}'")
                return cached, True

    # ── Bước 2: Scrape song song ─────────────────────────────────────
    print(f"🔄 [Scraping] Đang cào dữ liệu mới cho: {normalized_kw}...")
    raw_products = []

    with ThreadPoolExecutor(max_workers=len(SCRAPER_REGISTRY)) as executor:
        future_map = {
            executor.submit(fn, normalized_kw): store_name
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
    # ── Bước 3: Tiền lọc giá hợp lệ ─────────────────────────────────
    raw_products = [
        p for p in raw_products
        if is_valid_price(p.get('raw_price'))
    ]

# ── Bước 4: Áp dụng 3 lớp lọc ───────────────────────────────────
    filtered_products = apply_all_filters(raw_products, normalized_kw)

    # ── Bước 4.5: Loại bỏ sản phẩm trùng lặp bằng (Sàn + Tên + Giá) ─
    unique_products = []
    seen_items = set()
    for p in filtered_products:
        identifier = (p.get('site'), p.get('title'), p.get('raw_price'))
        if identifier not in seen_items:
            seen_items.add(identifier)
            unique_products.append(p)
    filtered_products = unique_products
    # ────────────────────────────────────────────────────────────────

    print(f"[search] {len(raw_products)} thô → {len(filtered_products)} sau lọc")

    # ── Bước 5: Lưu DB ───────────────────────────────────────────────
    save_to_db(normalized_kw, filtered_products, user_id=user_id)

    return filtered_products, False