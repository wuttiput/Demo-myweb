# =============================================================================
# routes/news.py — Tech & AI News Reader Blueprint
# รับผิดชอบ: ดึงข่าวสารและสรุปข่าวด้วย AI
# API Endpoints:
#   GET   /news           → หน้ารายการข่าวสาร (และตรวจสอบการอัปเดตแบบขี้เกียจ/Lazy Update)
#   GET   /news/status    → เช็คสถานะการอัปเดตเบื้องหลัง (JSON)
#   POST  /news/refresh   → กดอัปเดตข่าวสารแบบแมนนวล (ผ่าน Background Thread)
# =============================================================================

import os
import threading
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, session, jsonify, flash
import database
import news_agent
from routes.auth import is_logged_in

# สร้าง Blueprint ชื่อ 'news'
news_bp = Blueprint('news', __name__, url_prefix='/news')

# ---------------------------------------------------------------------------
# กลไก Thread-safety ป้องกัน Race Condition
# ---------------------------------------------------------------------------
IS_UPDATING = False
update_lock = threading.Lock()

def trigger_bg_update(force=False):
    """ตรวจสอบเวลาอัปเดตล่าสุดและทำการสปอน Background Thread เพื่อดึงข่าวใหม่"""
    global IS_UPDATING
    
    # หากกำลังทำงานอยู่ ข้ามขั้นตอน
    if IS_UPDATING:
        return False
        
    # เช็คเวลาอัปเดตล่าสุดจากฐานข้อมูล (ข้ามถ้าสั่ง Force=True)
    if not force:
        conn = database.get_db_connection()
        row = conn.execute("SELECT value FROM news_metadata WHERE key = 'last_updated_time'").fetchone()
        conn.close()
        
        if row:
            try:
                last_updated = datetime.strptime(row['value'], '%Y-%m-%d %H:%M:%S')
                # 6 ชั่วโมง = 21,600 วินาที
                diff_seconds = (datetime.now() - last_updated).total_seconds()
                if diff_seconds < 21600:
                    return False  # ยังไม่ถึงเวลาอัปเดต (6 ชั่วโมง)
            except Exception as e:
                print(f"Error parsing metadata date: {e}")
                pass # หากพาร์สวันเวลาพัง ให้รันอัปเดตต่อไป
    
    # ป้องกันการแข่งกันรันด้วย Lock
    with update_lock:
        if not IS_UPDATING:
            IS_UPDATING = True
            
            def bg_task():
                global IS_UPDATING
                print("[News Thread] Background update started...")
                try:
                    news_agent.update_news_data()
                except Exception as e:
                    print(f"[News Thread] Error running news agent update: {e}")
                finally:
                    with update_lock:
                        IS_UPDATING = False
                    print("[News Thread] Background update finished.")
            
            # รัน Thread แยกเป็น Daemon เพื่อไม่ให้เซิร์ฟเวอร์ค้างตอนปิดตัว
            t = threading.Thread(target=bg_task, daemon=True)
            t.start()
            return True
            
    return False

# ---------------------------------------------------------------------------
# GET /news — หน้ารายการข่าวสาร
# ---------------------------------------------------------------------------
@news_bp.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    username = session['username']
    
    # เรียกตัวตรวจสอบและรันอัปเดตเบื้องหลัง (แบบ Lazy Update)
    triggered = trigger_bg_update(force=False)
    
    # ตรวจสอบประวัติข่าวในฐานข้อมูล
    conn = database.get_db_connection()
    news_list = conn.execute("""
        SELECT id, title, summary, url, published_date, source, category, created_at
        FROM news
        ORDER BY id DESC
        LIMIT 50
    """).fetchall()
    
    # ดึงเวลาล่าสุดที่อัปเดตเสร็จ
    last_update_row = conn.execute("SELECT value FROM news_metadata WHERE key = 'last_updated_time'").fetchone()
    conn.close()
    
    last_update_time = last_update_row['value'] if last_update_row else "ยังไม่มีการอัปเดต"
    
    # ตรวจสอบการตั้งค่า API Key เพื่อส่งแบนเนอร์แจ้งผู้ใช้ใน UI
    has_api_key = bool(os.getenv("GEMINI_API_KEY"))
    
    return render_template(
        'news.html',
        username=username,
        news_list=news_list,
        last_update_time=last_update_time,
        has_api_key=has_api_key,
        is_updating=IS_UPDATING
    )

# ---------------------------------------------------------------------------
# GET /news/status — เช็คสถานะการอัปเดตเบื้องหลัง (สำหรับ JS Polling)
# ---------------------------------------------------------------------------
@news_bp.route('/status')
def status():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"is_updating": IS_UPDATING})

# ---------------------------------------------------------------------------
# POST /news/refresh — กดอัปเดตข่าวสารแบบแมนนวล
# ---------------------------------------------------------------------------
@news_bp.route('/refresh', methods=['POST'])
def refresh():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    global IS_UPDATING
    if IS_UPDATING:
        flash("ระบบกำลังอัปเดตข้อมูลข่าวสารอยู่เบื้องหลัง กรุณารอสักครู่...", "warning")
    else:
        triggered = trigger_bg_update(force=True)
        if triggered:
            flash("เริ่มดึงข้อมูลข่าวสารใหม่เบื้องหลังแล้ว หน้าจอจะแจ้งเตือนเมื่อเสร็จสิ้น!", "info")
        else:
            flash("ไม่สามารถสั่งรันอัปเดตข่าวสารได้ในขณะนี้", "danger")
            
    return redirect(url_for('news.index'))
