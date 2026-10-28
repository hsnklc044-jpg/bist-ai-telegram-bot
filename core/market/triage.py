"""
QuantBIST
Corporate action suspects with their evidence side by side, so a missing or misplaced row of
data/corporate_actions.csv is settled in minutes (DATA_CORRECTIONS, SKBNK 19.10.2026):

- the suspect: a jump in our (Yahoo) data that no row explains (core.market.quality);
- KAP: a capital increase/decrease disclosure of the same stock within 30 days;
- the second source: İş Yatırım's adjusted series on the same day. A small move there means
  the jump is a corporate action our data misses; the same jump there means a real move.

"güçlü" = both kinds of evidence: a proposed row is printed. Nothing is applied; the KAP text
is read (kap.yml detail) before a row is added.

    python -m core.market.triage --days 14
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, timedelta

KAP_WINDOW = timedelta(days=30)
LIMIT = 0.10  # BIST daily price limit: a larger move in the second source is not "adjusted away"


@dataclass
class Proposal:
    suspect: dict
    kap: list = field(default_factory=list)
    their_change: float | None = None
    problem: str = ""

    @property
    def verdict(self) -> str:
        adjusted_there = self.their_change is not None and abs(self.their_change) <= LIMIT
        return "güçlü" if self.kap and adjusted_there else "zayıf"

    def row(self) -> str | None:
        if self.verdict != "güçlü":
            return None
        s, k = self.suspect, self.kap[0]
        note = (f"otomatik öneri {today_text()} kanıtları: KAP sermaye bildirimi {k.published:%d.%m}, "
                f"İş Yatırım o gün {self.their_change * 100:+.1f}%; eklemeden önce KAP metni okunur")
        return f'{s["symbol"]},{s["date"]},factor,,,{s["suggested_factor"]},{k.link},"{note}"'


def today_text() -> str:
    from core.market.calendar import now_istanbul

    return f"{now_istanbul():%d.%m}"


def _their_change(symbol: str, day: date, fetch) -> float | None:
    frame = fetch(symbol.removesuffix(".IS"), day - timedelta(days=10), day + timedelta(days=3), retries=1)
    closes = frame["close"].dropna()
    at = closes.index.get_indexer([day.isoformat()])[0] if len(closes) else -1
    if at <= 0:
        return None
    return float(closes.iloc[at] / closes.iloc[at - 1] - 1)


def triage(suspects: list[dict], findings: list, fetch=None) -> list[Proposal]:
    if fetch is None:
        from core.market.crosscheck import fetch_isyatirim as fetch
    out = []
    for s in suspects:
        day = date.fromisoformat(s["date"])
        p = Proposal(s, [f for f in findings if f.symbol == s["symbol"] and f.kind == "sermaye"
                         and abs(f.published - day) <= KAP_WINDOW])
        try:
            p.their_change = _their_change(s["symbol"], day, fetch)
            if p.their_change is None:
                p.problem = "o gün veri yok"
        except Exception as exc:  # noqa: BLE001 - reported, the next suspect still runs
            p.problem = f"alınamadı ({type(exc).__name__})"
        out.append(p)
    return out


def format_proposals(proposals: list[Proposal]) -> str:
    if not proposals:
        return "Kurumsal işlem şüphesi incelemesi: yeni şüphe yok."
    lines = ["Kurumsal işlem şüphesi incelemesi (kanıtlar yan yana; hiçbir şey otomatik uygulanmadı):"]
    for p in proposals:
        s = p.suspect
        lines.append(f"\n{s['symbol'].removesuffix('.IS')} {s['date'][8:10]}.{s['date'][5:7]}.{s['date'][:4]} "
                     f"{s['change'] * 100:+.1f}% ({s['kind']}, çarpan önerisi {s['suggested_factor']}) → {p.verdict}")
        if p.kap:
            for k in p.kap:
                lines.append(f"  KAP {k.published:%d.%m}: {k.summary} {k.link}")
            lines.append("  KAP metni: kap.yml detail: " + ",".join(k.link.rsplit("/", 1)[-1] for k in p.kap))
        else:
            lines.append("  KAP: 30 gün içinde sermaye bildirimi yok")
        lines.append(f"  İş Yatırım: {p.problem}" if p.their_change is None
                     else f"  İş Yatırım o gün: {p.their_change * 100:+.1f}%"
                     + (" (düzeltilmiş seride küçük: bizde eksik/yanlış düzeltme)" if abs(p.their_change) <= LIMIT
                        else " (orada da büyük: gerçek hareket ya da kaynak hatası)"))
        if p.row():
            lines.append(f"  Önerilen satır: {p.row()}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market import kap, quality
    from core.market.calendar import now_istanbul
    from core.market.corrections import load_corporate_actions
    from core.market.membership import ever_members

    utf8_output()
    parser = argparse.ArgumentParser(description="Corporate action suspects with their evidence")
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args(argv)
    today = now_istanbul().date()
    actions = load_corporate_actions()
    known = {(a.symbol, a.ex_date.isoformat()) for a in actions}
    members = ever_members()
    suspects = quality.recent_suspects(quality.build_report(members),
                                       (today - timedelta(days=args.days)).isoformat(), known)
    findings = kap.check(today, members, actions, days=args.days + 30) if suspects else []
    print(format_proposals(triage(suspects, findings)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Proposal", "format_proposals", "triage"]
