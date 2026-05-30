# =============================================================================
# routes/chat.py — Multi-Model AI Chat Blueprint
# รับผิดชอบ: จัดการประวัติการสนทนาและการคุยกับ AI บอทหลายค่าย
# API Endpoints:
#   GET   /chat                     → หน้าแชทบอร์ด (และโหลด Session ที่กำหนด)
#   POST  /chat/session/create      → สร้างห้องสนทนาใหม่
#   POST  /chat/session/delete/<id> → ลบห้องสนทนา
#   POST  /chat/send                → ส่งข้อความคุยกับ AI (AJAX - JSON)
# =============================================================================

import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
import database
import ai_chat_agent
from routes.auth import is_logged_in

# สร้าง Blueprint ชื่อ 'chat'
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

# ---------------------------------------------------------------------------
# GET /chat — หน้าแชทบอร์ด
# ---------------------------------------------------------------------------
@chat_bp.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    username = session['username']
    
    # ดึงรหัสห้องแชทที่เลือก
    selected_session_id = request.args.get('session_id', '').strip()
    
    conn = database.get_db_connection()
    
    # 1. ดึงรายการห้องสนทนาทั้งหมดของผู้นี้ (เรียงตามห้องที่สร้างล่าสุดอยู่บนสุด)
    chat_sessions = conn.execute("""
        SELECT id, title, created_at
        FROM chat_sessions
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()
    
    # หากไม่ได้ระบุห้องแชท แต่มีห้องแชทค้างอยู่ ให้รีไดเรกต์ไปห้องล่าสุด
    if not selected_session_id and chat_sessions:
        conn.close()
        return redirect(url_for('chat.index', session_id=chat_sessions[0]['id']))
        
    # 2. ดึงประวัติข้อความของห้องแชทที่เลือก
    messages = []
    current_session = None
    if selected_session_id:
        # ตรวจสอบการเป็นเจ้าของห้องแชทก่อน
        current_session = conn.execute("""
            SELECT id, title 
            FROM chat_sessions 
            WHERE id = ? AND user_id = ?
        """, (selected_session_id, user_id)).fetchone()
        
        if current_session:
            messages = conn.execute("""
                SELECT sender, model_used, message, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
            """, (selected_session_id,)).fetchall()
            
    conn.close()
    
    # 3. ดึงรายการโมเดล AI ที่มีสิทธิ์และพร้อมใช้งาน
    available_models = ai_chat_agent.get_available_models()
    
    return render_template(
        'chat.html',
        username=username,
        chat_sessions=chat_sessions,
        messages=messages,
        current_session=current_session,
        available_models=available_models,
        selected_session_id=selected_session_id
    )

# ---------------------------------------------------------------------------
# POST /chat/session/create — สร้างห้องสนทนาใหม่
# ---------------------------------------------------------------------------
@chat_bp.route('/session/create', methods=['POST'])
def create_session():
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    new_session_id = uuid.uuid4().hex # สร้าง Unique ID
    
    conn = database.get_db_connection()
    try:
        conn.execute("""
            INSERT INTO chat_sessions (id, user_id, title)
            VALUES (?, ?, 'บทสนทนาใหม่')
        """, (new_session_id, user_id))
        conn.commit()
    except Exception as e:
        print(f"Error creating chat session: {e}")
        flash("ไม่สามารถสร้างห้องสนทนาได้", "danger")
    finally:
        conn.close()
        
    return redirect(url_for('chat.index', session_id=new_session_id))

# ---------------------------------------------------------------------------
# POST /chat/session/delete/<id> — ลบห้องสนทนา
# ---------------------------------------------------------------------------
@chat_bp.route('/session/delete/<session_id>', methods=['POST'])
def delete_session(session_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    
    conn = database.get_db_connection()
    # ป้องกันการยิงสุ่มลบโดยการเช็ค user_id
    conn.execute("DELETE FROM chat_sessions WHERE id = ? AND user_id = ?", (session_id, user_id))
    conn.commit()
    conn.close()
    
    flash("ลบประวัติการสนทนาเรียบร้อยแล้ว", "success")
    return redirect(url_for('chat.index'))

# ---------------------------------------------------------------------------
# POST /chat/send — ส่งข้อความแชทไปให้ AI ประมวลผลและเซฟประวัติ
# ---------------------------------------------------------------------------
@chat_bp.route('/send', methods=['POST'])
def send_message():
    if not is_logged_in():
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
        
    session_id = data.get("session_id", "").strip()
    message_text = data.get("message", "").strip()
    model_id = data.get("model_id", "gemini").strip()
    
    if not session_id or not message_text:
        return jsonify({"error": "กรุณากรอกข้อความ"}), 400
        
    user_id = session['user_id']
    
    conn = database.get_db_connection()
    
    # 1. ยืนยันสิทธิ์ในห้องแชท
    session_row = conn.execute("""
        SELECT title FROM chat_sessions 
        WHERE id = ? AND user_id = ?
    """, (session_id, user_id)).fetchone()
    
    if not session_row:
        conn.close()
        return jsonify({"error": "ไม่พบห้องสนทนา หรือคุณไม่มีสิทธิ์ใช้งาน"}), 403
        
    # 2. บันทึกข้อความของผู้ใช้ (User Message)
    conn.execute("""
        INSERT INTO chat_messages (session_id, sender, message)
        VALUES (?, 'user', ?)
    """, (session_id, message_text))
    
    # 3. อัปเดตชื่อห้องแชทอัตโนมัติหากเป็นชื่อเริ่มต้น
    renamed_title = None
    if session_row['title'] == 'บทสนทนาใหม่':
        # ใช้ข้อความคำแรกยาวไม่เกิน 25 ตัวอักษร
        new_title = message_text[:25] + '...' if len(message_text) > 25 else message_text
        conn.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (new_title, session_id))
        renamed_title = new_title
        
    # 4. ดึงประวัติคำถามตอบย้อนหลังในห้องนี้ส่งไปเป็น Context (ดึงมาสูงสุด 10 ข้อความย้อนหลัง)
    # เพื่อประหยัดโทเคนและป้องกันคีย์เต็ม
    db_history = conn.execute("""
        SELECT sender, message
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY id ASC
    """, (session_id,)).fetchall()
    
    # ตัวแปรส่งประวัติ (ยกเว้นข้อความผู้ใช้ปัจจุบันอันสุดท้าย เพราะเราจะผ่านแยกไปในฟังก์ชัน)
    history_list = [{"sender": r['sender'], "message": r['message']} for r in db_history[:-1]]
    
    # 5. เรียกประมวลผลการคุยกับ AI บอทผ่าน API
    ai_response = ai_chat_agent.generate_ai_response(model_id, message_text, history_list)
    
    # 6. บันทึกคำตอบของ AI ลงฐานข้อมูล
    conn.execute("""
        INSERT INTO chat_messages (session_id, sender, model_used, message)
        VALUES (?, 'assistant', ?, ?)
    """, (session_id, model_id, ai_response))
    
    conn.commit()
    conn.close()
    
    # คืนค่าคำตอบและชื่อห้องใหม่ (ถ้ามี) ไปทาง JSON
    response_data = {"response": ai_response}
    if renamed_title:
        response_data["renamed_title"] = renamed_title
        
    return jsonify(response_data)
