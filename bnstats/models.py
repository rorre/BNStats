from typing import List

from tortoise import fields, models

from bnstats.bnsite.enums import Genre, Language, MapStatus, Mode


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
    tags = fields.TextField()
    genre_id = fields.IntField()
    language_id = fields.IntField()
    difficultyrating = fields.FloatField()

    @property
    def status(self):
        return MapStatus(self.approved)

    @property
    def gamemode(self):
        return Mode(self.mode)

    @property
    def language(self):
        return Language(self.language_id)

    @property
    def genre(self):
        return Genre(self.genre_id)


class BeatmapSet:
    def __init__(self, beatmaps: List[Beatmap]):
        self.beatmaps = beatmaps

    @property
    def total_diffs(self):
        return len(self.beatmaps)

    @property
    def total_length(self):
        return sum([b.total_length for b in self.beatmaps])

    @property
    def longest_length(self):
        return max([b.total_length for b in self.beatmaps])

    @property
    def map_length(self):
        longest = self.longest_length
        minutes = longest // 60
        seconds = longest % 60
        if seconds < 10:
            seconds = f"0{seconds}"
        return f"{minutes}:{seconds}"

    def __getattr__(self, attr):
        return self.beatmaps[0].__getattribute__(attr)


class Nomination(models.Model):
    beatmapsetId = fields.IntField()
    userId = fields.IntField()
    artistTitle = fields.TextField()
    creatorId = fields.IntField(null=True)
    creatorName = fields.TextField(null=True)
    timestamp = fields.DatetimeField()
    user = fields.ForeignKeyField("models.User", related_name="nominations")

    async def get_map(self) -> BeatmapSet:
        diffs = await Beatmap.filter(beatmapset_id=self.beatmapsetId).all()
        return BeatmapSet(diffs)


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
    size_favor = fields.CharField(20, null=True)
    length_favor = fields.CharField(20, null=True)
    avg_length = fields.IntField(null=True)
    avg_diffs = fields.IntField(null=True)

    def __repr__(self):
        return f"User(osuId={self.osuId}, username={self.username})"

    @classmethod
    async def get_users(cls) -> List["User"]:
        users = await cls.all().order_by("username")
        return users

    async def get_nomination_activity(self) -> List[Nomination]:
        events = await Nomination.filter(userId=self.osuId).all()
        return events

    def total_nominations(self):
        return Nomination.filter(userId=self.osuId).count()
