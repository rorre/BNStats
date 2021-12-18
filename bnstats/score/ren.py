import math
import logging
from datetime import timedelta
from typing import Dict, List, Optional

from bnstats.helper import mode_to_db
from bnstats.bnsite.enums import MapStatus
from tortoise import timezone

from bnstats.models import BeatmapSet, Nomination
from bnstats.score.base import CalculatorABC

logger = logging.getLogger("bnstats.score")


class RenCalculator(CalculatorABC):
    BASE_SCORE = 1

    name = "ren"
    has_weight = True
    weight = 0.95

    attributes = {
        "Ranked%": ("ranked_score", "%d"),
        "Mapper%": ("mapper_score", "%d"),
        "Map%": ("mapset_score", "%d"),
        "Penalty": ("penalty", "%0.2f"),
    }

    def get_activity_score(self, nominations: List[Nomination]) -> float:
        if not nominations:
            return 0.0

        nominations.sort(
            key=lambda x: abs(x.score[self.name]["total_score"]),
            reverse=True,
        )

        total_score = 0
        for i, a in enumerate(nominations):
            total_score += a.score[self.name]["total_score"] * (self.weight ** i)

        mappers = set(nom.creatorId for nom in nominations)
        uniqueness = len(mappers) / len(nominations)
        logger.debug(f"Uniqueness: {uniqueness}")
        return total_score * uniqueness

    def calculate_mapset(self, beatmap: BeatmapSet):
        logger.info(
            f"Calculating score for beatmap: ({beatmap.beatmapset_id}) {beatmap.artist} - {beatmap.title} [{beatmap.creator}]"
        )
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
        logger.debug(f"Mapset base: {mapset_base}")

        # Bigger mapset means extra checking for each difficulty
        # And with that, we give bonus to bigger sets.
        bonus_drain = 0.0
        for diff in beatmap.beatmaps:
            # Easier diffs tend to be much easier to check
            # Of course, this is extremely naive especially with how slider is treated.
            bonus_drain += diff.hit_length * (diff.difficultyrating - 5.5) / 5.5
        bonus_drain *= math.log(beatmap.total_diffs, 8)
        logger.debug(f"Bonus drain: {bonus_drain}")

        final_score = round((drain_time + bonus_drain) / mapset_base, 2)
        logger.debug(f"Final score: {final_score}")
        return final_score

    async def calculate_nomination(
        self, nom: Nomination, save_to_db: bool = True
    ) -> Optional[Dict[str, float]]:
        logger.info(
            f"Calculating nomination score for beatmap: ({nom.beatmapsetId}) {nom.artistTitle} [{nom.creatorName})]"
        )

        user = await nom.user
        beatmap = await nom.get_map()
        if not beatmap.beatmaps:
            logger.warning("Beatmap no longer exists in osu!. Skipping.")
            # Skip beatmaps that doesn't exist anymore.
            return None

        # Filter beatmaps only to the mode being nominated.
        nomination_modes = nom.as_modes
        user_modes = [mode_to_db(m) for m in user.modes]
        map_modes = set([diff.mode for diff in beatmap.beatmaps])

        # Fallback to legacy and select all diffs where the nominator could nominate
        if not nomination_modes:
            for mode in user_modes:
                if mode in map_modes:
                    nomination_modes.append(mode)
        logger.debug(f"Mode for nomination: {nomination_modes}")

        diffs = []
        for mode in nomination_modes:
            diffs.extend(list(filter(lambda x: x.mode == mode, beatmap.beatmaps)))
        beatmap = BeatmapSet(diffs)

        # For every found mapper, reduce the score by 75%.
        # Basically, (4/5)^n.
        d = timezone.now() - timedelta(180)
        mapper = beatmap.creator_id
        recurring_mapper_count = (
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

        # Look for other nominator's nominations on same mapper
        # We can assume that if the mapper has more maps that have been nominated before,
        # their sets are easier to check due to their experience in mapping scene.
        other_nominator_noms = await Nomination.filter(
            creatorId=mapper,
            timestamp__gte=d,
            timestamp__lt=nom.timestamp,
            userId__not=user.osuId,
            beatmapsetId__not=nom.beatmapsetId,
        ).all()

        other_nominator_count = 0
        seen_maps = [nom.beatmapsetId]
        for other_nom in other_nominator_noms:
            if other_nom.beatmapsetId in seen_maps:
                continue
            other_nominator_count += 1
            seen_maps.append(other_nom.beatmapsetId)

        mapper_score = 0.8 ** recurring_mapper_count
        mapper_score *= 0.95 ** other_nominator_count
        logger.debug(f"Mapper value: {mapper_score}%")

        resets = await user.resets.filter(beatmapsetId=nom.beatmapsetId).all()
        penalty = 0
        for r in resets:
            total = r.obviousness + r.severity
            # If total is 0, then don't bother calculating.
            if total:
                penalty += (2 ** total) / 8
        logger.debug(f"Penalty: {penalty}")

        ranked_score = ((beatmap.status == MapStatus.Ranked) + 1) / 2
        mapper_score = mapper_score
        mapset_score = self.calculate_mapset(beatmap)

        # Final score
        score = round(self.BASE_SCORE * mapper_score * mapset_score, 2)
        score *= ranked_score
        score -= penalty
        logger.debug(f"Final score: {score}")

        score_data = {
            "ranked_score": ranked_score,
            "mapper_score": mapper_score,
            "mapset_score": self.calculate_mapset(beatmap),
            "penalty": penalty,
            "total_score": score,
        }
        return score_data
