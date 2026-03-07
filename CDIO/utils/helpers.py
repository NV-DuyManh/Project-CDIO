from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Vui lòng đăng nhập để tiếp tục.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('search.home'))
        return f(*args, **kwargs)
    return decorated
