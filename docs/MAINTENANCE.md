# Bakım takvimi

CHARTER J2. `/durum`'daki "Bakım takvimi" ve "Tatil takvimi" satırları süresi dolacak işleri önceden söyler.

## Haftalık (kendiliğinden)

| İş | Kim | Nerede görülür |
|---|---|---|
| Geri yükleme testi (izole) | Rapor | Cuma raporu; SLO "Yedek" |
| Araştırma, ikinci kaynak özeti, kurumsal işlem taraması | GitHub (cumartesi) | `research-results` dalı; SLO "Veri doğruluğu" |
| Paket güvenlik taraması | GitHub (pazartesi) | Actions > Security (kırmızıysa e-posta) |
| Kurumsal işlem şüphelerinin KAP'ta doğrulanması | Claude (döngü) | DATA_CORRECTIONS.md |
| Haftalık özet (SLO, gözlemler, sorunlar) | Claude (cumartesi araştırmasından sonra) | Sohbet |

## Aylık

| İş | Kim | Nasıl |
|---|---|---|
| Geri yükleme tatbikatı | Yerel otomasyon | `python -m core.backup --test-restore` (DISASTER_RECOVERY §2) |
| Veri kalitesi raporu | Claude | `python -m core.market.quality` (GitHub'da) |
| Yedek klasörünün PC dışında olduğunu doğrulama | Kullanıcı | OneDrive senkron simgesi; `/durum` "Yedek" |

## Üç aylık

| İş | Ne zaman | Nasıl |
|---|---|---|
| BIST 100 dönem değişiklikleri | Ocak/Nisan/Temmuz/Ekim'in 1'i; duyuru ~10 gün önce | `data/bist100_changes.csv`'ye kaynaklı satırlar, `data/universe.csv` güncelleme; testler 100/100 üyeliği denetler. `/durum` 14 gün önce haber verir, dönem başlayıp girilmediyse uyarır |

## Yıllık

| İş | Ne zaman | Nasıl |
|---|---|---|
| TÜFE ve kur verisi | aylık (kendiliğinden) | Akşam raporu her ayın 3'ünden sonra TCMB tablosundan yeni ayı ekler. `/durum` "Makro veri" 8 gün gecikirse uyarır. Yılda bir, PC'nin eklediği aylar depodaki `data/macro/cpi.csv`'ye taşınır (Claude, arşivli sayfayla). |
| Yeni yılın tatil takvimi | Aralık | `data/bist_holidays.csv`. 2027 satırları geçici olarak girildi (Kanun 2429 ve Diyanet 2027 takvimi). Borsa İstanbul'un Aralık duyurusuyla karşılaştırılır, fark varsa düzeltilir, sonra `calendar.PROVISIONAL`'dan çıkarılır. `/durum` Aralık'tan itibaren geçici yıl için uyarır. |
| Paket sürümleri | Yılda bir ya da güvenlik bulgusunda | Kilit dosyasını yükselt, tam test, küçük sürüm |
| Python sürümü | 3.11 desteği 31.10.2027'de biter | `/durum` 120 gün önce uyarır; geçiş planı DECISIONS'a |
| Stopaj ve faiz tabloları | Değişiklik olduğunda | `data/cash/` (kaynaklı satırlar) |
