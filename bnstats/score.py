import logging
import math
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, List, Optional, Type, Union

from tortoise import timezone

from bnstats.bnsite.enums import MapStatus, Mode
from bnstats.helper import mode_to_db
from bnstats.models import BeatmapSet, Nomination, User
from bnstats.models.fields import Score

logger = logging.getLogger("bnstats.score")


class CalculatorABC(ABC):
    """Base class for calculator.

    This class must be used as function standardization in order for consistent
    code style.

    `name`, `has_weight`, `calculate_mapset`, and `calculate_nomination`
    must be overriden for the derived classes.
    """

    name = "abstract"
    has_weight = False

    @abstractmethod
    def get_activity_score(self, nominations: List[Nomination]) -> float:
        pass

    async def get_user_score(
        self, user: User, days: int = 90, mode: Union[Mode, str] = None
    ) -> float:
        """Calculate a user's score.

        Args:
            user (User): User to be calculated.
            days (int, optional): Maximum days of nomination to be accounted. Defaults to 90.
            mode (Union[Mode, str], optional): The game mode to be accounted. Defaults to all game mode.

        Returns:
            float: The user's score.
        """
        date = timezone.now() - timedelta(days)
        activities = await user.get_nomination_activity(date, mode)
        return self.get_activity_score(activities)

    @abstractmethod
    def calculate_mapset(self, beatmap: BeatmapSet) -> float:
        """Calculate a beatmapset's score worth.

        Args:
            beatmap (BeatmapSet): The beatmapset to be calculated.

        Returns:
            float: The beatmapset's score.
        """
        pass

    @abstractmethod
    async def calculate_nomination(self, nom: Nomination) -> Optional[Dict[str, float]]:
        """Calculate a nomination's score.

        Args:
            nom (Nomination): Nomination to be calculated

        Returns:
            Dict[str, float]: Result of nomination calculation.
        """
        pass

    async def _save_nomination_score(
        self, nom: Nomination, score_data: Dict[str, float]
    ):
        new_data = nom.score
        new_data[self.name] = Score(calculator_name=self.name, **score_data)

        update_data = {"score": new_data}
        logger.info("Saving nomination data.")
        nom.update_from_dict(update_data)
        await nom.save()

    async def calculate_user(
        self, user: User, save_to_db: bool = True
    ) -> List[Dict[str, float]]:
        """Calculate and get user's nomination values.

        Args:
            user (User): User to be calculated.
            save_to_db (bool, optional): Whether to save calculated nomination data to database.
                Defaults to True.

        Returns:
            List[Dict[str, float]]: Array of results of each nomination score info.
        """
        logger.info(f"Calculating user: {user.username}")
        logger.info("Fetching activity for last 90 days.")
        d = timezone.now() - timedelta(90)
        activity = await user.get_nomination_activity(d)

        scores = []
        for nom in activity:
            nomination_score = await self.calculate_nomination(nom)
            if not nomination_score:
                continue
            scores.append(nomination_score)

            if save_to_db:
                await self._save_nomination_score(nom, nomination_score)
        return scores


class NaxessCalculator(CalculatorABC):
    name = "naxess"
    has_weight = True
    weight = 0.9

    def get_activity_score(self, nominations: List[Nomination]) -> float:
        nominations.sort(
            key=lambda x: abs(x.score[self.name].total_score), reverse=True
        )
        total_score = 0
        for i, a in enumerate(nominations):
            total_score += a.score[self.name].total_score * (self.weight ** i)
        return total_score

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

        mapper_score = (0.4 ** current_nominator_count) * (0.9 ** other_nominator_count)
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


class RenCalculator(CalculatorABC):
    name = "ren"
    BASE_SCORE = 1
    has_weight = True
    weight = 0.95

    def get_activity_score(self, nominations: List[Nomination]) -> float:
        if not nominations:
            return 0.0

        nominations.sort(
            key=lambda x: abs(x.score[self.name].total_score), reverse=True
        )
        total_score = 0
        for i, a in enumerate(nominations):
            total_score += a.score[self.name].total_score * (self.weight ** i)

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


# fmt: off
_AVAILABLE: Dict[str, Type[CalculatorABC]] = {}
for c in (NaxessCalculator, RenCalculator):
    _AVAILABLE[c.name] = c  # type: ignore

def get_system(name: str) -> Optional[Type[CalculatorABC]]: # noqa
    """Get calculator system from name.

    Args:
        name (str): Calculator system's name to be fetched from

    Returns:
        Type[CalculatorABC]: The calculator's class.
    """
    return _AVAILABLE.get(name)
# fmt: on
