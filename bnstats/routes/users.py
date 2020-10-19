import operator
from collections import Counter
from itertools import groupby
from typing import List

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Router

from bnstats.bnsite.enums import Difficulty, Genre, Language
from bnstats.helper import format_time
from bnstats.models import Beatmap, BeatmapSet, Nomination, User
from bnstats.plugins import templates

router = Router()


def _create_length_chartdata(nominations):
    counter = [0, 0, 0, 0, 0, 0]
    for nom in nominations:
        mapset: BeatmapSet = nom.map

        for i in range(1, 6):
            if mapset.longest_length <= i * 60:
                counter[i - 1] += 1
                break

        if mapset.longest_length > 300:
            counter[5] += 1
    return counter


def _create_nomination_chartdata(nominations: List[Nomination]):
    f = operator.attrgetter("timestamp.month", "timestamp.year")
    sorted_nominations = sorted(nominations, key=lambda x: x.timestamp)
    grouped = groupby(sorted_nominations, f)
    nomination_groups = []
    for k, v in grouped:
        nomination_groups.append([k, list(v)])

    # To anyone reading this:
    # If you know a better way to fill in the chart graph, then please let me know.
    # Current one works, but I'm very uncertain about the performance.
    i = len(nomination_groups) - 1
    while i > 0:
        current = nomination_groups[i][0]
        last = nomination_groups[i - 1][0]

        yeargap = 0
        delta = 0
        if current[1] != last[1]:
            if current[0] == 1 and last[0] == 12:
                i -= 1
                continue
            yeargap += 1

        if current[0] - last[0] == 1:
            i -= 1
            continue

        delta += current[0] + 12 * yeargap - last[0]

        new_year = current[1]
        for j in range(1, delta + 1):
            new_month = current[0] - j
            if new_month < 1:
                new_month += 12
                if yeargap > 0:
                    new_year -= 1
                    yeargap -= 1
            nomination_groups.insert(i, ((new_month, new_year), []))

        i -= 1

    labels = []
    datas = []
    for k, v in nomination_groups:
        labels.append("/".join(map(str, k)))
        datas.append(len(list(v)))

    return labels, datas


@router.route("/", name="list")
async def listing(request: Request):
    users = await User.get_users()
    counts = [await u.total_nominations() for u in users]
    ctx = {
        "request": request,
        "users": users,
        "counts": counts,
        "genres": [g.name.replace("_", " ") for g in Genre],
        "languages": [lang.name for lang in Language],
        "diffs": [diff.name for diff in Difficulty],
    }
    return templates.TemplateResponse("pages/user/listing.html", ctx)


@router.route("/{user_id:int}", name="show")
async def show_user(request: Request):
    uid: int = request.path_params["user_id"]
    user = await User.get_or_none(osuId=uid)
    if not user:
        raise HTTPException(404, "User not found.")

    nominations = await user.get_nomination_activity()

    # No nominations present, what even to show?
    if not nominations:
        ctx = {
            "request": request,
            "user": user,
            "error": True,
        }
        return templates.TemplateResponse("pages/user/no_noms.html", ctx)

    invalid_nominations = []
    for nom in nominations:
        nom.map = await nom.get_map()

        # Map is deleted in osu!
        if not nom.map.beatmaps:
            invalid_nominations.append(nom)

    for nom in invalid_nominations:
        nominations.remove(nom)

    graph_labels = {"genre": [], "language": [], "sr-top": [], "sr-all": []}
    graph_data = {"genre": [], "language": [], "sr-top": [], "sr-all": []}

    # Elem is not Beatmap, but BeatmapSet.
    # But since all attr for BeatmapSet redirects to Beatmap, we will just
    # mark it as Beatmap for better code prediction.
    elem: Beatmap

    # Count for genres
    counts_genre = Counter([nom.map.genre for nom in nominations])
    for elem, cnt in counts_genre.items():
        graph_labels["genre"].append(elem.name.replace("_", " "))
        graph_data["genre"].append(cnt)

    # Count for languages
    counts_lang = Counter([nom.map.language for nom in nominations])
    for elem, cnt in counts_lang.items():
        graph_labels["language"].append(elem.name)
        graph_data["language"].append(cnt)

    counts_top = list(
        Counter([nom.map.top_difficulty.difficulty for nom in nominations]).items()
    )
    counts_top.sort(key=lambda x: x[0].value)
    for elem, cnt in counts_top:
        graph_labels["sr-top"].append(elem.name)
        graph_data["sr-top"].append(cnt)

    difficulties = []
    for nom in nominations:
        for map in nom.map.beatmaps:
            difficulties.append(map.difficulty)

    counts_diff = list(Counter(difficulties).items())
    counts_diff.sort(key=lambda x: x[0].value)
    for elem, cnt in counts_diff:
        graph_labels["sr-all"].append(elem.name)
        graph_data["sr-all"].append(cnt)

    line_labels, line_datas = _create_nomination_chartdata(nominations)

    ctx = {
        "request": request,
        "user": user,
        "nominations": nominations,
        "labels": graph_labels,
        "datas": graph_data,
        "avg_length": format_time(user.avg_length),
        "length_data": _create_length_chartdata(nominations),
        "line_labels": line_labels,
        "line_datas": line_datas,
    }
    return templates.TemplateResponse("pages/user/show.html", ctx)
