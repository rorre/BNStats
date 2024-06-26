import sys
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

bnstats_logger = logging.getLogger("bnstats")
bnstats_logger.setLevel(logging.DEBUG)
bnstats_logger.addHandler(logging.StreamHandler(sys.stdout))

logger = logging.getLogger("bnstats.populate")


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
    await update_events_db(u, days)

    nominations = await u.get_nomination_activity()

    logger.info("Fetching maps")
    nominated_maps = []
    for nom in nominations:
        nominated_maps.append(await update_maps_db(nom))

    if nominated_maps:
        logger.info("Updating user information")
        await update_user_details(u, nominated_maps)

    logger.info("Recalculating score")
    for system_name in ("ren", "naxess"):
        calc_system = get_system(system_name)()  # type: ignore
        await calc_system.calculate_user(u)


async def run(days: int, skip_former: bool):
    send_webhook("Population starts.")
    try:
        await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
        await Tortoise.generate_schemas()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            users: List[User] = await update_users_db()

            logger.info(f"Populating {len(users)} users...")
            for u in users:
                logger.info(f"Populating {u.username}")
                if skip_former and not u.isBn and not u.isNat:
                    logger.info(">> Skipping former BN:", u.username)
                    continue

                await process_user(u, days)

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

    logger.info(f"Populating {u.username}")
    await process_user(u, days)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--days", type=int, default=999, help="Number of days to fetch.")
    parser.add_argument("--only-recalculate", help="Only recalculate users.", action="store_true")
    parser.add_argument("-u", "--user", help="Refetch a specific user")
    parser.add_argument(
        "--skip-former",
        help="Whether or not to skip populating former user",
        action="store_true",
    )

    args = parser.parse_args()
    if args.only_recalculate:
        run_async(run_calculate())
    else:
        if args.user:
            run_async(run_user(args.user, args.days))
        else:
            run_async(run(args.days, args.skip_former))
