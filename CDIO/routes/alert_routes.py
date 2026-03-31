"""
routes/alert_routes.py
=======================
Price alert CRUD endpoints.
All routes require login.
"""
from flask import Blueprint, request, jsonify, session
import pymysql.cursors

from database.db     import get_db_connection
from utils.helpers   import login_required

alert_bp = Blueprint("alert", __name__, url_prefix="/alerts")


@alert_bp.route("/set", methods=["POST"])
@login_required
def set_alert():
    """
    Create or update a price alert.
    Body JSON: {keyword, threshold_price, channel, contact, product_title}
    """
    data      = request.get_json(force=True) or {}
    user_id   = session["user_id"]
    keyword   = data.get("keyword", "").strip()
    threshold = int(data.get("threshold_price", 0))
    channel   = data.get("channel", "email")
    contact   = data.get("contact", "").strip()
    title     = data.get("product_title", "").strip()

    if not keyword or threshold <= 0:
        return jsonify({"ok": False, "error": "keyword và threshold_price là bắt buộc"}), 400

    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO price_alerts
                   (user_id, keyword, product_title, threshold_price, channel, contact)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                   threshold_price = VALUES(threshold_price),
                   channel         = VALUES(channel),
                   contact         = VALUES(contact),
                   is_active       = 1,
                   last_triggered  = NULL""",
            (user_id, keyword, title, threshold, channel, contact),
        )
        conn.commit()
        return jsonify({"ok": True, "message": "Đã đặt cảnh báo giá thành công!"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
    finally:
        if "conn" in locals() and conn:
            conn.close()


@alert_bp.route("/list")
@login_required
def list_alerts():
    """Return all active alerts for the current user."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM price_alerts WHERE user_id=%s ORDER BY created_at DESC",
            (session["user_id"],),
        )
        rows = cursor.fetchall()
        for r in rows:
            for k, v in r.items():
                if hasattr(v, "isoformat"):
                    r[k] = v.isoformat()
        return jsonify(rows)
    finally:
        if "conn" in locals() and conn:
            conn.close()


@alert_bp.route("/delete/<int:aid>", methods=["POST"])
@login_required
def delete_alert(aid: int):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM price_alerts WHERE id=%s AND user_id=%s",
            (aid, session["user_id"]),
        )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        if "conn" in locals() and conn:
            conn.close()


@alert_bp.route("/toggle/<int:aid>", methods=["POST"])
@login_required
def toggle_alert(aid: int):
    """Pause / resume an alert without deleting it."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE price_alerts SET is_active = 1 - is_active WHERE id=%s AND user_id=%s",
            (aid, session["user_id"]),
        )
        conn.commit()
        return jsonify({"ok": True})
    finally:
        if "conn" in locals() and conn:
            conn.close()