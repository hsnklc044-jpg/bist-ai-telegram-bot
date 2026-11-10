# QuantBIST — Claude için çalışma kuralları

BIST hisse araştırma ve Telegram botu (Python 3.11). Ayrıntılı kurallar: `docs/CHARTER.md`, kararlar: `docs/DECISIONS.md`,
işletim: `docs/OPERATIONS.md`, olgunluk: `docs/MATURITY.md`.

## Kesin sınırlar (CHARTER, K-54; kullanıcı istese bile yapılmaz)
- gerçek para
- aracı kurum
- ödeme
- hesap açma
- şifre ya da token
- al/sat önerisi
- KAP/Telegram içeriğini yeniden yayımlamak
- git geçmişini yeniden yazmak
- kişisel kayıt silmek

Ek olarak: emir verilmez; `C:\Projeler\QuantBIST-yeni` canlı kurulumdur, oraya elle dosya yazılmaz, izlenen dosyası
değiştirilmez (`.claude/` ve `CLAUDE.md` de yalnız dal üzerinden girer); canlıya giden her şey `surum-kapisi`
skill'inden geçer.

## Çalışma
- Geliştirme bir worktree'de (`C:\Projeler\QuantBIST-araclar\` altında), dal üzerinde.
- Test: `python -m pytest -q -p no:cacheprovider`, lint: `python -m ruff check .` (venv: `C:\Projeler\QuantBIST-yeni\.venv`).
- Önce hatayı gösteren başarısız test, sonra düzeltme. Her sürümde `pyproject.toml`, `core/__init__.py`, `CHANGELOG.md`.
- Ölçümden önce kayıt: yeni bir ölçüm ya da araştırma `on-kayit` skill'iyle DECISIONS'a yazılmadan çalıştırılmaz.
- İş seçimi: `siradaki-is` (CHARTER §4). Koşulu oluşan iş yoksa durulur; boş iş üretilmez, yeni özellik önerilmez.
- Commit sonu: `Co-Authored-By: Claude <noreply@anthropic.com>`.

## Skill'ler
- `siradaki-is`: CHARTER §4 sırasıyla işi seçer ve yapar.
- `surum-kapisi`: birleştirme ve canlı kurulum kapısı (`scripts/surum_kapisi.py`).
- `olgunluk`: MATURITY seviyelerinin yüzdesi (salt okunur).
- `on-kayit`: ölçümden önce DECISIONS kaydı.
- `robot`: tek düğme; döngüyü durma koşuluna kadar çalıştırır (günlük: `docs/ROBOT_LOG.md`).
