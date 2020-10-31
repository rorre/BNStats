from datetime import datetime, timedelta

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Router
from bnstats.models import User
from bnstats.plugins import templates

router = Router()


@router.route("/", name="list")
async def listing(request: Request):
    users = await User.get_users()
    for u in users:
        u.score = await u.get_score()
    users.sort(key=lambda x: x.score, reverse=True)
    ctx = {"request": request, "users": users, "title": "Leaderboard"}
    return templates.TemplateResponse("score/listing.html", ctx)


@router.route("/{user_id:int}", name="show")
async def show_user(request: Request):
    uid: int = request.path_params["user_id"]
    user = await User.get_or_none(osuId=uid)
    if not user:
        raise HTTPException(404, "User not found.")

    d = datetime.now() - timedelta(90)
    nominations = await user.get_nomination_activity(d)

    if not nominations:
        ctx = {"request": request, "user": user, "error": True, "title": user.username}
        return templates.TemplateResponse("pages/user/no_noms.html", ctx)

    for nom in nominations:
        nom.map = await nom.get_map()

    nominations.sort(key=lambda x: x.score, reverse=True)
    ctx = {
        "request": request,
        "user": user,
        "nominations": nominations,
        "title": user.username,
    }
    return templates.TemplateResponse("score/show.html", ctx)
