"""
QuantBIST
Ready-made /tara templates: the technical part of the user's own TradingView screens (görev
28.10.2026, Aşama B). They are filter templates, not advice and not research candidates: fixed
here in code exactly as given (never tuned on results), apart from the user's saved screens.
The conditions the system has no data for are named, never imitated. Their history cards are
computed in advance (warm), so /tara and /tara_sablonlar never wait for them.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.screen import card as C
from core.screen.language import parse

SOURCE = "kullanıcının TradingView taraması"


@dataclass(frozen=True)
class Template:
    title: str
    criteria: str
    source: str
    skipped: str  # conditions left out (no data), or "—"


TEMPLATES = {
    "basit_teknik": Template(
        "Basit teknik (06)", "goreli_hacim>1 kesti_yukari(rsi,50) kesti_yukari(ema5,ema20)",
        f"{SOURCE} 06, teknik kısım; kesişimler o günkü mumda", "piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak"),
    "basit_teknik_3g": Template(
        "Basit teknik, 3 gün (06 gevşek)",
        "goreli_hacim>1 son(3,kesti_yukari(rsi,50)) son(3,kesti_yukari(ema5,ema20))",
        f"{SOURCE} 06, kesişimler son 3 seansta", "piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak"),
    "bebek_teknik": Template(
        "Bebek hisse, teknik kısım (08)", "goreli_hacim>1 momentum10>0",
        f"{SOURCE} 08", "piyasa değeri 1–2 milyar TL, FSO < 1"),
    "duseni_kiran": Template(
        "Düşeni kıran (10)",
        "kapanis<zirve_1a rsi 50..70 goreli_hacim>1.5 ema5>ema10 ema10>ema20 ema20>ema40 ema50>ema100 "
        "ema100>ema200 vwma20<kapanis degisim_1h<15 degisim_1a<20 cci>-100 kapanis>acilis",
        f"{SOURCE} 10 (ve 3, aynı EMA dizilimi)", "—"),
    "tek_tus_trend": Template(
        "Tek tuş trend, teknik kısım",
        "kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ortalama_hacim_30g>10000000 degisim_1a<30 ema20<kapanis "
        "degisim_3a<60",
        f"{SOURCE} BIST TEK TUŞ TREND", "piyasa değeri > 10 milyar TL, beta 0,8–1,5"),
    "teknik_temel_ema": Template(
        "Teknik-temel, EMA kısmı (05)", "kapanis>ema50 ema50>ema200",
        f"{SOURCE} 05", "piyasa değeri > 2 milyar TL, gelir artışı (çeyreklik/yıllık), ÖGO, borç/öz kaynak"),
}


def _card_line(stats: dict | None) -> str:
    from core.reports.daily import pct

    if stats is None:
        return "karne hazırlanıyor"
    parts = []
    for h in sorted(stats):
        s = stats[h]
        if s.n < C.MIN_SAMPLES or s.mean is None:
            parts.append(f"{h} seans yetersiz örnek ({s.n})")
        else:
            interval = f" [{pct(s.low)}, {pct(s.high)}]" if s.low is not None else ""
            parts.append(f"{h} seans {pct(s.mean)}{interval}, {s.n} örnek → {s.label}")
    return "karne: " + "; ".join(parts)


def list_text(cards: dict | None = None) -> str:
    """/tara_sablonlar; cards come from the cache only (never computed here)."""

    from core.screen.command import DISCLAIMER

    lines = ["🧩 Hazır şablonlar (kullanıcının TradingView taramalarının teknik kısmı; filtre şablonu, öneri değil). "
             "Çalıştırmak: /tara AD"]
    for name, t in TEMPLATES.items():
        stats = cards.get(name) if cards is not None else C.peek(parse(t.criteria))
        lines += [f"\n{t.title} · /tara {name}", f"  {t.criteria}", f"  kaynak: {t.source}",
                  f"  atlanan (veri yok): {t.skipped}", f"  {_card_line(stats)}"]
    lines.append("\nKarneler geçmişin özetidir (maliyet dahil); şablonlar sonuçlara bakılarak ayarlanmaz ve "
                 "araştırma programına aday kural değildir.")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def warm(load=None) -> None:
    """Compute (or read back) every template's card; run in the background."""

    from core.screen import command

    for t in TEMPLATES.values():
        C.cached_history(parse(t.criteria), load or command._history_data)


def cards_text(load=None) -> str:
    """Every template's full card on real data (the weekly research run prints it)."""

    from core.screen import command

    lines = [f"/tara şablon karneleri ({C.HISTORY_START} – 30.10.2026, o günkü BIST 100 üyeleri, ertesi açılış, "
             "maliyet dahil; keşif, araştırma programı dışında)"]
    data = (load or command._history_data)()
    for name, t in TEMPLATES.items():
        stats = C.history(parse(t.criteria), *data)
        lines += [f"\n{name}: {t.criteria}", *command.card_lines(stats)[1:-1]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    print(cards_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["TEMPLATES", "Template", "cards_text", "list_text", "main", "warm"]
