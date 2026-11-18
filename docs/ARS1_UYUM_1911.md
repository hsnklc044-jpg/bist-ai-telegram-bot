# ARS-1 ile mevcut belgeler: çelişki tablosu (18.11.2026)

Bu dosya QB-ARS-1 için [BELGE_HARITASI_TASLAK](BELGE_HARITASI_TASLAK.md) biçimindedir.

**Durum:** ARS-1 taslaktır (sahibin gece talimatı, K-104). Hiçbir kural değişmedi.

**Karşılaştırılan belgeler:**
- DECISIONS: K-93 (S4/S5 hazırlığı), K-94 (S5 kâğıt defter), K-91 (Ö48), K-84 ve K-97 (resmî veri)
- MATURITY S4 ve S5
- `RESEARCH_LOG.md`
- `OPERATIONS.md`
- `CHARTER.md`
- 2027 planı (ROADMAP)
- ANAYASA

Durum sütunundaki değerler: **var** · **yeni** · **çelişiyor** · **uygulanamaz** (bugün) · **ön kayıtla kilitli** (K-93/K-94 değişmez; ARS testi yalnız ek bilgi).

| ARS-1 maddesi | Durum | Kanıt | Not / öneri |
|---|---|---|---|
| D-1 zamana sadık veri | var (kısmi) | `test_no_lookahead`, geçmiş endeks üyeliği (ROADMAP aşama C3) | Bilanço yayım tarihleri ayrıca denetlenmeli: veri denetimi D-1 (`VERI_DENETIMI_1911.md`) |
| D-2 hayatta kalan yanlılığı | var (kısmi) | K-36 (BIST 100 geçmiş üyelik); C3 survivorship testleri | Borsadan çıkan hisselerin fiyatının da veride olup olmadığı ölçülmeli: veri denetimi D-2 |
| D-3 kurumsal işlemler | var | `data/corporate_actions.csv` (OPERATIONS §2: her satırda kaynak ve gerekçe) | — |
| D-4 veri soy ağacı | kısmi | veri kesiti dondurma (OPERATIONS §7c, K-76); sonuç–veri özeti bağı yok | Yeni: deney kaydında veri özeti alanı (Faz A) |
| D-5 veri kalitesi raporu | var (kısmi) | SLO "Veri tazeliği", "Veri doğruluğu" (iki kaynak, K-93 (3), K-97) | Araştırma başına ek rapor yeni |
| C-1 likiditeye göre kayma | **ön kayıtla kilitli** | K-94 (c): kayma varsayımı %0,05, eşik %0,10 | K-94 değişmez. ARS kayma modeli yalnız ek bilgi |
| C-1 maliyet (%0,30) | **ön kayıtla kilitli** | K-93 (4): maliyet %0,30 sonrası %99 alt uç > 0 | aynı |
| C-2 fiyat adımı, tavan/taban | var | Ö48 / K-91 (kilitli seans) | tutarlı |
| C-3 kapasite | var (S5 için) | K-94 (c): günlük hacmin ≤ %1'i | S4 taraması için yeni |
| C-4 uygulama gecikmesi | kısmi | K-93 (1) `forward._verdict` ertesi seans; ayrıntı denetlenmeli | veri denetimi D-1 kapsamında bakılır |
| S-1 deneme kaydı | var (kısmi) | DECISIONS'ta deneme sayıları (K-85 vb.), `on-kayit` skill'i | Merkezî sayaç yok: Faz A deneme sayacı |
| S-2 çoklu test düzeltmesi | **ön kayıtla kilitli** (S4) | K-93 (4) tek eşik; düzeltme yöntemi seçilmemiş | a4 ön kaydında (Nisan 2027) seçilir; S4 ilk karar için yalnız ek bilgi |
| S-3 DSR, PSR, PBO | yeni | — | Faz B kütüphanesi (bu gece PSR, DSR) |
| S-4 CPCV | yeni | — | Tasarım notu `CPCV_TASARIM.md` |
| S-5 etki büyüklüğü | var | K-93 (4) güven aralığı alt ucu | tutarlı |
| S-6 sağlamlık | yeni | — | a4 ön kaydına girer |
| R-1 rejim analizi | yeni | — | rejim tanımlarının ön kaydı Faz C (Şubat–Mart) |
| R-2 risk ölçüleri | var (S5) | K-94 (d), K-93 (5) risk sınırları | tutarlı |
| R-3 kuyruk riski | yeni | — | a4 raporuna |
| R-4 rastgele seçim kıyası | yeni | — | tasarım `RASTGELE_KIYAS_TASARIM.md`; kod tasarım onayından sonra |
| L-1 aşamalar | var (benzer) | MATURITY S4 → S5 | model kartı yeni (İP-4) |
| L-2 bağımsız doğrulama oturumu | **uygulanamaz (bugün)** | 18.11'de güvenlik denetimi yeni oturum açmayı (`start_session`) reddetti | Sahip oturumu kendisi açar ya da bir alt ajan (temiz bağlam) kullanılır. Karar sahibin |
| L-3 kırmızı takım | uygulanamaz (bugün) | aynı | aynı |
| L-4 dağılım kayması | var (benzer) | K-94 (b) canlı %95 aralığı | eşik ön kayıtlı, tutarlı |
| L-5 emeklilik | yeni | STRATEGY_2031 S-1 ile aynı yön | — |
| §6 `data/deneyler/` | yeni | — | `data/` canlıda kişisel kayıt klasörüdür. Faz A yalnız kod ve testtir; klasörü canlıda araç oluşturur. Bu gece canlıya yazılmaz |
| §7 S6 seviyesi | karar talebi | MATURITY S1–S5 | [S6_KARAR_TALEBI](S6_KARAR_TALEBI.md) |
| Yürürlük | **çelişiyordu, düzeltildi** | K-103 "yürürlük 18.11"; gece talimatı "taslak olarak ekle" | K-104 yeni kayıtla düzeltir: ARS-1 taslaktır (Md. 11; K-103 silinmez) |

**Özet:** 28 satır.

| Durum | Sayı |
|---|---|
| var ya da kısmi | 13 |
| yeni | 8 |
| ön kayıtla kilitli | 3 |
| uygulanamaz | 2 |
| karar talebi | 1 |
| çelişiyordu, düzeltildi | 1 |

K-93 ve K-94 ile gerçek bir çelişki yok, çünkü ARS-1 kendi yürürlük kuralıyla onları dışarıda bırakıyor.

## Ek bulgu (18:28): a4 ön kaydı zaten kesinleşmiş (en önemli satır)
`docs/RESEARCH_LOG.md` satır 455'e göre a4 ön kaydı **28.10.2026'da onaylanmış ve "değiştirilmez"** diye kayda geçmiş (K-28 devriyle, Claude). Kayıt şunları sabitliyor:
- hipotezler: H4 eşit ağırlık, H5 düşük işlem hacmi;
- maliyet: %0,10 + %0,05;
- ölçüt: XU100'e göre blok bootstrap güven aralığı, Bonferroni ile %97,5;
- sağlamlık kapıları;
- holdout: 250 seans, en erken Kasım 2027;
- tarih kapısı: 27.04.2027, kodla zorlanıyor (`core/backtest/a4.py`).

**Çelişki:**
- 2027 planı (ROADMAP) ve ARS-1 yürürlük kuralı, a4 ön kaydının "Nisan başında bu standarda göre yazılacağını" söylüyor.
- ANAYASA Md. 3 ve ARS-1'in kendi kuralı ("kesinleşmiş ön kayıtlar geriye dönük değiştirilmez") ise 28.10 kaydını koruyor.
- 28.10 kaydını Nisan'da yeniden yazmak, sonuç görülmeden de olsa, ölçütü sonradan değiştirmek olur.

**Seçenekler (sahibin kararı, ANAYASA Md. 7):**
- **(a) Önerim.** a4 28.10 kaydıyla aynen çalışır. ARS-1 testleri (DSR, PBO, R-4 ve diğerleri) a4 için yalnız ek bilgi olarak raporlanır. ARS-1'e göre yazılacak ilk ön kayıt bir sonraki hipotez döngüsüdür (a5 ya da a6). 2027 planındaki "a4 ön kaydı Nisan başında yazılır" maddesi "a4 Nisan'da 28.10 kaydıyla çalışır; ARS ek raporu hazırlanır" diye düzeltilir.
- **(b)** a4 iptal edilir, ARS-1'e göre yeni bir ön kayıt yazılır. Bu, kesinleşmiş bir kaydı bırakmak demektir; gerekçesi DECISIONS'a yazılır. Eski kayıt silinmez.

Satır sayısı: 28 + 1 = 29.

