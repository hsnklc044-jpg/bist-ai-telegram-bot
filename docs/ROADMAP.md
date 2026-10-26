# QuantBIST yol haritası ve açık sorunlar

Son doğrulanmış nokta, ardından önceliklendirilmiş işler. Her sürümden sonra
güncellenir; tamamlanan iş, kanıtıyla birlikte "Doğrulanmış durum" bölümüne taşınır.

## Kaldığım yer (27.10.2026, kod v0.41.0)

- **Son sürüm:** v0.41.0. CI yeşil. Kullanıcı PC'si v0.35.0'da; v0.36–v0.41 PC'de doğrulanmadı.
- **Süren iş:** GitHub'da araştırma çalışması 40411662540 (v0.40.0, başlangıç tarihi elle verildi, `history.csv`'ye yazılmaz). Amaç sağlamlık bölümünü gerçek veride görmek.
- **Sıradaki adımlar:**
  1. Bu çalışma bittikten sonra v0.41.0 ile bir araştırma çalışması daha başlat (başlangıç tarihi 2023-08-01).
  2. Çıkan `view_expectations.csv` dosyasını kontrol et ve `data/` içine ekle. Bu dosya yokken `/performans` "geçmiş" sütununu göstermez.
  3. Sonuçları docs/RESEARCH_LOG.md'ye yaz.
- **Kullanıcıdan beklenen:**
  - v0.41.0 kurulumu: 371 test, `--market-db`, `--test-restore`, `/durum`.
  - KCAER katsayısı kararı (0,8650 → 0,8646).
  - Kapanış düzeltmeleri kapalı kalsın mı (öneri: kalsın).
- **Aşama 3** (yeni sinyal araştırması), PC doğrulaması tamamlanmadan başlamaz.

## Doğrulanmış durum (27.10.2026; kod v0.41.0, kullanıcı PC'si v0.35.0)

İşletim, yedek ve kurtarma: docs/OPERATIONS.md.

| Bileşen | Durum | Kanıt |
|---|---|---|
| Kod ve bağımlılıklar | Doğrulandı | CI yeşil; kullanıcı PC'sinde v0.35.0 ile 334 test (27.10) |
| Telegram botu | Doğrulandı | `/help` tek sürüm yanıtlıyor (26.10 14:11) |
| Zamanlayıcı | Doğrulandı | Windows görevi tek zamanlayıcı; 26.10 18:30 raporu zamanında geldi |
| Günlük rapor teslimi | Doğrulandı | 26.10.2026 kapanış raporu 18:30'da Telegram'a geldi, tek mesaj |
| Sanal emir dolumu (v0.28 alanları) | Doğrulandı | #1 THYAO 10 adet: açılış 260,25 + %0,05 kayma = 260,38; komisyon 2,60 TL; hesap 97.394 + 2.582 = 99.976 TL |
| Yedek ve geri yükleme | Doğrulandı | Günlük yedek 5 dosya (OneDrive). Kullanıcı provası (27.10, kopya üzerinde): ledger.csv bozuldu, paper_orders.csv boşaltıldı; `--restore` sonrası 5 dosya SHA-256 ile birebir aynı |
| `data/signal_log.csv` | Doğrulandı | 26.10 14:42 elle çalıştırma: 117 hisse kaydı |
| `logs/runs.csv` `sent` satırı, `/durum`, 20:00 kontrolü | **Kullanıcıdan kanıt bekleniyor** | Rapor geldiği için büyük olasılıkla doğru; çıktı görülmedi |
| Portföy "Risk:" satırı (v0.29) | Doğrulandı | Kullanıcı PC'si v0.35.0 raporunda görünüyor (27.10); etkin pozisyon sayısı hatası (1.498,7 yerine 1,0) kullanıcı tarafından bulundu, v0.36.1'de düzeltildi |
| Yarım gün / tatil davranışı | **Doğrulanmadı** | 28.10 yarım gün, 29.10 tatil |
| Cuma canlı ölçüm satırı | **Doğrulanmadı** | İlk görülme hedefi 30.10.2026 |
| Cumartesi araştırma iş akışı | Elle doğrulandı (pipefail ile çıktı dosyaları kontrol edildi, run 40377109448); zamanlanmış çalışma doğrulanmadı | İlk zamanlanmış çalışma 31.10 |
| İkinci kaynak kontrolü | Son 30 gün doğrulandı (116 tutarlı, XU100 tutarlı); 2022 sonrası tam tarama sürüyor | run 40377105196 |
| Test kapsamı | %90 satır (core + bot) | `coverage run -m pytest` |

## Bulgular

**İşletim**
- PC'de iki zamanlayıcı aynı anda çalışabilir: `scripts/register_daily_task.ps1` (Windows
  görevi, 18:30) ve `DAILY_REPORT_AT` (bot içi, 18:30). İkisi açıksa rapor iki kez gider ve iki
  süreç aynı anda `paper_orders.csv` / `ledger.csv` dosyalarını okuyup yazar: bekleyen bir sanal
  emir iki kez dolabilir. Kullanıcı PC'sinde Windows görevi kurulu çıktı (26.10); `DAILY_REPORT_AT`
  kaldırıldı. v0.22.0'dan itibaren kilit ve `logs/runs.csv` ikinci çalıştırmayı engeller.
- Bot içi zamanlayıcıda kaçırılan çalıştırma telafisi (misfire) ayarlanmamış: PC 18:30'da uykudaysa
  o günün raporu gitmez. Windows görevinde `StartWhenAvailable` var.
- Resmi tatillerde rapor yine çalışır ve önceki seansın verisini yeniden gönderir (kayıtlar tekrar
  yazılmaz, çünkü veri tarihine göre tekilleştirilir).
- Sistem sağlığı tek yerden görülemiyor: son rapor, son veri tarihi, son yedek, signal_log satır
  sayısı için bir komut yok.

**Araştırma**
- Düzeltildi (v0.24.0): `core.backtest.research` artık geçmiş BIST 100 üyeliğini kullanıyor; GitHub iş
  akışı eski üyelerin verisini indirmiyordu, bu yüzden önceki `--pit` sonuçları da eksik evrenle
  hesaplanmıştı (90/202 hisse dışarıda). Ayrıntı: docs/RESEARCH_LOG.md.
- Momentum walk-forward'un +%20 yıllık sonucu tek bir test penceresinden (+%140) geliyor; son
  pencere −%66,5. Pencere dağılımı ve güven aralığı raporlanmıyor.
- Aday kurallardan hiçbiri üç kapıyı geçmiyor (26.10 çalışması). Teknik skor (bot sinyali) yıllık
  +%7,5, XU100 +%14,6.
- Araştırma sonuçları yalnızca Actions özetinde (90 gün sonra silinir); hipotez ve sonuç kaydı yok.
- Veri geçmişi ~5 yıl (Yahoo); test dönemi ~3 yıl. Tek veri kaynağı.

**Veri**
- KPOWR verisiz; SASA'da 151 gün hacim eksik. CANTE (2026-01-26) ve KCAER (2024-11-28) bilinçli
  olarak düzeltilmedi.

**Test kapsamı boşlukları**
- `bot/watchlist.py` %28, `bot/portfolio.py` %34, `core/market/update.py` %32,
  `core/backtest/candidates.py` %22. PowerShell betikleri test edilmiyor.

## Öncelikli işler

Ölçüt sırası: güvenlik ve veri bütünlüğü → hesap doğruluğu → strateji doğrulama değeri →
kullanıcı faydası → sürdürülebilirlik → maliyet/risk.

| # | İş | Önem | Fayda | Uygulama riski | Modüller | Gerekli testler | Kabul kriteri |
|---|---|---|---|---|---|---|---|
| 1 | ✅ v0.22.0 (PC'de doğrulama bekliyor) — Tek çalıştırma güvencesi: rapor için dosya kilidi ve "bu veri günü için gönderildi" kaydı | Kritik | Çift rapor ve çift sanal dolum imkânsız olur | Düşük | `core/reports/daily.py`, `bot/scheduler.py` | Eşzamanlı iki çalıştırma; aynı gün ikinci çalıştırma; `/report` elle çalıştırma | İki süreç aynı anda başlasa da tek mesaj, tek dolum; `/report` yine çalışır |
| 2 | ✅ v0.23.0 (PC'de doğrulama bekliyor) — Sistem sağlığı: çalıştırma kaydı (`logs/runs.csv`), `/durum` komutu, kaçırılan rapor telafisi | Yüksek | Rapor gitmediğinde fark edilir; uyku/kapanma sonrası telafi | Düşük | `daily.py`, `scheduler.py`, `bot/` | Kaçırılan gün senaryosu; sağlık metni; veri yokken "bilinmiyor" (asla "sağlıklı" değil) | `/durum` son rapor, son veri tarihi, son yedek, signal_log satırı gösterir; uyanınca aynı gün rapor gider |
| 3 | ✅ v0.24.0 (sonuçlar: docs/RESEARCH_LOG.md) — Araştırmada istatistiksel doğrulama: research için PIT evren, pencere bazlı sonuç, blok bootstrap güven aralığı, çoklu deneme düzeltmesi | Yüksek | Rastlantısal sonuçların başarı gibi görünmesi engellenir | Orta | `core/backtest/research.py`, `reliability.py`, yeni test | Bilinen sıfır-beklentili seride CI sıfırı kapsar; PIT ile eski sonuçların karşılaştırması | Haftalık tablo her strateji için CI ve "anlamlı değil" etiketi gösterir |
| 4 | ✅ v0.25.0 (`research-results` dalı, `history.csv`, `docs/RESEARCH_LOG.md`) — Araştırma kaydı: `docs/RESEARCH_LOG.md` (hipotez, ön tanımlı ölçüt, sonuç, olumsuz sonuçlar dahil) ve haftalık sonuçların kalıcı saklanması | Yüksek | Süreklilik; veri gözetleme (snooping) izlenebilir | Düşük | `docs/`, `research.yml` | İş akışı çıktısı dosya olarak kalır | Her araştırma hipotezle başlar, sonuç tarihli kayıtlıdır |
| 5 | ✅ v0.26.0 (2026 takvimi; 2027 Aralık'ta eklenecek) — BIST takvimi: tatil/seanssız gün tespiti (yeni mum yoksa rapor "seans yok" der, yeniden göndermez) | Orta | Yanıltıcı tekrar raporu kalkar | Düşük | `daily.py`, `core/market/calendar.py` | Tatil günü simülasyonu; yarım gün (arife) mumu | Seanssız günde tek kısa bildirim veya hiç mesaj |
| 6 | ✅ v0.27.0 — Canlı ölçüm bütünlüğü: signal_log denetimi (tekrar, eksik gün, veri tarihi gecikmesi) ve `/performans`ta kayıt sağlığı | Orta | Canlı sonuçlara güven | Düşük | `core/reports/forward.py`, `core/signals_log.py` | Bozuk/tekrarlı log örnekleri | Eksik gün ve gecikmeler raporda görünür |
| 7 | ✅ v0.28.0 (kullanıcı onaylı, 26.10) — Sanal işlem kaydını zenginleştirme: emir gerekçesi/kaynağı, giriş anındaki risk, gerçekleşme koşulu (tavan/taban kilidi notu) | Orta | Her sanal işlem izlenebilir | Orta (dosya şeması değişir → onay gerekir) | `core/ledger/paper.py`, `book.py` | Eski dosyanın yeni şemayla okunması | Eski kayıtlar değişmeden okunur; yeni alanlar dolar |
| 8 | ✅ v0.29.0 (sektör verisi yok; sektör yoğunlaşması açık) — Portföy riski: yoğunlaşma, korelasyon ve likidite uyarıları (sektör verisi gerekirse ayrıca) | Orta | Risk tek hisse stop'undan genişler | Orta | `core/alerts/rules.py` | Sentetik portföylerle eşik testleri | Uyarı kuralları belgelenmiş ve testli; veri yoksa "hesaplanamadı" |
| 9 | ✅ v0.31.0 (İş Yatırım, getiri bazlı haftalık kontrol) — Veri kalitesi: ikinci kaynakla örneklem karşılaştırma, hacim eksikleri için uyarı | Orta | Tek kaynak riski azalır | Orta (ücretsiz kaynak sınırlı) | `core/market/` | Kaynak farkı tespiti | Fark eşiği aşan hisse raporlanır |
| 10 | ✅ v0.30.0 (hedef modüller %89–93; toplam %90) — Test boşlukları: bot komutları (watchlist, portfolio), `market/update`, `candidates` | Düşük-orta | Gerilemeler erken yakalanır | Düşük | `tests/` | — | Bu modüllerde kapsam ≥ %70 |

## Karar notları

- 2026-10: Teknik skor yatırım sinyali olarak sunulmaz; backtest'te XU100'ü geçmedi.
- 2026-10: KCAER/CANTE fiyat düzeltmesi yapılmadı (çift düzeltme riski).
- 2026-10: Eski karar katmanı (AL/SAT etiketleri, AI modülleri) kaldırıldı (v0.20.0, kullanıcı onaylı).
- Gerçek emir entegrasyonu: yalnızca canlı ölçüm bir kuralı istatistiksel olarak kanıtlarsa ve açık onayla.
