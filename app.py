"""
QuantBIST RC4
Dashboard
"""

from flask import Flask
from flask import render_template

from core.dashboard.service import get_dashboard

app = Flask(__name__)


@app.route("/")
def home():

    dashboard = get_dashboard()

    return render_template(
        "dashboard.html",
        stats=dashboard["stats"],
        signals=dashboard["signals"],
    )


if __name__ == "__main__":

    app.run(
        debug=True,
        port=5000,
    )