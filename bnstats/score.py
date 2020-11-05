import logging
import math
from datetime import datetime, timedelta

from bnstats.bnsite.enums import MapStatus
from bnstats.models import BeatmapSet, Nomination, User

logger = logging.getLogger("bnstats.score")
MODES = {"osu": 0, "taiko": 1, "catch": 2, "mania": 3}


def calculate_mapset(beatmap: BeatmapSet):
    """Calculate a mapset value."""
    logger.info(
        f"Calculating score for beatmap: ({beatmap.beatmapset_id}) {beatmap.artist} - {beatmap.title} [{beatmap.creator}]"
    )
    length_sorted = sorted(beatmap.beatmaps, key=lambda x: x.hit_length, reverse=True)

    multiplier = 0
    for i, b in enumerate(length_sorted):
        multiplier += b.hit_length * math.pow(0.8, i)
    multiplier /= 300

    return math.log(1 + multiplier, 2)


async def calculate_user(user: User):
    """Calculate all of user score and save to database."""
    logger.info(f"Calculating user: {user.username}")
    logger.info("Fetching activity for last 90 days.")
    d = datetime.now() - timedelta(90)
    activity = await user.get_nomination_activity(d)
    for nom in activity:
        logger.info(
            f"Calculating nomination score for beatmap: ({nom.beatmapsetId}) {nom.artistTitle} [{nom.creatorName})]"
        )
        beatmap = await nom.get_map()
        if not beatmap.beatmaps:
            logger.warn("Beatmap no longer exists in osu!. Skipping.")
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
                        logger.warn(
                            f"Cannot determine nominated mode for user {user.username}. Skipping"
                        )
                        # Hybrid map with hybrid BN, can't tell which mode is it.
                        nom.ambiguous_mode = True
                        await nom.save()
                        return
                    else:
                        nomination_mode = mode
        logger.debug(f"Mode for nomination: {nomination_mode}")

        beatmap = BeatmapSet(
            list(filter(lambda x: x.mode == nomination_mode, beatmap.beatmaps))
        )

        mapper = beatmap.creator_id

        # Find if the nominator has nominated other maps from the same mapper
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

        # If a map is not in pending, then find 2nd BN as they're qualified/ranked.
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
            # Find if 2nd nominator has nominated other maps from the same mapper
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

        mapper_score = (0.4 ** current_nominator_count) * (0.9 ** other_nominator_count)
        logger.debug(f"Mapper%: {mapper_score}")

        resets = await user.resets.filter(beatmapsetId=nom.beatmapsetId).all()
        penalty = 0
        for r in resets:
            total = r.obviousness + r.severity
            # If total is 0 or 1, then don't bother calculating.
            if total > 1:
                penalty += 0.5 * math.pow(2, total - 2)
        logger.debug(f"Penalty: {penalty}")

        # Qualified/Pending: 25%
        # Ranked: 100%
        nom.ranked_score = math.pow((beatmap.status == MapStatus.Ranked) + 1, 2) / 4
        nom.mapper_score = mapper_score
        nom.mapset_score = calculate_mapset(beatmap)
        nom.penalty = penalty

        nom.score = round(nom.mapper_score * nom.mapset_score * nom.ranked_score, 2)
        nom.score -= nom.penalty
        logger.debug(f"Final score: {nom.score}")

        logger.info("Saving nomination data.")
        await nom.save()
