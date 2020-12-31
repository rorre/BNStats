from starlette.requests import Request

from bnstats.plugins import templates
from starlette.responses import RedirectResponse


async def homepage(request: Request):
    ctx = {"request": request}
    return templates.TemplateResponse("pages/index.html", ctx)


async def switch(request: Request):
    target = request.query_params.get("system")
    print(target)
    if target in ("ren", "naxess"):
        request.session["calc_system"] = target
    return RedirectResponse(
        url=request.query_params.get("next", request.url_for("home"))
    )
