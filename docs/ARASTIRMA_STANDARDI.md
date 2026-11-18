# Kurumsal kantitatif araştırma standardı (QB-ARS-1)

- **Sürüm:** 1.0 (18.11.2026)
- **Sahibi:** kullanıcı
- **Uygulayıcı:** koordinatör

**Durum: TASLAK** (sahibin 18.11 gece talimatı, K-104). Yürürlüğe sahibin ayrı onayıyla girer.
- Çelişki tablosu: [ARS1_UYUM_1911](ARS1_UYUM_1911.md)
- S6 karar talebi: [S6_KARAR_TALEBI](S6_KARAR_TALEBI.md)

**Yeri:** belge hiyerarşisinde Katman 2'ye (strateji) bağlıdır. [ANAYASA](ANAYASA.md) Md. 2, 3 ve 12'yi araştırma yöntemine çevirir. Kayıt: DECISIONS K-103, K-104.

**Yürürlük kuralı:**
- Standart, yürürlüğe girdikten sonra **açılan** hipotezlere ve henüz kesinleşmemiş ön kayıtlara uygulanır. 27.04.2027 a4 ön kaydı da bunlara dahildir; Nisan başında bu standarda göre yazılır.
- Daha önce kesinleşmiş ön kayıtlar (K-93, K-94) geriye dönük **değiştirilmez**. Bu standardın testleri onlar için yalnız "ek bilgi" olarak raporlanır, karar ölçütü olmaz.

## 0. Amaç
"Bu kural geçmişte işe yaradı" ile "bu kural gerçekten bir şey yakalıyor" arasındaki farkı ölçmek.

Kantitatif araştırmada en sık yanılgı nedenleri şunlardır:
- aşırı uydurma;
- çoklu test;
- geleceğe bakma;
- hayatta kalan yanlılığı;
- maliyetin eksik hesaplanması.

Bu standart her birine bir kontrol koyar.

## 1. Veri standardı
- **D-1 Zamana sadık veri (point-in-time).** Her hesap, o gün gerçekten bilinebilecek veriyle yapılır. Sonradan düzeltilmiş fiyat, sonradan açıklanmış bilanço ve sonradan değişen endeks üyeliği o güne taşınmaz.
- **D-2 Hayatta kalan yanlılığı.** Evren, o tarihte işlem gören hisselerdir. Sonradan borsadan çıkan hisseler veride kalır.
- **D-3 Kurumsal işlemler.** Bölünme, bedelli ve bedelsiz artırım, temettü ve birleşme kayıtlıdır. Düzeltme yöntemi tek ve belgelidir.
- **D-4 Veri soy ağacı.** Her sonuç, hangi veri sürümüyle (özet değeri, tarih), hangi kaynaktan ve hangi dönüşümlerle üretildiği bilgisiyle birlikte saklanır.
- **D-5 Veri kalitesi raporu.** Eksik günler, aykırı değerler ve iki kaynak arasındaki fark raporlanır. Bu rapor her araştırmanın ekidir.

## 2. Maliyet ve uygulanabilirlik standardı
- **C-1 Gerçekçi maliyet.** Komisyon, BSMV, borsa payı, alış-satış farkı ve kayma (slippage) hesaba katılır. Kayma, hissenin likiditesine göre ölçeklenir ve ön kayıtta sabitlenir.
- **C-2 Fiyat adımı ve tavan/taban.** BIST fiyat adımları ve tavan/taban kilitleri modellenir. Kilitli seansta işlem yapılmış sayılmaz (Ö48 ve K-91 ile tutarlı).
- **C-3 Kapasite.** Kural, günlük işlem hacminin belirli bir oranından büyük pozisyon varsayamaz. Oran ön kayıtta yazılır.
- **C-4 Uygulama gecikmesi.** Sinyal ile işlem arasındaki gerçekçi gecikme modellenir. Kapanışta üretilen bir sinyal, o kapanıştan işlem görmüş sayılmaz.

## 3. İstatistik standardı
- **S-1 Deneme kaydı.** Denenen her varyant kayda geçer, başarısızlar da. Deneme sayısı N sonuçla birlikte raporlanır. Kayıtsız deneme bir araştırma ihlalidir.
- **S-2 Çoklu test düzeltmesi.** Anlamlılık, deneme sayısına göre düzeltilir: Bonferroni ya da yanlış keşif oranı (FDR). Hangisinin kullanılacağı ön kayıtta seçilir.
- **S-3 Aşırı uydurma ölçümleri.** Her aday kural için şunlar raporlanır:
  - saptırılmış Sharpe oranı (deflated Sharpe; deneme sayısını ve getiri dağılımının çarpıklığını hesaba katar);
  - olasılıksal Sharpe oranı (probabilistic Sharpe);
  - kombinatoryal doğrulamayla hesaplanan backtest aşırı uydurma olasılığı (PBO).
- **S-4 Doğrulama yöntemi.** Zaman serisi için arındırılmış ve ambargolu kombinatoryal çapraz doğrulama (CPCV) kullanılır. Eğitim ve test dönemleri arasında etiket süresi kadar boşluk bırakılır. Rastgele karıştırmalı doğrulama yasaktır.
- **S-5 Etki büyüklüğü.** Anlamlılık tek başına yetmez. Maliyet sonrası ortalama getiri, güven aralığı ve ekonomik anlamlılık eşiği ön kayıtta yazılır.
- **S-6 Sağlamlık.** Sonuç şu değişikliklerle tekrar hesaplanır:
  - parametrelerin ±%20 oynaması;
  - başlangıç tarihinin kaydırılması;
  - en etkili 3 hissenin çıkarılması;
  - en uç 5 günün çıkarılması.

  Sonuç tek bir parametre noktasına bağlıysa "kırılgan" etiketi alır.

## 4. Rejim ve risk standardı
- **R-1 Rejim analizi.** Sonuçlar şu ayrımlarla raporlanır:
  - yükselen, düşen ve yatay piyasa;
  - yüksek ve düşük oynaklık;
  - yüksek ve düşük enflasyon ya da faiz dönemleri.

  Rejim tanımları önceden kayıt altına alınır; sonuç görüldükten sonra yeni rejim tanımı üretilmez.
- **R-2 Risk ölçüleri (kâğıt portföy).** Azami düşüş ve süresi, CVaR %95, oynaklık ve en kötü ay. Bunlar getiriyle aynı tabloda, aynı büyüklükte yazılır.
- **R-3 Kuyruk riski.** Kuralın tarihî stres dönemlerindeki davranışı ayrıca gösterilir: 2018 kur şoku, Mart 2020 ve 2023 deprem haftası gibi.
- **R-4 Kıyas.** Her sonuç şunlarla karşılaştırılır:
  - XU100 al-tut;
  - eşit ağırlıklı evren;
  - aynı işlem sayısıyla rastgele seçim (Monte Carlo).

  Rastgele seçimi anlamlı biçimde geçemeyen kural, kural sayılmaz.

## 5. Model yaşam döngüsü
- **L-1 Aşamalar.** Fikir → ön kayıt → araştırma → bağımsız doğrulama → kâğıt → izleme → emeklilik. Hiçbir aşama atlanmaz. Her geçişin kanıtı model kartına yazılır.
- **L-2 Bağımsız doğrulama.** Kuralı geliştiren oturum onu doğrulayamaz. Doğrulamayı temiz bağlamlı bir oturum yapar; bu oturum yalnız ön kaydı, kodu ve veriyi alır, geliştirme notlarını görmez.
- **L-3 Kırmızı takım.** Her aday kural için bir oturuma "bu sonucu çürüt" görevi verilir. Bu oturum geleceğe bakma, maliyet hatası ve veri sızıntısı arar. Bulduğu her açık kuralı engeller.
- **L-4 Canlı izleme.** Kâğıt aşamasında, canlı sonuç dağılımının araştırma dağılımından sapması (dağılım kayması) ölçülür. Sapma eşiği ön kayıtlıdır; aşılırsa kural askıya alınır.
- **L-5 Emeklilik.** Etki azalırsa (yarı ömür ölçümü) ya da sapma eşiği aşılırsa kural emekliye ayrılır. Emekli kural sessizce silinmez; kartı arşivde kalır.

## 6. Deney kayıt sistemi
- Her deney için `data/deneyler/` altında tek bir klasör açılır. Klasörde ön kayıt, kod sürümü, veri özeti, parametreler, sonuçlar ve deneme sayacı bulunur.
- Deney kaydı silinemez ve değiştirilemez. KT-03 bu klasörü de kapsar.
- Aylık rapora tek satır girer: "Bu ay N deneme, K aday, 0/1 doğrulanmış."

## 7. Olgunluk merdivenine öneri (sahibin kararıdır, Md. 17 usulü)
S5'ten sonra şu seviye önerilir:

**S6 Kurumsal standart**
- En az bir kural bu standardın S-3, S-6, R-4, L-2 ve L-3 testlerinin hepsini geçmiş olmalı.
- Kural 6 ay kâğıt aşamasında, sapma eşiği aşılmadan izlenmiş olmalı.
- Tüm sonuçlar yeniden üretilebilir olmalı.

S6 da gerçek para **içermez**; merdivenin hiçbir seviyesi gerçek para içermez. Koordinatör bu öneriyi yalnız karar talebi olarak sunar, kendisi uygulamaz.

## 8. Uygulama sırası
Bu fazlar hayata geçirme programına eklenir ([PROGRAM](PROGRAM.md) §10).

| Faz | Dönem | İş |
|---|---|---|
| A | 25.11.2026'dan sonra (yalnız araç ve test, canlıya dokunmaz) | D-1, D-2 ve D-4 denetimleri; deney kayıt sistemi; deneme sayacı |
| B | Aralık 2026 – Ocak 2027 | deflated Sharpe, PSR ve PBO hesapları; kendi testleriyle CPCV; rastgele seçim kıyası |
| C | Şubat – Mart 2027 | maliyet modeli (kayma, fiyat adımı, kapasite); rejim tanımlarının ön kaydı |
| D | Nisan 2027 başı (27.04'ten önce) | a4 ön kaydı bu standarda göre yazılır ve sahibin onayına sunulur; kırmızı takım ve bağımsız doğrulama bir kuru çalıştırmayla denenir |

Her faz önce testle başlar. Her hesap yöntemi bilinen bir örnekle doğrulanır; örneğin deflated Sharpe, yayımlanmış bir örnekteki sayıyı aynen üretmelidir.

## 9. Raporlama
Her araştırma sonucu tek sayfalık bir "araştırma kartı" ile sunulur. Kartta şunlar bulunur:
- soru ve ön kayıt tarihi;
- deneme sayısı N;
- maliyet sonrası etki ve güven aralığı;
- deflated Sharpe ve PBO;
- sağlamlık, rejim ve kıyas tabloları;
- kırmızı takım sonucu;
- karar: kabul / ret / daha fazla veri.

Kartın en üstüne tek bir cümle yazılır: "Bu sonuç için gerçek bir etki olduğuna dair kanıt: güçlü / orta / zayıf / yok."
