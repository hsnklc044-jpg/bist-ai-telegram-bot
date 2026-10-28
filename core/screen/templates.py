"""
QuantBIST
Ready-made /tara templates: the technical part of the user's own TradingView screens (görev
28.10.2026, Aşama B). They are filter templates, not advice and not research candidates: fixed
here in code exactly as given (never tuned on results), apart from the user's saved screens.
The conditions the system has no data for are named, never imitated. Their history cards are
computed in advance (warm), so /tara and /tara_sablonlar never wait for them. Five more are the
example criteria of the /tara task (Aşama 5). Each names the research type it belongs to in
RESEARCH_LOG's "Reddedilen fikir türleri" table (tested 27.10.2026, did not beat XU100).
"""

from __future__ import annotations

from dataclasses import dataclass

from core.screen import card as C
from core.screen.language import parse

SOURCE = "kullanıcının TradingView taraması"
TASK = "/tara görev örneği (Aşama 5)"
PRO = "profesyonel filtre (Aşama 2)"
SIGNAL, TREND, MOMENTUM = "Teknik sinyal / puan", "Tek hissede trend takibi / kırılım", "Kesitsel momentum"
LOW_VOL = "Düşük oynaklık (H1)"


@dataclass(frozen=True)
class Template:
    title: str
    criteria: str
    source: str
    skipped: str  # conditions left out (no data), or "—"
    rejected: str  # the row of RESEARCH_LOG's "Reddedilen fikir türleri" it belongs to


TEMPLATES = {
    "basit_teknik": Template(
        "Basit teknik (06)", "goreli_hacim>1 kesti_yukari(rsi,50) kesti_yukari(ema5,ema20)",
        f"{SOURCE} 06, teknik kısım; kesişimler o günkü mumda", "piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak",
        SIGNAL),
    "basit_teknik_3g": Template(
        "Basit teknik, 3 gün (06 gevşek)",
        "goreli_hacim>1 son(3,kesti_yukari(rsi,50)) son(3,kesti_yukari(ema5,ema20))",
        f"{SOURCE} 06, kesişimler son 3 seansta", "piyasa değeri, gelir artışı, ÖGO, borç/öz kaynak", SIGNAL),
    "bebek_teknik": Template(
        "Bebek hisse, teknik kısım (08)", "goreli_hacim>1 momentum10>0",
        f"{SOURCE} 08", "piyasa değeri 1–2 milyar TL, FSO < 1", SIGNAL),
    "duseni_kiran": Template(
        "Düşeni kıran (10)",
        "kapanis<zirve_1a rsi 50..70 goreli_hacim>1.5 ema5>ema10 ema10>ema20 ema20>ema40 ema50>ema100 "
        "ema100>ema200 vwma20<kapanis degisim_1h<15 degisim_1a<20 cci>-100 kapanis>acilis",
        f"{SOURCE} 10 (ve 3, aynı EMA dizilimi)", "—", TREND),
    "tek_tus_trend": Template(
        "Tek tuş trend, teknik kısım",
        "kapanis>ema50 ema50>ema200 rsi 60..70 adx>20 ortalama_hacim_30g>10000000 degisim_1a<30 ema20<kapanis "
        "degisim_3a<60",
        f"{SOURCE} BIST TEK TUŞ TREND",
        "piyasa değeri > 10 milyar TL; beta 0,8–1,5 (fiyattan hesaplanır, `beta` alanı var; şablon görevdeki "
        "tanımla bırakıldı)", TREND),
    "teknik_temel_ema": Template(
        "Teknik-temel, EMA kısmı (05)", "kapanis>ema50 ema50>ema200",
        f"{SOURCE} 05", "piyasa değeri > 2 milyar TL, gelir artışı (çeyreklik/yıllık), ÖGO, borç/öz kaynak", TREND),
    "trend_takibi": Template("Trend takibi", "ema20>ema50 ema50>ema200 adx>20", TASK, "—", TREND),
    "asiri_satim": Template("Aşırı satım, uzun trend üstünde", "rsi<30 kapanis>ema200", TASK, "—", SIGNAL),
    "kirilim": Template("20 gün kırılımı, hacimli", "kapanis>yuksek_20g hacim_oran>1.5", TASK, "—", TREND),
    "sikisma": Template("Bollinger sıkışması (6 ayın en dar %10'u)", "bb_genislik_yuzdelik<10", TASK, "—", TREND),
    "goreli_guc": Template("Göreli güç, BIST 100'ün üst %20'si (60 seans)", "gg_sira>80", TASK, "—", MOMENTUM),
    # profesyonel filtreler Aşama 2 (K-47): fixed as the task gave them; sources are practitioners or papers,
    # none of them is evidence for BIST (the cards say what this market's past shows)
    "minervini": Template(
        "Minervini trend şablonu",
        "kapanis>sma150 kapanis>sma200 sma150>sma200 egim(sma200,21)>0 sma50>sma150 kapanis>sma50 "
        "dip_52h_oran>=130 zirve_52h_oran>=75 goreli_guc_yuzdelik>=70",
        f"{PRO}: Minervini (2013), Trend Template; pratisyen kuralı, akademik kanıtı sınırlı. "
        "goreli_guc_yuzdelik IBD 'RS rating' yaklaşımıdır", "—", TREND),
    "zirveye_yakin": Template(
        "52 hafta zirvesine yakın", "zirve_52h_oran>=95",
        f"{PRO}: George & Hwang (2004), 52 hafta zirvesi ve momentum", "—", MOMENTUM),
    "goreli_guc_ust": Template(
        "6-1 momentum, evrenin üst %20'si", "momentum_sira>=80",
        f"{PRO}: Jegadeesh & Titman (1993), 6 ay getirisi, son 1 ay hariç. Bu sistemde kesitsel momentum "
        "reddedildi (2025 +%88, 2026 −%73; RESEARCH_LOG)", "—", MOMENTUM),
    "dusuk_oynaklik": Template(
        "Düşük oynaklık, evrenin en sakin %20'si", "oynaklik_sira<=20",
        f"{PRO}: Ang, Hodrick, Xing & Zhang (2006); Blitz & van Vliet (2007). Bu sistemde H1 düşük oynaklık "
        "reddedildi (+%0,9 [−16,5; +18,6]; RESEARCH_LOG)", "—", LOW_VOL),
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
            shown = s.day_mean if s.day_mean is not None else s.mean
            base = f", tüm hisseler {pct(s.base)}" if s.base is not None else ""
            parts.append(f"{h} seans {pct(shown)}{interval}{base}, {s.n} örnek → {s.label}")
    return "karne: " + "; ".join(parts)


def list_text(cards: dict | None = None) -> str:
    """/tara_sablonlar; cards come from the cache only (never computed here)."""

    from core.screen.command import DISCLAIMER

    lines = ["🧩 Hazır şablonlar (TradingView taramalarının teknik kısmı ve görev örnekleri; filtre şablonu, öneri değil). "
             "Çalıştırmak: /tara AD"]
    for name, t in TEMPLATES.items():
        stats = cards.get(name) if cards is not None else C.peek(parse(t.criteria))
        lines += [f"\n{t.title} · /tara {name}", f"  {t.criteria}", f"  kaynak: {t.source}",
                  f"  atlanan (veri yok): {t.skipped}", f"  {_card_line(stats)}",
                  f"  tür: {t.rejected}; bu tür 27.10.2026'da test edildi, XU100'ü geçmedi "
                  "(RESEARCH_LOG, Reddedilen fikir türleri)"]
    lines.append("\nKarneler geçmişin özetidir (maliyet dahil); şablonlar sonuçlara bakılarak ayarlanmaz ve "
                 "araştırma programına aday kural değildir.")
    lines.append(DISCLAIMER)
    return "\n".join(lines)


def warm(load=None) -> None:
    """Compute (or read back) every template's card; run in the background."""

    from core.screen import command

    for t in TEMPLATES.values():
        C.cached_history(parse(t.criteria), load or command._history_data)


def _skipped_line(command) -> list[str]:
    skipped = command.history_skipped()
    if not skipped:
        return []
    reasons = command.history_skip_reasons()
    return [f"Dışarıda (araştırmadaki gibi; çözülmemiş ±%20 sıçrama ya da kısa geçmiş): {len(skipped)} hisse: "
            + ", ".join(s.removesuffix(".IS") + (f" ({reasons[s]})" if s in reasons else "") for s in skipped)]


def cards_text(load=None) -> str:
    """Every template's full card on real data (the weekly research run prints it)."""

    from core.screen import command

    lines = [f"/tara şablon karneleri ({C.HISTORY_START} – 30.10.2026, o günkü BIST 100 üyeleri, ertesi açılış, "
             "maliyet dahil; keşif, araştırma programı dışında)"]
    data = (load or command._history_data)()
    lines += _skipped_line(command)
    for name, t in TEMPLATES.items():
        stats = C.history(parse(t.criteria), *data)
        lines += [f"\n{name}: {t.criteria}", *command.card_lines(stats)[1:-1]]
    return "\n".join(lines)


def variants(criteria: str) -> list[tuple[str, str]]:
    """The same template under each definition that can differ from the user's own PC test."""

    out = [("şablon (varsayılan elemelerle)", criteria), ("ele=hayir", f"{criteria} ele=hayir")]
    if "goreli_hacim" in criteria:
        out.append(("20 günlük hacim (hacim_oran)", criteria.replace("goreli_hacim", "hacim_oran")))
        out.append(("20 günlük hacim, ele=hayir", criteria.replace("goreli_hacim", "hacim_oran") + " ele=hayir"))
    return out


def elimination_lines(data, horizon: int, pct) -> list[str]:
    """The eliminated and the kept stock-days, event mean before costs (K-45): kept from the card of
    'every stock' with the default eliminations, eliminated as the rest of the same events."""

    every = C.history(parse("kapanis>0 ele=hayir"), *data, horizons=(horizon,))[horizon]
    kept = C.history(parse("kapanis>0"), *data, horizons=(horizon,))[horizon]
    out = [f"\nEleme grupları ({horizon} seans, olay ortalaması maliyet hariç; aralıksız):",
           f"  kalan: {kept.n} · {pct(kept.gross)}"]
    gone = every.n - kept.n
    if gone > 0 and every.gross is not None and kept.gross is not None:
        out.append(f"  elenen: {gone} · {pct((every.gross * every.n - kept.gross * kept.n) / gone)}")
    return out


def explain_text(load=None, horizon: int = 20) -> str:
    """Why the cards differ from the user's numbers (RESEARCH_LOG): each variant's samples, the
    event mean with and without costs, the day mean. Explains, never selects (K-38)."""

    from core.screen import command

    def pct(x):
        return "—" if x is None else f"{x * 100:+.1f}%".replace(".", ",")

    lines = [f"/tara şablon farkları, {horizon} seans ({C.HISTORY_START} – 30.10.2026). Yalnız açıklama içindir; "
             "seçim için kullanılmaz, şablonlar değişmez.",
             "sütunlar: örnek · olay ortalaması maliyet hariç · maliyet dahil · gün ortalaması (maliyet dahil) · "
             "tüm hisseler (gün ortalaması)"]
    data = (load or command._history_data)()
    lines += _skipped_line(command)
    lines += elimination_lines(data, horizon, pct)
    for name, t in TEMPLATES.items():
        lines.append(f"\n{name}:")
        for label, criteria in variants(t.criteria):
            s = C.history(parse(criteria), *data, horizons=(horizon,))[horizon]
            lines.append(f"  {label}: {s.n} · {pct(s.gross)} · {pct(s.mean)} · {pct(s.day_mean)} · {pct(s.base)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output

    utf8_output()
    print(explain_text() if "--explain" in (argv or []) else cards_text())
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))


__all__ = ["TEMPLATES", "Template", "cards_text", "explain_text", "list_text", "main", "variants", "warm"]
