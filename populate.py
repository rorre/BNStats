import httpx
import logging
import warnings
from tortoise import Tortoise, run_async
from tortoise.query_utils import Q
from typing import List
from starlette.config import Config

from bnstats.routine import (
    update_events_db,
    update_users_db,
    update_maps_db,
    update_user_details,
)
from bnstats.score import get_system
from bnstats.models import User

config = Config(".env")
DB_URL = config("DB_URL")
SITE_SESSION = config("BNSITE_SESSION")
API_KEY = config("API_KEY")
WEBHOOK_URL = config("WEBHOOK_URL", default="")

logger = logging.getLogger("bnstats")
logger.setLevel(logging.DEBUG)


def send_webhook(msg):
    if not WEBHOOK_URL:
        return
    hook = {"embeds": [{"title": "BNStats Populator", "description": msg}]}
    httpx.post(WEBHOOK_URL, json=hook)


async def run_calculate():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
    await Tortoise.generate_schemas()

    users = await User.get_users()
    c = len(users)
    for i, u in enumerate(users):
        print(f">>> Calculating score for user: {u.username} ({i+1}/{c})")

        for system_name in ("ren", "naxess"):
            print(">>>> Using system:", system_name)
            calc_system = get_system(system_name)()
            await calc_system.calculate_user(u)


async def process_user(u: User, days: int):
    print(f">>> Populating events for user: {u.username}")
    await update_events_db(u, days)
    nominated_maps = []

    print(f">>> Populating maps for user: {u.username}")
    nominations = await u.get_nomination_activity()
    c_maps = len(nominations)
    for i, nom in enumerate(nominations):
        print(f">>> Fetching: {nom.beatmapsetId} ({i+1}/{c_maps})")
        nominated_maps.append(await update_maps_db(nom))

    if nominated_maps:
        print(f">>> Updating details for user: {u.username}")
        await update_user_details(u, nominated_maps)

    print(f">>> Calculating score for user: {u.username}")
    for system_name in ("ren", "naxess"):
        print(">>>> Using system:", system_name)
        calc_system = get_system(system_name)()  # type: ignore
        await calc_system.calculate_user(u)


async def run(days):
    send_webhook("Population starts.")
    try:
        await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
        await Tortoise.generate_schemas()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            print("> Populating users...")
            users: List[User] = await update_users_db()

            c = len(users)
            for i, u in enumerate(users):
                print(f">> Populating data for user: {u.username} ({i+1}/{c})")
                process_user(u, days)

            if len(w):
                e_msg = "\r\n".join(list(map(lambda x: str(x.message), w)))
                send_webhook(f"Warnings: \r\n```\r\n{e_msg}```")
    except BaseException as e:
        send_webhook(f"An exception occured during population: \r\n```\r\n{str(e)}```")
        raise e

    send_webhook("Population ends.")


async def run_user(user: str, days: int):
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})

    qargs = Q(username=user)
    if user.isnumeric():
        qargs |= Q(osuId=user)
    u = await User.filter(qargs).get()
    await process_user(u, days)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--days", type=int, default=999, help="Number of days to fetch."
    )
    parser.add_argument(
        "--only-recalculate", help="Only recalculate users.", action="store_true"
    )
    parser.add_argument("-u", "--user", help="Refetch a specific user")

    args = parser.parse_args()
    if args.only_recalculate:
        run_async(run_calculate())
    else:
        if args.user:
            run_async(run_user(args.user, args.days))
        else:
            run_async(run(args.days))
