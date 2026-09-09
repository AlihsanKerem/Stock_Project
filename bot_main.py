import os
import time
import schedule
from dotenv import load_dotenv
from telegram import Bot
import asyncio

from analyzer import run_analysis
from sentiment import analyze_sentiment
import yfinance as yf
from database import get_tracked_stocks, update_tracked_stock_price, get_active_alerts, mark_alert_triggered

# .env dosyasından ayarları yükle
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_message(message):
    """
    Telegram üzerinden mesaj gönderir.
    """
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        print("HATA: Telegram Bot Token ayarlanmamış.")
        return
        
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == "your_telegram_chat_id_here":
        print("HATA: Telegram Chat ID ayarlanmamış.")
        return

    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
        print("Mesaj Telegram'a gönderildi!")
    except Exception as e:
        print(f"Telegram'a mesaj gönderilirken hata: {e}")

def job():
    """
    Zamanlanmış görevin çalıştıracağı ana fonksiyon.
    """
    print("\n" + "="*50)
    print("Günlük Hisse Tarama İşlemi Başlıyor...")
    print("="*50)
    
    # 0. Veritabanını otomatik yedekle
    try:
        from backup_db import create_backup
        create_backup()
    except Exception as be:
        print(f"Otomatik yedekleme uyarısı: {be}")

    # Sinyalleri analyzer üzerinden al
    signals = run_analysis()
    
    if not signals:
        print("Bugün için herhangi bir sinyal bulunamadı.")
        return

    print(f"Toplam {len(signals)} adet sinyal bulundu. Haber analizleri yapılıyor...")
    
    final_messages = []
    
    for signal in signals:
        symbol = signal['symbol']
        msg = signal['message']
        
        # Haber duygu analizi (Sentiment Analysis)
        sentiment_result = analyze_sentiment(symbol)
        
        if sentiment_result and sentiment_result.get('status') not in ['error', 'neutral']:
            status = sentiment_result['status']
            title = sentiment_result.get('title', '')
            link = sentiment_result.get('link', '')
            
            # Duruma göre emoji
            emoji = "🟢" if status == "OLUMLU" else "🔴" if status == "OLUMSUZ" else "⚪"
            
            sentiment_msg = f"\n{emoji} <b>Haber Analizi:</b> {status}\n<i>{title}</i>\n<a href='{link}'>Habere Git</a>"
            msg += sentiment_msg
        
        final_messages.append(msg)
        
    # Telegram'ın 4096 karakter sınırını aşmamak için mesajları bölerek gönderelim
    MAX_LENGTH = 3500
    messages_to_send = []
    current_message = "<b>📈 GÜNLÜK HİSSE SİNYALLERİ</b>\n\n"
    
    for msg in final_messages:
        addition = f"• {msg}\n\n"
        if len(current_message) + len(addition) > MAX_LENGTH:
            messages_to_send.append(current_message)
            current_message = "<b>📈 SİNYALLER (Devamı)</b>\n\n" + addition
        else:
            current_message += addition
            
    if current_message:
        messages_to_send.append(current_message)
        
    # Asenkron fonksiyonu çalıştır
    for m in messages_to_send:
        asyncio.run(send_telegram_message(m))

def check_tracked_stocks_job():
    print("\n" + "="*50)
    print("Takip Edilen Hisseler Kontrol Ediliyor...")
    print("="*50)
    
    tracked = get_tracked_stocks()
    if not tracked:
        print("Takip edilen hisse bulunamadı.")
        return
        
    messages = []
    
    for stock in tracked:
        symbol = stock['symbol']
        last_price = stock['last_price']
        
        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period="5d")
            
            if history.empty:
                continue
                
            current_price = history.iloc[-1]['Close']
            
            if last_price is not None and current_price != last_price:
                diff = current_price - last_price
                pct_change = (diff / last_price) * 100
                
                # Sadece anlamlı değişimler için mesaj at (%0.1 den büyük)
                if abs(pct_change) > 0.1:
                    emoji = "📈" if diff > 0 else "📉"
                    sign = "+" if diff > 0 else ""
                    messages.append(f"<b>{symbol}</b>: {current_price:.4f} ({sign}{pct_change:.2f}%) {emoji}")
                    
            # Fiyatı güncelle
            if last_price != current_price:
                update_tracked_stock_price(symbol, current_price)
                
        except Exception as e:
            print(f"{symbol} kontrol edilirken hata: {e}")
            
    if messages:
        msg_body = "\n".join(messages)
        full_msg = f"<b>👀 TAKİP LİSTESİ GÜNCELLEMESİ</b>\n\n{msg_body}"
        asyncio.run(send_telegram_message(full_msg))
    else:
        print("Fiyatlarda anlamlı bir değişim olmadı (veya borsa kapalı).")

def check_alerts_job():
    """
    Aktif kullanıcı fiyat alarmlarını kontrol eder ve tetiklenenleri Telegram'a iletir.
    """
    print("\n" + "="*50)
    print("Aktif Fiyat Alarmları Kontrol Ediliyor...")
    print("="*50)

    alerts = get_active_alerts()
    if not alerts:
        print("Aktif fiyat alarmı bulunmuyor.")
        return

    print(f"Toplam {len(alerts)} aktif alarm denetleniyor...")

    for alert in alerts:
        alert_id = alert['id']
        symbol = alert['symbol']
        ref_price = alert['reference_price']
        target_pct = alert['target_percentage']
        target_price = alert['target_price']
        direction = alert['direction']
        notes = alert.get('notes', '')

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                continue

            current_price = float(hist.iloc[-1]['Close'])
            actual_pct = ((current_price - ref_price) / ref_price) * 100

            triggered = False
            if direction == 'UP' and current_price >= target_price:
                triggered = True
            elif direction == 'DOWN' and current_price <= target_price:
                triggered = True

            if triggered:
                # 1. DB'de tetiklendi olarak işaretle (Spam'i önler)
                mark_alert_triggered(alert_id, current_price)

                # 2. Telegram Bildirimi Oluştur
                emoji = "🚀 📈" if direction == 'UP' else "⚠️ 📉"
                dir_label = "YÜKSELİŞ" if direction == 'UP' else "DÜŞÜŞ"
                sign = "+" if actual_pct >= 0 else ""

                msg = (
                    f"<b>🚨 FİYAT ALARMI TETİKLENDİ!</b> {emoji}\n\n"
                    f"<b>Hisse:</b> {symbol}\n"
                    f"<b>Alarm Türü:</b> %{target_pct:+.2f} {dir_label}\n"
                    f"<b>Referans Fiyat:</b> ₺{ref_price:,.2f}\n"
                    f"<b>Hedef Fiyat:</b> ₺{target_price:,.2f}\n"
                    f"<b>Güncel Fiyat:</b> ₺{current_price:,.2f} ({sign}%{actual_pct:.2f})\n"
                )
                if notes:
                    msg += f"<b>Notunuz:</b> <i>{notes}</i>\n"

                print(f"ALARM TETİKLENDİ: {symbol} -> ₺{current_price}")
                asyncio.run(send_telegram_message(msg))

        except Exception as e:
            print(f"Alarm kontrol hatası ({symbol}): {e}")

def main():
    print("Sistem başlatıldı. Telegram ve API ayarlarınızı .env dosyasından kontrol ediniz.")
    print("Günlük tarama her gün saat 18:30'da çalışacak şekilde ayarlandı.")
    
    # Sistemin çalıştığını teyit etmek için açılışta bir kere test atıyoruz
    job()
    
    # Hafta içi her gün 18:30'da çalıştır (Borsa kapandıktan sonra)
    schedule.every().monday.at("18:30").do(job)
    schedule.every().tuesday.at("18:30").do(job)
    schedule.every().wednesday.at("18:30").do(job)
    schedule.every().thursday.at("18:30").do(job)
    schedule.every().friday.at("18:30").do(job)
    
    # Her 30 dakikada bir takip listesini kontrol et
    schedule.every(30).minutes.do(check_tracked_stocks_job)

    # Her 10 dakikada bir kullanıcı alarmlarını kontrol et
    schedule.every(10).minutes.do(check_alerts_job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        
    main()
