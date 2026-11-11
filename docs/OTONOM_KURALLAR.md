<!-- 11.11.2026'da `C:\Projeler\QuantBIST-araclar\otonom_kurallar.md` dosyasından taşındı (L madde 1); tek kaynak artık bu dosya. -->
# QuantBIST otonom işletim: kurallar ve iş sırası (kullanıcı onayı 10.11.2026)

## ÖNCELİKLİ KURAL (kullanıcı talimatı, 10.11.2026 16:40; bu dosyadaki her şeyden önce gelir)
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
- GitHub API kimliksiz ve saatte 60 istek: CI'a en fazla üç dakikada bir bak; durum için mümkünse `git fetch` kullan.
- Commit mesajı sonuna: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
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
Rapor: her kurulumdan sonra tek satır (sürüm, SHA, CI bağlantısı, canlı sağlık kanıtı); cumartesi haftalık SLO tablosu ve olgunluk yüzdeleri. Öncelik sırası ve "boş iş üretme" kuralı geçerli.

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
