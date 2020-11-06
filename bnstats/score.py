import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Type

from bnstats.bnsite.enums import MapStatus
from bnstats.models import BeatmapSet, Nomination, User

logger = logging.getLogger("bnstats.score")
MODES = {"osu": 0, "taiko": 1, "catch": 2, "mania": 3}


class CalculatorABC(ABC):
    name = "abstract"

    @abstractmethod
    def get_activity_score(self, nominations: List[Nomination]) -> float:
        pass

    async def get_user_score(self, user: User, days: int = 90) -> float:
        date = datetime.utcnow() - timedelta(days)
        activities = await user.get_nomination_activity(date)
        return self.get_activity_score(activities)

    @abstractmethod
    def calculate_mapset(self, beatmap: BeatmapSet) -> float:
        pass

    @abstractmethod
    async def calculate_nomination(
        self, nom: Nomination, save_to_db: bool = True
    ) -> Dict[str, float]:
        pass

    async def calculate_user(
        self, user: User, save_to_db: bool = True
    ) -> List[Dict[str, float]]:
        logger.info(f"Calculating user: {user.username}")
        logger.info("Fetching activity for last 90 days.")
        d = datetime.now() - timedelta(90)
        activity = await user.get_nomination_activity(d)

        scores = []
        for nom in activity:
            scores.append(await self.calculate_nomination(nom, save_to_db))
        return scores


class NaxessCalculator(CalculatorABC):
    name = "naxess"

    def get_activity_score(self, nominations: List[Nomination]) -> float:
        total_score = 0
        weight = 0.9
        for i, a in enumerate(nominations):
            total_score += a.score * (weight ** i)
        return total_score

    def calculate_mapset(self, beatmap: BeatmapSet):
        """Calculate a mapset value."""
        logger.info(
            f"Calculating score for beatmap: ({beatmap.beatmapset_id}) {beatmap.artist} - {beatmap.title} [{beatmap.creator}]"
        )
        length_sorted = sorted(
            beatmap.beatmaps, key=lambda x: x.hit_length, reverse=True
        )

        multiplier = 0
        for i, b in enumerate(length_sorted):
            multiplier += b.hit_length * math.pow(0.8, i)
        multiplier /= 300

        return math.log(1 + multiplier, 2)

    async def calculate_nomination(
        self, nom: Nomination, save_to_db: bool = True
    ) -> Dict[str, float]:
        logger.info(
            f"Calculating nomination score for beatmap: ({nom.beatmapsetId}) {nom.artistTitle} [{nom.creatorName})]"
        )

        user = await nom.user
        beatmap = await nom.get_map()
        if not beatmap.beatmaps:
            logger.warn("Beatmap no longer exists in osu!. Skipping.")
            # Skip beatmaps that doesn't exist anymore.
            return

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
        ranked_score = math.pow((beatmap.status == MapStatus.Ranked) + 1, 2) / 4
        mapset_score = self.calculate_mapset(beatmap)

        # Final score
        score = round(mapper_score * mapset_score * ranked_score, 2)
        score -= penalty
        logger.debug(f"Final score: {score}")

        update_data = {
            "ranked_score": ranked_score,
            "mapper_score": mapper_score,
            "mapset_score": mapset_score,
            "penalty": penalty,
            "score": score,
        }

        if save_to_db:
            logger.info("Saving nomination data.")
            nom.update_from_dict(update_data)
            await nom.save()
        return update_data


class RenCalculator(CalculatorABC):
    name = "ren"
    BASE_SCORE = 0.5

    def get_activity_score(self, nominations: List[Nomination]) -> float:
        return sum([a.score for a in nominations])

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
        bonus_drain = 0
        for diff in beatmap.beatmaps:
            # Easier diffs tend to be much easier to check
            # Of course, this is extremely naive especially with how slider is treated.
            bonus_drain += diff.hit_length * diff.difficultyrating / 5.5
        bonus_drain *= math.log(beatmap.total_diffs, 4)
        logger.debug(f"Bonus drain: {bonus_drain}")

        final_score = round((drain_time + bonus_drain) / mapset_base / 2, 2)
        logger.debug(f"Final score: {final_score}")
        return final_score

    async def calculate_nomination(
        self, nom: Nomination, save_to_db: bool = True
    ) -> Dict[str, float]:
        logger.info(
            f"Calculating nomination score for beatmap: ({nom.beatmapsetId}) {nom.artistTitle} [{nom.creatorName})]"
        )

        user = await nom.user
        beatmap = await nom.get_map()
        if not beatmap.beatmaps:
            logger.warn("Beatmap no longer exists in osu!. Skipping.")
            # Skip beatmaps that doesn't exist anymore.
            return

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

        # For every found mapper, reduce the score by 75%.
        # Basically, (1/4)^n.
        d = datetime.now() - timedelta(90)
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
        mapper_score = 0.25 ** recurring_mapper_count
        logger.debug(f"Mapper value: {mapper_score}%")

        resets = await user.resets.filter(beatmapsetId=nom.beatmapsetId).all()
        penalty = 0
        for r in resets:
            total = r.obviousness + r.severity
            # If total is 0, then don't bother calculating.
            if total:
                penalty += (2 ** total) / 8
        logger.debug(f"Penalty: {penalty}")

        ranked_score = (beatmap.status == MapStatus.Ranked) / 2
        mapper_score = mapper_score
        mapset_score = self.calculate_mapset(beatmap)

        # Final score
        score = round(self.BASE_SCORE * mapper_score * mapset_score, 2)
        score += ranked_score
        score -= penalty
        logger.debug(f"Final score: {score}")

        update_data = {
            "ranked_score": ranked_score,
            "mapper_score": mapper_score,
            "mapset_score": self.calculate_mapset(beatmap),
            "penalty": penalty,
            "score": score,
        }

        if save_to_db:
            logger.info("Saving nomination data.")
            nom.update_from_dict(update_data)
            await nom.save()
        return update_data


def get_system(name: str) -> Type[CalculatorABC]:
    _AVAILABLE: Dict[str, Type[CalculatorABC]] = {
        c.name: c for c in [NaxessCalculator, RenCalculator]
    }
    return _AVAILABLE[name]
