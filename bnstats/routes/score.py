from datetime import datetime, timedelta

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Router

from bnstats.config import CALC_SYSTEM
from bnstats.models import User
from bnstats.plugins import templates

router = Router()


@router.route("/{user_id:int}", name="show")
async def show_user(request: Request):
    uid: int = request.path_params["user_id"]
    mode: str = request.query_params.get("mode")
    if mode not in ["osu", "catch", "taiko", "mania"]:
        mode = None

    user = await User.get_or_none(osuId=uid)
    if not user:
        raise HTTPException(404, "User not found.")

    d = datetime.now() - timedelta(90)
    nominations = await user.get_nomination_activity(d, mode=mode)

    if not nominations:
        ctx = {"request": request, "user": user, "error": True, "title": user.username}
        return templates.TemplateResponse("pages/user/no_noms.html", ctx)

    for nom in nominations:
        nom.map = await nom.get_map()

    nominations.sort(key=lambda x: abs(x.score), reverse=True)
    ctx = {
        "calc_system": CALC_SYSTEM,
        "request": request,
        "user": user,
        "nominations": nominations,
        "title": user.username,
    }
    return templates.TemplateResponse("pages/user/score_show.html", ctx)
