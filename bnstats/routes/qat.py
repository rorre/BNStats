import traceback
from typing import Any, Awaitable, Callable, Dict

from dateutil.parser import parse
from starlette.config import Config
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Router

from bnstats.helper import generate_mongo_id, mode_to_db
from bnstats.models import Nomination, Reset, User
from bnstats.routine import update_maps_db, update_users_db

router = Router()

conf = Config(".env")
DEFAULT_KEY = "absolutelyunsafekey"
DEBUG: bool = conf("DEBUG", cast=bool, default=False)
QAT_KEY: str = conf("QAT_KEY", default=DEFAULT_KEY)

if DEFAULT_KEY == QAT_KEY and not DEBUG:
    raise ValueError("Cannot use default key in non-debug mode.")


async def nomination_update(event: Dict[str, Any]):
    event["timestamp"] = parse(event["timestamp"], ignoretz=True)
    event["user"] = await User.get_or_none(osuId=event["userId"])

    if not event["user"]:
        await update_users_db()
        event["user"] = await User.get_or_none(osuId=event["userId"])
        if not event["user"]:
            raise ValueError(
                "Cannot find user in database, maybe pishi site is falling behind?"
            )

    if "as_modes" in event:
        event["as_modes"] = [mode_to_db(m) for m in event["as_modes"]]

    db_event = await Nomination.get_or_none(
        beatmapsetId=event["beatmapsetId"],
        userId=event["userId"],
    )

    if not db_event:
        db_event = await Nomination.create(**event)

    await update_maps_db(db_event)


async def reset_update(event: Dict[str, Any]):
    if event["userId"] == 3:
        return
    event["timestamp"] = parse(event["timestamp"], ignoretz=True)
    db_event = await Reset.get_or_none(
        beatmapsetId=event["beatmapsetId"],
        userId=event["userId"],
        timestamp=event["timestamp"],
    )

    if "obviousness" in event and not event["obviousness"]:
        event["obviousness"] = 0
    if "severity" in event and not event["severity"]:
        event["severity"] = 0

    if not db_event:
        event["id"] = generate_mongo_id()
        db_event = await Reset.create(**event)
    else:
        db_event.update_from_dict(event)

    await db_event.fetch_related("user_affected")
    map_nominations = await Nomination.filter(
        beatmapsetId=event["beatmapsetId"]
    ).order_by("-timestamp")
    limit = 1 + (db_event.type == "disqualify")

    for nom in map_nominations[:limit]:
        user = await nom.user
        if user not in db_event.user_affected:
            await db_event.user_affected.add(user)

    await db_event.save()


classes = {
    "nominate": nomination_update,
    "qualify": nomination_update,
    "nomination_reset": reset_update,
    "disqualify": reset_update,
}


@router.route("/aiess", methods=["POST"])
async def new_entry(request: Request):
    if (
        "Authorization" not in request.headers
        or request.headers["Authorization"] != QAT_KEY
    ):
        return JSONResponse({"status": 401, "message": "Unauthorized."}, 401)

    event: Dict[str, Any] = await request.json()

    data_type: str = event["type"]
    if data_type not in classes.keys():
        return JSONResponse({"status": 400, "message": "Invalid type."}, 400)

    func: Callable[[Dict[str, Any]], Awaitable] = classes[data_type]
    try:
        await func(event)
    except BaseException as e:
        traceback.print_exc()
        return JSONResponse({"status": 500, "messages": str(e)}, 500)

    return JSONResponse({"status": 200, "message": "OK"})
