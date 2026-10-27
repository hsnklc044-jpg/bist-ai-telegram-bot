"""
QuantBIST
KAP (Kamuyu Aydınlatma Platformu) disclosures: corporate actions (bonus/rights issues,
splits, dividends) announced for our stocks, to be checked against data/corporate_actions.csv.

KAP has no official API; these are the public endpoints its own web site calls (the same ones
community tools use). They are reached from GitHub's servers (this sandbox cannot reach KAP).

    python -m core.market.kap --probe      # what the endpoints return now (shape only, step 1)

Nothing here changes prices or corporate_actions.csv; a person confirms every row.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from core.infrastructure.logger import get_logger

logger = get_logger(__name__)

BASE = "https://www.kap.org.tr/tr/api"
HEADERS = {"User-Agent": "Mozilla/5.0 (QuantBIST corporate action check)", "Accept": "application/json"}
TIMEOUT = 30
CLASSES = ("ODA", "DG")  # özel durum açıklamaları, diğer: capital increases and dividends are among these


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
                lines.append(f"  alanlar: {sorted(items[0])}")
                lines += [f"  {json.dumps(item, ensure_ascii=False)[:400]}" for item in items[:3]]
        except Exception as exc:  # noqa: BLE001
            lines.append(f"[{cls}] bildirimler alınamadı: {type(exc).__name__}: {exc}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    from core.infrastructure.console import utf8_output
    from core.market.calendar import now_istanbul

    utf8_output()
    parser = argparse.ArgumentParser(description="KAP corporate action disclosures")
    parser.add_argument("--probe", action="store_true", help="show what the KAP endpoints return now")
    args = parser.parse_args(argv)
    if args.probe:
        print(probe(now_istanbul().date()))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["disclosures", "probe", "subjects"]
