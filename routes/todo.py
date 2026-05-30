# =============================================================================
# routes/todo.py — To-Do List Blueprint
# รับผิดชอบ: จัดการรายการสิ่งที่ต้องทำรายวัน
# API Endpoints:
#   GET        /todo                  → หน้า To-Do (query: ?date=YYYY-MM-DD)
#   POST       /todo/add              → เพิ่มรายการ To-Do
#   POST       /todo/toggle/<id>      → Toggle เสร็จ/ยังไม่เสร็จ
#   POST       /todo/delete/<id>      → ลบรายการ To-Do
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import database
from routes.auth import is_logged_in

# สร้าง Blueprint ชื่อ 'todo' — ทุก route จะขึ้นต้นด้วย /todo
todo_bp = Blueprint('todo', __name__, url_prefix='/todo')


# ---------------------------------------------------------------------------
# GET /todo — หน้ารายการ To-Do รายวัน
# ---------------------------------------------------------------------------
@todo_bp.route('/')
def index():
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id  = session['user_id']
    username = session['username']

    # --- คำนวณวันที่ที่จะแสดง ---
    selected_date = request.args.get('date', '').strip()
    today_str     = datetime.now().strftime('%Y-%m-%d')

    if not selected_date:
        selected_date = today_str

    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    except ValueError:
        selected_date     = today_str
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')

    prev_date = (selected_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (selected_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    is_today  = (selected_date == today_str)

    conn = database.get_db_connection()

    # --- ดึงรายการ To-Do ของวันที่เลือก (เรียงตาม: ยังไม่เสร็จก่อน, แล้วค่อยเรียงตาม id) ---
    todos = conn.execute('''
        SELECT id, title, is_done, date
        FROM todos
        WHERE user_id = ? AND date = ?
        ORDER BY is_done ASC, id ASC
    ''', (user_id, selected_date)).fetchall()

    # --- นับสถิติรายการ ---
    stats = conn.execute('''
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN is_done = 1 THEN 1 ELSE 0 END) AS done
        FROM todos
        WHERE user_id = ? AND date = ?
    ''', (user_id, selected_date)).fetchone()

    conn.close()

    total_todos = stats['total'] or 0
    done_todos  = stats['done']  or 0

    return render_template(
        'todo.html',
        username=username,
        todos=todos,
        total_todos=total_todos,
        done_todos=done_todos,
        selected_date=selected_date,
        prev_date=prev_date,
        next_date=next_date,
        today_date=today_str,
        is_today=is_today
    )


# ---------------------------------------------------------------------------
# POST /todo/add — เพิ่มรายการ To-Do ใหม่
# ---------------------------------------------------------------------------
@todo_bp.route('/add', methods=['POST'])
def add():
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    title   = request.form.get('title', '').strip()
    date    = request.form.get('date', '').strip()

    # --- ตรวจสอบอินพุต ---
    if not title:
        flash('กรุณากรอกรายการที่ต้องทำ', 'danger')
        return redirect(url_for('todo.index', date=date or datetime.now().strftime('%Y-%m-%d')))

    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = database.get_db_connection()
    conn.execute(
        'INSERT INTO todos (user_id, title, date) VALUES (?, ?, ?)',
        (user_id, title, date)
    )
    conn.commit()
    conn.close()

    flash('เพิ่มรายการเรียบร้อยแล้ว', 'success')
    return redirect(url_for('todo.index', date=date))


# ---------------------------------------------------------------------------
# POST /todo/toggle/<id> — สลับสถานะเสร็จ/ยังไม่เสร็จ
# ---------------------------------------------------------------------------
@todo_bp.route('/toggle/<int:todo_id>', methods=['POST'])
def toggle(todo_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn    = database.get_db_connection()

    todo = conn.execute(
        'SELECT id, is_done, date FROM todos WHERE id = ? AND user_id = ?',
        (todo_id, user_id)
    ).fetchone()

    redirect_date = datetime.now().strftime('%Y-%m-%d')

    if todo:
        redirect_date = todo['date']
        new_status    = 0 if todo['is_done'] else 1
        conn.execute('UPDATE todos SET is_done = ? WHERE id = ?', (new_status, todo_id))
        conn.commit()
    else:
        flash('ไม่พบรายการ หรือคุณไม่มีสิทธิ์แก้ไขรายการนี้', 'danger')

    conn.close()
    return redirect(url_for('todo.index', date=redirect_date))


# ---------------------------------------------------------------------------
# POST /todo/delete/<id> — ลบรายการ To-Do
# ---------------------------------------------------------------------------
@todo_bp.route('/delete/<int:todo_id>', methods=['POST'])
def delete(todo_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn    = database.get_db_connection()

    todo = conn.execute(
        'SELECT date FROM todos WHERE id = ? AND user_id = ?',
        (todo_id, user_id)
    ).fetchone()

    redirect_date = datetime.now().strftime('%Y-%m-%d')

    if todo:
        redirect_date = todo['date']
        conn.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        conn.commit()
        flash('ลบรายการเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่พบรายการ หรือคุณไม่มีสิทธิ์ลบรายการนี้', 'danger')

    conn.close()
    return redirect(url_for('todo.index', date=redirect_date))
