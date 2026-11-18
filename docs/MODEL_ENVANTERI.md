# Model envanteri ve model kartı şablonu (ARS-1 L-1, STRATEGY S-1; ilk sürüm 18.11.2026)

**Durum:** ilk sürüm, yalnız kayıtlardan derlendi (DECISIONS, RESEARCH_LOG). Hiçbir hesap yeniden yapılmadı; aşama bilgileri kayıtlarda yazıldığı gibidir.

**Aşamalar (L-1):** fikir → ön kayıt → araştırma → bağımsız doğrulama → kâğıt → izleme → emeklilik.

## Envanter
| Kural | Aile | Aşama | Kanıt | Kart |
|---|---|---|---|---|
| H1 momentum / düşük oynaklık (Aşama 3) | a3 | **emekli** (RED, 27.10.2026) | RESEARCH_LOG:366 | eksik |
| H2 endeks trendi (Aşama 3) | a3 | **emekli** (RED) | RESEARCH_LOG:406 | eksik |
| H3 ay dönümü (Aşama 3) | a3 | **emekli** (RED) | RESEARCH_LOG:406 | eksik |
| H4 eşit ağırlık | a4 | **ön kayıt** (28.10.2026, kesin); tarama 27.04.2027'den önce yapılmaz (kod kapısı) | RESEARCH_LOG:455, `core/backtest/a4.py` | eksik |
| H5 düşük işlem hacmi | a4 | **ön kayıt** (aynı) | aynı | eksik |
| a5 profesyonel filtreler | a5 | **fikir** (ön kayıt taslağı ONAYLANMADI, 29.10) | RESEARCH_LOG:431 | — |
| Canlı teknik görünümler (5 görünüm, `forward._verdict`) | canlı ölçüm | **izleme / araştırma** (S4 ilk karar K-93 (1)) | K-93; `core/reports/s4_decision.py` | eksik |
| "Dip dönüşü" tetiği | K-63 | **araştırma** (ön kayıtlı ölçüm) | DECISIONS K-63 | eksik |
| Sinyal onay katmanı (meta-etiketleme) | K-64 / K-80 | **araştırma** (saatlik ileri test) | DECISIONS K-64, K-80 | eksik |
| Uzun vadeli fiyat faktörleri | K-78 | **araştırma** (keşif ölçümü) | DECISIONS K-78 | eksik |
| Sanal sinyal defteri | K-60 | **kâğıt** (araç; kural değil) | DECISIONS K-60 | — |

**Not:** kayıtlarda "reddedilen fikir türleri" adında ayrı bir özet de var (RESEARCH_LOG:93). Bunlar türdür, tek tek kural değildir; envantere girmez.

## Model kartı şablonu
```
# Model kartı: <kural adı>
- Kimlik ve aile: <ör. a4-H5>
- Aşama ve tarih: <ön kayıt / araştırma / bağımsız doğrulama / kâğıt / izleme / emekli>, <GG.AA.YYYY>
- Amaç: <hangi soruya cevap>
- Kural (sabit parametrelerle): <tam tanım>
- Veri: <kaynak, dönem, evren, veri sürümü/özeti (D-4)>
- Varsayımlar: <maliyet, kayma, gecikme, kapasite (C-1…C-4)>
- Ön kayıt: <K no / RESEARCH_LOG satırı, tarih>
- Deneme sayısı N ve çoklu test düzeltmesi: <S-1, S-2>
- Sonuçlar: <etki ve güven aralığı, DSR, PBO, sağlamlık, rejim, kıyas> (yalnız sonuç geldiyse)
- Bilinen zayıflıklar: <...>
- Bağımsız doğrulama ve kırmızı takım: <tarih, oturum, bulgular> (L-2, L-3)
- İzleme ve sapma eşiği: <L-4>
- Emeklilik ölçütü: <L-5>
- Kanıt bağlantıları: <commit, CI, dosya:satır>
```

## Sonraki adım
Her satır için kart, İP-4 kapsamında (gün 30–60) yazılır. Önce a4'ün H4 ve H5 kartları: ön kayıtları kesin olduğu için kartın sonuç dışındaki her alanı bugünden doldurulabilir.
