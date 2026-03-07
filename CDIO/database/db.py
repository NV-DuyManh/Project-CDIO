import pymysql
import pymysql.cursors
from config.config import DB_CONFIG


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


def get_data_from_db(keyword):
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        sql    = "SELECT * FROM search_history WHERE LOWER(keyword) = LOWER(%s) ORDER BY raw_price ASC"
        cursor.execute(sql, (keyword.strip(),))
        return cursor.fetchall()
    except Exception:
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def save_to_db(keyword, products):
    if not products:
        return
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s)", (keyword.strip(),))
        sql = "INSERT INTO search_history (keyword, site, title, price_str, raw_price, img, link) VALUES (%s,%s,%s,%s,%s,%s,%s)"
        for p in products:
            cursor.execute(sql, (keyword.strip(), p['site'], p['title'],
                                 p['price_str'], p['raw_price'], p['img'], p['link']))
        conn.commit()
    except Exception:
        pass
    finally:
        if 'conn' in locals() and conn:
            conn.close()


def init_extra_tables():
    """Tạo các bảng mới nếu chưa có."""
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
                product_name TEXT, price VARCHAR(200),
                payment_method VARCHAR(50), fullname VARCHAR(100),
                phone VARCHAR(20), email VARCHAR(120), address TEXT,
                status VARCHAR(20) DEFAULT 'paid',
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
    except Exception as e:
        print(f"[init_extra_tables] Warning: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
