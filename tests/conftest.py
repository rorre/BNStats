import asyncio
import json
import logging

import pytest
from dateutil.parser import parse
from freezegun import freeze_time
from starlette.config import Config
from starlette.testclient import TestClient
from tortoise.contrib.test import finalizer, initializer

from bnstats import app
from bnstats.models import Beatmap, Nomination, Reset, User
from bnstats.routine import update_user_details
from bnstats.score import NaxessCalculator

logger = logging.getLogger("bnstats")
logger.setLevel(logging.DEBUG)


@pytest.fixture(autouse=True)
def time_freeze():
    f = freeze_time("2020-11-03")
    f.start()
    yield f
    f.stop()


@pytest.fixture
def event_loop(request):
    cfg = Config(".env")
    db_url = cfg.get("TEST_DB_URL", default="sqlite://:memory:")

    loop = asyncio.get_event_loop()
    initializer(["bnstats.models"], db_url=db_url, app_label="models", loop=loop)
    yield loop
    finalizer()
    loop.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
@freeze_time("2020-11-05")
async def setup_db():
    with open("tests/data/sample_user.json") as f:
        u = await User.create(**json.load(f))

    with open("tests/data/nominations.json") as f:
        nom_objs = []
        noms = json.load(f)
        for nom in noms:
            nom["user"] = u
            nom["timestamp"] = parse(nom["timestamp"])
            nom_objs.append(Nomination(**nom))

        await Nomination.bulk_create(nom_objs)

    with open("tests/data/resets.json") as f:
        resets = json.load(f)
        for reset in resets:
            reset["timestamp"] = parse(reset["timestamp"])
            r = await Reset.create(**reset)
            await r.user_affected.add(u)

    with open("tests/data/beatmaps.json") as f:
        objs = []
        maps = json.load(f)
        for bmap in maps:
            objs.append(Beatmap(**bmap))

        await Beatmap.bulk_create(objs)

    objs = []
    for n in nom_objs:
        objs.append(await n.get_map())
    await update_user_details(u, objs)
    await NaxessCalculator().calculate_user(u)
