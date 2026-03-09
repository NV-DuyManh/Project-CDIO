from flask import Blueprint, render_template, request, session, redirect, url_for

from services.search_service import search_all_stores
from database.db import get_db_connection
from config.config import STORES
import pymysql.cursors

search_bp = Blueprint('search', __name__)


@search_bp.route("/", methods=["GET"])
def home():
    keyword      = request.args.get("keyword")
    
    # Nếu không có keyword trên URL nhưng có trong session thì chuyển hướng về lại kết quả cũ
    if not keyword and 'last_keyword' in session:
        return redirect(url_for('search.home', keyword=session['last_keyword']))
        
    all_products = []
    is_fast_load = False

    if keyword:
        # Lưu từ khóa hiện tại vào session
        session['last_keyword'] = keyword
        all_products, is_fast_load = search_all_stores(keyword)

    return render_template("index.html",
                           products=all_products,
                           keyword=keyword,
                           is_fast_load=is_fast_load,
                           store_count=len(STORES))


@search_bp.route("/history", methods=["GET"])
def history():
    conn   = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Sửa lại: Lấy đợt cào mới nhất (Time DESC) nhưng giữ đúng thứ tự sản phẩm trong đợt đó (ID ASC)
    cursor.execute("SELECT * FROM search_history ORDER BY created_at DESC, id ASC LIMIT 200")
    
    data = cursor.fetchall()
    conn.close()
    return render_template("history.html", products=data)