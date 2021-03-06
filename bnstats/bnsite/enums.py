from enum import Enum, IntEnum


class MapStatus(IntEnum):
    Graveyard = -2
    WIP = -1
    Pending = 0
    Ranked = 1
    Approved = 2
    Qualified = 3
    Loved = 4


class Genre(IntEnum):
    Any = 0
    Unspecified = 1
    Video_Game = 2
    Anime = 3
    Rock = 4
    Pop = 5
    Other = 6
    Novelty = 7
    Hip_Hop = 9
    Electronic = 10
    Metal = 11
    Classical = 12
    Folk = 13
    Jazz = 14


class Language(IntEnum):
    Any = 0
    Unspecified = 1
    English = 2
    Japanese = 3
    Chinese = 4
    Instrumental = 5
    Korean = 6
    French = 7
    German = 8
    Swedish = 9
    Spanish = 10
    Italian = 11
    Russian = 12
    Polish = 13
    Other = 14


class Mode(IntEnum):
    Standard = 0
    Taiko = 1
    Catch = 2
    Mania = 3


class Difficulty(Enum):
    Easy = 0
    Normal = 1
    Hard = 2
    Insane = 3
    Extra = 4
    Extreme = 5

    @classmethod
    def from_sr(cls, sr: float):
        if sr >= 6.5:
            return cls.Extreme
        elif sr >= 5.3:
            return cls.Extra
        elif sr >= 4.0:
            return cls.Insane
        elif sr >= 2.7:
            return cls.Hard
        elif sr >= 2.0:
            return cls.Normal
        else:
            return cls.Easy
