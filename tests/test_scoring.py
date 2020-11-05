import pytest

from bnstats.models import Nomination, User
from bnstats.score import calculate_mapset, calculate_user


@pytest.mark.asyncio
async def test_user():
    u = await User.get(pk=1)
    await calculate_user(u)

    score = await u.get_score()
    # Floating point
    assert f'{score:.2f}' == '3.08', "Incorrect score calculation for user."


@pytest.mark.asyncio
async def test_beatmap():
    m = await Nomination.get(beatmapsetId=1052074)
    beatmap = await m.get_map()
    score = calculate_mapset(beatmap)
    assert score == 1.7332097022818713, "Incorrect score calculation for beatmap."