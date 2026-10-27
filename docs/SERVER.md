# Sunucuya taşıma

Amaç: bilgisayar kapalıyken de botun ve 18:30 raporunun çalışması. Her şey Docker ile çalışır.
Aynı kurulum, Docker dosyaları her değiştiğinde (ve elle başlatılınca) GitHub'da temiz bir Linux makinede baştan sona denenir
(`.github/workflows/server-smoke.yml`).

**Ne zaman?** Karar ölçütü veriden önce yazıldı (DECISIONS K-23): 02.11–13.11 SLO'larında bot < %98 ya da rapor < %99 PC yüzündense, ya da haftada ≥ 1 PC kaynaklı bot alarmı varsa sunucu önerilir; karar 14.11. Ücretsiz seçenek: PC'yi 7/24 açık ve uykusuz tutmak.

**Dur noktası:** sunucu kiralamak ödeme gerektirir. Bu adımı kullanıcı yapar; aşağıdaki
adımlar sunucu hazır olduktan sonrası içindir.

## 0. Gerekenler

- Linux sunucu: Ubuntu 24.04, 1 CPU, 1–2 GB RAM, 20 GB disk yeterli. Fiyat veritabanı yaklaşık 100 MB.
- SSH ile bağlanabilen, sudo yetkili bir kullanıcı. İlk kullanıcı genellikle uid 1000'dir; bu, konteynerle aynıdır.
- Telegram bot token'ı ve chat id. Bunlar yalnız sunucudaki `.env` dosyasına yazılır, hiçbir yere gönderilmez.

## 1. Docker'ı kur (sunucuda)

```
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER      # sonra çıkıp yeniden bağlanın
docker compose version
```

## 2. Kodu al

```
git clone -b claude/borsa-bot-creation-n7nmc9 https://github.com/hsnklc044-jpg/bist-ai-telegram-bot.git ~/QuantBIST
cd ~/QuantBIST
```

## 3. Ayarlar (`.env`)

```
cp .env.example .env
nano .env
```

| Ayar | Sunucuda |
|---|---|
| `BOT_TOKEN`, `CHAT_ID` | PC'dekiyle aynı |
| `DAILY_REPORT_AT` | `18:30` (raporu bot kendisi gönderir; yeniden başlarsa kaçırdığını telafi eder) |
| `BACKUP_DIR` | `/app/backups` (sunucudaki `~/QuantBIST/backups` klasörü) |
| `HC_REPORT_URL`, `HC_BOT_URL` | İsteğe bağlı: dışarıdan izleme (OPERATIONS.md §7) |

`chmod 600 .env` ile dosyayı yalnız kendinize açın.

## 4. Kişisel dosyaları PC'den taşı

**Önce PC'de** botu durdurun ve Windows görevini kapatın. Aksi hâlde iki makine aynı anda rapor
üretir ve kayıtlar birbirinden ayrılır.

```
schtasks /Change /TN "QuantBIST Gunluk Rapor" /DISABLE
```

PC'de son bir yedek alın, sonra dosyaları sunucuya kopyalayın (PowerShell):

```
cd C:\Projeler\QuantBIST
.venv\Scripts\python -m core.backup
scp data\ledger.csv data\paper_orders.csv data\watchlist.json data\signal_log.csv data\equity_log.csv data\alerts_log.csv data\market.db kullanici@sunucu:QuantBIST/data/
```

Sunucuda klasörleri konteyner kullanıcısına (uid 1000) verin:

```
cd ~/QuantBIST
mkdir -p logs backups
sudo chown -R 1000:1000 data logs backups
```

## 5. Başlat ve doğrula

```
docker compose run --rm bot python -m core.market.update --bist100-history   # ilk sefer veya eksik veri
docker compose up -d --build
docker compose run --rm bot python -m core.reports.verify --no-backup
docker compose ps             # birkaç dakika sonra STATUS: (healthy)
```

Beklenen:
- `verify` çıktısında "Kişisel dosyalar" ve "Veri şeması" SAĞLIKLI.
- Telegram'da `/durum` çalışıyor; 5 dakika sonra "Telegram botu" satırı SAĞLIKLI.
- 18:30'da rapor geliyor; `logs/runs.csv` dosyasında `sent` satırı.

## 6. Yedekleri sunucudan al (haftalık, PC'de)

Sunucudaki yedekler verilerle aynı diskte durur. Bu yüzden `/durum` "Yedek" satırında, PC'ye
alınmadıkça uyarı verir. Yedekleri PC'ye almak için PC'de çalıştırın:

```
powershell -ExecutionPolicy Bypass -File scripts\pull_backups.ps1 -Server kullanici@sunucu
```

Betik şunları yapar:
1. Yedekleri OneDrive klasörüne kopyalar.
2. Geri yükleme testiyle okur.
3. Test geçerse sunucuya `pulled.txt` yazar.

`/durum` 8 gün çekilmezse uyarır. Haftalık bir Windows görevi olarak kurulabilir. Linux veya macOS için `scripts/pull_backups.sh` kullanılır.

## 7. Güncelleme ve geri dönüş

```
cd ~/QuantBIST
docker compose run --rm bot python -m core.backup              # önce yedek
git pull
docker compose up -d --build
docker compose run --rm bot python -m core.reports.verify --no-backup
```

Sorun çıkarsa önceki sürüme dönün: `git checkout <önceki commit> && docker compose up -d --build`.
Kişisel dosyalar `data/` içinde olduğu ve git tarafından izlenmediği için bu işlemlerden etkilenmez.

## 8. Geri PC'ye dönmek

1. Sunucuda `docker compose down` çalıştırın.
2. Dosyaları 4. adımın tersi yönünde `scp` ile PC'ye kopyalayın.
3. PC'de Windows görevini açın: `schtasks /Change /TN "QuantBIST Gunluk Rapor" /ENABLE`.

## Sorumluluk ayrımı

| Kim | Ne |
|---|---|
| Kullanıcı | Sunucu kiralama ve ödeme, SSH erişimi, `.env` içindeki token |
| Kod | Rapor, telafi çalıştırması, sağlık kontrolü, yedek ve geri yükleme testi, yedeklerin PC'ye alındığının takibi |
