import pymysql
import pymysql.cursors
from config.config import DB_CONFIG

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def get_data_from_db(keyword):
    """Lấy dữ liệu từ DB theo keyword chính xác."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql    = "SELECT *, created_at FROM search_history WHERE LOWER(keyword) = LOWER(%s) ORDER BY raw_price ASC"
        cursor.execute(sql, (keyword.strip(),))
        rows = cursor.fetchall()
        seen, unique_rows = set(), []
        for r in rows:
            identifier = (r['site'], r['title'], r['raw_price'])
            if identifier not in seen:
                seen.add(identifier)
                unique_rows.append(r)
        return unique_rows
    except Exception as e:
        print(f"Lỗi get_data_from_db: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


# ════════════════════════════════════════════════════════════════════
# CATEGORY QUERIES — chỉ đọc DB, không cào
# ════════════════════════════════════════════════════════════════════

def get_products_by_brand(brand: str, sort: str = 'asc', page: int = 1, per_page: int = 60):
    """
    Lấy sản phẩm theo thương hiệu.
    brand = 'iphone' | 'samsung' | 'other'
    sort  = 'asc' | 'desc'
    """
    order = "ASC" if sort != 'desc' else "DESC"
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        offset = (page - 1) * per_page

        if brand == 'other':
            sql = """
                SELECT * FROM search_history
                WHERE LOWER(title) NOT LIKE %s
                  AND LOWER(title) NOT LIKE %s
                  AND raw_price > 0
                ORDER BY raw_price {order}
                LIMIT %s OFFSET %s
            """.format(order=order)
            cursor.execute(sql, ('%iphone%', '%samsung%', per_page, offset))

            count_sql = """
                SELECT COUNT(*) as c FROM search_history
                WHERE LOWER(title) NOT LIKE %s
                  AND LOWER(title) NOT LIKE %s
                  AND raw_price > 0
            """
            cursor.execute(count_sql, ('%iphone%', '%samsung%'))
        else:
            sql = """
                SELECT * FROM search_history
                WHERE LOWER(title) LIKE %s
                  AND raw_price > 0
                ORDER BY raw_price {order}
                LIMIT %s OFFSET %s
            """.format(order=order)
            cursor.execute(sql, (f'%{brand.lower()}%', per_page, offset))

            count_sql = """
                SELECT COUNT(*) as c FROM search_history
                WHERE LOWER(title) LIKE %s AND raw_price > 0
            """
            cursor.execute(count_sql, (f'%{brand.lower()}%',))

        rows  = cursor.fetchall()
        total = cursor.fetchone()['c'] if cursor.fetchone() else len(rows)
        return _dedup(rows), total
    except Exception as e:
        print(f"Lỗi get_products_by_brand: {e}")
        return [], 0
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_products_by_series(series_keyword: str, sort: str = 'asc', page: int = 1, per_page: int = 60):
    """
    Lấy sản phẩm theo dòng máy, ví dụ 'iPhone 17', 'Galaxy S25'.
    Dùng LIKE '%iphone 17%' để bắt tất cả biến thể (Pro, Plus, Pro Max...).
    """
    order = "ASC" if sort != 'desc' else "DESC"
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        offset = (page - 1) * per_page
        pattern = f'%{series_keyword.lower()}%'

        sql = """
            SELECT * FROM search_history
            WHERE LOWER(title) LIKE %s AND raw_price > 0
            ORDER BY raw_price {order}
            LIMIT %s OFFSET %s
        """.format(order=order)
        cursor.execute(sql, (pattern, per_page, offset))
        rows = cursor.fetchall()

        count_sql = "SELECT COUNT(*) as c FROM search_history WHERE LOWER(title) LIKE %s AND raw_price > 0"
        cursor.execute(count_sql, (pattern,))
        total_row = cursor.fetchone()
        total = total_row['c'] if total_row else len(rows)
        return _dedup(rows), total
    except Exception as e:
        print(f"Lỗi get_products_by_series: {e}")
        return [], 0
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def search_db_only(query: str, sort: str = 'asc', page: int = 1, per_page: int = 60):
    """
    Tìm kiếm thuần DB — dùng cho thanh Search (không cào live).
    Tìm theo cả title lẫn keyword đã lưu.
    """
    order = "ASC" if sort != 'desc' else "DESC"
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        offset = (page - 1) * per_page
        pattern = f'%{query.strip().lower()}%'

        sql = """
            SELECT * FROM search_history
            WHERE (LOWER(title) LIKE %s OR LOWER(keyword) LIKE %s)
              AND raw_price > 0
            ORDER BY raw_price {order}
            LIMIT %s OFFSET %s
        """.format(order=order)
        cursor.execute(sql, (pattern, pattern, per_page, offset))
        rows = cursor.fetchall()

        count_sql = """
            SELECT COUNT(*) as c FROM search_history
            WHERE (LOWER(title) LIKE %s OR LOWER(keyword) LIKE %s) AND raw_price > 0
        """
        cursor.execute(count_sql, (pattern, pattern))
        total_row = cursor.fetchone()
        total = total_row['c'] if total_row else len(rows)
        return _dedup(rows), total
    except Exception as e:
        print(f"Lỗi search_db_only: {e}")
        return [], 0
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def _dedup(rows):
    """Loại trùng (site + title + price)."""
    seen, out = set(), []
    for r in rows:
        key = (r.get('site'), r.get('title'), r.get('raw_price'))
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


# ════════════════════════════════════════════════════════════════════
# Giữ nguyên các hàm cũ bên dưới
# ════════════════════════════════════════════════════════════════════

def save_to_db(keyword, products, user_id=None):
    if not products:
        return
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s) AND user_id = %s", (keyword.strip(), user_id))
        else:
            cursor.execute("DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s) AND user_id IS NULL", (keyword.strip(),))
        sql = """INSERT INTO search_history
                 (keyword, user_id, site, title, price_str, raw_price, img, link)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
        for p in products:
            cursor.execute(sql, (
                keyword.strip(), user_id,
                p.get('site', 'Unknown'), p.get('title', ''),
                p.get('price_str', ''), p.get('raw_price', 0),
                p.get('img', ''), p.get('link', '')
            ))
        conn.commit()
    except Exception as e:
        print(f"Lỗi save_to_db: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def init_extra_tables():
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                is_admin TINYINT(1) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                keyword VARCHAR(255),
                site VARCHAR(50),
                title TEXT,
                price_str VARCHAR(100),
                raw_price BIGINT,
                img TEXT,
                link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        try:
            cursor.execute("ALTER TABLE search_history ADD COLUMN user_id INT NULL")
            cursor.execute("ALTER TABLE search_history ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL")
        except Exception:
            pass
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title TEXT, price_str VARCHAR(100),
                img TEXT, link TEXT, site VARCHAR(50),
                quantity INT DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_name TEXT,
                price VARCHAR(200),
                payment_method VARCHAR(50) DEFAULT 'COD',
                fullname VARCHAR(100),
                phone VARCHAR(20),
                email VARCHAR(120),
                address TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title TEXT, price_str VARCHAR(100),
                img TEXT, link TEXT, site VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                product_title TEXT, content TEXT, rating INT DEFAULT 5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        print("✅ Database đã được khởi tạo và nâng cấp thành công!")
    except Exception as e:
        print(f"[init_extra_tables] Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def get_suggestions(query):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT DISTINCT keyword FROM search_history WHERE keyword LIKE %s LIMIT 8"
        cursor.execute(sql, (f"%{query}%",))
        results = cursor.fetchall()
        return [r['keyword'] for r in results]
    except Exception:
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

"""
database/db.py — PATCH: thêm hàm init_price_alerts_table() và 2 hàm helper.
Chèn đoạn này vào cuối file database/db.py hiện tại của bạn.
Không xóa hoặc sửa bất kỳ hàm nào đang có.
"""

# ════════════════════════════════════════════════════════════════════
# PRICE ALERTS — tạo bảng + helpers
# Nguyên lý Open-Closed: chỉ MỞ RỘNG, không sửa code cũ
# ════════════════════════════════════════════════════════════════════

CREATE_PRICE_ALERTS_SQL = """
CREATE TABLE IF NOT EXISTS `price_alerts` (
    `id`            INT AUTO_INCREMENT PRIMARY KEY,
    `user_id`       INT          NOT NULL,
    `product_title` VARCHAR(500) NOT NULL,
    `keyword`       VARCHAR(255) NOT NULL,
    `target_price`  BIGINT       NOT NULL,
    `is_active`     TINYINT(1)   NOT NULL DEFAULT 1,
    `created_at`    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_keyword  (`keyword`),
    INDEX idx_user_id  (`user_id`),
    INDEX idx_active   (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""


def init_price_alerts_table():
    """Tạo bảng price_alerts nếu chưa có. Gọi 1 lần khi khởi động app."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(CREATE_PRICE_ALERTS_SQL)
        conn.commit()
        print("✅ [DB] Bảng price_alerts đã sẵn sàng.")
    except Exception as e:
        print(f"❌ [DB] Lỗi tạo bảng price_alerts: {e}")
    finally:
        conn.close()


def get_active_alerts_for_keyword(keyword: str):
    """
    Trả về list[dict] các alert đang is_active=1 khớp với keyword.
    Dùng trong background job để so sánh giá.
    """
    conn = get_db_connection()
    try:
        import pymysql.cursors
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(
            """
            SELECT pa.*, u.email AS user_email
            FROM price_alerts pa
            JOIN users u ON pa.user_id = u.id
            WHERE pa.is_active = 1
              AND LOWER(pa.keyword) = LOWER(%s)
            """,
            (keyword,)
        )
        return cur.fetchall() or []
    except Exception as e:
        print(f"[DB] get_active_alerts_for_keyword error: {e}")
        return []
    finally:
        conn.close()


def deactivate_alert(alert_id: int):
    """Đánh dấu is_active=0 sau khi đã gửi email để tránh spam."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE price_alerts SET is_active = 0 WHERE id = %s",
            (alert_id,)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB] deactivate_alert error: {e}")
    finally:
        conn.close()


# ════════════════════════════════════════════════════════════════════
# HƯỚNG DẪN TÍCH HỢP VÀO app.py (cuối hàm main):
#
#   from database.db import init_extra_tables, init_price_alerts_table
#   ...
#   if __name__ == "__main__":
#       app = create_app()
#       init_extra_tables()
#       init_price_alerts_table()   # <-- thêm dòng này
#       app.run(debug=True, use_reloader=False)
# ════════════════════════════════════════════════════════════════════