"""
QuantBIST RC7
FastAPI Application
"""

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder

from core.api import (
    get_dashboard,
    get_decision,
    get_report,
)

app = FastAPI(
    title="QuantBIST API",
    description="QuantBIST Portfolio Intelligence API",
    version="7.0.0",
)


@app.get("/")
def root():
    return {
        "name": "QuantBIST",
        "version": "RC7",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.get("/dashboard")
def dashboard():
    """
    Complete dashboard.
    """
    dashboard_model = get_dashboard()
    return jsonable_encoder(dashboard_model)


@app.get("/decision")
def decision():
    """
    Latest investment decision.
    """
    decision_model = get_decision()
    return jsonable_encoder(decision_model)


@app.get("/report")
def report():
    """
    Complete analysis report.
    """
    report_model = get_report()
    return jsonable_encoder(report_model)