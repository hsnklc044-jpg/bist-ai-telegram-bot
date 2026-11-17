# Kâğıt üzerinde işlem defteri (S5 tasarımı, 18.11.2026)

**Durum: tasarım. Uygulanmadı.** Yalnız S4'te bir kural K-93 (4) eşiğini geçerse ve kullanıcı S5'i açarsa kurulur. **Gerçek para yok, aracı kurum yok, emir yok** (K-54). Bunu her CI'da `tests/test_no_orders.py` denetler: kodda aracı kurum ya da borsa SDK'sı yok, emir ucu (`/order`, `/trade` vb.) yok, KAP sorgusu dışında HTTP POST yok, defter modüllerinde ağ kütüphanesi yok. Eşikler: DECISIONS K-93 (5) ve K-94.

## 1. Neyin üstüne kurulur
Yeni bir defter yazılmaz; var olan iki çevrimdışı defter kullanılır:
- `core/signals/store.py` (K-60/K-67): sinyal defteri (SQLite), %1 risk lot hesabı, %6 şalter, onay düğmesi. Metni: "Sanal kayıttır; emir oluşturulmaz."
- `core/ledger/paper.py`: sanal emirler, açılışta dolum, komisyon ve kayma, kilitli günde dolum yok.

S5 defteri bunların yanında `logs/kagit_defter/` altında tutulan, yalnız S5 kuralına ait bir görünümdür.

## 2. Sinyal
- Kaynak: S4'te eşiği geçen tek kural. Kural ön kayıttaki tanımıyla kullanılır, parametresi değişmez.
- Zaman: kural akşam 18:30 raporundan sonra, o günün kesin kapanışıyla hesaplanır. Sinyal tarihi = veri günü.
- Kayıt: `tarih, hisse, kural, puan/gerekçe, veri_gunu, ref_kapanis`. Bu kayıt sonuç bilinmeden yazılır ve sonradan değiştirilmez.

## 3. Varsayılan giriş ve çıkış
| | Kural |
|---|---|
| Giriş | Sinyalden sonraki ilk seansın açılışı. Tavanda kilitliyse dolmaz, ertesi seansa kalır (K-75) |
| Çıkış | Kuralın kendi çıkışı; yoksa 5. seansın kapanışı. Tabanda kilitliyse ilk kilitsiz açılış (K-91 ile aynı) |
| Stop/hedef aynı mumda | K-90: açılış hedefin üstündeyse hedef, değilse stop |
| Büyüklük | `store.size_position`: işlem başına kasanın %1 riski, tek hisse ≤ %10 |

## 4. Maliyet ve kayma modeli (K-94)
- Komisyon: her yönde %0,10 (`COMMISSION`).
- Kayma: alışta açılış × (1 + %0,05), satışta açılış × (1 − %0,05) (`SLIPPAGE`). Gidiş-dönüş toplam ≈ %0,30, K-93 (4) eşiğinde düşülen tutarla aynı.
- Gerçekçilik denetimi: kâğıt dolum fiyatı ile o seansın gerçek açılışı arasındaki fark ve işlem tutarı / günlük işlem hacmi her satıra yazılır. Ortalama kayma > %0,10 ya da hacim payı > %1 ise S5 kanıtı "geçmedi" olur. Model sonradan iyileştirilmez.

## 5. Risk sınırları (K-93 (5))
| Sınır | Değer | Aşılınca |
|---|---|---|
| Tek hisse ağırlığı | ≤ %10 kasa | Lot küçültülür |
| İşlem başına risk | ≤ %1 kasa (stop mesafesiyle) | Lot küçültülür |
| Günlük gerçekleşen kayıp | ≤ %2 kasa | O gün yeni sinyal açılmaz |
| Toplam kayıp (şalter) | ≤ %6 | Yeni sinyal durur (K-60) |
| Art arda zarar | 5 işlem | Yeni sinyal durur; yalnız kullanıcının `/devam` komutu açar |

## 6. Günlük kayıt
Her seans günü 21:00'de bir dosya yazılır: `logs/kagit_defter/YYYY-MM-DD.csv` ve tek satırlık özet.
- Sütunlar: `tarih, hisse, olay (sinyal/giris/cikis/sinir/kayit_yok), fiyat, acilis, kayma, komisyon, adet, tutar, hacim_payi, kasa, gunluk_kar, toplam_kar, xu100_ayni_gun, not`.
- Kaçan gün geriye doldurulmaz. Ertesi gün `kayit_yok` olayı yazılır ve o gün 60 seanslık sayaçta eksik kalır (K-94 (a)).
- Haftalık özet cumartesi 21:00 SLO tablosunun altına eklenir: kural − XU100, maliyet sonrası, %95 aralık, kaçıncı seans (x/60).

## 7. Ne zaman ve nasıl açılır
1. S4'te K-93 (4) eşiği geçilir. Bot "🔔 Kural anlamlı çıktı" mesajını kanıtıyla bir kez gönderir (`core/reports/s4_decision.py`) ve hiçbir şeyi açmaz.
2. S4'ün beş satırı kapanmış olmalı (seviye atlanmaz).
3. Kullanıcı S5'i açık bir kararla açar. Kurulum ayrı bir dalda, önce testle ve kapıdan geçerek yapılır.
4. 60 seans sonra K-94 ölçütü uygulanır ve sonuç RESEARCH_LOG'a yazılır. Geçmezse kural yeni ayarla denenmez.
