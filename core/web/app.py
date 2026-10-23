"""
QuantBIST RC7
Web Dashboard
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core import __version__
from core.api import get_dashboard
from core.config.paths import WEB_STATIC_DIR, WEB_TEMPLATES_DIR
from core.infrastructure.logger import get_logger

logger = get_logger(__name__)





# =====================================================
# APP
# =====================================================


app = FastAPI(

    title="QuantBIST API",

    version=__version__,

)







# =====================================================
# STATIC FILES
# =====================================================


app.mount(

    "/static",

    StaticFiles(

        directory=str(WEB_STATIC_DIR)

    ),

    name="static",

)







# =====================================================
# TEMPLATES
# =====================================================


templates = Jinja2Templates(

    directory=str(WEB_TEMPLATES_DIR)

)







# =====================================================
# ROOT
# =====================================================


@app.get("/")
def root():

    return {


        "name":

            "QuantBIST",



        "version":

            __version__,



        "status":

            "running",


    }







# =====================================================
# HEALTH
# =====================================================


@app.get("/health")
def health():

    return {


        "status":

            "ok",


    }







# =====================================================
# DASHBOARD
# =====================================================


@app.get("/dashboard")
def dashboard(

    request: Request,

):


    try:


        logger.info(

            "Dashboard request received."

        )



        data = get_dashboard()



        return templates.TemplateResponse(

            name="dashboard.html",

            request=request,

            context={

                "data": data,

            },

        )





    except Exception as exc:


        logger.exception(

            "Dashboard rendering failed."

        )



        return JSONResponse(

            status_code=500,

            content={


                "status":

                    "error",



                "message":

                    str(exc),



                "type":

                    type(exc).__name__,


            },

        )







# =====================================================
# LOCAL SERVER
# =====================================================


if __name__ == "__main__":


    import uvicorn



    uvicorn.run(

        "core.web.app:app",

        host="127.0.0.1",

        port=8000,

        reload=False,

    )