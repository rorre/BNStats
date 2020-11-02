from datetime import datetime, timedelta
from typing import Any, Awaitable, List

from tortoise import fields, models

from bnstats.bnsite.enums import Difficulty, Genre, Language, MapStatus, Mode
from bnstats.helper import format_time


class Beatmap(models.Model):
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
    def __init__(self, beatmaps: List[Beatmap]):
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
    as_mode = fields.IntField(null=True)
    ambiguous_mode = fields.BooleanField(default=False)
    mapset_score = fields.FloatField(default=0.0)
    mapper_score = fields.FloatField(default=0.0)
    ranked_score = fields.FloatField(default=0.0)
    penalty = fields.FloatField(default=0.0)
    score = fields.FloatField(default=0.0)
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
        users = await cls.all().order_by("username")
        return users

    async def get_nomination_activity(self, date: datetime = None) -> List[Nomination]:
        if not date:
            events = (
                await Nomination.filter(userId=self.osuId).all().order_by("timestamp")
            )
        else:
            events = (
                await Nomination.filter(userId=self.osuId, timestamp__gte=date)
                .all()
                .order_by("timestamp")
            )
        return events

    async def get_score(self, days: int = 90) -> float:
        date = datetime.utcnow() - timedelta(days)
        activities = await self.get_nomination_activity(date)

        total_score = 0
        weight = 0.9
        for i, a in enumerate(activities):
            total_score += a.score * (weight ** i)
        return total_score

    def total_nominations(self) -> Awaitable[int]:
        # As we only redirect the function, we can just use def instead async def.
        return Nomination.filter(userId=self.osuId).count()  # type: ignore
