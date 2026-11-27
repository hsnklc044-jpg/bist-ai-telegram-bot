# K-115 uygulama öncesi denetim notu (27.11.2026)

Kayıt: DECISIONS K-115 ("yapımdan önce denetlenir"). Hazırlık kuyruğu 4, KUSURLAR S37. Hazırlayan: koordinatörün salt okunur inceleme alt ajanı; koordinatör 4 atfı ayrıca açıp doğruladı (`core/market/provider.py:92`, `core/market/membership.py:147`, `core/backtest/research.py:84`, `COVERAGE_START` bu dalda yok). Ağ, ölçüm, backtest çalıştırılmadı (K-106).

## 1. Yahoo istek yükü
- `core/market/provider.py:92-100`: `yf.download(symbols, threads=True)`; yfinance 1.7.0 sembolleri tek tek indirir, istek ≈ sembol sayısı (çerez/crumb istekleri doğrulanmadı).
- Önbellek 15 dk (`core/market/store.py:35, 194-205, 243`); artımlı indirme son 10 gün (`store.py:33, 252`); düzeltilmiş fiyat değişirse 5 yıllık yeniden indirme (`store.py:298-302`).
- Canlı liste `symbols_to_update()` (`core/reports/daily.py:296-310`): tekil ≈136 (alarm ve pozisyonlar sayılmadı). `ever_members()` 202 sembol; 76'sı canlı listede yok (K-115 75 diyor; fark doğrulanmadı). Çalışma başına ≈136 → ≈212 istek (+%56); hafta içi 18:30 raporu, başlangıç telafisi ve her `/report`.
- Risk: işlemden kalkmış sembol her çalışmada boş döner ve yeniden sorulur (`store.py:280`). "İşlem dışı" işareti indirme listesinden çıkarmayı da kapsamalı.
- CI iş akışları 202 sembolü zaten indiriyor (`core/market/update.py:34-37`); yük yalnız canlı bilgisayara yeni.

## 2. `ever_members` / `COVERAGE_START`
- `ever_members` (`core/market/membership.py:147-152`) yalnız üyelik CSV'lerini okur; K-115 bu dosyalara dokunmazsa sonucu değişmez.
- `COVERAGE_START` bu dalda yok (yalnız birleşmemiş `claude/d5-bilesen-1911`).
- Dolaylı etki: `core/backtest/research.py:84` `tradable_symbols(ever_members())` `before` olmadan; yeni mumlar ya da yeniden indirmeler araştırma evreninden hisse düşürebilir. `/tara` korunur (`before=HOLDOUT_START`). Etki 18.12 sonrası araştırmalara düşer.

## 3. K-93 / K-94
- K-94, K-93 (1), (4)–(7): etki yok (evren `universe.csv`, aday listesine girmedikçe).
- **K-93 (3) iki kaynak serisi: etki var.** Resmî karşılaştırma depo sembolleriyle kesişir (`core/official/compare.py:68`); K-115 sonrası kontrol edilen hisse ≈+75 artar, "≤ %1 farklı" oranının payı ve paydası değişir (`core/reports/slo.py:297-303`). Seri 05.12.2026'da biter (K-93 (3), K-97).

## 4. Sonuç
**Koşullu uygulanabilir: 18.12 sonrası, ayrı dal, kapıdan.** Koşullar: (a) kurulum anında K-93 (3) serisi sonuçlanmış olmalı, açıksa uygulanmaz ve sahibe karar talebi yazılır; (b) önce kırmızı testler: `ever_members()` = 202 ve bugünkü aday listesi değişmez; (c) "işlem dışı" hisseler indirme listesinden çıkar; (d) `research.py:84` evren etkisi 18.12 sonrası araştırmanın ön kaydına yazılır.

Doğrulanmadı: 75/76 farkı; yfinance çerez/crumb istekleri; `load_frames`/`SCREEN_END` kesimi; alarm ve pozisyon sembol sayısı.
