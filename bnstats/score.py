import math
from datetime import datetime, timedelta

from bnstats.bnsite.enums import MapStatus
from bnstats.models import BeatmapSet, User

BASE_SCORE = 0.5
BASE_REDUCTION = 0.5  # OBV/SEV reduction
BASE_MAPPER = 1  # 100%
MODES = {"osu": 0, "taiko": 1, "catch": 2, "mania": 3}


def calculate_mapset(beatmap: BeatmapSet):
    drain_times = [diff.hit_length for diff in beatmap.beatmaps]
    drain_time = sum(drain_times)

    # Expect all maps to be above 300s (5:00) of total drain time
    # This would be:
    # 5:00 * 1 diff
    # 1:30 * 4 diff
    #
    # If there are more diffs, we expect the map to have longer drain time
    # so that it is more or less normalized.
    mapset_base = 300 + (120 * beatmap.total_diffs / 4) * (
        math.log(beatmap.total_diffs / 4) + 0.601
    )

    # Bigger mapset means extra checking for each difficulty
    # And with that, we give bonus to bigger sets.
    bonus_drain = 0
    for diff in beatmap.beatmaps:
        # Easier diffs tend to be much easier to check
        # Of course, this is extremely naive especially with how slider is treated.
        bonus_drain += diff.hit_length * diff.difficultyrating / 5.5
    bonus_drain *= math.log(beatmap.total_diffs, 4)

    final_score = (drain_time + bonus_drain) / mapset_base
    return round(final_score / 2, 2)


async def calculate_user(user: User):
    nominated_mappers = []

    d = datetime.now() - timedelta(90)
    activity = await user.get_nomination_activity(d)
    for nom in activity:
        beatmap = await nom.get_map()
        if not beatmap.beatmaps:
            # Skip beatmaps that doesn't exist anymore.
            continue

        # Filter beatmaps only to the mode being nominated.
        user_modes = [MODES[m] for m in user.modes]
        map_modes = set([diff.mode for diff in beatmap.beatmaps])

        nomination_mode = nom.as_mode
        if not nomination_mode:
            for mode in user_modes:
                if mode in map_modes:
                    if nomination_mode:
                        # Hybrid map with hybrid BN, can't tell which mode is it.
                        nom.ambiguous_mode = True
                        await nom.save()
                        return
                    else:
                        nomination_mode = mode

        beatmap = BeatmapSet(
            list(filter(lambda x: x.mode == nomination_mode, beatmap.beatmaps))
        )

        mapper = beatmap.creator
        mapper_score = BASE_MAPPER

        # For every found mapper, reduce the score by 75%.
        # Basically, (1/4)^n.
        for u in nominated_mappers:
            if mapper == u:
                mapper_score *= 0.25
        nominated_mappers.append(mapper)

        resets = await user.resets.filter(beatmapsetId=nom.beatmapsetId).all()
        penalty_multiplier = 0
        for r in resets:
            penalty_multiplier += r.severity + r.obviousness

        nom.ranked_score = (beatmap.status == MapStatus.Ranked) / 2
        nom.mapper_score = mapper_score
        nom.mapset_score = calculate_mapset(beatmap)
        nom.penalty = penalty_multiplier * 0.5

        nom.score = round(BASE_SCORE * nom.mapper_score * nom.mapset_score, 2)
        nom.score += nom.ranked_score
        nom.score -= nom.penalty

        await nom.save()
