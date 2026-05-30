# =============================================================================
# app.py — Application Entry Point
# รับผิดชอบ: สร้าง Flask app, ลงทะเบียน Blueprints, เริ่มต้น database
#
# โครงสร้าง Blueprint:
#   auth_bp    → /register, /login, /logout
#   home_bp    → /, /home
#   finance_bp → /finance, /finance/add, /finance/delete/<id>
#   todo_bp    → /todo, /todo/add, /todo/toggle/<id>, /todo/delete/<id>
# =============================================================================

from flask import Flask
import database

# --- Import Blueprints จากโฟลเดอร์ routes/ ---
from routes.auth    import auth_bp
from routes.home    import home_bp
from routes.finance import finance_bp
from routes.todo    import todo_bp
from routes.news    import news_bp
from routes.chat    import chat_bp

# ---------------------------------------------------------------------------
# สร้าง Flask Application
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = 'finance-tracker-very-secret-key-to-keep-session-safe'

# ---------------------------------------------------------------------------
# ลงทะเบียน Blueprints
# ---------------------------------------------------------------------------
app.register_blueprint(auth_bp)     # /register, /login, /logout
app.register_blueprint(home_bp)     # /, /home
app.register_blueprint(finance_bp)  # /finance/*
app.register_blueprint(todo_bp)     # /todo/*
app.register_blueprint(news_bp)     # /news/*
app.register_blueprint(chat_bp)     # /chat/*



# ---------------------------------------------------------------------------
# เริ่มต้นสร้างตารางฐานข้อมูล (ถ้ายังไม่มี)
# ---------------------------------------------------------------------------
database.init_db()

# ---------------------------------------------------------------------------
# รันเซิร์ฟเวอร์
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
