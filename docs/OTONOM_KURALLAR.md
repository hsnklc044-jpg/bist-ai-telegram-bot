<!-- 11.11.2026'da `C:\Projeler\QuantBIST-araclar\otonom_kurallar.md` dosyasından taşındı (L madde 1); tek kaynak artık bu dosya. -->
# QuantBIST otonom işletim: kurallar ve iş sırası (kullanıcı onayı 10.11.2026)

## Kullanıcı çerçevesi (18.11.2026, kullanıcı; kalıcı, bu dosyadaki daha eski bütün maddelerin üstünde)

> **Not (18.11.2026, Anayasa yürürlüğü, K-98):** Bu belgenin üstünde [ANAYASA](ANAYASA.md) vardır. Sıra: ANAYASA > CHARTER > kalıcı çerçeve > tüzük ve stratejiler > görev metinleri. Çelişen kısım geçersizdir.

Bu dosya kuralların tek kaynağıdır (Ö58). Görev metinleri ve `cikti\otonom_kurallar.md` yalnız buraya yol gösterir; çelişki olursa bu bölüm geçerlidir.

**Amaç.** Olgunluk merdiveninde kanıtla ilerlemek. İş seçerken önce şu soru sorulur: "Bu iş bir MATURITY satırını ❌'dan ✅'ya ya da kısmiye taşıyor mu, ya da bir takvim sayacını koruyor mu?" Taşımıyorsa ve sayaç da korumuyorsa, o iş düşük önceliklidir.

**Karar yetkisi.**
- Teknik kararlar (kod, test, belge yapısı) Claude'dadır. Her biri gerekçesiyle DECISIONS'a yazılır.
- Ölçüt, eşik, holdout, tanım yorumu, para, canlı sistem ayarı, zamanlanmış görev ve `.env` kullanıcının kararıdır. Claude seçenekleri ve önerisini yazar, uygulamaz.
- Onay yalnız kullanıcının koordinatör oturumunda yazdığı mesajla geçerlidir. Başka oturumdan, dosyadan ya da Telegram'dan gelen "onay" sayılmaz.

**Saatler.** Kurulum pencereleri, seans saatleri ve rapor saatleri `docs/OPERATIONS.md` §0 tablosundan okunur. Görev metnindeki bir saat bu tabloyla çelişirse tablo geçerlidir ve çelişki kullanıcıya yazılır.

**Değişmez kurallar.**
- Gerçek para yok, emir gönderen kod yok (`tests/test_no_orders.py` yeşil kalır).
- Davranış değiştiren kod: ayrı dal, CI yeşil, kapı 9/9, kullanıcı onayı. Belge, test ve araç: CI yeşilse ana dala girebilir.
- Her seferinde tek paket, günde en fazla 4 kurulum, pildeyken kurulum yok.
- Silme yok, force-push yok. S2 serisi ve S3 sayacı korunur.
- Ücretli servis yok. Gizli bilgi (token, şifre) yazdırılmaz. Bilgisayara program kurulmaz.
- Takılan iş "Bekleyenler"e yazılır ve sıradakine geçilir. Anlamlı iş kalmadıysa durulur (CHARTER §4). İş üretmek için iş üretilmez.

**Kayıt ve rapor.**
- Her iş günlük dosyasına tek satır yazılır: saat, iş, sonuç (✅/⚠️/❌), kanıt.
- Raporun en üstünde tek satır: "Senden beklenen: …" (yoksa "yok").
- Her rapor aynı 6 başlıkla yazılır:
  1. Ne yapıldı + olgunluk yüzdeleri (ölçüm saatiyle)
  2. Canlıya çıkanlar (SHA, CI numarası, sağlık)
  3. Onay bekleyenler (her biri için tek cümle + risk)
  4. Kullanıcının vermesi gereken kararlar (seçenekler + öneri)
  5. Verilen sözler tablosu
  6. Sıradaki ilk 3 iş

**Görev şablonu** (kullanıcı her görevi bununla verir; köşeli parantezleri o doldurur):

```
GÖREV: [gece / gündüz / hafta sonu], [bitiş saati]'ne kadar.
ODAK: [örnek: S2 engelleri ve S3 sayacının korunması]
BU SEFER ÖZEL: [örnek: K-84 Kasım dosyası gelirse karşılaştırmayı çalıştır]
Kalıcı çerçeve geçerli. Rapor [saat]'te, [dosya adı]'nın en üstünde.
```

## Yetki devri (18.11.2026, kullanıcı; DECISIONS K-101)

Sahibin kendi yazısıyla verildi (koordinatör oturumu). [ANAYASA](ANAYASA.md)'ya bağlıdır: çelişen kısım geçersizdir ve sahibe bildirilir (bkz. 5).

**1. Devredilenler: sorma, yap, raporda bildir.**
- Belge, test ve araç paketlerinin kapıdan geçirilmesi (CI yeşil, kapı 9/9).
- Sahibin daha önce onayladığı kuyruğun sırası ve zamanlaması.
- Hata düzeltmeleri: davranışı yalnız hatayı gidermek için değiştiren ve önce kırmızı testle kanıtlanmış düzeltmeler.
- Belge birleştirme ve sadeleştirme. Eski belgeler arşivlenir, silinmez.
- Kontrollerin (KT-01…KT-10) ve kanarya testlerinin eklenmesi.

**2. İtiraz süreli devir: öner, 48 saat bekle, itiraz yoksa yap.**
- Botun davranışını değiştiren küçük kodlar (yeni özellik değil, mevcut özelliğin iyileştirilmesi).
- 90 günlük döngü önerisindeki iş paketleri.
- Kullanılmayan bir özelliğin kaldırılması.

Öneri Telegram'dan tek mesajla bildirilir. Sahip 48 saat içinde "dur" yazarsa yapılmaz.

> **Anayasa notu (K-101).** Bu sınıf, sahibin sessizliğini onay sayar. ANAYASA Md. 8 ise "sessizlikten onay çıkarılamaz" der. Md. 8 çekirdek değildir (Md. 18); Md. 17 usulüyle değiştirilebilir. Bu değişiklik yapılana kadar 2. sınıf şöyle uygulanır:
> - Öneri Telegram'dan tek mesajla gider.
> - İş, sahip açıkça "evet" yazınca yapılır.
> - 48 saat içinde cevap gelmezse iş yapılmaz ve "Bekleyenler"e yazılır.
>
> Md. 8'in değiştirilmesi önerisi K-101'dedir. Karar en erken 25.11.2026'da verilebilir (7 gün soğuma süresi).

**3. Devredilmeyenler: her zaman sahibin kararı; sessizlik onay sayılmaz.**
- Gerçek para, emir kodu, başkasına tavsiye.
- Eşik, ölçüt, holdout ve ön kayıt; sayaç ve tanım yorumları.
- Kapsam değişikliği, yeni hipotez, S-seviyelerinin kapanışı.
- `.env`, zamanlanmış görevlerin saati ve izinleri, bilgisayar ayarları.
- Bu yetki devrinin ve anayasanın değişmesi.

**4. Güvence.**
- Her raporda bir "Devirle yaptıklarım" bölümü bulunur: ne yapıldı, hangi madde, kanıt.
- Devirle yapılan bir iş SLO ihlaline ya da sapmaya yol açarsa o iş türü devirden çıkar ve sahibe sorulur.
- Bir işin hangi sınıfa girdiği belirsizse iş 3. sınıf sayılır ve sahibe sorulur.

**Onay (18.11.2026, K-102).** Sahip bu metni ayrıca onayladı. 2. sınıfın 48 saat kuralı için ANAYASA Md. 8 değişikliği Md. 17 usulüyle başladı; karar en erken 25.11.2026'da sahibe sunulur.

**5. Anayasayla ilişki (K-101).**
- **1. sınıf:** sahibin açık yazısıyla verilmiş, iş türüyle sınırlı bir ön onaydır (Md. 8). Yetkiyi Claude kendinde varsaymaz (Md. 1); her iş raporda bildirilir. Bu sınıf K-100'deki "Ç3 = (b)" kararının yerine geçer. Ç2 (şüphede sor) ve Ç4 (silme yok) aynen sürer.
- **2. sınıf:** yukarıdaki anayasa notuna göre uygulanır.
- **3. sınıf:** ANAYASA Md. 7 ile aynıdır.

## Dönem kuralı: "Az yeni şey, çok ölçüm" (19.11.2026–18.12.2026, kullanıcı; DECISIONS K-106)

Yürürlük: 19.11 sabahının sözleri tamamlandıktan sonra (08:40 K kurulumundan sonra).
1. **Dondurma.** Yeni yönetim belgesi, strateji, seviye ya da özellik açılmaz. Açık konular (S6, Md. 8 değişikliği ve benzerleri) beklemeye alınır ve 18.12'den sonra tek pakette sunulur.
2. **Yapılabilecek dört iş:** (a) onaylı kurulum zinciri, (b) sayaçların korunması (S2 07.12, S3 18.12), (c) gerçek hata düzeltmesi, (d) veri kalitesi. Bu dördüne girmeyen iş Bekleyenler'e yazılır.
   - **K-108 ile beşinci iş türü:** (e) dalga hazırlığı. Yalnız test, araç ve belge; dalda kalır. Sıra: veri kalitesi (#2, #8), sentetik veriyle doğrulanan tek komutluk ARS-1 test hattı, 1. dalga verisi (nakit getiri, BIST100 tarihsel üyelik), T1/T5 ön kayıt taslakları, 2. dalga veri araştırması, maliyet parametre önerisi. Kota %70'i geçerse son ikisi bırakılır. **ALTIN KURAL:** havuzdaki aday kurallar (T1–T5, F1–F8, C1) geçmiş ya da canlı veride çalıştırılmaz; araçlar yalnız sentetik veriyle sınanır; ihlal KRİTİK sapmadır. 18.12'de tek sayfalık hazırlık dosyası sunulur.
3. **Veri kalitesi önce.** VERI_DENETIMI bulguları sırayla ele alınır: D-1, D-2, D-4. Önce etki ölçülür, sonra düzeltilir. Davranış değiştiren düzeltme ayrı dalda kalır ve onayla girer. K-93 ya da K-94'ü etkileyen bulgu düzeltilmez, karar talebi olur. Hedef: 06.01.2027'den önce açık YÜKSEK bulgu kalmaması.
4. **Sadeleştirme (sınıf 1).** Aktif belgeler BELGE_HARITASI'ndaki 4 katmana iner; eskiler arşivlenir, silinmez. Çalışma klasörleri haftada bir temizlenir; dal silinmez. Kullanılmayan özellik için kaldırma önerisi Bekleyenler'e yazılır.
5. **Sahibin zamanı:** haftada en fazla 30 dk (bir kısa kontrol ve ayda bir karar paketi). Her hafta "Senden beklenen" madde sayısı ve onay sayısı rapora yazılır; hedef iki hafta üst üste aşılırsa sadeleştirme önerilir. Sohbette en fazla 10 satır, ayrıntı dosyada.
6. **Doğrulama ve dil.** "Bitti" yalnız kanıtla söylenir. Saatler Get-Date'ten okunur. Önemli hesap ve düzeltmeler kırmızı takımdan geçer. İyimser dil kullanılmaz; "kanıt gösteriyor" ile "henüz bilinmiyor" ayrı yazılır. Olumsuz S4 sonucu başarısızlık değildir (senaryo B).
7. **Ritim:** pazartesi en fazla 3 işlik plan; cumartesi SLO satırı ve tek sayfalık özet; ayın son günü karar paketi; Telegram yalnız gerçek sorunda.

## Sahibin bakışı (19.11.2026, kullanıcı; DECISIONS K-107)

Yürürlük: K-106 ile birlikte, 19.11 08:40 K kurulumundan sonra.
1. **Çıkış kararı, Mayıs 2027 (ön kayıtlı):** 27.04.2027 taramasından sonra, en geç 31.05.2027'de tek sayfalık "Devam / Bakım modu" sayfası sunulur. ARS-1 testlerini (maliyet sonrası, çoklu test düzeltmeli, rastgele kıyaslı) geçen en az bir S4 kuralı varsa DEVAM (S5 kâğıt izleme); yoksa BAKIM MODU (senaryo B). Ölçüt sonuç görüldükten sonra gevşetilmez; "biraz daha veri / bir parametre / bir hipotez daha" gerekçe değildir. Yeni hipotez yalnız yeni ön kayıt ve yeni veri dönemiyle açılır.
2. **Gerçek para ayrımı (Md. 4):** hiçbir çıktı gerçek para kullanımını önermez, ima etmez, hesaplamaz ("X TL yatırsaydın" yok). Sonuçlar yalnız oran, olasılık ve kâğıt portföy olarak yazılır.
3. **Sahibin dinlenmesi:** 23:00–07:00 arası sahipten karar, onay ya da işlem istenmez. Gece Telegram'ı yalnız ANAYASA KRİTİK durumları içindir. Sohbette yeni iş ya da ileri adım önerilmez; öneriler aylık karar paketinde gelir. Sahibin haftalık süresi haftalık özete tek satır olarak girer.
4. **Kota şeffaflığı:** aylık karar paketinde tek satır: ayın ortalama ve en yüksek haftalık kotası, önceki ayla karşılaştırma. Plan önerisi ya da yorum yapılmaz.
5. **Düşük bakım:** varsayılan hâl sessizce çalışan deneydir. Başarı, bir haftayı sahibe soru sormadan ve sorunsuz geçirmektir. Aylık karar paketinde tek satır: aktif belge, açık dal ve kural sayısı, önceki aya göre.

## Öğrenci döngüsü (K-117)

19.11.2026, sahibin talimatı; kalıcı. Saatler OPERATIONS §0 ve §0a'dadır.
1. **Sabah önce onarım.** Günün ilk turu önce `docs/DERS_DEFTERI.md`'deki açık kritik ve orta bulguları ele alır, sonra "anlaşılamadı" etiketlileri araştırır, sonra o günün 1/7/30 gün yeniden kontrollerini yapar. Anlaşılamadı sürerse sahibe 07:00–23:00 arasında, o günün bütün belirsizlikleri tek mesajda toplanarak sorulur (K-107 (3) ve (5): soru az tutulur).
2. **Açık kritik/orta varken yeni aşama yok** (gerekçeyle ertelenmiş bulgu hariç). Yeni özellik, dalga ya da madde açılmaz. Kapatılamayan bulgu gerekçesiyle ertelenir ve deftere yazılır. Düşükler sıraya girer.
3. **Düzeltme + koruma.** Her düzeltmeyle aynı hatayı yakalayan bir test ya da otomatik kontrol eklenir; "dikkat ederiz" koruma değildir. Kritik ve orta bulguda 5 Neden yazılır, kişiye değil sürece bakılır.
4. **Tekrar eden hata → süreç değişikliği.** Aynı tür hata ikinci kez görülürse ya da yeniden kontrolde geri gelirse bulgu "tekrar eden hata" olarak (yeniden) açılır ve süreç değiştirilir.
5. **Ders → kontrol maddesi.** Her dersten bir madde `docs/KAPI_KONTROL_LISTESI.md`'ye eklenir; her `surum-kapisi` çalışmasından önce liste okunur ve işaretlenir.
6. **Aşama kapısı.** Bir aşama (Dalga 1, Dalga 2, 18.12 hazırlığı vb.) ancak şunlarla biter: bütün maddeler kanıtla bitmiş; o aşamaya ait açık kritik/orta bulgu yok; tam test paketi yeşil; o aşamada kapanan bulguların 7. gün kontrolleri geçmiş. Geçiş DECISIONS ve KARAR_DEFTERI'ne yazılır, sonra yeni aşama açılır.
7. **Hata bütçesi (varsayılan; eşikleri sahip değiştirir).** Bir haftada 1'den fazla kritik ya da 4'ten fazla orta yeni hata ya da herhangi bir tekrar eden hata olursa ertesi hafta yalnız onarım haftasıdır: yeni özellik ya da aşama açılmaz. Durum haftalık karnede yazılır.
8. **Akşam tekrarı** günün son kurulumunun sağlık kontrolünden hemen sonra yapılır (AAR dört soru, kanıtla); hata yoksa "Bugün yeni hata yok."
9. Bu bölüm K-106 dönemi iş türlerini (a)–(e) genişletmez. Açık kritik/orta bulgu varken ya da yalnız onarım haftasında da onaylı kurulum zinciri ve sayaçların korunması (S2, S3) sürer; durdurulan, (e) dalga hazırlığına yeni madde açmak ve yeni özelliktir.
10. **Kapı listesi uygulaması.** `scripts/surum_kapisi.py` bu listeyi bugün okumuyor; kapıya bağlanması ayrı bir koddur. O zamana kadar robot listeyi kapıdan önce okur ve işaretlemeyi kurulum günlüğüne yazar. Haftalık karne ekleri de bot kodunda değil, robotun haftalık raporundadır.

## Saat kuralı (19.11.2026, kullanıcı; yetki devri sınıf 1, kalıcı)

1. Kayıtlara yazılan her saat o anda sistem saatinden okunur (`Get-Date`, `date`, `datetime.now()`). Saat tahmin edilmez.
2. Geçmiş bir olayın saati kendi kanıtından alınır: commit zamanı, dosya zamanı, olay günlüğü, log satırı. Kanıt yoksa "saat bilinmiyor" yazılır.
3. Yanlış yazılmış saat silinmez, üzerine yazılmaz; altına "Düzeltme: gerçek saat HH:MM (Get-Date / commit zamanı)" satırı eklenir (ANAYASA Md. 11).
4. Söz verilen saatler gerçek sistem saatine göre işler; bekleme, saati okuyan bir betikle yapılır.
5. Neden: 19.11 gecesi koordinatör, kayıtlara iş süresinden tahmin ettiği saatleri yazdı (ör. gerçek 00:35 yerine 01:55). Ayrıntı: `docs/NIGHT_LOG_2026-11-19.md`.

## Robotun görevi ve yetkisi (17.11.2026, kullanıcı)
Robot (07:00, 20:15, hafta sonu 13:00 turları) bütün ilerleme işlerini kullanıcıyı beklemeden yürütür: DECISIONS K-88 rotası ve `siradaki-is` sırasıyla sıradaki işi seçer; dal ve worktree açar; araştırma/ölçüm öncesi `on-kayit`; önce başarısız test, sonra düzeltme; CI; `surum-kapisi` ile birleştirme; kurulum sonrası sağlık (≥3 sinyal, ERROR 0); OTONOM_RAPOR.md'ye ve 21:00 özetine K-88 §6 raporu. Kullanıcıya yalnız bilgi verir; gerçekten kullanıcı kararı gereken bir şey çıkarsa tek soru yazar ve sıradaki işe geçer.
Sınırlar değişmez: CHARTER kesin sınırları (K-54), kapı geçmeden birleştirme yok, canlı klasöre elle yazma yok, güvenlik denetimi reddederse başka yol denenmez. Güncelleyici, yedek ve geri yükleme değişikliklerinin hafta sonu birleştirmesi kullanıcının tek komutuyla olur (K-88 §5); robot bunları hazırlar (aynı SHA'da dr-drill yeşil, kapı tam) ve hazır olduğunu bildirir. Para, token ya da hesap gerektiren adımlar ve kuralların kendisini değiştirmek kullanıcıya kalır.

## ~~ÖNCELİKLİ KURAL~~ — GEÇERSİZ, tarihsel kayıt (kullanıcı talimatı, 10.11.2026 16:40)
> **18.11.2026 işareti (öz-denetim 11, Ö59):** Bu bölüm artık geçerli değil. Yerine aşağıdaki "10.11.2026 ~19:27 — Tam otonom + robot modu YENİDEN GEÇERLİ" bölümü, OPERATIONS §5a onay devri (sürüm kapısı) ve en üstteki "Robotun görevi ve yetkisi (17.11.2026)" geçti. Metin değiştirilmedi, yalnız işaretlendi; kural değişikliği yok.

- PR birleştirme, bot dalına her türlü push (ileri sarma dahil), canlı kurulum ve dağıtım için HER SEFERİNDE kullanıcının açık onayı gerekir. Aşağıdaki "Birleştirme kapısı" yalnızca ön koşuldur, onay yerine geçmez.
- Haftalık tur: dalı hazırla, testleri ve CI'ı çalıştır, raporla; BİRLEŞTİRME. Hazır dalı `cikti\OTONOM_RAPOR.md` içinde "ONAY BEKLİYOR" olarak listele (dal, SHA, CI bağlantısı, değişen dosyalar).
- Canlı görev ayarlarını (zamanlanmış görevler, Windows görevleri, iş akışları) değiştirmek gerekiyorsa önce kullanıcıdan onay iste.
- İş sırası: 1) 9 Kasım yedeği (tamamlandı), 2) çalışma süresi incelemesi (tamamlandı), 3) üst alım fiyatı (yalnızca dal; birleştirme yok).

Bu dosya iki zamanlanmış görevin tek kaynağıdır: `quantbist-gunluk-bakim` (salt okunur) ve `quantbist-haftalik-gelistirme` (sınırlı yazma). Kullanıcı ikisini de açıkça onayladı. Kuralı değiştirmek için kullanıcının açık onayı gerekir; görev bu dosyayı kendisi gevşetemez.

## Ortam
- Canlı bot klasörü: `C:\Projeler\QuantBIST-yeni` (güncelleyici yönetir). Orada dosya değiştirme, dal değiştirme, commit yok.
- Geliştirme kopyası: `C:\Projeler\QuantBIST-araclar\wt-restore` (git worktree). Her iş için bot dalının ucundan yeni dal aç: `claude/otonom-<kısa-ad>`.
- Bot dalı: `claude/borsa-bot-creation-n7nmc9`. Birleştirmek = bu dalı ileri sarmak (`git push origin <sha>:refs/heads/claude/borsa-bot-creation-n7nmc9`); güncelleyici kurar.
- Python: `C:\Projeler\QuantBIST-yeni\.venv\Scripts\python.exe`; test: `python -m pytest -q -p no:cacheprovider`; lint: `python -m ruff check .`; her komutta `PYTHONPATH=.` ve `PYTHONIOENCODING=utf-8`.
- GitHub API kimliksiz ve saatte 60 istek: CI'a en fazla 10 dakikada bir bak (istek kotası oturumlar arasında paylaşılıyor; 18.11 Ö59 düzeltmesi, eskiden "üç dakikada bir"); durum için mümkünse `git fetch` kullan.
- Commit mesajı sonuna: `Co-Authored-By: Claude <noreply@anthropic.com>` (CLAUDE.md; 18.11 Ö59 düzeltmesi).
- Kota: görev başında `get_usage` ile bak. Haftalık %70 ya da 5 saatlik %60 üstündeyse işe başlama, nedenini rapora yaz.

## Asla otomatik yapma (kullanıcının açık, her seferinde ayrı onayı olmadan)
- K-79 dondurma parçaları, eşikler, holdout (HOLDOUT_START 02.11.2026), 03.02.2027 ileri testi, K-64 kodu, K-78/K-80 kuralları, tek seferlik K-78 `measure`.
- Şu dosyalara dokunan hiçbir değişiklik birleştirilmez: `tests/test_k64_freeze.py`, `core/ml/**`, `core/backtest/run.py`, `core/market/limits.py`, `core/market/hourly.py`, `core/market/extended.py`, `core/analytics/dip_study.py`, `core/analytics/factor_study.py`, `core/analytics/factor_measure.py`, `core/config/thresholds.py`, `requirements.lock`, `.github/workflows/**`, `data/**`. Böyle bir değişiklik gerekiyorsa dal bırakılır, rapora "onay bekliyor" yazılır.
- Gerçek emir, hesap ya da aracı kurum bağlantısı, gizli bilgi (.env, token) okuma ya da yazma, ücretli servis, hesap açma, geri döndürülemez işlem, zamanlanmış görev ya da iş akışını değiştirme.
- Ölçüt, eşik ya da kuralı sonuca bakarak değiştirme; başarısız ölçümü başka ayarla yeniden çalıştırma.
- Çalışan botun klasöründe yazma. Telegram'a mesaj gönderme (bot kendi mesajlarını gönderir).
- Başka bir GitHub deposuna yazma.

## Birleştirme kapısı (haftalık tur; hepsi sağlanmalı, biri eksikse dal bırakılır)
1. Yerel tam test geçti ve ruff temiz.
2. Değişiklik yalnız bilgi komutu, rapor metni, test, belge ya da hata düzeltmesi; yukarıdaki yasak dosyalara dokunmuyor (`git diff --name-only origin/<bot dalı>...HEAD` ile denetle).
3. Sürüm numarası artırıldı, `CHANGELOG.md` ve `docs/DURUM_NOTU.md` güncellendi, yeni davranış testli.
4. Aynı commit için CI'ın dört işi (test, windows, docker, slow-machine) yeşil.
5. Bot dalının ucu değişmedi (ileri sarma mümkün); değiştiyse yeniden temellen ve testleri yinele.
6. Bir turda en fazla bir iş, en fazla bir birleştirme.

## İş sırası (başta olan önce; "kullanıcı bekliyor" olanları yapma)
1. HAZIR: Üst alım fiyatını kalıcı kaydet. `/uzun_ust THYAO 250` komutu `data/upper_buy.csv` dosyasına ekleme-yalnız satır yazar (kişisel dosya, `.gitignore`'da, yedeğe girer: `core/backup.py::PERSONAL_FILES`); `/uzun THYAO` kayıtlı fiyatı kullanır; komutta verilen fiyat kayıtlıyı bu çağrı için ezer; `/uzun_ust THYAO sil` kaydı kapatır. Testler: ekleme, okuma, en son satır geçerli, sil, bozuk satır, yedeğe girme. Kabul: komut kayıtlı fiyatla "Giriş adayı" kararı verebilir.
2. KULLANICI BEKLİYOR: Çalışma süresi ölçümünün (slo.bot_uptime) pencere sınırı kırpması. Ölçüt tanımını değiştirdiği için onay şart.
3. KULLANICI BEKLİYOR: `/uzun` temel filtre, sektör farkı, lot, A/B/C geçmiş testi (finansal veri, sektör sınıflaması, risk bütçesi, portföy sınırı, çıkış kuralı gerekir).
4. KULLANICI BEKLİYOR: Veri doğruluğu için bağımsız fiyat kaynağı (aracı kurum dosyası ya da koşulları doğrulanmış kaynak).
5. KULLANICI BEKLİYOR: K-78 `snapshot` (en erken 11.11.2026, GitHub Actions'ta kullanıcı başlatır) ve `measure` (ayrı onay).
Hazır iş yoksa tur salt okunur çalışır: son commit'leri gözden geçir, belge tutarsızlığı ve test boşluğu ara, bulguları raporla; kod değiştirme.

## Rapor
- Günlük bakım: `C:\Projeler\QuantBIST-araclar\cikti\GUNLUK_DURUM.md` (en yeni üstte, son 14 gün; sorun varsa ilk satır `SORUN:`).
- Haftalık tur: `docs/DURUM_NOTU.md` içine "Otonom tur (tarih)" bölümü (ne yapıldı, kanıt, dal ve SHA, CI, birleşti mi, onay bekleyenler) ve `cikti\OTONOM_RAPOR.md`.
- Bir tur yarıda kalırsa durumu, açık işi ve sıradaki somut adımı aynı yere yaz.
- Dürüst raporla: çalıştırılmayan kontrol NOT_RUN, erişimle engellenen iş BLOCKED yazılır; başarı yalnız çalıştırılmış kanıtla belirtilir.

## Onay yetkisi devri (10.11.2026, kullanıcı kararı) — birleştirme ve canlı kurulum
Birleştirme ve canlı kurulum için onay beklenmez; aşağıdaki kapının HEPSİ sağlanırsa birleştirilir. Biri eksikse birleştirilmez, neden yazılır, sonraki işe geçilir.
1. Birleştirilecek SHA'da tam test ve ruff yerelde geçti; aynı SHA'nın CI'ı yeşil.
2. Canlıdaki sürüm sağlıklı: canlı klasör SHA ve sürüm doğru, "Telegram bot started" satırı var, kurulumdan beri en az 3 yaşam sinyali ERROR olmadan geldi.
3. Önceki kurulumdan beri hiçbir SLO kötüleşmedi.
4. Kurulum hafta içi 09:40–18:15 seans saatlerine ve 18:00–19:30 rapor penceresine denk gelmiyor (güncelleyici :40'ta kurar; birleştirme zamanı buna göre seçilir).
5. Aynı anda yalnız bir sürüm bekliyor; günde en fazla 3 canlı kurulum.
Yine kullanıcıya sorulur: scripts/guncelle.py, yedek, geri yükleme ya da kişisel kayıt biçimi değişikliği; dosya/klasör silme (eski sürüm temizliği dahil); .env, token, dış izleme ayarları. Yukarıdaki yasak dosya listesi ve K-79/K-78/K-80/holdout kuralları da aynen geçerli.
Asla: gerçek para, aracı kurum, emir, al/sat önerisi, git geçmişini yeniden yazma (bot dalına force push yok).
Sorun çıkarsa (bot başlamaz, ERROR, SLO düşer): önceki sürüme dön (bot dalına revert commit'i, ileri sarma; geçmiş yeniden yazılmaz), tüm birleştirmeleri durdur, kullanıcıya tek paragraf rapor; kullanıcı "devam" diyene kadar kapı kapalı.
Rapor: her kurulumdan sonra tek satır (sürüm, SHA, CI bağlantısı, canlı sağlık kanıtı); cumartesi haftalık SLO tablosu ve olgunluk yüzdeleri. Cumartesi 21:00'den sonraki ilk turda `python scripts/donem_kopyala.py` çalıştırılır ve yeni `docs/PERIODS/` dosyası dalda commit'lenir (K-17). Öncelik sırası ve "boş iş üretme" kuralı geçerli.

## Güncelleme (10.11.2026 ~18:30): hızlı sürüm + tam otonom talimat
- Kapı: rapor penceresi 18:00–20:00; hafta sonu/tatil açık; günde en fazla 4 kurulum; tek paket. Uygulama: worktree'den `scripts/surum_kapisi.py` (dal claude/skills ve sonrası). Zincir halindeki dallar tek paket (uç birleştirilir).
- Paket dışı: güncelleyici/yedek/geri yükleme (tek başına, yalnız hafta sonu, önce dr-drill, güncelleyicinin önceki sürümü C:\Projeler\QuantBIST_otomasyon\ altına); kişisel kayıt biçimi yalnız geriye uyumlu + geri yükleme testi.
- Silme: yalnız yeniden üretilebilenler (eski sürüm klasörleri/zip'ler, son 5 kalır; birleşmiş ya da 7 günden eski ve dalı uzakta worktree'ler). Kişisel kayıt, yedek, logs/, data/, .env asla.
- Durdurma: /otonom_dur (data/otonom_dur.flag), otomatik fren cikti\otonom_dur.flag; bayrak varken birleştirme/kurulum/silme yok. Freni yalnız kullanıcı kaldırır.
- Kullanıcıya kalan: .env, token, ödeme, hesap, dış izleme; frende "devam".

## 10.11.2026 ~19:20 — "QuantBIST Nirvana" ana talimatı (en yeni; daha katı olan geçerli)
- PR birleştirme, korunan dala yazma, canlı dağıtım, Windows görev değişikliği, canlı Telegram/WhatsApp değişikliği, ücretli servis, gizli anahtar, geri dönüşü zor silme/taşıma: AÇIK ONAY gerekir. Bu, önceki otomatik kapı yetkisini askıya alır; kapı betiği yalnız denetim için kullanılır, birleştirme kullanıcı onayıyla.
- Araştırma, test, dal geliştirme, belge, rapor: bağımsız.
- Denetim raporu: cikti\DENETIM_2026-11-10.md.

## 10.11.2026 ~19:27 — Tam otonom + robot modu YENİDEN GEÇERLİ (en yeni talimat; Nirvana'daki onay şartının yerine geçer)
- Kapı ve paketleme kuralları (hızlı sürüm) ile tam otonom kurallar geçerli; kullanıcıya soru sorulmaz, yalnız bilgi verilir. Sana kalanlar: .env, token, ödeme, hesap, dış izleme; fren "devam".
- Robot döngüsü: fren → durum → CHARTER §4 iş → worktree'de dal (önce başarısız test) → CI (arka planda) → kapı + paket → sağlık → docs/ROBOT_LOG.md satırı → baştan. Durur: iş kalmadı (yalnız zaman bekleyenler), fren, ya da sıradaki adım kullanıcıya kalan.
- Kilit: C:\Projeler\QuantBIST_otomasyon\robot.lock (başlama saati); varsa ikinci robot başlamaz; 6 saatten eskiyse devralınır ve raporlanır.
- Nirvana denetim raporu (cikti\DENETIM_2026-11-10.md) iş listesi olarak geçerli.

## 10.11.2026 20:05 — Kuyruk sınırı ve paket planı (kalıcı)
- Canlıya çıkmamış sürüm sayısı 5'i geçerse yeni dal açılmaz; önce kuyruk canlıya çıkarılır; yalnız kurtarma ve kuyruktaki dalların düzeltmeleri.
- Kuyruk küçük paketlerle çıkar; her paket bir öncekinin canlıda sağlıklı olduğu görülmeden birleştirilmez. Paket sorun çıkarırsa önceki pakete dön, sonrakileri durdur, fren kuralları.
- 10.11 planı: 114 (20:40) → Paket 1: 115–119 → Paket 2: 120–122 (/otonom_dur ve /otonom_devam doğrulanır) → Paket 3: 123–124 bot tarafı. 124'ün bildir.py kısmı hafta sonu, tek başına.
