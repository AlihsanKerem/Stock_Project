import os
import sys
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu():
    clear_screen()
    print("\033[96m" + "=" * 55)
    print("      🚀 BIST ALGO-TRADE & ANALİZ SİSTEMİ 🚀      ")
    print("=" * 55 + "\033[0m")
    print("\n\033[93m[1]\033[0m 🛠️  Sıfırdan Kurulum (Gerekli kütüphaneleri kurar)")
    print("\033[93m[2]\033[0m 🤖 Telegram Botunu Başlat (Otomatik Günlük Tarama)")
    print("\033[93m[3]\033[0m 🌐 Web Arayüzünü Başlat (Dashboard)")
    print("\033[93m[4]\033[0m 📊 Sadece Hızlı Tarama Yap (Veritabanını Güncelle)")
    print("\033[93m[0]\033[0m ❌ Çıkış\n")
    print("\033[96m" + "=" * 55 + "\033[0m")

def main():
    while True:
        print_menu()
        choice = input("\n👉 Lütfen bir işlem seçin (0-4): ")

        if choice == '1':
            print("\n⏳ Kütüphaneler kuruluyor, lütfen bekleyin...")
            os.system(f"{sys.executable} -m pip install -r requirements.txt")
            print("\n✅ Kurulum tamamlandı! Ana menüye dönülüyor...")
            time.sleep(2)
            
        elif choice == '2':
            print("\n🚀 Telegram botu başlatılıyor... (Kapatmak için Ctrl+C)")
            os.system(f"{sys.executable} bot_main.py")
            
        elif choice == '3':
            print("\n🌐 Web arayüzü başlatılıyor...")
            print("💡 Lütfen tarayıcınızda şu adresi açın: http://127.0.0.1:5000")
            print("(Kapatmak için Ctrl+C yapabilirsiniz)")
            os.system(f"{sys.executable} app.py")
            
        elif choice == '4':
            print("\n📊 Hızlı BIST100 Taraması Başlatılıyor...")
            os.system(f"{sys.executable} analyzer.py")
            print("\n✅ Tarama tamamlandı ve veritabanı güncellendi! Ana menüye dönülüyor...")
            time.sleep(3)
            
        elif choice == '0':
            print("\n👋 Çıkış yapılıyor. Bol kazançlar!\n")
            break
            
        else:
            print("\n⚠️ Hatalı seçim yaptınız, tekrar deneyin.")
            time.sleep(1)

if __name__ == "__main__":
    # Windows konsolunda renklerin düzgün çalışması için
    if os.name == 'nt':
        os.system('color')
    main()
