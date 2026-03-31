"""
services/price_alert_service.py
================================
Checks price_alerts after each scrape and notifies users
via email (Gmail SMTP) or Telegram Bot API.
"""
import smtplib
import json
import urllib.request
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText

import pymysql.cursors
from config.config  import ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD, TELEGRAM_BOT_TOKEN
from database.db    import get_db_connection


# ════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ════════════════════════════════════════════════════════════════════

def check_and_trigger_alerts(keyword: str, products: list):
    """
    After a scrape, check if any active alerts for `keyword` should fire.
    An alert fires when: product.raw_price <= alert.threshold_price.
    Respects a 6-hour cool-down (last_triggered) to avoid spam.
    """
    if not products:
        return

    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """SELECT pa.*, u.email AS user_email, u.username
               FROM price_alerts pa
               JOIN users u ON pa.user_id = u.id
               WHERE LOWER(pa.keyword) = LOWER(%s)
                 AND pa.is_active = 1
                 AND (pa.last_triggered IS NULL
                      OR pa.last_triggered < DATE_SUB(NOW(), INTERVAL 6 HOUR))""",
            (keyword.strip(),),
        )
        alerts = cursor.fetchall()
        if not alerts:
            return

        write_cursor = conn.cursor()
        for alert in alerts:
            matches = [
                p for p in products
                if p.get("raw_price") and p["raw_price"] <= alert["threshold_price"]
                and (
                    not alert.get("product_title")
                    or alert["product_title"].lower() in (p.get("title") or "").lower()
                )
            ]
            if not matches:
                continue

            best = matches[0]   # already sorted by price (cheapest first)
            _dispatch(alert, best)

            write_cursor.execute(
                "UPDATE price_alerts SET last_triggered=NOW() WHERE id=%s",
                (alert["id"],),
            )

        conn.commit()
    except Exception as exc:
        print(f"[price_alert] check error: {exc}")
    finally:
        if "conn" in locals() and conn:
            conn.close()


# ════════════════════════════════════════════════════════════════════
# DISPATCH
# ════════════════════════════════════════════════════════════════════

def _dispatch(alert: dict, product: dict):
    username  = alert.get("username", "bạn")
    threshold = f"{alert['threshold_price']:,}đ".replace(",", ".")
    price     = product.get("price_str", "N/A")
    title     = product.get("title", "Sản phẩm")
    site      = product.get("site", "")
    link      = product.get("link", "")

    subject = f"[PriceHunt] 🔔 Giá '{title[:40]}' giảm xuống {price}!"
    body = (
        f"Chào {username}!\n\n"
        f"Giá của sản phẩm bạn theo dõi đã giảm xuống dưới ngưỡng {threshold}.\n\n"
        f"📦 Sản phẩm : {title}\n"
        f"💰 Giá hiện tại: {price}\n"
        f"🏬 Cửa hàng  : {site}\n"
        f"🔗 Link mua  : {link}\n\n"
        f"Chúc bạn mua hàng vui vẻ!\n— PriceHunt Bot"
    )

    channel = alert.get("channel", "email")
    contact = alert.get("contact") or alert.get("user_email")

    if channel == "telegram":
        _send_telegram(contact, f"<b>{subject}</b>\n\n{body}")
    else:
        _send_email(contact, subject, body)


def _send_email(to: str, subject: str, body: str):
    if not all([ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD, to]):
        print(f"[alert:email] Config missing — skip (to={to})")
        return
    try:
        msg             = MIMEMultipart()
        msg["From"]     = ALERT_EMAIL_FROM
        msg["To"]       = to
        msg["Subject"]  = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD)
            smtp.send_message(msg)
        print(f"[alert:email] ✓ sent to {to}")
    except Exception as exc:
        print(f"[alert:email] ✗ {exc}")


def _send_telegram(chat_id: str, html_message: str):
    if not all([TELEGRAM_BOT_TOKEN, chat_id]):
        print("[alert:telegram] Config missing — skip")
        return
    try:
        payload = urllib.parse.urlencode({
            "chat_id":    chat_id,
            "text":       html_message,
            "parse_mode": "HTML",
        }).encode()
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        req = urllib.request.Request(url, data=payload, method="POST")
        urllib.request.urlopen(req, timeout=10)
        print(f"[alert:telegram] ✓ sent to {chat_id}")
    except Exception as exc:
        print(f"[alert:telegram] ✗ {exc}")