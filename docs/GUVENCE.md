# Uyum ve güvence programı

- **Belge no:** QB-GUV-1
- **Sürüm:** 1.0 (18.11.2026)
- **Sahibi:** kullanıcı
- **Uygulayıcı:** koordinatör

[ANAYASA](ANAYASA.md)'ya bağlıdır. Ona yeni bir ilke eklemez; var olan ilkeleri ölçülebilir hale getirir. Kontrol matrisi: [KONTROLLER.csv](KONTROLLER.csv).

## 1. Amaç
Anayasanın her maddesi için şu soruya kanıtla cevap vermek: "Bu ilke bugün gerçekten uygulanıyor mu?" Yazılı olup ölçülmeyen bir ilke uygulanıyor sayılmaz.

## 2. Üç savunma hattı (kurumsal risk yönetiminden uyarlanmıştır)
- **1. hat, uygulayan:** her iş kontrollerden geçerek yapılır (testler, kapı, CI).
- **2. hat, izleyen:** otomatik uyum kontrolleri her gün çalışır ve sapmaları raporlar.
- **3. hat, bağımsız güvence:** projeyi hiç görmemiş temiz bir oturum altı ayda bir örneklem denetimi yapar. Kontrolleri değil, kontrollerin çalışıp çalışmadığını denetler.

## 3. Kontrol matrisi
[KONTROLLER.csv](KONTROLLER.csv)'de her satır bir kontroldür.

Sütunlar: kontrol no, anayasa maddesi, risk, kontrol, tür (önleyici / tespit edici), otomasyon (otomatik / elle), sıklık, kanıt, sahip, son sonuç.

Kontrol numaraları DECISIONS'taki K numaralarından ayrıdır; ayrışsın diye "K-" yerine "KT-" önekiyle tutulur.

## 4. Uyum panosu
- Tek bir sayfadır: her kontrolün son sonucu (✅/⚠️/❌), tarihi ve kanıt bağlantısı.
- Haftalık rapora tek satır olarak girer: "Uyum: 10/10 ✅" ya da başarısız kontrollerin listesi.

## 5. Sapma yönetimi
Her ❌ bir sapma kaydı açar. Kayıtta şunlar yer alır:
- ne oldu;
- hangi madde;
- etkisi;
- kök neden;
- düzeltici önlem;
- önleyici önlem;
- kapanış kanıtı.

Önem dereceleri ve tepki süreleri:
- **KRİTİK** (Madde 1–4, çekirdek ihlali): sistem hemen güvenli moda alınır ve sahibe aynı gün Telegram'dan bildirilir.
- **YÜKSEK:** 48 saat içinde düzeltilir.
- **ORTA ve DÜŞÜK:** bir sonraki öz-denetimde ele alınır.

Aynı kök nedenden ikinci bir sapma çıkarsa düzeltme yetmez; kontrolün kendisi yeniden tasarlanır.

## 6. Kontrollerin denetimi
- Her kontrolün bir kanarya testi vardır: kasıtlı olarak bir ihlal üretilir ve kontrolün onu yakaladığı doğrulanır. Ardından eklenen şey geri alınır. Örnek: sahte bir emir fonksiyonu eklenir ve KT-01'in kırmızıya döndüğü görülür.
- Hiç alarm vermeyen bir kontrol "çalışıyor" değil, "doğrulanmamış" sayılır.

## 7. Güvence görüşü
Yılda bir kez bağımsız bir oturum yazar. Görüş şu dört biçimden biri olur:
- **Olumlu:** anayasa etkin biçimde uygulanıyor.
- **Şartlı:** belirli sapmalar dışında uygulanıyor.
- **Olumsuz:** uygulanmıyor.
- **Görüş bildirilemiyor:** kanıt yetersiz.

Görüş yumuşatılmadan, aynen arşivlenir.

## 8. Uygulama sırası
Önce en kritik kontroller.

| Dönem | Tarih | İş |
|---|---|---|
| Hafta 1 | 19–25.11.2026 | KT-01, KT-03, KT-04 (çekirdek) ve uyum panosu |
| Hafta 2 | 26.11–02.12.2026 | KT-02, KT-10 ve kanarya testleri |
| Ay 1 sonu | 18.12.2026 | kalan kontroller ve sapma kaydı şablonu |

- Her kontrol önce test olarak yazılır, sonra devreye alınır.
- Davranış değiştiren her şey kalıcı çerçeveye göre sahibin onayıyla girer.
- Kontrollerin çoğu test ya da araçtır, botun davranışını değiştirmez. Aralık planındaki "12.12'ye kadar canlıda riskli değişiklik yok" kuralıyla çakışmaz.
