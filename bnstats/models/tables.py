import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Awaitable, List, Union

from tortoise import fields, models

from bnstats.bnsite.enums import Difficulty, Genre, Language, MapStatus, Mode
from bnstats.helper import format_time
from bnstats.models.fields import ScoreField


if TYPE_CHECKING:
    from bnstats.score import CalculatorABC

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
        "models.User", related_name="nominations"
    )
    as_modes = fields.JSONField(null=True, default=[])
    ambiguous_mode = fields.BooleanField(default=False)

    # Scoring
    score = ScoreField()
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
    resets: fields.ManyToManyRelation[Reset]

    def __repr__(self):
        return f"User(osuId={self.osuId}, username={self.username})"

    @classmethod
    async def get_users(cls) -> List["User"]:
        """Get all users from database, sorted by username.

        Returns:
            List[User]: All users from database.
        """
        users = await cls.all().order_by("username")
        return users

    async def get_nomination_activity(
        self,
        date: datetime = None,
        mode: Union[Mode, str, int] = None,
    ) -> List[Nomination]:
        """Fetch user's nomination activities.

        Args:
            date (datetime, optional): Minimum date to fetch from. Defaults to None.
            mode (Union[Mode, str, int], optional): The game mode to fetch from. Defaults to all game mode.

        Returns:
            List[Nomination]: Nominations from user from minimum date to current for specified game mode.
        """
        filters = {"userId": self.osuId}
        if date:
            filters["timestamp__gte"] = date

        if mode:
            if type(mode) == Mode:
                filters["as_modes__contains"] = Mode.value
            elif type(mode) == str:
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
    ) -> float:
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
            d = datetime.now() - timedelta(days)
            return Nomination.filter(userId=self.osuId, timestamp__gte=d).count()
        return Nomination.filter(userId=self.osuId).count()  # type: ignore
