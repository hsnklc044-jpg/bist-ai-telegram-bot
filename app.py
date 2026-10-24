"""
QuantBIST
Web dashboard (Flask).

    python app.py
"""

from __future__ import annotations

from flask import Flask, render_template

from core.dashboard.service import (
    get_dashboard,
)
from core.infrastructure.exceptions import DashboardError
from core.infrastructure.logger import (
    get_logger,
)
from core.infrastructure.settings import settings

logger = get_logger(__name__)


app = Flask(__name__)


@app.route("/")
def dashboard():

    logger.info(
        "Dashboard requested."
    )

    try:
        data = get_dashboard()
    except DashboardError:
        return (
            "Panel hazırlanamadı: fiyat verisi yok. "
            "python -m core.market.update çalıştırıp sayfayı yenileyin.",
            503,
        )

    return render_template(

        "dashboard.html",

        dashboard=data,

    )


@app.route("/health")
def health():

    return {

        "status": "OK",

        "application": settings.app_name,

        "version": settings.version,

    }


if __name__ == "__main__":

    logger.info(
        "%s v%s web dashboard started.",
        settings.app_name,
        settings.version,
    )

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=settings.debug,

    )