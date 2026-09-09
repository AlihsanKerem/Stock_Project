import os
import sys
import io
import time
import subprocess

# Windows console encoding fix
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    clear_screen()
    print("\033[96m" + "=" * 60)
    print("      🚀 BIST ALGO-TRADE & EXECUTIVE DASHBOARD 🚀      ")
    print("=" * 60 + "\033[0m")
    print("\n\033[92m[1]\033[0m ⚡  \033[1mTÜM SİSTEMİ BAŞLAT\033[0m (Web Dashboard + Telegram Bot & Alarmlar)")
    print("\033[93m[2]\033[0m 🌐  Sadece Web Arayüzünü Başlat (Dashboard - Port 5000)")
    print("\033[93m[3]\033[0m 🤖  Sadece Telegram Bot & Alarm İzleyiciyi Başlat")
    print("\033[93m[4]\033[0m 📊  Hızlı BIST100 Taraması Yap (Veritabanını Güncelle)")
    print("\033[93m[5]\033[0m 💾  Veritabanını Yedekle (backups/ klasörüne kopyalar)")
    print("\033[93m[6]\033[0m 🛠️  Sıfırdan Kurulum (pip install -r requirements.txt)")
    print("\033[91m[0]\033[0m ❌  Çıkış\n")
    print("\033[96m" + "=" * 60 + "\033[0m")

def run_all():
    print("\n" + "=" * 60)
    print("🚀 Tüm sistem servisleri başlatılıyor...")
    print("💡 Web Dashboard: http://127.0.0.1:5000")
    print("💡 Telegram Bot & Alarm Takipçisi devrede...")
    print("⚠️  Tüm servisleri durdurmak için Ctrl + C tuşlarına basın.")
    print("=" * 60 + "\n")

    p_web = None
    p_bot = None
    try:
        p_web = subprocess.Popen([sys.executable, "app.py"])
        p_bot = subprocess.Popen([sys.executable, "bot_main.py"])
        
        while True:
            time.sleep(1)
            if p_web.poll() is not None or p_bot.poll() is not None:
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Servisler kapatılıyor...")
    finally:
        if p_web and p_web.poll() is None:
            p_web.terminate()
        if p_bot and p_bot.poll() is None:
            p_bot.terminate()
        print("✅ Tüm servisler güvenle durduruldu.")
        time.sleep(2)

def main():
    while True:
        print_menu()
        choice = input("\n👉 Lütfen bir işlem seçin (0-6): ").strip()

        if choice == '1':
            run_all()
            
        elif choice == '2':
            print("\n🌐 Web Dashboard başlatılıyor...")
            print("💡 Lütfen tarayıcınızda açın: http://127.0.0.1:5000")
            print("Kapatmak için Ctrl+C yapabilirsiniz.\n")
            try:
                os.system(f'"{sys.executable}" app.py')
            except KeyboardInterrupt:
                pass
            
        elif choice == '3':
            print("\n🤖 Telegram botu ve alarm izleyici başlatılıyor...")
            print("Kapatmak için Ctrl+C yapabilirsiniz.\n")
            try:
                os.system(f'"{sys.executable}" bot_main.py')
            except KeyboardInterrupt:
                pass
            
        elif choice == '4':
            print("\n📊 BIST100 Taraması Başlatılıyor...")
            os.system(f'"{sys.executable}" analyzer.py')
            input("\n✅ Tarama tamamlandı! Ana menüye dönmek için Enter'a basın...")
            
        elif choice == '5':
            print("\n💾 Veritabanı yedeği alınıyor...")
            try:
                from backup_db import create_backup
                backup_path = create_backup()
                if backup_path:
                    print(f"🎉 Başarılı! Yedek konumu: {backup_path}")
            except Exception as e:
                print(f"❌ Yedekleme hatası: {e}")
            input("\nAna menüye dönmek için Enter'a basın...")
            
        elif choice == '6':
            print("\n⏳ Kütüphaneler kuruluyor...")
            os.system(f'"{sys.executable}" -m pip install -r requirements.txt')
            input("\n✅ Kurulum tamamlandı! Ana menüye dönmek için Enter'a basın...")
            
        elif choice == '0':
            print("\n👋 Çıkış yapılıyor. Bol kazançlar!\n")
            break
            
        else:
            print("\n⚠️ Hatalı seçim yaptınız, tekrar deneyin.")
            time.sleep(1)

if __name__ == "__main__":
    if os.name == 'nt':
        os.system('color')
    main()

