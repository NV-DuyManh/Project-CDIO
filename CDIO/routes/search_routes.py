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

    # 1. Ưu tiên gợi ý cứng
    for s in STATIC_SUGGESTIONS:
        if query in s.lower():
            seen.add(s.lower())
            results.append(s)

    # 2. Bổ sung từ lịch sử tìm kiếm (Dùng chung cho cộng đồng)
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
    """Hàm chạy ngầm: Tạm xóa cache cũ và cào lại giá mới nhất"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Xóa cache cũ của từ khóa này
        if user_id:
            cursor.execute("DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s) AND user_id = %s", (keyword.strip(), user_id))
        else:
            cursor.execute("DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s) AND user_id IS NULL", (keyword.strip(),))
        conn.commit()
        conn.close()

        # Gọi hàm cào (lúc này db đã trống nên bot buộc phải đi cào web)
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
    user_id = session.get('user_id') # Lấy ID người dùng từ Session

    # Nếu không gõ gì nhưng session có từ khóa cũ thì gợi ý lại
    if not keyword and 'last_keyword' in session:
        return redirect(url_for('search.home', keyword=session['last_keyword']))

    all_products = []
    is_fast_load = False
    is_background_updating = False

    if keyword:
        session['last_keyword'] = keyword
        
        # 1. TÌM TRONG DATABASE TRƯỚC (Stale)
        cached_data = get_data_from_db(keyword)
        
        if cached_data:
            # NẾU CÓ CŨ -> Trả về ngay lập tức cho khách xem
            all_products = cached_data
            is_fast_load = True
            is_background_updating = True # Bật cờ báo cho giao diện biết
            
            # 2. CHẠY NGẦM BOT CÀO DỮ LIỆU (While-revalidate)
            thread = threading.Thread(target=background_scrape_task, args=(keyword, user_id))
            thread.daemon = True
            thread.start()
        else:
            # NẾU CHƯA TỪNG CÓ -> Bắt buộc chờ để cào lần đầu tiên
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
    
    # Nếu chưa đăng nhập thì bắt đăng nhập hoặc hiện trang trống
    if not user_id:
        return render_template("history.html", products=[], msg="Vui lòng đăng nhập để xem lịch sử")

    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        
        # CHỈ LẤY LỊCH SỬ CỦA USER_ID ĐANG ĐĂNG NHẬP
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