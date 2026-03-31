import os

# ════════════════════════════════════════════════════════════════════
# DATABASE — values now pulled from .env (same values, more secure)
# ════════════════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "Duymanh20092005#"),
    "database": os.environ.get("DB_NAME",     "cdio"),
    "charset":  "utf8mb4",
}

# ════════════════════════════════════════════════════════════════════
# FLASK
# ════════════════════════════════════════════════════════════════════
SECRET_KEY = os.environ.get("SECRET_KEY", "pricehunt-secret-key-change-in-production")

# ════════════════════════════════════════════════════════════════════
# STORES
# ════════════════════════════════════════════════════════════════════
STORES = [
    "Clickbuy",
    "CellphoneS",
    "Di Động 3A",
    "Smart Việt",
    "Bạch Long Store",
    "Tiến Trần Mobile",
]

FALLBACK_IMG = "https://via.placeholder.com/200x200/1a1a24/555568?text=No+Image"

# ════════════════════════════════════════════════════════════════════
# AI IMAGE SEARCH
# ════════════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ════════════════════════════════════════════════════════════════════
# UPLOAD
# ════════════════════════════════════════════════════════════════════
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT   = {"png", "jpg", "jpeg", "webp", "gif"}

# ════════════════════════════════════════════════════════════════════
# SCRAPER
# ════════════════════════════════════════════════════════════════════
SCRAPE_MAX_PRODUCTS = 15
SCRAPE_WAIT_SECONDS = 2

# ════════════════════════════════════════════════════════════════════
# CACHE  ← NEW
# ════════════════════════════════════════════════════════════════════
# Fresh window: data younger than TTL is served directly
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 3600))

# Hot keywords pre-warmed in background
HOT_KEYWORDS = [
    "iphone 15", "iphone 15 pro", "iphone 15 pro max",
    "iphone 16", "iphone 16 pro", "iphone 16 pro max",
    "samsung galaxy s24", "samsung galaxy s24 ultra",
    "samsung galaxy s25", "samsung galaxy s25 ultra",
    "xiaomi 14", "xiaomi 14 ultra",
    "redmi note 13", "redmi note 13 pro",
    "oppo reno 12", "vivo v30",
]

# ════════════════════════════════════════════════════════════════════
# PRICE ALERT  ← NEW
# ════════════════════════════════════════════════════════════════════
ALERT_EMAIL_FROM     = os.environ.get("ALERT_EMAIL_FROM",     "")
ALERT_EMAIL_PASSWORD = os.environ.get("ALERT_EMAIL_PASSWORD", "")
TELEGRAM_BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN",   "")