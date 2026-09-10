from flask import Flask, render_template, jsonify, request
from database import (
    get_all_stock_data, init_db, get_tracked_stocks, add_tracked_stock, 
    remove_tracked_stock, get_portfolio_positions, add_portfolio_position, 
    delete_portfolio_position, update_portfolio_position,
    record_sale, get_transactions, delete_transaction, get_monthly_target_stats,
    get_setting, set_setting, add_alert, get_all_alerts, get_active_alerts, delete_alert,
    save_signals, get_signals, clear_signal_history,
    save_backtest_results, get_backtest_results, get_signal_backtest_map
)
from analyzer import analyze_stock, run_analysis, BIST_SYMBOLS
from backtester import run_full_backtest, get_signal_stats
from sentiment import analyze_sentiment
import os
import json
import yfinance as yf

app = Flask(__name__)

# Veritabanını hazırla
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/portfolio')
def portfolio():
    return render_template('portfolio.html')

@app.route('/hisse-analiz')
def hisse_analiz():
    return render_template('detail.html')

@app.route('/takip')
def takip_listesi():
    return render_template('tracked.html')

@app.route('/api/dashboard/summary')
def api_dashboard_summary():
    try:
        # 1. Portföy verileri
        raw_positions = get_portfolio_positions()
        portfolio_positions = []
        total_cost = 0.0
        total_value = 0.0
        
        if raw_positions:
            symbols = list(set([p['symbol'] for p in raw_positions]))
            price_map = {}
            for sym in symbols:
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period="5d")
                    if not hist.empty:
                        price_map[sym] = float(hist.iloc[-1]['Close'])
                    else:
                        price_map[sym] = None
                except Exception:
                    price_map[sym] = None

            for p in raw_positions:
                sym = p['symbol']
                lot = int(p['lot'])
                buy_price = float(p['buy_price'])
                cur_price = price_map.get(sym) or buy_price
                cost = lot * buy_price
                val = lot * cur_price
                pnl = val - cost
                pnl_pct = ((cur_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0
                
                total_cost += cost
                total_value += val
                portfolio_positions.append({
                    "id": p['id'],
                    "symbol": sym.replace('.IS', ''),
                    "lot": lot,
                    "buy_price": round(buy_price, 2),
                    "current_price": round(cur_price, 2),
                    "total_cost": round(cost, 2),
                    "current_value": round(val, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2)
                })

        total_pnl = total_value - total_cost
        total_pnl_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0

        portfolio_summary = {
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "position_count": len(portfolio_positions),
            "positions": portfolio_positions
        }

        # 2. Aylık Hedef & Gerçekleşen K/Z
        target_stats = get_monthly_target_stats()

        # 3. Aktif Alarmlar
        active_alerts = get_active_alerts()
        recent_alerts = get_all_alerts(limit=5)

        # 4. En Son Sinyaller
        recent_signals = get_signals(limit=10)
        short_count = len([s for s in recent_signals if s.get('timeframe_key') == 'SHORT'])
        med_count = len([s for s in recent_signals if s.get('timeframe_key') == 'MEDIUM'])
        long_count = len([s for s in recent_signals if s.get('timeframe_key') == 'LONG'])

        # 5. Hisse Sayısı & Backtest Özeti
        stocks = get_all_stock_data()
        backtest_stats = get_backtest_results()

        return jsonify({
            "status": "success",
            "data": {
                "portfolio": portfolio_summary,
                "target": target_stats,
                "alerts": {
                    "active_count": len(active_alerts),
                    "items": recent_alerts
                },
                "signals": {
                    "total_count": len(recent_signals),
                    "short_count": short_count,
                    "med_count": med_count,
                    "long_count": long_count,
                    "items": recent_signals
                },
                "stock_count": len(stocks),
                "backtest_count": len(backtest_stats)
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/data')
def api_data():
    try:
        data = get_all_stock_data()
        # Parse signal_details JSON string if needed
        for row in data:
            sig_det = row.get('signal_details')
            if sig_det and isinstance(sig_det, str):
                try:
                    row['signal_details'] = json.loads(sig_det)
                except Exception:
                    pass
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==================== BACKTEST API ENDPOINTS ====================

@app.route('/api/backtest/stats')
def api_get_backtest_stats():
    try:
        results = get_backtest_results()
        if not results:
            return jsonify({
                "status": "not_run",
                "message": "Henüz backtest çalıştırılmadı. Lütfen /api/backtest/run çağırın.",
                "data": []
            })
        return jsonify({"status": "success", "data": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/backtest/run', methods=['POST'])
def api_run_backtest():
    try:
        data = request.json or {}
        period = data.get('period', '5y')
        symbols = data.get('symbols') or BIST_SYMBOLS
        
        # Backtest'i çalıştır
        results = run_full_backtest(symbols=symbols, period=period)
        return jsonify({
            "status": "success",
            "message": f"{len(symbols)} hisse için {period} süreli backtest başarıyla tamamlandı.",
            "data": results
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==================== SIGNALS API ENDPOINTS ====================

@app.route('/api/signals')
def api_get_signals():
    try:
        timeframe = request.args.get('timeframe')
        limit = int(request.args.get('limit', 100))
        signals = get_signals(timeframe_key=timeframe, limit=limit)
        return jsonify({"status": "success", "data": signals})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/signals/scan', methods=['POST'])
def api_trigger_scan():
    try:
        data = request.json or {}
        symbols = data.get('symbols')
        if not symbols:
            symbols = BIST_SYMBOLS[:20] # Varsayılan ilk 20 hisse veya tamamı
            
        found_signals = []
        raw_list = []
        for sym in symbols:
            res = analyze_stock(sym)
            if res:
                if res.get('signals'):
                    found_signals.extend(res['signals'])
                if res.get('raw_data'):
                    raw_list.append(res['raw_data'])
                    
        if raw_list:
            from database import save_stock_data
            save_stock_data(raw_list)
        if found_signals:
            save_signals(found_signals)
            
        return jsonify({
            "status": "success",
            "message": f"{len(symbols)} hisse tarandı. {len(found_signals)} adet doğrulanmış sinyal bulundu.",
            "scanned_count": len(symbols),
            "signals_found": len(found_signals)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/price/<symbol>')
def api_get_price(symbol):
    try:
        symbol = symbol.upper()
        if not symbol.endswith('.IS') and not '-' in symbol and not '.' in symbol:
            symbol = symbol + '.IS'
            
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="5d")
        if history.empty:
            return jsonify({"status": "error", "message": f"'{symbol}' için fiyat verisi bulunamadı."})
            
        last_price = float(history.iloc[-1]['Close'])
        return jsonify({
            "status": "success",
            "symbol": symbol,
            "price": round(last_price, 2)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/analyze/<symbol>')
def api_analyze(symbol):
    try:
        # ".IS" eklentisi yoksa ekle (Kullanıcı "THYAO" girecektir)
        symbol = symbol.upper()
        if not symbol.endswith('.IS'):
            symbol = symbol + '.IS'
            
        result = analyze_stock(symbol)
        if result:
            # Haberleri bul ve LLM (Ollama/Gemini) ile analiz et
            sentiment_result = analyze_sentiment(symbol)
            result['sentiment'] = sentiment_result
            
            return jsonify({"status": "success", "data": result})
        else:
            return jsonify({"status": "error", "message": "Veri bulunamadı. Lütfen geçerli bir hisse kodu girin."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tracked')
def api_get_tracked():
    try:
        data = get_tracked_stocks()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tracked/add', methods=['POST'])
def api_add_tracked():
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        if not symbol:
            return jsonify({"status": "error", "message": "Sembol boş olamaz."})
            
        # Check if it exists and fetch current price
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="5d")
        
        if history.empty:
            return jsonify({"status": "error", "message": f"'{symbol}' sembolü bulunamadı veya veri alınamadı. Uzantıyı (örn: BIST) doğru seçtiğinizden emin olun."})
            
        last_price = history.iloc[-1]['Close']
        add_tracked_stock(symbol, last_price)
        return jsonify({"status": "success", "message": f"{symbol} başarıyla listeye eklendi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/tracked/remove', methods=['POST'])
def api_remove_tracked():
    try:
        data = request.json
        symbol = data.get('symbol', '').upper()
        if not symbol:
            return jsonify({"status": "error", "message": "Sembol boş olamaz."})
            
        remove_tracked_stock(symbol)
        return jsonify({"status": "success", "message": f"{symbol} listeden çıkarıldı."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==================== PORTFOLIO API ENDPOINTS ====================

@app.route('/api/portfolio')
def api_get_portfolio():
    try:
        raw_positions = get_portfolio_positions()
        if not raw_positions:
            return jsonify({
                "status": "success",
                "data": {
                    "positions": [],
                    "summary": {
                        "total_cost": 0.0,
                        "total_value": 0.0,
                        "total_pnl": 0.0,
                        "total_pnl_pct": 0.0,
                        "position_count": 0,
                        "total_lots": 0
                    }
                }
            })
            
        # Unique sembollerin güncel fiyatlarını çek
        symbols = list(set([p['symbol'] for p in raw_positions]))
        price_map = {}
        
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="5d")
                if not hist.empty:
                    price_map[sym] = float(hist.iloc[-1]['Close'])
                else:
                    price_map[sym] = None
            except Exception as ex:
                print(f"Fiyat çekme hatası ({sym}): {ex}")
                price_map[sym] = None

        positions = []
        total_cost = 0.0
        total_value = 0.0
        total_lots = 0

        for p in raw_positions:
            sym = p['symbol']
            lot = int(p['lot'])
            buy_price = float(p['buy_price'])
            current_price = price_map.get(sym) or buy_price # Fallback to buy_price if unavailable
            
            cost = lot * buy_price
            val = lot * current_price
            pnl = val - cost
            pnl_pct = ((current_price - buy_price) / buy_price * 100) if buy_price > 0 else 0.0

            total_cost += cost
            total_value += val
            total_lots += lot

            positions.append({
                "id": p['id'],
                "symbol": sym,
                "lot": lot,
                "buy_price": round(buy_price, 2),
                "current_price": round(current_price, 2),
                "total_cost": round(cost, 2),
                "current_value": round(val, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "buy_date": p.get('buy_date', ''),
                "notes": p.get('notes', '')
            })

        total_pnl = total_value - total_cost
        total_pnl_pct = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0

        summary = {
            "total_cost": round(total_cost, 2),
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "position_count": len(positions),
            "total_lots": total_lots
        }

        return jsonify({
            "status": "success",
            "data": {
                "positions": positions,
                "summary": summary
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/portfolio/add', methods=['POST'])
def api_add_portfolio():
    try:
        data = request.json or {}
        symbol = str(data.get('symbol', '')).strip().upper()
        lot = data.get('lot')
        buy_price = data.get('buy_price')
        buy_date = data.get('buy_date')
        notes = data.get('notes', '')

        if not symbol:
            return jsonify({"status": "error", "message": "Hisse sembolü boş olamaz."})
        
        try:
            lot = int(lot)
            if lot <= 0:
                return jsonify({"status": "error", "message": "Lot adedi 0'dan büyük olmalıdır."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir lot adedi giriniz."})

        try:
            buy_price = float(buy_price)
            if buy_price <= 0:
                return jsonify({"status": "error", "message": "Alış fiyatı 0'dan büyük olmalıdır."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir alış fiyatı giriniz."})

        # BIST sembolü için .IS kontrolü
        if not symbol.endswith('.IS') and not '-' in symbol and not '.' in symbol:
            symbol = symbol + '.IS'

        pos_id = add_portfolio_position(symbol, lot, buy_price, buy_date=buy_date, notes=notes)
        return jsonify({
            "status": "success", 
            "message": f"{symbol} ({lot} lot) başarıyla portföye eklendi.",
            "position_id": pos_id
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/portfolio/delete', methods=['POST'])
def api_delete_portfolio():
    try:
        data = request.json or {}
        position_id = data.get('id')
        if not position_id:
            return jsonify({"status": "error", "message": "Pozisyon ID belirtilmedi."})
            
        delete_portfolio_position(position_id)
        return jsonify({"status": "success", "message": "Pozisyon başarıyla silindi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/portfolio/update', methods=['POST'])
def api_update_portfolio():
    try:
        data = request.json or {}
        position_id = data.get('id')
        lot = data.get('lot')
        buy_price = data.get('buy_price')
        notes = data.get('notes', '')

        if not position_id:
            return jsonify({"status": "error", "message": "Pozisyon ID belirtilmedi."})
        
        try:
            lot = int(lot)
            if lot <= 0:
                return jsonify({"status": "error", "message": "Lot adedi 0'dan büyük olmalıdır."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir lot adedi giriniz."})

        try:
            buy_price = float(buy_price)
            if buy_price <= 0:
                return jsonify({"status": "error", "message": "Alış fiyatı 0'dan büyük olmalıdır."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir alış fiyatı giriniz."})

        update_portfolio_position(position_id, lot, buy_price, notes=notes)
        return jsonify({"status": "success", "message": "Pozisyon başarıyla güncellendi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/portfolio/sell', methods=['POST'])
def api_sell_portfolio():
    try:
        data = request.json or {}
        position_id = data.get('position_id')
        sell_lot = data.get('lot')
        sell_price = data.get('sell_price')
        notes = data.get('notes', '')

        if not position_id:
            return jsonify({"status": "error", "message": "Pozisyon ID belirtilmedi."})

        try:
            sell_lot = int(sell_lot)
            if sell_lot <= 0:
                return jsonify({"status": "error", "message": "Satılacak lot adedi 0'dan büyük olmalıdır."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir lot adedi giriniz."})

        try:
            sell_price = float(sell_price)
            if sell_price <= 0:
                return jsonify({"status": "error", "message": "Satış fiyatı 0'dan büyük olmalıdır."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir satış fiyatı giriniz."})

        res = record_sale(position_id, sell_lot, sell_price, notes=notes)
        pnl_str = f"+₺{res['realized_pnl']:,.2f}" if res['realized_pnl'] >= 0 else f"-₺{abs(res['realized_pnl']):,.2f}"
        return jsonify({
            "status": "success",
            "message": f"{res['symbol']} ({res['sell_lot']} lot) satışı gerçekleştirildi. Net K/Z: {pnl_str}",
            "data": res
        })
    except ValueError as ve:
        return jsonify({"status": "error", "message": str(ve)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==================== TARGET & TRANSACTION API ENDPOINTS ====================

@app.route('/api/target/stats')
def api_get_target_stats():
    try:
        year_month = request.args.get('year_month')
        stats = get_monthly_target_stats(year_month)
        return jsonify({"status": "success", "data": stats})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/target/set', methods=['POST'])
def api_set_target():
    try:
        data = request.json or {}
        target_tl = data.get('target_tl')
        
        try:
            target_tl = float(target_tl)
            if target_tl < 0:
                return jsonify({"status": "error", "message": "Aylık hedef negatif olamaz."})
        except (ValueError, TypeError):
            return jsonify({"status": "error", "message": "Geçerli bir hedef tutarı giriniz."})

        set_setting('monthly_target_tl', target_tl)
        return jsonify({
            "status": "success", 
            "message": f"Aylık kazanç hedefiniz ₺{target_tl:,.2f} olarak güncellendi.",
            "target": target_tl
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/transactions')
def api_get_transactions():
    try:
        limit = int(request.args.get('limit', 100))
        year_month = request.args.get('year_month')
        txs = get_transactions(limit=limit, year_month=year_month)
        return jsonify({"status": "success", "data": txs})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/transactions/delete', methods=['POST'])
def api_delete_transaction():
    try:
        data = request.json or {}
        transaction_id = data.get('id')
        if not transaction_id:
            return jsonify({"status": "error", "message": "İşlem ID belirtilmedi."})
            
        delete_transaction(transaction_id)
        return jsonify({"status": "success", "message": "İşlem kaydı silindi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

# ==================== ALERT API ENDPOINTS ====================

@app.route('/api/alerts')
def api_get_alerts():
    try:
        limit = int(request.args.get('limit', 100))
        alerts = get_all_alerts(limit=limit)
        return jsonify({"status": "success", "data": alerts})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/alerts/add', methods=['POST'])
def api_add_alert():
    try:
        data = request.json or {}
        symbol = str(data.get('symbol', '')).strip().upper()
        reference_price = data.get('reference_price')
        target_percentage = data.get('target_percentage')
        target_price = data.get('target_price')
        direction = data.get('direction')
        notes = data.get('notes', '')

        if not symbol:
            return jsonify({"status": "error", "message": "Hisse sembolü boş olamaz."})

        if not symbol.endswith('.IS') and not '-' in symbol and not '.' in symbol:
            symbol = symbol + '.IS'

        # Referans fiyat girilmemişse güncel piyasa fiyatını çek
        if reference_price is None or reference_price == '':
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                return jsonify({"status": "error", "message": f"'{symbol}' için güncel referans fiyatı alınamadı."})
            reference_price = float(hist.iloc[-1]['Close'])
        else:
            reference_price = float(reference_price)

        if reference_price <= 0:
            return jsonify({"status": "error", "message": "Referans fiyat 0'dan büyük olmalıdır."})

        # Hedef oran mı yoksa hedef fiyat mı girildi?
        if target_percentage is not None and target_percentage != '':
            target_percentage = float(target_percentage)
            if not direction:
                direction = 'UP' if target_percentage >= 0 else 'DOWN'
        elif target_price is not None and target_price != '':
            target_price = float(target_price)
            if target_price <= 0:
                return jsonify({"status": "error", "message": "Hedef fiyat 0'dan büyük olmalıdır."})
            target_percentage = ((target_price - reference_price) / reference_price) * 100
            direction = 'UP' if target_price >= reference_price else 'DOWN'
        else:
            return jsonify({"status": "error", "message": "Lütfen bir hedef yüzde oranı (%±) veya hedef fiyat giriniz."})

        alert = add_alert(symbol, reference_price, target_percentage, direction=direction, notes=notes)
        dir_text = "artış" if direction == 'UP' else "düşüş"
        return jsonify({
            "status": "success",
            "message": f"{symbol} için %{target_percentage:+.2f} ({alert['target_price']:.2f} ₺) {dir_text} alarmı kuruldu.",
            "data": alert
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/alerts/delete', methods=['POST'])
def api_delete_alert():
    try:
        data = request.json or {}
        alert_id = data.get('id')
        if not alert_id:
            return jsonify({"status": "error", "message": "Alarm ID belirtilmedi."})
            
        delete_alert(alert_id)
        return jsonify({"status": "success", "message": "Alarm başarıyla silindi/iptal edildi."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Flask sunucusunu başlat
    app.run(debug=True, host='0.0.0.0', port=5000)

