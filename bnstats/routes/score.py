from bnstats.config import DEFAULT_CALC_SYSTEM
from datetime import datetime, timedelta

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Router

from bnstats.models import User
from bnstats.plugins import templates
from bnstats.score import get_system

router = Router()


@router.route("/{user_id:int}", name="show")
async def show_user(request: Request):
    calc_system = get_system(request.session.get("calc_system"))()
    if not calc_system:
        calc_system = DEFAULT_CALC_SYSTEM

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

    nominations.sort(
        key=lambda x: abs(x.score[calc_system.name].total_score), reverse=True
    )
    ctx = {
        "calc_system": calc_system,
        "request": request,
        "user": user,
        "nominations": nominations,
        "title": user.username,
    }
    return templates.TemplateResponse("pages/user/score_show.html", ctx)
