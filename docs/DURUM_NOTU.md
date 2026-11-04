# Durum notu (04.11.2026, kod v0.99.74 / 213f71d)

Bağlam sıkıştırılınca ilk iş bu dosya okunur ve buna göre devam edilir (kullanıcı talimatı, 04.11.2026).

## Faz B (ROADMAP "Eksiksiz iş planı")
- ✅ 1. adım (v0.99.73): `core/market/limits.py`, tek tavan/taban kuralı; %9,5 ve 1e-9 pay; 10 modül bunu kullanıyor; test, modüllerin kendi karşılaştırmasını yasaklıyor.
- ✅ 2. adım (v0.99.74): Kilitli günde dolum yok. Tabanda kilitli gün satış, tavanda kilitli gün alış dolmuyor. Defter, ML etiketleri, senaryolar ve karne.
- ✅ 3. adım: Yeniden ölçümler yapıldı ve RESEARCH_LOG'a eklendi ("04.11.2026 – Faz B yeniden ölçümleri"). Hiçbir karar değişmedi.
- ❌ K-64 kural/pencere ayrımı: geçersiz (aşağıda).
- ⏳ Kalan: Faz B kapanışı. Kullanıcı kuralı: yalnız üç ölçüm kayda geçince ve yedek doğrulanınca kapatılır. Kapanışta tek sayfalık özet yazılır: ne değişti, ne değişmedi, açık riskler, ileri testte bakılacak sayılar.
- Sonra "sonraki adım" önerisi gelir: en fazla 3 seçenek. Her seçenekte yanıtladığı soru, çalıştırmadan önce sabitlenmiş başarı ölçütü, süre ve ileri testi kirletip kirletmediği yazılır. Kullanıcı onaylamadan başlanmaz.

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
- **Döngü:** Otonom döngü `<<autonomous-loop-dynamic>>` ile sürüyor. Sıradaki iş Faz B kapanışı, sonra seçenek önerisi (onay beklenir).
