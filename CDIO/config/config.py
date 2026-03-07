import os

# ════════════════════════════════════════════════════════════════════
# DATABASE
# ════════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",
    "password": "Duymanh20092005#",
    "database": "cdio",
    "charset":  "utf8mb4"
}

# ════════════════════════════════════════════════════════════════════
# FLASK
# ════════════════════════════════════════════════════════════════════
SECRET_KEY = os.environ.get('SECRET_KEY', 'pricehunt-secret-key-change-in-production')

# ════════════════════════════════════════════════════════════════════
# STORES — thêm cửa hàng mới vào đây
# ════════════════════════════════════════════════════════════════════
STORES = ["Clickbuy", "CellphoneS"]

FALLBACK_IMG = "https://via.placeholder.com/200x200/1a1a24/555568?text=No+Image"

# ════════════════════════════════════════════════════════════════════
# AI IMAGE SEARCH — Gemini Vision (FREE)
# Lấy key tại: aistudio.google.com
# Set key:
#   PowerShell: $env:GEMINI_API_KEY="AIzaSy..."
#   CMD:        set GEMINI_API_KEY=AIzaSy...
# ════════════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# ════════════════════════════════════════════════════════════════════
# UPLOAD
# ════════════════════════════════════════════════════════════════════
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXT   = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

# ════════════════════════════════════════════════════════════════════
# SCRAPER
# ════════════════════════════════════════════════════════════════════
SCRAPE_MAX_PRODUCTS = 15
SCRAPE_WAIT_SECONDS = 2
