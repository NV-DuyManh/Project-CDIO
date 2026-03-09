import re
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
import pymysql.cursors

from database.db import get_db_connection
from utils.helpers import login_required

cart_bp = Blueprint('cart', __name__)


# ── FAVORITES ────────────────────────────────────────────────────────

@cart_bp.route("/favorites/add", methods=["POST"])
@login_required
def favorites_add():
    data    = request.get_json()
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO favorites (user_id, title, price_str, img, link, site) VALUES (%s,%s,%s,%s,%s,%s)",
            (user_id, data.get('title'), data.get('price_str'),
             data.get('img'), data.get('link'), data.get('site'))
        )
        conn.commit()
        return jsonify({'ok': True})
    except Exception:
        return jsonify({'ok': False}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@cart_bp.route("/favorites/remove/<int:fav_id>", methods=["POST"])
@login_required
def favorites_remove(fav_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE id=%s AND user_id=%s", (fav_id, session['user_id']))
        conn.commit()
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    return redirect(url_for('auth.profile'))


# ── CART ─────────────────────────────────────────────────────────────

@cart_bp.route("/cart")
@login_required
def cart():
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM cart WHERE user_id=%s", (user_id,))
        items = cursor.fetchall()
        return render_template("cart.html", cart_items=items)
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@cart_bp.route("/cart/add", methods=["POST"])
@login_required
def cart_add():
    data    = request.get_json()
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT id, quantity FROM cart WHERE user_id=%s AND title=%s",
                       (user_id, data.get('title')))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE cart SET quantity=quantity+1 WHERE id=%s", (existing['id'],))
        else:
            cursor.execute(
                "INSERT INTO cart (user_id, title, price_str, img, link, site, quantity) VALUES (%s,%s,%s,%s,%s,%s,1)",
                (user_id, data.get('title'), data.get('price_str'),
                 data.get('img'), data.get('link'), data.get('site'))
            )
        conn.commit()
        cursor.execute("SELECT COUNT(*) as c FROM cart WHERE user_id=%s", (user_id,))
        count = cursor.fetchone()['c']
        return jsonify({'ok': True, 'count': count})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@cart_bp.route("/cart/count")
def cart_count():
    if not session.get('user_id'):
        return jsonify({'count': 0})
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT COUNT(*) as c FROM cart WHERE user_id=%s", (session['user_id'],))
        count = cursor.fetchone()['c']
        return jsonify({'count': count})
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@cart_bp.route("/cart/update/<int:item_id>", methods=["POST"])
@login_required
def cart_update(item_id):
    data    = request.get_json()
    delta   = data.get('delta', 0)
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT quantity FROM cart WHERE id=%s AND user_id=%s", (item_id, user_id))
        row = cursor.fetchone()
        if not row:
            return jsonify({'ok': False}), 404
        new_qty = row['quantity'] + delta
        if new_qty <= 0:
            cursor.execute("DELETE FROM cart WHERE id=%s", (item_id,))
            conn.commit()
            return jsonify({'ok': True, 'removed': True})
        cursor.execute("UPDATE cart SET quantity=%s WHERE id=%s", (new_qty, item_id))
        conn.commit()
        return jsonify({'ok': True, 'quantity': new_qty})
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@cart_bp.route("/cart/remove/<int:item_id>", methods=["POST"])
@login_required
def cart_remove(item_id):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (item_id, session['user_id']))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        if 'conn' in locals() and conn:
            conn.close()


@cart_bp.route("/cart/clear", methods=["POST"])
@login_required
def cart_clear():
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cart WHERE user_id=%s", (session['user_id'],))
        conn.commit()
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    return redirect(url_for('cart.cart'))


# ── CHECKOUT ─────────────────────────────────────────────────────────

def _calc_cart_totals(user_id):
    conn   = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM cart WHERE user_id=%s", (user_id,))
    items     = cursor.fetchall()
    conn.close()
    total_raw = 0
    for item in items:
        nums       = re.findall(r'\d+', item['price_str'] or '0')
        price      = int(''.join(nums)) if nums else 0
        total_raw += price * item['quantity']
    subtotal_str = f"{total_raw:,}đ".replace(',', '.')
    total_str    = f"{total_raw + 30000:,}đ".replace(',', '.')
    return items, subtotal_str, total_str, total_raw


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = session['user_id']
    if request.method == "POST":
        fullname       = request.form.get('fullname', '')
        phone          = request.form.get('phone', '')
        email          = request.form.get('email', '')
        address        = request.form.get('address', '')
        payment_method = request.form.get('payment_method', 'cod')
        items, _, total_str, _ = _calc_cart_totals(user_id)
        if not items:
            flash('Giỏ hàng trống!', 'error')
            return redirect(url_for('cart.cart'))
        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            # Đảm bảo cột mới tồn tại (backward compatible)
            for col, definition in [
                ('quantity',    'INT DEFAULT 1'),
                ('total_price', 'BIGINT DEFAULT 0'),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE orders ADD COLUMN {col} {definition}")
                except Exception:
                    pass  # cột đã tồn tại → bỏ qua

            for item in items:
                nums        = re.findall(r'\d+', item['price_str'] or '0')
                unit_price  = int(''.join(nums)) if nums else 0
                quantity    = item.get('quantity', 1)
                total_price = unit_price * quantity

                cursor.execute("""
                    INSERT INTO orders (user_id, product_name, price, quantity,
                                       total_price, payment_method,
                                       fullname, phone, email, address, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'paid')
                """, (user_id, item['title'], item['price_str'], quantity,
                      total_price, payment_method,
                      fullname, phone, email, address))
            last_order_id = cursor.lastrowid
            cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
            conn.commit()

            # Chuẩn bị danh sách sản phẩm cho trang success
            order_items = []
            total_qty   = 0
            for item in items:
                nums       = re.findall(r'\d+', item['price_str'] or '0')
                unit_price = int(''.join(nums)) if nums else 0
                qty        = item.get('quantity', 1)
                total_qty += qty
                order_items.append({
                    'product_name': item['title'],
                    'quantity':     qty,
                    'price_str':    item['price_str'],
                    'total_price':  unit_price * qty,
                })

            return render_template("payment-success.html",
                                   order_id=last_order_id,
                                   order_items=order_items,
                                   total_qty=total_qty,
                                   total=total_str,
                                   payment_method=payment_method)
        except Exception as e:
            return render_template("payment-failed.html", error=str(e))
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    items, subtotal_str, total_str, _ = _calc_cart_totals(user_id)
    if not items:
        return redirect(url_for('cart.cart'))
    return render_template("checkout.html", cart_items=items, subtotal=subtotal_str, total=total_str)


@cart_bp.route("/payment-success")
def payment_success():
    return render_template("payment-success.html", order_id="N/A", product_count=0,
                           total="0đ", payment_method="N/A")


@cart_bp.route("/payment-failed")
def payment_failed():
    return render_template("payment-failed.html")


# ── ORDERS ───────────────────────────────────────────────────────────

@cart_bp.route("/orders")
@login_required
def orders():
    user_id = session['user_id']
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute("SELECT * FROM orders WHERE user_id=%s ORDER BY created_at DESC", (user_id,))
        data = cursor.fetchall()
        return render_template("orders.html", orders=data)
    finally:
        if 'conn' in locals() and conn:
            conn.close()
