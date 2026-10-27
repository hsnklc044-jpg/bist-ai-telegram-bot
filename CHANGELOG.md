# Sürüm geçmişi

Sade dille: ne değişti, nasıl doğrulandı. Her sürüm CI'da (ruff, tüm testler, v0.54.1'den beri kapsam ≥ %91) geçti; aksi yazılıysa o sürüm kırmızıydı ve bir sonraki düzeltti. Daha eski sürümler: `git log`.

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
