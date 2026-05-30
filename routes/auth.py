# =============================================================================
# routes/auth.py — Authentication Blueprint
# รับผิดชอบ: สมัครสมาชิก, เข้าสู่ระบบ, ออกจากระบบ
# API Endpoints:
#   GET/POST  /register  → หน้าสมัครสมาชิก
#   GET/POST  /login     → หน้าเข้าสู่ระบบ
#   GET       /logout    → ออกจากระบบ
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import database

# สร้าง Blueprint ชื่อ 'auth' — url_prefix ไม่มี (ใช้ path ตรง)
auth_bp = Blueprint('auth', __name__)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def is_logged_in() -> bool:
    """ตรวจสอบว่าผู้ใช้งานล็อกอินอยู่หรือไม่"""
    return 'user_id' in session


# ---------------------------------------------------------------------------
# GET/POST /register — สมัครสมาชิก
# ---------------------------------------------------------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if is_logged_in():
        return redirect(url_for('home.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้งานและรหัสผ่าน', 'danger')
            return redirect(url_for('auth.register'))

        password_hash = generate_password_hash(password)
        conn = database.get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            conn.commit()
            flash('สมัครสมาชิกสำเร็จแล้ว! สามารถเข้าสู่ระบบได้ทันที', 'success')
            return redirect(url_for('auth.login'))
        except sqlite3.IntegrityError:
            flash('ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว กรุณาเลือกชื่ออื่น', 'danger')
        finally:
            conn.close()

    return render_template('register.html')


# ---------------------------------------------------------------------------
# GET/POST /login — เข้าสู่ระบบ
# ---------------------------------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('home.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('กรุณากรอกชื่อผู้ใช้งานและรหัสผ่าน', 'danger')
            return redirect(url_for('auth.login'))

        conn = database.get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash(f'ยินดีต้อนรับกลับมา คุณ {user["username"]}!', 'success')
            return redirect(url_for('home.index'))
        else:
            flash('ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง', 'danger')

    return render_template('login.html')


# ---------------------------------------------------------------------------
# GET /logout — ออกจากระบบ
# ---------------------------------------------------------------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('ออกจากระบบเรียบร้อยแล้ว', 'success')
    return redirect(url_for('auth.login'))
