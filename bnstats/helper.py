import binascii
import os
import time
from typing import Union, Optional

MODES = {"osu": 0, "taiko": 1, "catch": 2, "mania": 3}


def format_time(total: int) -> str:
    """Formats seconds into mm:ss format.

    Args:
        total (int): Total seconds that will be converted.

    Returns:
        str: Time formatted as mm:ss.
    """
    minutes = total // 60
    seconds = total % 60
    if seconds < 10:
        seconds = f"0{seconds}"  # type: ignore
    return f"{minutes}:{seconds}"


# https://github.com/mxr/random-object-id/blob/master/random_object_id.py#L9-L12
def generate_mongo_id() -> str:
    """Generate MongoDB styled ID.

    Returns:
        str: Generated ID.
    """
    timestamp = "{:x}".format(int(time.time()))
    rest = binascii.b2a_hex(os.urandom(8)).decode("ascii")
    return timestamp + rest


def mode_to_db(mode_str: str) -> int:
    """Convert mode string to integer enum used by database.

    Args:
        mode_str (str): Mode represented as string, must be either "osu", "taiko", "catch", or "mania.

    Returns:
        int: Integer enum of the specified game mode.
    """
    return MODES[mode_str]


def ensure_int(string: Union[str, int]) -> Optional[int]:
    day_limit = None

    if isinstance(string, str):
        if string.isnumeric():
            day_limit = int(string)
    elif isinstance(string, int):
        day_limit = string

    return day_limit