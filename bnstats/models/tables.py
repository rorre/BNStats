import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Awaitable, Dict, List, Union

from tortoise import fields, models, timezone

from bnstats.bnsite.enums import Difficulty, Genre, Language, MapStatus, Mode
from bnstats.helper import format_time
from bnstats.models.fields import ScoreField
from tortoise.query_utils import Q

if TYPE_CHECKING:
    from bnstats.score.base import CalculatorABC
    from bnstats.score.object import Score

MODE_CONVERTER = {
    "osu": 0,
    "taiko": 1,
    "catch": 2,
    "mania": 3,
}
logger = logging.getLogger("bnstats.models")


class Beatmap(models.Model):
    """osu!beatmap representation.

    This class is used to represent a difficulty in an osu! beatmapset.
    """

    beatmapset_id = fields.IntField()
    beatmap_id = fields.IntField()
    approved = fields.IntField()
    total_length = fields.IntField()
    hit_length = fields.IntField()
    mode = fields.IntField()
    artist = fields.CharField(255)
    title = fields.CharField(255)
    creator = fields.CharField(255)
    creator_id = fields.IntField(default=0)
    tags = fields.TextField()
    genre_id = fields.IntField()
    language_id = fields.IntField()
    difficultyrating = fields.FloatField()

    @property
    def status(self) -> MapStatus:
        return MapStatus(self.approved)

    @property
    def gamemode(self) -> Mode:
        return Mode(self.mode)

    @property
    def language(self) -> Language:
        return Language(self.language_id)

    @property
    def genre(self) -> Genre:
        return Genre(self.genre_id)

    @property
    def difficulty(self) -> Difficulty:
        return Difficulty.from_sr(self.difficultyrating)


class BeatmapSet:
    """osu!mapset representation.

    This class inherits all Beatmap's attribute. Which is useful to
    fetch data effortlessly without going through one of the difficulties
    in the mapset.
    """

    def __init__(self, beatmaps: List[Beatmap]):
        """Initializes BeatmapSet with an array of beatmaps.

        Args:
            beatmaps (List[Beatmap]): Array of beatmaps that will be put
                together as a beatmapset.
        """
        self.beatmaps = beatmaps

    @property
    def total_diffs(self) -> int:
        return len(self.beatmaps)

    @property
    def total_length(self) -> int:
        return sum([b.total_length for b in self.beatmaps])

    @property
    def longest_length(self) -> int:
        return max([b.total_length for b in self.beatmaps])

    @property
    def map_length(self) -> str:
        return format_time(self.longest_length)

    @property
    def top_difficulty(self) -> Beatmap:
        return max([b for b in self.beatmaps], key=lambda x: x.difficultyrating)

    def __getattr__(self, attr: str) -> Any:
        return self.beatmaps[0].__getattribute__(attr)

    # typings derived from 'Beatmap'
    beatmapset_id: int
    beatmap_id: int
    approved: int
    hit_length: int
    mode: int
    artist: str
    title: str
    creator: str
    tags: str
    genre_id: int
    language_id: int
    difficultyrating: float
    gamemode: Mode
    status: MapStatus
    language: Language
    genre: Genre
    difficulty: Difficulty


class Nomination(models.Model):
    beatmapsetId = fields.IntField()
    userId = fields.IntField()
    artistTitle = fields.TextField()
    creatorId = fields.IntField(null=True)
    creatorName = fields.TextField(null=True)
    timestamp = fields.DatetimeField()
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User",
        related_name="nominations",
        null=True,
        on_delete="SET NULL",
    )
    as_modes = fields.JSONField(null=True, default=[])
    ambiguous_mode = fields.BooleanField(default=False)

    # Scoring
    score = ScoreField(null=True)
    map: BeatmapSet

    async def get_map(self) -> BeatmapSet:
        diffs = await Beatmap.filter(beatmapset_id=self.beatmapsetId).all()
        return BeatmapSet(diffs)


class Reset(models.Model):
    id = fields.TextField(pk=True)
    beatmapsetId = fields.IntField()
    userId = fields.IntField()
    artistTitle = fields.TextField()
    creatorId = fields.IntField(null=True)
    creatorName = fields.TextField(null=True)
    timestamp = fields.DatetimeField()
    content = fields.TextField(null=True)
    discussionId = fields.IntField(null=True)
    obviousness = fields.IntField(default=0)
    severity = fields.IntField(default=0)
    type = fields.CharField(50)
    user_affected: fields.ManyToManyRelation["User"] = fields.ManyToManyField(
        "models.User", related_name="resets", through="user_reset"
    )


class User(models.Model):
    _id = fields.TextField()
    osuId = fields.IntField(pk=True)
    username = fields.TextField()
    modesInfo = fields.JSONField()
    isNat = fields.BooleanField()
    isBn = fields.BooleanField()
    modes = fields.JSONField()
    last_updated = fields.DatetimeField(null=True)
    genre_favor = fields.JSONField(null=True)
    lang_favor = fields.JSONField(null=True)
    topdiff_favor = fields.JSONField(null=True)
    size_favor = fields.CharField(20, null=True)
    length_favor = fields.CharField(20, null=True)
    avg_length = fields.IntField(null=True)
    avg_diffs = fields.IntField(null=True)
    nominations: fields.ManyToManyRelation[Nomination]
    resets: fields.ReverseRelation[Reset]

    # Runtime variables
    score: "Score"
    score_modes: Dict[str, "Score"]

    def __repr__(self):
        return f"User(osuId={self.osuId}, username={self.username})"

    @classmethod
    async def get_users(cls, limit: int = None, page: int = None) -> List["User"]:
        """Get all users from database, sorted by username and paginated, if asked.

        If limit is given, then it will use pagination. If page is not given, then
        it will defaults to 0 if limit is defined.

        Args:
            limit (int, optional): Limit result to n users. Defaults to None.
            page (int, optional): Sets the offset to page n. Defaults to None.

        Returns:
            List[User]: All users from database.

        Raises:
            ValueError: If page is given, but not limit.
        """
        if page is not None and not limit:
            raise ValueError("Limit cannot be None or 0 if page is defined.")

        if not limit:
            users = (
                await cls.filter(Q(isBn=True) | Q(isNat=True))
                .all()
                .order_by("username")
            )
            return users

        if not page:
            page = 0

        offset = limit * page
        users = (
            await cls.filter(Q(isBn=True) | Q(isNat=True))
            .limit(limit)
            .offset(offset)
            .order_by("username")
            .all()
        )
        return users

    async def get_nomination_activity(
        self,
        date_min: datetime = None,
        date_max: datetime = None,
        mode: Union[Mode, str, int] = None,
    ) -> List[Nomination]:
        """Fetch user's nomination activities.

        Args:
            date_min (datetime, optional): Minimum date to fetch from. Defaults to None.
            date_max (datetime, optional): Maximum date to fetch from. Defaults to None.
            mode (Union[Mode, str, int], optional): The game mode to fetch from. Defaults to all game mode.

        Returns:
            List[Nomination]: Nominations from user from minimum date to current for specified game mode.
        """
        filters: Dict[str, Any] = {"userId": self.osuId}
        if date_min:
            filters["timestamp__gte"] = date_min

        if date_max:
            filters["timestamp__lte"] = date_max

        if mode:
            if isinstance(mode, Mode):
                filters["as_modes__contains"] = mode.value
            elif isinstance(mode, str):
                filters["as_modes__contains"] = MODE_CONVERTER[mode]
            else:
                filters["as_modes__contains"] = mode

        logger.info("Fetching events.")
        events = await Nomination.filter(**filters).all().order_by("timestamp")
        return events

    def get_score(
        self,
        system: "CalculatorABC",
        days: int = 90,
        mode: Mode = None,
    ) -> Awaitable["Score"]:
        """Get user's score using specified system.

        Args:
            system (CalculatorABC): Scoring system that will be used to calculate.
            days (int, optional): Number of days from now to fetch nomination from. Defaults to 90.
            mode (Mode, optional): Game mode to be calculated. Defaults to None.

        Returns:
            float: The user's score.
        """
        return system.get_user_score(self, days, mode)

    def total_nominations(self, days: int = 0) -> Awaitable[int]:
        """Fetch total nominations of the user.

        Args:
            days (int, optional): Number of days of nominations to count from. Defaults to 0.

        Returns:
            Awaitable[int]: Total nominations done.
        """
        # As we only redirect the function, we can just use def instead async def.
        if days:
            d = timezone.now() - timedelta(days)
            return Nomination.filter(userId=self.osuId, timestamp__gte=d).count()
        return Nomination.filter(userId=self.osuId).count()  # type: ignore

    def to_json(self):
        fields = (
            "_id",
            "osuId",
            "username",
            "modesInfo",
            "isNat",
            "isBn",
            "modes",
            "genre_favor",
            "lang_favor",
            "topdiff_favor",
            "size_favor",
            "length_favor",
            "avg_length",
            "avg_diffs",
        )

        result = {}
        for field in fields:
            result[field] = getattr(self, field)

        return result