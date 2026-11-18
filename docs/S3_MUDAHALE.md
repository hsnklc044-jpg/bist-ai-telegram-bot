# S3 "müdahale" ve 30 gün sayacını bozabilecek riskler (18.11.2026)

Bu belge yeni bir ölçüt ya da eşik koymaz. Tanım K-93 (6)'dır; oturum açma yorumu K-96'dır (18.11). Belge yalnız sayacı **12.12.2026**'ya kadar bozabilecek olayları, bugünkü korumayı ve önlemleri listeler. Kanıtlar 18.11 11:40'ta salt okunur olarak toplandı.

## Tanım (K-93 (6), özet)
- **Müdahale:** çalışan sistemin sürmesi için kullanıcının elle yaptığı onarım, kurulum, dosya düzenleme ya da yeniden başlatma.
- **Müdahale sayılmaz:** kuralların kullanıcıya bıraktığı onaylar (K-88 §5), tatbikatlar (`--drill`), elektrik ya da ağ kesintisi. Bu kesintiler SLO'ya yazılır.
- **Windows yeniden başlatmasından sonra oturum açmak müdahaledir (K-96).**
- **Sayaç:** 13.11'de başladı, en erken **12.12.2026**'da dolar. K-93 (6)'daki 03.12 geçersizdir. Ölçüm 12.12 olgunluk ölçümünde, aşağıdaki §Ölçüm'e göre yapılır.

## Riskler

| # | Risk | Kanıt | Bugünkü koruma | Açık | Önlem (kimin) |
|---|---|---|---|---|---|
| 1 | **Windows Update yeniden başlatması** | Etkin saatler 10:00–03:00, yani yeniden başlatma 03:00–10:00 arasında olabilir. Olay günlüğü 1074: 20.10 05:45 ve 12.11 05:46 planlı yeniden başlatma. `logs/heartbeats.csv` 12.11'de 05:39–07:28 arası boş (109 dk) | Bot görevi "QuantBIST Bot" **oturum açılışında** başlar (`MSFT_TaskLogonTrigger`, `Interactive`). 18:30 raporu `StartWhenAvailable` ile kaçanı telafi eder | Yeniden başlatmadan sonra bot, biri oturum açana kadar kapalı kalır. 12.11'de bot 07:28'de döndü: bu bir oturum açılışıdır. K-96'ya göre bu bir müdahaledir: sayaç 13.11'de yeniden başladı. Aynı olay yeniden olursa sayaç yine sıfırlanır | Kalıcı önlem görevin oturum açılmadan çalışmasıdır; Windows şifresi gerektirir, kullanıcıya kalır (K-54). İsteğe bağlı: Ayarlar → Windows Update → "Güncellemeleri duraklat" ile 12.12'ye kadar duraklatmak (sistem ayarı; Claude yapmaz) |
| 2 | **Planlı sürüm güncellemesi (07:40 ve kapı kurulumları)** | 17.11 20:40 ve 21:40 kurulumları pilde hız testinden düştü; canlı sürüm değişmeden kaldı | Yedek → deneme kopyasında ruff ve test → kurulum → bot açılmazsa eski sürüme dönüş (OPERATIONS §5). Aynı gün 2 geri dönüş otomatik fren koyar | Fren kalkmadan kurulum olmaz. Freni kullanıcı kaldırır, ama bu kuralın bıraktığı bir onaydır, onarım değildir. Elle `robocopy` ile geri dönüş ise müdahaledir | Kapının 8. satırı (pil, `claude/gunduz-1811`) pilde birleştirmeyi durdurur. Kurulumlar robot saatlerinde, tek paket |
| 3 | **Disk** | C: 152,3 GB boş | `health.disk_check`: 1 GB altında uyarı, 200 MB altında kritik (`core/reports/health.py:69`). Disk doluysa rapor yine gider (`test_corrupt_files…test_full_disk`) | Yok denecek kadar küçük; günlük büyüme MB düzeyinde | Gerekmez |
| 4 | **Telegram erişimi** | — | Açılışta internet yoksa ~7 dk boyunca 20 deneme (`bot/application.py:134`). Görev çökerse 5 dk arayla 3 kez yeniden başlatır (`RestartCount 3 / PT5M`). Rapor gönderimi 3 deneme yapar | Açılışta kesinti ~25 dakikayı aşarsa bot kapalı kalır. Ardından `Start-ScheduledTask "QuantBIST Bot"` gerekir: bu elle yeniden başlatmadır, yani müdahale | Bekçi yok. Gerekirse ayrı dalda bir izleme görevi eklenebilir. Bu bir zamanlanmış görev değişikliğidir, kullanıcı onayı gerekir |
| 5 | **GitHub erişimi** | Kapı ve güncelleyici CI sonucunu GitHub API'den okur (`_ci`). Token yok, saatte 60 istek sınırı var | Erişim yoksa kurulum olmaz, canlı sürüm olduğu gibi çalışır | Botu durdurmaz, müdahale gerektirmez. Yalnız sürüm gecikir | Gerekmez |
| 6 | **Pil ve güç** | Uyku AC ve DC'de "hiç" (`powercfg STANDBYIDLE` 0). Bot görevi pilde durmaz. 04.11 21:48–05.11 07:58 kalp atışı boşluğu var (610 dk) | Elektrik kesintisi tanım gereği müdahale değildir, SLO'ya yazılır. Kapının 8. satırı pilde kurulumu erteler | Kesintiden sonra bilgisayarı açmak ve oturum açmak 1. satırla aynı sorudur | 1. satırdaki karar burayı da kapsar |
| 7 | **Elle dosya düzenleme** | 03.11'de canlı kurulum elle taşındı; sayaç bu yüzden 04.11'de başladı | CLAUDE.md: canlı klasöre elle dosya yazılmaz, her şey `surum-kapisi`'nden geçer. Canlı klasörde beklenmeyen değişiklik otomatik fren koyar | `.env` düzenlemesi, Excel'de defter düzeltmesi ya da yarım satır silme (OPERATIONS §8) birer müdahaledir | 12.12'ye kadar `.env` ve canlı dosyalar değişmez (gündüz kuralı ile aynı) |

## Karar K-96 (18.11.2026): oturum açmak müdahaledir
- Kullanıcı kararı Claude'a bıraktı. Koordinatör oturumu K-96'yı yazdı (`claude/k96-s3-oturum-acma` b2817f2).
- Gerekçe: 12.11'de bot, kullanıcının elle yaptığı bir işlemle geri geldi. Elektrik ya da ağ kesintisinde sistem kendi kendine döner, burada dönmedi. Tanımı lehe yorumlamak ölçütü sonradan gevşetmek olurdu.
- Bu belgedeki önceki öneri (a, "sayılmaz") geçersizdir.
- Reddedilen yollar: görevi "oturum açılmasa da çalıştır" yapmak ya da otomatik oturum açma. İkisi de Windows şifresini gerektirir; şifre kesin sınırdır. Kalıcı önlem bu yüzden kullanıcıya kalır.

## Ölçüm (12.12.2026 olgunluk ölçümünde; yeni eşik yok)
1. `cikti\OTONOM_RAPOR.md` ve `docs/ROBOT_LOG.md`'de 13.11–12.12 arasındaki "elle" kayıtlarına bakılır (K-93 (6)).
2. `logs/heartbeats.csv`'deki her kalp atışı boşluğu Sistem olay günlüğüyle (1074 yeniden başlatma) eşleştirilir. Boşluk bir Windows yeniden başlatmasıyla başlayıp oturum açılışıyla bitiyorsa müdahaledir (K-96). Elektrik ya da ağ kesintisi müdahale değildir, SLO'ya yazılır.
3. Hiç müdahale yoksa S3'ün 30 gün satırı ✅ olur. Varsa sayaç, son müdahalenin ertesi günü yeniden başlar.
