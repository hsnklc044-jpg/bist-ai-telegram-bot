# Mesaj stili

Kullanıcı kararı (11.11.2026, A ve B). Bütün kullanıcı mesajlarına uygulanır. Kod karşılığı: `core/reports/style.py`
(sayı biçimi, puan sınıfı, başlık, yasak terim ve satır sınırı denetimi). Önceki tarama, mesaj sadeleştirme, `/tablo` ve
`/karne` mesaj kararlarının yerine geçer. Hesaplar, kurallar ve karne puanları bu belgeyle değişmez.

## Üç soru
Her mesaj yalnız üç soruya cevap verir:
1. Her şey yolunda mı?
2. Önemli ne değişti?
3. Kullanıcının bir şey yapması gerekiyor mu?

Gerisi "Ayrıntı" komutuna gider, kaybolmaz.

## Biçim
- **İlk satır:** başlık ve tarih, büyük harfle: `AKŞAM RAPORU · 11.11.2026`.
- **İkinci satır:** ✅ / ⚠️ / ❌ ya da puan sınıfı rengi ve tek cümle.
- Sorun yoksa sorun listelenmez; varsa yalnız sorunlar yazılır.
- `Senden beklenen:` satırı yalnız kullanıcıdan bir şey bekleniyorsa.
- **Uzunluk** (boş olmayan satır):
  - günlük rapor ≤ 7;
  - robot ve haftalık özet sorun yoksa ≤ 3, varsa ≤ 6;
  - uyarılar ≤ 4.
- **Tablolar** `<pre>` içinde, her satır ≤ 32 karakter, sayılar sağa hizalı.
- **Kullanıcı mesajında olmayanlar:** iç kod ve geliştirici terimi (SLO, CHARTER, K-/D-numaraları, ATR, CI, SHA, sürüm numarası, HTTP hata adı, dosya yolu). Sürüm yerine "güncelleme".
- **AL ve SAT** kelimesi ya da talimatı hiçbir mesajda yok (CLAUDE.md).
- **Sayılar:**
  - Türkçe ondalık virgül, binlik nokta: `1.234.567,89`.
  - Yüzde tek ondalık ve işaretli: `+1,2%`, `-4,6%`.
  - Fiyat 1.000 TL ve üstü ondalıksız (`12.249 TL`), altı iki ondalık (`644,25 TL`).
- **Emoji** yalnız durum (✅ ⚠️ ❌) ve puan sınıfı rengi (🟢 🟡 🟠 🔴); fiyat alarmında 🔔.
- **Uyarı ve dürüstlük notları** satır satır yazılmaz. "Teknik göstergedir, öneri değildir" notu detay çıktılarında kalır.
- **Veri notu:** veri doğrulanmamış kaynaktaysa (Seviye 3) başlığın altında tek satır "Veri: doğrulanmamış kaynak" (veri güveni kararı).

## Puan sınıfları (B; kodda sabit, detayda yazılı; açıklamadır, öneri değil)

| Puan | Renk | Sınıf |
|---|---|---|
| 80–100 | 🟢 | Güçlü |
| 60–79 | 🟢 | Olumlu |
| 40–59 | 🟡 | Karışık |
| 20–39 | 🟠 | Zayıf |
| 0–19 | 🔴 | Çok zayıf |

Puanı hesaplanamayan boyut "veri yok" olur; eksik boyut sıfır sayılmaz ve renk verilmez.

## Uygulanacak mesajlar
Günlük rapor, haftalık özet, 21:00 robot özeti, tarama abonelikleri (≤ 5 hisse), sağlık uyarıları, `/summary` ve `/durum` ilk
ekranı. Yeni `/robot_detay`: güncellemeler, bağlantılar, kuyruk. Güncelleyici bildirimleri ayrı tutulur, hafta sonu kurulur.

## Şablonlar (H; sayılar örnektir)

**Akşam raporu**
```
AKŞAM RAPORU · 11.11.2026
✅ Rapor tamam, sorun yok.
BIST 100: 10.760 (+0,8%)
Piyasa: 🟡 Karışık (trenddeki hisse %46)
Sanal hesap: 1.034.250 TL · bugün +0,4% · başlangıçtan +3,4% · reel -1,2%
/summary
```

**Tarama aboneliği** (değişiklik yoksa gönderilmez)
```
TARAMA · BIST100_KIRILIM · 11.11.2026
2 yeni · 1 çıkan
<pre>   Hisse Puan  Fiyat  Destek
🟢 PGSUS   78 154,40  147,50
🟡 TCELL   55  96,40   95,18</pre>
Çıkan: ALARK
/tara bist100_kirilim
```

**Fiyat alarmı**
```
🔔 ALARM · THYAO · 11.11.2026
Kapanış 289,76 TL · koşul: 290 TL altı
/alarm
```

**Robot özeti** (sorun yoksa 3 satır)
```
ROBOT · 11.11.2026
✅ 2 güncelleme sorunsuz kuruldu
Yarın: resmî endeks verisi
```
Sorun varsa: durum, tek cümle açıklama, `Senden beklenen:` (varsa), `/robot_detay`.

**Haftalık kontrol**
```
HAFTALIK KONTROL · 14.11.2026
✅ Sistem sağlıklı
```
Sorun varsa: `⚠️ 7 hedeften 6'sı tamam`, sorunlar madde madde, tek cümle sonuç, `/durum`.

**Acil uyarı**
```
❌ OLAY · 14:05
Bot yanıt vermedi; yeniden başlatıldı.
Şu an çalışıyor.
/durum
```

**Kullanıcının işi**
```
⚠️ SENİN İŞİN · 02.11.2026
Geçen ayın borsa fiyat ve endeks dosyalarını indir.
Robot bekliyor; diğer işler sürüyor.
/yardim_veri
```

## Karne notu (I madde 0)
Kullanıcının karnesinde (`core/analytics/scorecard.py` RULES, TradingView betiğinin birebir aktarımı) "SMA (fiyat üstü)" ve
"Bollinger (orta bant)" kuralları birebir aynıdır: ikisi de kapanış > SMA20 ve ikisi de 10 puan (11.11.2026'da koddan
doğrulandı). Betik böyle olduğu için değiştirilmez; bu tek koşul karneyi 20 puan etkiler.
