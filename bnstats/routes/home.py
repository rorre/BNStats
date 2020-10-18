from starlette.requests import Request

from bnstats.plugins import templates


async def homepage(request: Request):
    ctx = {"request": request}
    return templates.TemplateResponse("pages/index.html", ctx)
