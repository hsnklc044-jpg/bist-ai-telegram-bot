---
name: siradaki-is
description: QuantBIST'te sıradaki işi CHARTER §4 karar algoritmasıyla seçip yapar. Yeni oturumda ya da zamanlanmış "QuantBIST otonom" çalışmasında kullan; koşulu oluşan iş yoksa bekleyenleri listeleyip durur, yeni özellik önermez.
---

# Sıradaki iş

## Önce
- Durdurma bayrağı (`C:\Projeler\QuantBIST-yeni\data\otonom_dur.flag` ya da `C:\Projeler\QuantBIST-araclar\cikti\otonom_dur.flag`)
  varsa yalnız rapor üret; birleştirme, kurulum, silme yok. Fren bayrağı kendiliğinden kaldırılmaz.
- Kuralları oku: `docs/OTONOM_KURALLAR.md`, `docs/CHARTER.md` §4 ve §9, `CLAUDE.md`.
- Canlı klasöre (`C:\Projeler\QuantBIST-yeni`) yazma; çalışma worktree'de.

## Sıra (CHARTER §4; ilk koşulu oluşan iş yapılır)
1. CI ve son araştırma çalışması kırmızı mı? Önce onu düzelt.
2. Hedefi tutmayan ya da ölçülemeyen SLO var mı (`/durum`, `core.reports.slo.measure`)? Onu düzelt. S2 kapanana
   kadar öncelik SLO serisini korumak.
3. Açık hata (ROADMAP "açık" + kendi bulduğun): önem sırasıyla düzelt.
4. MATURITY'de koşulu oluşmuş en öncelikli iş.
5. Her 10 sürümde bir öz-denetim (CHARTER §7).
6. Bekleyen dallar: zincirin ucunu `surum-kapisi` ile denetle; geçerse birleştir.
7. Koşulu oluşan iş yoksa: bekleyenleri ve neyi beklediklerini yaz, dur.

## Yazılan
- Seçilen iş ve nedeni (hangi adım), yapılanlar, kanıt (test sayısı, SHA, CI) `cikti\OTONOM_RAPOR.md`'ye.
- Ölçüm ya da araştırma gerekiyorsa önce `on-kayit`.

## Yapılmaz
Yeni özellik önerme; kural, eşik, holdout ya da K-79/K-78/K-80 parçalarını sonuca bakarak değiştirme; CLAUDE.md'deki
kesin sınırlar; güncelleyiciye, yedeğe ya da .env'e dokunan iş (bunlar `surum-kapisi`'nin paket dışı kurallarıyla).
