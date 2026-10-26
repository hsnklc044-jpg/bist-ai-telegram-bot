# Araştırma kaydı

Her test: hipotez, yöntem, önceden belirlenmiş başarı ölçütü, sonuç ve karar.
Başarısız sonuçlar da yazılır; silinmez. Ölçüt sonuç görüldükten sonra değiştirilmez.

**Ortak başarı ölçütü (2026-10-26'dan itibaren):** strateji, XU100'e göre günlük fazla
getirisinin blok bootstrap güven aralığı (Bonferroni düzeltmeli) tamamen sıfırın üstündeyse
"XU100'ü geçti" sayılır. Aday kurallar ayrıca üç kapıyı geçmelidir (iki başlangıç tarihi,
en kârlı 5 hisse hariç, walk-forward).

Haftalık otomatik çalışmaların tam metni ve özet tablosu GitHub'da `research-results` dalında
(`runs/<tarih>/`, `history.csv`). Bu dosyaya yalnızca yorum ve kararlar yazılır.

---

## 2026-10-26 — Araştırma tablosu, geçmiş BIST 100 üyeliğiyle (v0.24.0)

- **Soru:** Bugünkü hisse listesiyle yapılan testler (survivorship bias) sonuçları ne kadar
  değiştiriyor? Hiçbir strateji XU100'ü istatistiksel olarak geçiyor mu?
- **Yöntem:** 2023-08-01 – 2026-10-23, komisyon %0,10 + kayma %0,05 her yön, nakit %0.
  Evren: 2022'den beri BIST 100'e girmiş 202 hisse, her gün yalnızca o günkü üyeler alınabilir;
  12'sinin verisi yok (çoğu spor kulübü). 6 strateji → %99,2 Bonferroni güven aralığı.
- **Kaynak:** GitHub Actions Research çalışması 40319864774.

| Strateji | Yıllık (geçmiş üyelik) | Yıllık (bugünkü liste) | XU100'e göre fazla getiri, %99,2 GA | Karar |
|---|---|---|---|---|
| Bot sinyali | +12,4% | +7,5% | −1,5% [−28,2%, +23,3%] | anlamlı değil |
| Bot sinyali + rejim | +10,8% | +3,4% | −3,6% [−35,2%, +26,2%] | anlamlı değil |
| Trend kuralı | +34,6% (MaxDD −48,5%) | +17,0% | +17,5% [−32,0%, +60,9%] | anlamlı değil |
| Momentum 6 ay, en iyi 10 | −16,6% | −9,5% | −28,9% [−132%, +39%] | anlamlı değil |
| Momentum + rejim | −12,6% | −2,5% | −24,0% [−142%, +51%] | anlamlı değil |
| Momentum walk-forward | +23,5% | +20,0% | +9,3% [−48,3%, +57,8%] | anlamlı değil |
| XU100 al-tut | +14,6% (MaxDD −26,5%) | | | |

- Walk-forward (geçmiş üyelik): XU100'ü geçen pencere 3/7, medyan test +%18,2,
  en iyi pencere hariç toplam +%12,9. Son pencere (2026-08 → 10) −%50,9 (XU100 −%17,1).
- Aday kurallar (190 hisse): weekly_trend ve dryup_breakout 1. ve 3. kapıyı geçti, ancak
  en kârlı 5 hisse çıkarılınca 2023 başlangıcında XU100'ün altına düştü (2. kapı ✗).
  Kazanç az sayıda hisseye bağlı. grouped_score ve breakout kapıları geçemedi.
- **Karar:** Hiçbir strateji XU100'ü istatistiksel olarak geçmedi. Hiçbiri sinyal olarak
  sunulmaz. Trend kuralının nokta tahmini yüksek ama aralık çok geniş ve düşüşü XU100'ün
  neredeyse iki katı; yalnızca izlenecek aday.

**Yöntem hatası, düzeltildi:** Bu çalışmadan önce GitHub iş akışı yalnızca bugünkü 117 hissenin
verisini indiriyordu; "geçmiş üyelik" testlerinde 202 eski üyenin 90'ı sessizce dışarıda
kalıyordu (`candidates --pit` dahil). Önceki `--pit` sonuçları bu yüzden geçersizdir.
İş akışı artık `--bist100-history` ile indiriyor ve eksik oran %10'u aşarsa rapor uyarıyor.

**Kalan sınırlar:** ~5 yıllık Yahoo verisi (yaklaşık 3 yıllık test dönemi), tek veri kaynağı,
2022 öncesi üyelik yaklaşık (değişiklik listesi 2022'de başlıyor), nakit getirisi %0.
