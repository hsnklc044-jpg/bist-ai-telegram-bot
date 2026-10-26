# Geliştirme oturumu için hazır mesajlar

Köşeli parantez içindeki yerleri doldurun. Doldurulmamış bir şablon gelirse hiçbir madde
"doğrulandı" olarak işaretlenmez.

## 1. Ara rapor isteme

```
v[SÜRÜM]'ı gördüm. Kısa bir ara rapor ver:
1. Son doğrulanan sürümden bu yana ne değişti (madde madde, sade dille)?
2. Hangi işler bitti, hangileri kaldı?
3. Bilgisayarımda neyi, hangi komutla doğrulamam gerekiyor; beklenen sonuç ne?
4. Bundan sonraki 3 iş ne, neden bu sırayla?
Sonra bana sormadan devam et.
```

## 2. Yeni sürümü kurduktan sonra

Kurulum:

```
robocopy qb\bist-ai-telegram-bot-claude-borsa-bot-creation-n7nmc9 C:\Projeler\QuantBIST /E /XF watchlist.json .env
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

`/MIR` kullanmayın; kişisel dosyaları siler. `verify.ps1` şu kontrolleri yapar:
- sürüm, paket kilidi, ruff ve testler;
- `/durum` kontrolleri;
- fiyat veritabanı yedeği ve geri yükleme testi (geçici klasörde);
- son rapor çalıştırmaları;
- son günlük log.

Hepsini `logs\verify_report.txt` dosyasına yazar. Token ve chat id gizlenir.

Ardından botu yeniden başlatın (`.venv\Scripts\python main.py`), 5 dakika bekleyin ve gönderin:

```
v[SÜRÜM] PC'de kuruldu. logs\verify_report.txt:
[DOSYANIN TAMAMINI YAPIŞTIR]
Telegram /durum (bot 5 dakika açık kaldıktan sonra): [Tüm kontroller geçti / şu satır sorunlu: ...]
Son 18:30 raporu: [sorun yok / şu tuhaf: ...]
ROADMAP'te doğrulanan maddeleri "PC'de doğrulandı" olarak işaretle ve devam et.
```

## 3. 18:30 raporu gelmezse

Önce şunu çalıştırın:

```
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

Sonra gönderin:

```
Bugün 18:30 raporu gelmedi.
logs\verify_report.txt:
[DOSYANIN TAMAMINI YAPIŞTIR]
Bilgisayar 18:30'da açık mıydı: [evet / uykudaydı / kapalıydı]
Sebebini bul, gerekirse düzelt; tekrar olmaması için ne yapılacağını söyle.
```

## 4. Rapor geldi ama bir şey tuhaf

```
Bugünkü raporda şu tuhaf görünüyor: [NE GÖRDÜN, ör. "etkin pozisyon sayısı 1.498,7"]
İlgili satır: [RAPORDAN KOPYALA]
Olması gerektiğini düşündüğüm: [BEKLENTİN]
Önce bunu yakalayan bir test yaz, sonra düzelt ve yeni sürüm olarak yayınla.
```

## 5. Ne yapıldığını anlamadığınızda

```
Son yaptığın işi teknik terim kullanmadan, 5 cümleyle anlat:
ne sorundu, ne yaptın, bana faydası ne, ben bir şey yapmalı mıyım?
```

## 6. Yön değiştirmek

```
Öncelik değişikliği: bundan sonra önce [KONU] üzerine çalış.
Önce planı 5 maddede yaz, maliyet ve riskleri belirt, sonra başla.
Gerçek para, şifre, ücretli servis veya gerçek veriyi değiştiren adımda dur ve bana sor.
```

## 7. Ara vermek

```
Kullanım limitim azalıyor. Elindeki işi güvenli bir noktada bitir, commit et,
docs/ROADMAP.md'deki "Kaldığım yer" bölümünü güncelle ve dur. Yeni iş başlatma.
```

## 8. Yeniden başlamak

```
Kaldığın yerden devam et: önce docs/ROADMAP.md'deki "Kaldığım yer" bölümünü oku,
CI durumunu kontrol et, sonra sıradaki işe bana sormadan geç.
```

## 9. Karar vermek

Bekleyen kararlar `docs/ROADMAP.md`'deki "Kaldığım yer" bölümünde listelenir.

```
Kararlarım: [ör. "KCAER katsayısı 0,8646 olsun", "kapanış düzeltmeleri kapalı kalsın"]
Uygula, testleri çalıştır, kayıt defterine (docs/DATA_CORRECTIONS.md) gerekçesiyle yaz.
```
