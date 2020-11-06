from datetime import datetime

import pytest

from bnstats.bnsite.enums import Difficulty, Genre, Language, MapStatus, Mode
from bnstats.models import Beatmap, Nomination, Reset, User


@pytest.mark.asyncio
async def test_user():
    users = await User.get_users()
    assert len(users) == 1, "User fetching unmatch!"

    u = users[0]
    noms = await u.get_nomination_activity()
    assert len(noms) == 3, "Nominations fetching unmatch!"

    # Expected: Only Souzou Forest to appear (Nominated on 2020-09-21)
    date_limit = datetime(2020, 9, 20)
    noms = await u.get_nomination_activity(date_limit)
    assert len(noms) == 1, "Nominations datetime fetching unmatch!"

    assert (await u.total_nominations()) == 3, "Total nominations unmatch!"


@pytest.mark.asyncio
async def test_nomination():
    nom = await Nomination.first()
    expected_user = await User.first()
    assert await nom.user == expected_user, "User FK unexpected!"
    assert (await nom.get_map()).beatmaps, "Failed to fetch beatmap!"


@pytest.mark.asyncio
async def test_beatmap():
    bmap = await Beatmap.get(beatmap_id=2198681)
    assert bmap.status == MapStatus.Ranked, "Unmatched map status!"
    assert bmap.gamemode == Mode.Standard, "Unmatched map game mode!"
    assert bmap.language == Language.Japanese, "Unmatched map language!"
    assert bmap.genre == Genre.Video_Game, "Unmatched map genre!"
    assert bmap.difficulty == Difficulty.Extra, "Unmatched map difficulty!"


@pytest.mark.asyncio
async def test_reset():
    event = await Reset.first()
    expected_user = await User.first()
    assert expected_user in (
        await event.user_affected.all()
    ), "User affected FK unexpected!"
