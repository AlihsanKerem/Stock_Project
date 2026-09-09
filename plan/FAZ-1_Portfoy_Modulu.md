# Faz 1: Portföy Modülü & K/Z (MVP)

## 🎯 Bu Fazın Amacı
Kullanıcının satın aldığı hisseleri adet (lot) ve alış maliyeti bazında sisteme kaydedebilmesini, güncel piyasa fiyatları üzerinden **gerçekleşmemiş kâr/zarar (Unrealized P&L)** ve toplam portföy değerini anlık olarak görebilmesini sağlamak.

---

## 📋 Gereksinimler
1. **Veritabanı Tablosu (`portfolio`):**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `symbol`: TEXT (Örn: THYAO.IS)
   - `lot`: INTEGER (Hisse adedi)
   - `buy_price`: REAL (Alış fiyatı / birim maliyet)
   - `buy_date`: TIMESTAMP (Alış tarihi)
   - `notes`: TEXT (Opsiyonel not)
2. **Veritabanı Fonksiyonları (`database.py`):**
   - `add_portfolio_position(symbol, lot, buy_price, buy_date=None, notes=None)`
   - `get_portfolio_positions()`
   - `delete_portfolio_position(position_id)`
   - `update_portfolio_position(position_id, lot, buy_price)`
3. **Backend API Route'ları (`app.py`):**
   - `GET /portfolio` -> `templates/portfolio.html` sayfasını render eder
   - `GET /api/portfolio` -> Portföydeki hisseleri, anlık fiyatları, her pozisyonun K/Z (TL ve %) ve toplam portföy özetini JSON döner
   - `POST /api/portfolio/add` -> Yeni hisse/lot alımı ekler
   - `POST /api/portfolio/delete` -> Pozisyon siler
4. **Hesaplama Mantığı:**
   - **Maliyet Toplamı:** `lot * buy_price`
   - **Güncel Değer:** `lot * current_price`
   - **Gerçekleşmemiş K/Z (TL):** `(current_price - buy_price) * lot`
   - **Gerçekleşmemiş K/Z (%):** `((current_price - buy_price) / buy_price) * 100`
   - Aynı hisseden birden fazla alım varsa gruplanmış **ağırlıklı ortalama maliyet** gösterimi desteği.
5. **Kullanıcı Arayüzü (`templates/portfolio.html`):**
   - **Üst Özet Kartları:** Toplam Portföy Değeri, Toplam Maliyet, Toplam K/Z (TL ve %)
   - **Pozisyon Tablosu:** Hisse Kodu | Adet (Lot) | Alış Fiyatı | Güncel Fiyat | Toplam Değer | K/Z (TL) | K/Z (%) | İşlemler (Sil / Düzenle)
   - **Alım Ekleme Formu / Modalı:** Hisse seçimi/kodu, Lot adedi, Alış fiyatı girişi

---

## 🛠️ Yapılma Adımları
1. **Veritabanı Katmanı:**
   - `database.py` içine `portfolio` tablosu `init_db()` fonksiyonuna eklenir.
   - CRUD fonksiyonları (`add_portfolio_position`, `get_portfolio_positions`, `delete_portfolio_position`) yazılır.
2. **Backend & API Katmanı:**
   - `app.py` içine `/portfolio` ve `/api/portfolio/*` endpoint'leri yazılır.
   - yfinance üzerinden portföydeki hisselerin anlık son kapanış/canlı fiyatları çekilerek K/Z hesaplanır.
3. **Arayüz Katmanı:**
   - `templates/portfolio.html` şablonu oluşturulur (Modern, responsive, renk kodlamalı yeşil/kırmızı K/Z).
   - Diğer sayfalara (`index.html`, `tracked.html`, `detail.html`) portföy navigasyon linki eklenir.
4. **Test ve Doğrulama:**
   - En az 3 farklı BIST hissesiyle alım pozisyonları girilerek test edilir.
   - Excel / el hesabı ile arayüzdeki kâr/zarar rakamları karşılaştırılır.

---

## 📊 Fazın Durumu
- **Durum:** 🟢 **Tamamlandı**
- **İlerleme:** %100
- **Tamamlananlar:**
  - [x] `portfolio` SQLite tablosu ve CRUD fonksiyonları (`database.py`)
  - [x] Portföy API endpoint'leri (`/api/portfolio`, `/api/portfolio/add`, `/api/portfolio/delete`, `/api/portfolio/update`) (`app.py`)
  - [x] Canlı fiyat çekimi ve Gerçekleşmemiş K/Z (Unrealized P&L) hesabı
  - [x] Modern ve responsive portföy arayüzü (`templates/portfolio.html` & `static/js/portfolio.js`)
  - [x] Sayfalar arası navigasyon entegrasyonu (Ana Sayfa, Hisse Analiz, Takip Listesi, Portföy)
  - [x] Gerçek piyasa fiyatlarıyla uçtan uca alım/satım ve K/Z testleri
