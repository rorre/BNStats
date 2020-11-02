import math
from datetime import datetime, timedelta

from bnstats.bnsite.enums import MapStatus
from bnstats.models import BeatmapSet, Nomination, User

BASE_SCORE = 0.5
BASE_REDUCTION = 0.25  # OBV/SEV reduction
BASE_MAPPER = 1  # 100%
MODES = {"osu": 0, "taiko": 1, "catch": 2, "mania": 3}


def calculate_mapset(beatmap: BeatmapSet):
    multiplier = 0
    for i, b in enumerate(beatmap.beatmaps):
        multiplier += b.hit_length * math.pow(0.8, i)
    multiplier /= 300

    return math.log(1 + multiplier, 2)


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

        mapper = beatmap.creator_id
        mapper_score = BASE_MAPPER

        d = datetime.now() - timedelta(90)
        current_nominator_count = (
            await Nomination.filter(
                creatorId=mapper,
                timestamp__gte=d,
                timestamp__lt=nom.timestamp,
                userId=user.osuId,
                beatmapsetId__not=nom.beatmapsetId,
            )
            .only("beatmapsetId")
            .distinct()
            .count()
        )

        if beatmap.status != MapStatus.Pending:
            other_nominator = (
                await Nomination.filter(
                    beatmapsetId=nom.beatmapsetId, userId__not=user.osuId
                )
                .order_by("-timestamp")
                .only("userId")
                .first()
            )
        else:
            other_nominator = None

        if other_nominator:
            other_nominator_count = (
                await Nomination.filter(
                    creatorId=mapper,
                    timestamp__gte=d,
                    timestamp__lt=nom.timestamp,
                    userId=other_nominator.userId,
                    beatmapsetId__not=nom.beatmapsetId,
                )
                .only("beatmapsetId")
                .distinct()
                .count()
            )
        else:
            other_nominator_count = 0

        if nom.beatmapsetId == 1208022:
            print(current_nominator_count)
            print(other_nominator_count)
        mapper_score = (0.4 ** current_nominator_count) * (0.9 ** other_nominator_count)

        resets = await user.resets.filter(beatmapsetId=nom.beatmapsetId).all()
        penalty = 0
        for r in resets:
            total = r.obviousness + r.severity
            # If total is 0, then don't bother calculating.
            if total > 1:
                penalty += 0.5 * math.pow(2, total - 2)

        nom.ranked_score = math.pow((beatmap.status == MapStatus.Ranked) + 1, 2) / 4
        nom.mapper_score = mapper_score
        nom.mapset_score = calculate_mapset(beatmap)
        nom.penalty = penalty

        nom.score = round(nom.mapper_score * nom.mapset_score * nom.ranked_score, 2)
        nom.score -= nom.penalty

        await nom.save()
