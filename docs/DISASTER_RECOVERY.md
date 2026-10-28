# Felaket kurtarma

CHARTER E. Her komut `tests/test_disaster_recovery.py` tarafından denetlenir: anılan her betik ve Python modülü depoda vardır, boş bir bilgisayara geri yükleme testte baştan sona çalışır.

## 1. PC tamamen bozuldu: sıfır Windows makinede kurulum

Gerekenler: yedek klasörü (OneDrive'daki `QuantBIST-yedek`), Telegram bot token'ı ve chat id (şifre yöneticin ya da BotFather), varsa Healthchecks adresleri. Kişisel kayıtlar yalnız yedekte vardır; GitHub'da yoktur.

1. **Python 3.11** kur (python.org, "Add to PATH" işaretli). Başka sürüm kullanma; paketler 3.11 ile kilitli.
2. **Kodu indir ve aç** (PowerShell):
   ```powershell
   Invoke-WebRequest "https://github.com/hsnklc044-jpg/bist-ai-telegram-bot/archive/refs/heads/claude/borsa-bot-creation-n7nmc9.zip" -OutFile "$env:TEMP\qb.zip"
   Expand-Archive "$env:TEMP\qb.zip" C:\Projeler -Force
   Rename-Item (Get-ChildItem C:\Projeler -Directory -Filter "bist-ai-telegram-bot-*")[0].FullName QuantBIST
   cd C:\Projeler\QuantBIST
   ```
3. **Kurulum**: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`. Sanal ortamı kurar, paketleri kilit dosyasından yükler, ruff ve testleri çalıştırır. Beklenen: `tests: OK`.
4. **.env** dosyasını oluştur (kullanıcının adımı; token kimseyle paylaşılmaz):
   ```
   BOT_TOKEN=...
   CHAT_ID=...
   BACKUP_DIR=C:\Users\<kullanıcı>\OneDrive\QuantBIST-yedek
   HC_REPORT_URL=...   (isteğe bağlı)
   HC_BOT_URL=...      (isteğe bağlı)
   ```
5. **Kişisel kayıtları geri yükle**: önce listele, sonra en yeni günlük yedeği yükle:
   ```powershell
   .venv\Scripts\python -m core.backup --list
   .venv\Scripts\python -m core.backup --restore <en yeni quantbist_YYYY-AA-GG.zip>
   ```
   Beklenen: defter, sanal emirler, takip listesi ve kayıtlar `data\` altına açılır.
6. **Fiyat deposu**: yedekteki en yeni `quantbist_marketdb_*.zip` içindeki `market.db`'yi `data\` içine kopyala ya da baştan indir: `.venv\Scripts\python -m core.market.update`. İkincisi daha yavaştır ama aynı sonucu verir.
7. **Zamanlanmış görevler**:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1
   powershell -ExecutionPolicy Bypass -File scripts\register_bot_task.ps1
   Start-ScheduledTask "QuantBIST Bot"
   ```
8. **Doğrula**: `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`. Ardından Telegram'da `/durum`; beklenen "Kişisel dosyalar" SAĞLIKLI ve sürüm doğru.
9. **Güncelleme görevini** yeniden kur. Güncelleyici depoda (`scripts\guncelle.py`, `scripts\bildir.py`); kilit ve log klasörü `C:\Projeler\QuantBIST_otomasyon` kendiliğinden oluşur. Komut [OPERATIONS](OPERATIONS.md) §5'te.

Beklenen en fazla kayıp: son yedekten sonraki komutlar. Yedek her gün rapordan sonra alınır, yani kayıp en fazla 1 gündür.

## 2. Aylık geri yükleme tatbikatı

Yerel otomasyon ayda bir çalıştırır; canlı dosyalara dokunmaz:
```powershell
.venv\Scripts\python -m core.backup --test-restore
```
Beklenen: her dosya için "okundu" satırı. Rapor da haftada bir aynı testi yapar; sonuç `/durum`'daki "Yedek" hedefinde görünür.

## 3. Token sızdı (ya da sızdığından şüpheleniliyor)

1. Telegram'da **@BotFather** → `/revoke` → botu seç. Eski token anında geçersiz olur.
2. Yeni token'ı `.env`'deki `BOT_TOKEN` satırına yaz (kullanıcının adımı).
3. Botu yeniden başlat: `Start-ScheduledTask "QuantBIST Bot"` (önce `Stop-ScheduledTask "QuantBIST Bot"`).
4. `/durum` ile doğrula. Log'da "Conflict" görürsen başka bir yerde eski kod hâlâ çalışıyor demektir; token yenilendiği için o kopya artık bağlanamaz.
5. Token bir dosyayla dışarı çıktıysa (ekran görüntüsü, e-posta, depo): o dosyayı kaldır. Depo herkese açık; `.env` hiçbir zaman commit edilmez ve CI bunu denetler.

**Healthchecks adresi sızdıysa:** Healthchecks'te ilgili kontrolün "Ping URL" adresini yenile, `.env`'deki satırı güncelle, botu yeniden başlat. Eski adres yalnız sahte "çalışıyorum" sinyali göndermeye yarar; veriye erişim vermez.

## 4. Kimin işi

| Adım | Kim |
|---|---|
| Python, kod, kurulum, görevler, doğrulama | Kullanıcı (ya da yerel otomasyon, kuruluysa) |
| .env, token, BotFather, Healthchecks | Kullanıcı |
| Yedeklerin varlığı ve haftalık geri yükleme testi | Sistem (rapor) |
| Aylık tatbikat | Yerel otomasyon |
