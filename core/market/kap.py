"""
QuantBIST
KAP (Kamuyu Aydınlatma Platformu) disclosures: corporate actions (bonus/rights issues,
splits, dividends) announced for our stocks, to be checked against data/corporate_actions.csv.

KAP has no official API; these are the public endpoints its own web site calls (the same ones
community tools use). They are reached from GitHub's servers (this sandbox cannot reach KAP).

    python -m core.market.kap --probe      # what the endpoints return now (shape only)
    python -m core.market.kap --days 14    # capital actions and dividends for our stocks
    python -m core.market.kap --detail 1685136,1684593   # a disclosure's own text

Nothing here changes prices or corporate_actions.csv; a person confirms every row.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

BASE = "https://www.kap.org.tr/tr/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (QuantBIST corporate action check)", "Accept": "application/json"}
TIMEOUT = 30
CLASSES = ("ODA", "DG")
# subject names as KAP returns them (probe 27.10.2026, research-results kap/probe_2026-10-27_23-34-05.txt)
KINDS = {
    "Sermaye Artırımı - Azaltımı İşlemlerine İlişkin Bildirim": "sermaye",
    "Kar Payı Dağıtım İşlemlerine İlişkin Bildirim": "temettü",
}
RECORDED_BEFORE = timedelta(days=30)  # a corporate_actions.csv row this close to the announcement covers it
RECORDED_AFTER = timedelta(days=180)  # ... or after it: the ex-date comes weeks or months later
CHUNK = 7  # days per request (a week is ~1,200 disclosures)
# a private placement (tahsisli) gives existing holders no rights: the price needs no adjustment
NO_ADJUSTMENT_WORDS = ("tahsisli",)


@dataclass(frozen=True)
class Finding:
    symbol: str
    kind: str  # sermaye | temettü
    published: date
    summary: str
    link: str
    recorded: bool  # sermaye: a row in corporate_actions.csv near this date; temettü: always False


def _published(text: str) -> date:
    return datetime.strptime(text.split()[0], "%d.%m.%Y").date()


def check(today: date, universe: list[str], actions: list, days: int = 14, post=None,
          problems: list[str] | None = None) -> list[Finding]:
    """KAP corporate actions and dividends for `universe` in the last `days` days, oldest first.
    Answers that could not be read are skipped and, when `problems` is given, described there."""

    ours = {s.removesuffix(".IS") for s in universe}
    found: dict[tuple, Finding] = {}
    start = today - timedelta(days=days - 1)
    while start <= today:
        end = min(start + timedelta(days=CHUNK - 1), today)
        answer = disclosures(start, end, "ODA", post=post)
        if not isinstance(answer, list):  # an error object instead of the list: skip this week, keep the rest
            logger.warning("KAP answered %s for %s..%s", type(answer).__name__, start, end)
            if problems is not None:
                problems.append(f"{start:%d.%m}–{end:%d.%m} arası okunamadı (KAP cevabı liste değil)")
            answer = []
        for item in answer:
            kind = KINDS.get((str(item.get("subject") or "")).strip()) if isinstance(item, dict) else None
            if not kind:
                continue
            try:
                published = _published(str(item.get("publishDate")))
            except ValueError:
                logger.warning("KAP date not understood: %r", item.get("publishDate"))
                if problems is not None:
                    problems.append(f"tarihi anlaşılmayan bildirim atlandı: {item.get('disclosureIndex')}")
                continue
            for code in str(item.get("stockCodes") or "").replace(" ", "").split(","):
                if code not in ours:
                    continue
                symbol = f"{code}.IS"
                summary = (item.get("summary") or "").strip()
                no_adjustment = any(w in summary.casefold() for w in NO_ADJUSTMENT_WORDS)
                recorded = kind == "sermaye" and (no_adjustment or any(
                    a.symbol == symbol and published - RECORDED_BEFORE <= a.ex_date <= published + RECORDED_AFTER
                    for a in actions))
                key = (symbol, kind, item.get("disclosureIndex"))
                found[key] = Finding(symbol, kind, published, summary[:120],
                                     f"https://www.kap.org.tr/tr/Bildirim/{item.get('disclosureIndex')}", recorded)
        start = end + timedelta(days=1)
    return sorted(found.values(), key=lambda f: (f.published, f.symbol))


def format_findings(found: list[Finding], today: date, days: int, problems: list[str] | None = None) -> str:
    head = f"KAP kurumsal işlem bildirimleri, son {days} gün ({today:%d.%m.%Y}); hiçbir şey kendiliğinden uygulanmaz."
    if problems:
        head += "\n⚠️ Eksik kontrol: " + "; ".join(problems)
    if not found:
        return head + "\nEvrendeki hisseler için sermaye artırımı/azaltımı ya da kâr payı bildirim yok."
    lines = [head]
    capital = [f for f in found if f.kind == "sermaye"]
    if capital:
        lines.append("\nSermaye artırımı / azaltımı (bedelsiz, bedelli, bölünme):")
        for f in capital:
            no_adjustment = any(w in f.summary.casefold() for w in NO_ADJUSTMENT_WORDS)
            mark = "tahsisli: fiyat düzeltme gerekmez" if no_adjustment else "kayıtlı" if f.recorded else "⚠️ corporate_actions.csv'de yok: KAP'ta doğrula, hak kullanım günü eklenecek"
            lines.append(f"  {f.symbol.removesuffix('.IS')} {f.published:%d.%m} – {f.summary} – {mark}")
            lines.append(f"    {f.link}")
    dividends = [f for f in found if f.kind == "temettü"]
    if dividends:
        lines.append("\nKâr payı (temettü; fiyat düzeltmesini Yahoo yapar, elinde varsa deftere temettü işlenir):")
        for f in dividends:
            lines.append(f"  {f.symbol.removesuffix('.IS')} {f.published:%d.%m} – {f.summary}")
            lines.append(f"    {f.link}")
    return "\n".join(lines)


def _criteria(start: date, end: date, disclosure_class: str, subjects: list[str] | None = None) -> dict:
    return {
        "fromDate": start.isoformat(), "toDate": end.isoformat(), "memberType": "", "mkkMemberOidList": [],
        "inactiveMkkMemberOidList": [], "disclosureClass": disclosure_class, "subjectList": list(subjects or []),
        "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOid": "", "index": "",
        "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
        "fromSrc": False, "srcCategory": "", "disclosureIndexList": [],
    }


def subjects(disclosure_class: str, get=None) -> list:
    get = get or _http("get")
    return get(f"{BASE}/disclosure/subjects/{disclosure_class}/IGS")


def disclosures(start: date, end: date, disclosure_class: str, subject_oids=None, post=None) -> list:
    post = post or _http("post")
    return post(f"{BASE}/disclosure/members/byCriteria", _criteria(start, end, disclosure_class, subject_oids))


def _http(method: str):
    import requests

    def call(url, body=None):
        if method == "get":
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        else:
            response = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    return call


def _page(url: str) -> bytes:
    import requests

    response = requests.get(url, headers={**HEADERS, "Accept": "text/html"}, timeout=TIMEOUT)
    response.raise_for_status()
    return response.content


def detail(index: int, get=None) -> str:
    """The text of one disclosure (its web page, scripts removed) plus any data embedded in the
    page, so a corporate action's dates are read from KAP itself. A person still decides."""

    from bs4 import BeautifulSoup

    url = f"https://www.kap.org.tr/tr/Bildirim/{index}"
    try:
        soup = BeautifulSoup((get or _page)(url), "lxml")
    except Exception as exc:  # noqa: BLE001 - reported, the next index still runs
        return f"KAP bildirimi {index} alınamadı: {type(exc).__name__}: {exc}"
    embedded = [s.get_text() for s in soup.find_all("script", type="application/json")]
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    start = text.find("Gönderim Tarihi")  # the site's menus come first (first run, 28.10.2026)
    lines = [f"KAP bildirimi {index} ({url})", text[max(start, 0):][:12000]]
    lines += [f"[sayfadaki veri] {e[:6000]}" for e in embedded if e.strip()]
    return "\n".join(lines)


def probe(today: date, get=None, post=None) -> str:
    """Step 1: the shape of today's answers, so the parser is written against facts, not guesses."""

    lines = [f"KAP uç nokta denemesi {today:%d.%m.%Y}"]
    for cls in CLASSES:
        try:
            found = subjects(cls, get=get)
            lines.append(f"\n[{cls}] konu sayısı: {len(found)}")
            lines += [f"  {json.dumps(item, ensure_ascii=False)[:300]}" for item in found]
        except Exception as exc:  # noqa: BLE001 - a probe reports every failure and goes on
            lines.append(f"\n[{cls}] konular alınamadı: {type(exc).__name__}: {exc}")
        try:
            items = disclosures(today - timedelta(days=7), today, cls, post=post)
            lines.append(f"[{cls}] son 7 gün bildirim sayısı (tüm şirketler): {len(items)}")
            if items:
                from collections import Counter

                lines.append(f"  alanlar: {sorted(items[0])}")
                lines += [f"  {json.dumps(item, ensure_ascii=False)[:400]}" for item in items[:3]]
                lines.append(f"[{cls}] konu dağılımı (subject: adet):")
                lines += [f"  {n:4d}  {s}" for s, n in Counter(i.get("subject") for i in items).most_common(80)]
                codes = [i.get("stockCodes") for i in items if i.get("stockCodes")][:15]
                lines.append(f"[{cls}] stockCodes örnekleri: {codes}")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"[{cls}] bildirimler alınamadı: {type(exc).__name__}: {exc}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market.calendar import now_istanbul

    utf8_output()
    parser = argparse.ArgumentParser(description="KAP corporate action disclosures")
    parser.add_argument("--probe", action="store_true", help="show what the KAP endpoints return now")
    parser.add_argument("--days", type=int, default=None, help="check the last N days against corporate_actions.csv")
    parser.add_argument("--detail", default=None, help="disclosure numbers, comma separated: their text")
    args = parser.parse_args(argv)
    if args.detail:
        for index in args.detail.replace(" ", "").split(","):
            print(detail(int(index)) + "\n")
        return 0
    today = now_istanbul().date()
    if args.probe:
        print(probe(today))
        return 0
    if args.days:
        from core.market.corrections import load_corporate_actions
        from core.market.universe import load_universe

        problems: list[str] = []
        found = check(today, load_universe(), load_corporate_actions(), days=args.days, problems=problems)
        print(format_findings(found, today, args.days, problems))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["Finding", "check", "detail", "disclosures", "format_findings", "probe", "subjects"]
