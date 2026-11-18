# S4 kuru çalıştırma (SAHTE VERİ, 18.11.2026)

**Bu bir ölçüm değildir.** Bütün sayılar sabit tohumla üretilmiş sahte veridir (`scripts/s4_kuru_calistirma.py`, tohum 20261118). Amaç, 06.01.2027'de (en erken, K-93 (1)) çalışacak yolun uçtan uca çalıştığını ve çıktının biçimini göstermektir. Canlı `data/signal_log.csv` ve `logs/` kullanılmadı; eşik ya da ölçüt değişmedi.

## Kurulum
- 5 görünüm × 4 sahte hisse × 46 seans (02.11.2026 – 04.01.2027), 5 seans ufku. Bir görünüm (Güçlü pozitif) bilerek +%1,5 ortalamayla üretildi ki sapma ve S5 bildirimi yolları da çalışsın; diğer dördünün ortalaması 0.
- Geçmiş (backtest) referansı her görünüm için 0; sahte XU100 serisi; sahte bir kurumsal işlem (BBB).
- Aynı yol: `s4_decision.check` → `first_decision` (değişmeyen `forward._verdict`) → `research_log_draft` → `drift.reasons` → S5 bildirimi.

## Sonuç
- 1. akşam (06.01.2027) gönderilecek mesaj sayısı: 2 (ilk karar + S5 bildirimi).
- 2. akşam (07.01.2027): 0 mesaj. Karar, taslak ve bildirim bir kez yazıldı.
- Taslak dosyası: `logs/research_log_taslak/2027-01-06_canli_ilk_karar.md` (bu çalışmada geçici klasörde).

## Telegram mesajları (örnek)
```text
📏 S4 canlı ölçüm: ilk karar (06.01.2027, K-93, 5 seans, maliyet öncesi)
• Güçlü pozitif: %+1.49 [%+1.23, %+1.75] → XU100'ü anlamlı şekilde geçiyor
• Pozitif: %-0.05 [%-0.38, %+0.28] → XU100'den farkı anlamlı değil
• Nötr: %-0.07 [%-0.39, %+0.26] → XU100'den farkı anlamlı değil
• Negatif: %+0.13 [%-0.29, %+0.55] → XU100'den farkı anlamlı değil
• Güçlü negatif: %+0.02 [%-0.35, %+0.39] → XU100'den farkı anlamlı değil
Karar bir kez yazıldı (logs/s4_ilk_karar.json); RESEARCH_LOG taslağı hazır. Ölçümdür, yatırım önerisi değildir.

🔔 Kural anlamlı çıktı (K-93 (4), 06.01.2027): maliyet (%0,30 gidiş-dönüş) düşüldükten sonra %99 güven aralığının alt ucu 0'ın üstünde.
• Güçlü pozitif: ortalama %+1.49, maliyet sonrası %99 alt uç %+0.82, 46 gün, 10 bağımsız dönem
Kanıt: logs/s4_ilk_karar.json ve logs/s5_bildirim.json. Bu yalnız bildirimdir: hiçbir şey açılmadı, hiçbir ayar değişmedi. S5 kullanıcı kararıdır ve S4'ün tamamen kapanmasını gerektirir. Yatırım önerisi değildir.
```

## RESEARCH_LOG taslağı (örnek)
```markdown
## 06.01.2027 – Canlı ölçüm ilk kararı (K-93)

- **Soru:** Günlük raporun 5 teknik görünümü, kayıttan sonraki 5 seansta XU100'den farklı mı?
- **Veri:** `data/signal_log.csv` kaynak `daily`, kayıt günleri 2026-11-02 – 2027-01-04; giriş ertesi açılış, çıkış 5. seans kapanışı, XU100 aynı seanslar (`core.reports.forward`). İleri veri; holdout'a dokunulmadı.
- **Ölçüt (K-93 (1), değişmedi):** `forward._verdict`: en az 20 gün ve 10 bağımsız dönem; %95 aralık 0'ın üstünde "geçiyor", altında "gerisinde", içeriyorsa "farkı anlamlı değil". Maliyet öncesi.
- **Sonuç:**
  - Güçlü pozitif: %+1.49 [%+1.23, %+1.75], 46 gün, 10 bağımsız dönem, isabet %90 → XU100'ü anlamlı şekilde geçiyor
  - Pozitif: %-0.05 [%-0.38, %+0.28], 46 gün, 10 bağımsız dönem, isabet %49 → XU100'den farkı anlamlı değil
  - Nötr: %-0.07 [%-0.39, %+0.26], 46 gün, 10 bağımsız dönem, isabet %50 → XU100'den farkı anlamlı değil
  - Negatif: %+0.13 [%-0.29, %+0.55], 46 gün, 10 bağımsız dönem, isabet %57 → XU100'den farkı anlamlı değil
  - Güçlü negatif: %+0.02 [%-0.35, %+0.39], 46 gün, 10 bağımsız dönem, isabet %52 → XU100'den farkı anlamlı değil
- **Backtest–canlı sapması (K-30):**
  - Güçlü pozitif: geçmiş %+0.00 → ⚠️ geçmişten anlamlı sapma (nedeni RESEARCH_LOG'a yazılır)
    - neden? Sapma en etkili 3 hisse (AAA, DDD, CCC) çıkarılınca da sürüyor: geniş tabanlı.
    - neden? Sapma tek bir güne bağlı değil.
    - neden? Piyasa: XU100'ün 5 seanslık ortalama getirisi canlı dönemde +%1,4, geçmiş dönemde -%0,6.
    - neden? Kurumsal işlem (fiyat düzeltmesi sonucu etkileyebilir): BBB 16.11.2026.
  - Pozitif: geçmiş %+0.00 → geçmişle uyumlu
  - Nötr: geçmiş %+0.00 → geçmişle uyumlu
  - Negatif: geçmiş %+0.00 → geçmişle uyumlu
  - Güçlü negatif: geçmiş %+0.00 → geçmişle uyumlu
- **S5 eşiği (K-93 (4), maliyet %0,30 sonrası %99 alt uç > 0):** Güçlü pozitif (%+0.82)
- **Deneme sayısı:** 14 (9 önceki kural + 5 canlı görünüm). Sonuca göre ölçüt, ufuk ya da görünüm değiştirilmez.
- **Kaynak:** bot taslağı `logs/research_log_taslak/2027-01-06_canli_ilk_karar.md`; RESEARCH_LOG'a değiştirilmeden taşınır.
```

## Kuru çalıştırmanın bulduğu (bu dalda düzeltilmedi; bot çıktısını değiştirir. Düzeltme ayrı davranış dalında: `claude/o63-o64` ea0f7af, `tests/test_s4_number_format.py`; aşağıdaki örnek eski biçimle)
- Aynı taslakta iki sayı biçimi var: `s4_decision._p` "%+1.49" (nokta, işaret % işaretinden sonra) yazıyor, `drift.reasons` ise "+%1,4" (virgül, Türkçe biçim). Düzeltme önerisi: `_p` yerine `core.reports.daily.pct` kullanmak. Kararın kendisini etkilemez, yalnız metni etkiler.
- Kayıt günleri ISO biçiminde ("2026-11-02 – 2027-01-04"); belgenin geri kalanı GG.AA.YYYY.
