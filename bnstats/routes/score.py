from datetime import timedelta
from typing import Optional

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Router
from tortoise import timezone

from bnstats.models import User
from bnstats.plugins import templates

router = Router()


@router.route("/{user_id:int}", name="show")
async def show_user(request: Request):
    calc_system = request.scope["calculator"]

    uid: int = request.path_params["user_id"]
    mode: Optional[str] = request.query_params.get("mode")
    if mode not in ["osu", "catch", "taiko", "mania"]:
        mode = None

    user = await User.get_or_none(osuId=uid)
    if not user:
        raise HTTPException(404, "User not found.")

    d = timezone.now() - timedelta(90)
    nominations = await user.get_nomination_activity(d, mode=mode)

    if not nominations:
        ctx = {"request": request, "user": user, "error": True, "title": user.username}
        return templates.TemplateResponse("pages/user/no_noms.html", ctx)

    for nom in nominations:
        nom.map = await nom.get_map()

    nominations.sort(
        key=lambda x: abs(x.score[calc_system.name]["total_score"]),
        reverse=True,
    )

    user.score = calc_system.get_activity_score(nominations)
    ctx = {
        "calc_system": calc_system,
        "request": request,
        "user": user,
        "nominations": nominations,
        "title": user.username,
    }
    return templates.TemplateResponse("pages/score/show.html", ctx)


@router.route("/leaderboard", name="leaderboard")
async def leaderboard(request: Request):
    calc_system = request.scope["calculator"]

    selected_mode = request.query_params.get("mode")
    is_valid_mode = selected_mode and selected_mode in [
        "osu",
        "taiko",
        "catch",
        "mania",
    ]
    if is_valid_mode:
        users = (
            await User.filter(modes__contains=[selected_mode])
            .all()
            .order_by("username")
        )
    else:
        users = await User.get_users()

    for u in users:
        u.score = await u.get_score(calc_system)
        u.score_modes = {}
        for mode in u.modes:
            u.score_modes[mode] = await u.get_score(calc_system, mode=mode)

    if is_valid_mode:
        users.sort(key=lambda x: x.score_modes[selected_mode], reverse=True)
    else:
        users.sort(key=lambda x: x.score, reverse=True)

    ctx = {
        "request": request,
        "users": users,
        "last_update": max(users, key=lambda x: x.last_updated).last_updated,
        "title": "Leaderboard",
        "mode": selected_mode,
    }
    return templates.TemplateResponse("pages/score/leaderboard.html", ctx)
