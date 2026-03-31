"""
database/db.py
==============
Central DB access layer.
Changes:
  - get_data_from_db: TTL-aware (scraped_at column)
  - save_to_db: writes user_id, scraped_at, price_history snapshot, keyword_log
  - init_extra_tables: adds all new tables + indexes + migrates existing tables
  - NEW: get_stale_data_from_db, get_user_search_history, log_keyword_search
"""
import pymysql
import pymysql.cursors
from config.config import DB_CONFIG, CACHE_TTL_SECONDS


# ════════════════════════════════════════════════════════════════════
# CONNECTION
# ════════════════════════════════════════════════════════════════════

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


# ════════════════════════════════════════════════════════════════════
# READ
# ════════════════════════════════════════════════════════════════════

def get_data_from_db(keyword: str, ttl: int = None) -> list:
    """
    Return cached products for keyword that are younger than `ttl` seconds.
    Returns [] if no fresh cache exists (caller should scrape).
    """
    if ttl is None:
        ttl = CACHE_TTL_SECONDS
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Gracefully handle missing scraped_at column during migrations
        try:
            cursor.execute(
                """SELECT * FROM search_history
                   WHERE LOWER(keyword) = LOWER(%s)
                     AND scraped_at > DATE_SUB(NOW(), INTERVAL %s SECOND)
                   ORDER BY raw_price ASC""",
                (keyword.strip(), ttl),
            )
        except pymysql.err.OperationalError:
            # scraped_at column not yet added – fall back to unfiltered
            cursor.execute(
                "SELECT * FROM search_history WHERE LOWER(keyword)=LOWER(%s) ORDER BY raw_price ASC",
                (keyword.strip(),),
            )
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if "conn" in locals() and conn:
            conn.close()


def get_stale_data_from_db(keyword: str) -> list:
    """
    Return ANY cached data regardless of age.
    Used by Stale-While-Revalidate: serve old data while background refresh runs.
    """
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT * FROM search_history WHERE LOWER(keyword)=LOWER(%s) ORDER BY raw_price ASC",
            (keyword.strip(),),
        )
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if "conn" in locals() and conn:
            conn.close()


def get_user_search_history(user_id: int, limit: int = 50) -> list:
    """Return recent distinct keywords searched by this user."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """SELECT DISTINCT keyword, MAX(scraped_at) as last_searched
               FROM search_history
               WHERE user_id = %s
               GROUP BY keyword
               ORDER BY last_searched DESC
               LIMIT %s""",
            (user_id, limit),
        )
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if "conn" in locals() and conn:
            conn.close()


def get_price_history(keyword: str, days: int = 30) -> list:
    """Return daily average price per site for sparkline charts."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            """SELECT site,
                      ROUND(AVG(raw_price)) AS avg_price,
                      MIN(raw_price)        AS min_price,
                      DATE(recorded_at)     AS record_date
               FROM price_history
               WHERE LOWER(keyword) = LOWER(%s)
                 AND recorded_at   > DATE_SUB(NOW(), INTERVAL %s DAY)
               GROUP BY site, DATE(recorded_at)
               ORDER BY record_date ASC""",
            (keyword.strip(), days),
        )
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if "conn" in locals() and conn:
            conn.close()


# ════════════════════════════════════════════════════════════════════
# WRITE
# ════════════════════════════════════════════════════════════════════

def save_to_db(keyword: str, products: list, user_id: int = None):
    """
    Persist scraped products.
    Also:
      - Records price snapshots in price_history
      - Updates keyword_log for instant-search suggestions
      - Associates with user_id if provided
    """
    if not products:
        return
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # ── Replace stale cache ───────────────────────────────────
        cursor.execute(
            "DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s)",
            (keyword.strip(),),
        )

        # ── Insert fresh results ──────────────────────────────────
        sh_sql = """
            INSERT INTO search_history
                (keyword, site, title, price_str, raw_price, img, link, user_id, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """
        for p in products:
            cursor.execute(
                sh_sql,
                (keyword.strip(), p["site"], p["title"],
                 p["price_str"], p["raw_price"], p["img"], p["link"], user_id),
            )

        # ── Price history snapshot ────────────────────────────────
        ph_sql = """
            INSERT INTO price_history (keyword, site, title, raw_price, price_str)
            VALUES (%s, %s, %s, %s, %s)
        """
        for p in products:
            cursor.execute(
                ph_sql,
                (keyword.strip(), p["site"], p["title"], p["raw_price"], p["price_str"]),
            )

        # ── Keyword log (for autocomplete) ────────────────────────
        cursor.execute(
            """INSERT INTO keyword_log (keyword, search_count, last_searched)
               VALUES (%s, 1, NOW())
               ON DUPLICATE KEY UPDATE
                   search_count  = search_count + 1,
                   last_searched = NOW()""",
            (keyword.strip().lower(),),
        )

        conn.commit()
    except Exception as e:
        print(f"[save_to_db] Error: {e}")
    finally:
        if "conn" in locals() and conn:
            conn.close()


def log_keyword_search(keyword: str):
    """Lightweight keyword-log update without full scrape (for cache-hit searches)."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO keyword_log (keyword, search_count, last_searched)
               VALUES (%s, 1, NOW())
               ON DUPLICATE KEY UPDATE
                   search_count  = search_count + 1,
                   last_searched = NOW()""",
            (keyword.strip().lower(),),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        if "conn" in locals() and conn:
            conn.close()


# ════════════════════════════════════════════════════════════════════
# SCHEMA INIT
# ════════════════════════════════════════════════════════════════════

def _safe_alter(cursor, sql: str):
    """Run ALTER TABLE silently — ignores 'duplicate column' errors."""
    try:
        cursor.execute(sql)
    except pymysql.err.OperationalError:
        pass  # Column / index already exists


def _safe_index(cursor, table: str, index_name: str, col: str, extra: str = ""):
    """Create index only if it does not already exist."""
    try:
        cursor.execute(f"CREATE INDEX {index_name} ON {table} ({col}) {extra}")
    except Exception:
        pass


def init_extra_tables():
    """
    Idempotent schema bootstrap.
    Safe to call on every startup — only creates / alters what is missing.
    """
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()

        # ── users ─────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                username      VARCHAR(80)  UNIQUE NOT NULL,
                email         VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin      TINYINT(1) DEFAULT 0,
                created_at    TIMESTAMP  DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── favorites ─────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                user_id    INT NOT NULL,
                title      TEXT, price_str VARCHAR(100),
                img        TEXT, link TEXT, site VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── cart ──────────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id        INT AUTO_INCREMENT PRIMARY KEY,
                user_id   INT NOT NULL,
                title     TEXT, price_str VARCHAR(100),
                img       TEXT, link TEXT, site VARCHAR(50),
                quantity  INT DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── orders — includes quantity/total_price from the start ─
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id             INT AUTO_INCREMENT PRIMARY KEY,
                user_id        INT NOT NULL,
                product_name   TEXT,
                price          VARCHAR(200),
                quantity       INT     DEFAULT 1,
                total_price    BIGINT  DEFAULT 0,
                payment_method VARCHAR(50),
                fullname       VARCHAR(100),
                phone          VARCHAR(20),
                email          VARCHAR(120),
                address        TEXT,
                status         VARCHAR(20) DEFAULT 'paid',
                created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── comments ──────────────────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                user_id       INT NOT NULL,
                product_title TEXT, content TEXT, rating INT DEFAULT 5,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # ── search_history — MIGRATE existing table ───────────────
        _safe_alter(cursor, "ALTER TABLE search_history ADD COLUMN user_id   INT          DEFAULT NULL")
        _safe_alter(cursor, "ALTER TABLE search_history ADD COLUMN scraped_at TIMESTAMP   DEFAULT CURRENT_TIMESTAMP")
        # Indexes
        _safe_index(cursor, "search_history", "idx_sh_keyword",  "keyword(100)")
        _safe_index(cursor, "search_history", "idx_sh_user",     "user_id")
        _safe_index(cursor, "search_history", "idx_sh_scraped",  "scraped_at")
        # orders indexes
        _safe_index(cursor, "orders", "idx_ord_user",   "user_id")
        _safe_index(cursor, "orders", "idx_ord_status", "status(10)")

        # ── price_history  ← NEW ──────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                keyword     VARCHAR(255) NOT NULL,
                site        VARCHAR(50),
                title       TEXT,
                raw_price   BIGINT,
                price_str   VARCHAR(100),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        _safe_index(cursor, "price_history", "idx_ph_keyword",  "keyword(100)")
        _safe_index(cursor, "price_history", "idx_ph_recorded", "recorded_at")

        # ── price_alerts  ← NEW ───────────────────────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id              INT AUTO_INCREMENT PRIMARY KEY,
                user_id         INT NOT NULL,
                keyword         VARCHAR(255) NOT NULL,
                product_title   TEXT,
                threshold_price BIGINT NOT NULL,
                channel         ENUM('email','telegram') DEFAULT 'email',
                contact         VARCHAR(255),
                is_active       TINYINT(1) DEFAULT 1,
                last_triggered  TIMESTAMP NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uniq_alert (user_id, keyword(100)),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        _safe_index(cursor, "price_alerts", "idx_pa_user",    "user_id")
        _safe_index(cursor, "price_alerts", "idx_pa_keyword", "keyword(100)")

        # ── keyword_log (for autocomplete)  ← NEW ─────────────────
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyword_log (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                keyword       VARCHAR(255) NOT NULL UNIQUE,
                search_count  INT       DEFAULT 1,
                last_searched TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        _safe_index(cursor, "keyword_log", "idx_kl_count", "search_count")

        conn.commit()
        print("[db] Schema bootstrap complete.")
    except Exception as e:
        print(f"[init_extra_tables] Warning: {e}")
    finally:
        if "conn" in locals() and conn:
            conn.close()