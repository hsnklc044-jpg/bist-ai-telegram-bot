# Temel veri girişi (bilanço kalemleri)

6–12 ay modelindeki temel filtre ve profesyonel filtre kartları (Piotroski, Altman, Beneish, Greenblatt,
Novy-Marx) `data/fundamentals.csv` dosyasını okur. Dosya yoksa çıktılarda "Temel filtre: değerlendirilmedi"
yazar ve karar durumu değişmez. KAP'tan otomatik çekme kullanım koşulları teyit edilene kadar kapalı (K-48),
bu yüzden veri elle hazırlanan bir CSV ile girer.

## En küçük girdi

Bir hisse ve bir dönem için 9 ana kalem:

| item | KAP tablosundaki karşılığı |
|---|---|
| revenue | Hasılat |
| gross_profit | Brüt kâr (zarar) |
| net_income | Ana ortaklık paylarına düşen net dönem kârı |
| operating_cash_flow | İşletme faaliyetlerinden nakit akışları |
| total_assets | Toplam varlıklar |
| total_equity | Ana ortaklığa ait özkaynaklar |
| current_assets | Dönen varlıklar |
| current_liabilities | Kısa vadeli yükümlülükler |
| paid_in_capital | Ödenmiş sermaye |

Diğer kalemler (`python -m core.fundamentals.store` içindeki `ITEMS` listesi) isteğe bağlıdır; bazı kartlar
onlarsız "veri yok" der.

## Adımlar

1. Boş tablo: `python -m core.fundamentals.store --template temel.csv --symbols THYAO,GARAN --period 2026-09-30`
   (var olan dosyanın üzerine yazmaz).
2. Her satırda `value`, `published_at` ve `source` sütunlarını doldur.
3. Deneme: `python -m core.fundamentals.store --check temel.csv`. Hiçbir şey yazmaz; eklenecek, zaten var olan
   ve reddedilecek satırları, her raporda eksik kalan ana kalemleri sayar.
4. İçe aktarma: `python -m core.fundamentals.store --import temel.csv`, ya da dosyayı `data/inbox/temel/`
   klasörüne bırak (bot birkaç dakikada bir okur, sonucu Telegram'dan bildirir).

## Kurallar

- **Birim TL.** KAP tablosu "bin TL" ise değeri 1000 ile çarp. Başka birim reddedilir.
- **Sayı biçimi:** ondalık ayırıcı nokta, binlik ayırıcı yok (`1234567.5`). Zarar eksi işaretle.
- **published_at:** bildirimin KAP'ta yayınlandığı an, saat dilimiyle: `2026-11-05T18:32:00+03:00`.
  Dönem sonundan sonra olmalı. Saat 18:00'den sonra yayınlanan bir rapor ertesi seanstan itibaren görülür.
- **consolidated:** konsolide tablo 1, solo tablo 0.
- **inflation_adjusted:** TMS 29 enflasyon düzeltmeli tablo 1 (2023 yıl sonu raporlarından itibaren), düzeltmesiz
  0, bilinmiyorsa boş. Büyüme oranları ikisini karıştırmaz.
- **source:** KAP bildirim bağlantısı ya da sağlayıcı adı; boş bırakılamaz.
- **Ara dönem nakit akışı** KAP'ta yıl başından birikimlidir (9 aylık rapor = ocak–eylül). Değeri tabloda
  yazdığı gibi gir; dönem `period_end` ile ayırt edilir.
- **Düzeltme:** yanlış girilmiş bir değer silinmez. Doğrusunu daha sonraki bir `published_at` ile yeni satır olarak
  gir; her gün o güne kadar yayınlanmış en yeni satır geçerlidir.
