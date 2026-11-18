# Hayata geçirme programı (QB-PRG-1)

- **Sürüm:** 1.0 (18.11.2026)
- **Sahibi:** kullanıcı
- **Program yöneticisi:** koordinatör
- **Süre:** 90 gün, 19.11.2026 (gün 1) – 16.02.2027 (gün 90)

Not: kontrol numaraları [KONTROLLER.csv](KONTROLLER.csv)'de KT-01…KT-10 olarak tutulur (DECISIONS'taki K numaralarıyla karışmasın diye). Aşağıda geçen "K-01" gibi kontrol adları KT-01'e karşılık gelir.

## 1. Programın amacı
Bu sohbette yazılan belgeleri çalışan ve ölçülen bir sisteme dönüştürmek. Belgeler:
- kalıcı çerçeve;
- Aralık planı;
- 2027 planı;
- CHARTER_2028;
- STRATEGY_2031;
- ANAYASA;
- GÜVENCE.

Başarı ölçütü belge sayısı değildir. Ölçüt, bu belgelerdeki kuralların kaçının otomatik uygulandığı ve test edildiğidir.

## 2. İlk iş: belge birleştirme (gün 1–7; 19–25.11.2026)
Belgeler birbirine yakın konuları tekrar ediyor. Anayasa Md. 5 (orantılılık) gereği önce sadeleştirilir:
- Tüm belgeler taranır. Tekrar eden, çelişen ve uygulanamayan maddeler tek bir tabloda gösterilir.
- Hedef yapı en fazla 4 katmandır:
  - ANAYASA (ilkeler);
  - STRATEJİ (çok yıllı yön);
  - YILLIK PLAN (bu yılın hedefleri);
  - KONTROLLER (otomatik testler).
- Görev metinleri belge değildir; günlüğe yazılır ve geçer.
- Birleştirme önerisi sahibe sunulur. Sahip onaylayınca eski belgeler arşivlenir. Silme yok.
- Çıktı: `docs/BELGE_HARITASI.md`. Her belge için tek satır: amacı, sahibi, ne zaman gözden geçirileceği.

## 3. İş paketleri (öncelik sırasıyla)

**İP-1. Çekirdek güvence (gün 1–14)**
- KT-01, KT-03, KT-04 kontrolleri, kanarya testleri ve uyum panosu.
- Kabul ölçütü: her kontrol kasıtlı bir ihlali yakalıyor ve pano haftalık rapora giriyor.

**İP-2. Sayaçların korunması (sürekli, 18.12'ye kadar; K-105, önce 12.12)**
- Aralık planındaki kilometre taşları. S2 ve S3 kapanış önerileri kanıtlarıyla sunulur.
- Kabul ölçütü: S2 ve S3 resmî olarak kapanmış, ya da kapanmama nedeni kanıtla yazılmış.

**İP-3. İş sürekliliği (gün 15–45)**
- S3 için oturum açmadan başlatma kararı (sahibin kararı).
- Sıfırdan kurulum tatbikatı, süresi ölçülmüş.
- "Ben 3 ay yokum" güvenli modu.
- Tek sayfalık sistem özeti.
- Kabul ölçütü: tatbikat raporu, ölçülen süre ve güvenli mod testi.

**İP-4. Model ve araştırma yönetişimi (gün 30–60)**
- Model kartı şablonu, model envanteri ve RISKS.md.
- S4'ün ilk olgun sonucu RESEARCH_LOG'da.
- Kabul ölçütü: envanterdeki her kuralın kartı tam.

**İP-5. Kalan kontroller ve ilk iç değerlendirme (gün 45–90)**
- KT-02 ve KT-05…KT-10 kontrolleri, sapma kaydı şablonu.
- 90. günde iç değerlendirme: program hedefleri tuttu mu?
- Kabul ölçütü: uyum panosu 10/10, ya da açık sapmalar kayıtlı.

## 4. Sorumluluk matrisi (RACI)
| Kim | Rol |
|---|---|
| Sahip | Onay (A); ölçüt ve kapsam kararları |
| Koordinatör | Uygulama ve raporlama (R) |
| Robot oturumları | Günlük işletme (R), yalnız yetki sınırında |
| Bağımsız oturum | 90. gün değerlendirmesi (C) |
| Sahibe bilgi (I) | Haftalık rapor, "Senden beklenen" satırı |

## 5. Kaynak bütçesi
- **Sahibin zamanı:** haftada en fazla 30 dakika onay ve karar. Aşılırsa iş paketleri yavaşlatılır, kapsam küçültülür.
- **Robot kotası:** haftalık kullanım ölçülür. %70'i geçerse düşük öncelikli işler durdurulur.
- **Canlı sistem riski:** sayaç dönemlerinde (18.12'ye kadar; K-105, önce 12.12) İP-1 ve İP-3 yalnız dalda hazırlanır; canlıya sahibin onayıyla geçer.

## 6. Program göstergeleri
Haftalık raporda tek tablo olarak yer alır.

| Gösterge | Hedef (gün 90) |
|---|---|
| Otomatik uygulanan kural sayısı / toplam kural | ≥ %80 |
| Kanarya testi geçen kontrol oranı | %100 |
| Aktif belge yapısı | ≤ 4 katman |
| Sahibin haftalık süresi | ≤ 30 dk |
| Açık YÜKSEK/KRİTİK sapma | 0 |
| S2 / S3 durumu | Kapandı ya da gerekçeli |

## 7. Durdurma ve yön değiştirme ölçütleri
- Program göstergeleri iki hafta üst üste ilerlemezse durulur, nedeni yazılır ve kapsam daraltma önerilir.
- Program canlı sistemde bir SLO ihlaline yol açarsa ilgili iş paketi hemen durur ve kök neden analizi yapılır.
- Program hedefine belge yazarak ulaşılmaz. Bir haftada yalnız belge üretilip kontrol eklenmediyse bu bir sapma sayılır.

## 8. Kapanış (gün 90)
- Program kapanış raporu: hedef/gerçekleşen tablosu, öğrenilen dersler, açık kalanlar.
- Bağımsız oturumun kısa görüşü.
- Sonraki 90 günlük programın taslağı; sahibin onayıyla açılır.

## 9. Program sonrası işleyiş: sürekli iyileştirme döngüsü (QB-SID-1)
Sürüm 1.0 (18.11.2026). Sahibi kullanıcı, uygulayıcısı koordinatör, süresiz. Yeni bir belge değildir; programın kendini yenileme kuralıdır.

**9.1 İlke.** Bundan sonra bir sonraki talimat kullanıcının hayal gücünden değil, sistemin kendi ölçümlerinden doğar. Koordinatör her döngü sonunda bir sonraki döngünün talimatını kendisi önerir. Kullanıcı onaylar, değiştirir ya da reddeder.

**9.2 Döngü** (90 günlük: Planla → Uygula → Ölç → İyileştir)
- **Planla:** önceki döngünün ölçümlerinden en zayıf 3 nokta seçilir. Gerekçe veri olmalıdır, tahmin değil.
- **Uygula:** her zayıf nokta için tek bir iş paketi yazılır. Her paketin kabul ölçütü sayısaldır.
- **Ölç:** haftalık göstergeler ve uyum panosu.
- **İyileştir:** döngü sonunda üç soru cevaplanır:
  1. Ne tuttu?
  2. Ne tutmadı ve neden?
  3. Hangi kural, kontrol ya da belge artık gereksiz ve kaldırılmalı?

**9.3 Talimat önerisi** (her döngünün 85. günü sahibe sunulur). İlk döngünün 85. günü 11.02.2027'dir. Öneri en fazla 1 sayfadır ve şunları içerir:
- ölçümlere göre en zayıf 3 nokta, kanıtlarıyla;
- önerilen 3 iş paketi ve kabul ölçütleri;
- kaldırılması önerilen 1 şey (zorunlu; her döngü sistemi biraz sadeleştirir);
- sahipten istenen kararlar;
- sahibin tahmini zamanı (dakika/hafta).

**9.4 Sınırlar**
- Öneri ANAYASA'yı, ölçütleri ya da kapsamı değiştiremez. Bunlar gerekiyorsa ayrı bir karar talebi olarak sunulur.
- Döngü önerisi kendiliğinden yürürlüğe girmez; sahibin onayı gerekir. Sahip 14 gün cevap vermezse önceki döngünün kuralları aynen devam eder ve yeni iş başlatılmaz.
- En fazla 3 iş paketi önerilir. Daha fazlasına ihtiyaç duyulması sadeleştirme gerekçesi sayılır.

**9.5 Döngünün kendisinin ölçülmesi.** Yılda bir şu sorular sorulur:
- Önerilen paketlerin kaçı kabul ölçütüne ulaştı?
- Sistem bir yılda sadeleşti mi, karmaşıklaştı mı (aktif kural, kontrol ve belge sayısı)?
- Kullanıcının harcadığı zaman azaldı mı?

Üç göstergeden ikisi kötüye gidiyorsa döngünün kendisi yeniden tasarlanır.

## 10. Araştırma standardı uygulaması (QB-ARS-1, 18.11.2026)
[ARASTIRMA_STANDARDI](ARASTIRMA_STANDARDI.md) §8'deki fazlar programa eklenir:
- **Faz A:** 25.11.2026'dan sonra; yalnız araç ve test.
- **Faz B:** Aralık 2026 – Ocak 2027.
- **Faz C:** Şubat – Mart 2027.
- **Faz D:** Nisan 2027 başı.

Faz A ve B program süresine (16.02.2027'ye kadar) girer ve İP-4 ile birlikte izlenir. Her faz önce testle başlar.
