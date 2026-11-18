# Süreklilik tatbikatı: kuru sıfırdan kurulum (18.11.2026)

**Kapsam:** canlıya dokunulmadı.
- Gerçek `.env`, Telegram ve Healthchecks adresleri kullanılmadı. Tatbikat klasöründe `.env` hiç yoktu.
- Windows görevi kaydedilmedi.

**Klasör:** `C:\Projeler\QuantBIST-tatbikat`, tatbikat sonunda kaldırıldı.

| Adım | Komut | Süre | Sonuç |
|---|---|---|---|
| 1. Depodan klon | `git clone --branch claude/borsa-bot-creation-n7nmc9` | 2 sn | ✅ 0af56f3 (bot dalı ucu, v0.99.144) |
| 2. Kurulum ve denetim | `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` | 507 sn | ✅ Kurulum ve doğrulamayı tek komutta yaptı: Python 3.11.8 sanal ortamı; paketler `requirements.lock` ile birebir aynı; ruff temiz; testler 1772 geçti, 2 atlandı (testler 220 sn) |
| **Toplam** | | **509 sn (8 dk 29 sn)** | 18:43:59 – 18:52:28 |

**Ortam:** bilgisayar prizdeydi. Aynı anda canlı bot ve bu oturum çalışıyordu.

## Kapsanmayan adımlar (gerçek bir arızada da gerekir)
| # | Adım | Neden kapsanmadı | Nerede yazılı | Tahmini ek süre |
|---|---|---|---|---|
| 1 | `.env` (BOT_TOKEN, CHAT_ID, HC adresleri, BACKUP_DIR) | gizli bilgi; tatbikatta kullanılmaz | `.env.example`, OPERATIONS §1 | kullanıcıya bağlı, ~5 dk |
| 2 | Kişisel kayıtların ve `data/`'nın yedekten geri yüklenmesi | gerçek yedek tatbikata alınmadı; geri yükleme testi ayrı çalışıyor (16.11 başarılı, SLO "Yedek") | OPERATIONS §3; `python -m core.backup --restore <zip>` | ölçülmedi |
| 3 | `market.db` ve fiyat geçmişi (3 GB `data/`) | yedekte mi, yeniden mi indirilecek, belirsiz | OPERATIONS §2 | **ölçülmeli** (en uzun adım olabilir) |
| 4 | Windows görevleri (bot, günlük rapor, güncelleyici) | sistem ayarıdır, kullanıcının işi | `scripts\register_*.ps1`, `scripts\yeni_kurulum.ps1` | ~2 dk |
| 5 | İlk Telegram mesajı ve Healthchecks sinyali | gerçek adres gerekir | OPERATIONS §7 | ~1 dk |

## Bulgular
- **B1 ✅** Depo ve `setup.ps1`, kodu ve test takımını 8,5 dakikada sıfırdan kurup doğruluyor. Paketler kilit dosyasıyla birebir aynı (Md. 12).
- **B2 ⚠️** Gerçek bir makine değişiminde en uzun ve en belirsiz adım `data/` (3 GB) ile kişisel kayıtların geri gelmesi. Bu adımın süresi hiç ölçülmedi. Öneri: KT-07 / İP-3 kapsamında, bir yedek zipinin geçici klasöre geri yüklenmesiyle süresi ölçülsün. Gerçek veri yalnız okunur ve geçici klasöre açılır; sahibin onayıyla, çünkü kişisel kayıt içerir.
- **B3 ℹ️** Klonlanan kod bot dalının ucu (0af56f3). Canlı kurulum b1ab854'te; aradaki fark yalnız belge. Bu gece 1a' ve 1d' girince fark kapanır.

**Hedef süre (CHARTER_2028 H3):** kod ve testler için 10 dk (bugün 8,5 dk ölçüldü). Uçtan uca geri dönüş süresi B2 ölçülünce yazılacak.
