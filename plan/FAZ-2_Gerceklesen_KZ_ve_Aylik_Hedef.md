# Faz 2: Gerçekleşen Kâr/Zarar & Aylık Gelir Hedefi

## 🎯 Bu Fazın Amacı
Kullanıcının portföyündeki hisseleri sattığında elde ettiği net kâr/zararı (**Gerçekleşmiş K/Z**) kaydetmek, kullanıcının belirlediği **aylık kazanç hedefine** kıyasla ilerlemesini dashboard üzerinde görsel olarak takip edebilmesini sağlamak.

---

## 📋 Gereksinimler
1. **Veritabanı Tabloları:**
   - **`transactions` (İşlem Geçmişi):**
     - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
     - `symbol`: TEXT
     - `lot`: INTEGER
     - `buy_price`: REAL (Ortalama alış maliyeti)
     - `sell_price`: REAL (Satış fiyatı)
     - `realized_pnl`: REAL (`(sell_price - buy_price) * lot`)
     - `sell_date`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - **`settings` (Kullanıcı Ayarları):**
     - `key`: TEXT PRIMARY KEY
     - `value`: TEXT (Örn: `monthly_target_tl: 25000`)
2. **Veritabanı Fonksiyonları (`database.py`):**
   - `record_sale(symbol, lot, buy_price, sell_price)`: Pozisyonu azaltır/kapatır ve transaction kaydı oluşturur.
   - `get_transactions(month=None, year=None)`: Belirli ay veya tüm işlem geçmişini getirir.
   - `get_setting(key, default=None)` & `set_setting(key, value)`
   - `get_monthly_realized_pnl(year, month)`: İlgili ayın toplam gerçekleşen kârını hesaplar.
3. **Backend API Route'ları (`app.py`):**
   - `POST /api/portfolio/sell` -> Hisse satışı yapar, `portfolio` tablosundan düşer ve `transactions` tablosuna işler.
   - `GET /api/target/progress` -> Bu ayın gerçekleşen kârı, aylık hedef, kalan tutar ve % ilerleme oranını döner.
   - `POST /api/settings/target` -> Aylık kazanç hedefini günceller.
   - `GET /api/transactions` -> Gerçekleşen satış geçmişini listeler.
4. **Kullanıcı Arayüzü Bileşenleri:**
   - **Aylık Hedef İlerleme Çubuğu (Progress Bar):**
     - Hedef: Örn. ₺30.000
     - Gerçekleşen Kâr: ₺12.450 (%41.5)
     - Kalan: ₺17.550
   - **Satış Yap Modalı:** Portföy sayfasında "Sat" butonu ile açılan pop-up (Satılacak lot adedi, satış fiyatı).
   - **Geçmiş İşlemler Tablosu:** Tarih | Hisse | Satılan Lot | Alış | Satış | Elde Edilen K/Z

---

## 🛠️ Yapılma Adımları
1. **DB Şemasının Genişletilmesi:** `transactions` ve `settings` tabloları `database.py`'a eklenir.
2. **Kısmi ve Tam Satış Mantığı:** Portföydeki lot adedinden düşme (veya lot 0 olursa satırı silme) ve gerçekleşen K/Z formülünün işletilmesi.
3. **Aylık Filtreleme Sorgusu:** SQLite `strftime('%Y-%m', sell_date)` ile ay bazında gerçekleşen net kâr toplama fonksiyonunun yazılması.
4. **Arayüz Entegrasyonu:** Portföy sayfasına "Satış Geçmişi" sekmesi ve Aylık Hedef ilerleme göstergesi eklenmesi.
5. **Test ve Doğrulama:**
   - Farklı aylara ait sahte işlemler girilerek ay geçişlerinde sıfırlanma/doğru ay filtresi testi.
   - Hedef 0 veya boşken sıfıra bölme (division by zero) hatası kontrolleri.

---

## 📊 Fazın Durumu
- **Durum:** 🟢 **Tamamlandı**
- **İlerleme:** %100
- **Tamamlananlar:**
  - [x] `transactions` ve `settings` SQLite tabloları (`database.py`)
  - [x] Kısmi ve tam satış fonksiyonu (`record_sale`), satış geçmişi listeleme ve ay bazlı gerçekleşen kâr hesaplaması
  - [x] Backend API route'ları (`/api/portfolio/sell`, `/api/target/stats`, `/api/target/set`, `/api/transactions`, `/api/transactions/delete`)
  - [x] Aylık Kazanç Hedefi ve İlerleme Göstergesi (Progress Bar) kartı
  - [x] Aktif Pozisyonlar ve Gerçekleşen Satış Geçmişi sekmeleri (Tabs)
  - [x] Canlı K/Z önizlemeli ve "Güncel Fiyattan Sat" butonlu Satış Modalı
  - [x] Uçtan uca alım, kısmi satış, kâr gerçekleşme ve hedef ilerleme testleri
