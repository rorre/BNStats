import asyncio
import sys
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlencode

from dateutil.parser import parse
from starlette.applications import Starlette

from bnstats.bnsite import request
from bnstats.bnsite.enums import MapStatus
from bnstats.bnsite.request import get, s
from bnstats.models import Beatmap, Nomination, User

API_URL = "https://osu.ppy.sh/api"
USERS_URL = "https://bn.mappersguild.com/users"


async def update_users_db():
    url = USERS_URL + "/relevantInfo"
    r = await get(url)

    users: List[User] = []
    for u in r["users"]:
        u["last_updated"] = datetime.utcnow()
        user = await User.get_or_none(osuId=u["osuId"])
        if user:
            user.update_from_dict(u)
        else:
            user = await User.create(**u)

        users.append(user)
    return users


async def _fetch_activity(user, days):
    deadline = time.time() * 1000
    url = (
        USERS_URL
        + f"/activity?osuId={user.osuId}&"
        + f"modes={','.join(user.modes)}&"
        + f"deadline={deadline}&mongoId={user._id}&"
        + f"days={days}"
    )
    activities: Dict[str, Any] = await get(url)
    return activities


async def update_nomination_db(user: User, days: int = 90):
    activities = await _fetch_activity(user, days)
    events: List[Nomination] = []
    for event in activities["uniqueNominations"]:
        db_event = await Nomination.get_or_none(
            timestamp=parse(event["timestamp"]),
            userId=event["userId"],
        )
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)
        event["user"] = user

        if not db_event:
            db_event = await Nomination.create(**event)
        events.append(db_event)

    return events


async def update_maps_db(nomination: Nomination):
    db_result = await Beatmap.filter(beatmapset_id=nomination.beatmapsetId).first()

    if not db_result or db_result.status not in [MapStatus.Approved, MapStatus.Ranked]:
        query = {"k": request.api_key, "s": nomination.beatmapsetId}
        url = API_URL + "/get_beatmaps?" + urlencode(query)
        r = await get(url)

        for map in r:
            db_diff = await Beatmap.filter(beatmap_id=map["beatmap_id"]).get_or_none()

            if not db_diff:
                await Beatmap.create(**map)
            else:
                db_diff.update_from_dict(map)


task = None


def setup_routine(app: Starlette):
    @app.on_event("startup")
    async def startup():
        global task

        async def routine():
            while True:
                try:
                    users = await update_users_db()
                    app.state.last_update = datetime.utcnow()

                    for u in users:
                        events = await update_nomination_db(u)

                        for e in events:
                            await update_maps_db(e)
                except BaseException as error:
                    if type(error) is asyncio.CancelledError:
                        break

                    traceback.print_exception(
                        type(error), error, error.__traceback__, file=sys.stderr
                    )
                await asyncio.sleep(300)

        loop = asyncio.get_event_loop()
        task = loop.create_task(routine())

    @app.on_event("shutdown")
    async def shutdown():
        global task
        task.cancel()
        asyncio.gather(task)
        await s.aclose()
