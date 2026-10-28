# Sürüm geçmişi

Sade dille: ne değişti, nasıl doğrulandı. Her sürüm CI'da (ruff, tüm testler, v0.54.1'den beri kapsam ≥ %91) geçti; aksi yazılıysa o sürüm kırmızıydı ve bir sonraki düzeltti. Daha eski sürümler: `git log`.

## v0.68.1 – 28.10.2026
- v0.66–v0.68 toplu taramasında iki düzeltme:
  - Güncelleyici, GitHub API'ye özel başlığı zip ve sürüm dosyası isteklerine de gönderiyordu. Zip indirme bu başlıkla hiç denenmemişti; ilk gerçek kurulumda reddedilebilirdi. Başlık artık yalnız API isteğinde.
  - Alarm dosyası bozuksa `/alarm` cevap vermek yerine hata veriyordu. Artık dosyanın okunamadığını söylüyor ve dosya düzelene kadar hiçbir şey yazmıyor.

## v0.68.0 – 28.10.2026
- PC güncelleyicisi depoya alındı (`scripts/guncelle.py`, `scripts/bildir.py`). Artık yalnız GitHub'da CI'ı yeşil olan sürümü kuruyor ve her sonucu (kuruldu, kurulmadı, geri alındı, hata) Telegram'a "🤖 Otomasyon" olarak yazıyor. Yeni sürüm yoksa sessiz kalıyor.

## v0.67.0 – 28.10.2026
- Araştırma döngüsü a4 ön kayda alındı (H4 eşit ağırlık, H5 düşük işlem hacmi). Kurallar yazıldı ve yalnız yapay veriyle test edildi. Haftalık araştırma bu taramayı ön kaydın izin verdiği 27.04.2027'den önce çalıştırmaz; o tarihten sonra kendiliğinden çalıştırıp sonucu `a4` ailesi olarak kaydeder.

## v0.66.0 – 28.10.2026
- `/alarm THYAO altında 240` (ya da `üstünde`): kapanış fiyatı alarmı. Akşam raporu o günün kapanışıyla kontrol eder ve geçen alarmı bir kez "🔔" satırıyla söyler. `/alarm` listeler, `/alarm sil 1` siler. Gün içi fiyat izlenmez. Kayıt `data/price_alarms.csv` (yalnız ekleme, günlük yedekte, `/durum` sağlam okunduğunu kontrol eder).

## v0.65.0 – 28.10.2026
- Cuma raporuna eğilim satırı: sanal hesap ve XU100'ün son 20 seansı yan yana küçük metin grafiğiyle (▁▂▃▅▇) ve yüzde değişimle.

## v0.64.0 – 28.10.2026
- `/stres [sanal]`: stres testi. Açık pozisyonlar XU100'ün kayıtlı geçmişindeki en kötü 1, 5 ve 20 seanslık düşüşlerini yaşasaydı her hisse kendi o günkü getirisiyle ne kaybederdi. Dönemleri veri kendisi bulur; bilgi amaçlıdır.

## v0.63.1 – 27.10.2026
- Öz-denetim 3: kritik ya da yüksek bulgu yok. KAP bir hafta için beklenmedik cevap verirse haftalık kontrol artık çökmüyor; atlanan aralık çıktıda "Eksik kontrol" diye yazıyor.

## v0.63.0 – 27.10.2026
- `/yil [2026] [gerçek|sanal]`: yıllık döküm. Yıl içindeki satışların sonucu (FIFO maliyet, komisyon dahil), net temettüler ve ödenen komisyon. Defter dökümüdür, vergi danışmanlığı değildir.

## v0.62.1 – 27.10.2026
- KAP takibinin ilk gerçek çalışmasında HEKTS'in *tahsisli* sermaye artırımı yanlışlıkla "kayıtta yok" çıktı; tahsisli artırım mevcut ortaklara hak vermez, fiyat düzeltmesi gerekmez. Artık "tahsisli: fiyat düzeltme gerekmez" yazıyor.

## v0.62.0 – 27.10.2026
- KAP takibi: her cumartesi araştırma çalışması son 14 günün KAP duyurularından bizim hisselerdeki sermaye artırımı/azaltımı ve temettüleri listeler; `corporate_actions.csv`'de kaydı olmayan sermaye işlemi "KAP'ta doğrula" diye bağlantısıyla gelir. Hiçbir şey kendiliğinden uygulanmaz.

## v0.61.1 – 27.10.2026
- KAP takibinin 1. adımı: KAP'ın (resmî API'si yok) sitesinin kullandığı uç noktaları GitHub'dan deneyen komut ve iş akışı (`kap.yml`). Hiçbir veri değişmez; amaç ayrıştırıcıyı tahmin değil gerçek cevap üzerine yazmak.

## v0.61.0 – 27.10.2026
- `/rapor_tekrar`: kaçan ya da silinen günlük raporu kayıttan yeniden gönderir (`/rapor_tekrar 27.10`). `/start` sık kullanılan komutları düğme olarak açar; Telegram "Menu" bütün komutları listeler.

## v0.60.1 – 27.10.2026
- Bot ve rapor görevi izleme durumunu aynı anda yazarsa biri artık kaybolmuyor. İkinci kaynak çökmüşse bilgi mesajı denemesi rapor görevini en fazla bir zaman aşımı kadar uzatıyor (önce ~3 dk).

## v0.60.0 – 27.10.2026
- `/performans`: canlı ölçüm olgunlaşınca her teknik görünüm için geçmiş (backtest) sonucuyla "uyumlu" mu, yoksa "anlamlı sapma" mı olduğunu kendisi söyler. Sunucu kararının ölçütü veriden önce yazıldı (DECISIONS K-23).

## v0.59.3 – 27.10.2026
- Gerçek alarm tatbikatı başarılı (DOWN 22:53, UP 22:56; Telegram ve e-posta). İkinci kaynak mesajı artık yalnız Yahoo gerçekten cevap vermediğinde gider; Yahoo yalnız gecikmişse beklenir (öz-denetim Ö6).

## v0.59.2 – 27.10.2026
- Dışarıdan izleme açıldı (PC, 22:23). Kurulumda yaşanan iki yazım hatası artık kendiliğinden yakalanıyor: adrese giren boşluk silinir; `< >` örnek metni ya da eksik kod `/durum`'da "biçimi hatalı" diye görünür (adres gösterilmez).

## v0.59.1 – 27.10.2026
- Erken öz-denetim (ROADMAP "Öz-denetim 2"): kritik ya da yüksek bulgu yok. Bir orta bulgu düzeltildi: GitHub'daki iş akışları sonuçlarını aynı dala aynı anda yazmaya çalışırsa haftalık araştırma sonuçları kaybolabiliyordu; artık yeniden denerler.

## v0.59.0 – 27.10.2026
- Araştırma programı (docs/RESEARCH_PROGRAM.md): deneme bütçesi, ön kayıt ve 02.11.2026'dan başlayan ileri holdout. Araştırma araçları artık 30.10.2026'dan sonraki fiyatları göremez; bu kodla zorunlu. Günlük rapor ve canlı ölçüm etkilenmez.

## v0.58.0 – 27.10.2026
- Yahoo bir seansın verisini vermezse o gün sessiz geçmiyor: bir kez kısa mesajla XU100 ve elindeki hisselerin İş Yatırım'daki kapanışları gelir ("yalnız bilgi"). Bu veri fiyat deposuna yazılmaz; sanal emirler ve ölçüm Yahoo'yu bekler.

## v0.57.0 – 27.10.2026
- Tek arıza noktası analizi (docs/SPOF.md): PC, internet, Yahoo, Telegram, GitHub ve diğerleri için B planları.
- Günlük rapor göndermeden önce `logs/reports/rapor_<gün>.txt` dosyasına da yazılır: Telegram uzun süre çökse bile o günün raporu kaybolmaz.

## v0.56.3 – 27.10.2026
- Felaket kurtarma tatbikatı temiz Windows makinesinde baştan sona başarılı (yedekten geri yüklenen dosyalar birebir aynı). Tatbikatın `/durum` çıktısı son bir eksik gösterdi: elle ya da aylık yapılan geri yükleme testi "Yedek" hedefine sayılmıyordu. Artık sayılıyor; başarısızlık da kaydediliyor. Sunucudan çekilen yedeklerin denetimi bu makinenin hedefine sayılmaz (`--no-record`).

## v0.56.2 – 27.10.2026
- Felaket kurtarma tatbikatının 2. çalışması kurulumu geçti; 574 testten biri, Windows'ta WSL'in boş `bash` kabuğunu çalıştırmaya çalıştığı için düştü. Bu test Windows'ta artık atlanıyor (Windows'un kendi betiği `pull_backups.ps1`'dir).

## v0.56.1 – 27.10.2026
- İlk felaket kurtarma tatbikatı gerçek bir hata buldu: belgedeki gibi zip olarak indirilen kodda `setup.ps1`, git klasörü olmadığı için Windows PowerShell'de duruyordu. Düzeltildi; kurulum adımları artık çıkış koduyla denetleniyor. Git'siz kopyada tüm testler geçti.

## v0.56.0 – 27.10.2026
- İzleme alarm tatbikatı: `python -m core.infrastructure.ping --drill` bilerek bir alarm üretir, `--recover` geri alır; adres hiçbir yerde yazılmaz (OPERATIONS §7). Windows'ta aylık felaket kurtarma tatbikatı iş akışı (dr-drill.yml). Olgunluk merdiveni (docs/MATURITY.md): S1 kapandı.

## v0.55.3 – 27.10.2026
- Öz-denetim (ROADMAP). Bakım takvimi BIST 100 dönemlerini çeyreğin ilk işlem gününden de tanıyor; aksi halde Ocak 2027'de kalıcı yanlış uyarı verecekti.

## v0.55.2 – 27.10.2026
- SLO'lar kaydın başladığı günden ölçülür: PC'de rapor ve yedek hedefi, kaydı olmayan eski günleri "eksik" sayıp %25 gösteriyordu. Hiç kaydedilmemiş geri yükleme testi artık "bilinmiyor".

## v0.55.1 – 27.10.2026
- Bot açılışında tek bir DNS hatasının ardından bağlantı gelirse botun açılmaya devam ettiği, python-telegram-bot'un gerçek yeniden deneme döngüsüyle test edildi (eski ayarla aynı test başarısız olur). PC doğrulamaları (D13, v0.45.13–v0.46.0) ROADMAP'e işlendi.

## v0.55.0 – 27.10.2026
- `/durum`'a "Bakım takvimi": BIST 100 üç aylık dönem değişikliği yaklaşınca haber, girilmezse uyarı; Python 3.11 destek sonu.
- El kitabı (docs/HANDBOOK.md), bakım takvimi (docs/MAINTENANCE.md), bu dosya.
- Doğrulama: yeni testler; belgelerin bağlantıları test ediliyor.

## v0.54.1 – 27.10.2026
- Test kapsamı kapısı: %91'in altına düşen sürüm CI'da kırmızı olur. "Kalite" hedefi GitHub'daki son CI sonucunu gösterir.
- v0.54.0'daki kırmızı test düzeltildi (gizli bilgi testi kendi örneğini yakalıyordu).

## v0.54.0 – 27.10.2026 (CI kırmızı; v0.54.1 düzeltti)
- Her pazartesi paket güvenlik taraması (pip-audit). Depoda token, izleme adresi ya da kişisel kayıt olmadığını denetleyen test.

## v0.53.0 – 27.10.2026
- Felaket kurtarma belgesi: sıfır bilgisayara kurulum, aylık tatbikat, token sızarsa. Belgedeki her komutu test denetliyor.

## v0.52.1 – 27.10.2026
- Haftalık kurumsal işlem şüphesi taraması (bedelsiz/bedelli/bölünme olabilecek sıçramalar); hiçbir şey kendiliğinden uygulanmaz.

## v0.52.0 – 27.10.2026
- "Veri doğruluğu" hedefi ikinci kaynağa (İş Yatırım) bağlandı; şüpheli hisseler isimle. Araştırmada şüphelileri dışlama seçeneği.

## v0.51.1 – 27.10.2026
- Her rapor çalıştırması için tek, aranabilir log satırı (`RUN daily … status=…`).

## v0.51.0 – 27.10.2026
- Sağlık hedefleri (SLO): `/durum` ve cuma raporunda son 7 günün rapor teslimi, bot ayakta kalma, veri tazeliği, yedek, kayıt bütünlüğü; ölçülemeyen "bilinmiyor".

## v0.50.0 – 27.10.2026
- Disk dolunca rapor yine gider; saat geri alınınca rapor kilitlenmez. Yönetim belgesi (CHARTER) kaydedildi.

## v0.49.3 – 27.10.2026
- v0.49.2'de kırık bırakılan test düzeltildi.

## v0.49.2 – 27.10.2026 (CI kırmızı; v0.49.3 düzeltti)
- Cuma raporuna haftalık sistem özeti.

## v0.49.1 – 27.10.2026
- `/durum`'a dışarıdan izleme satırı; adres asla gösterilmez.

## v0.49.0 – 27.10.2026
- Uyku/uyanma, geç internet, Excel'de açık dosya, elektrikte yarım kalan satır senaryoları; kesinti tablosu (OPERATIONS §8).

## v0.48.x – 27.10.2026
- Bot açılışta ağ hatasında ~7 dk yeniden dener (v0.48.4). Fiyat düzeltme onay kapısı (v0.48.1). Şüpheli mumları İş Yatırım ile yan yana gösterme (v0.48.2–3). Aşama 3: H2/H3 (v0.48.0) reddedildi.

## v0.47.x – 27.10.2026
- Aşama 3 H1 (düşük oynaklık) reddedildi (v0.47.0). İkinci kaynak yanıt vermezse kontrol erken biter (v0.47.1).

## v0.46.x – 27.10.2026
- Dışarıdan izleme (Healthchecks) kodu (v0.46.0); Windows konsolunda emoji çökmesi (v0.46.1); iki bot çakışması açık bir satırla (v0.46.2).
