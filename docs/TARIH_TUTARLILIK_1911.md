# S2 / S3 / S4 tarih tutarlılığı (19.11.2026 gecesi)

**Neden:** 18.11 23:36 olgunluk ölçümü bir çelişki buldu. K-105 canlıdaki DECISIONS'ta yoktu, MATURITY'deki S3 satırı ise hâlâ eski tarihi (03.12 / 12.12) gösteriyordu.
**Kural:** eşik, ölçüt ve ön kayıt değişmez. Yalnız aynı karardan çıkan tarihler hizalanır. Sahibin yazdığı metinler (Aralık planının hedef cümlesi) silinmez, yanına not düşülür (Md. 11).

## Karşılaştırma (düzeltmeden önce → sonra)

| Kilometre taşı | Dayanak | MATURITY | ROADMAP | S3_MUDAHALE | PROGRAM | Durum |
|---|---|---|---|---|---|---|
| S2 dördüncü hafta satırı | K-93 (7), seri 14.11'den | en erken 05.12 (satır 46) | 05.12 cumartesi | — | "Aralık planındaki kilometre taşları" | ✅ tutarlı |
| S2 en erken kapanış | K-93 (7) | 07.12 (2. hafta tutmazsa 14.12) | 07.12 | — | S2 kapanmış ya da gerekçeli (QB-PRG-1 kabul ölçütü) | ✅ tutarlı |
| S3 30 gün sayacı | K-93 (6) → K-96 → **K-105** | 03.12 ve 12.12 (K-105 yalnız satırın sonunda) → **en başta "Güncel: en erken 18.12"** | tablo satırı 12.12 (K-96), altında K-105 notu → **18.12 (K-105)** | başlık, sayaç, §Ölçüm 12.12 ve 13.11–12.12 → **18.12 ve 19.11–18.12** | İP-2 ve risk satırı "12.12'ye kadar" → **18.12'ye kadar** | ✅ düzeltildi |
| S3'ün S2 ile aynı gün kapanması | seviye atlanmaz | "S3 S2 ile aynı gün kapanabilir (05–07.12)" → **"S3 S2'den önce kapanamaz: S2 en erken 07.12, S3 en erken 18.12"** | — | — | — | ✅ düzeltildi |
| "15.12'ye kadar resmî S3" hedefi | Aralık planı (sahibin metni) | — | hedef cümlesi aynen; altında K-105 notu: "hedef tutmaz, tarih kayar, ölçüt gevşemez" | — | — | ✅ not var; yeni hedef 15.12 değerlendirmesinde |
| S4 ilk olgun sonuç | Aralık planı | S4 kısmi (satır 44) | Kasım sonu | — | "S4'ün ilk olgun sonucu RESEARCH_LOG'da" | ✅ tutarlı |
| S4 holdout | K-22, a4 ön kaydı | — | 27.04.2027'den önce bakılmaz | — | — | ✅ tutarlı (a4 ile 2027 planı arasındaki ayrı çelişki sahipte bekliyor) |

## Nereye girdi
- **Sabahki zincir:** `claude/zincir3-d-1911` 9c6eaa2. K-96 paketinin (78eaad0) üstüne tek belge commit'i eklendi: DECISIONS K-105 (8bddfb8'deki metnin aynısı), MATURITY ve S3_MUDAHALE. Sürüm v0.99.148 olarak kalır. 08:40'taki K kurulumu bu ucu kurar (otonom_kurallar 1aa).
- **B ve T yeniden kuruldu:** `claude/zincir3-b-1911` 556ed15 ve `claude/zincir3-t-1911` d49ca34. Eski uçlarla tek farkları bu üç belge dosyası (`git diff --stat`).
- **ROADMAP ve PROGRAM satırları:** yalnız bu dalda düzeltildi. Bu iki belgedeki planlar sabahki zincirde yok, o yüzden ancak belge dalı girince canlıya gelir.
- **Kalan iş:** `claude/gece-log-1911` ve `claude/faz-a2-1911` hâlâ eski T'nin üstünde. Kapıya verilmeden önce zincir3-t üstüne yeniden kurulmaları gerekir; bu sırada 8bddfb8 atlanır.
