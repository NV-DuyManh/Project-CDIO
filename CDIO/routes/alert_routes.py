"""
routes/alert_routes.py
======================
Route mới cho tính năng Price Drop Alert.
Nguyên lý Open-Closed: file HOÀN TOÀN MỚI, không động vào code cũ.

Đăng ký trong app.py:
    from routes.alert_routes import alert_bp
    app.register_blueprint(alert_bp)
"""

from flask import Blueprint, request, jsonify, session
import pymysql.cursors

from database.db import get_db_connection
from utils.helpers import login_required

alert_bp = Blueprint('alert', __name__)


# ── Helpers ────────────────────────────────────────────────────────

def _conn():
    return get_db_connection()


# ── POST /api/alert/add ────────────────────────────────────────────

@alert_bp.route('/api/alert/add', methods=['POST'])
@login_required
def add_alert():
    """
    Nhận JSON: { title, keyword, target_price }
    Lưu vào bảng price_alerts gắn với user đang đăng nhập.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'ok': False, 'error': 'Dữ liệu không hợp lệ'}), 400

    title        = (data.get('title') or '').strip()
    keyword      = (data.get('keyword') or '').strip()
    target_price = data.get('target_price')
    user_id      = session['user_id']

    # Validation
    if not title:
        return jsonify({'ok': False, 'error': 'Thiếu tên sản phẩm'}), 400
    if not keyword:
        return jsonify({'ok': False, 'error': 'Thiếu từ khóa'}), 400
    try:
        target_price = int(str(target_price).replace(',', '').replace('.', ''))
        if target_price <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Mức giá không hợp lệ'}), 400

    conn = None
    try:
        conn = _conn()
        cur  = conn.cursor(pymysql.cursors.DictCursor)

        # Kiểm tra đã có alert giống hệt chưa (tránh duplicate)
        cur.execute(
            """SELECT id FROM price_alerts
               WHERE user_id=%s AND keyword=%s AND is_active=1""",
            (user_id, keyword)
        )
        existing = cur.fetchone()
        if existing:
            # Cập nhật target_price thay vì tạo mới
            cur.execute(
                "UPDATE price_alerts SET target_price=%s, product_title=%s WHERE id=%s",
                (target_price, title, existing['id'])
            )
            conn.commit()
            return jsonify({
                'ok': True,
                'message': f'Đã cập nhật mức giá theo dõi cho "{title}"',
                'updated': True
            })

        # Tạo mới
        cur.execute(
            """INSERT INTO price_alerts
               (user_id, product_title, keyword, target_price, is_active)
               VALUES (%s, %s, %s, %s, 1)""",
            (user_id, title, keyword, target_price)
        )
        conn.commit()
        return jsonify({
            'ok': True,
            'message': f'Đã đặt theo dõi giá cho "{title}"!\nBạn sẽ nhận email khi giá xuống dưới {target_price:,}đ',
        })

    except Exception as e:
        print(f'[Alert] add_alert error: {e}')
        return jsonify({'ok': False, 'error': 'Lỗi hệ thống, vui lòng thử lại'}), 500
    finally:
        if conn:
            conn.close()


# ── GET /api/alert/list ────────────────────────────────────────────

@alert_bp.route('/api/alert/list', methods=['GET'])
@login_required
def list_alerts():
    """Trả về danh sách các alert đang active của user hiện tại."""
    user_id = session['user_id']
    conn = None
    try:
        conn = _conn()
        cur  = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            """SELECT id, product_title, keyword, target_price, is_active, created_at
               FROM price_alerts
               WHERE user_id=%s
               ORDER BY created_at DESC
               LIMIT 50""",
            (user_id,)
        )
        rows = cur.fetchall() or []

        import datetime
        safe = []
        for r in rows:
            safe.append({
                'id':            r['id'],
                'product_title': r['product_title'],
                'keyword':       r['keyword'],
                'target_price':  r['target_price'],
                'is_active':     bool(r['is_active']),
                'created_at':    str(r['created_at']) if isinstance(r['created_at'], datetime.datetime) else r['created_at'],
            })
        return jsonify(safe)

    except Exception as e:
        print(f'[Alert] list_alerts error: {e}')
        return jsonify([]), 500
    finally:
        if conn:
            conn.close()


# ── DELETE /api/alert/remove/<id> ─────────────────────────────────

@alert_bp.route('/api/alert/remove/<int:alert_id>', methods=['POST'])
@login_required
def remove_alert(alert_id):
    """Xóa / hủy theo dõi giá."""
    user_id = session['user_id']
    conn = None
    try:
        conn = _conn()
        cur  = conn.cursor()
        cur.execute(
            "UPDATE price_alerts SET is_active=0 WHERE id=%s AND user_id=%s",
            (alert_id, user_id)
        )
        conn.commit()
        return jsonify({'ok': True})
    except Exception as e:
        print(f'[Alert] remove_alert error: {e}')
        return jsonify({'ok': False}), 500
    finally:
        if conn:
            conn.close()