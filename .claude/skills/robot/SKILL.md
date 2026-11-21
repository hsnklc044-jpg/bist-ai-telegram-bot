---
name: robot
description: QuantBIST robot modu, tek düğme. Çağrıldığında fren, durum, iş seçimi, yapım, CI, kapı, kurulum ve sağlık döngüsünü durma koşullarından biri oluşana kadar soru sormadan çalıştırır. "QuantBIST otonom" zamanlanmış görevi bunu çağırır.
---

# Robot

Kurallar başka yerde; burada sayı kopyalanmaz:
- Kesin sınırlar: `CLAUDE.md`, `docs/CHARTER.md` §9.
- Kapı, paketleme, paket dışı işler, fren: `docs/OPERATIONS.md` §5a ve `surum-kapisi` skill'i.
- İş seçimi: `siradaki-is` skill'i (CHARTER §4). Ölçüm: önce `on-kayit`.
- Otonom çalışmanın ek kuralları: `docs/OTONOM_KURALLAR.md`.

## Başlarken
1. Kilit: `C:\Projeler\QuantBIST_otomasyon\robot.lock`. Varsa ve 6 saatten yeniyse başka robot çalışıyordur: başlama, rapora yaz,
   bitir. 6 saatten eskiyse önceki robot çökmüş sayılır: kilidi devral ve bunu rapora yaz. Yoksa içine başlama saatini yazarak oluştur.
2. Bitişte (hangi nedenle olursa) kilidi sil.

## Döngü (her turda sırayla)
1. **Fren:** `/otonom_dur` bayrağı ya da otomatik fren bayrağı varsa yalnız kurtarma (geri dönüş, tanılama) yap ve dur.
   Bayrağı asla kendin kaldırma.
2. **Durum:** canlı sürüm ve sağlığı (SHA, sürüm, "Telegram bot started", yaşam sinyali, ERROR), CI'lar, bekleyen dallar, SLO'lar.
3. **İş seçimi:** önce kuyruk sınırı (`docs/OPERATIONS.md` §5a): aşıldıysa yeni dal açma, yalnız kuyruğu canlıya çıkar,
   kurtarma ve kuyruktaki dalların düzeltmelerini yap. Aşılmadıysa `siradaki-is` sırasıyla koşulu oluşan ilk iş.
4. **Yapım:** worktree'de (`C:\Projeler\QuantBIST-araclar\` altında) yeni dal; önce başarısız test, sonra en küçük düzeltme;
   ruff ve tam test paketi; dalı gönder. Sürüm, CHANGELOG.
5. **CI:** aynı SHA'nın CI'ını arka planda bekle (GitHub API'yi seyrek sorgula); bu arada sıradaki işi hazırla.
6. **Kapı ve kurulum:** `surum-kapisi` ile kuyruğu küçük paketlerle (OPERATIONS §5a) birleştir; her paket bir öncekinin canlıda
   sağlıklı olduğu görüldükten sonra. Kurulum penceresi kapalıysa beklemek durma nedeni değildir.
7. **Sağlık:** kurulumdan sonra `surum-kapisi`'nin sağlık koşulu; sorun varsa geri dön ve fren kurallarını uygula.
   Günün son kurulumunun sağlık kontrolünden sonra (kurulum yoksa günün son turunun sonunda) akşam tekrarı yapılır; yöntem: `aksam-tekrari` kılavuzu (OPERATIONS §0a, K-122).
8. **Kayıt:** `cikti\OTONOM_RAPOR.md`'ye tek satır (tarih saat · iş · dal/SHA · sonuç); asıl kayıt budur. `docs/ROBOT_LOG.md` 11.11'den beri tutulmuyor, tarihsel kayıttır (18.11, Ö65). 1. adıma dön.

## Durma koşulları (yalnız bunlar)
- Koşulu oluşan iş kalmadı; kalanlar yalnız zaman bekliyor (SLO serisi, 30 gün, canlı ölçüm tarihi gibi).
- Fren devreye girdi.
- Sıradaki adım kullanıcıya kalanlar listesinde (.env, token, ödeme, hesap, dış izleme ayarları).
- Kota: haftalık %70 ya da 5 saatlik %60 üstü; yalnız sağlık kontrolü ve rapor (`docs/OTONOM_KURALLAR.md` "Ortam").
- Sıradaki iş güncelleyici, yedek ya da geri yükleme birleştirmesi: hafta sonu kullanıcının tek komutuyla olur (K-88 §5); robot hazırlar ve bildirir, kendisi birleştirmez.

Durunca kullanıcıya tek mesaj: bu çalışmada yapılanlar, kurulan sürümler, durma nedeni, bir sonraki zamanlanmış çalışmada ilk iş.
Soru sorulmaz.
