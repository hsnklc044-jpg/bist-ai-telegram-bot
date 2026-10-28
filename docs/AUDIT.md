# EVRE 0 — Doğrulanmış durum raporu (28.10.2026, kod v0.86.1 → v0.87.0)

Profesyonel geliştirme talimatının (28.10.2026) ilk adımı ve öz-denetim 6. Bu rapor yalnız **gerçekten görülen** kanıta dayanır. Kanıtı olmayan her şey "doğrulanamadı" olarak yazıldı; varsayım yok.

**Kanıtın nereden geldiği:**
- Depo ve bu bulut ortamı: kod, testler, belgeler, git geçmişi.
- GitHub Actions'ta gerçek veriyle çalışan iş akışları: fiyat indirme ve kalite tablosu, ikinci kaynak kontrolü, tatil takvimi, KAP taraması, paket güvenliği, felaket kurtarma tatbikatı.
- **Kullanıcının PC'si bu ortamdan görülmez.** Kişisel kayıtlar, sanal portföy, PC'deki fiyat veritabanı, yedekler ve loglar için son kanıt, kullanıcının 28.10 sabahı gönderdiği `/durum` ve kurulum çıktısıdır.

## Durum tablosu

| Alan | Durum | Kanıt |
|---|---|---|
| Kod ve testler | ✅ doğrulandı | 105 Python modülü, yaklaşık 18 bin satır, 91 test dosyası. Yerelde ve CI'da 818 test geçti, kapsam %91,95, ruff temiz (CI, commit 08bde54). Testler gerçek `data/` ve `logs/`'a dokunmuyor (yazma koruması). |
| Python ortamı ve bağımlılıklar | ✅ doğrulandı | Python 3.11 sabit (`pyproject.toml`). Tüm paketler `requirements.lock`'ta tam sürümle. |
| Paket güvenliği | ✅ doğrulandı (ilk kez bugün) | pip-audit: bilinen açık yok (Security çalışması 40676080251). Haftalık tarama daha önce hiç çalışmamıştı (bkz. D7). |
| Depoda gizli bilgi | ✅ doğrulandı | Tüm git geçmişinde bot token deseni 0. Geçmişteki 2 Healthchecks adresi test örneği (`test_ping`, `test_repo_secrets`), gerçek değil. |
| Tarihsel fiyat (OHLCV) kapsamı | ⚠️ kısmen | 209 sembol, 5 yıl (2021-10-25 – 2026-10-27, Actions 28.10). 207'si tam, 2'si boş: KPOWR, KERVT. XU100'de 3 eksik gün (biliniyor: 09.04.2024 yarım gün vb.). 4 hissede 1'er hatalı OHLC mumu (BASGZ, BIOEN, BOBET, PSGYO). SASA'da 151 gün sıfır hacim, PAHOL'da 6. |
| İkinci kaynak | ✅ doğrulandı | İş Yatırım'la son 30 gün: 118 hissenin 117'si tutarlı, 2574 hisse-gün; XU100 tutarlı. KPOWR kontrol edilemedi (iki kaynakta da yok). |
| Kurumsal işlem düzeltmeleri | ❌ eksik (D4) | `corporate_actions.csv`'de 16 satır var. 10 hissede **15 çözülmemiş ±%20 sıçrama** kayıtta yok: ADEL, ASUZU, BJKAS, CVKMD, EUREN, FENER, GOLTS, GSRAY, TSPOR, TUKAS. Haftalık inceleme yalnız son 14 güne baktığı için "yeni şüphe yok" diyor. |
| Sembol değişiklikleri | ✅ doğrulandı | Kod değişiklikleri eşleme tablosunda (`membership.py`, ör. KOZAA→TRMET 24.11.2025). KERVT (BIST 100 üyesi 2023-01 – 2023-07) Yahoo'da yok: geçmiş evrende 1 hisselik veri boşluğu. |
| Tarihsel endeks üyeliği | ✅ doğrulandı | `bist100_stable.csv` + `bist100_changes.csv` (344 değişiklik, kaynaklı). 23.10.2026 listesiyle 100/100. |
| Tatil takvimi | ⚠️ kısmen (D9) | 2026'nın 13 günü XU100 mumlarıyla tutarlı. Dosya yalnız 2026'yı kapsıyor; 2027 yıl bitmeden eklenmeli. Önceki yıllar mumlardan çıkarılıyor. |
| Finansal (temel) veri | ❌ yok | Sistemde temel veri hiç yok. Kaynak seçenekleri tasarımda (K-40); yeni görevin Aşama 3'ü bunu kuracak. |
| Veri lisansları | ⚠️ belgesiz (D5) | Yahoo (yfinance, resmi olmayan API) ve İş Yatırım (resmi olmayan uç nokta) için kullanım koşulları hiçbir belgede yazılı değil. |
| Felaket kurtarma | ✅ doğrulandı (CI'da) | `dr-drill` 27.10'da başarılı. PC'deki gerçek yedekler buradan görülmez. |
| Holdout ve geleceği görme | ✅ doğrulandı | Karne holdout'u iki yerde keser; kesim kaldırılırsa test kırmızı olur. Giriş ertesi açılışta. Sanal köprüde geleceği görme testi var. |
| Kişisel kayıtlar (defter, sanal emirler, izleme, alarmlar, canlı ölçüm, hesap değeri) | ❓ doğrulanamadı | Yalnız PC'de. Son kanıt kullanıcının 28.10 sabahki `/durum`'u. Bugünkü hali görülmedi. |
| Sanal portföy raporu | ❓ doğrulanamadı | PC'de; `/performans` çıktısı gerekiyor. |
| PC'deki fiyat veritabanı, loglar, yedek bütünlüğü (SHA) | ❓ doğrulanamadı | PC'de. `/durum` "Yedek" satırı ve `python -m core.backup --test-restore` gerekiyor. |
| PC'de çalışan sürüm | ❓ doğrulanamadı | Son kanıt v0.75.0. 29.10 07:40'taki otomatik kurulum en yeni yeşil sürümü kuracak. |

## Bulgular (öz-denetim 6)

| # | Önem | Bulgu | Durum |
|---|---|---|---|
| D1 | **YÜKSEK** | /tara geçmiş karnesi, araştırmanın dışarıda bıraktığı hisseleri de kullanıyordu: çözülmemiş ±%20 sıçrama ya da kısa geçmiş (`tradable_symbols`). Örneğin FENER'in düzeltilmemiş −%78'lik veri sıçraması karnede −%78'lik bir işlem gibi sayılabiliyordu. Bu, 28.10'daki şablon karnelerini ve kullanıcı sayılarıyla karşılaştırmayı da etkiledi. | ✅ v0.87.0: karne aynı hisseleri dışarıda bırakıyor ve hangilerini bıraktığını yazıyor; eski önbellek geçersiz (`CARD_FORMAT=3`, `test_screen_card_jumps`). Şablon karneleri yeniden hesaplanacak. |
| D2 | ORTA | Canlı /tara listesi, abonelik ve sanal köprü yakın tarihte çözülmemiş sıçraması olan hisseyi eleyemiyor: CVKMD 03.08.2026'da −%61,9. 60 seanslık göstergeler bozuk çıkar. | ✅ v0.88.0: "veri sorunu" elemesi (252 seans) |
| D3 | ORTA | Göreli hacim, eksik (sıfır) hacmi 1,0 ile dolduruyor; işlem tutarı sıfır hacmi 0 TL sayıyor (SASA 151 gün). Talimattaki "sahte doldurma yok" kuralına aykırı. | ✅ v0.88.0 eleme: son 20 seansta 3+ gün sıfır hacim "veri sorunu" sayılır. Göreli hacim tanımı puan ve araştırma beklentilerine bağlı olduğu için değişmedi (ayrı karar). |
| D4 | ORTA | 10 hissede 15 çözülmemiş sıçrama kayıtta yok (yukarıda). Bu hisseler araştırmadan ve artık karneden tümüyle çıkıyor: geçmiş evrenin yaklaşık %5'i kayıp. | kısmen ✅ v0.88.1: bugünkü BIST 100'de olup sıçraması son 252 seansta kalanlar eklendi (FENER 2025'in iki işlemi, CVKMD). Kalan 12 sıçrama açık (DATA_CORRECTIONS). |
| D5 | DÜŞÜK | Veri kaynaklarının lisansı ve kullanım koşulları belgesiz. | açık → Aşama 3 kaynak kararıyla birlikte DECISIONS'a yazılacak. |
| D6 | DÜŞÜK | Herkese açık git geçmişinde (eski commit 7ece232) Telegram sohbet kimliği ve 2 hisselik eski izleme listesi var. Kimlik bir parola değil; bot yalnız token sahibiyle konuşur ve izinli sohbet dışını reddeder. | kabul. Geçmişi yeniden yazmak kopyaları bozar ve varsayılan dal üzerinde kullanıcı kararıdır; kayıt altında. |
| D7 | DÜŞÜK | Haftalık paket güvenlik taraması eklendiğinden beri hiç çalışmamıştı (zamanı pazartesi, iş akışı salı geldi). | ✅ 28.10'da elle çalıştırıldı, temiz. Bir sonraki otomatik çalışma 02.11. |
| D8 | BİLGİ | Rapor evreninde (`universe.csv`) verisi olmayan KPOWR var; K-36 evren farkı (32 fazla, 14 eksik) sürüyor. | açık; karar Kasım sonu (K-36). |
| D9 | BİLGİ | Tatil dosyası yalnız 2026'yı kapsıyor. | açık: 2027 listesi Borsa İstanbul duyurusundan (genelde aralık) eklenecek. |
| D10 | BİLGİ | `likidite`/`islem_tl` bugünkü seansı da içeren 20 günlük ortalama. Talimat "önceki 20 tam seans" diyor. Kırılımda (`yuksek_20g`) ve göreli hacimde bugün zaten hariç. | ✅ v0.88.0: eleme tabanı önceki 20 seans, bugün hariç (K-45). Görüntülenen `islem_tl` alanı aynı kaldı. |

## Hesap tanımları talimata göre

| Tanım | Durum |
|---|---|
| RSI14 | Wilder (ta `RSIIndicator`). |
| ATR14 / ADX14 | Wilder. Hızlı sürüm kütüphaneyle bit bit aynı (test). |
| EMA kesişimi | Yalnız önceki kapanışta ilişki tersken. |
| Kırılım | `kapanis > max(yüksek[t-20..t-1])`; bugün hariç. |
| Göreli hacim | Önceki 20 (veya 10) seansın ortalamasına oran; bugün hariç. Sıfır hacim: D3. |
| Likidite | D10. |
| Sinyal → işlem | Kapanış sinyali ertesi açılışta işlenir. Karne, araştırma ve sanal köprü aynı. |

## Kullanıcıdan gereken kanıt (BENİM ADIMLARIM)

PC tarafını doğrulamak için 29.10 otomatik kurulumundan sonra şunları gönder:
1. `/durum` ekran görüntüsü (kişisel dosyalar, yedek, şema, sürüm).
2. `/performans` ekran görüntüsü (sanal portföy ve canlı ölçüm).
3. PowerShell'de `C:\Projeler\QuantBIST` içinde:

   ```
   .venv\Scripts\python.exe -m core.backup --test-restore
   ```

   Çıktıyı yapıştır. Bu komut son yedekleri geçici bir klasöre açar ve SHA kontrolüyle okur. Kişisel dosyalara dokunmaz; yalnız sonucunu yedek testi kaydına (`logs/`) bir satır olarak ekler.

Bunlar gelene kadar bu satırlar "doğrulanamadı" olarak kalır.
