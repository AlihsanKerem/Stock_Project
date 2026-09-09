# Faz 4: Vade Bazlı Sinyal Tablosu & Tarama

## 🎯 Bu Fazın Amacı
`analyzer.py` içindeki teknik ve temel analiz sinyallerini net yatırım vadelerine (Kısa Vade: Birkaç gün - 1 hafta / Orta Vade: 2-4 hafta / Uzun Vade: Temettü-Değer) göre kategorize etmek, hedeflenen getiri potansiyelini özetleyen filtrelenebilir bir sinyal paneli sunmak.

---

## 📋 Gereksinimler
1. **Sinyal - Vade Eşleme Matrisi (`analyzer.py`):**
   - **Kısa Vade (1 - 7 Gün):** Haftalık Al-Sat (SMA5 > SMA20 kesişimi), Hacim Onaylı RSI Kırılımı
   - **Orta Vade (1 - 4 Hafta):** Aylık Al-Sat (SMA20 > SMA50 kesişimi), Trend Dönüşü
   - **Uzun Vade (1 - 6 Ay+):** Değer Avcısı (PD/DD <= 1 & RSI < 30), Temettü Kalesi (Temettü Verimi >= %5 & F/K < 10)
2. **Hedef Getiri & Risk Aralıkları:**
   - Her sinyal tipi için yaklaşık hedef getiri bandı (örn: Kısa vade için %4 - %8, Orta vade için %10 - %20).
3. **Veritabanı Sinyal Geçmişi (`signal_history`):**
   - `id`: INTEGER PRIMARY KEY AUTOINCREMENT
   - `symbol`: TEXT
   - `signal_type`: TEXT
   - `timeframe`: TEXT ('SHORT', 'MEDIUM', 'LONG')
   - `price_at_signal`: REAL
   - `target_return`: TEXT
   - `created_at`: DATE
4. **Kullanıcı Arayüzü:**
   - Vadeye göre filtreleme butonları (Hepsi / Kısa Vade / Orta Vade / Değer & Temettü)
   - Sütunlar: Hisse Kodu | Sinyal Adı | Vade | Sinyal Fiyatı | Hedef Getiri | RSI | Tarih | Detay Gör

---

## 🛠️ Yapılma Adımları
1. **Analiz Motorunun Güncellenmesi:** `analyzer.py` içindeki `analyze_stock` çıktısına `timeframe` (Kısa/Orta/Uzun Vade) ve `target_range` alanlarının eklenmesi.
2. **Sinyal Geçmişi Tablosu:** Her gün taranan sinyallerin `signal_history` tablosuna kaydedilmesi (böylece eski sinyaller kaybolmaz).
3. **API Endpoint:** `GET /api/signals?timeframe=short` gibi filtre parametreleri destekleyen endpoint yazılması.
4. **Arayüz Tablosu:** Ana sayfada veya ayrı bir sekmede vade etiketli, renkli rozetlerle (badge) zenginleştirilmiş sinyal tablosu oluşturulması.
5. **Test ve Doğrulama:**
   - BIST100 taraması yapıldığında kategorilerin ve etiketlerin doğru yansıdığının test edilmesi.

---

## 📊 Fazın Durumu
- **Durum:** 🟢 **Tamamlandı**
- **İlerleme:** %100
- **Tamamlananlar:**
  - `analyzer.py` sinyal motoru vade etiketleri (`timeframe_key`, `timeframe_label`), hedef getiri bantları (`target_return`), `risk_level` ile zenginleştirildi.
  - `database.py` içine `signal_history` tablosu eklendi; `save_signals`, `get_signals`, `clear_signal_history` fonksiyonları yazıldı.
  - `app.py` içinde `/api/signals` (vadeye göre filtreleme) ve `/api/signals/scan` (canlı tarama) endpoint'leri oluşturuldu.
  - `templates/index.html` ve `static/js/main.js` yenilendi; özet istatistik kartları, vade filtre butonları (Kısa / Orta / Uzun / Sinyalliler), renkli rozetler ve hızlı aksiyon butonları eklendi.

