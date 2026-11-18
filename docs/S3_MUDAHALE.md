# S3 30 gün sayacı: müdahale tanımı, riskler ve önlemler (18.11.2026)

**Tanım (K-93 (6), değiştirilmez).** Müdahale, sistemin çalışmayı sürdürmesi için kullanıcının elle yaptığı onarım, kurulum, dosya düzenleme ya da yeniden başlatmadır.

Müdahale sayılmayanlar:
- kuralların kullanıcıya bıraktığı onaylar (K-88 §5, hafta sonu birleştirmeleri, 18.11 paket onayları gibi);
- tatbikatlar (`--drill`);
- elektrik ve ağ kesintileri (bunlar SLO'ya yazılır).

**Sayaç** 04.11.2026'da başladı ve **03.12.2026**'da dolar; 27.11 hesabı geçersizdir. Ölçüm 03.12 olgunluk ölçümünde yapılır. Kanıt, OTONOM_RAPOR ve ROBOT_LOG'daki "elle" kayıtlarıdır.

## Sayacı bozabilecek riskler

Durum sütunu 18.11.2026 11:40 itibarıyla salt okunur denetimle dolduruldu.

| # | Risk | Neden müdahale doğurur | Bugünkü durum (kanıt) | Önlem | Kalan iş, tarih |
|---|---|---|---|---|---|
| R1 | Windows güncellemesiyle yeniden başlama | "QuantBIST Bot" görevi yalnız **oturum açılınca** başlar (tetikleyici `MSFT_TaskLogonTrigger`). Oturum açılmazsa bot da başlamaz. | Bekleyen yeniden başlatma yok (`RebootRequired` = False). | Kullanıcı yeniden başlatmadan sonra oturum açar; bu elektrik kesintisi gibi sayılır, ama kesinti süresi SLO'ya yazılır. | Kullanıcıya kalır: otomatik oturum açma ya da "oturum açılmadan çalıştır" seçeneği hesap ve şifre gerektirir (K-54). Robot yalnız uyarır. |
| R2 | Bot art arda çöker | Görev 5 dk arayla **en fazla 3 kez** yeniden başlar (`RestartCount 3`, `RestartInterval PT5M`); sonra durur ve elle başlatma gerekir. | 17.11 22:45'ten beri 0 ERROR (`logs/quantbist.log`). | Ö57 (v0.99.140): açılışta Telegram zaman aşımı botu kapatmaz. 1a' (ping yeniden deneme) bu akşam. | Yeniden başlatma sayısını artırmak güncelleyici/kurulum betiği değişikliğidir (ALONE, `scripts/setup.ps1`). Gerekirse hafta sonu kullanıcı komutuyla yapılır. |
| R3 | Pilde kurulum düşer | Kurulum "KURULMADI" der ve eski sürümde kalır. Müdahale gerekmez, ama kurulum gecikir. | 17.11 20:40 ve 21:40'ta pildeyken iki kurulum düştü (Kernel-Power 105, 18:49–22:04). | Hız testi makinenin ölçülen hızına bağlandı (`claude/gunduz-1811` 8ae5165, D.1b). Akşamları bilgisayar şarjda tutulur. | 8ae5165 kapıya girince kapanır (18–19.11). |
| R4 | Uyku | Uykudaki bilgisayarda bot çalışmaz. | Uyku prizde ve pilde kapalı (`powercfg STANDBYIDLE` AC 0, DC 0). | Kullanıcı kararı K-89: bilgisayar 7/24 açık. | Yok. |
| R5 | Disk dolar | Günlük ya da veritabanı yazılamaz. | C: 152,3 GB boş, `logs/` 9,2 MB. | `/durum` disk denetimi. | Yok (yıllarca yeter). |
| R6 | GitHub API sınırı (Ö54) | Güncelleyici kimliksiz sorgu yapar (saatte 60). Paylaşılan IP'de sınır dolarsa kurulum gecikir. | Açık, ORTA (ROADMAP Ö54). | Gecikme müdahale değildir; güncelleyici sonraki saat yeniden dener. | Token gerektirir: kullanıcıya kalır (K-54). |
| R7 | Fren bayrağı | Bayrağı yalnız kullanıcı kaldırır, bu bir müdahaledir. | Bayrak yok (17.11 22:31 gece robotu). | Robot bayrağı yalnız gerçek arızada koyar. | Bayrak konursa sayaç sıfırlanır ve nedeni DECISIONS'a yazılır. |
| R8 | Süresi dolan şeyler (tatil takvimi, endeks listesi, Python ve paket sürümleri) | Elle güncelleme gerekir. | ✅ önceden uyarı var (`test_health_ops.MaintenanceCalendarTest`, `QuarterlyReviewDateTest`; MATURITY S3 satır 2). Telegram bot token'ının süresi dolmaz. | Uyarı 30 gün önceden gelir. | Yok. |
| R9 | OneDrive yedek klasörü dolar ya da eşitleme durur | Yedek yazılamaz, S1 yedek satırı bozulur. | 17.11 20:40 yedeği yazıldı (`Backup written`, `logs/quantbist.log`). | `/durum` yedek tazeliği SLO'su. | Yok. |
| R10 | Elle düzeltme isteği | Kullanıcı canlı klasöre elle bir şey yazarsa bu müdahaledir. | 03.11'den beri yok. | CLAUDE.md: canlıya elle yazılmaz; her şey `surum-kapisi`'nden geçer. | Yok. |

## Ölçüm

03.12.2026 olgunluk ölçümünde bakılacaklar:
- OTONOM_RAPOR, ROBOT_LOG ve DECISIONS'ta 04.11–03.12 arasında "elle" geçen kayıtlar;
- `logs/quantbist.log`'da beklenmeyen "Telegram bot started" satırları (planlı kurulum dışında yeniden başlama).

Müdahale bulunursa sayaç o günden yeniden başlar; tarih ve neden DECISIONS'a yazılır. Ölçütler sonradan gevşetilmez.
