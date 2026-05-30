import sqlite3
import os

# =============================================================================
# database.py — Database Module
# รับผิดชอบ: เชื่อมต่อ SQLite และสร้างตารางทั้งหมดของแอปพลิเคชัน
#
# ตารางทั้งหมด:
#   users        — ข้อมูลบัญชีผู้ใช้
#   transactions — รายรับ-รายจ่ายรายวัน (Finance Tracker)
#   todos        — รายการสิ่งที่ต้องทำรายวัน (To-Do List)
# =============================================================================

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'finance.db')


def get_db_connection():
    """สร้างและคืน connection ไปยัง SQLite database"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row          # เข้าถึงคอลัมน์ด้วยชื่อ เช่น row['username']
    conn.execute("PRAGMA foreign_keys = ON;")  # บังคับใช้ Foreign Key
    return conn


def init_db():
    """สร้างตารางทั้งหมดหากยังไม่มีอยู่ใน database"""
    conn   = get_db_connection()
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # ตาราง: users
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL
        )
    ''')

    # ------------------------------------------------------------------
    # ตาราง: transactions (Finance Tracker)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            type        TEXT    NOT NULL CHECK(type IN ('income', 'expense')),
            amount      REAL    NOT NULL,
            description TEXT,
            date        TEXT    NOT NULL DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ------------------------------------------------------------------
    # ตาราง: todos (To-Do List)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title   TEXT    NOT NULL,
            is_done INTEGER NOT NULL DEFAULT 0,   -- 0 = ยังไม่เสร็จ, 1 = เสร็จแล้ว
            date    TEXT    NOT NULL DEFAULT (date('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ------------------------------------------------------------------
    # ตาราง: news (AI News Reader)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            title          TEXT NOT NULL,
            summary        TEXT NOT NULL,
            url            TEXT UNIQUE NOT NULL,
            published_date TEXT,
            source         TEXT,
            category       TEXT,
            created_at     TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ------------------------------------------------------------------
    # ตาราง: news_metadata
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS news_metadata (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # ------------------------------------------------------------------
    # ตาราง: chat_sessions (AI Chat Room)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id         TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL,
            title      TEXT NOT NULL DEFAULT 'บทสนทนาใหม่',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # ------------------------------------------------------------------
    # ตาราง: chat_messages (AI Chat Messages)
    # ------------------------------------------------------------------
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender     TEXT NOT NULL CHECK(sender IN ('user', 'assistant')),
            model_used TEXT,
            message    TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()




if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")
