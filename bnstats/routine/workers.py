from collections import Counter
import json
import logging
from typing import List
from urllib.parse import urlencode

from dateutil.parser import parse
from tortoise import timezone

from bnstats.bnsite.enums import MapStatus
from bnstats.bnsite.request import get
from bnstats.config import API_KEY, USE_AIESS, USE_INTEROP
from bnstats.helper import mode_to_db
from bnstats.models import Beatmap, BeatmapSet, Nomination, Reset, User
from bnstats.routine.fetchers import (
    fetch_events_api,
    fetch_events_interop,
    fetch_users_api,
    fetch_users_interop,
)
from bnstats.routine.constants import API_URL

logger = logging.getLogger("bnstats.routine")


async def reconnect_relations(user: User):
    logger.info(f"Reconnecting relations for user {user.username}")
    nominations = await Nomination.filter(userId=user.osuId).all()
    for nom in nominations:
        nom.update_from_dict({"user": user})
        await nom.save()


async def update_users_db():
    if USE_INTEROP:
        fetcher = fetch_users_interop
    else:
        fetcher = fetch_users_api
    r = await fetcher()

    db_uids = await User.all().values_list("osuId", flat=True)
    current_uids = [u["osuId"] for u in r]

    # Remove all kicked users
    logger.info("Removing all kicked users.")
    deleted_users = filter(lambda x: x not in current_uids, db_uids)
    logger.debug(f"Database: {db_uids}")
    logger.debug(f"BN site: {current_uids}")
    logger.debug(f"Kicked users: {deleted_users}")
    # for u in deleted_users:
    #     user = await User.get(osuId=u)
    #     await user.resets.clear()
    #     await user.delete()

    logger.info("Updating users.")
    users: List[User] = []
    for u in r:
        # HACK: This is for no mode NAT. They can nominate anything, so they will be given any modes.
        if "none" in u["modes"]:
            u["modesInfo"] = [
                {"mode": "mania", "level": "full"},
                {"mode": "osu", "level": "full"},
                {"mode": "taiko", "level": "full"},
                {"mode": "catch", "level": "full"},
            ]
            u["modes"] = ["mania", "osu", "taiko", "catch"]

        u["last_updated"] = timezone.now()
        user = await User.get_or_none(osuId=u["osuId"])
        if user:
            logger.debug(f"Updating user: {user.username}")
            user.update_from_dict(u)
            await user.save()
        else:
            logger.debug(f"New user: {u['username']}")
            user = await User.create(**u)
            await reconnect_relations(user)

        users.append(user)
    return users


async def _insert_reset_event(event):
    event["id"] = event["_id"]
    event["timestamp"] = parse(event["timestamp"])

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
    else:
        update_data = {
            "obviousness": event["obviousness"] if "obviousness" in event else 0,
            "severity": event["severity"] if "severity" in event else 0,
        }
        db_event.update_from_dict(update_data)
        await db_event.save()

    return db_event


async def update_events_db(user: User, days: int = 90):
    if USE_INTEROP:
        fetcher = fetch_events_interop
    else:
        fetcher = fetch_events_api
    activities = await fetcher(user, days)

    if USE_AIESS:
        # Skip nomination activities from bnsite, it's already provided from aiess.
        activities["uniqueNominations"] = []

    for event in activities["uniqueNominations"]:
        nom_event = await Nomination.get_or_none(
            beatmapsetId=event["beatmapsetId"],
            userId=event["userId"],
        )
        event["timestamp"] = parse(event["timestamp"])
        event["user"] = user

        nomination_modes = []
        for mode in user.modes:
            if mode in event["modes"]:
                nomination_modes.append(mode_to_db(mode))

        event["as_modes"] = nomination_modes
        if not nom_event:
            logger.info(
                f"Creating new nomination event: {event['userId']} for mapset {event['beatmapsetId']}"
            )
            nom_event = await Nomination.create(**event)
        else:
            nom_event.update_from_dict({"as_modes": nomination_modes})
            await nom_event.save()

    resets = activities["nominationsDisqualified"] + activities["nominationsPopped"]
    for event in resets:
        reset_event = await _insert_reset_event(event)

        await reset_event.fetch_related("user_affected")
        if user and user not in reset_event.user_affected:
            await reset_event.user_affected.add(user)

    resets_done = activities["disqualifications"] + activities["pops"]
    for event in resets_done:
        reset_event = await _insert_reset_event(event)

        await reset_event.fetch_related("user_affected")
        map_nominations = await Nomination.filter(
            beatmapsetId=event["beatmapsetId"],
            timestamp__lt=event["timestamp"]
        ).order_by("-timestamp")
        limit = 1 + (reset_event.type == "disqualify")

        for nom in map_nominations[:limit]:
            nominator = await nom.user
            if nominator and nominator not in reset_event.user_affected:
                await reset_event.user_affected.add(nominator)

        await reset_event.save()


async def update_maps_db(nomination: Nomination):
    db_result = await Beatmap.filter(beatmapset_id=nomination.beatmapsetId).all()

    if not db_result or db_result[0].status not in [
        MapStatus.Approved,
        MapStatus.Ranked,
    ]:
        query = {"k": API_KEY, "s": nomination.beatmapsetId}
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
        "last_updated": timezone.now(),
    }
    user.update_from_dict(updates)
    await user.save()
