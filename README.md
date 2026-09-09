# 🚀 BIST Algo-Trade & Executive Dashboard

BIST (Borsa İstanbul) hisse senetleri için geliştirilmiş; teknik analiz ve temel rasyolara dayalı **Vade Bazlı Sinyal Tarayıcısı**, **Canlı K/Z Portföy Modülü**, **Aylık Gelir Hedefi Takipçisi**, **Oran Bazlı Fiyat Alarm Sistemi** ve **Telegram Bildirim Botu** içeren uçtan uca modern finansal karar destek platformu.

---

## 🌟 Öne Çıkan Özellikler

### 1. 📊 Executive Single-Pane Dashboard
- **Donut Portföy Dağılım Grafiği (Chart.js):** Açık pozisyonların güncel portföydeki payını renkli grafik ile görselleştirir.
- **Canlı KPI Sayaçları:** Toplam Portföy Varlığı, Canlı K/Z (₺ ve %), Bu Ayın Gerçekleşen Kârı, Günün Sinyalleri ve Aktif Alarmlar.
- **Aylık Kazanç Hedefi İlerlemesi:** Belirlediğiniz aylık TL kâr hedefine göre dinamik dolan renkli ilerleme çubuğu.

### 2. ⚡ Vade Bazlı Sinyal Tarayıcısı (`analyzer.py`)
Teknik ve temel analiz indikatörleri 3 temel yatırım vadesine ayrılmıştır:
- **⚡ Kısa Vade (1 - 7 Gün):** Haftalık Al-Sat (SMA5 > SMA20 kesişimi), Hacim Patlaması & Dönüş (Hedef: %2.5 - %7)
- **📈 Orta Vade (1 - 4 Hafta):** Aylık Al-Sat (SMA20 > SMA50 kesişimi, Hedef: %5 - %12)
- **💎 Uzun Vade / Değer:** Değer Avcısı (PD/DD <= 1 & RSI < 30, Hedef: %15 - %30+), Temettü Kalesi (Temettü > %5 & F/K < 15, Hedef: %10 - %25+)
- **Geçmiş Sinyal Günlüğü:** Üretilen tüm sinyaller tarih ve fiyat damgasıyla `signal_history` tablosuna kaydedilir.

### 3. 💼 Akıllı Portföy & Gerçekleşen K/Z Modülü
- Otomatik güncel piyasa fiyatı çekme desteği (`⚡ Güncel Fiyattan Al`).
- Kısmi veya tam satış desteği ile **Gerçekleşen K/Z (Realized PnL)** kaydı ve işlem geçmişi.

### 4. 🔔 Kullanıcı Tanımlı Oran Bazlı Bildirim & Telegram Botu
- "THYAO alış fiyatımdan %5 artarsa" veya "EREGL 45.00 ₺ altına düşerse" şeklinde oran/fiyat bazlı alarmlar.
- `bot_main.py` 5 dakikada bir fiyatları kontrol eder, hedef gerçekleştiğinde Telegram üzerinden anında bildirim iletir.
- Spam koruması ile tetiklenen alarmlar otomatik olarak `TRIGGERED` durumuna geçer.

### 5. 💾 Otomatik Veritabanı Yedekleme (`backup_db.py`)
- SQLite Online Backup API ile veritabanı aktifken dahi bozulmadan `backups/` klasörüne zaman damgalı yedekleme.
- Otomatik rotasyon: En güncel 10 yedek saklanır, eski yedekler disk doldurmamak için otomatik temizlenir.

---

## 🛠️ Kurulum ve Başlatma

### Gereksinimler
- Python 3.9+
- İnternet bağlantısı

### 1. Kütüphaneleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Ortam Değişkenlerini Ayarlayın
`.env.example` dosyasını `.env` olarak kopyalayın ve bilgilerinizi girin:
```bash
cp .env.example .env
```
`.env` içeriği:
```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_PORT=5000
SCAN_TIME=18:30
ALERT_CHECK_INTERVAL_MINUTES=5
```

### 3. Tek Komutla Başlatın
```bash
python baslat.py
```
Açılan menüden:
- `[1]` seçeneği ile **tüm sistemi (Web + Telegram Bot & Alarmlar)** tek tıkla başlatabilirsiniz.
- Tarayıcınızda [http://127.0.0.1:5000](http://127.0.0.1:5000) adresini açarak kullanmaya başlayabilirsiniz.

---

## 📁 Proje Dizin Yapısı

```
Stock_Project/
│
├── app.py                 # Flask Backend & API Endpoint'leri
├── analyzer.py            # Vade Bazlı Sinyal Tarama & Teknik Analiz Motoru
├── bot_main.py            # Telegram Botu & Arka Plan Alarm Scheduler'ı
├── database.py            # SQLite Veritabanı & CRUD Fonksiyonları
├── backup_db.py           # Otomatik & Rotasyonlu Veritabanı Yedekleme Aracı
├── sentiment.py           # LLM (Gemini / Ollama) Destekli Haber Duygu Analizi
├── baslat.py              # İnteraktif Başlatıcı Menüsü (Çoklu Süreç Desteği)
│
├── backups/               # Otomatik veritabanı yedekleri (.db)
├── templates/             # Jinja2 HTML Sayfa Şablonları
│   ├── index.html         # Executive Single-Pane Dashboard & Tarayıcı
│   ├── portfolio.html     # Portföy & Gerçekleşen K/Z Yönetimi
│   ├── tracked.html       # Takip Listesi & Alarm Yönetim Merkezi
│   └── detail.html        # Tekli Hisse Analizi & AI Yorumları
│
├── static/
│   ├── css/style.css      # Modern Glassmorphic Dark UI Tasarım Sistemi
│   └── js/
│       ├── main.js        # Dashboard, Chart.js & Sinyal Tablosu Mantığı
│       ├── portfolio.js   # Portföy & Satış Modalı Mantığı
│       └── tracked.js     # Alarm & Takip Listesi Mantığı
│
└── plan/                  # 6 Fazlık İteratif Geliştirme Yol Haritası & Dokümanları
```

---

## 📑 Geliştirme Fazları Özeti

| Faz | Başlık | Durum |
|---|---|---|
| **Faz 0** | Baseline & Mevcut Durum Tespiti | 🟢 Tamamlandı |
| **Faz 1** | Portföy Modülü & K/Z (MVP) | 🟢 Tamamlandı |
| **Faz 2** | Gerçekleşen K/Z & Aylık Gelir Hedefi | 🟢 Tamamlandı |
| **Faz 3** | Kullanıcı Tanımlı Oran Bazlı Bildirim Sistemi | 🟢 Tamamlandı |
| **Faz 4** | Vade Bazlı Sinyal Tablosu & Tarama | 🟢 Tamamlandı |
| **Faz 5** | Sadeleştirilmiş Tek Dashboard (Executive View) | 🟢 Tamamlandı |
| **Faz 6** | Sağlamlaştırma, Hata Yönetimi & Dağıtım | 🟢 Tamamlandı |

---

## 🔒 Güvenlik & Yasal Uyarı

Bu yazılım yalnızca kişisel analiz ve takip amaçlıdır. Algoritmik sinyaller ve AI yorumları **yatırım tavsiyesi niteliğinde değildir**.
