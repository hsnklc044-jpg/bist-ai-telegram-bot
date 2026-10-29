# QuantBIST yol haritası ve açık sorunlar

Son doğrulanmış nokta, ardından önceliklendirilmiş işler. Her sürümden sonra
güncellenir; tamamlanan iş, kanıtıyla birlikte "Doğrulanmış durum" bölümüne taşınır.

## Ana yönetim belgesine göre durum (docs/CHARTER.md, 27.10.2026)

CHARTER tek kaynaktır (önceki "sürekli yol haritası"nın yerini aldı). Her turda karar algoritması (CHARTER §4) izlenir; kararlar DECISIONS.md'de.

| Aşama | Konu | Koşul | Durum |
|---|---|---|---|
| A | Dayanıklılık | her zaman | A1 v0.48.4; A2 (uyku/uyanma, geç internet, DNS, Telegram 429/5xx, kilitli dosya, yarım satır, disk dolu, saat değişimi, eşzamanlı çalıştırma) v0.49.0–v0.50.0; A3 OPERATIONS §8 (kimin işi sütunuyla) — **tamam** |
| B | Gözlemlenebilirlik | kod hemen | B1 SLO ölçümü v0.51.0 (/durum + cuma raporu; doğruluk ve kalite 'bilinmiyor' → C1 ve I); B2 izleme satırı v0.49.1 (aktivasyon: kullanıcının .env adımı); B3 çalıştırma log satırı v0.51.1 — **tamam** (aktivasyon hariç) |
| C | Veri bütünlüğü | kod hemen | C3 lookahead/survivorship testleri var (test_no_lookahead, geçmiş üyelik); C1 ikinci kaynak→SLO v0.52.0 (haftalık özet `crosscheck/latest.json`, /durum'da 'Veri doğruluğu', araştırmada `--exclude-suspects`); C2 haftalık kurumsal işlem taraması v0.52.1 (araştırmada `quality --recent 14`) — **tamam**; bulguların KAP doğrulaması her hafta (D) |
| D | Gerçek ortam gözlemleri | olay olunca | bekliyor: 28.10 yarım gün, 29.10 tatil, 30.10 canlı ölçüm + ilk haftalık sistem özeti, 31.10 araştırma |
| E | Felaket kurtarma | kod hemen | E1 ve E3 v0.53.0 (docs/DISASTER_RECOVERY.md; adımları test_disaster_recovery denetler); E2 aylık tatbikat yerel otomasyonun işi (komut belgede) — **tamam** |
| F | Altyapı kararı | ≥1 haftalık kayıt ya da SLO tutmazsa | bekliyor (03.11 sonrası) |
| G | Araştırma | yazılım/dayanıklılık/veri işi bitince | **açık/engelli**: veri 2015'e uzatma için kaynaklı üyelik listesi yok (DECISIONS K-16); mevcut veriyle güç düşük |
| H | Canlı ölçüm kararı | yeterli bağımsız veri | bekliyor (Kasım sonu) |
| I | Güvenlik ve bağımlılıklar | kod hemen | I1 haftalık pip-audit, I2 gizli bilgi testi v0.54.0; I3 kural DECISIONS'ta; kapsam kapısı %91 ve kalite SLO'su v0.54.1 — **tamam** |
| J | Bakım ve devir | yazılım işi bitince | J1 HANDBOOK, J2 MAINTENANCE, J3 /durum 'Bakım takvimi', J4 CHANGELOG v0.55.0 — **tamam** |

Öz-denetim (CHARTER §7): her 10 sürümde bir. İlk denetim 27.10 (v0.50.0–v0.55.2, 11 sürüm); sayaç v0.55.3'ten yeniden başlar.

**Öz-denetim 27.10.2026 bulguları** (önem sırasıyla)
| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö1 | YÜKSEK | "Bakım takvimi" yalnız ayın 1'ini dönem başı sayıyordu; dönemler çeyreğin ilk işlem gününde başlıyor (2023-01-02, 2026-01-02…). Ocak 2027 değişikliği 04.01 ile girilince /durum kalıcı "girilmedi" uyarısı verecekti | ✅ v0.55.3 (`QuarterlyReviewDateTest`) |
| Ö2 | YÜKSEK | SLO'lar kayıt başlamadan önceki günleri "eksik" sayıyordu (PC'de %25) | ✅ v0.55.2 (K-15) |
| Ö3 | DÜŞÜK | `logs/monitoring.json` iki süreçten (bot, rapor görevi) aynı `.tmp` adıyla yazılıyor; çakışırsa biri kaydedilmez (OSError yakalanıp loglanır), izleme satırı bir sonraki sinyalde düzelir | ✅ v0.60.1: her süreç kendi geçici dosyasıyla yazar (`test_ping.ConcurrentStateWriteTest`) |
| Ö4 | DÜŞÜK | `logs/heartbeats.csv` sınırsız büyür (~3 MB/yıl) ve /durum her seferinde tamamını okur | kabul; yıllık bakımda (MAINTENANCE) gözden geçirilir |
| Ö5 | BİLGİ | Cuma raporu SLO tablosu için iki GitHub sorgusu yapar (10 sn zaman aşımı); internet yoksa "bilinmiyor" | beklenen davranış |

Saat dilimi, sessiz hata yutma, belge-kod uyumu: bugün eklenen kod (slo, health, daily, runs, ping, crosscheck, quality) tarandı; başka bulgu yok.

**Öz-denetim 2 — 27.10.2026, erken (v0.55.3 → v0.59.0, 7 sürüm)**. Sürüm sayısı 10'u bulmadan yapıldı: gün içinde rapor yolu (`daily`), yedek komutu, kurulum betiği ve araştırma veri girişi değişti. Kapsam: `git diff 41f6efe..3cc4544 -- core bot scripts .github` (9 dosya, +264 satır).

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö6 | ORTA | İkinci kaynak mesajı (v0.58.0) Yahoo yalnız *gecikmişse* de gidiyordu; rapor sonra gelirse aynı akşam iki mesaj olurdu | ✅ v0.59.3: yalnız Yahoo XU100 için cevap vermediyse (`failed`/`empty`) gider; cevap verip bugünün mumu yoksa beklenir (`test_second_source.…test_yahoo_only_late_sends_nothing`) |
| Ö7 | DÜŞÜK | İş Yatırım da çökmüşse o deneme rapor görevine ~3 dk ekler (3 deneme × 60 sn) | ✅ v0.60.1: bilgi mesajı için tek deneme, en çok bir zaman aşımı (`test_second_source.SecondSourceTriesOnceTest`) |
| Ö8 | ORTA | Beş iş akışı research-results'a tek seferlik `git push` yapıyordu. Uzun süren haftalık araştırma sırasında başka biri (kaynak arşivi, veri kontrolü, tatbikat) push ederse araştırmanın push'u reddedilir; haftanın sonuçları ve "Veri doğruluğu" SLO'sunun okuduğu `crosscheck/latest.json` kaybolurdu. Ayın 3'ü cumartesiye denk gelince tatbikat (07:41) araştırmayla (07:17) çakışabilir | ✅ v0.59.1: hepsi rebase + 3 deneme (`test_results_push`) |
| Ö9 | BİLGİ | Holdout kesimi verisi olmayan sembolde (KPOWR) bozulur mu? | denendi, bozulmuyor; regresyon testi eklendi (`test_holdout`) |

Kontrol edilenler: yeni hata yolları (rapor metni yazılamazsa, ikinci kaynak/Telegram çökerse, geri yükleme testi başarısızsa) raporu durdurmuyor ve sessiz değil (log); kişisel kayıtlara yazan yeni kod yok; adres/token yazdıran yeni satır yok (`ping --drill`); testler gerçek `data/`, `logs/`a dokunmuyor (yazma koruması, v0.56.3'te bir kez yakaladı ve düzeltildi). **Kritik ya da yüksek bulgu yok.** İlk değerlendirmede DÜŞÜK sanılan Ö8 kontrol edilince ORTA çıktı ve düzeltildi.

**Öz-denetim 3 — 27.10.2026 (v0.59.2 → v0.63.0, 9 sürüm)**. Kapsam: `git diff d96afd7..baea6ec -- core bot scripts .github` (14 dosya, +564 satır): izleme adresi denetimi, ikinci kaynak mesajı, sapma işareti, /rapor_tekrar ve düğmeler, KAP takibi, /yil.

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö10 | DÜŞÜK | KAP bir hafta için liste yerine hata nesnesi döndürürse ya da tarih biçimini değiştirirse haftalık KAP kontrolünün tamamı çöküyordu; atlanırsa da sessiz kalacaktı | ✅ v0.63.1: o aralık/bildirim atlanır ve çıktıda "⚠️ Eksik kontrol: …" yazar (`test_kap.UnexpectedAnswerTest`) |
| Ö11 | BİLGİ | KAP kontrolü güncel evreni (`universe.csv`) tarar; evren dışından alınmış bir hisse kapsanmaz | kabul: haftalık sıçrama taraması (`corporate.txt`) ve `/durum` veri notları aynı evrene dayanıyor; evren dışı pozisyon olursa evrene eklenir |
| Ö12 | BİLGİ | `/start` düğmelerindeki `is_persistent` eski python-telegram-bot sürümlerinde yok; olsaydı bot açılmazdı | denendi: kilitli sürüm 22.8, destekleniyor |

Kontrol edilenler: yeni komutlar yalnız okur (/rapor_tekrar, /yil); kullanıcı tarihi dosya yoluna yalnız `date` olarak girer (yol enjeksiyonu yok); `/yil` defteri yükleme anında doğrular (tutarsız geçmiş yükleme hatası verir); KAP'tan gelen hiçbir şey veriye yazılmaz (K-24); menü kurulamazsa bot açılır; testler gerçek `data/`, `logs/`a dokunmaz. **Kritik ya da yüksek bulgu yok.**

**Öz-denetim 4 — 28.10.2026 (v0.64.0 → v0.71.0, 9 sürüm)**. Kapsam: `git diff 620cf78..897738c -- core bot scripts .github`: /stres, cuma grafiği, kapanış alarmı (yüzde dahil), a4 kuralları ve tarih kapısı, depodaki güncelleyici, sapma nedenleri, sunucu kararı hesabı. v0.66–v0.68 ayrıca v0.68.1'de tarandı (iki düzeltme).

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö13 | ORTA (doğruluk) | Sunucu kararı hesabı yalnız aynı bot sürecindeki boşlukları (uyku) PC'ye yazıyordu; gece **kapanan** PC'de bot yeni süreçle açılır, kayıp PC'ye sayılmıyordu. K-23 "kapalı/uykuda" diyor; karar yanlışlıkla "PC'de kalınır" çıkabilirdi | ✅ v0.72.0: 20 dakikadan uzun her boşluk da PC'nin (botun kendi yeniden başlatmaları 3×5 dk); `test_server_decision.DecisionTest.test_a_pc_switched_off_every_night_counts_too`, hızlı yeniden başlama sayılmaz (`test_a_quick_bot_restart_is_not_the_pc`) |
| Ö14 | DÜŞÜK | Sunucu kararı 13.11 raporunda çıkar; o rapor gitmezse karar da gelmez | kabul: komut satırı (`python -m core.reports.server_decision`) ve 14.11 kontrolü; karar zaten 14.11 dönem değerlendirmesinde yazılır |
| Ö15 | BİLGİ | `/alarm THYAO altında 1.240` noktayı ondalık okur (1,24) | kabul: onay mesajı seviyeyi açıkça yazar; README'de 1.000 TL üstü için rakamı noktasız yazma notu |
| Ö16 | BİLGİ | Araştırmadaki a4 adımı (27.04.2027'den sonra) hata verirse çalışma kırmızı olur ve sonraki adımlar atlanır | kabul: ilk gerçek çalışmanın sessiz kalmaması tercih; `/durum` kırmızı araştırmayı gösterir. Aşama 3 adımı aynı biçimde |

Kontrol edilenler: güncelleyici geri sürüm kurmaz, kırmızı/süren CI'ı kurmaz, sürüm ve zip aynı commit'ten; depoya gizli bilgi girmedi (`bildir.py` token'ı .env'den okur, `test_guncelle.BildirTest`); alarm tetiklenmesi rapor gittikten sonra yazılır, `--force` ile tekrar söylenmez; a4 ve sapma nedenleri ileriye bakmaz; testler gerçek `data/`, `logs/`a dokunmaz. **Kritik ya da yüksek bulgu yok.**

**Öz-denetim 9 — 29.10.2026 (v0.95.5 → v0.98.0, 10 sürüm).** Kapsam: `git diff 7b7480b..5a0eeaf -- core bot .github`:
- kur süre sınırı ve ikinci kaynak;
- eleme canlı ölçümü;
- İş Yatırım'ın kapatılması;
- senaryolar (şablonlar, karne, canlı kayıt, `/tara senaryo`);
- risk bütçesi.

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö35 | DÜŞÜK | Senaryolarda "2R" hedefi, giriş bilinmeden hesaplandığı için sinyal günü kapanışıyla kuruluyor (giriş + 2 × risk yerine kapanış + 2 × risk). Ertesi açılış farklıysa gerçek R 2'den biraz sapar. | kabul: hedef sinyal günü sabitlenmeli (geleceği görmemek için); K-55'e not olarak düşüldü. |
| Ö36 | BİLGİ | Kapsam %92,4'ten %91,6'ya indi; kapı %91. Yeni modüllerin hata yolları (ağ, bozuk dosya) kısmen testsiz. | açık: sonraki sürümlerde hata yolu testleri eklenecek. |
| Ö37 | BİLGİ | Cuma karnesi (senaryolar) akşam raporunun ardından bütün geçmişle hesaplanıyor. GitHub'da 26 sn sürdü; PC'de birkaç dakika sürebilir. Rapor zaten gönderilmiş oluyor. | kabul: rapor görevinin 30 dakikalık sınırı içinde. |
| Ö38 | BİLGİ | `datacheck.yml` iş akışı İş Yatırım kapalıyken yalnız kapalı olduğunu yazıyor. | kabul (D13). |

**Kontrol edilenler:**
- **Geleceği görme yok.** Senaryo sinyalleri (test), karne holdout'u (test), rejim, TÜFE ve eleme ölçümü.
- **Testlerde ağ ve kişisel dosya yok.** Kur, TÜFE, sınır, senaryo kaydı, karne önbelleği ve eleme kaydı geçici klasörde. Yazma koruması testi geçiyor.
- **Hiçbir çıktıda öneri dili yok** (test). `/risk ekle` ve `/risk denge` emir oluşturmuyor; senaryolarda sanal emir yalnız `/paper` ile.
- **Gerçek ve sanal hesap karışmıyor** (`account_state` tek hesap okuyor).
- **Yeni kişisel dosya** `risk_limits.csv` yedekte, şema denetiminde ve git dışında (test).

**Kritik ya da yüksek bulgu yok.** Sayaç v0.98.0'da sıfırlandı.

**Öz-denetim 8 — 29.10.2026 (v0.91.2 → v0.95.3, 10 sürüm).** Kapsam: `git diff 8d98938..4131e34 -- core bot .github`:
- 2027 tatil takvimi ve geçici yıl uyarısı;
- dört bazlı sonuç (`macro.py`, rapor, `/performans`, araştırma);
- rejim ve `/piyasa`;
- `/tara rejim=`;
- araştırma iş akışındaki kur önbelleği.

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö27 | ORTA | `/tara ... rejim=` canlı listede fiyatı olmayan bir hisse (boş ya da `None` tablo) varken rejim hesabında çöküyordu. Komut hata verirdi. | ✅ v0.95.4: verisiz hisseler rejim hesabından çıkarılıyor (`test_screen_regime`). |
| Ö28 | DÜŞÜK | Rejim değişince `rejim=` filtreli abonelik "Çıkanlar: hepsi" diyordu ama nedenini yazmıyordu. | ✅ v0.95.4: mesaj bugünkü rejimi ve filtreyi yazıyor (`test_screen_subscriptions`). |
| Ö29 | DÜŞÜK | PC 14 günden uzun kapalı kalırsa kur önbelleğinde boşluk olur. O günler için bir önceki kur kullanılır: eski bir kur, ama geleceği görme yok. | kabul: `python -m core.market.macro --usd TARİH` doldurur; `/durum` kur 5 günden eskiyse uyarır. |
| Ö30 | BİLGİ | 2027 geçici kalırsa `/durum` Aralık'tan itibaren uyarır. Teyit için kod sürümü gerekir (`calendar.PROVISIONAL`). | kabul: MAINTENANCE'ta Aralık işi. |
| Ö31 | BİLGİ | Geçmiş TÜFE yayım tarihleri kuraldan geliyor (iki kaynaklı istisna). Bilinmeyen başka bir erteleme olduysa değer birkaç gün erken görünmüş olabilir. | kabul: K-52'de sınır olarak yazılı; birincil ölçüt bunu kullanmıyor. |
| Ö34 | YÜKSEK (bulundu, zarar yok) | Gerçek veride ilk araştırma raporunda XU100'ün USD getirisi +%383 çıktı, doğrusu yaklaşık +%56. Yarı dolmuş kur önbelleğinde bitiş günü için aylarca eski kur kullanılmıştı. Bu yalnız deneme çalışmasında görüldü; PC'de önbellek son iki haftayla dolduğu için rapor etkilenmedi. | ✅ v0.95.7: 10 günden eski kur hiçbir zaman kullanılmıyor ("kur yok"). Önbellek önce dönemin iki ucunu dolduruyor. Doldurma başlangıcı araştırmanın başlangıcına bağlandı. |
| Ö32 | DÜŞÜK | Yahoo ile ikinci kaynak kur karşılaştırması (K-51) henüz yok. | ✅ v0.95.6: akşam raporu karşılaştırıyor, `/durum` %1 üstünde uyarıyor. |
| Ö33 | YÜKSEK (bulundu, zarar yok) | Araştırmadaki kur adımı ilk çalışmada bütün geçmişi sınırsız istiyordu. TCMB'de bir istek ~1,6 sn sürdüğü için adım 33 dakikayı geçti. İşin 90 dakikalık sınırıyla cumartesi araştırması sonuç kaydedilmeden kesilebilirdi. Elle başlatılan deneme çalışmasında görüldü ve iptal edildi; kayıt etkilenmedi. | ✅ v0.95.5: süre sınırı (araştırmada 8 dk, adım sınırı 10 dk; raporda 30 sn), 50 bültende bir ara kayıt; önbellek haftadan haftaya dolar. |

**Kontrol edilenler:**
- **Geleceği görme yok.** TÜFE yayımın ertesi gününden önce görünmüyor (test). Rejim etiketinde gelecek değişince geçmiş değişmiyor (test). Karne, etiketleri tarama dönemi sonunda kesilmiş veriyle hesaplıyor; holdout'a girmiyor.
- **Testlerde ağ yok.** `conftest` TCMB isteklerini kapatıyor ve kur dosyalarını geçici klasöre yönlendiriyor.
- **Depoya kişisel ya da önbellek dosyası girmiyor.** `usdtry.csv` ve `cpi_local.csv` git dışında. `cpi.csv` kaynaklı kamu verisi; TCMB şartı kaynak gösterilerek kullanıma izin veriyor.
- **Yeni ek satırlar raporu durdurmuyor.** Hata olursa log'a yazılıp atlanıyor.
- **Hiçbir yeni metinde öneri kelimesi yok** (test).

**Kritik bulgu yok.** İki yüksek bulgu (Ö33, Ö34) gerçek çalışmada bulundu ve v0.95.5 ile v0.95.7'de kapatıldı. Sayaç v0.95.4'te sıfırlandı.

**Öz-denetim 7 — 28.10.2026 (v0.87.0 → v0.91.1, 11 sürüm).** Kapsam:
- eleme filtreleri ve karnede gün gün uygulanması;
- D11 (tek `report_due_day`), D12 (karne sırası, yavaş makine CI işi);
- profesyonel şablonlar ve evren içi sıra;
- temel veri deposu;
- veri borcunun kapatılması (yeni `reduction_rights` türü, `candle_exceptions`, KERVT→BESLR, KPOWR).

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö22 | DÜŞÜK | Eleme, `corporate_actions.csv`'yi süreç başına bir kez okur. PC'de dosya elle değiştirilirse çalışan bot yeniden başlayana kadar eski satırları kullanır. | kabul: güncelleyici her kurulumda botu yeniden başlatır; satırlar yalnız depodan gelir |
| Ö23 | DÜŞÜK | BJKAS 07.04.2025'te ikinci kaynakla bir günlük ~10 puanlık artık fark | açık, belgeli (DATA_CORRECTIONS); tek gün, hükümleri etkilemez |
| Ö24 | DÜŞÜK | `/durum` "Temel veri" satırı veri gelince de hep BİLGİ; eskimiş temel veri uyarı vermez | açık: ilk gerçek veri içe aktarıldığında "son yayın 120 günden eski" uyarısı eklenecek |
| Ö25 | BİLGİ | Yavaş makine işi CI süresini yaklaşık 5 dakika uzatıyor | kabul: D12 türü hataları yakalamanın bedeli |
| Ö26 | BİLGİ | D13 (İş Yatırım robots.txt) kullanıcı kararı bekliyor; ikinci kaynak doğrulamaları bu arada aynı düşük hacimle sürüyor | açık: kullanıcı kararı |

**Kontrol edilenler:**
- **Elemeler geleceği görmez.** Kurumsal işlem yalnız işlem gününden itibaren 60 seans eler, öncesini değil (test). Karne, eleme kesimi ve holdout kesimiyle birlikte çalışır.
- **Liste ve karne aynı tanımı kullanır.** Sıra alanları liste, karne ve açıklamada ortak fonksiyondan gelir.
- **`report_due_day` dört kontrolde ortak.** Yarım gün, tatil ve hafta sonu testli.
- **Karne mesajı listeden sonra gider.** Liste adımı hata verse de karne asılı kalmaz (test).
- **Temel veri modülünde ağ kodu yok** (test). Yayın akşamı kullanılmaz.
- **Yeni veri satırlarının hepsi kaynaklı.** Kaynaksız satır okunmaz. İkinci kaynakta 11.954 hisse-günde açıklanamayan fark 2 gün.
- **Zamana bağlı testler tarandı.** Kalan `sleep` ya da duvar saati ölçümü yok; hız testi CPU süresi ölçüyor.
- **Kişisel dosyalar** (yeni `screen_subscriptions`, `screen_virtual`, `fundamentals`) yedekte ve şema denetiminde; git'e girmez.

**Kritik ya da yüksek bulgu yok.** Sayaç v0.91.2'de sıfırlandı.

**Öz-denetim 6 — 28.10.2026 (v0.80.0 → v0.86.1, 10 sürüm) = profesyonel talimatın EVRE 0'ı.** Tam rapor: [AUDIT.md](AUDIT.md).

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| D1 | YÜKSEK | /tara karnesi, araştırmanın dışarıda bıraktığı hisseleri (çözülmemiş ±%20 sıçrama, kısa geçmiş) kullanıyordu | ✅ v0.87.0 |
| D2 | ORTA | Canlı liste yakın tarihli sıçramalı hisseyi eleyemiyor (CVKMD 03.08) | açık → profesyonel filtreler Aşama 1 |
| D3 | ORTA | Sıfır hacim göreli hacimde 1,0 ile dolduruluyor (SASA 151 gün) | açık → Aşama 1 veri elemesi; tanım değişikliği ayrı karar |
| D4 | ORTA | 10 hissede 15 sıçrama `corporate_actions.csv`'de yok | açık: KAP'la tek tek |
| D5 | DÜŞÜK | Veri lisansları belgesiz | açık → Aşama 3 |
| D6 | DÜŞÜK | Eski commit'te sohbet kimliği ve eski izleme listesi | kabul (geçmiş yeniden yazılmaz) |
| D7 | DÜŞÜK | Haftalık paket taraması hiç çalışmamıştı | ✅ 28.10 temiz |
| D8–D10 | BİLGİ | KPOWR verisiz; tatil dosyası yalnız 2026; likidite bugünü içeriyor | açık, AUDIT.md |

**Öz-denetim 5 — 28.10.2026 (v0.73.0 → v0.79.0, 10 sürüm).** Kapsam: KAP metin aracı, SKBNK düzeltmesi, kanıt dosyası (triage), /tara motoru, Telegram arayüzü, dürüst karne, evren düzeltmesi.

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| Ö17 | ORTA (tutarlılık) | Liste likidite tabanını uyguluyordu, karne uygulamıyordu: karne listede hiç görünmeyecek sığ hisselerin olaylarını da sayıyordu (kullanıcının "liste ve karne aynı evrende olsun" bulgusuyla aynı tür) | ✅ v0.80.0: karne tabanı o günün 20 günlük işlem hacmiyle uygular (`test_screen_card.AuditFiveTest`) |
| Ö18 | DÜŞÜK | `logs/screen_cards.json` her yeni kriterle sınırsız büyüyordu | ✅ v0.80.0: en yeni 500 karne tutulur |
| Ö19 | DÜŞÜK | Karne evren olarak her zaman o günkü BIST 100 üyelerini alır; `evren=izleme/quantbist` listesinde karne o evrene daraltılmaz | kabul: karne başlığı bunu yazar; izleme listesi gibi küçük evrende karne örneği anlamsız küçülür |
| Ö20 | BİLGİ | `/tara` oturumu (`/tara_devam`, düğmeler) bellekte; bot yeniden başlarsa unutulur | kabul: cevap "Önce /tara" der; kişisel kayıt değildir |
| Ö21 | BİLGİ | Bot üzerinden giden testler gerçek `signal_log`'a yazabiliyordu | ✅ v0.78.0'da bulunmuştu (yazma koruması), conftest kalıcı yönlendiriyor |

Kontrol edilenler: ayrıştırıcıda eval/exec yok, izin verilen karakter kümesi dışı her şey reddedilir; holdout karnede iki yerde kesilir (kesim kaldırılınca test kırmızı); giriş ertesi açılış; düğmeler yalnız izinli sohbete cevap verir; KAP'tan gelen hiçbir şey kendiliğinden veriye yazılmaz (SKBNK elle, kanıtla); ATR/ADX hızlı sürümleri kütüphaneyle bit bit aynı. **Kritik ya da yüksek bulgu yok.**

## Özellik ve yönetişim paketi C, D, E, F (kullanıcı, 28.10.2026)

Kapıların okunuşu DECISIONS K-51'de: Talimat 1 = Özellik A, Talimat 2 = Özellik B. Kullanıcı başka belgeyi kastediyorsa tarihler değişir. Koşulu oluşmamış iş için boş iş üretilmez.

### C – Piyasa bağlamı ve reel getiri
- **Koşul:** ✅ **açıldı** (kullanıcı, 28.10 akşamı; K-52).
- **Yapılan:**
  - ✅ v0.95.0: dört bazlı sonuç (`core/market/macro.py`; günlük rapor, `/performans`, `/durum` "Makro veri"); TÜFE ve kur kendiliğinden güncelleniyor.
  - ✅ v0.95.1: rejim etiketi, genişlik ve dört ana sektör (`core/market/regime.py`, `/piyasa`); sektör endeksleri akşam güncellemesinde.
  - ✅ v0.95.2: `/tara` `rejim=` filtresi (liste ve karne).
  - ✅ v0.95.3: araştırma raporunda dört baz. Haftalık araştırma TCMB kur bültenlerini önbellekle dolduruyor.
  - ✅ v0.95.5–v0.95.6: kur önbelleğine süre sınırı; Yahoo ile ikinci kaynak kur karşılaştırması.
- **Kalan:**
  - sektör kısmı: hisse sektörü, `/analyze` sektör satırı, `/tara` `sektor` ve `sektor_goreli_guc`. Kaynak kararı kullanıcıda (D14).
  - PC kanıtı: bu sürümlerin PC'de bir akşam raporu ve `/piyasa` ile çalıştığının görülmesi. Sektör endekslerinin Yahoo'da gelip gelmediği de bu kanıtla görülecek.
- **En erken:** kod 31.10 (30.10 akşam kanıtı gelirse).
- **Bitti ölçütü:**
  - nominal / reel / USD / nakit sonuçları günlük raporda, `/performans`'ta ve araştırma raporunda;
  - `/piyasa` çalışıyor; sektör bilgisi `/analyze` ve `/tara`'da (`sektor`, `sektor_goreli_guc`, `rejim`);
  - kaynaklar DATA_SOURCES.md'de, tazelikleri `/durum`'da;
  - elle hesaplanmış reel/USD testleri; TÜFE yayımından önce görünmez testi.

### D – Olay takvimi ve KAP izleme
- **Koşul:** C ile aynı (A'nın bitti ölçütü). Ek ön koşul: KAP kullanım koşulunun teyidi (K-48); teyit yoksa yalnız mevcut elle/Actions yolu kullanılır.
- **En erken:** kod 31.10. Bitti ölçütü en az 10 iş günü PC kanıtı istediği için kapanış en erken ~14.11.
- **Bitti ölçütü:**
  - günlük raporda "📅 Yaklaşan olaylar (7 gün)" ve "📰 Bugünkü KAP bildirimleri";
  - KRİTİK olay ayrı mesajla, bir kez; `/takvim` çalışıyor;
  - kurumsal işlem önerisi (onayla) ve `/trade` uyarısı test edilmiş;
  - en az 10 iş günü PC'de çalışmış; kaçırılan bildirim yok, varsa nedeni yazılı.

### E – Portföy risk bütçesi ve yapı analizi
- **Koşul:** ✅ açıldı (K-54). Sektör sınırı kaynak olmadığı için etkin değil.
- **Durum:** ✅ tasarım K-56 (575237e, sonuçtan önce); ✅ v0.98.0 `/risk`, `/risk ekle`, `/risk denge`, günlük rapor satırı, `alerts_log` uyarıları, web `/risk/{hesap}`, HANDBOOK §13 örnek dosyayla. Kalan: web panelinde grafik (sektör ağırlığı yok; risk katkısı grafiği sonraki iş).
- **En erken:** C bittikten sonraki gün. C'nin süresi ve sektör kaynağı kararı (D14) belli olmadığından tarih yok.
- **Bitti ölçütü:**
  - `/risk [gerçek|sanal]`, `/risk ekle`, `/risk denge` ("hesap sonucu, öneri değil") testleriyle çalışıyor;
  - sınır uyarıları `alerts_log`'a giriyor ve tekrar etmiyor;
  - `data/risk_limits.csv` kişisel ve yedekte; HANDBOOK'ta örnek dosyalı "risk bütçemi nasıl tanımlarım" bölümü var.

### F – Model riski yönetimi ve bağımsız doğrulama
- **Koşul:** F1 envanteri hemen; gerisi B'nin bitti ölçütünden sonra.
- **Durum:** F1 ✅ docs/MODELS.md (29 model, 11'i yüksek risk). F kapısı açıldı (K-58). ✅ v0.99.1 `/durum` "Model doğrulama" ve MAINTENANCE takvimi. F2: ilk üç bağımsız doğrulama (M15, M14, M11) alt ajanlarla sürüyor.
- **En erken:** B'nin kapısı A'nın bitti ölçütüne bağlı. B'nin kendi bitti ölçütünde canlı kayıt olduğundan F2+ Kasım'dan önce açılmaz.
- **Bitti ölçütü:**
  - MODELS.md eksiksiz;
  - bütün yüksek riskli modellerin bağımsız doğrulama raporu (`docs/validation/<model>.md`; ayrı oturum ya da alt ajan);
  - değişiklik kontrolü sürüm notlarında işliyor;
  - izleme eşikleri `/durum`'da;
  - doğrulama takvimi MAINTENANCE.md'de.

## Kaldığım yer (27.10.2026, kod v0.56.0)

- **Son sürüm:** v0.99.3 (M11 stop düzeltmesi). Öz-denetim sayacı: v0.98.0'dan beri 5.
- **Bağımsız doğrulama bulguları (F3, önem sırasıyla):**

| Model | Karar | YÜKSEK | ORTA | Durum |
|---|---|---|---|---|
| M14 hesap ve defter | kısıtlı kullanılabilir | alım günü getirisi; sanal hesaba şirket işlemi girilemiyor | FIFO + bedelli maliyet satırı | ✅ iki YÜKSEK v0.99.2'de düzeltildi; yeniden doğrulama gerekir |
| M15 fiyat düzeltmeleri | kısıtlı kullanılabilir | — | ~~Yahoo sonradan düzeltirse çift düzeltme~~ (v0.99.5); ~~CSV satırları denetlenmiyor~~ (v0.99.4); "ham" fiyat temettü düzeltmeli | ORTA'lar ve D-3/D-7 kapandı (v0.99.4–6); açık: yeniden doğrulama |
| M11 pozisyon uyarıları | kısıtlı kullanılabilir | iz süren stop yalnız yukarı gitmiyor, uyarı çok sık | stop backtest'tekiyle aynı değil; teyitsiz işlem kelime kontrolü kırılgan; eksik veride sessiz | ✅ YÜKSEK ve iki ORTA v0.99.3'te düzeltildi; açık: stopun ayrı karnesi yok (backtest sabit stopu ölçüyor); yeniden doğrulama gerekir |
| M12 portföy riski | kısıtlı kullanılabilir | — | stres raporu fiyatsız pozisyonu sessizce düşürüyor; pencere seans değil satır sayıyor; aşımlar kümeleniyor (oynaklık rejimi) | sıradaki işler |
| M28 risk bütçesi | kısıtlı kullanılabilir | /risk denge gerçek hesabı sınıra döndürmüyor (satış toplamı küçültüyor; eşit kesinti ağırlığı değiştirmiyor) | ölçülemeyen satır "sınırlar içinde" deniyor; sınır dosyası sorunları gösterilmiyor; nan/inf kabul; fiyatsız pozisyon toplamı şişiriyor | ✅ YÜKSEK ve üç ORTA v0.99.8'de düzeltildi; açık: fiyatsız pozisyon; yeniden doğrulama |
| M16 veri kalitesi | kısıtlı kullanılabilir | ±%10 içindeki hatalar görünmüyor (ikinci kaynak kapalı): ×1,05 tek günlük hata %91, düz mum %94 kaçıyor; açılış yüksek–düşük aralığında mı denetlenmiyor | küçük bedelsiz elenmiyor; önerilen katsayı günün gerçek hareketini içeriyor; haftalık tarama kalıntıyı gizliyor; doğruluk SLO'su az örnekle yeşil | ✅ YÜKSEK v0.99.9'da kısmen kapandı (açılış, düz mum ve geri dönen mum listeleniyor; ayırt etmek için ikinci kaynak gerekir); açık: ORTA'lar; yeniden doğrulama |
- **Kullanıcı kararları devretti (29.10, K-54).** Döngü onay beklemeden ilerliyor. Sınırlar aynı.
- **İleri hedefler:**
  - ✅ 2027 tatilleri, v0.94.2 (geçici; Aralık'ta Borsa İstanbul duyurusuyla teyit).
  - ✅ Elenen ve kalan grubun canlı izlenmesi, v0.96.0 (K-53). İlk sonuç 30.10 kaydından 5 seans sonra.
  - ✅ Haftalık kayıtlı tarama özeti, v0.98.1. Kayıtlı taramalar PC'de kişisel dosyada olduğu için cumartesi araştırması yerine cuma raporunda; 30 kayıttan önce "veri birikiyor".
- **Özellik talimatları (28.10):**
  - A destek/direnç: tasarım ✅ v0.90.1 (K-49). Veri borcu ✅ v0.91.0–v0.91.1: ikinci kaynakla doğrulandı; dışarıda yalnız PAHOL var, o da kısa geçmiş, borç değil. **Kapı açık.** Kod ✅ v0.92.0–v0.94.0: levels.py, /seviye, /analyze, /tara alanları, rapor satırı, kayıt, /durum, web, ölçüm (ayırt edilemedi). Bitti ölçütünden kalan: PC'de seviye kaydının yazıldığının kanıtı. İlk rapor 30.10'da (29.10 bayram).
  - B senaryolar: ✅ şablon tasarımı K-55 (c7b25ea, sonuçtan önce); ✅ v0.97.0 `/senaryo` (iki kullanım). ✅ v0.97.1 karne (cuma akşamı ve GitHub `screens.yml`), canlı kayıt ve `/performans` "Senaryolar". ✅ v0.97.2 `/tara senaryo(...)`. ✅ karne RESEARCH_LOG'da (29.10: üçünde de ortalama R sıfırdan ayırt edilemedi). Kalan: isteğe bağlı ölçüm kitabı, canlı kaydın PC kanıtı.
  - C, D, E, F paketi: aşağıdaki dört başlık. Şu an açık olanlar yalnız C1 tasarımı ve kaynak araştırması ile F1 envanteri.
- **Profesyonel filtreler görevi (28.10):** Aşama 1–3 ✅; Aşama 4 ✅ v0.99.0 (K-57 formüller, `/temel`; veri gelene kadar "veri yok"); Aşama 5 ✅ a5 ön kayıt taslağı (RESEARCH_LOG; onaylanmadı, veri ve tarih koşulu bekliyor). Kalan: temel puanların `/tara` alanı olarak eklenmesi (veri gelince anlamlı).
- **/tara Aşama 4 sırası:** 4a kayıt listesi/silme ✅ v0.83.0 → 4b abonelik ✅ v0.83.0 → 4c /performans "Taramalar" ✅ v0.84.0 → 4d /tara_sanal ✅ v0.85.0. Aşama 5 ✅ v0.86.0. Aşama 6 ✅ v0.86.1 (kalan testler, BotFather listesi, CHARTER §9 uyumu).
- **Şablon görevi (28.10):** A ✅ v0.80.0, B ✅ v0.81.0, C ✅ v0.82.0, D ✅ v0.82.1 (tasarım). Açık: şablon karnelerinin gerçek verideki sonuçlarını kullanıcının keşif sayılarıyla karşılaştırmak (araştırma çalışması bekleniyor); temel veri uygulaması ayrı karar.
- **PC'de doğrulandı (28.10 yerel otomasyon, v0.68.0 → v0.75.0):** 699 test geçti (4 atlandı), ruff temiz, `/durum` hepsi SAĞLIKLI, SLO 6/7 hedefte. Dışarıdan izleme çalışıyor (bot sinyali 10:42). Bayram günü rapor görevi "holiday" ile başarılı sinyal gönderiyor; 29.10'da yanlış alarm beklenmiyor, 30.10'da `logs/monitoring.json`'dan doğrulanacak. v0.68.1–v0.75.0 PC'de doğrulandı.
- **Açık (K-36):** günlük raporun ve canlı ölçümün evreni (`data/universe.csv`, 118 hisse) resmi BIST 100 ile aynı değil: 32 fazla, 14 eksik. Ölçüm sürerken değiştirilmeyecek. Karar ilk canlı ölçüm dönemi bitince (Kasım sonu) verilecek.
- **/tara paketi (kullanıcı, 28.10):** Aşama 1 ✅ v0.76.0, Aşama 2 ✅ v0.77.0, Aşama 3 ✅ v0.78.0. Sırada Aşama 4 (kayıt/abonelik/ölçüm), 5 (şablonlar), 6 (kalite ve belgeler). **Açık:** BIST 30 listesi kaynağıyla eklenmeli (K-33).
- **Veri doğruluğu SLO'su ilk kez ölçüldü (Research 28.10 09:50, v0.72.1 koduyla):** 116/117 tutarlı, %0,85 ≤ %1 → hedefte. Tek fark SKBNK 19.10 (v0.73.1'de düzeltildi), KPOWR ikinci kaynakta yok.
- **Araştırma elle çalıştırıldı (28.10 09:25, Research #18, başarılı):** a4 adımı "27.04.2027'den önce çalıştırılmadı" yazdı (doğru); KAP kontrolü 5 bildirim, sermaye işlemleri kayıtlı ya da tahsisli. İkinci kaynak özeti 117/118 "fark" verdi; hepsi Yahoo'da henüz olmayan 27.10 seansı (ölçüm hatası, v0.72.1'de düzeltildi). Gerçek tek fark: SKBNK 19.10 (Yahoo −%24,6 / İş −%3,1); şüphe taraması da aynı günü verdi (çarpan 0,7542, %40 bedelli 1 TL ile ~7,2 TL fiyatta tutarlı). `corporate_actions.csv`'deki kayıt 22.10 tarihli, KAP'ın hak kullanım tarihleri bildirimi 21.10'da: Yahoo'nun düşüşü bildirimden önce ve ±%10 limitinin dışında. **Kapandı (v0.73.1):** KAP 1685136 metni (rüçhan 22.10–05.11) ve iki kaynaktaki ham fiyatlar kopukluğu 19.10'da gösterdi; satır 19.10'a taşındı (DATA_CORRECTIONS). SKBNK pozisyonda yok.
- **PC v0.68.0'da (28.10 08:51, eski güncelleyiciyle son kurulum):** 654 geçti + 4 atlandı, ruff temiz, bot yeniden başladı. "QuantBIST Guncelle" görevi depodaki `scripts\guncelle.py`'ye çevrildi (07:40). Elle deneme 09:05: "GitHub'da CI'ı yeşil son sürüm 0.68.0 (14c56e9)" → GÜNCEL, Telegram'a mesaj yok (bilerek). `bildir.py` denemesi Telegram'a "🤖 Otomasyon" olarak ulaştı.
- **PC v0.66.0'da (28.10 08:16, kullanıcıyla birlikte `guncelle.py`):** PC v0.59.0'daymış; güncelleme görevi yoktu. 639 geçti + 4 atlandı, ruff temiz, bot yeniden başladı; `/durum` tüm kontroller SAĞLIKLI. "QuantBIST Guncelle" görevi kuruldu, her gün 07:40 (K-27). Geri yükleme testi başarılı. İlk alarm kuruldu (#1 THYAO < 260): bu akşam gerçek veriyle ilk deneme.
- **Dışarıdan izleme açıldı (27.10 22:23, yerel otomasyon):** iki .env satırında önce örnek metin (`<…kod>`), sonra `.com/` ile kod arasında boşluk vardı (Healthchecks HTTP 400); düzeltilince bot sinyali kabul edildi, `/durum` izleme satırı SAĞLIKLI. Rapor kontrolü ilk sinyalini 28.10 18:30'da alacak. Adresler hiçbir yerde yazdırılmadı.
- **İlk otomatik kurulu sürümle rapor (27.10 18:30, yerel otomasyon doğruladı):** runs.csv 18:30:01→18:30:39, veri günü 27.10, tek mesaj. Sayılar elle sağlandı: hesap 97.394+2.530=99.924 TL, günlük −%0,05, THYAO 10×253,00, −76 TL/−%2,93, risk ~78 TL (%0,08→%0,1), etkin pozisyon 1,0 (26.10 düzeltmesi tuttu). KPOWR verisi yok (bilinen). S1 kanıtına eklendi.
- **PC doğrulaması (27.10 09:09, v0.46.0):** 448 test geçti (Windows'ta 2 test atlandı), ruff temiz, paketler kilit dosyasıyla aynı. `/durum`'daki 12 kontrolün hepsi SAĞLIKLI; geri yükleme testi başarılı.
- **Bulunan sorunlar:**
  - `verify.ps1` sonda emoji yazdırırken çöküyordu (v0.46.1'de düzeltildi).
  - Bot açılırken `telegram.error.Conflict` hatası çıktı: aynı token'la iki bot aynı anda çalışıyordu (kullanıcının log'u, 27.10 09:21). v0.46.2'den itibaren bu durum log'a tek bir açık satırla yazılıyor.
- **PC doğrulaması (27.10 09:22, v0.46.1):** 450 test geçti (2 atlandı); `verify.ps1` hatasız tamamlandı.
- **Bot tek örnek (27.10 09:30):** arka plandaki eski bot (08:40) kapatıldı ve v0.46.1 ile yeniden başlatıldı. Başlangıçtan sonra `Conflict` satırı yok; yaşam sinyali 09:30:56'da yazıldı. Botu otomatik başlatan bir şey yoktu: bilgisayar yeniden başlarsa bot açılmayacaktı. Kullanıcı 27.10'da "QuantBIST Bot" görevini kurdu (oturum açılışında, tek kopya, çökerse yeniden başlatır); aynı ayarlar `scripts/register_bot_task.ps1` dosyasında.
- **Bot görev üzerinden (27.10 10:15):** görev yeniden başlatılınca elle açılmış eski bot da çalışır durumdaydı (iki bot); eski kopya kapatıldı. Şimdi tek bot, "QuantBIST Bot" görevinin başlattığı. Bot artık yalnız görevle başlatılır/yeniden başlatılır.
- **Aşama 3 kapandı:** H1, H2, H3'ün üçü de ön kayıtlı birincil ölçütü (Bonferroni %98,3 fazla getiri aralığı > 0) geçemedi, hepsi **red** (RESEARCH_LOG, 27.10). H2/H3 nakdi kullanıcı onaylı plan değişikliği 1 ile TCMB politika faizi. Haftalık araştırma üçünü kayıt için yeniden hesaplıyor; yeni hipotez yalnız yeni plan ve onayla.
- **PC doğrulaması (yerel nöbetçi, 27.10 08:41–08:45):** v0.46.0 kuruldu, 448 test geçti (2 atlandı), ruff temiz, /durum 13/13 SAĞLIKLI. D13 (temettü, v0.45.15) ve v0.45.13–v0.46.0 **PC'de doğrulandı**: ledger, paper_orders, equity_log ve signal_log dosyalarının SHA-256 değerleri kurulumdan önce ve sonra aynı, yeni sürüm dördünü de sonuna kadar okuyor, kurulumdan önce yedek alındı (quantbist_2026-10-27.zip, 08:39). Aynı mesajdaki açılış hatası v0.48.4'te düzeltildi; v0.55.1'de kütüphanenin gerçek yeniden deneme döngüsüyle de test edildi.
- **Kurulum rolü (kullanıcı, 27.10):** kodu Claude geliştirir; PC'deki yerel otomasyon (`C:\Projeler\QuantBIST_otomasyon\guncelle.py`) yalnız bu dalı indirir, yedek alır, deneme kopyasında ruff+pytest çalıştırır, geçerse kurar, bot açılmazsa eski sürüme döner ve botu "QuantBIST Bot" göreviyle yeniden başlatır. Telegram'daki "🤖 Otomasyon" mesajları ondan gelir. Kullanıcıya kurulum (robocopy) komutu verilmez.
- **08:36 kurulum hatası (27.10):** Conflict değildi. Log: `getaddrinfo failed` (DNS) ve "Network Retry Loop (Bootstrap Initialize Application): Failed run number 0 of 0. Aborting." Bot açılışta tek ağ hatasında kapanıyordu. v0.48.4'te açılış yaklaşık 7 dakika yeniden dener (`bootstrap_retries=20`); yanlış token yine hemen durur.
- **Yerel çalışma klasörleri:** canlı klasörde `backups\`, `qb\`, `research_workspace\` var, repoda yok. pytest yalnız `tests/`'i toplar. `ruff check .` (setup.ps1/verify.ps1) bunları v0.48.4'ten beri taramaz.
- **Denetim:** D1–D14'ün hepsi kapandı (v0.45.1–v0.45.15).
- **Kullanıcı kararları (27.10) uygulandı:**
  - KCAER katsayısı 0,8646 (v0.45.13).
  - `/performans` "geçmiş" sütunu (v0.45.14).
  - Temettü kaydı (v0.45.15).
  - Tek gün kapanış düzeltmeleri kapalı kalıyor.
  - Dışarıdan izleme: Healthchecks.io kodu hazır (v0.46.0); adresler girilene kadar kapalı.
  - Sunucu: şimdilik PC'de kalınıyor; hazırlık docs/SERVER.md'de bekliyor.
- **Kullanıcıdan beklenen:**
  - **PC doğrulaması (27.10 14:26, v0.48.1):** 489 test geçti (2 atlandı), `/durum` 12/12 SAĞLIKLI, yedek alındı ve doğrulandı, bot görevle yeniden başlatıldı.
  - PC'deki elle değişiklikler (27.10) incelendi ve v0.48.1'de repoya alındı: onay kapısı `core/market/corrections.py`'de, onaylar `data/price_fix_approvals.csv`'de (şimdilik boş). PC'deki `research_workspace` kapısı artık kullanılmıyor; v0.48.1 kurulunca PC'deki üç dosya repodakiyle değişir.
  - Healthchecks.io hesabı ve iki adres (OPERATIONS.md §7: "QuantBIST rapor" Cron `35 18 * * 1-5` Europe/Istanbul, grace 1 saat; "QuantBIST bot" period 5 dk, grace 20 dk).
- **Gözlem tarihleri:**
  - 28.10: yarım gün.
  - 29.10: tatil.
  - 30.10: cuma canlı ölçüm satırı.
  - 31.10: zamanlanmış cumartesi araştırması.
  - Kasım sonu: canlı ölçüm kararı. 5 seanslık ufukta 10 bağımsız dönem yaklaşık 50 seans sürer.

## Bağımsız denetim (27.10.2026, v0.45.0 üzerinde)

Kod baştan okundu. Aranan sorun türleri:
- hesap hatası,
- sessizce yutulan hata,
- tarih ve saat dilimi sorunu,
- aynı işi iki kez yapan kod,
- ölü kod.

Kritik bulgu yok. Satır satır kaynak ve risk tablosu: docs/RAKAMLAR.md. Yüksek önemli bulgular sırayla düzeltilir; her biri önce başarısız bir testle gösterilir.

| # | Önem | Bulgu | Etki | Durum |
|---|---|---|---|---|
| D1 | YÜKSEK | Gerçek hesabın "Günlük değişim" satırı ve "zirveden düşüş" uyarısı, hisse alımını kazanç, satışı kayıp sayıyor. Değer yalnız hisselerin piyasa değeri; arada para giriş-çıkışı ayrılmıyor | Yeni alım gününde "+%20" gibi sahte bir değişim görünüyor. Yarı satışta yanlış "hesap zirvesinden %50 aşağıda" uyarısı (yüksek önem) çıkıyor | ✅ v0.45.1 (`test_report_numbers.RealAccountFlowsTest`) |
| D2 | YÜKSEK | Rapor yalnız BIST 100 listesindeki hisselerin fiyatını güncelliyor. Listede olmayan bir hisseyi tutunca değer ve kâr/zarar eski fiyattan hesaplanıyor. Bekleyen bir sanal emir hiç dolmuyor ve bunu söylemiyor | Değer ve uyarılar eski fiyata dayanıyor. Uyarı ancak 5 gün sonra çıkıyor | ✅ v0.45.2 (`test_report_numbers.HeldOutsideUniverseTest`) |
| D3 | YÜKSEK | `/performans`'taki güven aralığı 20 ve 60 seanslık getirilerin üst üste bindiğini hesaba katmıyor. Ardışık günlerin 20 günlük getirileri neredeyse aynı ama bağımsız sayılıyor | Aralık olması gerekenden çok dar; "XU100'ü anlamlı şekilde geçiyor" kararı yanlışlıkla çıkabilir | ✅ v0.45.3 (`test_forward.SummaryTest.test_overlapping_horizons_do_not_make_noise_significant`) |
| D4 | ORTA | `data/corporate_actions.csv` içindeki bozuk bir satır yalnız log'a yazılıp atlanıyor | O hissenin geçmiş fiyatları düzeltilmeden kullanılıyor ve kimse fark etmiyor | ✅ v0.45.4 (`test_corrections.BadCorporateActionRowTest`) |
| D5 | ORTA | Canlı ölçüm kaydı yazılamazsa hata yalnız log'a gidiyor, raporda görünmüyor | O gün ölçümden düşüyor; `/durum` bunu ancak sonraki günlerde "kaydı olmayan seans" olarak gösteriyor | ✅ v0.45.5 (`test_daily.ScoreRecordingFailureTest`) |
| D6 | ORTA | İki ayrı mesaj bölücü var (`bot/common.split_message`, `daily.split_text`). Günlük raporun bölücüsü 4.000 karakteri aşan tek bir satırı bölmüyor | Çok uzun bir satır Telegram'da hata verir ve rapor gitmez | ✅ v0.45.6 (`test_daily.SplitLongLineTest`) |
| D7 | ORTA | Hesap değerleme mantığı üç yerde ayrı ayrı yazılmış: `daily.build_daily`, `service.portfolio_text`, `service._paper_value`. `/portfolio` fiyatın tarihini göstermiyor | Bir düzeltme bir yerde kalıp diğerlerinde eksik kalabilir; eski fiyat "son kapanış" gibi görünebilir | ✅ v0.45.7 (`test_report_numbers.PortfolioCommandTest`) |
| D8 | DÜŞÜK | `/analyze` skoru 2 yıllık, günlük kayıt 5 yıllık geçmişle hesaplıyor (EMA/RSI başlangıç farkı) | Seyrek de olsa bir puanlık fark ve farklı görünüm çıkabilir | ✅ sorun değil: 300 seride 2 ve 5 yıllık geçmiş aynı skoru, görünümü ve göstergeleri veriyor (`test_strategy_score.HistoryLengthTest`) |
| D9 | DÜŞÜK | Ölü kod: `market.data.load_last_price`, `load_snapshot`, `load_market`, `get_data_quality`; `indicators.is_bullish`, `is_bearish`, `is_neutral`, `strong_buy_signal`, `strong_sell_signal`, `indicator_score`; `watchlist.service.get_watchlist_details` | Bakım yükü; bu fonksiyonların hiçbiri çağrılmıyor | ✅ v0.45.8 (11 fonksiyon, 319 satır kaldırıldı; tüm testler geçiyor) |
| D10 | DÜŞÜK | Saat dilimi belirtilmemiş zamanlar: fiyat deposunun eşitleme zamanı, veri önbelleği, log dosyası adı | PC ve sunucu İstanbul saatinde olduğu için bugün doğru. Başka bir saat diliminde 15 dakikalık yenileme ve log adı kayar | ✅ v0.45.9 (`test_data_layer.StoreTest.test_times_with_and_without_time_zone_mix_safely`; testler UTC ve İstanbul saatinde geçiyor) |
| D11 | DÜŞÜK | Telegram mesaj sınırı UTF-16 birimiyle sayılıyor, kod Python karakteri sayıyor | 96'dan fazla emoji içeren bir parça sınırı aşabilir; bugünkü raporlarda olmuyor | ✅ v0.45.10 (`test_daily.SplitUtf16Test`) |
| D12 | DÜŞÜK | `/report` elle çalıştırılınca yeni uyarıları kayda geçiriyor. Aynı gün 18:30 raporu onları "🆕" olarak yeniden göstermiyor | Kullanıcı uyarıyı `/report` çıktısında zaten görmüş oluyor | ✅ v0.45.11 (`test_report_numbers.ManualReportAlertsTest`) |
| D13 | ORTA | Temettü kaydı yok. Defterde temettü satırı (`dividend`) bulunmuyor; temettü günü ham fiyat düşüyor ama nakde bir şey eklenmiyor | Sanal ve gerçek hesap getirisi temettü kadar eksik görünüyor; temettü günü "Günlük değişim" kayıp gösteriyor. Backtest (temettüye göre düzeltilmiş fiyat) ile sanal hesap tutarsız | ✅ v0.45.15, kullanıcı onayıyla (`test_ledger.DividendTest`, `test_report_numbers.DividendReportTest`); PC'de doğrulandı 27.10. Sanal hesaba otomatik temettü yazılmıyor: temettü verisi yok |
| D14 | DÜŞÜK | "Günlük değişim" son hesap kaydına göre hesaplanıyor. PC bir veya birkaç gün kapalı kaldıysa satır birkaç günün toplamını gösteriyor ama "günlük" yazıyor | Yanıltıcı etiket; hesabın kendisi doğru | ✅ v0.45.12 (`test_report_numbers.ChangeLabelTest`) |

## Aşama 2: tamamlandı (PC'de doğrulandı, 27.10.2026)

Yazılım tarafı bitti. Testler `tests/` içinde, CI numarası her maddenin yayınlandığı
sürümün ana dalındaki çalışması. Son CI: **#66 (run 40413981373, 55e3384), 380 test**.
"PC" sütunu, kullanıcının bilgisayarında görülmüş kanıtı gösterir.

| Madde | Kanıt (test) | CI | PC |
|---|---|---|---|
| Envanter, arıza etkisi, kurtarma adımları | docs/OPERATIONS.md | #57 | — |
| Günlük doğrulamalı yedek (SHA-256 manifest) | `test_backup.BackupTest.test_backup_contains_existing_files_and_verifies`, `test_corruption_is_detected`, `test_rotation_keeps_newest_daily_backups` | #54 | ✅ 5 dosya, OneDrive (26.10) |
| Fiyat veritabanı anlık yedeği (SQLite backup API, bot yazarken) | `test_backup_restore.RestoreTest.test_snapshot_while_another_connection_writes`, `test_snapshot_rotation_and_daily_list_are_separate` | #54 | kod testli; PC'de çakışma gözlenmedi |
| İzole geri yükleme testi (haftalık, raporda) | `RestoreTest.test_restore_reads_every_file_and_leaves_live_files_alone`, `test_corrupt_backup_is_detected`, `test_unreadable_content_fails_the_test`, `WeeklyCheckInReportTest` | #54 | ✅ PC, `verify_report` 27.10: 6 dosya geçici klasörde okundu |
| Gerçek geri yükleme önce mevcut hâli yedekler | `test_backup.BackupTest.test_restore_round_trip_with_safety_copy` | #54 | ✅ kullanıcı provası, 5 dosya SHA-256 aynı (27.10) |
| Yedek ayrı fiziksel hedefte | `test_health_ops.BackupLocationTest` (3 test) | #66 | ✅ PC, `verify_report` 27.10: OneDrive klasörü, "Yedek" SAĞLIKLI |
| `.env` yedeklenmez, rapor çıktısında token/chat id gizli | `test_verify.RedactTest` | #64 | — |
| Yazma kilidi (rapor ile `/paper`, `/trade` çakışmaz) | `test_write_safety.LockedWritesTest` (3 test) | #54 | kod testli; PC'de çakışma gözlenmedi |
| Tek çalıştırma, çift rapor yok, eski kilit 1 saatte düşer | `test_runs.LockTest`, `OncePerDataDayTest` | önceki sürümler | ✅ 26.10 tek mesaj |
| Telegram yeniden deneme (ağ/5xx/429), yanlış token tekrar denenmez | `test_write_safety.SendRetryTest` (4 test) | #54 | — |
| Sağlık seviyeleri; doğrulanamayan asla SAĞLIKLI değil | `test_health.ReportTextTest.test_verdict_never_ok_with_unknowns`, `ReportCheckTest.test_no_records_is_unknown_not_ok` | #56 | ✅ PC, `verify_report` 27.10 |
| Veritabanı bütünlüğü, kilitli veritabanı uyarı sayılır | `test_health_ops.DatabaseTest` (2 test) | #57 | ✅ PC, `verify_report` 27.10 |
| Disk, veri şeması (yanlış sürüm), yaşam sinyali | `DiskTest`, `SchemaTest`, `HeartbeatTest`, `ReportWarningsTest.test_bot_down_shows_in_the_daily_report` | #56 | ✅ PC, `verify_report` 27.10 |
| GitHub araştırma başarısızlığı uyarısı | `test_health_ops.ResearchTest.test_states` | #56 | — |
| Eski veri uyarısı | `test_health.DataChecksTest.test_prices_current_and_behind` | önceki sürümler | — |
| Başarısız rapor bildirimi | `test_backup.DailyIntegrationTest.test_failed_report_is_announced_in_telegram`, `test_runs.OncePerDataDayTest.test_failure_is_recorded` | önceki sürümler | — |
| 20:00 kontrolü, önem seviyesi, tekrar etmeyen uyarı | `test_scheduler.ReportWatchTest`, `AlertDedupTest`, `SeverityTest` | #57 | ✅ PC, `verify_report` 27.10 |
| Tek komutla kurulum kanıtı | `test_verify` (6 test); `scripts/verify.ps1` Windows'ta denenmedi | #64 | ✅ PC, `verify_report` 27.10 (v0.46.1'de konsol düzeltmesi) |
| Testler ağa çıkmaz, gerçek `data/` ve `logs/`'a yazmaz | `test_health_ops.ResearchTest.test_tests_never_reach_the_network`; conftest oturum sonu kontrolü | #56 | — |

**Açık (yazılım dışı):**
- PC'de `verify.ps1` çıktısı ve `/durum` bekleniyor.
- PC kapalıyken çalışma ancak sunucuyla mümkün (bkz. sunucu hazırlığı).

## Doğrulanmış durum (27.10.2026; kod v0.46.1, kullanıcı PC'si v0.46.0)

İşletim, yedek ve kurtarma: docs/OPERATIONS.md.

| Bileşen | Durum | Kanıt |
|---|---|---|
| Kod ve bağımlılıklar | Doğrulandı | CI yeşil; kullanıcı PC'sinde v0.46.0 ile 448 test, paketler `requirements.lock` ile aynı (27.10 09:09) |
| Telegram botu | Doğrulandı | `/help` tek sürüm yanıtlıyor (26.10 14:11) |
| Zamanlayıcı | Doğrulandı | Windows görevi tek zamanlayıcı; 26.10 18:30 raporu zamanında geldi |
| Günlük rapor teslimi | Doğrulandı | 26.10.2026 kapanış raporu 18:30'da Telegram'a geldi, tek mesaj |
| Sanal emir dolumu (v0.28 alanları) | Doğrulandı | #1 THYAO 10 adet: açılış 260,25 + %0,05 kayma = 260,38; komisyon 2,60 TL; hesap 97.394 + 2.582 = 99.976 TL |
| Yedek ve geri yükleme | Doğrulandı | Günlük yedek 5 dosya (OneDrive). Kullanıcı provası (27.10, kopya üzerinde): ledger.csv bozuldu, paper_orders.csv boşaltıldı; `--restore` sonrası 5 dosya SHA-256 ile birebir aynı |
| `data/signal_log.csv` | Doğrulandı | 26.10 14:42 elle çalıştırma: 117 hisse kaydı |
| `logs/runs.csv` `sent` satırı, `/durum` | Doğrulandı | 26.10 18:30 `sent` satırı; `/durum` 12/12 SAĞLIKLI (verify_report 27.10). 20:00 kontrolü uyarı gerektiren bir durum olmadığı için henüz tetiklenmedi |
| Portföy "Risk:" satırı (v0.29) | Doğrulandı | Kullanıcı PC'si v0.35.0 raporunda görünüyor (27.10); etkin pozisyon sayısı hatası (1.498,7 yerine 1,0) kullanıcı tarafından bulundu, v0.36.1'de düzeltildi |
| Yarım gün / tatil davranışı | **Doğrulanmadı** | 28.10 yarım gün, 29.10 tatil |
| Cuma canlı ölçüm satırı | **Doğrulanmadı** | İlk görülme hedefi 30.10.2026 |
| Cumartesi araştırma iş akışı | Elle doğrulandı (pipefail ile çıktı dosyaları kontrol edildi, run 40377109448); zamanlanmış çalışma doğrulanmadı | İlk zamanlanmış çalışma 31.10 |
| İkinci kaynak kontrolü | Son 30 gün doğrulandı (116 tutarlı, XU100 tutarlı); 2022 sonrası tam tarama sürüyor | run 40377105196 |
| Test kapsamı | %90 satır (core + bot) | `coverage run -m pytest` |

## Bulgular

**İşletim**
- PC'de iki zamanlayıcı aynı anda çalışabilir: `scripts/register_daily_task.ps1` (Windows
  görevi, 18:30) ve `DAILY_REPORT_AT` (bot içi, 18:30). İkisi açıksa rapor iki kez gider ve iki
  süreç aynı anda `paper_orders.csv` / `ledger.csv` dosyalarını okuyup yazar: bekleyen bir sanal
  emir iki kez dolabilir. Kullanıcı PC'sinde Windows görevi kurulu çıktı (26.10); `DAILY_REPORT_AT`
  kaldırıldı. v0.22.0'dan itibaren kilit ve `logs/runs.csv` ikinci çalıştırmayı engeller.
- Bot içi zamanlayıcıda kaçırılan çalıştırma telafisi (misfire) ayarlanmamış: PC 18:30'da uykudaysa
  o günün raporu gitmez. Windows görevinde `StartWhenAvailable` var.
- Resmi tatillerde rapor yine çalışır ve önceki seansın verisini yeniden gönderir (kayıtlar tekrar
  yazılmaz, çünkü veri tarihine göre tekilleştirilir).
- Sistem sağlığı tek yerden görülemiyor: son rapor, son veri tarihi, son yedek, signal_log satır
  sayısı için bir komut yok.

**Araştırma**
- Düzeltildi (v0.24.0): `core.backtest.research` artık geçmiş BIST 100 üyeliğini kullanıyor; GitHub iş
  akışı eski üyelerin verisini indirmiyordu, bu yüzden önceki `--pit` sonuçları da eksik evrenle
  hesaplanmıştı (90/202 hisse dışarıda). Ayrıntı: docs/RESEARCH_LOG.md.
- Momentum walk-forward'un +%20 yıllık sonucu tek bir test penceresinden (+%140) geliyor; son
  pencere −%66,5. Pencere dağılımı ve güven aralığı raporlanmıyor.
- Aday kurallardan hiçbiri üç kapıyı geçmiyor (26.10 çalışması). Teknik skor (bot sinyali) yıllık
  +%7,5, XU100 +%14,6.
- Araştırma sonuçları yalnızca Actions özetinde (90 gün sonra silinir); hipotez ve sonuç kaydı yok.
- Veri geçmişi ~5 yıl (Yahoo); test dönemi ~3 yıl. Tek veri kaynağı.

**Veri**
- KPOWR verisiz; SASA'da 151 gün hacim eksik. CANTE (2026-01-26) ve KCAER (2024-11-28) bilinçli
  olarak düzeltilmedi.

**Test kapsamı boşlukları**
- `bot/watchlist.py` %28, `bot/portfolio.py` %34, `core/market/update.py` %32,
  `core/backtest/candidates.py` %22. PowerShell betikleri test edilmiyor.

## Öncelikli işler

Ölçüt sırası: güvenlik ve veri bütünlüğü → hesap doğruluğu → strateji doğrulama değeri →
kullanıcı faydası → sürdürülebilirlik → maliyet/risk.

| # | İş | Önem | Fayda | Uygulama riski | Modüller | Gerekli testler | Kabul kriteri |
|---|---|---|---|---|---|---|---|
| 1 | ✅ v0.22.0 (PC'de doğrulama bekliyor) — Tek çalıştırma güvencesi: rapor için dosya kilidi ve "bu veri günü için gönderildi" kaydı | Kritik | Çift rapor ve çift sanal dolum imkânsız olur | Düşük | `core/reports/daily.py`, `bot/scheduler.py` | Eşzamanlı iki çalıştırma; aynı gün ikinci çalıştırma; `/report` elle çalıştırma | İki süreç aynı anda başlasa da tek mesaj, tek dolum; `/report` yine çalışır |
| 2 | ✅ v0.23.0 (PC'de doğrulama bekliyor) — Sistem sağlığı: çalıştırma kaydı (`logs/runs.csv`), `/durum` komutu, kaçırılan rapor telafisi | Yüksek | Rapor gitmediğinde fark edilir; uyku/kapanma sonrası telafi | Düşük | `daily.py`, `scheduler.py`, `bot/` | Kaçırılan gün senaryosu; sağlık metni; veri yokken "bilinmiyor" (asla "sağlıklı" değil) | `/durum` son rapor, son veri tarihi, son yedek, signal_log satırı gösterir; uyanınca aynı gün rapor gider |
| 3 | ✅ v0.24.0 (sonuçlar: docs/RESEARCH_LOG.md) — Araştırmada istatistiksel doğrulama: research için PIT evren, pencere bazlı sonuç, blok bootstrap güven aralığı, çoklu deneme düzeltmesi | Yüksek | Rastlantısal sonuçların başarı gibi görünmesi engellenir | Orta | `core/backtest/research.py`, `reliability.py`, yeni test | Bilinen sıfır-beklentili seride CI sıfırı kapsar; PIT ile eski sonuçların karşılaştırması | Haftalık tablo her strateji için CI ve "anlamlı değil" etiketi gösterir |
| 4 | ✅ v0.25.0 (`research-results` dalı, `history.csv`, `docs/RESEARCH_LOG.md`) — Araştırma kaydı: `docs/RESEARCH_LOG.md` (hipotez, ön tanımlı ölçüt, sonuç, olumsuz sonuçlar dahil) ve haftalık sonuçların kalıcı saklanması | Yüksek | Süreklilik; veri gözetleme (snooping) izlenebilir | Düşük | `docs/`, `research.yml` | İş akışı çıktısı dosya olarak kalır | Her araştırma hipotezle başlar, sonuç tarihli kayıtlıdır |
| 5 | ✅ v0.26.0 (2026 takvimi; 2027 Aralık'ta eklenecek) — BIST takvimi: tatil/seanssız gün tespiti (yeni mum yoksa rapor "seans yok" der, yeniden göndermez) | Orta | Yanıltıcı tekrar raporu kalkar | Düşük | `daily.py`, `core/market/calendar.py` | Tatil günü simülasyonu; yarım gün (arife) mumu | Seanssız günde tek kısa bildirim veya hiç mesaj |
| 6 | ✅ v0.27.0 — Canlı ölçüm bütünlüğü: signal_log denetimi (tekrar, eksik gün, veri tarihi gecikmesi) ve `/performans`ta kayıt sağlığı | Orta | Canlı sonuçlara güven | Düşük | `core/reports/forward.py`, `core/signals_log.py` | Bozuk/tekrarlı log örnekleri | Eksik gün ve gecikmeler raporda görünür |
| 7 | ✅ v0.28.0 (kullanıcı onaylı, 26.10) — Sanal işlem kaydını zenginleştirme: emir gerekçesi/kaynağı, giriş anındaki risk, gerçekleşme koşulu (tavan/taban kilidi notu) | Orta | Her sanal işlem izlenebilir | Orta (dosya şeması değişir → onay gerekir) | `core/ledger/paper.py`, `book.py` | Eski dosyanın yeni şemayla okunması | Eski kayıtlar değişmeden okunur; yeni alanlar dolar |
| 8 | ✅ v0.29.0 (sektör verisi yok; sektör yoğunlaşması açık) — Portföy riski: yoğunlaşma, korelasyon ve likidite uyarıları (sektör verisi gerekirse ayrıca) | Orta | Risk tek hisse stop'undan genişler | Orta | `core/alerts/rules.py` | Sentetik portföylerle eşik testleri | Uyarı kuralları belgelenmiş ve testli; veri yoksa "hesaplanamadı" |
| 9 | ✅ v0.31.0 (İş Yatırım, getiri bazlı haftalık kontrol) — Veri kalitesi: ikinci kaynakla örneklem karşılaştırma, hacim eksikleri için uyarı | Orta | Tek kaynak riski azalır | Orta (ücretsiz kaynak sınırlı) | `core/market/` | Kaynak farkı tespiti | Fark eşiği aşan hisse raporlanır |
| 10 | ✅ v0.30.0 (hedef modüller %89–93; toplam %90) — Test boşlukları: bot komutları (watchlist, portfolio), `market/update`, `candidates` | Düşük-orta | Gerilemeler erken yakalanır | Düşük | `tests/` | — | Bu modüllerde kapsam ≥ %70 |

## Karar notları

- 2026-10: Teknik skor yatırım sinyali olarak sunulmaz; backtest'te XU100'ü geçmedi.
- 2026-10: KCAER/CANTE fiyat düzeltmesi yapılmadı (çift düzeltme riski). Sonra v0.34.0'da ikinci kaynakla eklendi.
- 2026-10-27 (kullanıcı kararları):
  - KCAER katsayısı teorik değere, 0,8646'ya çekildi (v0.45.13).
  - Tek gün kapanış düzeltmeleri kapalı kalıyor.
  - `/performans`'a "geçmiş" sütunu eklenecek.
  - Temettü kaydı (D13) eklenecek.
- 2026-10: Eski karar katmanı (AL/SAT etiketleri, AI modülleri) kaldırıldı (v0.20.0, kullanıcı onaylı).
- Gerçek emir entegrasyonu: yalnızca canlı ölçüm bir kuralı istatistiksel olarak kanıtlarsa ve açık onayla.
