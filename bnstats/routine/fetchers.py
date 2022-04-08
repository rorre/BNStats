import json
import logging
import time
import warnings
from typing import Any, Dict

from bnstats.bnsite.request import get
from bnstats.models import User
from bnstats.routine.constants import USERS_URL, INTEROP_URL

logger = logging.getLogger("bnstats.routine")


async def fetch_users_api():
    url = USERS_URL + "/relevantInfo"
    try:
        logger.info("Fetching user data from BN site.")
        r = await get(url)
        return r["users"]
    except json.decoder.JSONDecodeError:
        # Session expired.
        # Just return an empty list so that it doesn't go any further.
        # TODO: Notify or something
        warnings.warn("BN site down or cookie expired.")
        return []


async def fetch_users_interop():
    url = INTEROP_URL + "/users/all"
    events: Dict[str, Any] = await get(url)
    return events


# Events
async def fetch_events_interop(user: User, days: int = 90):
    url = INTEROP_URL + f"/nominationResets/{user.osuId}/{days}/"
    events: Dict[str, Any] = await get(url)
    return events


async def fetch_events_api(user: User, days: int = 90):
    try:
        logger.info(f"Fetching nomination activity for user: {user.username}")
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
    except json.decoder.JSONDecodeError:
        # Session expired.
        # Just return an empty list so that it doesn't go any further.
        # TODO: Notify or something
        warnings.warn("BN site down or cookie expired.")
        return []
    return activities