from flask import Blueprint, render_template, redirect, url_for
import pymysql.cursors

from database.db import get_db_connection
from utils.helpers import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route("/admin")
@admin_required
def admin():
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT COUNT(*) as c FROM users");          users_count    = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM orders");         orders_count   = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM comments");       comments_count = cursor.fetchone()['c']
        cursor.execute("SELECT COUNT(*) as c FROM search_history"); products_count = cursor.fetchone()['c']
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
        cursor.execute("SELECT o.*, u.username FROM orders o LEFT JOIN users u ON o.user_id=u.id ORDER BY o.created_at DESC LIMIT 100")
        all_orders = cursor.fetchall()
        cursor.execute("SELECT c.*, u.username FROM comments c LEFT JOIN users u ON c.user_id=u.id ORDER BY c.created_at DESC LIMIT 100")
        all_comments = cursor.fetchall()
        cursor.execute("SELECT * FROM search_history ORDER BY created_at DESC LIMIT 100")
        all_products = cursor.fetchall()
        return render_template("admin.html",
                               stats={'users': users_count, 'orders': orders_count,
                                      'comments': comments_count, 'products': products_count},
                               users=users, all_orders=all_orders,
                               all_comments=all_comments, all_products=all_products)
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@admin_bp.route("/admin/delete/user/<int:uid>", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s AND is_admin=0", (uid,))
    conn.commit(); conn.close()
    return redirect(url_for('admin.admin'))


@admin_bp.route("/admin/delete/order/<int:oid>", methods=["POST"])
@admin_required
def admin_delete_order(oid):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id=%s", (oid,))
    conn.commit(); conn.close()
    return redirect(url_for('admin.admin'))


@admin_bp.route("/admin/delete/comment/<int:cid>", methods=["POST"])
@admin_required
def admin_delete_comment(cid):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM comments WHERE id=%s", (cid,))
    conn.commit(); conn.close()
    return redirect(url_for('admin.admin'))


@admin_bp.route("/admin/delete/product/<int:pid>", methods=["POST"])
@admin_required
def admin_delete_product(pid):
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("DELETE FROM search_history WHERE id=%s", (pid,))
    conn.commit(); conn.close()
    return redirect(url_for('admin.admin'))
