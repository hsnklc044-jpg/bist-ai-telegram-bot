# Belge haritası: taslak (18.11.2026)

**Durum: taslak.** Hiçbir şey arşivlenmedi, silinmedi, yürürlüğe girmedi. PROGRAM §2'deki gün 1–7 işinin ilk hali; son hali en geç 25.11'de `docs/BELGE_HARITASI.md` olarak sunulur.

**Girdi.** "Claude ile para kazanma sistemi" oturumunun hazırladığı 4 katmanlı özet, `C:\Users\hsnkl\Yeni klasör\quantbist-talimatlar\YONETISIM_TASLAGI.md` (18.11, 4.496 bayt). Özet şu belgelerle karşılaştırıldı:
- `docs/ANAYASA.md` (yürürlükte, K-98);
- `docs/CHARTER.md`;
- `docs/OTONOM_KURALLAR.md` "Kullanıcı çerçevesi";
- `docs/OPERATIONS.md`;
- `docs/MATURITY.md`;
- `docs/DECISIONS.md` (K-93…K-100);
- `docs/CHARTER_2028.md`, `docs/STRATEGY_2031.md`, `docs/GUVENCE.md`, `docs/PROGRAM.md`.

Bu dosyadaki tablolar şu soruların cevabıdır: özetteki hangi madde zaten var, hangisi yeni, hangisi mevcut belgelerle çelişiyor, hangisi uygulanamıyor? Ardından sahibin vermesi gereken kararlar gelir.

## 1. Karşılaştırma tablosu

Durum: **var** (aynı kural yürürlükteki bir belgede) · **yeni** · **çelişiyor** · **uygulanamaz** (bugünkü araçlarla ya da bugünkü kurallarla).

| Taslak maddesi | Durum | Kanıt (yürürlükteki yer) | Not |
|---|---|---|---|
| K1-1 Sahiplik | var | ANAYASA Md. 1 | aynı |
| K1-2 Dürüstlük | var | ANAYASA Md. 2 | aynı |
| K1-3 Ön kayıt | var | ANAYASA Md. 3; CLAUDE.md "ölçümden önce kayıt"; `on-kayit` skill'i | aynı |
| K1-4 Zarar vermeme | var | ANAYASA Md. 4; CHARTER_2028 §2 (SPK) | taslak SPK'yı ilkeye taşıyor; anlamı aynı |
| K1-5 Orantılılık | var | ANAYASA Md. 5 | taslak "belge"yi açıkça ekliyor; anlam genişliyor ama çelişmiyor |
| K1-6 Haftada 30 dk | **çelişiyor** | ANAYASA Md. 6 sınırı stratejiye bırakıyor; CHARTER_2028 H4 **15 dk**; PROGRAM §5 **30 dk** | tek sayı seçilmeli (Karar 2) |
| K1-7 Onay yalnız koordinatör oturumunda | **çelişiyor** (dar) | ANAYASA Md. 8: "sahibin kendi yazdığı açık bir ifade" (oturum sınırı yok); kalıcı çerçeve: "bu oturumda" | ANAYASA'yı daraltmak Md. 17 usulünü ister (7 gün soğuma). Öneri: kural kalıcı çerçevede kalsın, ANAYASA'ya taşınmasın (Karar 3) |
| K1-8 Kayıt değişmezliği | var | ANAYASA Md. 11; CHARTER "kişisel kayıtlar silinmez"; K-99, K-100 | aynı |
| K1-9 Güvenli varsayılan | var | ANAYASA Md. 13; K-99 | aynı |
| K1-10 Değişiklik usulü, çekirdek 1–4 | var | ANAYASA Md. 17, 18 | aynı |
| ANAYASA Md. 14 açık biçim, Md. 15 emeklilik, Md. 16 devir, Md. 19 yorum | **taslakta yok** | ANAYASA | Taslak ANAYASA'nın yerine geçerse bu dört madde düşer. Bu, Md. 17'ye göre değişikliktir. Öneri: taslak ANAYASA'nın yerine geçmez, yalnız bir özettir (Karar 1) |
| K2 Aralık: S2 07.12, S3 12.12 | var | ROADMAP "Aralık hedefi"; K-96; MATURITY | aynı |
| K2 2027: holdout 27.04, a4 ön kaydı, S5 kâğıt üzerinde 3 ay | var | ROADMAP "2027"; K-93; K-94 | aynı |
| K2 2028 senaryolar A/B/C | var | STRATEGY_2031 §1 | yürürlük 2028 sonu |
| K2 kalıcı sütunlar | var | STRATEGY_2031 §2; CHARTER_2028 H2–H4 | aynı |
| K3 Program 1, İP-1…İP-5 | var | PROGRAM §3 | aynı |
| K3 sürekli iyileştirme, 85. gün, 14 gün | var | PROGRAM §9 (QB-SID-1) | aynı |
| K3 durdurma ölçütleri | var | PROGRAM §7 | aynı |
| K4 kontrol listesi K-01…K-10 | var (ad farkı) | GUVENCE §3; KONTROLLER.csv KT-01…KT-10 | Taslak "K-" kullanıyor; DECISIONS K numaralarıyla karışır. Öneri: "KT-" (Karar 5) |
| K4 K-04 "hangi ilke: 1, 7" | var | KONTROLLER.csv KT-04 = Md. 8 | eşleme farkı, önemsiz |
| K4 K-09 "ilke 8" | çelişiyor (eşleme) | KONTROLLER.csv KT-09 = Md. 14 (açık biçim) | taslakta Md. 14 olmadığı için yanlış ilkeye bağlanmış |
| K4 kanarya, önem dereceleri | var | GUVENCE §5, §6; KT-01 kanaryası 18.11 | aynı |
| Rapor biçimi (6 başlık + "Senden beklenen") | var | kalıcı çerçeve; CHARTER_2028 §7 | aynı |
| K3 "S3 oturum açma çözümü" (İP-3) | uygulanamaz (şimdilik) | `docs/S3_OTURUMSUZ_BASLATMA.md`: S4U kipinde ağ erişimi belirsiz, önce deneme gerekir; görev değişikliği sahibin kararı ve ALONE | karar ve deneme sahibin |
| K4 K-08 "kullanıcının süresi" otomatik | uygulanamaz (bugün) | süreyi ölçen bir kaynak yok | Öneri: vekil ölçü olarak haftalık onay mesajı sayısı ve "Senden beklenen" madde sayısı (Karar 4) |

**Özet:** 25 satır. Var: 18 (biri ad farkıyla). Çelişiyor: 3 (K1-6, K1-7, K-09 eşlemesi). Taslakta yok: 1 (ANAYASA'nın 4 maddesi). Uygulanamaz: 2. Yeni kural: 0.

Taslak yeni bir kural getirmiyor; mevcut belgelerin iyi bir özeti. Asıl değeri 4 katmanlı yapı önerisinde.

## 2. Önerilen yapı (PROGRAM §2 hedefi: en fazla 4 katman)

| Katman | Belge | Amaç | Sahibi | Gözden geçirme |
|---|---|---|---|---|
| 1 İlkeler | `ANAYASA.md` (CHARTER'ın ilke kısmı buraya atıfla bağlanır) | değişmez ilkeler | sahip | yılda bir; değişiklik Md. 17 |
| 2 Strateji | `STRATEGY.md` = CHARTER_2028 + STRATEGY_2031 + RISKS | çok yıllı yön, riskler | sahip | yılda bir (aralık) |
| 3 Yıllık plan | `PLAN_2026_2027.md` = ROADMAP üstündeki iki plan + PROGRAM + kalıcı çerçevenin işletme kuralları | bu yılın hedefleri, 90 günlük program | sahip onaylar, koordinatör yazar | 90 günde bir (85. gün önerisi) |
| 4 Kontroller | `GUVENCE.md` + `KONTROLLER.csv` + testler | otomatik denetim | koordinatör | haftalık pano |

Katman dışında kalanlar:
- **İşletme belgeleri** (OPERATIONS, MATURITY, DECISIONS, RESEARCH_LOG, ROADMAP bulguları, CHANGELOG): kayıt ve el kitabıdır, yönetişim belgesi değildir.
- **Görev metinleri:** günlüğe yazılır ve geçer.
- **Arşiv:** birleştirilen eski belgeler `docs/arsiv/` altına taşınır. Silme yok; her birinin başına "yerine: …" notu eklenir.

## 3. Karar paketi (sahip koordinatör oturumunda kendisi onaylar)

| # | Karar | Seçenekler | Önerim | Neden |
|---|---|---|---|---|
| 1 | YONETISIM_TASLAGI'nın yeri | (a) ANAYASA'nın yerine geçer; (b) yalnız özet olarak kalır, ANAYASA aynen sürer | **(b)** | (a) ANAYASA'nın 4 maddesini düşürür; Md. 17 gereği 7 gün soğuma ister |
| 2 | Haftalık süre sınırı | 15 dk (CHARTER_2028) · 30 dk (PROGRAM) · program süresince 30, sonra 15 | **program süresince 30 dk, 16.02.2027'den sonra 15 dk** | ikisini de korur; program başı yoğun |
| 3 | "Onay yalnız koordinatör oturumunda" | (a) ANAYASA Md. 8'e eklenir (Md. 17 usulü); (b) kalıcı çerçevede işletme kuralı olarak kalır | **(b)** | aynı korumayı sağlar, anayasayı değiştirmez |
| 4 | KT-08 süre ölçümü | (a) sahip haftada bir süresini yazar; (b) vekil ölçü: onay mesajı ve "Senden beklenen" madde sayısı | **(b)** | sahibe yük eklemez |
| 5 | Kontrol numaraları | "K-" · "KT-" | **KT-** | DECISIONS K-01…K-100 ile çakışmaz |
| 6 | 4 katmanlı birleştirme ve arşiv | onay · değişiklikle onay · ret | **onay; yapım 25.11'e kadar dalda, canlıya haftalık onay listesiyle** | Md. 5 orantılılık; belge sayısı 10'dan 4'e iner |

**Sahibin tahmini zamanı:** bu paket için 5–10 dakika. Tek mesajla cevaplanabilir, örneğin: "1b 2-öneri 3b 4b 5-KT 6-onay".

## 4. Otomasyon notu
"Claude ile para kazanma sistemi" oturumu ayrı bir otomasyon oturumu kurmuyor. Sonraki adımı PROGRAM §9 döngüsü önerecek (ilk öneri 11.02.2027). Bu, K-100 ve 1s maddesiyle uyumlu; ek iş gerekmiyor.
