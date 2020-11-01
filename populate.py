from tortoise import Tortoise, run_async
from typing import List
from starlette.config import Config

from bnstats.routine import (
    update_nomination_db,
    update_users_db,
    update_maps_db,
    update_user_details,
)
from bnstats.score import calculate_user
from bnstats.bnsite import request
from bnstats.models import User

config = Config(".env")
DB_URL = config("DB_URL")
SITE_SESSION = config("BNSITE_SESSION")
API_KEY = config("API_KEY")


async def run_calculate():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
    await Tortoise.generate_schemas()

    users = await User.get_users()
    c = len(users)
    for i, u in enumerate(users):
        print(f">>> Calculating score for user: {u.username} ({i+1}/{c})")
        await calculate_user(u)


async def run(days):
    request.setup_session(SITE_SESSION, API_KEY)
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
    await Tortoise.generate_schemas()

    print("> Populating users...")
    users: List[User] = await update_users_db()

    c = len(users)
    for i, u in enumerate(users):
        print(f">> Populating data for user: {u.username} ({i+1}/{c})")
        nominations = await update_nomination_db(u, days)

        print(f">>> Populating maps for user: {u.username}")
        user_maps = []
        c_maps = len(nominations)
        for i, nom in enumerate(nominations):
            print(f">>> Fetching: {nom.beatmapsetId} ({i+1}/{c_maps})")
            m = await update_maps_db(nom)
            user_maps.append(m)

        if user_maps:
            print(f">>> Updating details for user: {u.username}")
            await update_user_details(u, user_maps)

        print(f">>> Calculating score for user: {u.username}")
        await calculate_user(u)

    await request.s.aclose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--days", type=int, default=999, help="Number of days to fetch."
    )
    parser.add_argument(
        "--only-recalculate", help="Only recalculate users.", action="store_true"
    )

    args = parser.parse_args()
    if args.only_recalculate:
        run_async(run_calculate())
    else:
        run_async(run(args.days))
