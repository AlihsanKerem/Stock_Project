import sqlite3
import os

DB_FILE = "stocks.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_data (
            symbol TEXT PRIMARY KEY,
            price REAL,
            rsi REAL,
            volume REAL,
            pb_ratio REAL,
            pe_ratio REAL,
            div_yield REAL,
            signals TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_stocks (
            symbol TEXT PRIMARY KEY,
            last_price REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_stock_data(data_list):
    """
    data_list: list of dicts. 
    Each dict should have: symbol, price, rsi, volume, pb_ratio, pe_ratio, div_yield, signals (comma separated string)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    for item in data_list:
        cursor.execute('''
            INSERT INTO stock_data (symbol, price, rsi, volume, pb_ratio, pe_ratio, div_yield, signals, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET
                price=excluded.price,
                rsi=excluded.rsi,
                volume=excluded.volume,
                pb_ratio=excluded.pb_ratio,
                pe_ratio=excluded.pe_ratio,
                div_yield=excluded.div_yield,
                signals=excluded.signals,
                updated_at=CURRENT_TIMESTAMP
        ''', (
            item.get('symbol'),
            item.get('price'),
            item.get('rsi'),
            item.get('volume'),
            item.get('pb_ratio'),
            item.get('pe_ratio'),
            item.get('div_yield'),
            item.get('signals', '')
        ))
    
    conn.commit()
    conn.close()

def get_all_stock_data():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_data ORDER BY symbol ASC")
    rows = cursor.fetchall()
    conn.close()
    
    # Return list of dicts
    return [dict(row) for row in rows]

def add_tracked_stock(symbol, last_price=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tracked_stocks (symbol, last_price, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(symbol) DO UPDATE SET
            last_price=excluded.last_price,
            updated_at=CURRENT_TIMESTAMP
    ''', (symbol, last_price))
    conn.commit()
    conn.close()

def remove_tracked_stock(symbol):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tracked_stocks WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

def get_tracked_stocks():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracked_stocks ORDER BY symbol ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_tracked_stock_price(symbol, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE tracked_stocks 
        SET last_price = ?, updated_at = CURRENT_TIMESTAMP
        WHERE symbol = ?
    ''', (price, symbol))
    conn.commit()
    conn.close()

# Initialize db when this file is imported
init_db()
