"""
QuantBIST
Research history: every weekly research table, kept and compared.

    python -m core.backtest.research --records history.csv   # append this run
    python -m core.backtest.history history.csv              # this run vs the previous one

The GitHub workflow keeps history.csv and the full text reports on the
`research-results` branch, so results outlive the 90-day Actions logs.

Looking at the same strategies every week is itself repeated testing:
a single week that comes out "significant" is not evidence. The
comparison therefore also shows in how many runs each strategy was
significant.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

import pandas as pd

from core.market.calendar import now_istanbul

FIELDS = (
    "run_date", "universe", "period_start", "period_end", "strategy", "cagr", "max_drawdown",
    "sharpe", "trades", "excess", "excess_low", "excess_high", "level", "verdict",
)
SIGNIFICANT = "XU100'den anlamlı yüksek"
UNIVERSE_NAMES = {"pit": "geçmiş üyelik", "today": "bugünkü liste"}


def _cell(value) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def append_records(records: list[dict], path: Path | str, run_date: str | None = None) -> int:
    path = Path(path)
    run_date = run_date or now_istanbul().strftime("%Y-%m-%d %H:%M")
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()

    with open(path, "a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, FIELDS, lineterminator="\n")
        if new:
            writer.writeheader()
        for record in records:
            writer.writerow({k: _cell({**record, "run_date": run_date}.get(k)) for k in FIELDS})

    return len(records)


def _pct(x) -> str:
    return "-" if x is None or pd.isna(x) else f"{x * 100:+.1f}%"


def compare(path: Path | str) -> str:
    path = Path(path)
    if not path.exists():
        return "Araştırma geçmişi yok."

    df = pd.read_csv(path)
    runs = sorted(df["run_date"].unique())
    last = df[df["run_date"] == runs[-1]]
    previous = df[df["run_date"] == runs[-2]] if len(runs) > 1 else df.iloc[0:0]

    lines = [f"Araştırma geçmişi: {len(runs)} çalışma, son {runs[-1]}" + (f", önceki {runs[-2]}" if len(runs) > 1 else "")]
    if previous.empty:
        lines.append("İlk kayıt; karşılaştırma bir sonraki çalışmada.")

    tested = df[df["verdict"].notna() & (df["verdict"] != "")]
    for universe, part in last.groupby("universe", sort=False):
        lines += ["", f"[{UNIVERSE_NAMES.get(universe, universe)}] dönem {part['period_start'].iloc[0]} – {part['period_end'].iloc[0]}"]
        for _, row in part.iterrows():
            before = previous[(previous["universe"] == universe) & (previous["strategy"] == row["strategy"])]
            change = ""
            if not before.empty:
                b = before.iloc[0]
                change = f" (önceki {_pct(b['cagr'])})"
                if isinstance(b["verdict"], str) and isinstance(row["verdict"], str) and b["verdict"] != row["verdict"]:
                    change += f" ⚠️ karar değişti: {b['verdict']} → {row['verdict']}"
            verdict = row["verdict"] if isinstance(row["verdict"], str) else ""
            history = tested[(tested["universe"] == universe) & (tested["strategy"] == row["strategy"])]
            count = f"; anlamlı yüksek {int((history['verdict'] == SIGNIFICANT).sum())}/{len(history)} çalışmada" if verdict else ""
            lines.append(f"  {row['strategy']}: yıllık {_pct(row['cagr'])}{change}" + (f" | {verdict}{count}" if verdict else ""))

    lines += [
        "",
        "Not: aynı stratejilere her hafta bakmak da çoklu denemedir; tek bir haftanın 'anlamlı' "
        "sonucu kanıt sayılmaz, sürekliliğine bakılır.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compare the latest research run with the previous one.")
    parser.add_argument("history", help="history.csv written by core.backtest.research --records")
    args = parser.parse_args(argv)
    print(compare(args.history))


if __name__ == "__main__":
    main()


__all__ = ["append_records", "compare"]
