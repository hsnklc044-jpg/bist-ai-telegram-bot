"""K-64 hourly: separate the rule effect (K-75) from the window effect (descriptive only).

    python scripts/k64_split.py download FILE        # freeze one hourly snapshot (pickle) and print its range
    python scripts/k64_split.py evaluate FILE         # run THIS checkout's K-64 hourly evaluation on it

The workflow k64-split.yml runs `evaluate` on the same frozen file from two checkouts: the code before
K-75 (v0.99.72) and after (v0.99.74). Nothing is tuned; the decision rule of K-64 is not touched.
"""

from __future__ import annotations

import pickle
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    action, path = argv[0], Path(argv[1])
    if action == "download":
        from core.market.hourly import load_hourly

        frames = load_hourly().frames
        path.write_bytes(pickle.dumps(frames))
        first = min(df.index[0] for df in frames.values() if len(df))
        last = max(df.index[-1] for df in frames.values() if len(df))
        print(f"dondurulan veri: {len(frames)} hisse, {sum(len(df) for df in frames.values())} mum, {first} – {last}")
        return 0
    from core.backtest.run import HOLDOUT_START
    from core.ml.signal_filter import SPEC, evaluate, events, text

    frames = pickle.loads(path.read_bytes())
    x, y = SPEC["saatlik"]
    report = evaluate(events(frames, x, y, None, HOLDOUT_START.tz_localize("Europe/Istanbul")), "saatlik")
    print(text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
