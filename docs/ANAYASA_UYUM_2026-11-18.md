# Anayasa uyum taraması (18.11.2026)

Anayasa 18.11.2026 17:23'te sahibin onayıyla yürürlüğe girdi ("Evet, yürürlükte", koordinatör oturumu; DECISIONS K-98). Bu tablo, yürürlük maddesinin istediği taramadır.

**Taranan belgeler:**
- `docs/CHARTER.md`, `docs/OTONOM_KURALLAR.md`, `docs/OPERATIONS.md`, `docs/CHARTER_2028.md`, `docs/STRATEGY_2031.md`, `CLAUDE.md`;
- `.claude/skills/*/SKILL.md`;
- robot görev metinleri (`quantbist-otonom` ve sarmalayıcıları);
- koordinatörün bugünkü kayıtları;
- canlı `data/` klasörünün dosya biçimleri (salt okunur).

**Yöntem:** anahtar sözcük taraması (soru, onay, devir, silme, düzeltme, tavsiye) ve madde madde okuma. Tam bir satır satır denetim değildir; yıllık bağımsız denetim (CHARTER_2028 §4) bunu tamamlar.

**Durum sütunu:**
- "öneri": sahibin kararını bekler;
- "yapıldı": 18.11'de belge düzeltmesi olarak uygulandı (alt belgenin kendi metni değişmedi, yalnız hiyerarşiyi bildiren yeni bir not eklendi);
- sonraki kararlar K-99, K-100, K-101 ve K-102'dedir.

| # | Alt belge ve yer | Madde | Çelişki | Düzeltme önerisi | Karar | Durum |
|---|---|---|---|---|---|---|
| Ç1 | Koordinatörün 18.11 kayıtları: `cikti/OTONOM_RAPOR.md` (16:35, 16:41, 16:56, 17:00, 17:06 satırları) ve `cikti/otonom_kurallar.md` (1g, 1h, 1i) | 11 | Yanlış yazılan saatler eski satırın üstüne düzeltildi. 1g maddesi zincir yeniden kurulunca yerinde yeniden yazıldı. | Bundan sonra düzeltme, eskisine atıf yapan yeni bir satırdır. Bugünkü düzeltmeler 17:25 tarihli düzeltme kaydıyla açıklandı. | Claude (kayıt biçimi) | yapıldı |
| Ç2 | Robot görev metni `quantbist-otonom` ("kullanıcıya soru sorma"); `OTONOM_KURALLAR` D.6 "BOŞ DURMA YOK" | 13, 19 | Robot şüphede de soru sormadan ilerliyor. | Robot şüphede işi yapmaz: soruyu "Senden beklenen" satırına ve "Bekleyenler"e yazar, o iş için güvenli moda geçer. | Sahip | K-100: evet |
| Ç3 | `OTONOM_KURALLAR` "Onay yetkisi devri (10.11.2026)"; `OPERATIONS` §5a; `surum-kapisi` skill'i | 7, 8 | Madde 7'ye göre canlı sistem yalnız sahibindir; otomatik kapı ise kurulum yapıyor. | (a) Devir teknik karar sayılır ve sürer. (b) Her canlı kurulum için açık onay istenir. | Sahip | K-100: (b); K-101 ile 1. sınıf açık ön onay |
| Ç4 | `OTONOM_KURALLAR` "Onay yetkisi devri", "Silme: yalnız yeniden üretilebilenler" | kalıcı çerçeve, 11 | Kalıcı çerçeve "Silme yok" diyor; eski bölüm robota bazı silmelere izin veriyor. | Eski izin geçersiz sayılır. Disk dolmaya yaklaşırsa robot yalnız uyarır. | Sahip | K-100: evet |
| Ç5 | `docs/CHARTER_2028.md`, `docs/STRATEGY_2031.md`, kalıcı çerçeve | Hiyerarşi | Öncelik sıralarında ANAYASA yok. | Her birine yeni bir not: "18.11.2026'dan beri en üstte ANAYASA vardır." Belgelerin kendi metni değişmez. | Claude (belge yapısı) | yapıldı |
| Ç6 | Tek sayfalık özet | 16 | Henüz yok. Eksiktir, çelişki değildir. | STRATEGY S-3 (c) ile aynı iş; Aşama 1'de yapılır. | Claude (takvim) | K-99: 31.01.2027 |
| Ç7 | Canlı `data/`: 3 adet `.db` (SQLite, 458 MB), geri kalanı CSV/MD/TXT/JSON | 14 | SQLite açık ve belgelenmiş bir biçimdir, ama düz metin değildir. | SQLite uygun sayılır; kâğıt sinyal defteri her ay CSV'ye dökülür. | Sahip (yorum) | K-100: dokunulmaz, CSV dökümü 12.12 sonrası |
| Ç8 | Kalıcı çerçeve "Onay yalnız bu oturumda yazılan mesajla" | 8 | Çelişki yok; Madde 8 daha geniştir. | — | — | uyumlu (K-102: 3b) |
| Ç9 | CHARTER, CLAUDE.md, CHARTER_2028 §2, STRATEGY S-5 (al/sat, tavsiye, gerçek para) | 4 | Çelişki yok. | — | — | uyumlu |

**Madde 11'e aykırı düşen işlerim (Ç1):** 18.11'de beş kayıt satırının saatini yerinde düzelttim ve 1g maddesini yerinde yeniden yazdım. Bunlar anayasa yürürlüğe girmeden önceydi; yine de bildiriyorum (Madde 2).

**Kayıt notu (18.11.2026 18:25, Madde 11):** Bu dosya 2846e8f'de doğru yazıldı. Sonraki satır sonu dönüştürme komutundaki bir hata (dosyayı okumadan önce boşaltan `open(p,'wb')`) dosyayı boş bıraktı. İçerik bu commit'le geri yazıldı. Ayrıca 2846e8f'den sonraki karar sonuçlarını gösteren durum sütunları eklendi. Hata ve önlemi DECISIONS K-104'tedir.
