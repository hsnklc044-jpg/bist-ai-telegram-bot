---
name: olgunluk
description: QuantBIST olgunluk durumunu (docs/MATURITY.md S1–S5) güncel kanıtlarla karşılaştırıp her seviyenin yüzdesini ve resmî seviyeyi yazar. Salt okunur; belgeyi yalnız açıkça istenirse günceller.
---

# Olgunluk

1. `docs/MATURITY.md`'deki her seviyenin "çıkış kanıtı" satırlarını oku.
2. Her satırı güncel veriyle denetle (salt okunur): `core.reports.slo.measure`, `logs/heartbeats.csv`,
   `logs/runs.csv`, yedek klasörü, CI sonucu (az istekle), ROADMAP, RESEARCH_LOG, DECISIONS.
3. Puan: kanıtı tam olan satır 1, kısmi kanıt 0,5, yok 0. Seviye yüzdesi = puan / satır sayısı.
4. Resmî seviye: bütün çıkış kanıtları tam olan en yüksek ardışık seviye.
5. Çıktı: seviye başına "S2 GÜVENİLİR: %62 (5 satırın 2,5'i)", her satır için tek cümle kanıt ve tarihi; resmî
   seviye. Belgeyle çelişen kanıt varsa ayrıca yaz.
6. `docs/MATURITY.md` yalnız kullanıcı isterse, dal üzerinden güncellenir.
