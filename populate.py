from tortoise import Tortoise, run_async
from typing import List
from starlette.config import Config

from bnstats.routine import update_nomination_db, update_users_db, update_maps_db
from bnstats.bnsite import request
from bnstats.models import User

config = Config(".env")
DB_URL = config("DB_URL")
SITE_SESSION = config("BNSITE_SESSION")
API_KEY = config("API_KEY")


async def run():
    request.setup_session(SITE_SESSION, API_KEY)
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
    await Tortoise.generate_schemas()

    print("> Populating users...")
    users: List[User] = await update_users_db()

    c = len(users)
    for i, u in enumerate(users):
        print(f">> Populating data for user: {u.username} ({i+1}/{c})")
        nominations = await update_nomination_db(u, 999)

        print(f">>> Populating maps for user: {u.username}")
        c_maps = len(nominations)
        for i, nom in enumerate(nominations):
            print(f">>> Fetching: {nom.beatmapsetId} ({i+1}/{c_maps})")
            await update_maps_db(nom)

    await request.s.aclose()


run_async(run())
