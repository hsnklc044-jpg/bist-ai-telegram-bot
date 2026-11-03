"""
QuantBIST
/tara ai (03.11.2026 request): the technical trigger on the BIST 30 ("dip dönüşü",
core.market.extended), each candidate asked to the signal confirmation layer
(core.ml.signal_filter). Probability >= 0.60: a rich message (stock, technical state, ML
confidence, entry zone, 2% stop, 4% take-profit); below: "AI Reddi: Olasılık %X".

The layer did not pass its out-of-sample test (K-64): until it does, every message says the model
is not validated and no signal is written to the paper book. Rule output, not advice.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

import pandas as pd

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

STOP, TARGET = 0.02, 0.04
DISCLAIMER = "Kural çıktısıdır, öneri değildir. Karar ve sorumluluk kullanıcıdadır."


@dataclass
class Candidate:
    symbol: str
    close: float
    rsi: float
    stoch_k: float
    bb: float
    macd_hist: float
    proba: float | None
    lots: int = 0  # K-67: the lots whose 2% stop costs 1% of the cash box
    box: float = 0.0


def candidates(frames: dict[str, pd.DataFrame], model) -> list[Candidate]:
    """Stocks whose latest final daily candle triggers, with the model's probability."""

    from core.market.extended import add_indicators, trigger_mask
    from core.ml.signal_filter import features

    found = []
    for symbol, df in sorted(frames.items()):
        try:
            if df is None or len(df) < 250:
                continue
            ind = add_indicators(df)
            if not bool(trigger_mask(ind).iloc[-1]):
                continue
            row = features(df).iloc[[-1]]
            proba = None
            if model is not None and not row.isna().any(axis=None):
                proba = float(model.predict_proba(row.to_numpy())[0, 1])
            last = ind.iloc[-1]
            found.append(Candidate(symbol, float(last["close"]), float(last["rsi"]), float(last["stoch_k"]),
                                   float(last["bb_yuzde"]), float(last["macd_hist"]), proba))
        except Exception as exc:  # noqa: BLE001 - one stock's bad data must not stop the scan
            logger.warning("AI scan failed | %s | %s", symbol, exc)
    return found


def _n(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sizing(c: Candidate) -> list[str]:
    if not c.lots:
        return ["<b>Lot:</b> hesaplanamadı (kasada boş nakit yok)"]
    cost = c.lots * c.close
    risk = c.lots * c.close * STOP
    return [f"<b>Lot (%1 risk kalkanı):</b> {_n(c.lots, 0)} adet × ~{_n(c.close)} = ~{_n(cost, 0)} TL "
            f"(kasanın %{_n(cost / c.box * 100, 0)}'i)",
            f"<i>Stop gelirse ~{_n(risk, 0)} TL (kasa {_n(c.box, 0)} TL'nin %1'i); boşluklu açılışta kayıp daha "
            "büyük olabilir. Bu kural tek hisseye kasanın büyük bir kısmını ayırır.</i>"]


def message(c: Candidate, validated: bool) -> str:
    """HTML (Telegram parse_mode="HTML"): the rich approval, or the rejection line."""

    from core.ml.signal_filter import APPROVE

    code = html.escape(c.symbol.removesuffix(".IS"))
    if c.proba is None:
        return f"🤖 {code}: teknik tetik var, AI olasılığı hesaplanamadı (model ya da veri yok)."
    if c.proba < APPROVE:
        return f"🚫 <b>AI Reddi</b>: {code} – olasılık %{_n(c.proba * 100, 0)} (eşik %{_n(APPROVE * 100, 0)})"
    state = ("doğrulandı (K-64)" if validated else
             "⚠️ model örneklem dışı ölçümde geçmedi (K-64): kendiliğinden işlem açılmaz, işleme girmek sizin kararınız")
    return "\n".join([
        f"✅ <b>AI onayı: {code}</b>",
        f"<b>Teknik durum:</b> RSI {_n(c.rsi, 1)} · Stoch %K {_n(c.stoch_k, 1)} · Bollinger %b {_n(c.bb)} · "
        "MACD histogramı sıfırın altında yükseliyor",
        f"<b>ML güven skoru:</b> %{_n(c.proba * 100, 0)}",
        f"<b>Giriş bölgesi:</b> ertesi seans açılışı (son kapanış {_n(c.close)} TL)",
        f"<b>Zarar durdur (%2, iz süren):</b> ~{_n(c.close * (1 - STOP))} TL · <b>Kâr al (%4):</b> "
        f"~{_n(c.close * (1 + TARGET))} TL",
        "<i>Stop ve hedef gerçek girişe (açılış fiyatı) göre kesinleşir; stop zirveyi %2 geriden izler.</i>",
        *_sizing(c),
        f"<b>Doğrulama:</b> {state}",
        *_record_line(),
        f"<i>{DISCLAIMER}</i>",
    ])


def _record_line() -> list[str]:
    """v0.99.35: what the out-of-sample test found, so the decision is made with the real figures."""

    from core.analytics import card_study
    from core.ml.signal_filter import SPEC, track_record

    own = [card_study.card_line(*card_study.latest())]
    r = track_record("gunluk")
    if r is None:
        return own
    x, y = SPEC["gunluk"]
    verdict = ("onay isabeti artırmadı" if r.precision <= r.base_rate else "onaylananlar tabanın üstünde")
    return [f"<b>Geçmiş ölçüm:</b> onaylanan {r.approved} sinyalde isabet %{_n(r.precision * 100, 1)}, "
            f"tüm tetiklerde %{_n(r.base_rate * 100, 1)} ({verdict}; isabet: {x} seans sonra kapanış ≥ "
            f"+%{y * 100:g}; {html.escape(r.source)})", *own]


def run(day, frames: dict[str, pd.DataFrame], model, validated: bool, book=None) -> list[tuple[str, int | None]]:
    """(message, card id) of one /tara ai. An approved candidate is written to the paper book as
    "onay_bekliyor" with its lots; it is entered only when the user presses [✅ İşleme Gir]
    (K-67). The id is None for every other message (no buttons)."""

    from core.ml.signal_filter import APPROVE
    from core.signals import store

    found = candidates(frames, model)
    if not found:
        return [(f"🔎 /tara ai: bugün BIST 30'da teknik tetik (dip dönüşü) olan hisse yok. {DISCLAIMER}", None)]
    out: list[tuple[str, int | None]] = [(f"🔎 /tara ai: {len(found)} hissede teknik tetik; AI katmanına soruldu.",
                                          None)]
    conn = None
    try:
        for c in found:
            card = None
            if c.proba is not None and c.proba >= APPROVE:
                try:
                    conn = conn or store.connect(book)
                    box, free = store.cash(conn)
                    c.box, c.lots = box, store.size_position(box, free, c.close)
                    if c.lots:
                        card = store.add(conn, day, c.symbol, c.close, c.proba, source="tara-ai", qty=c.lots,
                                         status=store.PENDING)
                except Exception as exc:  # noqa: BLE001 - the message still goes out, without buttons
                    logger.warning("AI card not recorded | %s | %s", c.symbol, exc)
            out.append((message(c, validated), card))
    finally:
        if conn is not None:
            conn.close()
    return out


def live(day) -> list[str]:
    """The bot's /tara ai: BIST 30 daily candles, the live model (trained when missing)."""

    from core.config.bist30 import BIST30_TICKERS
    from core.ml import signal_filter as S
    from core.reports.daily import adjusted_bars

    saved = S.load_live()
    if saved is None:
        frames, members = S._daily()
        S.fit_live(frames, members, day)
        saved = S.load_live()
    frames = {s: adjusted_bars(s) for s in BIST30_TICKERS}
    return run(day, frames, saved["model"] if saved else None, S.validated("gunluk"))


__all__ = ["Candidate", "candidates", "live", "message", "run"]
