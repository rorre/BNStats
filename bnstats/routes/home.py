from starlette.requests import Request
from starlette.routing import Router

from bnstats.plugins import templates

router = Router()


@router.route("/")
async def homepage(request: Request):
    ctx = {"request": request}
    return templates.TemplateResponse("pages/index.html", ctx)