# Faz 3: Kullanıcı Tanımlı Oran Bazlı Bildirim Sistemi

## 🎯 Bu Fazın Amacı
Kullanıcının belirlediği hisseler için özel tetikleyiciler kurabilmesini ("THYAO %5 artarsa haber ver" veya "EREGL %3 düşerse uyar") ve eşik aşıldığında Telegram üzerinden anlık bildirim almasını sağlamak.

---

## 📋 Gereksinimler
1. **Veritabanı Tablosu (`alerts`):**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `symbol`: TEXT (Örn: THYAO.IS)
   - `reference_price`: REAL (Alarm kurulduğu andaki baz fiyat)
   - `target_percentage`: REAL (Örn: +5.0 veya -3.0)
   - `target_price`: REAL (`reference_price * (1 + target_percentage/100)`)
   - `direction`: TEXT ('UP' veya 'DOWN')
   - `status`: TEXT ('ACTIVE', 'TRIGGERED', 'CANCELLED')
   - `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - `triggered_at`: TIMESTAMP
2. **Veritabanı Fonksiyonları (`database.py`):**
   - `add_alert(symbol, reference_price, target_percentage, direction)`
   - `get_active_alerts()`
   - `mark_alert_triggered(alert_id)`
   - `delete_alert(alert_id)`
3. **Arka Plan Kontrol Servisi (`bot_main.py` / Scheduler):**
   - Aktif alarmları periyodik olarak (örn. 10-15 dakikada bir) kontrol etme.
   - yfinance üzerinden anlık fiyatı çekip hedef fiyatın aşılıp aşılmadığını denetleme.
   - Tetiklenme durumunda Telegram botu ile formatlı mesaj atma (`🚨 ALARM TETİKLENDİ: THYAO %5.2 yükseldi!`).
   - Tekrarlayan spam bildirimleri önlemek için alarmın durumunu `TRIGGERED` olarak güncelleme.
4. **Kullanıcı Arayüzü & API:**
   - `GET /api/alerts` -> Tüm alarmları listeler.
   - `POST /api/alerts/add` -> Yeni alarm oluşturur.
   - `POST /api/alerts/delete` -> Alarm iptal eder.
   - Takip listesi veya portföy sayfasında "⏰ Alarm Kur" modalı ve "Aktif Alarmlar" sekmesi.

---

## 🛠️ Yapılma Adımları
1. **Veritabanı Hazırlığı:** `alerts` tablosu ve ilgili CRUD metotlarının eklenmesi.
2. **Bildirim Servisi Geliştirmesi:** `bot_main.py` içine `check_alerts_job()` fonksiyonunun yazılması ve `schedule` kütüphanesine bağlanması.
3. **Telegram Mesaj Formatlama:** Eşik aşıldığında net, emoji destekli ve okunabilir bir Telegram bildirim şablonu oluşturulması.
4. **Arayüz Entegrasyonu:** Web sayfasından hızlı alarm kurma butonları ve aktif alarmların durumunu gösteren arayüz bileşeni eklenmesi.
5. **Test ve Doğrulama:**
   - Test verisi ile sahte bir fiyat yükselişi simüle edilerek Telegram mesajının ulaşıp ulaşmadığının test edilmesi.
   - Tekrarlanan mesaj spam'i oluşmadığının teyit edilmesi.

---

## 📊 Fazın Durumu
- **Durum:** 🟢 **Tamamlandı**
- **İlerleme:** %100
- **Tamamlananlar:**
  - [x] `alerts` SQLite tablosu ve CRUD operasyonları (`database.py`)
  - [x] Backend API route'ları (`/api/alerts`, `/api/alerts/add`, `/api/alerts/delete`)
  - [x] Telegram bot arka plan kontrol servisi (`check_alerts_job`) ve otomatik tetikleme/spam önleme mantığı (`bot_main.py`)
  - [x] Takip listesi sayfasının **"👀 Takip & 🔔 Alarmlar"** merkezine dönüştürülmesi (`templates/tracked.html` & `static/js/tracked.js`)
  - [x] Tek tıkla canlı referans fiyatlı ve hızlı yüzde butonlu (`+%3`, `+%5`, `+%10`, `-%3`, `-%5`) Alarm Modalı
  - [x] Uçtan uca alarm kurma, tetikleme simülasyonu ve iptal testleri
