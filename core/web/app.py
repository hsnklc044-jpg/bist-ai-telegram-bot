"""
QuantBIST
Web panel (FastAPI).

    python -m core.web.app        -> http://127.0.0.1:8000/dashboard
                                     http://127.0.0.1:8000/docs  (API belgeleri)

The page shows analysis only; the scores have no proven predictive power
(see the warning at the top of the page).
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import __version__
from core.api import get_dashboard
from core.config.paths import WEB_STATIC_DIR, WEB_TEMPLATES_DIR
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import settings

logger = get_logger(__name__)

app = FastAPI(title="QuantBIST API", version=__version__)
app.mount("/static", StaticFiles(directory=str(WEB_STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(WEB_TEMPLATES_DIR))


def portfolio_source() -> str:
    """Where the panel's portfolio comes from (ledger or the sample file)."""

    try:
        from core.portfolio.repository import load_portfolio

        return load_portfolio().attrs.get("source", "")
    except Exception:  # noqa: BLE001 - the page still renders without it
        logger.exception("Portfolio source could not be determined.")
        return ""


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health():
    return {"status": "ok", "application": settings.app_name, "version": __version__}


@app.get("/dashboard")
def dashboard(request: Request):
    logger.info("Dashboard request received.")
    try:
        data = get_dashboard()
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"dashboard": data, "portfolio_source": portfolio_source()},
        )
    except Exception as exc:
        logger.exception("Dashboard rendering failed.")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc), "type": type(exc).__name__},
        )


if __name__ == "__main__":
    import uvicorn

    logger.info("%s v%s web panel started.", settings.app_name, __version__)
    uvicorn.run("core.web.app:app", host="127.0.0.1", port=8000, reload=settings.debug)
