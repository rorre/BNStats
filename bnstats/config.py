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

INTEROP_USERNAME = config("INTEROP_USERNAME", default="")
INTEROP_PASSWORD = config("INTEROP_PASSWORD", default="")
USE_INTEROP = INTEROP_USERNAME and INTEROP_PASSWORD
USE_AIESS = config("USE_AIESS", cast=bool, default=False)
