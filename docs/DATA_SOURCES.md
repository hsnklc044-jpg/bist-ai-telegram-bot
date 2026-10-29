# Veri kaynakları ve kullanım koşulları

Talimat C §C1.1 ve AUDIT D5. Sistemin okuduğu ya da okuması planlanan her dış kaynak burada yazılıdır: ne için kullanıldığı, nasıl erişildiği ve kullanım koşulu. Koşulun kanıtı mümkünse `research-results` dalında arşivlenmiş kopyadır (`sources/<tarih>/`, `sources.yml`).

**Kurallar:**
- Ücretli kaynak kullanılmaz.
- Otomatik çekmeyi yasaklayan kaynak kullanılmaz.
- Koşulu doğrulanmamış kaynak otomatik çekilmez; durumu "teyit bekliyor" olur.
- Hiçbir kaynak için şifre ya da token istenmez. Anahtar gerekirse kullanıcı kendi `.env`'ine girer (BENİM ADIMLARIM); depoya girmez.
- KAP ya da Telegram içeriği depoya konmaz ve yeniden yayımlanmaz.

## Durum özeti

| Kaynak | Ne için | Erişim | Koşul | Durum |
|---|---|---|---|---|
| Yahoo Finance (yfinance) | günlük fiyat deposu, XU100, sektör endeksleri, USDTRY ikinci kaynak | resmi olmayan API | şartlar otomatik toplamayı izinsiz yasaklıyor (D15, arşivli) | **kullanımda, kabul edilmiş risk** (K-54): günde bir toplu indirme, genişletilmez |
| İş Yatırım | ikinci kaynak doğrulaması | resmi olmayan uç nokta | robots.txt `/_layouts/` yolunu yasaklıyor (D13) | **kapalı** (K-54, v0.96.1) |
| KAP | kurumsal işlem metinleri, temel veri | Actions `kap.yml`, elle | kullanım koşulu teyit edilmedi | metin yalnız doğrulama için okunur; otomatik temel veri çekme **kapalı** (K-48) |
| TCMB politika faizi | nakit karşılaştırması | elle, `data/cash/policy_rate.csv` | TCMB, kaynak gösterilerek | **kullanımda** |
| TCMB gösterge kurları (XML) | USD/TRY (kullanımda, v0.95.0) | `tcmb.gov.tr/kurlar/` | robots.txt izin veriyor; site şartları: kaynak gösterilerek yayımlanabilir, **ticari kullanım yazılı izne tabi** (arşivli) | **planlı**; kişisel, ticari olmayan kullanım |
| TCMB EVDS | USD/TRY, TÜFE serisi (C, planlı) | web servisi, API anahtarı | kaynak gösterilerek kullanılabilir ve yayımlanabilir (arşivli) | **planlı, yedek yol**; anahtar kullanıcı adımı |
| Yahoo `USDTRY=X` | USD/TRY ikinci kaynak (C, planlı) | yfinance | Yahoo ile aynı | **planlı** |
| TÜFE (TÜİK verisi, TCMB tablosu) | reel getiri | TCMB "Tüketici Fiyatları" sayfası | TCMB site şartları: kaynak gösterilerek, ticari olmayan (arşivli) | **kullanımda (v0.95.0)**; `data/macro/cpi.csv` + PC'nin eklediği aylar |
| Borsa İstanbul (site ve dosyaları) | sektör üyeliği (C, planlı); BIST 100 değişiklikleri (mevcut) | `borsaistanbul.com` | robots.txt `Allow: /`, ama telif bildirimi bilgilerin yazılı izinsiz "kopya edilemez … ileride kullanılmak üzere saklanamaz" diyor (arşivli) | **sektör dosyası kullanılmaz**; mevcut kullanım AUDIT D14, kullanıcı kararı |

## Ayrıntı

### Yahoo Finance
- **Kullanım:** `core/market/provider.py` ve `update.py`. Günlük OHLCV ve XU100 için yfinance kullanılır; kurumsal işlem düzeltmesi bizde yapılır (DATA_CORRECTIONS).
- **Koşul:** yfinance resmi bir API değildir. Yahoo'nun şartları otomatik yollarla veri toplamayı açık izin olmadan yasaklıyor (arşiv `sources/2026-10-29_09-28-44/007.html`, AUDIT D15).
- **Karar (K-54):** ücretsiz ve uyumlu bir BIST kaynağı olmadığı için mevcut kişisel, ticari olmayan, günde bir toplu indirme kabul edilmiş risk olarak sürer.
  - Kullanım genişletilmez: hisse başına ek sorgu ya da sayfa yok.
  - Veri depoya konmaz (`market.db` git dışında).
  - Uyumlu çözüm lisanslı bir veri kaynağıdır; bu bir ödeme kararıdır ve kullanıcınındır.
- **Risk:** uç nokta haber vermeden değişebilir. İkinci kaynak kapalı olduğu için (D13) Veri doğruluğu SLO'su "bilinmiyor"; fiyat kalitesini yalnız `quality` denetimi ve kurumsal işlem kayıtları izliyor.

### İş Yatırım
- **Kullanım:** haftalık ikinci kaynak özeti (`crosscheck`), şüpheli gün doğrulaması (`datacheck.yml`). Fiyatı depoya yazılmaz (K-21).
- **Koşul:** 28.10.2026'da robots.txt'nin kullandığımız `/_layouts/` yolunu yasakladığı görüldü (AUDIT D13). Temel veri kaynağı olarak seçilmedi (K-48).
- **Karar (K-54):** otomatik istek kapatıldı (`crosscheck.ENABLED = False`). 29.10'da robots.txt yeniden arşivlendi; yasak aynen duruyor.

### KAP
- **Kullanım:** kurumsal işlem satırlarının kaynağı. Bildirim metni Actions'ta okunur; satıra yalnız bildirim numarası ve özet yazılır, metin depoya girmez.
- **Koşul:** resmi API yok; kullanım koşulu teyit edilmedi. Otomatik temel veri çekme bu yüzden kapalı (K-48). D talimatı (KAP izleme) kodlanmadan önce bu koşulun teyidi gerekir; D'nin tasarımına yazılır.

### TCMB politika faizi
- **Kullanım:** `data/cash/policy_rate.csv`. Yalnız değişiklik günleri tutulur; her satırda kaynak bulunur. `effective_date`, karardan sonraki iş günüdür. Ayrıntı `data/cash/README.md`'de.
- **C'deki yeri:** dört bazdan "nakde göre" sütunu. Yeni kaynak gerekmez.

### TCMB gösterge kurları ve EVDS (USD/TRY)
- **Birincil (planlı):** `https://www.tcmb.gov.tr/kurlar/YYYYMM/GGAAYYYY.xml` (o günün bülteni) ve `today.xml`.
  - Anahtar gerekmez.
  - USD için `ForexBuying` (döviz alış) kullanılır. Gerekçe: bülten günü sabittir; alış ile satış arasındaki %0,2'lik fark getiri karşılaştırmasında önemsizdir. Seçim sonuç görülmeden yapıldı (K-51).
  - Bülten yalnız iş günlerinde yayımlanır, yaklaşık 15:30'da. Bülten olmayan günde son bülten ileri taşınır.
  - 28.10.2026 yarım gününde arşivlenen `today.xml` 27.10 bültenini gösterdi: USD alış 49,6997, bülten no 2026/203.
- **Kanıt:**
  - `sources/2026-10-28_20-24-31/007.html` (today.xml) ve `003.html` (tcmb.gov.tr robots.txt: yalnız `*/search+results` yasak).
  - `sources/2026-10-28_20-26-19/001.html` (TCMB site kullanım şartları): "Sitede yer alan bilgiler, kaynak gösterilmek suretiyle yayımlanabilir; ancak bu bilgilerin ticari amaçlarla kullanımı TCMB'nin yazılı iznine tabidir."
  - Bu proje kişiseldir ve ticari değildir. Ticari kullanıma geçilirse bu kaynak için izin gerekir.
- **EVDS:** kullanım şartları arşivlendi (`006.html`, PDF):
  - Veriler "kaynak gösterilmek koşuluyla üçüncü kişiler tarafından kullanılabilir ve yayımlanabilir".
  - Ticari kullanımda bile kullanıcıya ek ücret olarak yansıtılmaz.
  - TCMB sorgu limiti koyabilir. İçerik yatırım tavsiyesi değildir.
  - Web servisi bir API anahtarı ister. Bu bir **kullanıcı adımıdır** ve yalnız XML yolu yetmezse gerekir. Şu an gerekmiyor.
- **İkinci kaynak:** Yahoo `USDTRY=X` kapanışı. Fark eşiği C tasarımında (K-51).
- **Gösterim:** çıktıda "Kaynak: TCMB" yazılır.

### TÜFE (TÜİK verisi, TCMB'nin tablosundan)
- **Kullanım:** reel getiri (`core/market/macro.py`, K-51 ve K-52).
- **Kaynak:** TCMB'nin "Tüketici Fiyatları" sayfası. TÜİK'in açıkladığı aylık ve yıllık yüzde değişimleri 2014'ten bugüne tek tabloda veriyor. Arşiv: `sources/2026-10-29_00-47-43/001.html`. TCMB şartları kaynak gösterilerek, ticari olmayan kullanıma izin veriyor.
- **TÜİK'in kendi sitesi kullanılmıyor:** yazılı kullanım koşulu bulunamadı ve sayfa JavaScript istiyor.
- **Endeks:** aylık değişimlerden zincirlenir. TÜİK 2026'da baz yılını 2025=100'e taşıdı; getiri yalnız oranlara baktığı için baz yılı sonucu etkilemez. Kontrol: zincirlenen 12 ay, TÜİK'in açıkladığı yıllık değişimle ±0,15 puan içinde (test).
- **Yayım tarihi:**
  - TÜİK ayın 3'ünde, saat 10:00'da açıklar; 3'ü hafta sonuysa pazartesi.
  - Kaynaklı istisnalar: Nisan 2022 → 5 Mayıs (bayram), Mayıs 2026 → 5 Haziran.
  - Değer, yayım gününün ertesi gününden itibaren kullanılır.
- **Yeni aylar:** akşam raporu her ayın 3'ünden sonra TCMB tablosunu bir kez okur. Yeni ayı `data/macro/cpi_local.csv`'ye ekler (yerel, git dışı). Yayım tarihi olarak **ilk görüldüğü gün** yazılır: gerçek açıklamadan önce olamaz, bu yüzden geleceği görme yoktur. Depodaki satır her zaman yerel satırdan önce gelir.
- **Ay içi tahmin yok:** son açıklanan ay ileri taşınır. Bir aydan kısa pencerede reel getiri nominale eşit çıkabilir; çıktı bunu yazar.

### Borsa İstanbul
- **Telif bildirimi** (`sources/2026-10-28_20-28-55/001.html`):
  - "Kullanıcılar bilgi ve dokümanları, sadece bilgi edinme amacıyla kullanabilir."
  - "Burada mevcut bulunan bilgiler, Borsa İstanbul'un önceden yazılı olarak izni alınmadan kısmen veya tamamen kopya edilemez, uygulamaya konulamaz, dağıtılamaz, kiralanamaz, çoğaltılamaz, alt lisansla kullandırılamaz, değiştirilemez, ileride kullanılmak üzere saklanamaz."
  - robots.txt `Allow: /` diyor, ama bu bir izin değildir; bildirim daha dar olandır.
- **Sektör üyeliği:** sektör endeksi sayfası (`002`) pay–endeks eşleşmesini `/datum/hisse_endeks_ds.csv` dosyasında veriyor. Bildirim saklamayı yasakladığı için bu dosya **indirilmez ve kullanılmaz**. Kural: otomatik çekmeyi ya da saklamayı yasaklayan kaynak kullanılmaz.
- **Sektör endeks fiyatları:** XBANK, XUSIN, XUHIZ, XHOLD ve alt sektörler. Fiyatlar Yahoo'dan alınır (`XBANK.IS` biçimi; mevcut fiyat kaynağıyla aynı koşul). Varlıkları ve geçmişleri kodlamadan önce `datacheck.yml` ile doğrulanır.
- **Sektör ataması için kalan yollar** (K-51):
  1. Borsa İstanbul'dan yazılı izin (kullanıcı adımı).
  2. KAP şirket kartındaki sektör alanı. KAP koşulu teyit edilmedi (K-48).
  3. Yahoo'nun kendi sektör sınıflaması. Farklı bir sınıflamadır, BIST sektör endeksleriyle birebir eşleşmez; kullanılırsa adıyla "Yahoo sektörü" yazılır.
  - Seçilene kadar her hisse "sektör: bilinmiyor" görünür, tahminle doldurulmaz (C3).
- **Mevcut kullanım:**
  - `data/bist100_changes.csv` BIST 100 değişikliklerini Borsa İstanbul duyurularına atıfla tutuyor.
  - `sources.yml` Borsa İstanbul sayfalarını herkese açık `research-results` dalına arşivledi.
  - Bu ikisi bildirimle çelişebilir: AUDIT D14, kullanıcı kararı. O zamana kadar Borsa İstanbul sayfası yeni arşivlenmez ve yeni satır eklenmez. Mevcut dosya araştırmanın survivorship korumasıdır, silinmez. Git geçmişi yeniden yazılmaz.

## Açık işler
- TCMB site kullanım şartları sayfasının arşivi.
- TÜİK'in kendi kullanım koşulu (artık gerekmiyor: veri TCMB tablosundan).
- Sektör ataması kaynağı (Borsa İstanbul izni, KAP ya da Yahoo; K-51).
- AUDIT D14: Borsa İstanbul telif bildirimi ile mevcut kullanım.
- KAP kullanım koşulu (K-48, D'nin kapısı).
- Yahoo ve İş Yatırım lisans durumu (D5, D13).
