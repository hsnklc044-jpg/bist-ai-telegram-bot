"""
QuantBIST
/tara ai (03.11.2026 request): the technical trigger on the BIST 30 ("dip dönüşü",
core.market.extended), each candidate asked to the signal confirmation layer
(core.ml.signal_filter). Probability >= 0.60: a rich message (stock, technical state, ML
confidence, entry zone, 2% stop, 4% take-profit); below: "AI Reddi: Olasılık %X".

The layer did not pass its out-of-sample test (K-64) and its independent validation says
"kullanılamaz" (docs/validation/M31.md): until that changes the card is titled "Doğrulanmamış model
sinyali", not "AI onayı", and carries the measured track record. A card is written to the paper book
as "onay bekliyor" only so that the user's own button can enter it (K-67); nothing is entered by the
system. Rule output, not advice.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date

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
    candle_day: date | None = None  # the day of the candle the trigger came from


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
                                   float(last["bb_yuzde"]), float(last["macd_hist"]), proba,
                                   candle_day=pd.Timestamp(df.index[-1]).date()))
        except Exception as exc:  # noqa: BLE001 - one stock's bad data must not stop the scan
            logger.warning("AI scan failed | %s | %s", symbol, exc)
    return found


def _n(x: float, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _sizing(c: Candidate, validated: bool = True) -> list[str]:
    if not c.lots:
        return ["<b>Lot:</b> hesaplanamadı (kasada boş nakit yok)"]
    cost = c.lots * c.close
    risk = c.lots * c.close * STOP
    # M31 re-validation Y1: an unvalidated card's lots are the paper book's, not a trade size
    label = "Lot (%1 risk kalkanı)" if validated else "Lot (%1 risk kalkanı; yalnız sanal defter, işlem önerisi değil)"
    return [f"<b>{label}:</b> {_n(c.lots, 0)} adet × ~{_n(c.close)} = ~{_n(cost, 0)} TL "
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
    title = (f"✅ <b>AI onayı: {code}</b>" if validated else
             f"🧪 <b>Doğrulanmamış model sinyali: {code}</b> (M31 bağımsız doğrulamada kullanılamaz)")
    return "\n".join([
        title,
        f"<b>Teknik durum:</b> RSI {_n(c.rsi, 1)} · Stoch %K {_n(c.stoch_k, 1)} · Bollinger %b {_n(c.bb)} · "
        "MACD histogramı sıfırın altında yükseliyor",
        (f"<b>ML güven skoru:</b> %{_n(c.proba * 100, 0)}" if validated else  # O3: not a calibrated probability
         f"<b>Model skoru (kalibre değil, olasılık değildir):</b> %{_n(c.proba * 100, 0)}"),
        f"<b>Giriş bölgesi:</b> ertesi seans açılışı{_entry_day(c)} (son kapanış {_n(c.close)} TL)",
        f"<b>Zarar durdur (%2, iz süren):</b> ~{_n(c.close * (1 - STOP))} TL · <b>Kâr al (%4):</b> "
        f"~{_n(c.close * (1 + TARGET))} TL",
        "<i>Stop ve hedef gerçek girişe (açılış fiyatı) göre kesinleşir; stop zirveyi %2 geriden izler.</i>",
        *_sizing(c, validated),
        f"<b>Doğrulama:</b> {state}",
        *_record_line(),
        f"<i>{DISCLAIMER}</i>",
    ])


def _entry_day(c: Candidate) -> str:
    """O2: the session the paper book enters at (the first session after the candle), named on the card."""

    from datetime import timedelta

    from core.market.calendar import is_session_day

    if c.candle_day is None:
        return ""
    day = c.candle_day + timedelta(days=1)
    for _ in range(15):
        if is_session_day(day):
            return f" ({day:%d.%m.%Y})"
        day += timedelta(days=1)
    return ""


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


def reason(c: Candidate) -> str:
    """K-70: why the card exists, as recorded in the book."""

    return (f"dip dönüşü; RSI {_n(c.rsi, 1)}; Stoch %K {_n(c.stoch_k, 1)}; Bollinger %b {_n(c.bb)}; "
            f"MACD histogramı {_n(c.macd_hist)} (yükseliyor); ML %{_n(c.proba * 100, 0)}")


def run(day, frames: dict[str, pd.DataFrame], model, validated: bool, book=None,
        expected: date | None = None) -> list[tuple[str, int | None]]:
    """(message, card id) of one /tara ai. An approved candidate is written to the paper book as
    "onay_bekliyor" with its lots; it is entered only when the user presses [✅ İşleme Gir]
    (K-67). The id is None for every other message (no buttons). A candidate whose candle is older
    than `expected` (the last final session) gets no card: stale prices (M31-ORTA-3)."""

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
            if expected is not None and c.candle_day is not None and c.candle_day < expected:
                out.append((f"⚠️ {html.escape(c.symbol.removesuffix('.IS'))}: veri eski (son mum "
                            f"{c.candle_day:%d.%m.%Y}, beklenen {expected:%d.%m.%Y}); kart yazılmadı. "
                            "Fiyat güncellemesini /durum'dan kontrol edin.", None))
                continue
            if c.proba is not None and c.proba >= APPROVE:
                try:
                    if conn is None:
                        conn = store.connect(book)
                        store.expire_pending(conn, day)
                    box, free = store.cash(conn)
                    # D2: today's cards waiting for their button share the free cash (they are not
                    # open positions yet, so store.cash does not count them)
                    waiting = sum((s.qty or 0) * (s.signal_close or 0) for s in store.signals(conn)
                                  if s.status == store.PENDING and s.created == day)
                    c.box, c.lots = box, store.size_position(box, free - waiting, c.close)
                    if c.lots:
                        card = store.add(conn, day, c.symbol, c.close, c.proba, source="tara-ai", qty=c.lots,
                                         status=store.PENDING, reason=reason(c))
                except Exception as exc:  # noqa: BLE001 - the message still goes out, without buttons
                    logger.warning("AI card not recorded | %s | %s", c.symbol, exc)
            out.append((message(c, validated), card))
    finally:
        if conn is not None:
            conn.close()
    return out


MAX_MODEL_AGE = 10  # days; the model is retrained every Friday


def live(day) -> list[tuple[str, int | None]]:
    """The bot's /tara ai: BIST 30 daily candles, the live model (trained when missing or older than
    MAX_MODEL_AGE). Returns (message, card id) pairs like run()."""

    from core.config.bist30 import BIST30_TICKERS
    from core.ml import signal_filter as S
    from core.reports.daily import adjusted_bars

    saved = S.load_live()
    try:  # M31-13: a model older than MAX_MODEL_AGE (a missed Friday retrain) is retrained, not used
        stale = saved is not None and (day - date.fromisoformat(str(saved.get("trained")))).days > MAX_MODEL_AGE
    except (TypeError, ValueError):
        stale = True
    if saved is None or stale:
        from core.ml import training_log

        frames, members = S._daily()
        rows = S.fit_live(frames, members, day)
        training_log.record(day, "tara-ai", "model yok" if saved is None else f"model eski ({saved.get('trained')})",
                            rows)
        saved = S.load_live()
    from core.market.calendar import last_final_session_date

    frames = {s: adjusted_bars(s) for s in BIST30_TICKERS}
    out = run(day, frames, saved["model"] if saved else None, S.validated("gunluk"),
              expected=last_final_session_date())
    try:  # D1: a model still too old after the retrain attempt is used, but never silently
        trained = date.fromisoformat(str(saved.get("trained"))) if saved else None
    except (TypeError, ValueError):
        trained = None
    if saved is not None and (trained is None or (day - trained).days > MAX_MODEL_AGE):
        when = f"{trained:%d.%m.%Y}" if trained else "bilinmeyen bir tarihte"
        out.insert(0, (f"⚠️ /tara ai: model {when} eğitildi ve yeniden eğitilemedi; skorlar eski modelden.", None))
    return out


__all__ = ["Candidate", "candidates", "live", "message", "run"]
