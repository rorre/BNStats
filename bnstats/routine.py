import asyncio
import sys
import time
import traceback
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlencode

from dateutil.parser import parse
from starlette.applications import Starlette

from bnstats.bnsite import request
from bnstats.bnsite.enums import MapStatus
from bnstats.bnsite.request import get, s
from bnstats.models import Beatmap, BeatmapSet, Nomination, User

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
            await user.save()
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
            beatmapsetId=event["beatmapsetId"],
            userId=event["userId"],
        )
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)
        event["user"] = user

        if not db_event:
            db_event = await Nomination.create(**event)
        events.append(db_event)

    return events


async def update_maps_db(nomination: Nomination):
    db_result = await Beatmap.filter(beatmapset_id=nomination.beatmapsetId).all()

    if not db_result or db_result[0].status not in [
        MapStatus.Approved,
        MapStatus.Ranked,
    ]:
        query = {"k": request.api_key, "s": nomination.beatmapsetId}
        url = API_URL + "/get_beatmaps?" + urlencode(query)
        r = await get(url)

        db_result: List[Beatmap] = []
        for map in r:
            db_diff = await Beatmap.filter(beatmap_id=map["beatmap_id"]).get_or_none()

            if not db_diff:
                db_diff = await Beatmap.create(**map)
            else:
                db_diff.update_from_dict(map)
                await db_diff.save()
            db_result.append(db_diff)
    return BeatmapSet(db_result)


async def update_user_details(user: User, maps: List[BeatmapSet]):
    FAVOR_THRESHOLD = 0.20

    invalid_maps = []
    for m in maps:
        if not m.beatmaps:
            invalid_maps.append(m)

    for m in invalid_maps:
        maps.remove(m)

    # Count for genres
    counts_genre = Counter([m.genre for m in maps])
    genre_favors = []
    for genre, c in counts_genre.most_common(3)[::-1]:
        if c / len(maps) > FAVOR_THRESHOLD:
            genre_favors.append(genre.name)

    if not genre_favors:
        genre_favors.append(genre.name)

    # Count for languages
    counts_lang = Counter([m.language for m in maps])
    lang_favors = []
    for lang, c in counts_lang.most_common(3)[::-1]:
        if c / len(maps) > FAVOR_THRESHOLD:
            lang_favors.append(lang.name)

    if not lang_favors:
        lang_favors.append(lang.name)

    total_length = sum([m.total_length for m in maps])
    total_diffs = sum([m.total_diffs for m in maps])
    average_length = total_length // total_diffs
    average_diffs = sum([len(m.beatmaps) for m in maps]) // len(maps)

    if average_length < 120:
        length = "Short"
    elif average_length < 180:
        length = "Medium"
    else:
        length = "Long"

    size_factor = average_diffs * average_length
    # Anime TV Size 100s NHIX
    if size_factor <= 400:
        size = "Small"
    # Full version (3:30) HIX
    elif size_factor <= 630:
        size = "Medium"
    else:
        size = "Big"

    updates = {
        "avg_length": average_length,
        "avg_diffs": average_diffs,
        "length_favor": length,
        "size_favor": size,
        "genre_favor": genre_favors,
        "lang_favor": lang_favors,
    }
    user.update_from_dict(updates)
    await user.save()


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

                        user_maps = []
                        for e in events:
                            m = await update_maps_db(e)
                            user_maps.append(m)

                        if user_maps:
                            await update_user_details(u, user_maps)
                except BaseException as error:
                    if type(error) is asyncio.CancelledError:
                        break

                    traceback.print_exception(
                        type(error), error, error.__traceback__, file=sys.stderr
                    )
                await asyncio.sleep(60 * 60)

        loop = asyncio.get_event_loop()
        task = loop.create_task(routine())

    @app.on_event("shutdown")
    async def shutdown():
        global task
        task.cancel()
        asyncio.gather(task)
        await s.aclose()
