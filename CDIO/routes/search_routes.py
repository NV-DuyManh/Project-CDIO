from flask import Blueprint, render_template, request

from services.search_service import search_all_stores
from database.db import get_db_connection
from config.config import STORES
import pymysql.cursors

search_bp = Blueprint('search', __name__)


@search_bp.route("/", methods=["GET"])
def home():
    keyword      = request.args.get("keyword")
    all_products = []
    is_fast_load = False

    if keyword:
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
    cursor.execute("SELECT * FROM search_history ORDER BY created_at DESC LIMIT 200")
    data = cursor.fetchall()
    conn.close()
    return render_template("history.html", products=data)
