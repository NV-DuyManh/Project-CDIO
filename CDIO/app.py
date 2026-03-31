from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask

from config.config   import SECRET_KEY
from database.db     import init_extra_tables

from routes.search_routes import search_bp
from routes.upload_routes import upload_bp
from routes.auth_routes   import auth_bp
from routes.cart_routes   import cart_bp
from routes.admin_routes  import admin_bp
from routes.alert_routes  import alert_bp   # ← NEW


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    app.register_blueprint(search_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(alert_bp)   # ← NEW

    return app


if __name__ == "__main__":
    app = create_app()
    init_extra_tables()

    # ── Start background pre-warmer ──────────────────────────────
    from services.prewarm_service import start_prewarm_scheduler
    start_prewarm_scheduler()

    app.run(debug=True, use_reloader=False)  # use_reloader=False avoids double thread