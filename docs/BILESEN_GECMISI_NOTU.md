# BIST 100 bileşen geçmişi: geriye uzatma notu (19.11.2026)

`data/bist100_changes.csv` 2022-04-01'den 2020-10-01'e uzatıldı (6 çeyrek, 118 satır). Kaynak yalnız Borsa
İstanbul'un çeyrek duyurularındaki BIST 100 tablosu (ALINACAK / ÇIKARILACAK; YEDEK PAYLAR kullanılmadı).
Yürürlük tarihi, duyurunun yazdığı dönemin ilk günüdür.

| Yürürlük | Duyuru | Satır |
|---|---|---|
| 2022-01-01 | 12771 | 18 |
| 2021-10-01 | 14213 | 34 |
| 2021-07-01 | 12664 | 20 |
| 2021-04-01 | 14147 | 22 |
| 2021-01-01 | 14132 | 12 |
| 2020-10-01 | 14118 | 12 |

## Ek: 2020 Ç1–Ç3 ve iki dönem dışı olay (19.11.2026 öğleden sonra)

Aşağıdaki "Durma noktası" bölümündeki iki sorun KAP bildirimleriyle çözüldü; kayıt 2020-01-01'e uzatıldı (68 satır daha).

| Yürürlük | Kaynak | Satır | Not |
|---|---|---|---|
| 2021-06-16 | KAP 942442 (15.06.2021) | 2 | BAGFS Yakın İzleme Pazarı'na geçti, çıkarıldı; yerine 1. yedek ECZYT |
| 2020-07-01 | duyuru 12559 (19.06.2020) | 8 | |
| 2020-05-21 | KAP 845949 (20.05.2020) | 2 | OYAK Çimento birleşmesi: ADANA çıkarıldı; yerine 1. yedek SARKY |
| 2020-04-01 | duyuru 12557 (19.03.2020) | 10 | |
| 2020-01-01 | duyuru 11428 (17.12.2019) | 46 | |

- KAP bildirimleri haber sitelerindeki birebir kopyalarından okundu (bigpara, uzmanpara); kaynak sütununa KAP adresi yazıldı.
- CIMSA (2020-01-01) ve OYAKC (2020-07-01) alınıp bir daha çıkarılmadığı için sabit listeden değişiklik kaydına geçti.
  Sabit hisse (tam geçmiş) 47 → 45; varsayılan sonuçlar değişmedi (202 hisse, eski dosyalarla aynı).
- `ever_members(full_history=True)` 234 hisse. Her tarihte 100 üye (test: `test_2020_q1_to_q3_and_adana_merger`).
- Daha geri (2019 ve öncesi) bu notta yok; sonraki adım 2019 Ç4'ten 2015 Ç3'e, her dönem dışı olay için KAP kaynağıyla.

## Ek 2: 2019 (19.11.2026 öğleden sonra)

| Yürürlük | Duyuru | Satır |
|---|---|---|
| 2019-10-01 | 11632 (20.09.2019) | 12 |
| 2019-07-01 | 11867 (21.06.2019) | 10 |
| 2019-04-01 | 12070 (18.03.2019) | 8 |
| 2019-01-02 | 12304 (21.12.2018; dönem "02/01/2019") | 10 |

- GUSGR 2019-10-01'de alınıyor, hiç çıkarılmıyor: Güneş Sigorta 31.08.2020'de Türkiye Sigorta oldu, kod TURSG (şirketin
  31.08.2020 özel durum açıklaması; Ziraat Yatırım TURSG ayrılma akçesi dokümanında aktarılıyor). `ALIASES` GUSGR→TURSG
  eklendi; TURSG'nin kayıttaki ilk olayı 2023-07-03 çıkarılma, zincir bununla her tarihte 100. Kesin KAP bildirim numarası
  bulunmadı (açık uç).
- 11867'de "A.V.O.D" yazılı; kod AVOD.
- DOAS (2019-01-02 çıkış, 2019-10-01 giriş) sabit listeden kayda geçti. Sabit hisse (tam geçmiş) 45 → 44; varsayılan
  sonuçlar değişmedi (202 hisse). `ever_members(full_history=True)` 239.
- 2015 Ç4–2018 Ç4 duyuru numaraları `duyurular-eski` sayfalarında bulundu (11751, 11669, 11596, 11564, 11532, 11511, 11492,
  11503, 11473, 11466, 11443, 12512, 12465); 2015 Ç3 duyurusu daha eski sayfalarda, henüz aranmadı.

## Durma noktası: 2020 Ç3 eklenmedi (çözüldü, yukarıdaki ek)

2020-07-01 (duyuru 12559) eklenince zincir bozuluyor:

- BAGFS 2020-07-01'de alınıyor, 2022-07-01'de (14401) yeniden alınıyor; arada hiçbir çeyrek duyurusunda çıkarılmıyor.
- ECZYT 2020-07-01'de çıkarılıyor, 2021-10-01'de (14213) yeniden çıkarılıyor; arada alınmıyor.

Yedek listeleri bir dönem dışı değişikliği gösteriyor: ECZYT 14118, 14132 ve 14147'de (karar 15.03.2021) 1. yedek,
12664'te (karar 18.06.2021) artık yedek değil. Yani dönem dışı bir tarihte BAGFS çıkarılıp yerine ECZYT alınmış
olmalı. Bu tarih (15.03.2021 ile 18.06.2021 arası) bulunamadı; tahmin yazılmadı.

Etki: 2020-10-01 ile o tarih arasında BAGFS üye görünmüyor (gerçekte üye), ECZYT üye görünüyor (gerçekte değil).
Sayı 100'de kalıyor; diğer 98 hisse doğru. Tarih bulununca iki satır (BAGFS remove, ECZYT add) eklenir.

2020 Ç1'de (11428) ayrı bir sorun var: ADANA (Adana Çimento A) alınıyor, sonra hiç çıkarılmıyor; 2020 Ç3'te OYAKC
alınıyor. Adana Çimento'nun OYAK Çimento birleşmesi ve kod değişikliği dönem dışı bir çıkış gerektiriyor; bu
eklenince üye sayısı 101 oluyor. 2020 Ç3 ve öncesi bu iki dönem dışı olay çözülmeden eklenemez.

## Diğer durumlar

- 12771 (2022 Ç1): BIST 100 tablosu iç içe tablonun içinde ve başlığı "BIST PAY ENDEKSLERİ ... DÖNEMİ
  DEĞİŞİKLİKLERİ". Giriş metninde ilk sayılan endeks BIST 100, sonraki tablo "BIST 50"; BIST 100 tablosu kabul edildi.
- 14118 (2020 Ç4): Şişecam birleşmesi nedeniyle TRKCM, ANACM, SODA çıkarılıyor (duyuru metni). DENCM BIST 100 tablosunda
  yok.
- Yürürlük tarihleri tatil olabilir (2021-01-01, 2022-01-01): duyurunun yazdığı tarih kullanıldı; işlem günü
  olmadığı için üyelik sonucu değişmez.
- Kod değişiklikleri: IPEKE (2021-10 çıkış, 2022-01 giriş) mevcut `ALIASES` ile TRENJ'ye eşleniyor; yeni eşleme
  gerekmedi. Aynı çeyrekte hem alınan hem çıkarılan hisse yok.
- `bist100_stable.csv`'den değişiklik kaydına geçen 3 hisse: ENKAI (2021-07), MAVI (2021-10), BRYAT (2022-01).
  Sabit hisse 50 → 47.
- `ever_members(full_history=True)` 225 hisse (varsayılan 202; fark yalnız 2020-2022 arasında üye olan 23 hisse).

## Kaynak adresleri

- Çıplak `/duyuru/<id>` biçimi artık 404 veriyor; bütün satırlar `/duyuru/<id>/<slug>` biçimine çevrildi (24 adres,
  hepsi 200 döndü).
- 2026-04-01 satırları `15391` gösteriyordu; o çeyreğin duyurusu 15392 (BIST 100 tablosu satırlarla birebir aynı).
- 2022-10-01 satırları bir aracı kurum PDF'ini gösteriyordu; resmi duyuru 12960 ile değiştirildi (tablo aynı).
- KONTR dönem dışı satırları (paratic.com) olduğu gibi bırakıldı.

## Daha geriye gitmek

Duyuru sayfaları 2017'ye kadar aynı biçimde (11473 = 2017 Ç4, 11503 = 2017 Ç3, 11492 = 2017 Ç2, 11511 = 2017 Ç1).
Asıl iş tablo okumak değil, dönem dışı değişiklikleri (birleşme, kod değişikliği, borsadan çıkma) bulmak: her biri
zinciri bozuyor ve Borsa İstanbul duyuru listesinde ayrı başlıkla görünmüyor.

## Etkilenen kod: bugün davranış değişmez

- `COVERAGE_START = 2022-04-01` (K-77). Bütün fonksiyonlar (`load_changes`, `load_stable`, `members_on`,
  `membership_panel`, `ever_members`) varsayılan olarak bu tarihten önceki satırları yok sayar; satırları yalnız
  bu tarihten önce olan ve "add" ile biten hisseler (ENKAI, MAVI, BRYAT) sabit sayılır. Sonuç eski dosyalarla
  birebir aynıdır: 202 hisse, aynı üyelikler (test: `tests/fixtures/bist100_2022/` eski dosyalarla karşılaştırır).
- Eski satırlar yalnız `full_history=True` ile kullanılır (225 hisse). Günlük indirme seti, K-77 / M30 ve
  K-93 / K-94 ön kayıtları değişmez; varsayılanı değiştirmek sahibin kararıdır (18.12 sonrası).
