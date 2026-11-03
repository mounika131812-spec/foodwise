"""SQLite database layer for the Smart Food Waste Management Platform."""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'foodwaste.db')


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def compute_status(expiry_date, explicit=None):
    """Derive a food item's status from its expiry date.

    Kept in sync with the frontend's `getStatus()` in public/js/app.js:
      wasted  -> 'wasted'  (only when explicitly requested, e.g. via waste logging)
      past    -> 'expired'
      within 3 days -> 'expiring'
      else    -> 'fresh'
    """
    if explicit:
        return explicit
    from datetime import date
    today = date.today()
    y, m, d = map(int, expiry_date.split('-'))
    diff = (date(y, m, d) - today).days
    if diff < 0:
        return 'expired'
    if diff <= 3:
        return 'expiring'
    return 'fresh'


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'household',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            purchase_date TEXT NOT NULL,
            expiry_date TEXT NOT NULL,
            location TEXT NOT NULL DEFAULT 'fridge',
            notes TEXT,
            status TEXT NOT NULL DEFAULT 'fresh',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS waste_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_item_id INTEGER,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            waste_date TEXT NOT NULL DEFAULT (datetime('now')),
            reason TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            ingredients TEXT NOT NULL,
            instructions TEXT NOT NULL,
            prep_time INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_food_user ON food_items(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_food_expiry ON food_items(expiry_date);
        CREATE INDEX IF NOT EXISTS idx_waste_user ON waste_log(user_id, waste_date);
    ''')
    conn.commit()
    conn.close()
    print('Database initialized at', DB_PATH)