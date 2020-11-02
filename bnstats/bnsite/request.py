import json
import os

import aiofiles
import httpx

s: httpx.AsyncClient = httpx.AsyncClient(timeout=60.0)
api_key = ""


def setup_session(session, osu_key):
    global api_key, s

    api_key = osu_key
    s.cookies.set(domain="bn.mappersguild.com", name="connect.sid", value=session)


async def get(url, is_json=True, attempts=5):
    current_attempt = 1
    while current_attempt <= attempts:
        try:
            r = await s.get(url)
        except BaseException as e:
            current_attempt += 1

            # Reraise if we already give too many attempts
            if current_attempt > attempts:
                raise e
            continue

        r.raise_for_status()
        break
    if is_json:
        _result = r.json()
    else:
        _result = r.text
    return _result


async def cached_request(url, t, filename, is_json=True):
    filepath = f"cache/{t}/{filename}"

    os.makedirs(f"cache/{t}/", exist_ok=True)
    if os.path.exists(filepath):
        async with aiofiles.open(filepath) as f:
            js_text = await f.read()
            return json.loads(js_text) if is_json else js_text

    result = await get(url, is_json)
    if is_json:
        result_str = json.dumps(result)
    else:
        result_str = result

    async with aiofiles.open(filepath, "w") as f:
        await f.write(result_str)
    return result
