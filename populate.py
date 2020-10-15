from datetime import datetime
from tortoise import Tortoise, run_async

from starlette.config import Config

from bnstats.bnsite import request
from bnstats.models import User

config = Config(".env")
DB_URL = config("DB_URL")
SITE_SESSION = config("BNSITE_SESSION")
API_KEY = config("API_KEY")


class MockClass:
    def __init__(self):
        self.app = self
        self.state = self
        self.last_update = {"user-list": datetime.min, "user": {}}


async def run():
    mock = MockClass()

    request.setup_session(SITE_SESSION, API_KEY)
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})
    await Tortoise.generate_schemas()

    print("Populating users...")
    users = await User.get_users(mock)

    c = len(users)
    for i, u in enumerate(users):
        print(f"Populating data for user: {u.username} ({i+1}/{c})")
        nominations = await u.get_nomination_activity(mock)

        print(f"Populating maps for user: {u.username} ({i+1}/{c})")
        for nom in nominations:
            await nom.get_map()

    await request.s.aclose()


run_async(run())
