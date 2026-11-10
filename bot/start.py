"""
QuantBIST
Start / Help Command
"""

from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from core.infrastructure.settings import settings

HELP_TEXT = f"""🚀 {settings.app_name} v{settings.version}

Komutlar:
/top – teknik skoru en yüksek hisseler (tahmin gücü yok)
/analyze THYAO – tek hisse teknik analizi (en yakın 3 destek ve 3 direnç dahil)
/seviye THYAO – bütün destek/direnç seviyeleri: yöntem, güç, ATR uzaklığı (teknik seviye, öneri değil)
/karne THYAO – 12 göstergeli teknik karne, 100 puan (TradingView betiğinin kuralları; öneri değil)
/tablo – takip listen, kayıtlı tarama ya da seçtiğin hisseler için RSI, fiyat/EMA, hacim ve mum tablosu (öneri değil)
/uzun THYAO [üst alım fiyatı] – 6–12 ay modeli: 100 puanlık teknik puan ve puandan ayrı giriş kararı (İzle / Giriş adayı / Veri yetersiz; temel filtre henüz yok; öneri değil)
/uzun_ust THYAO 250 – üst alım fiyatını kalıcı kaydet (/uzun bunu kullanır); /uzun_ust THYAO sil; /uzun_ust liste (sınır senindir, öneri değil)
/piyasa – piyasa rejimi (yükseliş/düşüş/karışık/yüksek oynaklık), genişlik ve dört ana sektör (etiket, sinyal değil)
/senaryo THYAO – senaryo şablonları: giriş varsayımı, geçersizlik, hedef, R ve adet hesabı (hesap aracı, öneri değil); /senaryo THYAO giris 240 gecersiz 232 hedef 262
/risk [gercek|sanal] – risk bütçesi: sınırlarının kullanımı; /risk ekle THYAO 100 (ya şöyle olsaydı), /risk denge (hesap sonucu, öneri değil)
/temel THYAO – temel puanlar: Piotroski F, Altman Z'', Beneish M, Greenblatt, Novy-Marx (yayın tarihli veriden; veri yoksa 'veri yok')
/summary – portföy ve piyasa özeti
/panik – acil durdurma: bekleyen sinyalleri iptal eder, açık pozisyonları son kapanıştan kapatır, taramaları kilitler; /devam – kilidi kaldırır
/watchlist – takip listesi
/watchadd EREGL – listeye ekle
/watchremove EREGL – listeden çıkar
/watchscan – takip listesini tara

Portföy ve risk:
/portfolio – pozisyonlar ve kâr/zarar (gerçek ve sanal)
/trade al THYAO 100 285,50 – gerçekleşmiş işlemi deftere yaz
/paper al THYAO 100 – sanal emir (bir sonraki açılıştan dolar)
/paper – bekleyen sanal emirler, /paper iptal 3
/alerts – açık risk uyarıları
/report – günlük raporu şimdi üret
/performans – kayıtlı görünümlerin ve sanal hesabın canlı sonucu (XU100'e karşı)
/durum – sistem sağlığı: son rapor, veri, canlı kayıt, yedek
/rapor_tekrar – kayıtlı son raporu yeniden gönder (/rapor_tekrar 27.10)
/stres – pozisyonlar XU100'ün en kötü geçmiş düşüşlerinde ve en büyük kur şoklarında ne kaybederdi (/stres sanal)
/saglik – portföy sağlık raporu: dağılım, yoğunlaşma, korelasyon, reel ve dolar bazında getiri (her cumartesi de gelir)
/denge THYAO=30 ASELS=20 – hedef ağırlığa dönmek için gereken işlem hesabı (öneri değil, emir yok)
/takvim – temettü ve şirket olayları takvimi; /takvim ekle THYAO 05.12.2026 temettü 3,25 TL (elle girilir)
/ozet – haftalık işletme özeti şimdi (pazar 18:00'de kendiliğinden gelir; gelmezse pazartesi 09:00'da uyarı)
/yil – yıllık döküm: satış sonuçları, temettü, komisyon (/yil 2026 sanal)
/alarm THYAO altında 240 – kapanış alarmı (akşam raporunda bir kez); %5 de olur (son kapanışa göre); /alarm liste, /alarm sil 1
/tara rsi<30 ema20>ema50 – hisseleri kendi gösterge koşullarınla filtrele, geçmiş karnesiyle (/tara: kılavuz ve örnekler; /tara_alanlar, /tara_aciklama THYAO rsi<30, /tara_devam, /tara_kaydet AD koşullar, /tara_liste, /tara_sil AD). Filtredir, öneri değildir
/tara ai – BIST 30'da teknik tetik (dip dönüşü) arar, her adayı AI katmanına sorar: %60 ve üstü onay mesajı (güven skoru, giriş bölgesi, %2 stop, %4 kâr al), altı 'AI Reddi'. Onaylı kartın altındaki [✅ İşleme Gir] düğmesiyle sanal pozisyon açılır (lot %1 risk kuralıyla, stop iz süren), [❌ İptal Et] ile atılır
/tara_sablonlar – hazır şablonlar (TradingView taramalarının teknik kısmı) ve karneleri; /tara AD ile çalışır
/tara_abone AD – kayıtlı tarama ya da şablon her işlem günü 18:30 raporundan sonra çalışır, yalnız giren/çıkan hisseler gelir (/tara_abonelikler, /tara_abone_iptal AD)
/tara_sanal AD – taramayı önceden yazılmış kurallarla ölçüm amaçlı sanal kitapta işletir (varsayılan kapalı; /performans'ta "sanal" etiketiyle; /paper'a dokunmaz)
/help – bu mesaj

ℹ️ Teknik skorun backtest'te getiri tahmin gücü bulunmadı;
bilgi amaçlıdır, yatırım tavsiyesi değildir. Bot gerçek emir göndermez."""


# everyday commands as buttons under the text field (a tap sends the command)
KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton(c) for c in row] for row in (
        ("/durum", "/summary", "/portfolio"),
        ("/alerts", "/performans", "/rapor_tekrar"),
    )],
    resize_keyboard=True,
    is_persistent=True,
)


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start and /help."""

    await update.effective_message.reply_text(HELP_TEXT, reply_markup=KEYBOARD)
