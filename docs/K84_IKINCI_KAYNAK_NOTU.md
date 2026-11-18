# Karar notu taslağı: Borsa İstanbul resmî gün sonu verisi ikinci kaynak sayılır mı? (18.11.2026)

**Durum: taslak. Uygulanmadı, eşik değişmedi. Karar kullanıcının.**

## 0. Bugünkü durum (önce bilinmesi gereken)
- "Veri doğruluğu" SLO'su artık ❔ değil. 18.11 08:45 ölçümünde ✅ %99,5 çıktı: 206 hissede 1 hisse farklı (RALYH), kaynak "Borsa İstanbul resmî gün sonu" (`logs/price_second_source.json`, `core.reports.slo.accuracy`). ❔ durumu 12.11'deydi; o gün İş Yatırım kapalıydı (D13) ve resmî karşılaştırma daha bağlanmamıştı.
- K-93 (3) (18.11, ön kayıt) bu soruyu zaten yanıtlıyor: resmî veri ikinci kaynak sayılır, "tutuyor" = art arda 4 cumartesi ✅. Bu not bu kararı **yeniden açmıyor**. Ölçütün bir zayıf yanını gösteriyor (§3) ve onaylaman ya da değiştirmen için seçenekleri yazıyor (§4).

## 1. Artılar
- **Üretici kaynak:** Borsa İstanbul fiyatın kendisini üretir; Yahoo yalnız yeniden dağıtır. Seviye 1 kaynak (K-82).
- **Bağımsız:** dosya DataStore'dan gelir; Yahoo'nun akışından ve bizim kodumuzdan bağımsızdır. Okuma kuralları K-84'te sabit, bilinmeyen başlık reddedilir.
- **Ücretsiz ve izinli:** 0 TL, kişisel kullanım (DATA_SOURCES). Yeni hesap, ücret ya da token gerekmez.
- **Geçmişte sınandı:** 467 dosya; 2005 öncesi ölçek kuralı kanıtla seçildi (K-84).

## 2. Eksiler
- **Aylık ve elle indiriliyor:** dosya ay bitince yayımlanıyor ve kullanıcı elle indiriyor. Karşılaştırma bu yüzden her zaman **geçen ayı** ölçer. Bugünkü kontrol (18.11) Ekim dosyasını kullanıyor (`period: 2026-10`); Kasım verisi en erken Aralık başında karşılaştırılabilir.
- **Tarih alanı yanıltıcı:** `price_second_source.json` içindeki `date` her gece kontrolün çalıştığı günü yazıyor (18.11). Veri ise 31.10'da bitiyor. SLO'nun 8 günlük tazelik sınırı (`ACCURACY_MAX_AGE`) bu yüzden veri yaşını değil, kontrolün yaşını ölçüyor.
- **Son gün eksik kalabilir:** Yahoo'nun henüz yayımlamadığı son seans fark sayılmıyor (30.10: 75 hisse); bir sonraki çalışmada karşılaştırılıyor.
- **Düzeltilmiş fiyat yöntemleri aynı olmayabilir:** açıklanamayan farklar KAP'tan ve üçüncü bir kaynaktan doğrulanmadan düzeltilmiyor (karşılaştırma raporunun kendi notu).

## 3. Bu ölçütle geçmiş haftalarda ne çıkardı
| Dönem | Sonuç | Kaynak |
|---|---|---|
| Haziran 2026 | 2 hisse farklı (KONTR, TRILC) | RESEARCH_LOG, K-85 denemesi (11.11) |
| Ağustos 2026 | 0 | aynı |
| Eylül 2026 | 0 | aynı |
| Ekim 2026 | 206 hissede 1 (RALYH, yalnız Yahoo'da 1 gün: 20.10), 4.250 hisse-gün | `logs/resmi_karsilastirma_2026-10.txt` |
| 14.11 haftası | ✅ %99,5 (1/206) | `logs/haftalik_slo/2026-11-14.txt`, `docs/PERIODS/2026-11-14.md` |
| 07.11 ve öncesi | ❔ (İş Yatırım kapalı, resmî karşılaştırma henüz bağlı değil) | MATURITY 12.11 notu |

**Zayıf yan:** K-93 (3) ile 21.11, 28.11 ve 05.12 cumartesileri büyük olasılıkla **aynı Ekim dosyasını** yeniden ölçecek. Kasım dosyası Aralık başında indirilmezse "4 hafta tutuyor" kanıtı fiilen tek bir ayın tek ölçümü olur.

## 4. Seçenekler
- **A. K-93 (3) olduğu gibi kalsın.** Sade ve ön kayıtla uyumlu. Eksi: 4 haftanın 4'ü aynı veriyi ölçebilir.
- **B. K-93 (3) kalsın, kanıt yorumuna bir not eklensin.** Kasım dosyası 05.12'den önce indirilip karşılaştırılırsa "tutuyor" iki ayı kapsar. Bu bir eşik değişikliği değil, senin bir veri adımındır: Kasım dosyası Borsa İstanbul'da yayımlanınca DataStore'dan indirmen gerekir. Önerim bu.
- **C. Yeni ölçüt: sayılan her hafta kontrol edilen verinin son günü en fazla 35 gün eski olsun.** Daha sıkı. Ama bu yeni bir eşik olur ve ölçümden önce yeni bir ön kayıt gerektirir. S2 ve S4 tarihleri büyük olasılıkla Aralık ortasına kayar.
- **D. Resmî veriyi ikinci kaynak saymamak, günlük bir kaynak aramak.** Ücretsiz ve izinli günlük bir kaynak şu an yok (İş Yatırım D13 ile kapandı). Ücretli servis kuralı gereği önerilmez.

## 5. Senden beklenen
Yalnız bir seçim: A, B, C ya da D. C seçilirse önce `on-kayit` ile yeni bir K yazılır, sonra uygulanır. B'de ek iş: Kasım dosyası yayımlanınca indirip `data/inbox/bist/` klasörüne koyman (`core/official/prices.py` `INBOX`).
