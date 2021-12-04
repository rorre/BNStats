import pytest

from bnstats.models import Nomination, User
from bnstats.score import NaxessCalculator, RenCalculator


class FakeNomination:
    def __init__(self, js):
        self._js = js

    def __getattr__(self, name: str) -> float:
        return self._js[name]


@pytest.fixture
def naxess_calculator():
    return NaxessCalculator()


@pytest.fixture
def ren_calculator():
    return RenCalculator()


@pytest.mark.asyncio
async def test_user_naxess(naxess_calculator: NaxessCalculator):
    u = await User.get(pk=1)
    scores = await naxess_calculator.calculate_user(u)
    activities = [FakeNomination(a) for a in scores]
    score = naxess_calculator.get_activity_score(activities)
    # Floating point
    assert f"{score:.2f}" == "3.08", "Incorrect score calculation for user."


@pytest.mark.asyncio
async def test_beatmap_naxess(naxess_calculator: NaxessCalculator):
    m = await Nomination.get(beatmapsetId=1052074)
    beatmap = await m.get_map()
    score = naxess_calculator.calculate_mapset(beatmap)
    assert score == 1.7332097022818713, "Incorrect score calculation for beatmap."


@pytest.mark.asyncio
async def test_user(ren_calculator: RenCalculator):
    u = await User.get(pk=1)
    scores = await ren_calculator.calculate_user(u)
    activities = [FakeNomination(a) for a in scores]
    score = ren_calculator.get_activity_score(activities)
    assert score == 3.53, "Incorrect score calculation for user."


@pytest.mark.asyncio
async def test_beatmap(ren_calculator: RenCalculator):
    m = await Nomination.get(beatmapsetId=1052074)
    beatmap = await m.get_map()
    score = ren_calculator.calculate_mapset(beatmap)
    assert score == 2.09, "Incorrect score calculation for beatmap."
