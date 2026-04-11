# routes/category_routes.py
"""
Chỉ lấy dữ liệu từ DB — KHÔNG tự cào khi vào trang danh mục.
Route:
  /category/<brand>/<series_key>/<keyword_slug>
  /category/<brand>/<series_key>
  /category/<brand>
"""

from flask import Blueprint, render_template, abort, session
from database.db import get_data_from_db
from config.categories import CATEGORIES

category_bp = Blueprint("category", __name__)


def _db_products_for_keyword(keyword: str) -> list:
    """Lấy từ DB, trả về list rỗng nếu chưa có — không cào."""
    try:
        rows = get_data_from_db(keyword)
        return rows if rows else []
    except Exception:
        return []


@category_bp.route("/category/<brand>")
def brand_page(brand: str):
    """Trang thương hiệu — hiện danh sách series."""
    brand = brand.lower()
    cat = CATEGORIES.get(brand)
    if not cat:
        abort(404)
    return render_template(
        "category.html",
        view="brand",
        brand_key=brand,
        brand=cat,
        series=None,
        series_key=None,
        model_keyword=None,
        products=[],
        all_categories=CATEGORIES,
    )


@category_bp.route("/category/<brand>/<series_key>")
def series_page(brand: str, series_key: str):
    """Trang series — hiện danh sách model."""
    brand = brand.lower()
    cat = CATEGORIES.get(brand)
    if not cat:
        abort(404)
    series = cat["series"].get(series_key)
    if not series:
        abort(404)
    return render_template(
        "category.html",
        view="series",
        brand_key=brand,
        brand=cat,
        series=series,
        series_key=series_key,
        model_keyword=None,
        products=[],
        all_categories=CATEGORIES,
    )


@category_bp.route("/category/<brand>/<series_key>/<path:model_keyword>")
def model_page(brand: str, series_key: str, model_keyword: str):
    """Trang model — lấy sản phẩm từ DB theo keyword."""
    brand = brand.lower()
    cat = CATEGORIES.get(brand)
    if not cat:
        abort(404)
    series = cat["series"].get(series_key)
    if not series:
        abort(404)

    # Giải mã keyword từ URL (dấu - thành space)
    keyword = model_keyword.replace("-", " ")

    # Tìm label đúng từ config
    model_label = keyword
    for m in series["models"]:
        if m["keyword"].lower() == keyword.lower():
            model_label = m["label"]
            keyword = m["keyword"]
            break

    # Chỉ lấy từ DB — không cào
    products = _db_products_for_keyword(keyword)

    # Dedup
    seen, unique = set(), []
    for p in products:
        ident = (p.get("site"), p.get("title"), p.get("raw_price"))
        if ident not in seen:
            seen.add(ident)
            unique.append(p)
    products = sorted(unique, key=lambda x: x.get("raw_price", 0))

    return render_template(
        "category.html",
        view="model",
        brand_key=brand,
        brand=cat,
        series=series,
        series_key=series_key,
        model_keyword=keyword,
        model_label=model_label,
        products=products,
        all_categories=CATEGORIES,
    )