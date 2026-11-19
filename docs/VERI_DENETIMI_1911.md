# Veri denetimi: D-1, D-2, D-4 (QB-ARS-1 Faz A, 18.11.2026)

**Durum:** salt okunur denetim. Bu gece hiçbir şey düzeltilmedi. Düzeltme önerileri risk sırasıyla en sondadır.

**Yöntem:**
- Kod taraması: `core/backtest`, `core/strategy`, `core/market`, `tests/test_no_lookahead.py`.
- Canlı veritabanı okuması: `data/market.db`, salt okunur kipte (`mode=ro`).
- Betik çalışma klasörünün dışındadır: geçici klasörde `d2_kontrol.py`. Hiçbir dosya yazmadı.

## D-1 Zamana sadık veri (geleceğe bakma)
| # | Bulgu | Sınıf | Kanıt |
|---|---|---|---|
| 1 | Kural ve motor için geleceğe bakma testi var. Gelecek fiyatlar karıştırılıyor ve kesiliyor; geçmiş aynı kalmalı. Trend, momentum, düşük oynaklık, endeks trendi, ay dönümü ve motor kapsanıyor. | ✅ uyumlu | `tests/test_no_lookahead.py` (iki değişken: scrambled, truncated) |
| 2 | Momentum ve düşük oynaklık için "kesilmiş geçmiş" değişkeni kapalı (`truncation_ok=False`). Kesme günü ay sonuna denk geldiğinde sinyal farklı çıkıyor. Bu bir geleceğe bakma değil: aylık yeniden dengeleme günü, geçmişin ne kadar olduğuna göre değişiyor. Ama testle kanıtlanmış değil. **Kapanış (19.11.2026 15:35, v0.99.153, dal `claude/vd2-1911`):** test açılınca 6 kesmeden 5'inde kırmızı oldu (66c4a6b). Neden: ay sonu günü verinin o aydaki son mumuydu; kesilmiş geçmişte en yeni mum ay sonu sayılıyordu. Düzeltme: ay sonu seans takviminden (`session_calendar`), endeks trendindeki gibi (619d04d). Etki, yalnız sentetik test verisinde: düşük oynaklıkta en yeni günün 2 sinyal satırı, momentumda 0; işlem ve özsermaye aynı (ölçüm: eski `rules.py` 66c4a6b ile yenisi aynı fixture üzerinde `run_backtest(max_positions=4)`; çıktı: "momentum differing signal rows: 0 | equity equal: True trades: 38 38", "low_vol differing signal rows: 2 days: [2026-10-23] | equity equal: True trades: 31 31"). Kırmızı takım (19.11): geçmiş günlerin hiçbiri değişmiyor; test eski kodda 10 kırmızı, yenide yeşil. Teste gerçek ay sonu kesmesi (31.03.2026) eklendi. Bayram arifesi kesmesi test edilemedi: sentetik fixture tatil günlerinde de mum içeriyor (27–29.05.2026); bu yalnız test verisinin kusurudur. K-93 (günlük görünümler), K-94 (kâğıt defter), sabah tablosu ve aday listeleri bu kuralları kullanmıyor. **Açık kalan:** aynı kalıp `_monthly_lowest`'ta (a4 H4/H5: `equal_weight_signals`, `low_turnover_signals`) duruyor. a4 ön kaydının koduna dokunulmadı; düzeltilip düzeltilmeyeceği karar talebidir (18.12 paketi). | ✅ kapandı (#2) / ⚠️ ORTA (a4 kalıbı) | `tests/test_no_lookahead.py` `test_momentum`, `test_low_volatility`; `core/strategy/rules.py` `_month_end_sessions` |
| 3 | `expectations.view_excess` ve `rules.turn_of_month_signals` içindeki `shift(-1)` kullanımları sonuç etiketi (ertesi açılıştan giriş) ve seans takvimidir. Sinyal girdisi değildirler. Ay dönümü kesilmiş testi geçiyor. | ✅ uyumlu | `core/backtest/expectations.py:55`, `core/strategy/rules.py:282`, `test_turn_of_month` |
| 4 | Temel analiz verisi (bilanço, F/K) araştırma ve backtest kodunda hiç kullanılmıyor. Bilanço yayım tarihi riski bugün yok. Ancak kullanılmaya başlanırsa, yayım tarihine göre hizalama zorunlu olmalı. | ✅ bugün yok / ileride DÜŞÜK | `core/backtest` ve `core/strategy` içinde `fundamentals` geçmiyor |
| 5 | Endeks üyeliği zamana sadık: Q2 2022'den beri her çeyrek değişikliği kaynağıyla kayıtlı; her gün tam 100 üye olduğu denetleniyor. a4 tarama dönemi (2023-08 →) bu aralığın içinde. | ✅ uyumlu | `core/market/membership.py`, `tests/test_membership.py` |

## D-2 Hayatta kalan yanlılığı
| # | Bulgu | Sınıf | Kanıt |
|---|---|---|---|
| 6 | Q2 2022'den beri BIST 100'den çıkan 136 hisseden 134'ünün fiyatı veritabanında var. Evren sonradan çıkanları içeriyor. | ✅ büyük ölçüde uyumlu | `d2_kontrol.py` çıktısı: 136 / 134 |
| 7 | 2 hissenin fiyatı yok: IPEKE ve KERVT. Kod değişikliği ya da birleşme olabilir; doğrulanmadı. Bu iki hisse üyeyken geçen günlerde evren 100'den eksik hesaplanıyor olabilir. | ⚠️ ORTA | aynı çıktı |
| 8 | Endeksten çıkan hisselerin son fiyat günü 28.10.2026. Fiyat güncellemesi yalnız güncel listeyi kapsıyor. a4'ün ileri verisi (02.11'den itibaren) için sorun şu: bir hisse ileride endeksten çıkarsa, tutulduğu ayın kalan fiyatları gerekir. | ⚠️ ORTA (ileri ölçüm) | aynı çıktı: en erken son günler 28.10 |
| 9 | Borsadan tamamen çıkan (kote olmaktan çıkan) hisse ile yalnız endeksten çıkan hisse ayrımı tutulmuyor. | ℹ️ BİLGİ | — |

## D-4 Veri soy ağacı
| # | Bulgu | Sınıf | Kanıt |
|---|---|---|---|
| 10 | Araştırma geçmişinde (`history.csv`) kod sürümü ve veri özeti (hash) alanı yok. Bir sonucun hangi veriyle üretildiği bugün izlenemiyor. | ⚠️ YÜKSEK (ARS-1 D-4, ANAYASA Md. 12) | `core/backtest/history.py:28` FIELDS |
| 11 | Saatlik ölçüm için veri kesiti dondurma var: görüntü klasörü ve iki çalıştırmanın birebir karşılaştırması. Bu, istenen soy ağacının bir örneği. | ✅ kısmi | OPERATIONS §7c, K-76 |
| 12 | Yeni deney kaydı (Faz A) veri özeti alanını zorunlu tutuyor (`veri_ozeti`). İleriki deneyler bu sorunu taşımaz. | ✅ yeni araç | `core/research/experiments.py` (`claude/faz-a2-1911`) |

## Düzeltme önerileri (risk sırasıyla; uygulama sonraki gecelerde, önce kırmızı test)
1. **(YÜKSEK, #10)** `history.csv`'ye kod sürümü ve veri özeti sütunları eklensin. Kayıt biçimi değişikliğidir; ALONE olabilir ve kapı kontrolü 7'ye takılır. Hafta sonu sahibin komutuyla girer.
2. **(ORTA, #8)** Endeksten çıkan hisselerin fiyatı, en az ilgili ileri ölçüm penceresi boyunca güncellenmeye devam etsin. Fiyat güncelleme davranışını değiştirir; yetki devri 2. sınıf, sahibin "evet"i gerekir.
3. **(ORTA, #7)** IPEKE ve KERVT için kod değişikliği ya da birleşme kaydı KAP'tan doğrulansın ve `corporate_actions` ya da eşleme tablosuna yazılsın. Veri kaydıdır; sonuç görülmeden yapılır.
4. **(ORTA, #2)** Momentum ve düşük oynaklık için kesilmiş geçmiş testi, aylık yeniden dengeleme gününü sabitleyerek açılsın. Yalnız test işidir (1. sınıf).
5. **(BİLGİ, #9)** Kote olmaktan çıkma bilgisi, KT-09 ve D-2'nin sonraki sürümüne bırakılır.

**En önemli 3 bulgu:**
- #10: soy ağacı yok;
- #8: endeksten çıkanların fiyatı 28.10'da durmuş;
- #7: 2 hissenin fiyatı yok.

**Not (ARS1_UYUM düzeltmesi):** Çelişki tablosunda S-3 (DSR, PBO) "yeni" yazılmıştı. Bu yanlış. Deflated Sharpe ve PBO, K-81 ile `core/backtest/overfit.py`'de zaten var; araştırma raporunda yalnız bilgi olarak gösteriliyor ve özellik testleri mevcut. Eksik olan iki şey var: PSR ve yayımlanmış bir sayıyla doğrulama. Faz B bunları yapacak. Düzeltme yeni bir satır olarak `ARS1_UYUM_1911.md`'ye eklendi.
