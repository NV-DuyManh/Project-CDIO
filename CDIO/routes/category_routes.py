# routes/category_routes.py
"""
Trang danh mục — chỉ đọc DB, KHÔNG cào live.

Routes:
  /category/brand/<brand>          → iPhone / Samsung / other
  /category/series/<series_slug>   → iPhone 17, Galaxy S Series …
  /category/<brand>/<series_key>/<model_keyword>   (giữ tương thích cũ)
"""

from flask import Blueprint, render_template, abort, request, session
from database.db import get_products_by_brand, get_products_by_series
from config.categories import CATEGORIES

category_bp = Blueprint("category", __name__)

# ── Mapping series slug → từ khóa LIKE ──────────────────────────────
# Thêm vào đây khi có series mới; key phải khớp với URL slug
SERIES_KEYWORDS = {
    # iPhone
    "iphone-17": "iPhone 17",
    "iphone-16": "iPhone 16",
    "iphone-15": "iPhone 15",
    "iphone-14": "iPhone 14",
    # Samsung S
    "samsung-s25": "Galaxy S25",
    "samsung-s24": "Galaxy S24",
    # Samsung A
    "samsung-a":   "Galaxy A",
    # Samsung Z
    "samsung-z":   "Galaxy Z",
}

BRAND_LABELS = {
    "iphone":  "iPhone",
    "samsung": "Samsung",
    "other":   "Thương hiệu khác",
}


# ════════════════════════════════════════════════════════════════════
# BRAND PAGE  —  /category/brand/<brand>
# ════════════════════════════════════════════════════════════════════
@category_bp.route("/category/brand/<brand>")
def brand_page(brand: str):
    brand = brand.lower()
    if brand not in BRAND_LABELS:
        abort(404)

    sort    = request.args.get("sort", "asc")
    page    = max(1, int(request.args.get("page", 1)))
    per_page = 60

    products, total = get_products_by_brand(brand, sort=sort, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        "category_new.html",
        view         = "brand",
        brand_key    = brand,
        brand_label  = BRAND_LABELS[brand],
        series_slug  = None,
        series_label = None,
        products     = products,
        total        = total,
        page         = page,
        total_pages  = total_pages,
        sort         = sort,
        all_categories = CATEGORIES,
    )


# ════════════════════════════════════════════════════════════════════
# SERIES PAGE  —  /category/series/<series_slug>
# ════════════════════════════════════════════════════════════════════
@category_bp.route("/category/series/<series_slug>")
def series_page(series_slug: str):
    series_slug = series_slug.lower()
    keyword = SERIES_KEYWORDS.get(series_slug)
    if not keyword:
        abort(404)

    sort     = request.args.get("sort", "asc")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 60

    products, total = get_products_by_series(keyword, sort=sort, page=page, per_page=per_page)
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Xác định brand_key từ slug để breadcrumb hoạt động
    brand_key = "iphone" if "iphone" in series_slug else "samsung"

    return render_template(
        "category_new.html",
        view         = "series",
        brand_key    = brand_key,
        brand_label  = BRAND_LABELS.get(brand_key, brand_key.title()),
        series_slug  = series_slug,
        series_label = keyword,
        products     = products,
        total        = total,
        page         = page,
        total_pages  = total_pages,
        sort         = sort,
        all_categories = CATEGORIES,
    )


# ════════════════════════════════════════════════════════════════════
# BACKWARD COMPAT — giữ nguyên route cũ để không vỡ link đã lưu
# /category/<brand>/<series_key>/<model_keyword>
# ════════════════════════════════════════════════════════════════════
@category_bp.route("/category/<brand>")
def old_brand_page(brand: str):
    from flask import redirect, url_for
    return redirect(url_for("category.brand_page", brand=brand.lower()))


@category_bp.route("/category/<brand>/<series_key>")
def old_series_page(brand: str, series_key: str):
    from flask import redirect, url_for
    slug = f"{brand.lower()}-{series_key.split('-')[-1]}" if '-' in series_key else series_key
    if slug in SERIES_KEYWORDS:
        return redirect(url_for("category.series_page", series_slug=slug))
    return redirect(url_for("category.brand_page", brand=brand.lower()))


@category_bp.route("/category/<brand>/<series_key>/<path:model_keyword>")
def old_model_page(brand: str, series_key: str, model_keyword: str):
    from flask import redirect, url_for
    kw = model_keyword.replace("-", " ")
    return redirect(url_for("search.home", keyword=kw))