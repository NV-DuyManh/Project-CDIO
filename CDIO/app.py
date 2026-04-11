from dotenv import load_dotenv
load_dotenv()
import os
import time
from flask import Flask
from flask_apscheduler import APScheduler 

from config.config import SECRET_KEY
from database.db import init_extra_tables
from services.search_service import search_all_stores 

# ── Import Blueprints ────────────────────────────────────────────────
from routes.search_routes import search_bp
from routes.upload_routes  import upload_bp
from routes.auth_routes    import auth_bp
from routes.cart_routes    import cart_bp
from routes.admin_routes   import admin_bp
from routes.category_routes import category_bp 
from routes.analytics_routes import analytics_bp
from database.db import init_price_alerts_table, get_active_alerts_for_keyword, deactivate_alert
from services.email_service import send_price_alert_email

# ════════════════════════════════════════════════════════════════════
# CONFIG LỊCH TRÌNH CÀO NGẦM (PRE-WARM CACHE)
# ════════════════════════════════════════════════════════════════════
class SchedulerConfig:
    SCHEDULER_API_ENABLED = True

# Biến toàn cục lưu nhật ký để hiển thị lên trang Admin
BOT_LOGS = [] 

"""
app.py — PATCH: Nâng cấp pre_warm_cache_job để kiểm tra price alerts.

HƯỚNG DẪN: Thay hàm pre_warm_cache_job() hiện tại trong app.py bằng
hàm bên dưới. Thêm 2 dòng import ở đầu file.
Không thay đổi bất kỳ phần nào khác của app.py.
"""

# ── Thêm 2 dòng import này vào đầu app.py (sau các import hiện có) ──
# from database.db import init_price_alerts_table, get_active_alerts_for_keyword, deactivate_alert
# from services.email_service import send_price_alert_email
# ────────────────────────────────────────────────────────────────────

# ── Thay hàm pre_warm_cache_job() bằng hàm bên dưới ─────────────────

def pre_warm_cache_job():
    """
    Hàm chạy ngầm: Tự động cào dữ liệu cho các sản phẩm HOT.
    [NÂNG CẤP] Sau khi cào xong → kiểm tra price alerts → gửi email nếu đủ điều kiện.
    """
    global BOT_LOGS

    HOT_KEYWORDS = [
        "iPhone 15 Pro Max", "Samsung S24 Ultra",
        "MacBook Air M3", "Xiaomi 14", "iPhone 16"
    ]

    print(f"🚀 [Background Job] Bắt đầu chu kỳ làm nóng Cache...")

    for kw in HOT_KEYWORDS:
        msg_start = f"Đang cào dữ liệu cho {kw}..."
        BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg_start}")
        print(f"🔎 {msg_start}")

        try:
            # ── Bước 1: Cào dữ liệu (logic cũ, giữ nguyên) ──────────
            filtered_products, _ = search_all_stores(kw)

            msg_success = f"✅ Đã làm nóng xong: {kw} ({len(filtered_products)} sản phẩm)"
            BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg_success}")
            print(msg_success)

            # ── Bước 2: Kiểm tra Price Alerts (logic MỚI) ────────────
            if filtered_products:
                best_product = filtered_products[0]   # Đã sắp xếp giá thấp→cao
                best_price   = best_product.get('raw_price', 0)

                alerts = get_active_alerts_for_keyword(kw)
                for alert in alerts:
                    if best_price <= alert['target_price']:
                        # Giá đã đạt mục tiêu → gửi email
                        print(f"💌 [Alert] Gửi email tới {alert['user_email']} "
                              f"— {kw} @ {best_price:,}đ (mục tiêu: {alert['target_price']:,}đ)")

                        sent = send_price_alert_email(
                            user_email    = alert['user_email'],
                            product_title = best_product.get('title', alert['product_title']),
                            new_price     = best_price,
                            link          = best_product.get('link', '#'),
                            keyword       = kw,
                            target_price  = alert['target_price'],
                        )

                        if sent:
                            # Tắt alert để tránh spam
                            deactivate_alert(alert['id'])
                            log_msg = (f"💌 Đã gửi alert email tới {alert['user_email']} "
                                       f"— {kw} @ {best_price:,}đ")
                        else:
                            log_msg = (f"⚠️ Gửi email thất bại cho {alert['user_email']} "
                                       f"— {kw}")

                        BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {log_msg}")

        except Exception as e:
            msg_error = f"❌ Lỗi khi cào {kw}: {str(e)}"
            BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg_error}")
            print(msg_error)

        # Giới hạn chỉ giữ lại 15 dòng nhật ký gần nhất
        BOT_LOGS = BOT_LOGS[:15]
        time.sleep(5)

    print("🏁 [Background Job] Hoàn tất chu kỳ làm nóng!")


# ════════════════════════════════════════════════════════════════════
# PATCH cho search_routes.py (search_all_stores):
# Sau dòng `save_to_db(...)`, chèn đoạn code kiểm tra alert bên dưới.
#
# VỊ TRÍ CHÈN: cuối hàm search_all_stores(), trước return
#
# from database.db import get_active_alerts_for_keyword, deactivate_alert
# from services.email_service import send_price_alert_email
#
# # ── Kiểm tra Price Alert khi user chủ động tìm kiếm ──────────────
# try:
#     if filtered_products:
#         best       = filtered_products[0]
#         best_price = best.get('raw_price', 0)
#         alerts     = get_active_alerts_for_keyword(normalized_kw)
#         for alert in alerts:
#             if best_price <= alert['target_price']:
#                 sent = send_price_alert_email(
#                     user_email    = alert['user_email'],
#                     product_title = best.get('title', alert['product_title']),
#                     new_price     = best_price,
#                     link          = best.get('link', '#'),
#                     keyword       = normalized_kw,
#                     target_price  = alert['target_price'],
#                 )
#                 if sent:
#                     deactivate_alert(alert['id'])
# except Exception as e:
#     print(f"[search] price alert check error: {e}")
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
# APP FACTORY
# ════════════════════════════════════════════════════════════════════

def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    
    # Cấu hình Scheduler
    app.config.from_object(SchedulerConfig())
    scheduler = APScheduler()
    scheduler.init_app(app)

    # Đặt lịch: Cứ mỗi 180 phút (3 tiếng) chạy một lần
    scheduler.add_job(id='WarmCacheJob', func=pre_warm_cache_job, trigger='interval', minutes=180)
    
    scheduler.start()
    print("⏰ Background Scheduler đã được kích hoạt!")

    # Register all blueprints
    app.register_blueprint(search_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(analytics_bp)

    return app

if __name__ == "__main__":
    app = create_app()
    init_extra_tables()
    
    # LƯU Ý: use_reloader=False để tránh job chạy lặp 2 lần khi debug
    app.run(debug=True, use_reloader=False)