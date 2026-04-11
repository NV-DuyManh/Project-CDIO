"""
routes/analytics_routes.py
==========================
API cho Admin Dashboard: KPIs, charts, scraper status, DB viewer.

Thêm vào app.py:
    from routes.analytics_routes import analytics_bp
    app.register_blueprint(analytics_bp)
"""

from flask import Blueprint, jsonify, request
import pymysql.cursors

from database.db import get_db_connection
from utils.helpers import admin_required

analytics_bp = Blueprint('analytics', __name__)

ALLOWED_TABLES = {
    'users', 'orders', 'cart', 'favorites',
    'comments', 'search_history', 'price_history',
}


def _conn():
    return get_db_connection()

def _q(sql, params=()):
    conn = _conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql, params)
        return cur.fetchall() or []
    except Exception as e:
        print(f"[Analytics] {e}")
        return []
    finally:
        conn.close()

def _q1(sql, params=()):
    conn = _conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql, params)
        return cur.fetchone() or {}
    except Exception as e:
        print(f"[Analytics] {e}")
        return {}
    finally:
        conn.close()


@analytics_bp.route('/api/analytics/summary')
@admin_required
def summary():
    today  = _q1("SELECT COUNT(*) AS c FROM search_history WHERE DATE(created_at)=CURDATE()")
    total  = _q1("SELECT COUNT(*) AS c FROM search_history")
    users  = _q1("SELECT COUNT(*) AS c FROM users")
    orders = _q1("SELECT COUNT(*) AS c FROM orders")
    last_r = _q1("SELECT created_at FROM search_history ORDER BY created_at DESC LIMIT 1")
    last_crawl = (
        last_r['created_at'].strftime('%H:%M:%S')
        if last_r and last_r.get('created_at') else '--:--:--'
    )
    site_rows = _q("SELECT site, COUNT(*) AS cnt FROM search_history GROUP BY site")
    total_p   = total.get('c') or 1
    weak      = sum(1 for r in site_rows if r['cnt'] / total_p < 0.02)
    err_rate  = round(weak / max(len(site_rows), 1) * 100, 1)
    return jsonify({
        'today_count': today.get('c', 0),
        'total_count': total.get('c', 0),
        'user_count':  users.get('c', 0),
        'order_count': orders.get('c', 0),
        'error_rate':  err_rate,
        'last_crawl':  last_crawl,
    })


@analytics_bp.route('/api/analytics/top-keywords')
@admin_required
def top_keywords():
    rows = _q("SELECT keyword, COUNT(*) AS cnt FROM search_history GROUP BY keyword ORDER BY cnt DESC LIMIT 10")
    return jsonify([{'keyword': r['keyword'], 'count': r['cnt']} for r in rows])


@analytics_bp.route('/api/analytics/site-distribution')
@admin_required
def site_distribution():
    rows  = _q("SELECT site, COUNT(*) AS cnt FROM search_history GROUP BY site ORDER BY cnt DESC")
    total = sum(r['cnt'] for r in rows) or 1
    return jsonify([
        {'site': r['site'], 'count': r['cnt'], 'percent': round(r['cnt']/total*100, 1)}
        for r in rows
    ])


@analytics_bp.route('/api/analytics/scraper-status')
@admin_required
def scraper_status():
    from config.config import STORES
    rows = _q("SELECT site, COUNT(*) AS cnt FROM search_history WHERE created_at >= NOW() - INTERVAL 24 HOUR GROUP BY site")
    count_map = {r['site']: r['cnt'] for r in rows}
    return jsonify([
        {'name': s, 'count': count_map.get(s, 0), 'online': count_map.get(s, 0) > 0}
        for s in STORES
    ])


@analytics_bp.route('/api/analytics/crawl-trend')
@admin_required
def crawl_trend():
    rows = _q("SELECT DATE(created_at) AS day, COUNT(*) AS cnt FROM search_history WHERE created_at >= NOW() - INTERVAL 7 DAY GROUP BY DATE(created_at) ORDER BY day ASC")
    return jsonify([{'day': str(r['day']), 'count': r['cnt']} for r in rows])


@analytics_bp.route('/api/bot-logs')
@admin_required
def bot_logs():
    rows = _q("SELECT site, keyword, created_at, COUNT(*) AS cnt FROM search_history WHERE created_at >= NOW() - INTERVAL 2 HOUR GROUP BY site, keyword, DATE_FORMAT(created_at,'%Y-%m-%d %H:%i') ORDER BY created_at DESC LIMIT 30")
    logs = []
    for r in rows:
        ts  = r.get('created_at')
        t   = ts.strftime('%H:%M:%S') if ts else '??:??:??'
        ico = '✅' if r['cnt'] > 0 else '❌'
        logs.append(f"[{t}] {ico} [{r['site']}] {r['cnt']} sp — {r['keyword']}")
    return jsonify(logs)


# ── Database Viewer ────────────────────────────────────────────────────

@analytics_bp.route('/api/admin/tables')
@admin_required
def db_tables():
    result = []
    for tbl in sorted(ALLOWED_TABLES):
        try:
            row = _q1(f"SELECT COUNT(*) AS c FROM `{tbl}`")
            result.append({'name': tbl, 'rows': row.get('c', 0)})
        except Exception:
            result.append({'name': tbl, 'rows': -1})
    return jsonify(result)


@analytics_bp.route('/api/admin/table/<name>')
@admin_required
def db_table_data(name):
    if name not in ALLOWED_TABLES:
        return jsonify({'error': 'Bảng không được phép'}), 403

    page     = max(1, int(request.args.get('page', 1)))
    per_page = min(100, int(request.args.get('per_page', 20)))
    search   = request.args.get('search', '').strip()
    offset   = (page - 1) * per_page

    conn = _conn()
    try:
        cur = conn.cursor(pymysql.cursors.DictCursor)
        cur.execute(f"DESCRIBE `{name}`")
        columns = [r['Field'] for r in cur.fetchall()]

        if search and columns:
            like_clauses = " OR ".join(f"CAST(`{c}` AS CHAR) LIKE %s" for c in columns)
            like_vals    = [f'%{search}%'] * len(columns)
            cur.execute(f"SELECT COUNT(*) AS c FROM `{name}` WHERE {like_clauses}", like_vals)
            total = cur.fetchone()['c']
            cur.execute(f"SELECT * FROM `{name}` WHERE {like_clauses} LIMIT %s OFFSET %s",
                        like_vals + [per_page, offset])
        else:
            cur.execute(f"SELECT COUNT(*) AS c FROM `{name}`")
            total = cur.fetchone()['c']
            try:
                cur.execute(f"SELECT * FROM `{name}` ORDER BY id DESC LIMIT %s OFFSET %s",
                            (per_page, offset))
            except Exception:
                cur.execute(f"SELECT * FROM `{name}` LIMIT %s OFFSET %s",
                            (per_page, offset))

        rows = cur.fetchall() or []

        import datetime
        safe_rows = []
        for row in rows:
            safe_row = {}
            for k, v in row.items():
                if isinstance(v, (datetime.datetime, datetime.date)):
                    safe_row[k] = str(v)
                elif isinstance(v, bytes):
                    safe_row[k] = v.decode('utf-8', errors='replace')
                else:
                    safe_row[k] = v
            safe_rows.append(safe_row)

        return jsonify({
            'columns':     columns,
            'rows':        safe_rows,
            'total':       total,
            'page':        page,
            'per_page':    per_page,
            'total_pages': max(1, (total + per_page - 1) // per_page),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()