"""
routes/admin_routes.py — Robust version
Bọc mỗi query trong try/except để tránh crash toàn trang khi 1 bảng lỗi.
"""

from flask import Blueprint, render_template, redirect, url_for, jsonify, request
import pymysql.cursors

from database.db import get_db_connection
from utils.helpers import admin_required

admin_bp = Blueprint('admin', __name__)


# ── Helpers ────────────────────────────────────────────────────────────
def _conn():
    return get_db_connection()

def _q(cursor, sql, params=()):
    """Chạy query, trả list[dict], không crash."""
    try:
        cursor.execute(sql, params)
        return cursor.fetchall() or []
    except Exception as e:
        print(f"[Admin query] {e}")
        return []

def _q1(cursor, sql, params=()):
    """Chạy query, trả 1 row dict."""
    try:
        cursor.execute(sql, params)
        return cursor.fetchone() or {}
    except Exception as e:
        print(f"[Admin query1] {e}")
        return {}


# ── /admin ─────────────────────────────────────────────────────────────
@admin_bp.route("/admin")
@admin_required
def admin():
    conn = None
    try:
        conn = _conn()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        stats = {
            'users':    _q1(cur, "SELECT COUNT(*) AS c FROM users").get('c', 0),
            'orders':   _q1(cur, "SELECT COUNT(*) AS c FROM orders").get('c', 0),
            'comments': _q1(cur, "SELECT COUNT(*) AS c FROM comments").get('c', 0),
            'products': _q1(cur, "SELECT COUNT(*) AS c FROM search_history").get('c', 0),
        }

        users        = _q(cur, "SELECT * FROM users ORDER BY created_at DESC")
        all_orders   = _q(cur,
            "SELECT o.*, u.username FROM orders o "
            "LEFT JOIN users u ON o.user_id=u.id "
            "ORDER BY o.created_at DESC LIMIT 100")
        all_comments = _q(cur,
            "SELECT c.*, u.username FROM comments c "
            "LEFT JOIN users u ON c.user_id=u.id "
            "ORDER BY c.created_at DESC LIMIT 100")
        all_products = _q(cur,
            "SELECT * FROM search_history ORDER BY created_at DESC LIMIT 100")

    except Exception as e:
        print(f"[Admin] Fatal: {e}")
        stats        = {'users': 0, 'orders': 0, 'comments': 0, 'products': 0}
        users        = []
        all_orders   = []
        all_comments = []
        all_products = []
    finally:
        if conn:
            conn.close()

    return render_template("admin.html",
        stats=stats, users=users,
        all_orders=all_orders,
        all_comments=all_comments,
        all_products=all_products,
    )


# ── Delete routes ──────────────────────────────────────────────────────
@admin_bp.route("/admin/delete/user/<int:uid>", methods=["POST"])
@admin_required
def admin_delete_user(uid):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id=%s AND is_admin=0", (uid,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin.admin'))


@admin_bp.route("/admin/delete/order/<int:oid>", methods=["POST"])
@admin_required
def admin_delete_order(oid):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM orders WHERE id=%s", (oid,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin.admin'))


@admin_bp.route("/admin/delete/comment/<int:cid>", methods=["POST"])
@admin_required
def admin_delete_comment(cid):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM comments WHERE id=%s", (cid,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin.admin'))


@admin_bp.route("/admin/delete/product/<int:pid>", methods=["POST"])
@admin_required
def admin_delete_product(pid):
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM search_history WHERE id=%s", (pid,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin.admin'))