"""
QuantBIST
Web panel (FastAPI).

    python -m core.web.app        -> http://127.0.0.1:8000/dashboard
                                     http://127.0.0.1:8000/docs  (API belgeleri)

The page shows the same read-only overview as /summary: market state,
both accounts and the open risk alerts. No buy/sell call: no tested rule
has shown predictive power.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from core import __version__
from core.config.paths import WEB_TEMPLATES_DIR
from core.infrastructure.logger import get_logger
from core.infrastructure.settings import settings
from core.reports.daily import DISCLAIMER
from core.reports.overview import build_overview

logger = get_logger(__name__)

app = FastAPI(title="QuantBIST API", version=__version__)
templates = Jinja2Templates(directory=str(WEB_TEMPLATES_DIR))


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
        overview = build_overview()
        return templates.TemplateResponse(
            request=request,
            name="overview.html",
            context={
                "overview": overview,
                "title": overview.text.splitlines()[0].removeprefix("📋 "),
                "disclaimer": DISCLAIMER,
                "version": __version__,
            },
        )
    except Exception as exc:
        logger.exception("Dashboard rendering failed.")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(exc), "type": type(exc).__name__},
        )


@app.get("/seviye/{code}")
def levels_route(code: str):
    """The same list as /seviye (Özellik A §2.2): teknik seviye, öneri değil."""

    from core.analytics import levels as L
    from core.reports.daily import adjusted_bars
    from core.watchlist.service import normalize_symbol

    try:
        symbol = normalize_symbol(code)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(exc)})
    found = L.levels(adjusted_bars(symbol))
    return {"symbol": symbol.removesuffix(".IS"), "label": L.LABEL, "note": L.STUDY_NOTE,
            "levels": [{"price": round(lv.price, 4), "kind": lv.kind, "method": lv.method, "name": lv.name,
                        "strength": lv.strength, "touches": lv.touches, "breaks": lv.breaks,
                        "last_touch": lv.last_touch.isoformat() if lv.last_touch else None,
                        "dist_atr": round(lv.dist_atr, 3), "dist_pct": round(lv.dist_pct, 3)} for lv in found]}


if __name__ == "__main__":
    import uvicorn

    logger.info("%s v%s web panel started.", settings.app_name, __version__)
    uvicorn.run("core.web.app:app", host="127.0.0.1", port=8000, reload=settings.debug)
