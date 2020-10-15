import time
from datetime import datetime, timedelta
from typing import Any, Dict, List
from urllib.parse import urlencode

from dateutil.parser import parse
from starlette.requests import Request
from tortoise import fields, models

from bnstats.bnsite import request
from bnstats.bnsite.enums import Genre, Language, MapStatus, Mode
from bnstats.bnsite.request import cached_request as get


class Beatmap:
    def __init__(self, js):
        self.beatmapset_id: int = int(js.get("beatmapset_id"))
        self.beatmap_id: int = int(js.get("beatmap_id"))
        self.approved: MapStatus = MapStatus(int(js.get("approved")))
        self.total_length: int = int(js.get("total_length"))
        self.hit_length: int = int(js.get("hit_length"))
        self.mode: Mode = Mode(int(js.get("mode")))
        self.artist: str = js.get("artist")
        self.artist_unicode: str = js.get("artist_unicode")
        self.title: str = js.get("title")
        self.title_unicode: str = js.get("title_unicode")
        self.creator: str = js.get("creator")
        self.tags: str = js.get("tags")
        self.genre_id: int = int(js.get("genre_id"))
        self.language_id: int = int(js.get("language_id"))
        self.difficultyrating: float = float(js.get("difficultyrating"))
        self.language: Language = Language(int(self.language_id))
        self.genre: Genre = Genre(int(self.genre_id))


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
    BASE_URL = "https://osu.ppy.sh/api"

    beatmapsetId = fields.IntField()
    userId = fields.IntField()
    artistTitle = fields.TextField()
    creatorId = fields.IntField(null=True)
    creatorName = fields.TextField(null=True)
    timestamp = fields.DatetimeField()

    async def get_map(self) -> BeatmapSet:
        query = {"k": request.api_key, "s": self.beatmapsetId}
        url = self.BASE_URL + "/get_beatmaps?" + urlencode(query)

        r = await get(url, "map", f"{self.beatmapsetId}.json")
        beatmaps = list(map(Beatmap, r))
        return BeatmapSet(beatmaps)


class User(models.Model):
    BASE_URL = "https://bn.mappersguild.com/users"

    _id = fields.TextField()
    osuId = fields.IntField(pk=True)
    username = fields.TextField()
    modesInfo = fields.JSONField()
    isNat = fields.BooleanField()
    isBn = fields.BooleanField()
    modes = fields.JSONField()

    def __repr__(self):
        return f"User(osuId={self.osuId}, username={self.username})"

    @classmethod
    async def get_users(cls, request: Request) -> List["User"]:
        last_update = request.app.state.last_update["user-list"]
        current_time = datetime.now()

        if current_time - last_update > timedelta(minutes=30):
            url = cls.BASE_URL + "/relevantInfo"
            r = await get(url, "users", "listing.json")

            users = []
            for u in r["users"]:
                user = await cls.get_or_none(osuId=u["osuId"])
                if user:
                    user.update_from_dict(u)
                else:
                    user = await cls.create(**u)

                users.append(user)

            request.app.state.last_update["user-list"] = current_time
        else:
            users = await cls.all()
        return users

    async def _fetch_activity(self, days):
        deadline = time.time() * 1000
        url = (
            self.BASE_URL
            + f"/activity?osuId={self.osuId}&"
            + f"modes={','.join(self.modes)}&"
            + f"deadline={deadline}&mongoId={self._id}&"
            + f"days={days}"
        )
        activities: Dict[str, Any] = await get(url, "activity", f"{self.username}.json")
        return activities

    async def get_nomination_activity(self, request, days=90) -> List[Nomination]:
        last_update = datetime.min
        update_states = request.app.state.last_update["user"]
        if self.osuId in update_states:
            last_update = update_states[self.osuId]
        current_time = datetime.now()

        if current_time - last_update > timedelta(minutes=30):
            activities = await self._fetch_activity(days)

            events = []
            for event in activities["uniqueNominations"]:
                db_event = await Nomination.get_or_none(
                    timestamp=parse(event["timestamp"]),
                    userId=event["userId"],
                )

                if not db_event:
                    db_event = await Nomination.create(**event)
                events.append(db_event)
        else:
            events = Nomination.filter(userId=self.osuId).all()

        return events

    def total_nominations(self):
        return Nomination.filter(userId=self.osuId).count()
