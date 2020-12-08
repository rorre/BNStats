from starlette.config import Config

from bnstats.score import get_system

config = Config(".env")

DEBUG: bool = config("DEBUG", cast=bool, default=False)
SECRET: str = config("SECRET")
DB_URL: str = config("DB_URL")
SITE_SESSION: str = config("BNSITE_SESSION")
API_KEY: str = config("API_KEY")
CALC_SYSTEM = get_system(config("CALC_SYSTEM"))()
SENTRY_URL = config("SENTRY_URL", default="")
