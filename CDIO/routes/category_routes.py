"""
routes/category_routes.py — Fixed v4
Fixes:
1. Thêm samsung-s25 và samsung-s24 vào SERIES_KEYWORDS
2. Fix query brand page trả về đúng sản phẩm
3. Fix series page Samsung S25/S24
"""

from flask import Blueprint, render_template, abort, request, redirect, url_for
from config.categories import CATEGORIES

category_bp = Blueprint("category", __name__)

SERIES_KEYWORDS = {
    "iphone-17": "iPhone 17",
    "iphone-16": "iPhone 16",
    "iphone-15": "iPhone 15",
    "iphone-14": "iPhone 14",
    "samsung-s25": "Galaxy S25",   # ← FIX: thiếu trong code gốc
    "samsung-s24": "Galaxy S24",   # ← FIX: thiếu trong code gốc
    "samsung-s":   "Galaxy S",
    "samsung-a":   "Galaxy A",
    "samsung-z":   "Galaxy Z",
    "other":       None,
}

BRAND_LABELS = {
    "iphone":  "iPhone",
    "samsung": "Samsung",
    "other":   "Thương hiệu khác",
}


def _get_conn():
    from database.db import get_db_connection
    return get_db_connection()


def _query_by_series(keyword, sort, page, per_page):
    """Truy vấn theo series — tìm trong title VÀ keyword column."""
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
            "SELECT COUNT(*) AS c FROM search_history "
            "WHERE LOWER(title) LIKE %s OR LOWER(keyword) LIKE %s",
            (like, like)
        )
        total = cur.fetchone()["c"]

        cur.execute(
            f"SELECT * FROM search_history "
            f"WHERE LOWER(title) LIKE %s OR LOWER(keyword) LIKE %s "
            f"ORDER BY raw_price {order} LIMIT %s OFFSET %s",
            (like, like, per_page, offset)
        )
        rows = cur.fetchall()
        print(f"[category] series '{keyword}': {total} total, {len(rows)} rows")
        return rows, total
    finally:
        conn.close()


def _query_by_brand(brand, sort, page, per_page):
    """Truy vấn TẤT CẢ sản phẩm của brand."""
    import pymysql.cursors
    conn = _get_conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        order  = "ASC" if sort == "asc" else "DESC"
        offset = (page - 1) * per_page

        if brand == "iphone":
            where = "(LOWER(title) LIKE '%iphone%' OR LOWER(keyword) LIKE '%iphone%')"
            params_count = ()
            params_query = (per_page, offset)
        elif brand == "samsung":
            where = (
                "(LOWER(title) LIKE '%samsung%' OR LOWER(title) LIKE '%galaxy%' "
                "OR LOWER(keyword) LIKE '%samsung%' OR LOWER(keyword) LIKE '%galaxy%')"
            )
            params_count = ()
            params_query = (per_page, offset)
        else:
            # other: không phải iphone, không phải samsung/galaxy
            where = (
                "LOWER(title) NOT LIKE '%iphone%' "
                "AND LOWER(title) NOT LIKE '%samsung%' "
                "AND LOWER(title) NOT LIKE '%galaxy%' "
                "AND title IS NOT NULL AND title != '' "
                "AND raw_price > 0"
            )
            params_count = ()
            params_query = (per_page, offset)

        cur.execute(f"SELECT COUNT(*) AS c FROM search_history WHERE {where}")
        total = cur.fetchone()["c"]

        cur.execute(
            f"SELECT * FROM search_history WHERE {where} "
            f"ORDER BY raw_price {order} LIMIT %s OFFSET %s",
            params_query
        )
        rows = cur.fetchall()
        print(f"[category] brand '{brand}': {total} total, {len(rows)} rows")
        return rows, total
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════
# BRAND PAGE
# ════════════════════════════════════════════════════════════════
@category_bp.route("/category/brand/<brand>")
def brand_page(brand: str):
    brand = brand.lower()
    if brand not in BRAND_LABELS:
        abort(404)

    sort     = request.args.get("sort", "asc")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 60

    try:
        products, total = _query_by_brand(brand, sort, page, per_page)
    except Exception as e:
        print(f"[category] brand '{brand}' error: {e}")
        products, total = [], 0

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "category_new.html",
        view          = "brand",
        brand_key     = brand,
        brand_label   = BRAND_LABELS[brand],
        series_slug   = None,
        series_label  = BRAND_LABELS[brand],
        products      = products,
        total         = total,
        page          = page,
        total_pages   = total_pages,
        sort          = sort,
        all_categories = CATEGORIES,
    )


# ════════════════════════════════════════════════════════════════
# SERIES PAGE
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
            products, total = _query_by_brand("other", sort, page, per_page)
        else:
            products, total = _query_by_series(keyword, sort, page, per_page)
    except Exception as e:
        print(f"[category] series '{series_slug}' error: {e}")
        products, total = [], 0

    total_pages = max(1, (total + per_page - 1) // per_page)
    
    if "iphone" in series_slug:
        brand_key = "iphone"
    elif "samsung" in series_slug:
        brand_key = "samsung"
    else:
        brand_key = "other"

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