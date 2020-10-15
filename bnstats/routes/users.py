from collections import Counter

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.routing import Router

from bnstats.models import Beatmap, BeatmapSet, User
from bnstats.plugins import templates

router = Router()


def _format_time(total):
    minutes = total // 60
    seconds = total % 60
    if seconds < 10:
        seconds = f"0{seconds}"
    return f"{minutes}:{seconds}"


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


@router.route("/", name="list")
async def listing(request: Request):
    users = await User.get_users(request)
    counts = [await u.total_nominations() for u in users]
    ctx = {"request": request, "users": users, "counts": counts}
    return templates.TemplateResponse("pages/user/listing.html", ctx)


@router.route("/{user_id:int}", name="show")
async def show_user(request: Request):
    uid: int = request.path_params["user_id"]
    user = await User.get_or_none(osuId=uid)
    if not user:
        raise HTTPException(404, "User not found.")

    nominations = await user.get_nomination_activity(request)

    for nom in nominations:
        nom.map = await nom.get_map()

    graph_labels = {"genre": [], "language": []}
    graph_data = {"genre": [], "language": []}

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

    total_length = sum([nom.map.total_length for nom in nominations])
    total_diffs = sum([nom.map.total_diffs for nom in nominations])
    average_length = total_length // total_diffs
    average_diffs = sum([len(nom.map.beatmaps) for nom in nominations]) // len(
        nominations
    )

    if average_length < 120:
        length = "Short"
    elif average_length < 180:
        length = "Medium"
    else:
        length = "Long"

    size_factor = average_diffs * average_length
    # Anime TV Size 100s NHIX
    if size_factor <= 400:
        size = "Small"
    # Full version (3:30) HIX
    elif size_factor <= 630:
        size = "Medium"
    else:
        size = "Big"

    ctx = {
        "request": request,
        "user": user,
        "nominations": nominations,
        "labels": graph_labels,
        "datas": graph_data,
        "avg_length": _format_time(average_length),
        "avg_diffs": average_diffs,
        "length_favor": length,
        "size_favor": size,
        "genre_favor": counts_genre.most_common(1)[0][0].name,
        "lang_favor": counts_lang.most_common(1)[0][0].name,
        "length_data": _create_length_chartdata(nominations),
    }
    return templates.TemplateResponse("pages/user/show.html", ctx)
