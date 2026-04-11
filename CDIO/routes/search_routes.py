# routes/search_routes.py
import threading
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from services.search_service import search_all_stores
from database.db import (
    get_db_connection, save_to_db, get_data_from_db, search_db_only
)
from config.config import STORES
import pymysql.cursors
from config.categories import CATEGORIES

search_bp = Blueprint('search', __name__)

STATIC_SUGGESTIONS = [
    "iPhone 15", "iPhone 15 Pro Max", "Samsung S24 Ultra", "Xiaomi 14", "MacBook M3",
    "iPhone 16", "OPPO Reno 12", "Laptop Dell XPS", "HP Spectre", "Asus ROG"
]


# ════════════════════════════════════════════════════════════════════
# API GỢI Ý
# ════════════════════════════════════════════════════════════════════
@search_bp.route("/api/suggestions")
def suggestions():
    query = request.args.get("q", "").strip().lower()
    if len(query) < 1:
        return jsonify([])
    results, seen = [], set()
    for s in STATIC_SUGGESTIONS:
        if query in s.lower():
            seen.add(s.lower())
            results.append(s)
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT DISTINCT keyword FROM search_history WHERE LOWER(keyword) LIKE %s LIMIT 5",
            (f"%{query}%",)
        )
        for row in cursor.fetchall():
            kw = row["keyword"].strip()
            if kw.lower() not in seen:
                results.append(kw)
        conn.close()
    except Exception:
        pass
    return jsonify(results[:8])


# ════════════════════════════════════════════════════════════════════
# BACKGROUND SCRAPE (chỉ gọi từ /scrape route riêng)
# ════════════════════════════════════════════════════════════════════
def _background_scrape(keyword, user_id):
    try:
        fresh, is_fast = search_all_stores(keyword)
        if fresh and not is_fast:
            save_to_db(keyword, fresh, user_id=user_id)
        print(f"[Background] Cập nhật xong: {keyword}")
    except Exception as e:
        print(f"[Background] Lỗi: {e}")


# ════════════════════════════════════════════════════════════════════
# TRANG CHỦ / TÌM KIẾM  — CHỈ ĐỌC DB
# ════════════════════════════════════════════════════════════════════
@search_bp.route("/", methods=["GET"])
def home():
    keyword = request.args.get("keyword", "").strip()
    sort    = request.args.get("sort", "asc")        # 'asc' | 'desc'
    page    = max(1, int(request.args.get("page", 1)))
    per_page = 60

    all_products = []
    total        = 0
    total_pages  = 1
    db_miss      = False   # True khi không có gì trong DB

    if keyword:
        session['last_keyword'] = keyword

        # ── Truy vấn DB thuần ────────────────────────────────────────
        all_products, total = search_db_only(keyword, sort=sort, page=page, per_page=per_page)
        total_pages = max(1, (total + per_page - 1) // per_page)

        if not all_products:
            db_miss = True   # Thông báo cho user biết chưa có dữ liệu

    return render_template(
        "index.html",
        all_categories=CATEGORIES,
        products=all_products,
        keyword=keyword,
        sort=sort,
        page=page,
        total_pages=total_pages,
        total=total,
        db_miss=db_miss,
        store_count=len(STORES),
        is_fast_load=True,
        is_background_updating=False,
    )


# ════════════════════════════════════════════════════════════════════
# SCRAPE ROUTE RIÊNG — kích hoạt cào thủ công (admin / trusted user)
# ════════════════════════════════════════════════════════════════════
@search_bp.route("/scrape", methods=["GET"])
def scrape():
    """
    Cho phép kích hoạt cào live với keyword cụ thể.
    Gọi ngầm rồi redirect về trang chủ với keyword đó.
    """
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return redirect(url_for("search.home"))

    user_id = session.get("user_id")
    thread  = threading.Thread(target=_background_scrape, args=(keyword, user_id))
    thread.daemon = True
    thread.start()

    # Redirect ngay về trang kết quả — dữ liệu mới sẽ xuất hiện khi F5
    return redirect(url_for("search.home", keyword=keyword, scraping="1"))


# ════════════════════════════════════════════════════════════════════
# LỊCH SỬ
# ════════════════════════════════════════════════════════════════════


# ════════════════════════════════════════════════════════════════════
# BOT LOGS
# ════════════════════════════════════════════════════════════════════
@search_bp.route("/api/bot-logs")
def get_bot_logs():
    try:
        from app import BOT_LOGS
        return jsonify(BOT_LOGS)
    except Exception:
        return jsonify(["[SYSTEM] Robot đang khởi động..."])