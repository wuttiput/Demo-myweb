# =============================================================================
# routes/home.py — Home Page Blueprint
# รับผิดชอบ: หน้าหลักหลังล็อกอิน (เลือกฟีเจอร์ที่ต้องการใช้งาน)
# API Endpoints:
#   GET  /        → redirect ไป /home
#   GET  /home    → หน้าเมนูหลัก
# =============================================================================

from flask import Blueprint, render_template, redirect, url_for, session
from routes.auth import is_logged_in

# สร้าง Blueprint ชื่อ 'home'
home_bp = Blueprint('home', __name__)


# ---------------------------------------------------------------------------
# GET / — Redirect ไปหน้าหลัก
# ---------------------------------------------------------------------------
@home_bp.route('/')
def root():
    if is_logged_in():
        return redirect(url_for('home.index'))
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# GET /home — หน้าหลัก (เลือกฟีเจอร์)
# ---------------------------------------------------------------------------
@home_bp.route('/home')
def index():
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    username = session['username']
    return render_template('home.html', username=username)
