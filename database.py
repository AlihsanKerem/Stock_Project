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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            lot INTEGER NOT NULL,
            buy_price REAL NOT NULL,
            buy_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position_id INTEGER,
            symbol TEXT NOT NULL,
            lot INTEGER NOT NULL,
            buy_price REAL NOT NULL,
            sell_price REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            realized_pnl_pct REAL NOT NULL,
            sell_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            reference_price REAL NOT NULL,
            target_percentage REAL NOT NULL,
            target_price REAL NOT NULL,
            direction TEXT NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            triggered_at TIMESTAMP,
            triggered_price REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            signal_name TEXT NOT NULL,
            timeframe_key TEXT NOT NULL,
            timeframe_label TEXT NOT NULL,
            price_at_signal REAL NOT NULL,
            target_return TEXT,
            risk_level TEXT,
            rsi REAL,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# ==================== PORTFOLIO OPERATIONS ====================

def add_portfolio_position(symbol, lot, buy_price, buy_date=None, notes=None):
    """
    Yeni portföy pozisyonu ekler.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if buy_date:
        cursor.execute('''
            INSERT INTO portfolio (symbol, lot, buy_price, buy_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (symbol, lot, buy_price, buy_date, notes))
    else:
        cursor.execute('''
            INSERT INTO portfolio (symbol, lot, buy_price, notes)
            VALUES (?, ?, ?, ?)
        ''', (symbol, lot, buy_price, notes))
    conn.commit()
    position_id = cursor.lastrowid
    conn.close()
    return position_id

def get_portfolio_positions():
    """
    Tüm portföy pozisyonlarını döndürür.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM portfolio ORDER BY buy_date DESC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_portfolio_position(position_id):
    """
    Belirtilen ID'deki portföy pozisyonunu siler.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
    conn.commit()
    conn.close()

def update_portfolio_position(position_id, lot, buy_price, notes=None):
    """
    Mevcut portföy pozisyonunu günceller.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE portfolio
        SET lot = ?, buy_price = ?, notes = ?
        WHERE id = ?
    ''', (lot, buy_price, notes, position_id))
    conn.commit()
    conn.close()

# ==================== SETTINGS OPERATIONS ====================

def get_setting(key, default=None):
    """
    Ayarlar tablosundan bir anahtarın değerini çeker.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return default

def set_setting(key, value):
    """
    Ayarlar tablosuna bir anahtar-değer çifti kaydeder veya günceller.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    ''', (key, str(value)))
    conn.commit()
    conn.close()

# ==================== TRANSACTION / SALE OPERATIONS ====================

def record_sale(position_id, sell_lot, sell_price, notes=None):
    """
    Portföyden kısmi veya tam hisse satışı yapar, 
    transactions tablosuna gerçekleşen K/Z kaydeder.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM portfolio WHERE id = ?", (position_id,))
    pos = cursor.fetchone()
    
    if not pos:
        conn.close()
        raise ValueError("Satılmak istenen pozisyon bulunamadı.")
        
    pos = dict(pos)
    current_lot = int(pos['lot'])
    buy_price = float(pos['buy_price'])
    symbol = pos['symbol']
    
    sell_lot = int(sell_lot)
    sell_price = float(sell_price)
    
    if sell_lot <= 0:
        conn.close()
        raise ValueError("Satılacak lot adedi 0'dan büyük olmalıdır.")
        
    if sell_lot > current_lot:
        conn.close()
        raise ValueError(f"Portföyde sadece {current_lot} lot var, {sell_lot} lot satılamaz.")
        
    realized_pnl = (sell_price - buy_price) * sell_lot
    realized_pnl_pct = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0
    
    # 1. Transactions tablosuna ekle
    cursor.execute('''
        INSERT INTO transactions (position_id, symbol, lot, buy_price, sell_price, realized_pnl, realized_pnl_pct, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (position_id, symbol, sell_lot, buy_price, sell_price, round(realized_pnl, 2), round(realized_pnl_pct, 2), notes))
    
    transaction_id = cursor.lastrowid
    
    # 2. Portföyü güncelle veya sil
    if sell_lot == current_lot:
        cursor.execute("DELETE FROM portfolio WHERE id = ?", (position_id,))
    else:
        new_lot = current_lot - sell_lot
        cursor.execute("UPDATE portfolio SET lot = ? WHERE id = ?", (new_lot, position_id))
        
    conn.commit()
    conn.close()
    
    return {
        "transaction_id": transaction_id,
        "symbol": symbol,
        "sell_lot": sell_lot,
        "remaining_lot": current_lot - sell_lot,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "realized_pnl": round(realized_pnl, 2),
        "realized_pnl_pct": round(realized_pnl_pct, 2)
    }

def get_transactions(limit=100, year_month=None):
    """
    Gerçekleşen satış işlemlerini listeler.
    year_month formatı: 'YYYY-MM' (örn: '2026-09')
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if year_month:
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE strftime('%Y-%m', sell_date) = ?
            ORDER BY sell_date DESC, id DESC
            LIMIT ?
        ''', (year_month, limit))
    else:
        cursor.execute('''
            SELECT * FROM transactions 
            ORDER BY sell_date DESC, id DESC
            LIMIT ?
        ''', (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_transaction(transaction_id):
    """
    Satış kaydını siler.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()

def get_monthly_target_stats(year_month=None):
    """
    Belirli bir ayın gerçekleşen net kâr/zararını ve kullanıcı hedefini döner.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if not year_month:
        cursor.execute("SELECT strftime('%Y-%m', 'now')")
        year_month = cursor.fetchone()[0]
        
    cursor.execute('''
        SELECT 
            COALESCE(SUM(realized_pnl), 0) as total_pnl,
            COUNT(id) as total_trades,
            COALESCE(SUM(CASE WHEN realized_pnl > 0 THEN realized_pnl ELSE 0 END), 0) as profit_sum,
            COALESCE(SUM(CASE WHEN realized_pnl < 0 THEN realized_pnl ELSE 0 END), 0) as loss_sum
        FROM transactions
        WHERE strftime('%Y-%m', sell_date) = ?
    ''', (year_month,))
    
    row = cursor.fetchone()
    total_pnl = float(row[0]) if row else 0.0
    total_trades = int(row[1]) if row else 0
    profit_sum = float(row[2]) if row else 0.0
    loss_sum = float(row[3]) if row else 0.0
    
    # Kullanıcı aylık hedefi
    cursor.execute("SELECT value FROM settings WHERE key = 'monthly_target_tl'")
    target_row = cursor.fetchone()
    monthly_target = float(target_row[0]) if target_row and target_row[0] else 0.0
    
    conn.close()
    
    progress_pct = 0.0
    if monthly_target > 0:
        progress_pct = round((total_pnl / monthly_target) * 100, 2)
        
    remaining_tl = max(0.0, monthly_target - total_pnl)
    
    return {
        "year_month": year_month,
        "monthly_target": round(monthly_target, 2),
        "realized_pnl": round(total_pnl, 2),
        "progress_pct": progress_pct,
        "remaining_tl": round(remaining_tl, 2),
        "total_trades": total_trades,
        "profit_sum": round(profit_sum, 2),
        "loss_sum": round(loss_sum, 2)
    }

# ==================== PRICE ALERT OPERATIONS ====================

def add_alert(symbol, reference_price, target_percentage, direction=None, notes=None):
    """
    Kullanıcı tanımlı oran/fiyat bazlı alarm ekler.
    Örn: THYAO %5 artarsa (target_percentage = +5.0)
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    reference_price = float(reference_price)
    target_percentage = float(target_percentage)
    
    if not direction:
        direction = 'UP' if target_percentage >= 0 else 'DOWN'
        
    target_price = reference_price * (1 + target_percentage / 100)
    
    cursor.execute('''
        INSERT INTO alerts (symbol, reference_price, target_percentage, target_price, direction, status, notes)
        VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?)
    ''', (symbol, round(reference_price, 2), round(target_percentage, 2), round(target_price, 2), direction, notes))
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        "id": alert_id,
        "symbol": symbol,
        "reference_price": round(reference_price, 2),
        "target_percentage": round(target_percentage, 2),
        "target_price": round(target_price, 2),
        "direction": direction,
        "status": "ACTIVE",
        "notes": notes
    }

def get_active_alerts():
    """
    Kontrol edilmeyi bekleyen aktif alarmları döner.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts WHERE status = 'ACTIVE' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_alerts(limit=100):
    """
    Tüm alarmları (aktif ve tetiklenenler) döner.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM alerts 
        ORDER BY 
            CASE WHEN status = 'ACTIVE' THEN 0 ELSE 1 END,
            created_at DESC 
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def mark_alert_triggered(alert_id, triggered_price):
    """
    Alarm tetiklendiğinde durumunu günceller.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE alerts
        SET status = 'TRIGGERED', triggered_at = CURRENT_TIMESTAMP, triggered_price = ?
        WHERE id = ?
    ''', (triggered_price, alert_id))
    conn.commit()
    conn.close()

def delete_alert(alert_id):
    """
    Alarmı siler veya iptal eder.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

# ==================== SIGNAL HISTORY OPERATIONS ====================

def save_signals(signals_list):
    """
    Tarama sonucu üretilen sinyalleri signal_history tablosuna kaydeder.
    signals_list: list of dicts (symbol, type, name, timeframe_key, timeframe_label, price_at_signal, target_return, risk_level, rsi, message)
    """
    if not signals_list:
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    for sig in signals_list:
        symbol = sig.get('symbol', '').replace('.IS', '')
        cursor.execute('''
            INSERT INTO signal_history (
                symbol, signal_type, signal_name, timeframe_key, 
                timeframe_label, price_at_signal, target_return, 
                risk_level, rsi, message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol,
            sig.get('type', ''),
            sig.get('name', ''),
            sig.get('timeframe_key', 'SHORT'),
            sig.get('timeframe_label', 'Kısa Vade'),
            sig.get('price_at_signal', 0.0),
            sig.get('target_return', ''),
            sig.get('risk_level', 'Orta'),
            sig.get('rsi'),
            sig.get('message', '')
        ))
        
    conn.commit()
    conn.close()

def get_signals(timeframe_key=None, limit=100):
    """
    Kaydedilmiş sinyal geçmişini getirir.
    timeframe_key: 'SHORT', 'MEDIUM', 'LONG' veya None (tümü)
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if timeframe_key and timeframe_key.upper() != 'ALL':
        cursor.execute('''
            SELECT * FROM signal_history
            WHERE UPPER(timeframe_key) = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        ''', (timeframe_key.upper(), limit))
    else:
        cursor.execute('''
            SELECT * FROM signal_history
            ORDER BY created_at DESC, id DESC
            LIMIT ?
        ''', (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def clear_signal_history():
    """
    Tüm sinyal geçmişini temizler.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM signal_history")
    conn.commit()
    conn.close()

# Initialize db when this file is imported
init_db()

