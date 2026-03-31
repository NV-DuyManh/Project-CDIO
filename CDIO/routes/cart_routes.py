from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db_connection
from functools import wraps
import pymysql
import re

# ✅ FIX: khai báo Blueprint
cart_bp = Blueprint('cart', __name__)


# =========================
# LOGIN REQUIRED DECORATOR
# =========================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập!", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


# =========================
# CALCULATE CART TOTAL
# =========================
def _calc_cart_totals(user_id: int):
    """
    Return (items, subtotal_str, total_str, total_raw).
    Prefers raw_price column; falls back to regex parsing of price_str.
    """
    conn   = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM cart WHERE user_id=%s", (user_id,))
    items = cursor.fetchall()
    conn.close()

    total_raw = 0
    for item in items:
        unit = item.get("raw_price") or 0
        if not unit:
            nums = re.findall(r"\d+", item.get("price_str") or "0")
            unit = int("".join(nums)) if nums else 0

        total_raw += unit * item.get("quantity", 1)

    subtotal_str = f"{total_raw:,}đ".replace(",", ".")
    total_str    = f"{total_raw + 30000:,}đ".replace(",", ".")

    return items, subtotal_str, total_str, total_raw


# =========================
# VIEW CART
# =========================
@cart_bp.route("/cart")
@login_required
def cart():
    user_id = session["user_id"]
    items, subtotal, total, _ = _calc_cart_totals(user_id)

    return render_template(
        "cart.html",
        cart_items=items,
        subtotal=subtotal,
        total=total
    )


# =========================
# CHECKOUT (FIXED)
# =========================
@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    user_id = session["user_id"]

    if request.method == "POST":
        fullname       = request.form.get("fullname", "")
        phone          = request.form.get("phone", "")
        email          = request.form.get("email", "")
        address        = request.form.get("address", "")
        payment_method = request.form.get("payment_method", "cod")

        items, _, total_str, _ = _calc_cart_totals(user_id)

        if not items:
            flash("Giỏ hàng trống!", "error")
            return redirect(url_for("cart.cart"))

        conn = None
        try:
            conn   = get_db_connection()
            cursor = conn.cursor()

            conn.begin()  # ✅ transaction start

            order_items   = []
            total_qty     = 0
            last_order_id = None

            for item in items:
                unit_price = item.get("raw_price") or 0
                if not unit_price:
                    nums = re.findall(r"\d+", item.get("price_str") or "0")
                    unit_price = int("".join(nums)) if nums else 0

                quantity    = item.get("quantity", 1)
                total_price = unit_price * quantity
                total_qty  += quantity

                cursor.execute(
                    """
                    INSERT INTO orders
                    (user_id, product_name, price, quantity, total_price,
                     payment_method, fullname, phone, email, address, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'paid')
                    """,
                    (
                        user_id,
                        item["title"],
                        item["price_str"],
                        quantity,
                        total_price,
                        payment_method,
                        fullname,
                        phone,
                        email,
                        address,
                    ),
                )

                last_order_id = cursor.lastrowid

                order_items.append({
                    "product_name": item["title"],
                    "quantity": quantity,
                    "price_str": item["price_str"],
                    "total_price": total_price,
                })

            # ✅ clear cart AFTER success
            cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))

            conn.commit()  # ✅ commit all

            return render_template(
                "payment-success.html",
                order_id=last_order_id,
                order_items=order_items,
                total_qty=total_qty,
                total=total_str,
                payment_method=payment_method,
            )

        except Exception as exc:
            if conn:
                try:
                    conn.rollback()
                except:
                    pass

            return render_template("payment-failed.html", error=str(exc))

        finally:
            if conn:
                conn.close()

    # GET
    items, subtotal_str, total_str, _ = _calc_cart_totals(user_id)

    if not items:
        return redirect(url_for("cart.cart"))

    return render_template(
        "checkout.html",
        cart_items=items,
        subtotal=subtotal_str,
        total=total_str
    )