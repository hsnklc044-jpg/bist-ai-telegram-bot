"""
QuantBIST RC4
Application Entry Point
"""

from __future__ import annotations

from flask import Flask
from flask import render_template

from core.dashboard.service import (
    get_dashboard,
)

from core.infrastructure.logger import (
    get_logger,
)

logger = get_logger(__name__)

app = Flask(__name__)


@app.route("/")
def dashboard():

    logger.info(
        "Dashboard requested."
    )

    data = get_dashboard()

    return render_template(

        "dashboard.html",

        dashboard=data,

    )


@app.route("/health")
def health():

    return {

        "status": "OK",

        "application": "QuantBIST RC4",

    }


if __name__ == "__main__":

    logger.info(
        "QuantBIST RC4 started."
    )

    app.run(

        host="127.0.0.1",

        port=5000,

        debug=True,

    )