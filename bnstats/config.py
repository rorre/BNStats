from pydantic import ConfigError
from starlette.config import Config

from bnstats.score import get_system

config = Config(".env")

DEBUG: bool = config("DEBUG", cast=bool, default=False)
SECRET: str = config("SECRET")
DB_URL: str = config("DB_URL")
SITE_SESSION: str = config("BNSITE_SESSION")
API_KEY: str = config("API_KEY")
SENTRY_URL: str = config("SENTRY_URL", default="")

INTEROP_USERNAME: str = config("INTEROP_USERNAME", default="")
INTEROP_PASSWORD: str = config("INTEROP_PASSWORD", default="")
USE_INTEROP: bool = bool(INTEROP_USERNAME and INTEROP_PASSWORD)
USE_AIESS: bool = config("USE_AIESS", cast=bool, default=False)

selected_system = get_system(config("DEFAULT_CALC_SYSTEM"))
if not selected_system:
    raise ConfigError("Calculator system is invalid.")
DEFAULT_CALC_SYSTEM = selected_system
