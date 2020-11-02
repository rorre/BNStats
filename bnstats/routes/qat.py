from datetime import datetime
from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Router
from starlette.config import Config

from bnstats.models import User, Beatmap, Nomination, Reset
from dateutil.parser import parse

from tortoise.models import Model

router = Router()

conf = Config(".env")
DEFAULT_KEY = "absolutelyunsafekey"
DEBUG: bool = conf("DEBUG", cast=bool, default=False)
QAT_KEY: str = conf("QAT_KEY", default=DEFAULT_KEY)

if DEFAULT_KEY == QAT_KEY and not DEBUG:
    raise ValueError("Cannot use default key in non-debug mode.")


async def nomination_update(req_data: Dict[str, Any]):
    for event in req_data["events"]:
        db_event = await Nomination.get_or_none(
            beatmapsetId=event["beatmapsetId"],
            userId=event["userId"],
        )
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)
        event["user"] = await User.get_or_none(osuId=event["userId"])

        if not db_event:
            db_event = await Nomination.create(**event)
        else:
            db_event.update_from_dict(event)
            await db_event.save()

    return JSONResponse({"status": 200, "message": "OK"})


async def reset_update(req_data: Dict[str, Any]):
    for event in req_data["events"]:
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)
        db_event = await Reset.get_or_none(id=event["id"])
        if not db_event:
            db_event = await Reset.create(**event)
        else:
            db_event.update_from_dict(event)
            await db_event.save()

    return JSONResponse({"status": 200, "message": "OK"})


async def beatmap_update(req_data: Dict[str, Any]):
    for bmap in req_data["beatmaps"]:
        db_diff = await Beatmap.filter(beatmap_id=bmap["beatmap_id"]).get_or_none()

        if not db_diff:
            db_diff = await Beatmap.create(**bmap)
        else:
            db_diff.update_from_dict(bmap)
            await db_diff.save()

    return JSONResponse({"status": 200, "message": "OK"})


async def user_update(req_data: Dict[str, Any]):
    db_uids = await User.all().values_list("osuId", flat=True)
    current_uids = [u["osuId"] for u in req_data["users"]]

    # Remove all kicked users
    deleted_users = filter(lambda x: x not in current_uids, db_uids)
    for u in deleted_users:
        await (await User.get(osuId=u)).delete()

    for u in req_data["users"]:
        u["last_updated"] = datetime.utcnow()
        user = await User.get_or_none(osuId=u["osuId"])
        if user:
            user.update_from_dict(u)
            await user.save()
        else:
            user = await User.create(**u)

    return JSONResponse({"status": 200, "message": "OK"})


classes = {
    "nominate": nomination_update,
    "reset": reset_update,
    "beatmap": user_update,
    "user": beatmap_update,
}


@router.route("/aiess", methods=["POST"])
async def new_entry(request: Request):
    if (
        "Authorization" not in request.headers
        or request.headers["Authorization"] != QAT_KEY
    ):
        return JSONResponse({"error": "Unauthorized."}, 401)

    req_data: Dict[str, Any] = await request.json()

    data_type: str = req_data["type"]
    if data_type not in classes.keys():
        return JSONResponse({"error": "Invalid type."}, 400)

    func: Model = classes[data_type]

    try:
        return await func()
    except:
        return JSONResponse({"status": 500, "message": "An exception occured."})
