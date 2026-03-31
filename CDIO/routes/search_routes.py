from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
import pymysql.cursors

from services.search_service     import search_all_stores
from services.keyword_normalizer import normalize_keyword, get_instant_suggestions
from database.db                 import get_db_connection, get_price_history
from config.config               import STORES, CACHE_TTL_SECONDS

search_bp = Blueprint("search", __name__)


# ── HOME / SEARCH ─────────────────────────────────────────────────

@search_bp.route("/", methods=["GET"])
def home():
    keyword = request.args.get("keyword", "").strip() or None

    if not keyword and "last_keyword" in session:
        return redirect(url_for("search.home", keyword=session["last_keyword"]))

    all_products = []
    is_fast_load = False
    is_stale     = False

    if keyword:
        session["last_keyword"] = keyword
        user_id      = session.get("user_id")
        all_products, is_fast_load, is_stale = search_all_stores(keyword, user_id)

    return render_template(
        "index.html",
        products     = all_products,
        keyword      = keyword,
        is_fast_load = is_fast_load,
        is_stale     = is_stale,       # ← NEW: triggers SWR UI
        store_count  = len(STORES),
    )


# ── HISTORY ───────────────────────────────────────────────────────

@search_bp.route("/history")
def history():
    conn   = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM search_history ORDER BY created_at DESC LIMIT 200")
    data = cursor.fetchall()
    conn.close()
    return render_template("history.html", products=data)


# ════════════════════════════════════════════════════════════════════
# JSON APIS
# ════════════════════════════════════════════════════════════════════

@search_bp.route("/api/suggest")
def api_suggest():
    """
    Instant-search autocomplete.
    GET /api/suggest?q=ipho
    Returns: [{"text": "iphone 15 pro", "type": "popular"}, …]
    """
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    # Fetch trending keywords from DB
    db_rows = []
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        normalized = normalize_keyword(q)
        cursor.execute(
            """SELECT keyword, search_count FROM keyword_log
               WHERE keyword LIKE %s
               ORDER BY search_count DESC
               LIMIT 10""",
            (f"%{normalized}%",),
        )
        db_rows = cursor.fetchall()
    except Exception:
        pass
    finally:
        if "conn" in locals() and conn:
            conn.close()

    suggestions = get_instant_suggestions(q, db_results=db_rows, limit=8)
    return jsonify(suggestions)


@search_bp.route("/api/cache-status")
def api_cache_status():
    """
    SWR polling endpoint.
    GET /api/cache-status?keyword=iphone+15
    Returns: {"status": "fresh"} or {"status": "stale"}
    Used by frontend to know when background refresh is done.
    """
    keyword = request.args.get("keyword", "").strip()
    if not keyword:
        return jsonify({"status": "unknown"})

    normalized = normalize_keyword(keyword)
    fresh = get_db_connection()  # just test
    # Re-use get_data_from_db with fresh TTL
    from database.db import get_data_from_db
    data = get_data_from_db(normalized, ttl=CACHE_TTL_SECONDS)
    return jsonify({"status": "fresh" if data else "stale"})


@search_bp.route("/api/filter")
def api_filter():
    """
    Server-side fast-filter for cached products.
    GET /api/filter?keyword=iphone+15&sort=price_asc&storage=256gb&max_price=30000000
    """
    keyword   = request.args.get("keyword", "").strip()
    sort_by   = request.args.get("sort",      "price_asc")
    storage   = request.args.get("storage",   "").strip()
    min_price = request.args.get("min_price", 0,  type=int)
    max_price = request.args.get("max_price", 0,  type=int)

    if not keyword:
        return jsonify([])

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)

        sql    = ["SELECT * FROM search_history WHERE LOWER(keyword)=LOWER(%s)"]
        params = [keyword]

        if storage:
            sql.append("AND title LIKE %s")
            params.append(f"%{storage}%")
        if min_price:
            sql.append("AND raw_price >= %s")
            params.append(min_price)
        if max_price:
            sql.append("AND raw_price <= %s")
            params.append(max_price)

        order_col = "raw_price ASC" if sort_by != "price_desc" else "raw_price DESC"
        sql.append(f"ORDER BY {order_col}")

        cursor.execute(" ".join(sql), params)
        return jsonify(cursor.fetchall())
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    finally:
        if "conn" in locals() and conn:
            conn.close()


@search_bp.route("/api/price-history")
def api_price_history():
    """
    Price history for sparkline charts.
    GET /api/price-history?keyword=iphone+15&days=30
    Returns: [{site, avg_price, min_price, record_date}, …]
    """
    keyword = request.args.get("keyword", "").strip()
    days    = request.args.get("days", 30, type=int)
    if not keyword:
        return jsonify([])

    data = get_price_history(normalize_keyword(keyword), days=days)
    # Convert date objects to strings for JSON serialisation
    for row in data:
        if hasattr(row.get("record_date"), "isoformat"):
            row["record_date"] = row["record_date"].isoformat()
    return jsonify(data)