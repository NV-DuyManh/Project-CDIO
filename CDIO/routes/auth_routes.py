"""
routes/auth_routes.py
=====================
FIX: Đảm bảo session['is_admin'] luôn là Python bool thực sự,
     không phải None hoặc bytearray từ MySQL.
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql.cursors

from database.db import get_db_connection
from utils.helpers import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get('user_id'):
        return redirect(url_for('search.home'))
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not username or not email or not password:
            flash('Vui lòng điền đầy đủ thông tin.', 'error')
            return render_template("register.html")
        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự.', 'error')
            return render_template("register.html")
        try:
            conn   = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
            if cursor.fetchone():
                flash('Tên đăng nhập hoặc email đã tồn tại.', 'error')
                return render_template("register.html")
            cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s,%s,%s)",
                           (username, email, generate_password_hash(password)))
            conn.commit()
            flash('Đăng ký thành công! Hãy đăng nhập.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Lỗi hệ thống: {e}', 'error')
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get('user_id'):
        return redirect(url_for('search.home'))
    if request.method == "POST":
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        try:
            conn   = get_db_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user['password_hash'], password):
                session['user_id']  = user['id']
                session['username'] = user['username']

                # FIX: Ép kiểu rõ ràng — MySQL trả TINYINT(1) có thể là int 0/1
                # bool(1) = True, bool(0) = False, bool(None) = False
                raw_admin = user.get('is_admin', 0)
                session['is_admin'] = bool(int(raw_admin)) if raw_admin is not None else False

                flash(f'Chào mừng trở lại, {username}!', 'success')
                return redirect(url_for('search.home'))
            flash('Tên đăng nhập hoặc mật khẩu không đúng.', 'error')
        except Exception as e:
            flash(f'Lỗi hệ thống: {e}', 'error')
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash('Đã đăng xuất thành công.', 'info')
    return redirect(url_for('search.home'))


@auth_bp.route("/profile")
@login_required
def profile():
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        cursor.execute("SELECT * FROM favorites WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
        favorites = cursor.fetchall()
        cursor.execute("SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
        orders = cursor.fetchall()
        cursor.execute("SELECT COUNT(*) as c FROM comments WHERE user_id=%s", (user_id,))
        comments_count = cursor.fetchone()['c']
        return render_template("profile.html", user=user, favorites=favorites, orders=orders,
                               orders_count=len(orders), favorites_count=len(favorites),
                               comments_count=comments_count)
    finally:
        if 'conn' in locals() and conn:
            conn.close()
