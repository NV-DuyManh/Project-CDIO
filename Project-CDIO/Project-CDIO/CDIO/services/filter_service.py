"""
services/filter_service.py
==========================
Bộ lọc 3 lớp loại "sản phẩm rác" khỏi kết quả scraping.

  Lớp 1 — Blacklist     : loại title chứa từ phụ kiện (ốp lưng, sạc, cáp...)
  Lớp 2 — Exact Model   : loại sai số model (tìm "iPhone 15" → bỏ "iPhone 16")
  Lớp 3 — Price Range   : loại giá bất thường so với median tập kết quả
"""

import re
import statistics
from typing import List, Dict, Optional

# ════════════════════════════════════════════════════════════════════
# CẤU HÌNH — chỉnh tại đây, không cần sửa logic bên dưới
# ════════════════════════════════════════════════════════════════════

# Danh sách từ phụ kiện bị loại (không phân biệt hoa/thường, có/không dấu)
ACCESSORY_BLACKLIST: List[str] = [
    # Vỏ bảo vệ
    "ốp lưng", "op lung", "ốp điện thoại", "op dien thoai",
    "kính cường lực", "kinh cuong luc", "cường lực", "cuong luc",
    "miếng dán", "mieng dan", "dán màn hình", "dan man hinh",
    "bao da", "bao silicon",
    "túi đựng", "tui dung",
    # Cáp & sạc
    "sạc", "củ sạc", "cục sạc", "adapter sạc",
    "cáp sạc", "cap sac",
    "cáp usb", "cap usb",
    "cáp lightning", "cap lightning",
    "cáp type-c", "cap type-c", "cáp type c", "cap type c",
    "dây sạc", "day sac",
    "đầu sạc", "dau sac",
    # Tai nghe
    "tai nghe", "earphone", "earbud", "airpod",
    "headphone", "headset",
    # Pin & nguồn
    "pin dự phòng", "pin du phong",
    "sạc dự phòng", "sac du phong",
    "pin thay thế", "pin thay the",
    # Phụ kiện đặt máy
    "đế sạc", "de sac", "dock sạc", "dock sac",
    "giá đỡ", "gia do",
    # Bút & phụ kiện nhập liệu
    "bút cảm ứng", "but cam ung", "stylus",
    # Lưu trữ
    "memory card", "thẻ nhớ", "the nho", "thẻ sd", "the sd",
    # Khay SIM
    "sim khay", "khay sim",
    # Lens
    "lens camera", "lens điện thoại", "lens dien thoai",
    # Phụ kiện đeo
    "dây đeo", "day deo", "strap",
    "kẹp điện thoại", "kep dien thoai",
    # Vệ sinh
    "bộ vệ sinh", "bo ve sinh", "vệ sinh", "ve sinh",
    # Khác
    "sticker", "decal",
]

# Compile regex một lần duy nhất khi import
_BLACKLIST_PATTERN = re.compile(
    r'(?<!\w)(' + '|'.join(re.escape(w) for w in ACCESSORY_BLACKLIST) + r')(?!\w)',
    re.IGNORECASE | re.UNICODE
)

# Nhãn thương hiệu cần kiểm tra số model
_MODEL_BRANDS = [
    "iphone", "samsung", "galaxy", "redmi", "xiaomi", "poco",
    "realme", "oppo", "vivo", "nokia", "pixel", "oneplus",
    "huawei", "honor", "asus", "zenfone",
]

# Giá tối thiểu tuyệt đối (VND) — dưới ngưỡng này chắc chắn là phụ kiện/rác
MIN_PRICE: int = 200_000        # 200k VND

# Ngưỡng lọc giá theo median
PRICE_LOWER_FACTOR: float = 0.15   # < median × 15% → loại
PRICE_UPPER_FACTOR: float = 6.0    # > median × 600% → loại


# ════════════════════════════════════════════════════════════════════
# LỚP 1 — BLACKLIST FILTER
# ════════════════════════════════════════════════════════════════════

def _title_has_blacklisted_word(title: str) -> bool:
    return bool(_BLACKLIST_PATTERN.search(title))


def _title_relevant_to_keyword(title: str, keyword: str) -> bool:
    """
    Kiểm tra title có liên quan đến keyword không.
    Yêu cầu ít nhất 50% token quan trọng (> 2 ký tự) của keyword xuất hiện trong title.
    """
    norm_title   = title.lower()
    norm_keyword = keyword.lower()

    # Khớp hoàn toàn → pass ngay
    if norm_keyword in norm_title:
        return True

    tokens = [t for t in re.split(r'\s+', norm_keyword) if len(t) > 2]
    if not tokens:
        return True  # Keyword quá ngắn, không lọc

    matched = sum(1 for t in tokens if t in norm_title)
    return matched >= max(1, len(tokens) * 0.5)


def filter_layer1_blacklist(products: List[Dict], keyword: str) -> List[Dict]:
    """
    Lớp 1: Loại sản phẩm:
      (a) Title chứa từ phụ kiện trong blacklist
      (b) Title không liên quan đến keyword tìm kiếm
    """
    result = []
    for p in products:
        title = p.get('title') or ''
        if _title_has_blacklisted_word(title):
            continue
        if not _title_relevant_to_keyword(title, keyword):
            continue
        result.append(p)
    return result


# ════════════════════════════════════════════════════════════════════
# LỚP 2 — EXACT MODEL MATCH FILTER
# ════════════════════════════════════════════════════════════════════

_MODEL_TOKEN_RE = re.compile(
    r'\b([a-z]?\d{1,4}[a-z+]*|[a-z]{2,}\d{1,4}[a-z+]*)\b',
    re.IGNORECASE
)


def _extract_model_tokens(text: str) -> List[str]:
    """Trích xuất token số model: '15', 's24', 'a55', 'note20'..."""
    return [m.group(0).lower() for m in _MODEL_TOKEN_RE.finditer(text.lower())]


def _get_keyword_model_tokens(keyword: str) -> Optional[List[str]]:
    """
    Trả về danh sách model token nếu keyword thuộc brand có đánh số model.
    Trả về None nếu không cần lọc model (keyword quá chung chung).
    """
    kw_lower = keyword.lower()
    if not any(brand in kw_lower for brand in _MODEL_BRANDS):
        return None

    tokens = [t for t in _extract_model_tokens(keyword) if len(t) >= 2]
    return tokens if tokens else None


def _title_matches_model(title: str, model_tokens: List[str]) -> bool:
    """
    Kiểm tra title có chứa ĐÚNG số model trong keyword không.

    Ví dụ:
      keyword_tokens = ["15"]
        "iPhone 15 Pro Max"  → ✅  (chứa "15")
        "iPhone 16 Pro"      → ❌  (có "16", không có "15")
        "iPhone 15 Plus"     → ✅  (chứa "15")

      keyword_tokens = ["s24"]
        "Samsung Galaxy S24 Ultra" → ✅
        "Samsung Galaxy S23 FE"    → ❌
    """
    title_lower  = title.lower()
    title_tokens = _extract_model_tokens(title)

    for kw_token in model_tokens:
        if kw_token.isdigit():
            # Số thuần: dùng word boundary để "15" không match "115"
            if not re.search(r'\b' + re.escape(kw_token) + r'\b', title_lower):
                return False
        else:
            # Chữ+số (s24, a55...): phải có trong title_tokens
            if kw_token not in title_tokens:
                return False
    return True


def filter_layer2_exact_model(products: List[Dict], keyword: str) -> List[Dict]:
    """
    Lớp 2: Loại sản phẩm sai số model.
    Chỉ kích hoạt khi keyword chứa số model rõ ràng.
    Bỏ qua với keyword chung ("điện thoại", "laptop"...).
    """
    model_tokens = _get_keyword_model_tokens(keyword)
    if not model_tokens:
        return products  # Không có số model → bỏ qua lớp này

    result = [
        p for p in products
        if _title_matches_model(p.get('title') or '', model_tokens)
    ]
    # Nếu lọc quá gắt (ra 0 kết quả) → giữ nguyên để tránh trang trắng
    return result if result else products


# ════════════════════════════════════════════════════════════════════
# LỚP 3 — PRICE RANGE FILTER
# ════════════════════════════════════════════════════════════════════

def filter_layer3_price(products: List[Dict]) -> List[Dict]:
    """
    Lớp 3: Loại sản phẩm có giá bất thường.
      Bước A: Loại giá dưới ngưỡng tuyệt đối MIN_PRICE
      Bước B: Tính median, loại sản phẩm lệch quá xa
    """
    # Bước A
    candidates = [
        p for p in products
        if isinstance(p.get('raw_price'), (int, float))
        and p['raw_price'] >= MIN_PRICE
    ]

    if len(candidates) < 2:
        return candidates

    # Bước B
    prices = [p['raw_price'] for p in candidates]
    med    = statistics.median(prices)
    lower  = med * PRICE_LOWER_FACTOR
    upper  = med * PRICE_UPPER_FACTOR

    result = [p for p in candidates if lower <= p['raw_price'] <= upper]
    return result if result else candidates


# ════════════════════════════════════════════════════════════════════
# HÀM CÔNG KHAI — gọi từ search_service
# ════════════════════════════════════════════════════════════════════

def apply_all_filters(products: List[Dict], keyword: str) -> List[Dict]:
    """
    Áp dụng 3 lớp lọc theo thứ tự hiệu quả nhất:
      1. Blacklist  → loại nhanh số lượng lớn rác
      2. Model match → loại sai dòng máy
      3. Price range → loại phụ kiện giá thấp sót lại

    Trả về danh sách đã lọc, sắp xếp theo giá tăng dần.
    """
    step1 = filter_layer1_blacklist(products, keyword)
    step2 = filter_layer2_exact_model(step1, keyword)
    step3 = filter_layer3_price(step2)
    return sorted(step3, key=lambda x: x.get('raw_price', 0))


# ════════════════════════════════════════════════════════════════════
# DEBUG — dùng khi kiểm tra, không dùng trên production
# ════════════════════════════════════════════════════════════════════

def debug_explain(product: Dict, keyword: str,
                  pool: Optional[List[Dict]] = None) -> Dict:
    """Giải thích tại sao một sản phẩm được giữ hoặc bị loại."""
    title = product.get('title', '')
    price = product.get('raw_price', 0)

    blacklisted  = _title_has_blacklisted_word(title)
    kw_relevant  = _title_relevant_to_keyword(title, keyword)
    model_tokens = _get_keyword_model_tokens(keyword)
    model_ok     = _title_matches_model(title, model_tokens) if model_tokens else None
    price_ok     = price >= MIN_PRICE

    median_info = None
    if pool:
        valid = [p['raw_price'] for p in pool
                 if isinstance(p.get('raw_price'), (int, float)) and p['raw_price'] >= MIN_PRICE]
        if valid:
            med = statistics.median(valid)
            median_info = {
                'median':    med,
                'lower':     med * PRICE_LOWER_FACTOR,
                'upper':     med * PRICE_UPPER_FACTOR,
                'in_range':  med * PRICE_LOWER_FACTOR <= price <= med * PRICE_UPPER_FACTOR,
            }

    passed = (not blacklisted) and kw_relevant and price_ok
    if model_ok is not None:
        passed = passed and model_ok
    if median_info:
        passed = passed and median_info['in_range']

    return {
        'title':        title,
        'price':        price,
        'passed':       passed,
        'blacklisted':  blacklisted,
        'kw_relevant':  kw_relevant,
        'model_tokens': model_tokens,
        'model_ok':     model_ok,
        'price_ok':     price_ok,
        'median_info':  median_info,
    }