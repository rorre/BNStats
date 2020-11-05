from bnstats.helper import format_time


def test_time_formatter():
    assert format_time(90) == "1:30"
    assert format_time(61) == "1:01"
    assert format_time(1 * 60 * 60 + 2 * 60 + 1) == "62:01"
