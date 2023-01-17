import logging
import math
from datetime import timedelta
from typing import Dict, List, Optional

from tortoise import timezone

from bnstats.bnsite.enums import MapStatus
from bnstats.helper import mode_to_db
from bnstats.models import BeatmapSet, Nomination
from bnstats.score.base import CalculatorABC
from bnstats.score.object import Score

logger = logging.getLogger("bnstats.score")


class NaxessCalculator(CalculatorABC):
    name = "naxess"
    has_weight = True
    weight = 0.9

    attributes = {
        "Ranked%": ("ranked_score", "%d"),
        "Mapper%": ("mapper_score", "%d"),
        "Map%": ("mapset_score", "%d"),
        "Penalty": ("penalty", "%0.2f"),
    }

    def get_activity_score(self, nominations: List[Nomination]) -> Score:
        nominations = list(
            filter(lambda x: x.score[self.name] is not None, nominations)
        )
        nominations.sort(
            key=lambda x: abs(x.score[self.name]["total_score"]),
            reverse=True,
        )

        total_score = 0
        for i, a in enumerate(nominations):
            total_score += a.score[self.name]["total_score"] * (self.weight**i)
        return Score(total_score=total_score, attribs={})

    def calculate_mapset(self, beatmap: BeatmapSet):
        length_sorted = sorted(
            beatmap.beatmaps, key=lambda x: x.hit_length, reverse=True
        )

        multiplier = 0.0
        for i, b in enumerate(length_sorted):
            multiplier += b.hit_length * math.pow(0.8, i)
        multiplier /= 300

        return math.log(1 + multiplier, 2)

    async def calculate_nomination(
        self, nom: Nomination, save_to_db: bool = True
    ) -> Optional[Dict[str, float]]:
        logger.info(
            "Calculating nomination score for beatmap: "
            + f"({nom.beatmapsetId}) {nom.artistTitle} [{nom.creatorName})]"
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

        # Fallback to legacy if as_modes isnt set
        # and select all diffs where the nominator could nominate
        if not nomination_modes:
            for mode in user_modes:
                if mode in map_modes:
                    nomination_modes.append(mode)
        logger.debug(f"Mode for nomination: {nomination_modes}")

        diffs = []
        for mode in nomination_modes:
            diffs.extend(list(filter(lambda x: x.mode == mode, beatmap.beatmaps)))
        beatmap = BeatmapSet(diffs)

        mapper = beatmap.creator_id

        # Find if the nominator has nominated other maps from the same mapper
        d = timezone.now() - timedelta(180)
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

        mapper_score = (0.4**current_nominator_count) * (0.9**other_nominator_count)
        logger.debug(
            f"Self: {current_nominator_count} | Other: {other_nominator_count}"
        )
        logger.debug(f"Mapper%: {mapper_score}")

        resets = await user.resets.filter(beatmapsetId=nom.beatmapsetId).all()
        penalty = 0.0
        for r in resets:
            total = r.obviousness + r.severity
            # If total is 0 or 1, then don't bother calculating.
            if total:
                penalty += 0.5 + ((total - 1) / 2 * total)
        logger.debug(f"Penalty: {penalty}")

        # Qualified/Pending: 25%
        # Ranked: 100%
        ranked_score = math.pow((beatmap.status == MapStatus.Ranked) + 1, 2) / 4
        mapset_score = self.calculate_mapset(beatmap)

        # Final score
        score = round(mapper_score * mapset_score * ranked_score, 2)
        score -= penalty
        logger.debug(f"Final score: {score}")

        score_data = {
            "ranked_score": ranked_score,
            "mapper_score": mapper_score,
            "mapset_score": mapset_score,
            "penalty": penalty,
            "total_score": score,
        }
        return score_data
