"""
QuantBIST
/tara as text: the list, the eliminated stocks by name, the history card and the fixed last
line. A filter, not advice (DECISIONS K-32, K-33): no "al/sat/öneri/fırsat/hedef fiyat" wording,
the order is alphabetical or by a measured field, never "best".
"""

from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from core.config.paths import SCREENS_FILE
from core.infrastructure.csvfiles import open_append, read_rows
from core.screen import card as C
from core.screen import engine, universe
from core.screen.language import ScreenError, normalize, parse

SOURCE = "tara"
MAX_ROWS = 15
MAX_SAVED = 20
DISCLAIMER = "Filtre sonucudur, yatırım önerisi değildir."
SAVE_USAGE = "Kullanım: /tara_kaydet AD koşullar (ör. /tara_kaydet dusuk_rsi rsi<30)"
ORDER_TEXT = {"alfabetik": "alfabetik", "goreli_guc": "göreli güç (XU100'e göre 20 seans, büyükten küçüğe)",
              "hacim": "hacim oranı (büyükten küçüğe)", "rsi": "RSI (küçükten büyüğe)"}
EXAMPLES = ("rsi<30", "ema20>ema50 ve hacim_oran>1,5", "kesti_yukari(ema20,ema50) ve adx>20",
            "kapanis>yuksek_20g ve islem_tl>50 sirala=hacim", "rsi 30..50 ve gg_sira>80 evren=izleme")
_NAME = re.compile(r"[a-z0-9_]{1,20}")


def criterion_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


# --- message --------------------------------------------------------------------------------------


def _line(m: engine.Match) -> str:
    from core.reports.daily import tr

    close, atr = m.close, m.atr
    if close and atr == atr:
        risk = (f"1 ATR %{tr(atr / close * 100, 1)} ({tr(atr, 2)} TL) · "
                f"2 ATR %{tr(2 * atr / close * 100, 1)} ({tr(2 * atr, 2)} TL)")
    else:
        risk = "ATR —"
    flags = "".join(f" | ⚠️ {f}" for f in m.flags)
    return (f"• {m.symbol.removesuffix('.IS')} {tr(close, 2)} | {' · '.join(m.met)} | {risk} | "
            f"likidite {engine.value_text('islem_tl', m.liquidity)}{flags}")


def format_result(result: engine.Result, card: dict | None, note: str = "", rows: int = MAX_ROWS,
                  trials: tuple[int, int] | None = None) -> str:
    q = result.query
    lines = [f"🔎 /tara {q.text}"]
    if q.template:
        from core.screen.templates import TEMPLATES

        t = TEMPLATES[q.template]
        lines.append(f"🧩 şablon: {q.template} ({t.source}; atlanan: {t.skipped})")
    if note:
        lines.append(f"🕒 {note}")
    listed = result.scanned + len(result.missing)
    lines.append(f"{result.day:%d.%m.%Y} kapanışı · {universe.LABELS[q.universe]}, {listed} hisse · "
                 f"{result.scanned} hisse tarandı · "
                 f"{len(result.matches)} hisse koşulları sağlıyor · sıra: {ORDER_TEXT[q.order]}")
    if result.matches:
        lines += [_line(m) for m in result.matches[:rows]]
        if len(result.matches) > rows:
            lines.append(f"(+{len(result.matches) - rows} hisse daha: /tara_devam)")
    else:
        lines.append("Koşulları sağlayan hisse yok.")
        if result.funnel:
            lines.append(f"Koşul hunisi ({result.scanned} hisse tarandı; her koşul tek başına / öncekilerle birlikte):")
            lines += [f"  {text}: tek başına {alone}, birlikte {together}" for text, alone, together in result.funnel]
            worst = min(result.funnel, key=lambda f: f[1])
            lines.append(f"  en çok eleyen: {worst[0]} (tek başına {worst[1]} hisse)")
    if result.illiquid:
        names = ", ".join(s.removesuffix(".IS") for s in result.illiquid[:10])
        more = f" +{len(result.illiquid) - 10}" if len(result.illiquid) > 10 else ""
        lines.append(f"Likidite tabanının altında (20 gün ort. < {q.liquidity:g} mn TL, taranmadı): "
                     f"{names}{more}. Kapatmak için likidite=0")
    if result.missing:
        lines.append("Veri eksik (taranmadı): " + "; ".join(f"{s.removesuffix('.IS')} ({why})"
                                                             for s, why in result.missing))
    lines.append("")
    lines += card_lines(card, trials)
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def card_lines(card: dict | None, trials: tuple[int, int] | None = None) -> list[str]:
    import pandas as pd

    from core.backtest.run import SCREEN_END
    from core.reports.daily import pct, tr

    if card is None:
        return ["📒 Geçmiş karne hesaplanamadı."]
    lines = [f"📒 Geçmiş karne ({C.HISTORY_START[:7]} – {pd.Timestamp(SCREEN_END):%d.%m.%Y}, holdout öncesi; o günkü "
             f"BIST 100 üyeleri; giriş ertesi seansın açılışı, maliyet dahil (gidiş-dönüş %{tr(C.ROUND_TRIP_COST * 100, 2)}); "
             "XU100'e göre fazla getiri):"]
    for h in sorted(card):
        s = card[h]
        if s.n < C.MIN_SAMPLES or s.mean is None:
            lines.append(f"  {h} seans: yetersiz örnek ({s.n})")
            continue
        interval = f" %95 [{pct(s.low)}, {pct(s.high)}]" if s.low is not None else " (aralık için gün az)"
        without = f", en kârlı 5 hisse hariç {pct(s.without_top)}" if s.without_top is not None else ""
        gross = f" (maliyet hariç {pct(s.gross)})" if s.gross is not None else ""
        day = f"gün ortalaması {pct(s.day_mean)}{interval} · " if s.day_mean is not None else ""
        base = (f" · tüm hisseler {pct(s.base)}, fark {pct(s.day_mean - s.base)}"
                if s.base is not None and s.day_mean is not None else "")
        lines.append(f"  {h} seans: {day}olay ortalaması {pct(s.mean)}{gross}, medyan {pct(s.median)}, "
                     f"isabet %{s.hit * 100:.0f}, örnek {s.n} (bağımsız {s.independent}){without}{base} → {s.label}")
    if trials:
        lines.append(f"  ⚠️ Veri gözetlemesi: bu oturumda {trials[0]}. deneme; bugüne kadar {trials[1]} farklı kriter "
                     "denendi. Ne kadar çok koşul denenirse iyi görünen bir karnenin şans olma ihtimali o kadar artar.")
    lines.append("  Geçmişin özetidir; bir kuralın işe yaradığına kanıt sayılmaz (araştırma programı dışında).")
    return lines


# --- the chat's last screen: /tara_devam and the buttons --------------------------------------------


@dataclass
class Session:
    result: engine.Result
    card: dict | None
    offset: int = MAX_ROWS
    trials: tuple | None = None


SESSIONS: dict = {}  # chat id -> Session (memory only; a restart forgets it)


def _criteria(query) -> str:
    return query.text + (f" sirala={query.order}" if query.order != "alfabetik" else "")


def more_text(chat_id) -> str:
    session = SESSIONS.get(chat_id)
    if session is None:
        return "Önce /tara ile bir tarama yap."
    matches = session.result.matches
    if session.offset >= len(matches):
        return "Liste bitti; başka hisse yok."
    start, end = session.offset, min(session.offset + MAX_ROWS, len(matches))
    session.offset = end
    lines = [f"🔎 /tara {session.result.query.text} · {start + 1}–{end} / {len(matches)}"]
    lines += [_line(m) for m in matches[start:end]]
    if end < len(matches):
        lines.append(f"(+{len(matches) - end} hisse daha: /tara_devam)")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def has_more(chat_id) -> bool:
    session = SESSIONS.get(chat_id)
    return session is not None and session.offset < len(session.result.matches)


def card_text(chat_id) -> str:
    session = SESSIONS.get(chat_id)
    if session is None:
        return "Önce /tara ile bir tarama yap."
    return "\n".join([f"🔎 /tara {session.result.query.text}", *card_lines(session.card, session.trials), DISCLAIMER])


def save_hint(chat_id) -> str:
    session = SESSIONS.get(chat_id)
    if session is None:
        return "Önce /tara ile bir tarama yap."
    return ("Kaydetmek için bu satırı kopyala, AD yerine bir ad yaz (harf, rakam, _):\n"
            f"/tara_kaydet AD {_criteria(session.result.query)}")


def fields_text() -> str:
    from core.screen import fields as F

    lines = ["🔎 /tara alanları (birimleriyle). Parametre alanlar: ema(50), rsi(7), roc(5), atr(20), adx(20)."]
    group = None
    for name, f in F.FIELDS.items():
        if f.group != group:
            group = f.group
            lines.append(f"\n{group}")
        shown = f"{name}(n), varsayılan {f.param}" if f.param else name
        lines.append(f"  {shown}: {f.text} [{f.unit}]")
    lines.append("\nKısaltmalar: hacim = hacim_oran, goreli_guc = gg_20. Örnekler için /tara.")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


EXPLAIN_USAGE = "Kullanım: /tara_aciklama KOD koşullar (ör. /tara_aciklama THYAO rsi<30 ema20>ema50)"


def _leaf_line(leaf, tail) -> str:
    holds = bool(leaf.mask(tail).iloc[-1])
    row = tail.iloc[-1]
    from core.screen import language as L

    if isinstance(leaf, L.Within):
        detail = "son pencerede " + ("sağlandı" if holds else "sağlanmadı")
    elif isinstance(leaf, L.Cross):
        detail = ", ".join(f"{engine.label(o.key)} {engine.value_text(o.key, row[o.key])}"
                           for o in (leaf.a, leaf.b) if o.key is not None)
    elif isinstance(leaf, L.Range):
        detail = f"{engine.label(leaf.operand.key)} {engine.value_text(leaf.operand.key, row[leaf.operand.key])}"
    else:
        detail = ", ".join(f"{engine.label(o.key)} {engine.value_text(o.key, row[o.key])}"
                           for o in (leaf.left, leaf.right) if o.key is not None)
    return f"{'✓' if holds else '✗'} {leaf.text()} — {detail}"


def explain_text(words: list[str], chat_id=None, live=None, history_data=None, signal_path=None, saved_path=None,
                 now: datetime | None = None, suspects=None) -> str:
    from core.market.calendar import now_istanbul
    from core.screen import fields as F
    from core.screen import language as L

    now = now or now_istanbul()
    if len(words) < 2:
        return EXPLAIN_USAGE
    code = normalize(words[0]).upper().removesuffix(".IS")
    symbol = f"{code}.IS"
    text = " ".join(words[1:])
    try:
        saved = load_saved(saved_path)
    except Exception:  # noqa: BLE001
        saved = {}
    text = saved.get(normalize(text), text)
    try:
        query = parse(text)
        scanned = universe.symbols(query.universe, chat_id) if "gg_sira" in query.fields else []
    except ScreenError as exc:
        return str(exc)
    frames, bench = (live or _live)(sorted({symbol, *scanned}))
    df = frames.get(symbol)
    if df is None or df.empty:
        return f"{code} için fiyat verisi yok (BIST kodu doğru mu?).\n{DISCLAIMER}"
    lines = [f"🔎 /tara_aciklama {code}: {query.text}"]
    latest = bench.index[-1]
    found = universe.suspects() if suspects is None else suspects
    if df.index[-1] != latest:
        lines.append(f"⚠️ /tara bu hisseyi taranmadı sayar: son kapanış {df.index[-1]:%d.%m} "
                     f"(son seans {latest:%d.%m}); değerler {df.index[-1]:%d.%m} kapanışından.")
    elif code in found:
        lines.append("⚠️ /tara bu hisseyi taranmadı sayar: ikinci kaynakta fark var (düzeltme bekliyor).")
    wanted = engine.columns(query)
    table = F.table(df, bench["close"], wanted)
    if "gg_sira" in query.fields:
        others = {s: F.table(f, bench["close"], ["gg_60"])["gg_60"].iloc[-1]
                  for s, f in frames.items() if f is not None and not f.empty and f.index[-1] == latest}
        ranks = (pd_series(others).rank(pct=True) * 100) if others else None
        table.loc[table.index[-1], "gg_sira"] = ranks.get(symbol) if ranks is not None else float("nan")
    tail = table.iloc[-engine.LOOKBACK:]
    lines += [_leaf_line(leaf, tail) for leaf in query.leaves()]
    liquidity = table["islem_tl"].iloc[-1]
    if query.liquidity > 0:
        ok = liquidity >= query.liquidity
        lines.append(f"{'✓' if ok else '✗'} likidite {engine.value_text('islem_tl', liquidity)} "
                     f"(taban {query.liquidity:g} mn TL{'' if ok else '; altında olduğu için taranmaz'})")
    holds = bool(query.mask(tail).iloc[-1])
    whole = "koşulların hepsi" if isinstance(query.root, (L.And, L.Compare, L.Range, L.Cross)) else "ifade"
    lines.append(f"Sonuç: {whole} {'sağlanıyor' if holds else 'sağlanmıyor'} ({df.index[-1]:%d.%m.%Y} kapanışı).")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def pd_series(values: dict):
    import pandas as pd

    return pd.Series(values, dtype=float)


# --- saved screens (CSV until Aşama 4) ------------------------------------------------------------

SAVED_COLUMNS = ("at", "name", "criteria")


def load_saved(path: Path | None = None) -> dict[str, str]:
    """name -> criteria; a later row for the same name replaces the earlier one."""

    return {row["name"]: row["criteria"] for _, row in read_rows(Path(path or SCREENS_FILE), SAVED_COLUMNS)}


def save_text(words: list[str], path: Path | None = None, now: datetime | None = None) -> str:
    from core.market.calendar import now_istanbul
    from core.screen import fields as F

    path = Path(path or SCREENS_FILE)
    if len(words) < 2:
        return SAVE_USAGE
    name = normalize(words[0])
    if not _NAME.fullmatch(name):
        return "⚠️ Ad yalnız küçük harf, rakam ve _ olabilir (en fazla 20). " + SAVE_USAGE
    if name in F.FIELDS:
        return f"⚠️ Ad bir alan adı olamaz ('{name}'). " + SAVE_USAGE
    from core.screen.templates import TEMPLATES

    if name in TEMPLATES:
        return f"⚠️ '{name}' hazır bir şablonun adı; başka bir ad seç (/tara_sablonlar). " + SAVE_USAGE
    try:
        query = parse(" ".join(words[1:]))
    except ScreenError as exc:
        return str(exc)
    saved = load_saved(path)
    if name not in saved and len(saved) >= MAX_SAVED:
        return f"⚠️ En fazla {MAX_SAVED} kayıtlı tarama olabilir."
    criteria = query.text + (f" sirala={query.order}" if query.order != "alfabetik" else "")
    fh, new_file = open_append(path)
    with fh:
        writer = csv.writer(fh, lineterminator="\n")
        if new_file:
            writer.writerow(SAVED_COLUMNS)
        writer.writerow([(now or now_istanbul()).isoformat(timespec="seconds"), name, criteria])
    return f"💾 Kaydedildi: {name}: {criteria}\nÇalıştırmak için: /tara {name}"


# --- the command ----------------------------------------------------------------------------------


def help_text(saved: dict[str, str]) -> str:
    lines = ["🔎 /tara: hisseleri kendi gösterge koşullarınla filtrele (yan yana yazılan koşulların hepsi sağlanmalı).",
             "Örnekler:"] + [f"  /tara {e}" for e in EXAMPLES]
    lines += ["Karşılaştırma < > <= >=, aralık rsi 30..50, kesişim kesti_yukari(a,b) / kesti_asagi(a,b), "
              "pencere son(5, ...), ve / veya / değil ve parantez.",
              "Seçenekler: evren=bist100 (güncel üyelik)|quantbist|izleme · likidite=10 (mn TL; 0 kapalı) · "
              "sirala=alfabetik|goreli_guc|hacim|rsi",
              "Tüm alanlar: /tara_alanlar · Hazır şablonlar: /tara_sablonlar · Kayıt: /tara_kaydet AD koşullar, "
              "sonra /tara AD"]
    if saved:
        lines += ["Kayıtlı taramaların:"] + [f"  {k}: {v}" for k, v in sorted(saved.items())]
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def _live(symbols: list[str]):
    from core.market.universe import BENCHMARK
    from core.reports.daily import adjusted_bars

    return {s: adjusted_bars(s) for s in symbols}, adjusted_bars(BENCHMARK)


_HISTORY: dict = {}


def _history_data():
    """Research-period prices of every BIST 100 member since 2022 and their membership; cut at
    SCREEN_END by load_frames. Kept for the day."""

    import pandas as pd

    from core.backtest.run import load_frames
    from core.market.calendar import now_istanbul
    from core.market.membership import ever_members, membership_panel
    from core.market.universe import BENCHMARK

    key = now_istanbul().date()
    if key not in _HISTORY:
        frames = {s: df for s, df in load_frames(ever_members()).items() if not df.empty}
        index = pd.DatetimeIndex(sorted(set().union(*(df.index for df in frames.values()))))
        _HISTORY.clear()
        _HISTORY[key] = (frames, load_frames([BENCHMARK])[BENCHMARK], membership_panel(index, list(frames)))
    return _HISTORY[key]


def resolve(words: list[str], chat_id=None, saved_path=None):
    """(query, None) to scan, or (None, answer) when the answer needs no scan (guide, error)."""

    text = " ".join(words).strip()
    try:
        saved = load_saved(saved_path)
    except Exception:  # noqa: BLE001 - a damaged saved file must not stop a plain /tara
        saved = {}
    if not text:
        return None, help_text(saved)
    from core.screen.templates import TEMPLATES

    template = normalize(text) if normalize(text) in TEMPLATES else ""
    text = TEMPLATES[template].criteria if template else saved.get(normalize(text), text)
    try:
        query = parse(text)
        query.template = template
        universe.symbols(query.universe, chat_id)  # an empty watchlist is an answer, not an error
    except ScreenError as exc:
        return None, str(exc)
    return query, None


PENDING = "pending"


def finish(query, chat_id, result, trials, history, now: datetime | None = None, signal_path=None) -> str:
    """Record the matches (live measurement), keep the chat's session, write the answer.
    `history` PENDING: the card follows in its own message."""

    from core.market.calendar import now_istanbul
    from core.signals_log import log_signal

    now = now or now_istanbul()
    details = f"kriter={query.text};ozet={criterion_hash(query.text)}"
    for m in result.matches:  # every match, not only the rows shown
        log_signal(SOURCE, m.symbol, None, query.text, m.day, m.close, details=details, path=signal_path, now=now)
    pending = history == PENDING
    card = None if pending else history
    if chat_id is not None:
        SESSIONS[chat_id] = Session(result, card, trials=trials)
    text = format_result(result, card, engine.time_note(result.day, now), trials=trials)
    if pending:
        text = text.replace("📒 Geçmiş karne hesaplanamadı.",
                            "📒 Geçmiş karne hesaplanıyor; hazır olunca ayrı mesajla gelecek.")
    return text


def screen_text(words: list[str], chat_id=None, live=None, history_data=None, signal_path=None, saved_path=None,
                now: datetime | None = None, suspects=None) -> str:
    """The whole answer in one go (the bot uses resolve / screen_list / finish to send the card
    later when it takes long)."""

    from core.infrastructure.logger import get_logger

    query, answer = resolve(words, chat_id, saved_path)
    if query is None:
        return answer
    result, trials = screen_list(query, chat_id, live, suspects)
    try:
        if history_data is not None:
            data = history_data()
            history = C.history(query, *data) if data is not None else None
        else:
            history = C.cached_history(query, _history_data)
    except Exception:  # noqa: BLE001 - the list still goes out
        get_logger(__name__).exception("History card failed")
        history = None
    return finish(query, chat_id, result, trials, history, now, signal_path)


def card_later(chat_id, history) -> str:
    """The card that was still being computed when the list went out."""

    session = SESSIONS.get(chat_id)
    if session is not None:
        session.card = history
    return card_text(chat_id)


def screen_list(query, chat_id=None, live=None, suspects=None):
    """The live list and the trial count, without the history card (the bot sends the card later
    when it takes long)."""

    frames, bench = (live or _live)(universe.symbols(query.universe, chat_id))
    found = universe.suspects() if suspects is None else suspects
    result = engine.run(query, frames, bench, found)
    try:
        trials = C.record_trial(chat_id if chat_id is not None else 0, query.text)
    except Exception:  # noqa: BLE001 - the count is a warning, never a reason to fail
        trials = None
    return result, trials


__all__ = ["DISCLAIMER", "SESSIONS", "SOURCE", "card_text", "criterion_hash", "explain_text", "fields_text",
           "format_result", "has_more", "help_text", "load_saved", "more_text", "save_hint", "save_text", "screen_text"]
