# =============================================================================
# routes/finance.py — Finance Tracker Blueprint
# รับผิดชอบ: บันทึกรายรับ-รายจ่าย ดูยอดรายวัน เพิ่ม/ลบรายการ
# API Endpoints:
#   GET        /finance               → หน้า Dashboard (รายวัน, query: ?date=YYYY-MM-DD)
#   POST       /finance/add           → เพิ่มรายการธุรกรรม
#   POST       /finance/delete/<id>   → ลบรายการธุรกรรม
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import database
from routes.auth import is_logged_in

# สร้าง Blueprint ชื่อ 'finance' — ทุก route จะขึ้นต้นด้วย /finance
finance_bp = Blueprint('finance', __name__, url_prefix='/finance')


# ---------------------------------------------------------------------------
# GET /finance — หน้า Dashboard รายรับ-รายจ่ายรายวัน
# ---------------------------------------------------------------------------
@finance_bp.route('/')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id  = session['user_id']
    username = session['username']

    # --- คำนวณวันที่ที่จะแสดง ---
    selected_date = request.args.get('date', '').strip()
    today_str = datetime.now().strftime('%Y-%m-%d')

    if not selected_date:
        selected_date = today_str

    try:
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
    except ValueError:
        selected_date = today_str
        selected_date_obj = datetime.strptime(selected_date, '%Y-%m-%d')

    prev_date = (selected_date_obj - timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (selected_date_obj + timedelta(days=1)).strftime('%Y-%m-%d')
    is_today  = (selected_date == today_str)

    conn = database.get_db_connection()

    # --- ดึงรายการธุรกรรมของวันที่เลือก ---
    transactions = conn.execute('''
        SELECT id, type, amount, description, date
        FROM transactions
        WHERE user_id = ? AND date = ?
        ORDER BY id DESC
    ''', (user_id, selected_date)).fetchall()

    # --- คำนวณยอดรวมรายรับ/รายจ่ายของวันที่เลือก ---
    totals = conn.execute('''
        SELECT
            SUM(CASE WHEN type = 'income'  THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS total_expense
        FROM transactions
        WHERE user_id = ? AND date = ?
    ''', (user_id, selected_date)).fetchone()

    conn.close()

    total_income  = totals['total_income']  or 0.0
    total_expense = totals['total_expense'] or 0.0
    balance       = total_income - total_expense

    return render_template(
        'dashboard.html',
        username=username,
        transactions=transactions,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        selected_date=selected_date,
        prev_date=prev_date,
        next_date=next_date,
        today_date=today_str,
        is_today=is_today
    )


# ---------------------------------------------------------------------------
# POST /finance/add — เพิ่มรายการธุรกรรมใหม่
# ---------------------------------------------------------------------------
@finance_bp.route('/add', methods=['POST'])
def add():
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id          = session['user_id']
    transaction_type = request.form.get('type')
    amount_str       = request.form.get('amount')
    description      = request.form.get('description', '').strip()
    date             = request.form.get('date', '').strip()

    # --- ตรวจสอบอินพุต ---
    if not transaction_type or transaction_type not in ['income', 'expense']:
        flash('ประเภทรายการไม่ถูกต้อง', 'danger')
        return redirect(url_for('finance.dashboard'))

    if not amount_str:
        flash('กรุณากรอกจำนวนเงิน', 'danger')
        return redirect(url_for('finance.dashboard'))

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash('จำนวนเงินต้องมากกว่าศูนย์', 'danger')
            return redirect(url_for('finance.dashboard'))
    except ValueError:
        flash('กรุณากรอกจำนวนเงินเป็นตัวเลขที่ถูกต้อง', 'danger')
        return redirect(url_for('finance.dashboard'))

    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    conn = database.get_db_connection()
    conn.execute(
        'INSERT INTO transactions (user_id, type, amount, description, date) VALUES (?, ?, ?, ?, ?)',
        (user_id, transaction_type, amount, description, date)
    )
    conn.commit()
    conn.close()

    flash('บันทึกรายการรายรับ-รายจ่ายเรียบร้อยแล้ว', 'success')
    return redirect(url_for('finance.dashboard', date=date))


# ---------------------------------------------------------------------------
# POST /finance/delete/<id> — ลบรายการธุรกรรม
# ---------------------------------------------------------------------------
@finance_bp.route('/delete/<int:transaction_id>', methods=['POST'])
def delete(transaction_id):
    if not is_logged_in():
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    conn    = database.get_db_connection()

    # ดึงวันที่ก่อนลบ เพื่อ redirect กลับมาหน้าวันเดิม
    tx = conn.execute(
        'SELECT date FROM transactions WHERE id = ? AND user_id = ?',
        (transaction_id, user_id)
    ).fetchone()

    redirect_date = datetime.now().strftime('%Y-%m-%d')

    if tx:
        redirect_date = tx['date']
        conn.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        conn.commit()
        flash('ลบรายการเรียบร้อยแล้ว', 'success')
    else:
        flash('ไม่พบรายการ หรือคุณไม่มีสิทธิ์ลบรายการนี้', 'danger')

    conn.close()
    return redirect(url_for('finance.dashboard', date=redirect_date))
