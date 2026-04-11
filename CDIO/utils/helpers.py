"""
utils/helpers.py
================
Decorators dùng chung: login_required, admin_required
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Vui lòng đăng nhập để tiếp tục.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kiểm tra đăng nhập trước
        if not session.get('user_id'):
            flash('Vui lòng đăng nhập.', 'error')
            return redirect(url_for('auth.login'))

        # FIX: is_admin có thể là bool True, int 1, hoặc string "1"
        # → dùng truthy check thay vì so sánh strict
        is_admin = session.get('is_admin')
        if not is_admin:
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('search.home'))

        return f(*args, **kwargs)
    return decorated_function
