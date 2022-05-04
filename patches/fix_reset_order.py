
from tortoise import Tortoise, run_async
from starlette.config import Config

from bnstats.models import  Reset, Nomination

config = Config(".env")
DB_URL = config("DB_URL")

async def apply_patch():
    await Tortoise.init(db_url=DB_URL, modules={"models": ["bnstats.models"]})

    resets = await Reset.all().prefetch_related("user_affected")
    for reset in resets:
        await reset.user_affected.clear()
        map_nominations = await Nomination.filter(
            beatmapsetId=reset.beatmapsetId,
            timestamp__lt=reset.timestamp
        ).order_by("-timestamp")
        limit = 1 + (reset.type == "disqualify")

        for nom in map_nominations[:limit]:
            nominator = await nom.user
            if nominator and nominator not in reset.user_affected:
                await reset.user_affected.add(nominator)
        
        await reset.save()

if __name__ == "__main__":
    run_async(apply_patch())
