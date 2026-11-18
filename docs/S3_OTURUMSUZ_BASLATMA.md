# S3 kalıcı çözüm taslağı: yeniden başlamadan sonra bot oturum açılmadan dönsün (18.11.2026)

**Durum: taslak, uygulanmadı.** Zamanlanmış görev ve canlı sistem ayarı kullanıcının kararıdır (Kullanıcı çerçevesi). Bu belge seçenekleri, kanıtları ve önerilen deneme adımını yazar.

## Sorun
"QuantBIST Bot" görevi yalnız oturum açılınca başlar. 18.11'de salt okunur denetimde görülen ayarlar:
- tetikleyici `MSFT_TaskLogonTrigger`;
- `Principal.LogonType` = Interactive, `RunLevel` = Limited, kullanıcı `hsnkl` (yerel hesap, Administrators üyesi);
- eylem `C:\Projeler\QuantBIST-yeni\.venv\Scripts\pythonw.exe main.py`, çalışma klasörü canlı klasör.

12.11'de Windows Update yeniden başlattı ve bot 109 dk kapalı kaldı. K-96'ya göre oturum açmak müdahaledir ve S3 sayacını sıfırlar.

## Kaynaklar (resmî, 18.11'de okundu)
- **Principal.LogonType** (learn.microsoft.com/en-us/windows/win32/taskschd/principal-logontype):
  - S4U'da "no password is stored by the system";
  - ayrıca "no access to either the network or encrypted files".
- **Log on as a batch job** (learn.microsoft.com, Windows 10/11 güvenlik ilkesi):
  - istemcide varsayılan hak Administrators grubundadır;
  - "Task Scheduler automatically grants this right when a user schedules a task".
- **New-ScheduledTaskPrincipal** (learn.microsoft.com, ScheduledTasks modülü): `-LogonType` parametresi S4U değerini alır. Asıl açıklaması: "Task Scheduler can run the task regardless of whether that account is logged on".

## Seçenekler
| # | Yol | Şifre saklanır mı | Program kurulur mu | Belirsizlik / risk |
|---|---|---|---|---|
| A | Aynı görev S4U ile ("kullanıcı oturum açmış olsun olmasın çalıştır" + "parolayı saklama"); tetikleyici "başlangıçta" | Hayır | Hayır | Belge S4U için "ağa erişim yok" diyor. Telegram, Yahoo ve GitHub HTTPS gerektirir, bu yüzden **önce denenmeli**. Şifreli dosya yok. OneDrive yedek klasörüne yazılır, ama eşitleme oturum açılınca başlar. |
| B | Görev SYSTEM hesabıyla, başlangıçta | Hayır | Hayır | Ağ var. Bot gereğinden yüksek yetkiyle çalışır. Oluşturduğu dosyaların sahibi SYSTEM olur, `logs/` ve `data/` izinleri karışabilir. `.env` ve kullanıcı ortam değişkenleri farklı okunabilir. Önerilmez. |
| C | Otomatik oturum açma (Autologon vb.) | Evet (LSA'da) | Evet (Sysinternals) | Kullanıcı sınırı: şifre kaydedilmez, program kurulmaz. **Elendi.** |
| D | Yalnız önlem: Windows Update'i 12.12'ye kadar duraklatmak, etkin saatler | — | Hayır | Kalıcı çözüm değil. Elektrik kesintisinden sonraki açılışta da oturum gerekir. 18.11'de Telegram'dan hatırlatıldı. |

## Öneri: A, önce zararsız bir denemeyle
1. **Deneme görevi (kullanıcı açar, bot görevine dokunulmaz).**
   - Ayrı bir görev açılır: "QuantBIST S4U deneme", S4U, tek seferlik, tetikleyici "başlangıçta".
   - Görev şu satırla `https://api.github.com` adresine HTTPS isteği atar ve sonucu `C:\Projeler\QuantBIST-araclar\cikti\s4u_deneme.txt` dosyasına yazar:
     `pythonw.exe -c "import urllib.request,datetime;open(r'...\s4u_deneme.txt','a').write(f'{datetime.datetime.now():%d.%m %H:%M} '+str(urllib.request.urlopen('https://api.github.com',timeout=20).status)+'\n')"`
   - Token kullanılmaz.
2. **Sonuç.**
   - Bir sonraki yeniden başlatmadan sonra, oturum açmadan önce dosyada `200` satırı varsa S4U ağa çıkabiliyor demektir.
   - Hata varsa A elenir. Kalan yollar B ya da D'dir, ve kullanıcının kararıdır.
3. **Yalnız deneme geçerse.**
   - "QuantBIST Bot" görevinin oturum türü S4U, tetikleyicisi "başlangıçta" olur. Yeniden deneme ayarları aynı kalır: `RestartCount 3`, `PT5M`.
   - İki bot birden çalışmamalı. Oturum açma tetikleyicisi kaldırılır; kalırsa da Telegram ikinci botu reddeder (OPERATIONS §8).
   - Bu bir kurulum betiği değişikliğidir (`scripts/register_bot_task.ps1`, ALONE). Hafta sonu kullanıcı komutuyla yapılır (K-88).
4. **Ölçüm.**
   - Sonraki ilk yeniden başlatmada `logs/quantbist.log`'da "Telegram bot started" satırının saati oturum açma saatinden önce olmalı. Oturum açma saati Güvenlik günlüğünde, olay 4624, tür 2.
   - Böyle olursa yeniden başlama artık müdahale sayılmaz (K-96'nın tanımı değişmez, yalnız olgu değişir).

## Açık kalanlar
- "Ağa erişim yok" ifadesinin giden HTTPS'i de kapsayıp kapsamadığı belgede net değil. Bunu deneme gösterir.
- Görev Windows Home'da S4U ile kaydedilebiliyor mu? Belgeye göre hak, görev kaydedilince kendiliğinden verilir. Bunu da deneme gösterir.
- OneDrive eşitlemesi oturum açılana kadar bekler. Yedek yerelde yazılır, ama S1 yedek tazeliği OneDrive kopyasına bakıyorsa gecikme görünür. Ölçülecek.
