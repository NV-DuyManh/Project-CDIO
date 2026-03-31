import threading
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
from services.search_service import search_all_stores
from database.db import get_db_connection, save_to_db, get_data_from_db
from config.config import STORES
import pymysql.cursors

search_bp = Blueprint('search', __name__)

# ════════════════════════════════════════════════════════════════════
# GỢI Ý TỪ KHÓA (GIỮ NGUYÊN DANH SÁCH CỨNG)
# ════════════════════════════════════════════════════════════════════
STATIC_SUGGESTIONS = [
    "iPhone 15", "iPhone 15 Pro Max", "Samsung S24 Ultra", "Xiaomi 14", "MacBook M3",
    "iPhone 16", "OPPO Reno 12", "Laptop Dell XPS", "HP Spectre", "Asus ROG"
]

@search_bp.route("/api/suggestions")
def suggestions():
    query = request.args.get("q", "").strip().lower()
    if len(query) < 1: return jsonify([])

    results = []
    seen = set()

    for s in STATIC_SUGGESTIONS:
        if query in s.lower():
            seen.add(s.lower())
            results.append(s)

    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT DISTINCT keyword FROM search_history WHERE LOWER(keyword) LIKE %s LIMIT 5", (f"%{query}%",))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            kw = row["keyword"].strip()
            if kw.lower() not in seen:
                results.append(kw)
    except: pass
    return jsonify(results[:8])

# ════════════════════════════════════════════════════════════════════
# HÀM CHẠY NGẦM (BACKGROUND TASK)
# ════════════════════════════════════════════════════════════════════
def background_scrape_task(keyword, user_id):
    """Hàm chạy ngầm: Cào giá mới nhất, xong xuôi mới lưu đè lên cache cũ"""
    try:
        fresh_products, is_fast = search_all_stores(keyword)
        
        if fresh_products and not is_fast:
            save_to_db(keyword, fresh_products, user_id=user_id)
        print(f"[Background] Đã cập nhật xong giá mới nhất cho: {keyword}")
    except Exception as e:
        print(f"[Background] Lỗi cào ngầm: {e}")

# ════════════════════════════════════════════════════════════════════
# TRANG CHỦ / TÌM KIẾM
# ════════════════════════════════════════════════════════════════════

@search_bp.route("/", methods=["GET"])
def home():
    keyword = request.args.get("keyword")
    updated = request.args.get("updated")
    user_id = session.get('user_id')

    if not keyword and 'last_keyword' in session:
        return redirect(url_for('search.home', keyword=session['last_keyword']))

    all_products = []
    is_fast_load = False
    is_background_updating = False

    if keyword:
        session['last_keyword'] = keyword
        
        # 1. TÌM TRONG DATABASE TRƯỚC
        cached_data = get_data_from_db(keyword)
        
        if cached_data:
            all_products = cached_data
            is_fast_load = True
            
            # CỨ TÌM KIẾM BÌNH THƯỜNG LÀ CÀO NGẦM (Miễn là không có cờ updated=1)
            # Đã bỏ luật chặn 30 phút!
            if updated != "1":
                is_background_updating = True 
                thread = threading.Thread(target=background_scrape_task, args=(keyword, user_id))
                thread.daemon = True
                thread.start()
        else:
            # 2. NẾU CHƯA CÓ TRONG DB THÌ BẮT BUỘC CÀO LẦN ĐẦU
            all_products, is_fast_load = search_all_stores(keyword)
            if all_products and not is_fast_load:
                save_to_db(keyword, all_products, user_id=user_id)

    return render_template("index.html",
                           products=all_products,
                           keyword=keyword,
                           is_fast_load=is_fast_load,
                           is_background_updating=is_background_updating,
                           store_count=len(STORES))

# ════════════════════════════════════════════════════════════════════
# LỊCH SỬ CÀO
# ════════════════════════════════════════════════════════════════════

@search_bp.route("/history", methods=["GET"])
def history():
    user_id = session.get('user_id')
    
    if not user_id:
        return render_template("history.html", products=[], msg="Vui lòng đăng nhập để xem lịch sử")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        sql = "SELECT * FROM search_history WHERE user_id = %s ORDER BY created_at DESC LIMIT 100"
        cursor.execute(sql, (user_id,))
        data = cursor.fetchall()
    except Exception as e:
        print(f"Lỗi lấy lịch sử: {e}")
        data = []
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            
    return render_template("history.html", products=data)

# ════════════════════════════════════════════════════════════════════
# NHẬT KÝ BOT (DÙNG CHO ADMIN)
# ════════════════════════════════════════════════════════════════════

@search_bp.route("/api/bot-logs")
def get_bot_logs():
    try:
        from app import BOT_LOGS
        return jsonify(BOT_LOGS)
    except:
        return jsonify(["[SYSTEM] Robot đang khởi động..."])