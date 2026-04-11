"""
routes/category_routes.py — Fixed
- /category/brand/iphone  → redirect sang iPhone 16 Series (series mặc định)
- /category/brand/samsung → redirect sang Galaxy S25 Series
- /category/series/<slug> → hiện sản phẩm từ DB
- Fallback query nếu db.py thiếu hàm get_products_by_series
"""

from flask import Blueprint, render_template, abort, request, redirect, url_for
from config.categories import CATEGORIES

category_bp = Blueprint("category", __name__)

SERIES_KEYWORDS = {
    "iphone-17": "iPhone 17",
    "iphone-16": "iPhone 16",
    "iphone-15": "iPhone 15",
    "iphone-14": "iPhone 14",
    "samsung-s25": "Galaxy S25",
    "samsung-s24": "Galaxy S24",
    "samsung-a":   "Galaxy A",
    "samsung-z":   "Galaxy Z",
    "other":       None,
}

BRAND_LABELS = {
    "iphone":  "iPhone",
    "samsung": "Samsung",
    "other":   "Thương hiệu khác",
}

# Series mặc định khi click vào brand
BRAND_DEFAULT_SERIES = {
    "iphone":  "iphone-16",
    "samsung": "samsung-s25",
}


def _get_conn():
    from database.db import get_db_connection
    return get_db_connection()


def _query_by_series(keyword, sort, page, per_page):
    """Ưu tiên hàm có sẵn trong db.py, fallback query thủ công."""
    try:
        from database.db import get_products_by_series
        return get_products_by_series(keyword, sort=sort, page=page, per_page=per_page)
    except (ImportError, AttributeError):
        pass

    import pymysql.cursors
    conn = _get_conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        order  = "ASC" if sort == "asc" else "DESC"
        offset = (page - 1) * per_page
        like   = f"%{keyword.lower()}%"

        cur.execute(
            "SELECT COUNT(*) AS c FROM search_history WHERE LOWER(title) LIKE %s",
            (like,)
        )
        total = cur.fetchone()["c"]

        cur.execute(
            f"SELECT * FROM search_history WHERE LOWER(title) LIKE %s "
            f"ORDER BY raw_price {order} LIMIT %s OFFSET %s",
            (like, per_page, offset)
        )
        return cur.fetchall(), total
    finally:
        conn.close()


def _query_other(sort, page, per_page):
    """Sản phẩm không phải iPhone / Samsung."""
    try:
        from database.db import get_products_by_brand
        return get_products_by_brand("other", sort=sort, page=page, per_page=per_page)
    except (ImportError, AttributeError):
        pass

    import pymysql.cursors
    conn = _get_conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        order  = "ASC" if sort == "asc" else "DESC"
        offset = (page - 1) * per_page

        cur.execute(
            "SELECT COUNT(*) AS c FROM search_history "
            "WHERE LOWER(title) NOT LIKE '%iphone%' AND LOWER(title) NOT LIKE '%samsung%' "
            "AND LOWER(title) NOT LIKE '%galaxy%'"
        )
        total = cur.fetchone()["c"]

        cur.execute(
            f"SELECT * FROM search_history "
            f"WHERE LOWER(title) NOT LIKE '%iphone%' AND LOWER(title) NOT LIKE '%samsung%' "
            f"AND LOWER(title) NOT LIKE '%galaxy%' "
            f"ORDER BY raw_price {order} LIMIT %s OFFSET %s",
            (per_page, offset)
        )
        return cur.fetchall(), total
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════
# BRAND PAGE — redirect về series mặc định
# /category/brand/iphone  → /category/series/iphone-16
# /category/brand/samsung → /category/series/samsung-s25
# /category/brand/other   → hiện trang other
# ════════════════════════════════════════════════════════════════
@category_bp.route("/category/brand/<brand>")
def brand_page(brand: str):
    brand = brand.lower()
    if brand not in BRAND_LABELS:
        abort(404)

    # iphone / samsung → redirect sang series mặc định
    if brand in BRAND_DEFAULT_SERIES:
        return redirect(url_for("category.series_page",
                                series_slug=BRAND_DEFAULT_SERIES[brand]))

    # other → hiện trang
    sort     = request.args.get("sort", "asc")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 60

    try:
        products, total = _query_other(sort, page, per_page)
    except Exception as e:
        print(f"[category] other error: {e}")
        products, total = [], 0

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "category_new.html",
        view          = "brand",
        brand_key     = "other",
        brand_label   = "Thương hiệu khác",
        series_slug   = None,
        series_label  = None,
        products      = products,
        total         = total,
        page          = page,
        total_pages   = total_pages,
        sort          = sort,
        all_categories = CATEGORIES,
    )


# ════════════════════════════════════════════════════════════════
# SERIES PAGE — /category/series/<series_slug>
# ════════════════════════════════════════════════════════════════
@category_bp.route("/category/series/<series_slug>")
def series_page(series_slug: str):
    series_slug = series_slug.lower()
    keyword = SERIES_KEYWORDS.get(series_slug)
    if keyword is None and series_slug != "other":
        abort(404)

    sort     = request.args.get("sort", "asc")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 60

    try:
        if series_slug == "other":
            products, total = _query_other(sort, page, per_page)
        else:
            products, total = _query_by_series(keyword, sort, page, per_page)
    except Exception as e:
        print(f"[category] series_page '{series_slug}' error: {e}")
        products, total = [], 0

    total_pages = max(1, (total + per_page - 1) // per_page)
    brand_key = "iphone" if "iphone" in series_slug else (
                "samsung" if "samsung" in series_slug else "other")

    return render_template(
        "category_new.html",
        view          = "series",
        brand_key     = brand_key,
        brand_label   = BRAND_LABELS.get(brand_key, brand_key.title()),
        series_slug   = series_slug,
        series_label  = keyword or "Thương hiệu khác",
        products      = products,
        total         = total,
        page          = page,
        total_pages   = total_pages,
        sort          = sort,
        all_categories = CATEGORIES,
    )


# ════════════════════════════════════════════════════════════════
# BACKWARD COMPAT
# ════════════════════════════════════════════════════════════════
@category_bp.route("/category/<brand>")
def old_brand_page(brand: str):
    return redirect(url_for("category.brand_page", brand=brand.lower()))

@category_bp.route("/category/<brand>/<series_key>")
def old_series_page(brand: str, series_key: str):
    slug = series_key.lower()
    if slug in SERIES_KEYWORDS:
        return redirect(url_for("category.series_page", series_slug=slug))
    return redirect(url_for("category.brand_page", brand=brand.lower()))

@category_bp.route("/category/<brand>/<series_key>/<path:model_keyword>")
def old_model_page(brand: str, series_key: str, model_keyword: str):
    kw = model_keyword.replace("-", " ")
    return redirect(url_for("search.home", keyword=kw))