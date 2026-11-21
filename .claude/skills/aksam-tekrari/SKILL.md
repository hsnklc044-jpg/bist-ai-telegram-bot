---
name: aksam-tekrari
description: QuantBIST akşam tekrarı (K-117 öğrenci döngüsü, K-122 kılavuzu). Günün son kurulumunun sağlık kontrolünden sonra, kurulum yoksa son robot turunun sonunda kullan. Günün işini AAR'nin dört sorusuyla kanıta dayanarak gözden geçirir. Bulguları DERS_DEFTERI'ne yalnız ekleyerek yazar, dersleri KAPI_KONTROL_LISTESI'ne çevirir, ertesi günün önce onarım listesini çıkarır ve gün sonu sinyalini yazar. Tekrar sırasında kod değiştirmez.
---

# Akşam tekrarı

Bağlayıcı kurallar başka yerdedir, burada sayı, tarih ve saat kopyalanmaz (testle korunur: `tests/test_ogrenci_dongusu.py`):
- Zaman: `docs/OPERATIONS.md` §0, "Akşam tekrarı (K-117)" ve "Gün sonu sinyali (K-122)" satırları.
- Döngü: `docs/OPERATIONS.md` §0a ve `docs/OTONOM_KURALLAR.md` "Öğrenci döngüsü (K-117)".
- Saat: `docs/OTONOM_KURALLAR.md` "Saat kuralı". Kayda yazılan her saat o anda `Get-Date` ile okunur; saat tahmin edilmez. Geçmiş olayın saati kendi kanıtından (commit, log satırı) alınır.
- Defter biçimi: `docs/DERS_DEFTERI.md` başlığı. Kontrol listesi biçimi: `docs/KAPI_KONTROL_LISTESI.md` başlığı.

Bu kılavuz ile o belgeler çelişirse belgeler geçerlidir. Çelişki de bir bulgudur, deftere yazılır.

## Başlarken
1. Kayda gerçek başlama zamanını `Get-Date` ile yaz. Son kurulum gece yarısını geçtiyse tekrar yine o günün tarihiyle yapılır (OPERATIONS §0a).
2. Fren bayrağı varsa (`surum-kapisi` adım 1) tekrar yine yapılır, ama yalnız okuma ve rapor olarak. Defter yazımı fren kalkınca dal üzerinden aktarılır.

## Adımlar

**1. Kanıtı topla.** Günün işlerini listele:
- bot dalındaki günün commit'leri,
- kurulumlar,
- kararlar (`docs/DECISIONS.md`, `docs/KARAR_DEFTERI.csv`),
- robot turları (`cikti\OTONOM_RAPOR.md`),
- canlı sağlık: SHA, sürüm, "Telegram bot started", yaşam sinyali, ERROR sayısı.

**2. AAR: her iş için dört soru.**
1. Ne olmalıydı?
2. Ne oldu?
3. Fark neden oluştu?
4. Neyi sürdürüyoruz, neyi iyileştiriyoruz?

Her cevabın yanında bir kanıt olur: test sonucu, sağlık kontrolü, log satırı ya da Telegram mesajı. "Çalıştı sanıyorum" kanıt sayılmaz. Kanıtı bulunamayan iş "anlaşılamadı" etiketiyle yazılır, tahminle kapatılmaz.

**3. Bulguyu sınıflandır.** Önem kritik, orta ya da düşüktür. Emin değilsen bir üst önemi seç.

**4. Kök neden.** Kritik ve orta bulguda en az beş kez "neden" sorulur. Asıl nedene inilmeden bulgu kapatılmaz. İnceleme suçlamasızdır: kişiye değil sürece bakılır.

**5. Deftere yaz.** `docs/DERS_DEFTERI.md` dosyasına **yalnız ekleme** yapılır:
- Eski satır değiştirilmez, silinmez, yeri değişmez. Durum değişikliği yeni satır olarak eklenir.
- Bütün sütunlar doldurulur. Hücre içinde `|` kullanılmaz.
- Aynı türden hata daha önce görüldüyse durum "tekrar eden hata" olur. Kök neden yeniden incelenir ve süreç değişikliği önerilir.
- Yeni hata yoksa tek satır yeterlidir: "Bugün yeni hata yok."

**6. Düzeltme ve koruma.** Her düzeltmenin yanında aynı hatayı otomatik yakalayacak bir test ya da kontrol yazılır (`dosya:satır`). "Dikkat ederiz" koruma sayılmaz. Koruma henüz yazılmadıysa bulgu açık kalır.

**7. Dersi kontrol listesine çevir.** Her dersten kısa bir madde çıkar ve `docs/KAPI_KONTROL_LISTESI.md` dosyasına başlıktaki biçimle ekle. Bu dosyaya da yalnız ekleme yapılır.

**8. Yeniden kontroller.** Kapanmış bulguların bugün vadesi gelen 1, 7 ve 30 gün kontrollerini yap. Düzeltme hâlâ çalışıyor mu? Hata geri döndüyse bulgu yeni satırla yeniden açılır ve "tekrar eden hata" sayılır.

**9. Hata bütçesi.** Haftanın yeni kritik, yeni orta ve tekrar eden hata sayılarını güncelle. Eşik `docs/OTONOM_KURALLAR.md` "Öğrenci döngüsü (K-117)" madde 7'dedir; aşıldıysa ertesi haftayı "yalnız onarım haftası" olarak işaretle ve rapora yaz.

**10. Önce onarım listesi.** Ertesi günün ilk robot turu için sıralı bir liste çıkar:
1. açık kritik bulgular,
2. açık orta bulgular,
3. "anlaşılamadı" etiketli konular,
4. vadesi gelen yeniden kontroller.

Bu liste kapanmadan yeni özellik, yeni dalga ya da yeni madde açılmaz. Kapatılamayan bulgu gerekçesiyle ertelenir ve deftere yazılır. Düşük bulgular sıraya girer.

**11. Kaydet.** Defter ve kontrol listesi değişiklikleri ayrı dalda yapılır, CI'dan ve `surum-kapisi` kılavuzundan geçer. Kapıdan önce KAPI_KONTROL_LISTESI okunur ve işaretlenir. Kapıya tam SHA verilir.

**12. Bildir.**
- Gün sonu sinyalini ("GÜN SONU HAZIR") OPERATIONS §0 "Gün sonu sinyali (K-122)" satırındaki saatten önce yaz ve merkez oturuma bildir. Sinyal, bekleyen sağlık doğrulaması ya da yaşam sinyali yüzünden ertelenmez: bekleyen doğrulama varsa sinyale o satırdaki not eklenir ve doğrulama sabahki önce onarım listesine girer. Sinyalin saati `Get-Date` ile okunur.
- `cikti\OTONOM_RAPOR.md` dosyasına tek satır yaz (saat `Get-Date` ile): "aksam-tekrari kılavuzuyla" atfı ve deneme günü (ör. "deneme 3/7", K-122), kaç iş gözden geçirildi, kaç yeni bulgu çıktı (kritik/orta/düşük), kaç bulgu kapandı, önce onarım listesinin ilk üç maddesi, sinyal geç kaldıysa nedeni.

## Yapma
- Geçmiş defter ya da kontrol listesi satırını değiştirme veya silme.
- Tekrar sırasında kod düzeltme. Düzeltme ertesi gün, önce onarım sırasında ve ayrı dalda yapılır.
- Sahipten bir şey isteme; soru yasak saatini OPERATIONS §0a ve K-107 belirler. Soru ertesi günün önce onarım listesine yazılır.
- Eşik, ön kayıt ya da hipotez kararı verme. Bir düzeltme bunlardan birine dokunuyorsa merkez oturuma "SAHİP KARARI" olarak bildir.
- Belirsizliği tahminle kapatma. Saati tahmin etme.
