"""
QuantBIST RC4
Dashboard Charts
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DATA_FILE = Path("data/equity_curve.csv")
OUTPUT_FILE = Path("static/equity_curve.png")


def generate_equity_curve():

    if not DATA_FILE.exists():
        return

    df = pd.read_csv(DATA_FILE)

    if df.empty:
        return

    equity = df["equity"]

    plt.figure(figsize=(10, 4))

    plt.plot(
        equity,
        linewidth=3,
    )

    plt.title("Equity Curve")

    plt.grid(True)

    plt.tight_layout()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT_FILE,
        dpi=150,
    )

    plt.close()