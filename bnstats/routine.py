import json
import logging
import time
import warnings
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import urlencode

from dateutil.parser import parse

from bnstats.bnsite import request
from bnstats.bnsite.enums import MapStatus
from bnstats.bnsite.request import get
from bnstats.models import Beatmap, BeatmapSet, Nomination, Reset, User

logger = logging.getLogger("bnstats.routine")
API_URL = "https://osu.ppy.sh/api"
USERS_URL = "https://bn.mappersguild.com/users"


async def update_users_db():
    url = USERS_URL + "/relevantInfo"
    try:
        logger.info("Fetching user data from BN site.")
        r = await get(url)
    except json.decoder.JSONDecodeError:
        # Session expired.
        # Just return an empty list so that it doesn't go any further.
        # TODO: Notify or something
        warnings.warn("BN site down or cookie expired.")
        return []

    db_uids = await User.all().values_list("osuId", flat=True)
    current_uids = [u["osuId"] for u in r["users"]]

    # Remove all kicked users
    logger.info("Removing all kicked users.")
    deleted_users = filter(lambda x: x not in current_uids, db_uids)
    logger.debug(f"Database: {db_uids}")
    logger.debug(f"BN site: {current_uids}")
    logger.debug(f"Kicked users: {deleted_users}")
    for u in deleted_users:
        await (await User.get(osuId=u)).delete()

    logger.info("Updating users.")
    users: List[User] = []
    for u in r["users"]:
        u["last_updated"] = datetime.utcnow()
        user = await User.get_or_none(osuId=u["osuId"])
        if user:
            logger.debug(f"Updating user: {user.username}")
            user.update_from_dict(u)
            await user.save()
        else:
            logger.debug(f"New user: {u['username']}")
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
    logger.debug(f"Fetching: {url}")
    activities: Dict[str, Any] = await get(url)
    return activities


async def update_nomination_db(user: User, days: int = 90):
    try:
        logger.info(f"Fetching nomination activity for user: {user.username}")
        activities = await _fetch_activity(user, days)
    except json.decoder.JSONDecodeError:
        # Session expired.
        # Just return an empty list so that it doesn't go any further.
        # TODO: Notify or something
        warnings.warn("BN site down or cookie expired.")
        return []

    events: List[Nomination] = []
    for event in activities["uniqueNominations"]:
        db_event = await Nomination.get_or_none(
            beatmapsetId=event["beatmapsetId"],
            userId=event["userId"],
        )
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)
        event["user"] = user

        if not db_event:
            logger.info(
                f"Creating new nomination event: {event['userId']} for mapset {event['beatmapsetId']}"
            )
            db_event = await Nomination.create(**event)
        events.append(db_event)

    resets = activities["nominationsDisqualified"] + activities["nominationsPopped"]
    for event in resets:
        event["id"] = event["_id"]
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)

        # Hack because pishi mongodb zzz
        if "obviousness" in event and not event["obviousness"]:
            event["obviousness"] = 0
        if "severity" in event and not event["severity"]:
            event["severity"] = 0

        db_event = await Reset.get_or_none(
            beatmapsetId=event["beatmapsetId"],
            userId=event["userId"],
            timestamp=event["timestamp"],
        )
        if not db_event:
            logger.info(
                f"Creating reset event: {event['userId']} for mapset {event['beatmapsetId']}"
            )
            db_event = await Reset.create(**event)

        await db_event.fetch_related("user_affected")
        if user not in db_event.user_affected:
            await db_event.user_affected.add(user)

    resets_done = activities["disqualifications"] + activities["pops"]
    for event in resets_done:
        event["id"] = event["_id"]
        event["timestamp"] = parse(event["timestamp"], ignoretz=True)

        db_event = await Reset.get_or_none(
            beatmapsetId=event["beatmapsetId"],
            userId=event["userId"],
            timestamp=event["timestamp"],
        )
        if not db_event:
            logger.info(
                f"Creating reset event: {event['userId']} for mapset {event['beatmapsetId']}"
            )
            db_event = await Reset.create(**event)

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

    return events


async def update_maps_db(nomination: Nomination):
    db_result = await Beatmap.filter(beatmapset_id=nomination.beatmapsetId).all()

    if not db_result or db_result[0].status not in [
        MapStatus.Approved,
        MapStatus.Ranked,
    ]:
        query = {"k": request.api_key, "s": nomination.beatmapsetId}
        url = API_URL + "/get_beatmaps?" + urlencode(query)
        logger.info(f"Fetching osu! for beatmapset: {nomination.beatmapsetId}")
        r = await get(url)

        db_result: List[Beatmap] = []  # type: ignore
        for bmap in r:
            db_diff = await Beatmap.filter(beatmap_id=bmap["beatmap_id"]).get_or_none()

            if not db_diff:
                logger.info(f"Creating Beatmap entry for beatmap: {bmap['beatmap_id']}")
                db_diff = await Beatmap.create(**bmap)
            else:
                logger.info(f"Updating Beatmap entry for beatmap: {bmap['beatmap_id']}")
                db_diff.update_from_dict(bmap)
                await db_diff.save()
            db_result.append(db_diff)
    return BeatmapSet(db_result)


async def update_user_details(user: User, maps: List[BeatmapSet]):
    FAVOR_THRESHOLD = 0.20

    logger.info(f"Updating user details for user: {user.username}")
    logger.info("Removing invalid maps.")
    invalid_maps = []
    for m in maps:
        if not m.beatmaps:
            invalid_maps.append(m)

    for m in invalid_maps:
        maps.remove(m)

    # Count for genres
    logger.info("Counting genre favor.")
    counts_genre = Counter([m.genre for m in maps])
    genre_favors = []
    for genre, c in counts_genre.most_common(3)[::-1]:
        if c / len(maps) > FAVOR_THRESHOLD:
            genre_favors.append(genre.name)

    if not genre_favors:
        genre_favors.append(genre.name)

    # Count for languages
    logger.info("Counting language favor.")
    counts_lang = Counter([m.language for m in maps])
    lang_favors = []
    for lang, c in counts_lang.most_common(3)[::-1]:
        if c / len(maps) > FAVOR_THRESHOLD:
            lang_favors.append(lang.name)

    if not lang_favors:
        lang_favors.append(lang.name)

    # Count for languages
    logger.info("Counting diffculty favor.")
    diff_favors = []
    counts_top = Counter([m.top_difficulty.difficulty for m in maps])
    for diff, c in counts_top.most_common(3)[::-1]:
        if c / len(maps) > FAVOR_THRESHOLD:
            diff_favors.append(diff.name)

    logger.info("Counting length and diff favor.")
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

    logger.info("Pushing new user details to database.")
    updates = {
        "avg_length": average_length,
        "avg_diffs": average_diffs,
        "length_favor": length,
        "size_favor": size,
        "genre_favor": genre_favors,
        "lang_favor": lang_favors,
        "topdiff_favor": diff_favors,
        "last_updated": datetime.utcnow(),
    }
    user.update_from_dict(updates)
    await user.save()
