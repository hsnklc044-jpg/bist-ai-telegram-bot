"""
QuantBIST
The live ML filter (K-59): used only after the out-of-sample evaluation passed
(core.ml.ml_filter.enabled). The model is refitted on every row whose label was already known
and saved to logs/ml_model.joblib; each day's probabilities use features up to that day's close.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from core.config.paths import LOG_DIR
from core.ml.features import FEATURES, dataset, features

MODEL_FILE = LOG_DIR / "ml_model.joblib"


def fit(frames: dict[str, pd.DataFrame], members=None, today: date | None = None, path: Path | None = None,
        make_model=None) -> int:
    """Train on every row whose label was known before `today`; returns the number of rows."""

    import joblib

    from core.ml.ml_filter import model

    data = dataset(frames, members)
    if today is not None:
        data = data[data["label_end"] < pd.Timestamp(today)]
    if data.empty or data["label"].nunique() < 2:
        return 0
    m = (make_model or model)()
    m.fit(data[list(FEATURES)].to_numpy(), data["label"].to_numpy(dtype=int))
    path = Path(path or MODEL_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": m, "rows": len(data), "trained": str(today)}, path)
    return len(data)


def probabilities(frames: dict[str, pd.DataFrame], path: Path | None = None) -> dict[str, float]:
    """The model's probability for each stock's latest close; stocks without full features are left out."""

    import joblib

    path = Path(path or MODEL_FILE)
    if not path.exists():
        return {}
    m = joblib.load(path)["model"]
    rows = {}
    for symbol, df in frames.items():
        if df is None or len(df) < 250:
            continue
        last = features(df).iloc[[-1]][list(FEATURES)]
        if not last.isna().any(axis=None):
            rows[symbol] = last
    if not rows:
        return {}
    x = pd.concat(rows.values())
    proba = m.predict_proba(x.to_numpy())[:, 1]
    return dict(zip(rows, proba.astype(float).tolist(), strict=True))


__all__ = ["MODEL_FILE", "fit", "probabilities"]
