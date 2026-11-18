# Stratejik tüzük: QuantBIST 2027/H2 – 2028

- **Sahibi:** kullanıcı
- **Uygulayıcı:** koordinatör
- **Sürüm:** 1.0 (18.11.2026)

Mevcut [CHARTER](CHARTER.md), kalıcı çerçeve ([OTONOM_KURALLAR](OTONOM_KURALLAR.md) "Kullanıcı çerçevesi"), Aralık planı ve 2027 planı ([ROADMAP](ROADMAP.md) en üstü) geçerliliğini korur. Çelişki olursa sıra: **CHARTER > kalıcı çerçeve > bu tüzük**.

## 1. Vizyon
QuantBIST, BIST için kanıta dayalı, tekrar üretilebilir ve bağımsız denetime açık bir araştırma ve karar destek platformudur.

Başarı getiriyle ölçülmez. Ölçü şu sorudur: "Bu sistemin söylediğine güvenmek için yeterli kanıt var mı?"

## 2. Kapsam
**Kapsam içi:**
- araştırma;
- ölçüm;
- kâğıt üzerinde karar desteği;
- raporlama;
- sistem güvenilirliği.

**Kapsam dışı:**
- gerçek emir ve gerçek para;
- başkalarına sinyal, tavsiye ya da abonelik sunmak (bu, SPK yetkisi gerektiren yatırım danışmanlığıdır);
- müşteri verisi.

Kapsam değişikliğini yalnız kullanıcı, yazılı olarak açar.

## 3. Stratejik hedefler (OKR)

**H1. Araştırma kalitesi**
- Her araştırma sorusu sonuç görülmeden ön kayıt edilir. Hedef: ön kayıtsız sonuç sayısı 0.
- Yılda en fazla 2 yeni hipotez açılır. Her hipotez ya kanıtla kapanır ya da gerekçesiyle terk edilir; yarım kalan hipotez olmaz.
- Negatif sonuçlar da RESEARCH_LOG'a aynı ayrıntıyla yazılır.

**H2. Tekrar üretilebilirlik**
- Her yayımlanmış sonuç tek komutla, aynı veriden, aynı sayıyla yeniden üretilebilir. Ölçüm: çeyrekte bir, rastgele seçilen bir sonucun yeniden üretim testi.
- Veri sürümleri dondurulur. Hangi sonucun hangi veri sürümüyle üretildiği kayıtlıdır.

**H3. İşletme güvenilirliği**
- S2 SLO'ları yıl boyunca hedefte kalır. Hedef dışı her hafta için kök neden analizi yapılır.
- Sıfırdan kurulum tatbikatı yılda iki kez yapılır. Hedef süre yazılır ve ölçülür.
- Bilgisayar ya da disk arızası senaryosu yazılır: sistem en geç kaç saatte, hangi adımlarla geri gelir?

**H4. Sürdürülebilirlik**
- Bakım yükü her çeyrek ölçülür: robot kotası, kullanıcı müdahale sayısı, açık bulgu sayısı.
- Kullanıcıdan haftada 15 dakikadan fazla zaman istenmez. Aşılırsa sadeleştirme önerisi sunulur.
- Kod tabanının büyümesi gerekçelendirilir. Her yıl bir "budama" çeyreği yapılır ve kullanılmayan özellikler kaldırılır.

## 4. Yönetişim
**Karar kademeleri:**
- (a) Teknik karar: Claude karar verir ve DECISIONS'a yazar.
- (b) Ölçüt, eşik, kapsam ve sayaç yorumu: Claude seçenekleri sunar, kullanıcı karar verir.
- (c) Bu tüzüğün değişmesi: yalnız kullanıcı.

**Bağımsız denetim.** Yılda bir, projeyi hiç görmemiş yeni bir oturum (temiz bağlam) yalnız depo ve belgelerle denetim yapar. Bulgular aynen yayımlanır ve düzeltilmeden önce sınıflanır.

**Değişiklik dondurma.** Sayaç ya da ölçüm dönemlerinde canlı sistemde yalnız hata düzeltmesi yapılır.

## 5. Risk kaydı
Kayıt [RISKS.md](RISKS.md)'dedir ve çeyrekte bir gözden geçirilir. Her risk için olasılık, etki, erken uyarı işareti, önlem ve sorumlu yazılır.

Başlangıç riskleri:
- veri kaynağının kapanması;
- bağımlılıkların eskimesi;
- model ya da kota değişiklikleri;
- tek bilgisayara bağımlılık;
- aşırı uydurma (overfitting) ve çoklu test yanılgısı;
- kullanıcının zamanının azalması;
- düzenleyici çerçevenin değişmesi.

## 6. Başarı ve çıkış ölçütleri (2028 sonu)
**Başarı:**
- S5 en az 6 ay kâğıt üzerinde, ön kayda uygun izlenmiş olmalı.
- Tüm sonuçlar yeniden üretilebilir olmalı.
- Bağımsız denetimde KRİTİK bulgu olmamalı.

**Dürüst çıkış.** S4'te anlamlı kural çıkmadıysa ya da S5 kâğıt sonucu ön kayıttaki beklentiyi tutmadıysa, proje "araştırma tamamlandı, olumsuz sonuç" diye bir kapanış raporu yazar. Bu da geçerli bir başarıdır. O durumda:
- sistem salt izleme moduna alınır;
- bakım yükü en aza iner;
- bu karar kullanıcıya sunulur.

## 7. Raporlama ritmi
| Sıklık | Rapor |
|---|---|
| Haftalık | cumartesi seri satırı |
| Aylık | tek sayfa rapor |
| Çeyreklik | OKR karnesi, risk kaydı ve proje sağlığı |
| Yıllık | bağımsız denetim ve tüzük gözden geçirmesi |

Her raporun en üstünde tek satır bulunur: "Senden beklenen: …"
