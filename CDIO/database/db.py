import pymysql
import pymysql.cursors
from config.config import DB_CONFIG

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def get_data_from_db(keyword):
    """Lấy dữ liệu từ DB, trả về cả created_at để check thời gian cào."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        # Lấy thêm created_at để search_service biết giá cào từ lúc nào
        sql    = "SELECT *, created_at FROM search_history WHERE LOWER(keyword) = LOWER(%s) ORDER BY raw_price ASC"
        cursor.execute(sql, (keyword.strip(),))
        return cursor.fetchall()
    except Exception as e:
        print(f"Lỗi get_data_from_db: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def save_to_db(keyword, products, user_id=None):
    """Lưu kết quả cào kèm theo user_id để quản lý lịch sử theo tài khoản."""
    if not products:
        return
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        
        # Xóa dữ liệu cũ của từ khóa này để cập nhật giá mới nhất
        cursor.execute("DELETE FROM search_history WHERE LOWER(keyword) = LOWER(%s)", (keyword.strip(),))
        
        # Thêm user_id vào câu lệnh INSERT
        sql = """INSERT INTO search_history 
                 (keyword, user_id, site, title, price_str, raw_price, img, link) 
                 VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
        
        for p in products:
            cursor.execute(sql, (
                keyword.strip(), 
                user_id, # Lưu ID người dùng (có thể là None nếu khách chưa login)
                p['site'], 
                p['title'],
                p['price_str'], 
                p.get('raw_price', 0), 
                p['img'], 
                p['link']
            ))
        conn.commit()
    except Exception as e:
        print(f"Lỗi save_to_db: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def init_extra_tables():
    """Tạo và cập nhật cấu trúc các bảng."""
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Bảng Users (Giữ nguyên)
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

        # 2. Bảng Search History (NÂNG CẤP: Thêm user_id và created_at)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NULL,
                keyword VARCHAR(255),
                site VARCHAR(50),
                title TEXT,
                price_str VARCHAR(100),
                raw_price DECIMAL(15,2),
                img TEXT,
                link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # 3. Bảng Cart (Giữ nguyên)
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

        # 4. Bảng Orders (NÂNG CẤP: Để fix thanh toán)
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

        # 5. Các bảng khác (Favorites, Comments)
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
    """Lấy gợi ý từ lịch sử tìm kiếm chung."""
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