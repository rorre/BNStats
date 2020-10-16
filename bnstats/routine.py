from datetime import datetime
import sys
import time
from starlette.applications import Starlette
from bnstats.models import User, Nomination
from bnstats.bnsite.request import get, s
from dateutil.parser import parse
from typing import Dict, Any, List
import asyncio
import traceback

USERS_URL = "https://bn.mappersguild.com/users"


async def update_users_db():
    url = USERS_URL + "/relevantInfo"
    r = await get(url)

    users: List[User] = []
    for u in r["users"]:
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

        if not db_event:
            db_event = await Nomination.create(**event)
        events.append(db_event)

    return events


task = None


def setup_routine(app: Starlette):
    @app.on_event("startup")
    async def startup():
        global task

        async def routine():
            while True:
                try:
                    users = await update_users_db()
                    app.state.last_update["user-list"] = datetime.utcnow()

                    for u in users:
                        events = await update_nomination_db(u)
                        app.state.last_update["user"][u.osuId] = datetime.utcnow()

                        for e in events:
                            await e.get_map()
                except BaseException as error:
                    if type(error) is asyncio.CancelledError:
                        break

                    traceback.print_exception(
                        type(error), error, error.__traceback__, file=sys.stderr
                    )

        loop = asyncio.get_event_loop()
        task = loop.create_task(routine())

    @app.on_event("shutdown")
    async def shutdown():
        global task
        task.cancel()
        asyncio.gather(task)
        await s.aclose()
