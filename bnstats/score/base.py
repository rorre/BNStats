import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Dict, List, Optional, Tuple, Union

from tortoise import timezone

from bnstats.bnsite.enums import Mode
from bnstats.models import BeatmapSet, Nomination, User

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
    attributes: Dict[str, Tuple[str, str]] = {}

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
        new_data[self.name] = dict(calculator_name=self.name, **score_data)

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
