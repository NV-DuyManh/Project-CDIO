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

# ════════════════════════════════════════════════════════════════════
# CONFIG LỊCH TRÌNH CÀO NGẦM (PRE-WARM CACHE)
# ════════════════════════════════════════════════════════════════════
class SchedulerConfig:
    SCHEDULER_API_ENABLED = True

# Biến toàn cục lưu nhật ký để hiển thị lên trang Admin
BOT_LOGS = [] 

def pre_warm_cache_job():
    """Hàm chạy ngầm: Tự động cào dữ liệu cho các sản phẩm HOT"""
    global BOT_LOGS
    
    # Danh sách từ khóa hot nhất
    HOT_KEYWORDS = [
        "iPhone 15 Pro Max", "Samsung S24 Ultra", 
        "MacBook Air M3", "Xiaomi 14", "iPhone 16"
    ]
    
    print(f"🚀 [Background Job] Bắt đầu chu kỳ làm nóng Cache...")
    
    for kw in HOT_KEYWORDS:
        # 1. Ghi log bắt đầu vào danh sách (để hiện lên Web Admin)
        msg_start = f"Đang cào dữ liệu cho {kw}..."
        BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg_start}")
        print(f"🔎 {msg_start}")
        
        try:
            # 2. Gọi hàm cào dữ liệu (tự động lưu vào DB nếu cần)
            search_all_stores(kw)
            
            # 3. Ghi log thành công
            msg_success = f"✅ Đã làm nóng xong: {kw}"
            BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg_success}")
            print(msg_success)
            
        except Exception as e:
            # 4. Ghi log lỗi
            msg_error = f"❌ Lỗi khi cào {kw}: {str(e)}"
            BOT_LOGS.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg_error}")
            print(msg_error)
            
        # Giới hạn chỉ giữ lại 15 dòng nhật ký gần nhất
        BOT_LOGS = BOT_LOGS[:15]
        
        # Nghỉ 5 giây giữa các từ khóa để tránh bị chặn IP
        time.sleep(5)

    print("🏁 [Background Job] Hoàn tất chu kỳ làm nóng!")

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

    return app

if __name__ == "__main__":
    app = create_app()
    init_extra_tables()
    
    # LƯU Ý: use_reloader=False để tránh job chạy lặp 2 lần khi debug
    app.run(debug=True, use_reloader=False)