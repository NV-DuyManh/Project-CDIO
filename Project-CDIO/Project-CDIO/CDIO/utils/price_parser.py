import re
from config.config import FALLBACK_IMG


def parse_price(price_str):
    """
    Xử lý giá mạnh mẽ.
    "23.990.000₫" → 23990000 | None nếu không hợp lệ.
    Không bao giờ trả float('inf') → tránh OverflowError.
    """
    try:
        if not price_str or not isinstance(price_str, str):
            return None
        cleaned = re.sub(r'[^\d]', '', price_str.strip())
        if not cleaned:
            return None
        value = int(cleaned)
        if value <= 0 or value > 1_000_000_000:
            return None
        return value
    except Exception:
        return None


def is_valid_price(raw_price):
    """Kiểm tra giá có hợp lệ để sort/lưu không."""
    if raw_price is None:
        return False
    if isinstance(raw_price, float) and (raw_price != raw_price or raw_price == float('inf')):
        return False
    return True


def sanitize_product(p):
    """Làm sạch dữ liệu sản phẩm, lọc sản phẩm không có giá."""
    raw = p.get('raw_price')
    if not is_valid_price(raw):
        return None
    return {
        'site':      p.get('site') or 'Unknown',
        'title':     (p.get('title') or 'Sản phẩm chưa có tên').strip(),
        'price_str': (p.get('price_str') or 'Liên hệ').strip(),
        'raw_price': int(raw),
        'img':       p.get('img') or FALLBACK_IMG,
        'link':      p.get('link') or '#',
    }
