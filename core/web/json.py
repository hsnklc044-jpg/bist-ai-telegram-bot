"""
QuantBIST RC7
Web Application JSON Debug Layer
"""

from __future__ import annotations


import traceback


from fastapi import FastAPI, Request

from fastapi.responses import JSONResponse

from fastapi.staticfiles import StaticFiles

from fastapi.templating import Jinja2Templates



from core.api import get_dashboard





app = FastAPI(

    title="QuantBIST API",

    description="QuantBIST Portfolio Intelligence API",

    version="RC7",

)






# =====================================================
# STATIC
# =====================================================


app.mount(

    "/static",

    StaticFiles(

        directory="core/web/static"

    ),

    name="static",

)







# =====================================================
# TEMPLATE
# =====================================================


templates = Jinja2Templates(

    directory="core/web/templates"

)







# =====================================================
# ROOT
# =====================================================


@app.get("/")

def root():

    return {

        "name": "QuantBIST",

        "version": "RC7",

        "status": "running",

    }







# =====================================================
# HEALTH
# =====================================================


@app.get("/health")

def health():

    return {

        "status": "ok",

    }







# =====================================================
# DASHBOARD
# =====================================================


@app.get("/dashboard")

def dashboard(request: Request):


    try:


        print("==============================")

        print("DASHBOARD START")


        dashboard_data = get_dashboard()



        print(

            "DASHBOARD TYPE:",

            type(dashboard_data)

        )


        print(

            "DASHBOARD DATA:",

            dashboard_data

        )



        print("DASHBOARD END")

        print("==============================")





        return templates.TemplateResponse(


            name="dashboard.html",


            context={


                "request": request,


                "data": dashboard_data,


            },

        )





    except Exception as exc:


        print("==============================")

        print("DASHBOARD ERROR")

        traceback.print_exc()

        print("==============================")



        return JSONResponse(


            status_code=500,


            content={


                "status": "error",


                "message": str(exc),


                "type": type(exc).__name__,


            },

        )