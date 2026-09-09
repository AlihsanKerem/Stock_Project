import os
import sys
import io
import shutil
import sqlite3
from datetime import datetime

# Windows console encoding fix
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_FILE = "stocks.db"
BACKUP_DIR = "backups"
MAX_BACKUPS = 10

def create_backup(db_path=DB_FILE, backup_folder=BACKUP_DIR, max_backups=MAX_BACKUPS):
    """
    stocks.db veritabanının güvenli bir kopyasını backups/ klasörüne alır
    ve en fazla max_backups kadar eski yedeği saklayıp gerisini temizler.
    """
    if not os.path.exists(db_path):
        print(f"⚠️ Yedeklenecek veritabanı bulunamadı: {db_path}")
        return None

    # backups klasörünü oluştur
    os.makedirs(backup_folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"stocks_backup_{timestamp}.db"
    backup_path = os.path.join(backup_folder, backup_filename)

    try:
        # SQLite online backup API'sini kullanarak aktif okuma/yazma esnasında da bozulmadan yedek alalım
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(backup_path)
        
        with dst_conn:
            src_conn.backup(dst_conn)
            
        dst_conn.close()
        src_conn.close()
        
        print(f"✅ Veritabanı yedeği başarıyla oluşturuldu: {backup_path}")

        # Rotasyon: Eski yedekleri kontrol et ve temizle
        rotate_backups(backup_folder, max_backups)
        return backup_path

    except Exception as e:
        print(f"❌ Yedekleme sırasında hata oluştu, fallback kopyalama deneniyor: {e}")
        try:
            shutil.copy2(db_path, backup_path)
            print(f"✅ Dosya kopyalama ile yedek alındı: {backup_path}")
            rotate_backups(backup_folder, max_backups)
            return backup_path
        except Exception as copy_err:
            print(f"❌ Fallback kopyalama da başarısız oldu: {copy_err}")
            return None

def rotate_backups(backup_folder=BACKUP_DIR, max_backups=MAX_BACKUPS):
    """
    Yedek klasöründeki dosyaları sıralar ve max_backups adedinden fazlasını siler.
    """
    try:
        backups = [
            os.path.join(backup_folder, f) 
            for f in os.listdir(backup_folder) 
            if f.startswith("stocks_backup_") and f.endswith(".db")
        ]
        # Değiştirilme tarihine göre eskisinden yenisine sırala
        backups.sort(key=os.path.getmtime)

        if len(backups) > max_backups:
            to_delete = backups[:-max_backups]
            for file_path in to_delete:
                try:
                    os.remove(file_path)
                    print(f"🗑️ Eski yedek temizlendi: {os.path.basename(file_path)}")
                except Exception as ex:
                    print(f"Yedek silinirken hata: {ex}")
    except Exception as e:
        print(f"Rotasyon kontrolü sırasında hata: {e}")

def list_backups(backup_folder=BACKUP_DIR):
    """
    Mevcut yedekleri listeler.
    """
    if not os.path.exists(backup_folder):
        return []
    backups = [
        f for f in os.listdir(backup_folder) 
        if f.startswith("stocks_backup_") and f.endswith(".db")
    ]
    backups.sort(reverse=True)
    return backups

if __name__ == "__main__":
    print("📦 SQLite Veritabanı Yedekleme Aracı")
    create_backup()
