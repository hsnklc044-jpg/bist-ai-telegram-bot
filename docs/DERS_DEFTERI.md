# Ders defteri (K-117, öğrenci döngüsü)

Akşam tekrarında (OPERATIONS §0a) bulunan eksik, gedik ve hatalar buraya yazılır. **Yalnız ekleme:** eski satır değiştirilmez, silinmez, yeri değişmez. Durum değişikliği (kapandı, yeniden açıldı, ertelendi, yeniden kontrol sonucu) yeni bir satırla, ilk satırın tarihine ve bulgusuna atıfla yazılır (ANAYASA Md. 11).

- **önem:** kritik / orta / düşük. Kritik ve orta bulguda kök neden 5 Neden ile yazılır; inceleme suçlamasızdır.
- **koruma:** aynı hatayı otomatik yakalayan test ya da kontrol (dosya:satır). "Dikkat ederiz" koruma sayılmaz.
- **kontrol maddesi:** `docs/KAPI_KONTROL_LISTESI.md`'ye eklenen madde.
- **yeniden kontrol:** kapanıştan 1, 7 ve 30 gün sonraki tarihler; hata dönerse bulgu yeniden açılır, "tekrar eden hata" sayılır.
- **durum:** açık / kapandı / ertelendi (gerekçe) / anlaşılamadı / tekrar eden hata.
- Hata yoksa tek satır: "Bugün yeni hata yok." Hücre içinde `|` kullanılmaz (sütun sayısı `tests/test_ogrenci_dongusu.py` ile denetlenir).

| tarih | bulgu | önem | kök neden (5 neden özeti) | düzeltme | koruma | ders | kontrol maddesi | yeniden kontrol (1/7/30 gün) | durum |
|---|---|---|---|---|---|---|---|---|---|
