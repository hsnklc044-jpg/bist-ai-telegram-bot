# Durum notu (05.11.2026, kod v0.99.88)

Bağlam sıkıştırılınca ilk iş bu dosya okunur ve buna göre devam edilir (kullanıcı talimatı, 04.11.2026).

## Faz B (ROADMAP "Eksiksiz iş planı")
- ✅ 1. adım (v0.99.73): `core/market/limits.py`, tek tavan/taban kuralı; %9,5 ve 1e-9 pay; 10 modül bunu kullanıyor; test, modüllerin kendi karşılaştırmasını yasaklıyor.
- ✅ 2. adım (v0.99.74): Kilitli günde dolum yok. Tabanda kilitli gün satış, tavanda kilitli gün alış dolmuyor. Defter, ML etiketleri, senaryolar ve karne.
- ✅ 3. adım: Yeniden ölçümler yapıldı ve RESEARCH_LOG'a eklendi ("04.11.2026 – Faz B yeniden ölçümleri"). Hiçbir karar değişmedi.
- ❌ K-64 kural/pencere ayrımı: geçersiz (aşağıda).
- ✅ **Faz B kapandı (04.11)**: `docs/FAZ_B_KAPANIS.md`. Kullanıcı A seçeneğini onayladı; ayrım ölçümü yeniden çalıştırılmayacak.
- ✅ Sonraki adım önerisi verildi. Kullanıcı **seçenek 1'i onayladı (04.11)**: ileri test için ölçüm altyapısını sağlamlaştırmak.

## Seçenek 1: ölçüm altyapısı (K-76) – ✅ tamamlandı
- Önceden sabitlenmiş başarı ölçütü:
  - (a) Her ölçüm adımı veri aralığını, satır sayısını, veri SHA-256 özetini ve kod commit'ini yazdırıyor.
  - (b) Aynı dondurulmuş veride iki çalıştırma birebir aynı rapor veriyor ve bunu sınayan test CI'da.
  - (c) 02.11.2026 öncesi saatlik veri görüntüsü dondurulup saklanıyor.
  - (d) 41→36 için iki indirme hisse hisse karşılaştırılıyor; neden bulunamazsa "bilinmiyor" yazılıyor.
  - Kural, eşik ve ileri test ölçütüne dokunulmuyor.
- ✅ v0.99.75 (c30c81f):
  - `core/analytics/provenance.py`.
  - K-63, K-64 ve K-68 veri ve kod satırı ile rapor özetini yazıyor.
  - `--veri` seçeneği eklendi; `hourly.yml` veriyi bir kez indirip donduruyor.
  - Yeni `snapshot.yml`.
  - `test_provenance`: 17 test.
- ✅ v0.99.76 (46c226f): CI kırmızısı düzeltildi. 0c8408a ve c30c81f kırmızıydı:
  - `create_backup` varsayılanı;
  - canlı model testinin gerçek `logs/`'a yazması;
  - koruyucu mesajının cp1252 konsolda çökmesi.
- ✅ `snapshot.yml` çalışması 41880444802 (46c226f) yeşil bitti:
  - A ve B indirmeleri aynı: 62.075 mum, özet `4fc8a1bc…`.
  - K-63 ve K-64 iki kez çalıştırıldı, sonuçlar birebir aynı (K-64: 36 onay).
  - 41→36 farkının nedeni bilinmiyor.
  - Ayrıntı RESEARCH_LOG'da. Hatırlatma silindi.
- ✅ v0.99.77 (eb60894): `scripts\olcum.ps1`, aynı kontrolü PC'de tek komutla yapıyor. Görüntü `BACKUP_DIR\olcum` klasörüne, rapor `logs\olcum_report.txt`'ye yazılıyor. Kullanıcı 04.11'de kotayı korumak için rutin işlerin Python/PowerShell ile yürümesini istedi.
- ⏳ Sıradaki: kullanıcının seçimi. Kalan seçenekler: Faz C (K-64 değerlendirme kodunu değiştiren maddeler ileri testten sonraya) ya da M31/M32 yeniden doğrulaması. Onay gelmeden başlanmaz.
- ✅ **M31/M32 yeniden doğrulaması (v0.99.78):**
  - M31 kullanılamaz, M32 kısıtlı. Raporlar ve geliştirici ekleri `docs/validation/` altında.
  - Ek sorular:
    1. Ayrımda her adım kendi kodunu çalıştırdı: dolaylı olarak kanıtlandı.
    2. 41→36: kod, Python yaması ve rastgelelik dışlandı; fark veride, ama hangi verinin farklı olduğu kayıtlardan ayrılamıyor.
    3. Kayıt: iş akışları artık tamam, sonuç JSON'larına damga v0.99.78'de eklendi.
  - Düzeltilenler: M32 Y1 (saatlik kilit), O2, O3, D6, D7; M31 Y1, O1, O2, O3, D1, D2, D5, D8.
  - Ertelenenler: M31 D3, D4, D6, D7 ve ML etiketlerinde süre kilidi (Faz C ya da 03.02.2027 sonrası).
- ✅ **Faz C, temiz maddeler (v0.99.79–83):**
  - M30 (K-77): blok bootstrap, PIT başlangıç, holdout etiket sonu, getiri ve kuyruk koşulu, kilitli süre dolumu, skor adı.
  - M5 karne; M27 senaryo karnesi; M32-3 saatlik ve günlük aynı kural; M8 seviyeler; M1 skorun çevresi.
  - ⏸ K-64'e dokunanlar 03.02.2027 sonrasına kaldı.
- ✅ M30 yeniden doğrulaması (v0.99.85): kullanılamaz. Canlı ML modeli artık 2022 sonrası ve holdout öncesi veriyle eğitiliyor; blok 20 seans.
- ✅ Yol planı 2. bölüm (v0.99.86–88): `/saglik` (cumartesi 10:00), `/denge`, `/stres` kur şoku, `/takvim`; `/temel` zaten vardı.
- ⚠️ **PC kurulumu kapalı:** v0.99.78'den beri deneme kopyasında 1 test kalıyor; PC v0.99.77'de. Burada yeniden üretilemedi (git'siz kopya: 1303 geçti). Kullanıcıdan `C:\Projeler\QuantBIST_otomasyon\logs\guncelle_*.log` son 25 satırı istendi. v0.99.84'ten sonra güncelleyici başarısız testin adını Telegram'a yazıyor, ama bu ancak bir sürüm kurulunca çalışır.
- ⏳ Sıradaki: yol planı 4. bölüm (haftalık otomatik özet, aylık DR tatbikatı raporu). 3. bölüm (araştırma programı) önceden yazılmış kurallar ister; kullanıcıya önerilecek.
- **Kullanıcı (05.11):** "onay komut almadan devam et, her türlü izni veriyorum". Güvenlik kuralları, holdout ve ileri test sınırları yine geçerli.
- **Genel onay (kullanıcı, 04.11 akşam):** "Benden onay bekleme, her aşamaya onay veriyorum." Sıra şöyle:
  1. M31 ve M32 bağımsız inceleme raporları (başlatıldı 18:14 UTC, yalnız rapor).
  2. Bulguların önem sırasıyla düzeltilmesi; her düzeltme önce kırmızı test, sonra kod.
  3. Faz C'nin temiz maddeleri.
  - K-64 değerlendirme kodunu değiştiren maddeler (M31-2, M31-3, M31-8, M30-3) ve 03.02.2027 ölçütüne dokunan her şey ileri testten sonraya kalır.
  - Güvenlik kuralları, holdout, eşikler ve GEÇMEDİ kararları aynı kalır. Genel onay bunları kapsamaz.
- **Kota kuralı (kullanıcı, 04.11):** Rutin kontroller sohbetle değil, PC'deki betiklerle yapılır. CI ve çalışma izlemeyi gereğinden fazla sorgulama; uzun beklemelerde kendine hatırlatma kur, kısa aralıklarla sorgulama.

## Üç ölçüm (ef12819, 04.11.2026 15:39–15:51 UTC; ayrıntı RESEARCH_LOG)
1. Kart kuralı K-68 (Actions 41859950394): 207 olay, fark %+0,20 (%−0,25 – %+0,62). GEÇMEDİ.
2. Saatlik (41859970212): K-63 575 olay, fark %−0,02 (%−0,64 – %+0,57), GEÇMEDİ. K-64 saatlik 41 onay, %46,3 (%32,8–69,0), taban %24,5, GEÇMEDİ (41 < 50).
3. Günlük ML ve karneler (41859955331): K-59, K-62 KAPALI. K-64 günlük 42 onay, %26,2, GEÇMEDİ. Senaryo karneleri sıfırdan ayırt edilemiyor. Hepsi değişmedi.

## K-64 kural/pencere ayrımı (açıklayıcı ölçüm)
- İş akışı `k64-split.yml`, betik `scripts/k64_split.py`.
- Çalışma 41869771588: ölçüm başlamadan düştü (betik yolu hatası, `core` bulunamadı).
- Çalışma 41871166804: push bitmeden başlatıldı, düzeltilmemiş commit'te koştu; iptal edildi, ölçüm yok.
- **Geçerli çalışma 41871216084, commit 213f71d. Tek yeniden deneme hakkı bununla kullanıldı. Yeniden deneme yok.**
- 213f71d yalnız iş akışındaki bir satırı değiştirdi (`PYTHONPATH=.`); kural kodu ve eşikler aynı.
- Kod kontrolü (yalnız okuma): iki adım `core`'u kendi klasöründen almış görünüyor; çalışma anında kanıtlanmadı. 41→36 farkının nedeni bilinmiyor; açık risk (FAZ_B_KAPANIS).
- Sonuç: Dondurulan veri 30 hisse, 62.870 mum, 05.11.2025 09:30 – 04.11.2026 17:30. Eski kural (d0f4033) ve yeni kural (ef12819) aynı çıktıyı verdi: 570 olay / 380 test, 36 onay, isabet %44,4 (%30,0–70,0), taban %23,4.
- **Doğrulama:**
  - SHA doğrulandı: head_sha 213f71d; worktree HEAD d0f4033 ve ef12819.
  - Aynı veri görüntüsü doğrudan doğrulanamadı: değerlendirme adımları kendi aralık ve satır sayısını yazdırmadı.
  - Kullanıcı kuralı gereği sonuç **geçersiz** kaydedildi ve kullanıcıya bildirildi. Karar ve kurallar etkilenmez.
- 16:55 UTC kontrolünün işi bu çalışmayı okuyup sonucu RESEARCH_LOG'a yazmaktı; bu yapıldı.

## Değişmeyecek kurallar
- K-63, K-64 ve K-68'in kuralları ve eşikleri bu sonuçlara bakılarak değiştirilmez.
- GEÇMEDİ kararları GEÇMEDİ kalır. K-64'ün 50 onay koşulu 41 ya da 36 onayla karşılanmış sayılmaz. Aralığın alt ucunun tabanın üstünde olması bu koşulun yerine geçmez.
- 50 onaya ulaşmak için pencere ya da parametre değiştirilmez; yeniden çalıştırma bu amaçla kullanılmaz.
- 03.02.2027 ileri testi, tarihi ve ölçütü değişmez.
- Üretime kural değişikliği alınmaz.
- Bir ölçüm başarısız olur ya da eksik biterse yalnız bir kez yeniden denenir, sonra neden kullanıcıya bildirilir.

## Hâlâ geçerli diğer talimatlar
- **Onay:** Kullanıcı 04.11'de "benden onay isteme, vermiş gibi düşün" dedi. Commit ve push için ayrıca sorulmaz. Ama aşağıdaki sınırlar değişmez.
- **K-70 güvenilirlik talimatı:**
  - Eksik veri tahminle doldurulmaz.
  - Başarısız model başarılı raporlanmaz.
  - Yeni bir kaynağa otomatik erişim koşullar doğrulanıp kullanıcı onaylamadan açılmaz (robots.txt aşılmaz, birincil kaynağa geri düşülmez).
  - Holdout (02.11.2026 sonrası) kullanılmaz.
  - "Tam güvenilir" etiketi 20 seans gözlem ve 14/14 rapor olmadan konmaz.
- **Kesinlikle yapılmaz:**
  - Gerçek parayla emir, aracı kurum bağlantısı, ödeme.
  - Şifre ya da token girmek veya istemek.
  - Al-sat önerisi.
  - KAP ya da Telegram içeriğini depoya koymak.
  - Git geçmişini yeniden yazmak.
  - Kullanıcının PC'sinde onaysız silme.
- **Kişisel dosyalar depoya girmez:** `.env`, `data/*.db`, ledger, `paper_orders`, `signal_log`, `equity_log`, `data/inbox/` ve diğerleri.
- **Her değişiklikte:** önce kırmızı test, ruff, tam test, kapsam ≥ %91, CHANGELOG / ROADMAP / AUDIT, sürüm (`core/__init__.py` ve `pyproject.toml`), commit trailer. Commit'lere model adı yazılmaz.
- **İletişim:** Türkçe. Kısa raporlar.
- **PC:**
  - `C:\Projeler\QuantBIST-yeni` bir git deposu.
  - Görevler: "QuantBIST Guncelle" (saatte bir, yalnız tamamı yeşil CI), "QuantBIST Gunluk Rapor" (18:30), "QuantBIST Bot".
  - Eski Cowork "otomatik güncelleme" görevi kullanıcı tarafından kapatıldı.
- **CI:** Linux, yavaş makine, Windows ve docker işleri. Windows işi PC'deki hatayı önceden yakalamak için var.
- **Döngü:** Durduruldu (04.11). Kullanıcı sonraki adımı seçene kadar yeni iş başlatılmaz.
