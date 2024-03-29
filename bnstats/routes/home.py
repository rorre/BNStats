from starlette.requests import Request
from starlette.responses import RedirectResponse

from bnstats.plugins import templates


async def homepage(request: Request):
    ctx = {"request": request}
    return templates.TemplateResponse("pages/index.html", ctx)


async def switch(request: Request):
    target = request.query_params.get("system")
    if target in ("ren", "naxess"):
        request.session["calc_system"] = target

    return RedirectResponse(
        url=request.query_params.get("next", request.url_for("home"))
    )
