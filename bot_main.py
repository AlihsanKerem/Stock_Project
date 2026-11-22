import os
import time
import schedule
import threading
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

from analyzer import run_analysis
from sentiment import analyze_sentiment
from agent_engine import stock_agent
from prediction_tracker import (
    is_bist_market_open, is_weekday,
    run_funnel_committee_digest, evaluate_open_predictions
)
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

    # Sinyalleri analyzer üzerinden al (tüm liste veritabanına ve Web Dashboard'a kaydolur)
    signals = run_analysis()
    
    if not signals:
        print("Bugün için herhangi bir sinyal bulunamadı.")
        return

    print(f"Toplam {len(signals)} adet sinyal bulundu. Akıllı Huni & Yatırım Komitesi çalıştırılıyor...")
    
    # Uzun ham listeler yerine sadece en güçlü 5 adayı Komite + Time Machine'den geçirip kısa özet at
    digest = run_funnel_committee_digest(signals, max_candidates=5)
    digest_msg = digest.get("digest_message")
    if digest_msg:
        asyncio.run(send_telegram_message(digest_msg))

def check_tracked_stocks_job():
    if not is_bist_market_open():
        print("⏸️ BIST seans saatleri dışında (veya hafta sonu), takip listesi kontrolü atlandı.")
        return

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
    if not is_bist_market_open():
        print("⏸️ BIST seans saatleri dışında (veya hafta sonu), alarm kontrolü atlandı.")
        return

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

def scheduled_backtest_job():
    """
    Haftalık periyodik backtest güncelleme görevi.
    Pazar akşamları çalışarak son 5 yıllık veriyi ve sinyal istatistiklerini günceller.
    """
    print("\n" + "="*50)
    print("Haftalık Otomatik Backtest Güncellemesi Başlıyor...")
    print("="*50)
    try:
        from backtester import run_full_backtest
        results = run_full_backtest(period="5y")
        print(f"Haftalık Backtest Tamamlandı: {len(results)} kural güncellendi.")
    except Exception as e:
        print(f"Haftalık backtest çalıştırılırken hata: {e}")

# ==========================================
# 🤖 Telegram İnteraktif AI Ajan İşleyicileri
# ==========================================

async def telegram_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı /start yazdığında karşılama mesajı gönderir."""
    welcome_msg = (
        "🤖 <b>BIST Otonom Portföy ve Risk Asistanına Hoş Geldiniz!</b>\n\n"
        "Ben portföyünüzü inceleyebilir, hisseleriniz için teknik göstergeleri (RSI, ATR stop-loss) "
        "hesaplayabilir, 5 yıllık backtest başarılarını sorgulayabilir ve güncel KAP haberlerini yorumlayabilirim.\n\n"
        "<b>Kullanabileceğiniz Komutlar:</b>\n"
        "• /briefing - Anlık Yönetici Strateji Bülteni oluşturur\n"
        "• /portfolio - Açık portföy durumunuzu ve K/Z özetler\n"
        "• /signals - Bugün tespit edilen güncel sinyalleri listeler\n\n"
        "<i>Veya bana doğrudan soru yazabilirsiniz: Örn: 'THYAO teknik durumu nasıl?', 'Portföyümdeki riskler neler?'</i>"
    )
    await update.message.reply_text(welcome_msg, parse_mode="HTML")

async def telegram_briefing_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı /briefing yazdığında tek tıkla bülten üretir."""
    await update.message.reply_text("⏳ <i>Yönetici strateji bülteni hazırlanıyor, lütfen bekleyin...</i>", parse_mode="HTML")
    try:
        briefing = stock_agent.generate_executive_briefing()
        resp = briefing.get("response", "Bülten hazırlanamadı.")
        await update.message.reply_text(resp)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Bülten oluşturulurken hata: {e}")

async def telegram_portfolio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı /portfolio yazdığında portföy analizi ister."""
    await update.message.reply_text("⏳ <i>Portföyünüz denetleniyor...</i>", parse_mode="HTML")
    try:
        result = stock_agent.ask("Portföyümün güncel kâr/zararını ve açık hisselerimi detaylı özetle.", session_id=f"tg_{update.effective_chat.id}")
        await update.message.reply_text(result.get("response", "Portföy bilgisi alınamadı."))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Hata: {e}")

async def telegram_signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı /signals yazdığında güncel sinyalleri özetler."""
    await update.message.reply_text("⏳ <i>Güncel sinyaller taranıyor...</i>", parse_mode="HTML")
    try:
        result = stock_agent.ask("Bugün gelen en güncel AL ve SAT sinyallerini ve bunların backtest güvenilirliklerini listele.", session_id=f"tg_{update.effective_chat.id}")
        await update.message.reply_text(result.get("response", "Sinyal bilgisi alınamadı."))
    except Exception as e:
        await update.message.reply_text(f"⚠️ Hata: {e}")

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının yazdığı serbest metinleri AI Ajanına iletir."""
    if not update.message or not update.message.text:
        return
        
    user_text = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Telegram "yazıyor..." bildirimi
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    try:
        result = stock_agent.ask(user_text, session_id=f"tg_{chat_id}")
        response = result.get("response", "Yanıt alınamadı.")
        tools = result.get("tools_used", [])

        tool_info = ""
        if tools:
            tool_info = f"<i>[⚡ Kullanılan Araçlar: {', '.join(tools)}]</i>\n\n"

        full_msg = f"{tool_info}{response}"
        # Telegram 4096 karakter sınırına karşı parçalama
        if len(full_msg) > 4000:
            for chunk in [full_msg[i:i+4000] for i in range(0, len(full_msg), 4000)]:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(full_msg)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ajan hatası: {e}")

def check_predictions_job():
    """
    Hafta içi günde 3 kez (Sabah 10:30, Öğle 14:00, Akşam 18:15)
    açık AI tahminlerini canlı piyasa fiyatıyla karşılaştırıp Telegram'a karne gönderir.
    """
    if not is_weekday():
        return

    print("\n" + "="*50)
    print("🎯 AI Tahmin Doğrulama Kontrolü Başlıyor...")
    print("="*50)
    try:
        res = evaluate_open_predictions()
        report_msg = res.get("report_message")
        if report_msg:
            asyncio.run(send_telegram_message(report_msg))
        else:
            print("Kontrol edilecek açık AI tahmini bulunmuyor.")
    except Exception as pe:
        print(f"Tahmin doğrulama hatası: {pe}")

def run_strategy_lab_job():
    """
    Hafta içi 18:35'te 9 Strateji Laboratuvarı portföyünü günceller,
    döngüsünü tamamlayanlarda Öz-Denetim (Self-Audit) çalıştırıp Telegram'a rapor atar.
    """
    if not is_weekday():
        return

    print("\n" + "="*50)
    print("🧪 Strateji Laboratuvarı Günlük Döngüsü Başlıyor...")
    print("="*50)
    try:
        from strategy_lab import run_lab_daily_cycle
        res = run_lab_daily_cycle()
        tg_msg = res.get("telegram_message")
        if tg_msg:
            asyncio.run(send_telegram_message(tg_msg))
    except Exception as le:
        print(f"Strateji Lab döngü hatası: {le}")

def run_scheduler_thread():
    """Zamanlanmış görevleri arka plan iş parçacığında çalıştırır."""
    while True:
        try:
            schedule.run_pending()
        except Exception as se:
            print(f"Schedule döngü hatası: {se}")
        time.sleep(30)

def main():
    print("Sistem başlatıldı. Telegram ve API ayarlarınızı .env dosyasından kontrol ediniz.")
    print("Günlük tarama hafta içi her gün saat 18:30'da çalışacak şekilde ayarlandı.")
    
    # Hafta içi her gün 18:30'da çalıştır (Borsa kapandıktan sonra)
    schedule.every().monday.at("18:30").do(job)
    schedule.every().tuesday.at("18:30").do(job)
    schedule.every().wednesday.at("18:30").do(job)
    schedule.every().thursday.at("18:30").do(job)
    schedule.every().friday.at("18:30").do(job)

    # Gün içi 3 kez AI tahmin doğrulama kontrolü (Sabah, Öğle, Akşam)
    schedule.every().day.at("10:30").do(check_predictions_job)
    schedule.every().day.at("14:00").do(check_predictions_job)
    schedule.every().day.at("18:15").do(check_predictions_job)

    # Hafta içi 18:35'te Strateji Laboratuvarı (9 portföy + Öz-Denetim)
    schedule.every().monday.at("18:35").do(run_strategy_lab_job)
    schedule.every().tuesday.at("18:35").do(run_strategy_lab_job)
    schedule.every().wednesday.at("18:35").do(run_strategy_lab_job)
    schedule.every().thursday.at("18:35").do(run_strategy_lab_job)
    schedule.every().friday.at("18:35").do(run_strategy_lab_job)
    
    # Her 30 dakikada bir takip listesini kontrol et
    schedule.every(30).minutes.do(check_tracked_stocks_job)

    # Her 10 dakikada bir kullanıcı alarmlarını kontrol et
    schedule.every(10).minutes.do(check_alerts_job)

    # Her Pazar akşamı 22:00'de haftalık backtest çalıştır (Yeni hafta öncesi)
    schedule.every().sunday.at("22:00").do(scheduled_backtest_job)
    
    # Arka plan zamanlayıcı thread'ini başlat
    scheduler_thread = threading.Thread(target=run_scheduler_thread, daemon=True)
    scheduler_thread.start()
    print("⏰ Arka plan zamanlayıcı iş parçacığı (Scheduler) başlatıldı.")

    # Telegram Bot Polling (Eğer Token geçerliyse)
    is_token_valid = (
        TELEGRAM_BOT_TOKEN 
        and TELEGRAM_BOT_TOKEN not in ["your_telegram_bot_token_here", ""]
    )

    if is_token_valid:
        try:
            print("🤖 Telegram İnteraktif Bot dinleyicisi başlatılıyor...")
            app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Komut işleyicileri
            app.add_handler(CommandHandler("start", telegram_start_cmd))
            app.add_handler(CommandHandler("help", telegram_start_cmd))
            app.add_handler(CommandHandler("briefing", telegram_briefing_cmd))
            app.add_handler(CommandHandler("portfolio", telegram_portfolio_cmd))
            app.add_handler(CommandHandler("signals", telegram_signals_cmd))

            # Doğal dil / serbest mesaj işleyicisi
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_message_handler))

            print("✅ Telegram Botu aktif! Gelen mesajları yanıtlamaya hazır.")
            app.run_polling()
        except Exception as te:
            print(f"⚠️ Telegram polling başlatılamadı ({te}). Zamanlayıcı çalışmaya devam ediyor...")
            while True:
                time.sleep(60)
    else:
        print("ℹ️ Telegram Token ayarlanmadığı için interaktif dinleme devre dışı. Zamanlayıcı aktif.")
        while True:
            time.sleep(60)

if __name__ == "__main__":
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        
    main()
