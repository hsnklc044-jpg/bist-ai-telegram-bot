---
name: surum-kapisi
description: QuantBIST birleştirme ve canlı kurulum kapısı. Bir dalı ya da zincirin ucunu bot dalına birleştirmeden önce kullan; beş koşulu ve paket istisnasını ✅/❌ ile denetler, hepsi geçerse ileri sararak birleştirir.
---

# Sürüm kapısı

Canlıya giden her şey buradan geçer (kullanıcının 10.11.2026 onay devri; `docs/OPERATIONS.md` §5a).

## Adımlar
1. Durdurma bayrağı var mı: `C:\Projeler\QuantBIST-yeni\data\otonom_dur.flag` (bot `/otonom_dur`) ya da
   `C:\Projeler\QuantBIST-araclar\cikti\otonom_dur.flag` (otomatik fren). Varsa birleştirme, kurulum ve silme yok; yalnız rapor.
2. Birleştirilecek SHA'yı belirle. Zincir halinde bekleyen dallar varsa (her biri bir öncekinin üstünde) ucunu tek
   paket olarak birleştir; zincirdeki her dalın kendi CI'ı yeşil ve tam test paketi geçmiş olmalı.
3. Worktree'de o SHA'da tam test ve ruff çalıştır (canlı klasörde asla).
4. `python scripts/surum_kapisi.py <SHA> --testler-gecti` (worktree'den). Her satır ✅ olmalı:
   0 bayrak yok, canlı klasör temiz (`git status`); 1 test+ruff ve aynı SHA'nın CI'ı yeşil; 2 canlı sürüm sağlıklı
   (SHA, sürüm, "Telegram bot started", ≥3 ERROR'suz yaşam sinyali); 3 önceki kurulumdan beri hiçbir SLO kötüleşmedi;
   4 kurulum (güncelleyicinin sonraki :40 çalışması, 07:40–23:40) seans günü 09:40–18:15 ve 18:00–20:00 dışında
   (hafta sonu/tatil açık); 5 aynı anda tek paket, günde ≤4 kurulum; 6 ileri sarılabilir; 7 paket istisnası yok.
5. Hepsi ✅ ise `--birlestir` ile tekrar çalıştır (kilit dosyası iki oturumun aynı anda birleştirmesini önler).
   Biri ❌ ise birleştirme; nedenini `cikti\OTONOM_RAPOR.md`'ye yaz ve sonraki işe geç.
6. Kurulumdan sonra tek satır rapor: sürüm, paketteki dallar, CI bağlantıları, canlı sağlık kanıtı (SHA, sürüm,
   "Telegram bot started", yaşam sinyali, ERROR sayısı).

## Paket dışı (tek başına, ayrı kural)
- Güncelleyici (`scripts/guncelle.py`), yedek, geri yükleme: tek başına, yalnız hafta sonu; önce aynı SHA'da
  `dr-drill` iş akışı başarılı; güncelleyicinin önceki sürümü `C:\Projeler\QuantBIST_otomasyon\` altına kopyalanır;
  sonraki ilk güncelleyici çalışması ve ilk yedek doğrulanana kadar başka birleştirme yok.
- Kişisel kayıt biçimi: yalnız geriye uyumlu (eski biçimi okuyan) değişiklik; geri yükleme testi geçmeli; tek başına.
- .env, token, ödeme, hesap, dış izleme ayarları: yapılmaz, kullanıcıya yazılır.

## Sorun çıkarsa
Bot başlamazsa, ERROR görülürse ya da bir SLO düşerse: önceki sürüme dön (bot dalına `git revert` commit'i, ileri
sarma; geçmiş yeniden yazılmaz), hangi dalın sorun çıkardığını dalları tek tek deneyerek bul. Aynı gün 2 geri dönüş,
KRİTİK SLO, canlı klasörde beklenmeyen değişiklik, güncelleyicinin üst üste 2 başarısız çalışması ya da aynı hatayı
iki kez düzeltememek otomatik frendir: `cikti\otonom_dur.flag` yaz, dur, kullanıcıya tek paragraf yaz. Fren
bayrağını yalnız kullanıcı kaldırır.
