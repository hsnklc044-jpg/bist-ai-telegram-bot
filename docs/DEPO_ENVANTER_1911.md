# Depo envanteri ve hijyen (18.11.2026 18:55; GECE EKİ 2)

**Yöntem:** salt okunur betik. Her çalışma klasörü için şunlara bakıldı:
- `git worktree list`;
- bot dalının (`origin/claude/borsa-bot-creation-n7nmc9`) atası mı (`merge-base --is-ancestor`);
- `cikti/emekli_uclar.txt`'de var mı;
- `git status --porcelain` temiz mi;
- uzak dal var mı;
- boyutu ne (`.git` hariç).

**Sınıflar:**
- **1:** birleşmiş ya da emekli, temiz ve korunmuyor; kaldırılabilir.
- **2:** onay bekliyor ya da bugün/bu gece açıldı; kalmalı.
- **3:** belirsiz; dokunulmaz.

Kalan dallar `claude/*` olarak uzak depoda durur. **Hiçbir dal silinmedi** (ANAYASA Md. 11).

## A. Envanter (kaldırmadan önce)
﻿| Klasör | Dal | Uç | Son commit | Bot dalına birleşmiş | emekli_uclar | Durum | Uzakta dal | MB | Sınıf | Neden |
|---|---|---|---|---|---|---|---|---|---|---|
| wt-d7f6d4e | (ayrık) | d7f6d4e | 2026-11-12 | evet | hayır | temiz | hayır | 4.0 | 1 |  |
| wt-k88 | claude/k88-yurutme-rotasi | d9df3bf | 2026-11-16 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-k89 | claude/k89-sunucu-o52-o53 | 38e73e2 | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 1 |  |
| wt-k89a | claude/k89-sunucu-belge | e93ee09 | 2026-11-17 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-kur | (ayrık) | 3bcbd28 | 2026-11-11 | evet | hayır | temiz | hayır | 4.0 | 1 |  |
| wt-l | claude/yedek-github-duzeni | 200eb2a | 2026-11-11 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-o47 | claude/o47-ayni-mum-acilis-v143 | dcf1eb6 | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 1 |  |
| wt-o48 | claude/o48-senaryo-sure-kilit-v144 | f59643b | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 1 |  |
| wt-o48v2 | claude/o48-senaryo-sure-kilit-v2 | 850f4f9 | 2026-11-17 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-o49 | claude/o49-risk-toplam-sifir | 06cca4c | 2026-11-16 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-o50 | claude/o50-filtre-onay-sayisi | 0f9b8ed | 2026-11-16 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-o51 | claude/o51-tufe-eksik-ay | 93ebc2d | 2026-11-16 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-o55 | claude/o55-kapi-setup-yolu | a24bc43 | 2026-11-16 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-o56 | claude/o56-rapor-yeniden-deneme | fa8e662 | 2026-11-16 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-o57 | claude/o57-acilis-zaman-asimi | f4031bf | 2026-11-16 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-o61 | claude/o61-ping-retry | 7a94051 | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 1 |  |
| wt-olgunluk | claude/haftalik-slo-dosya | d7f6d4e | 2026-11-12 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-olgunluk-1811 | claude/olgunluk-belge-1811 | cad9bcd | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 1 |  |
| wt-oz11 | claude/oz-denetim-11 | 18b7a49 | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 1 |  |
| wt-paket3 | claude/giden-mesaj | 7186b9e | 2026-11-10 | evet | hayır | temiz | evet | 3.8 | 1 |  |
| wt-restore | claude/resmi-fiyat | 36ba603 | 2026-11-11 | evet | hayır | temiz | evet | 28.5 | 3 | eski kurallarda (otonom_kurallar:91) ve eski görev metninde geliştirme kopyası olarak geçiyor |
| wt-s2 | claude/maturity-s2-alarm | b1ab854 | 2026-11-17 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-t39 | (ayrık) | 07dfe92 | 2026-11-14 | evet | hayır | temiz | hayır | 4.0 | 1 |  |
| wt-telafi | claude/o40-trust-v133 | bc3ba60 | 2026-11-14 | evet | hayır | temiz | evet | 4.0 | 1 |  |
| wt-yetki | claude/robot-yetki-belge | 64de0a1 | 2026-11-17 | evet | hayır | temiz | evet | 4.1 | 1 |  |
| wt-147 | claude/o63-o64-v2 | f8d0ef0 | 2026-11-18 | hayır | evet | temiz | evet | 4.2 | 2 | bugün/bu gece |
| wt-1a2 | claude/o61-ping-retry-v2 | 3805752 | 2026-11-18 | hayır | hayır | temiz | evet | 4.1 | 2 | bugün/bu gece |
| wt-1d2 | claude/s4-s5-hazirlik-v2 | bfa3916 | 2026-11-18 | hayır | hayır | temiz | evet | 4.2 | 2 | bugün/bu gece |
| wt-gece | claude/gece-belge-1811 | 0af56f3 | 2026-11-18 | evet | hayır | temiz | evet | 4.1 | 2 | bugün/bu gece |
| wt-gunduz | claude/gunduz-1811 | 0b380ba | 2026-11-18 | hayır | evet | temiz | evet | 4.2 | 2 | bugün/bu gece |
| wt-k96 | claude/k96-s3-oturum-acma | b2817f2 | 2026-11-18 | hayır | evet | temiz | evet | 4.1 | 2 | bugün/bu gece |
| wt-o47v2 | claude/o47-ayni-mum-acilis-v2 | 07bd70a | 2026-11-17 | hayır | evet | temiz | evet | 4.1 | 2 | hafta sonu tek başına birleştirme (K-88) |
| wt-o52 | claude/o52-store-belge | d34dc92 | 2026-11-17 | hayır | hayır | temiz | evet | 4.1 | 2 | hafta sonu tek başına birleştirme (K-88) |
| wt-o63 | claude/o63-o64 | ea0f7af | 2026-11-18 | hayır | evet | temiz | evet | 4.2 | 2 | bugün/bu gece |
| wt-o67 | claude/o66-o67-test-belge | 028742b | 2026-11-18 | hayır | evet | temiz | evet | 4.1 | 2 | bugün/bu gece |
| wt-o67v2 | claude/o66-o67-test-belge-v2 | 5642e42 | 2026-11-18 | hayır | evet | temiz | evet | 4.2 | 2 | bugün/bu gece |
| wt-s3risk | claude/s3-mudahale-riskleri | a618afc | 2026-11-18 | hayır | evet | temiz | evet | 4.1 | 2 | bugün/bu gece |
| wt-s4s5 | claude/s4-s5-hazirlik | a9ae94b | 2026-11-18 | hayır | evet | temiz | evet | 4.1 | 2 | bugün/bu gece |
| wt-slo-yedek | claude/haftalik-slo-yedek | 953ea73 | 2026-11-12 | hayır | hayır | temiz | evet | 4.0 | 2 | hafta sonu tek başına birleştirme (K-88) |
| wt-zincir1911 | claude/faz-a2-1911 | cb68afa | 2026-11-18 | hayır | hayır | temiz | evet | 4.4 | 2 | bugün/bu gece |
| wt-o39 | claude/resmi-icerik-durum | 7491f2d | 2026-11-12 | hayır | hayır | temiz | evet | 4.0 | 3 | ne birleşmiş ne emekli |
| wt-o40 | claude/trust-hata-log | f93b0c3 | 2026-11-12 | hayır | hayır | temiz | evet | 4.0 | 3 | ne birleşmiş ne emekli |
| wt-oz10 | claude/oz-denetim-10 | 64d1d82 | 2026-11-12 | hayır | hayır | temiz | evet | 4.0 | 3 | ne birleşmiş ne emekli |
| wt-oz10b | claude/oz-denetim-10-guncel | 1335806 | 2026-11-15 | hayır | hayır | temiz | evet | 4.0 | 3 | ne birleşmiş ne emekli |
| wt-yedek134 | claude/oz-denetim-10-v3 | 428e5a5 | 2026-11-14 | hayır | hayır | temiz | evet | 4.0 | 3 | ne birleşmiş ne emekli |
| wt-zincir | (ayrık) | 8a51f34 | 2026-11-12 | hayır | hayır | temiz | hayır | 4.2 | 3 | ne birleşmiş ne emekli |
| wt-zincir132 | claude/oz-denetim-10-v2 | 9afac8f | 2026-11-12 | hayır | hayır | temiz | evet | 4.0 | 3 | ne birleşmiş ne emekli |

Sayılar: 1. sınıf 24, 2. sınıf 15, 3. sınıf 8. `wt-restore` önce 1. sınıfa girmişti; bir göreve bağlı olduğu görülünce 3. sınıfa alındı.

Canlı klasör (`QuantBIST-yeni`, b1ab854) ve geçici klasördeki `wt-k2` (başka bir oturumun) envantere dahil edilmedi ve dokunulmadı.

## B. Uygulama
- Her klasörde kaldırmadan hemen önce `git status` yeniden denetlendi; hepsi temizdi.
- Kaldırma `git worktree remove` ile, zorlama (`--force`) olmadan yapıldı. Kaldırılan 24 klasör: wt-d7f6d4e, wt-k88, wt-k89, wt-k89a, wt-kur, wt-l, wt-o47, wt-o48, wt-o48v2, wt-o49, wt-o50, wt-o51, wt-o55, wt-o56, wt-o57, wt-o61, wt-olgunluk, wt-olgunluk-1811, wt-oz11, wt-paket3, wt-s2, wt-t39, wt-telafi, wt-yetki.
- **Disk:** boş alan 155.686 MB'tan 155.801 MB'a çıktı (+115 MB).
- **Doğrulama:** kaldırılan klasörlerin dalları yerel ve uzakta aynı uçla duruyor. Örnekler: `claude/k88-yurutme-rotasi` d9df3bf, `claude/o61-ping-retry` 7a94051, `claude/oz-denetim-11` 18b7a49, `claude/robot-yetki-belge` 64de0a1.
- Çalışma klasörü sayısı 49'dan 25'e indi (canlı ve geçici klasördeki dahil).
- 2. ve 3. sınıflara dokunulmadı.

## C. Büyüyen dosyalar ve disk (yalnız okuma ve öneri)
| Dosya / klasör | Boyut (18.11) | Büyüme | Not |
|---|---|---|---|
| `logs/quantbist.log` (+ `.1`) | 2,9 MB + 5,0 MB | 10.11'den beri 2,9 MB, yani ~0,36 MB/gün | döndürme var (`.1` 5 MB'ta açıldı); toplam sınırlı |
| `logs/levels_log.csv` | 1,2 MB | ölçülmedi (ilk kayıt tarihi bakılmadı) | döndürmesiz CSV; ~yılda birkaç MB |
| `logs/heartbeats.csv` | 135 KB | 5 dakikada bir satır, ~9 KB/gün | yılda ~3 MB; SLO kanıtı olduğu için döndürülmemeli |
| `logs/` toplam | 10 MB | — | — |
| `cikti/` | 14 MB | — | PDF'ler 6,7 MB |
| `QuantBIST_otomasyon/logs` (güncelleyici) | 1 MB, 281 dosya | günde ~16 dosya | yılda ~6.000 dosya, ~6 MB |
| `data/` | 3 GB | ölçülmedi | fiyat geçmişi |
| C: boş alan | 155,8 GB | — | — |

**Disk ne zaman dolar?** Bugünkü hızlarla (`logs/` + güncelleyici kayıtları yılda ~20 MB, `data/` büyümesi bilinmiyor) on yıllar içinde dolmaz. Asıl belirsizlik `data/`'nın büyüme hızı. Öneri: KT-09 çeyrek taramasına `data/` boyutu eklensin.

**Döndürme önerileri** (uygulanmadı; canlı log ayarı sahibin kararı):
1. Güncelleyici kayıtları (`guncelle_*.log`) için aylık klasör ya da 90 günden eski olanların zip arşivi. Silme değil, arşiv. Dosya sayısı yılda ~6.000'e çıkar; boyut sorun değil.
2. `levels_log.csv` için yıllık bölme (`levels_log_2026.csv`). Kişisel kayıt değilse. Önce kaydın ne olduğu belirlenmeli.
3. `heartbeats.csv` ve `runs.csv` döndürülmesin; S2 kanıtıdır.
