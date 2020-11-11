import logging

from starlette.applications import Starlette
from starlette.config import Config
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from tortoise.contrib.starlette import register_tortoise

from bnstats.bnsite import request
from bnstats.middlewares.maintenance import MaintenanceMiddleware
from bnstats.routes import home, qat, score, users
from bnstats.score import CalculatorABC, get_system

logger = logging.getLogger("bnstats")

logger.info("Fetching settings.")
config = Config(".env")

DEBUG: bool = config("DEBUG", cast=bool, default=False)
SECRET: str = config("SECRET")
DB_URL: str = config("DB_URL")
SITE_SESSION: str = config("BNSITE_SESSION")
API_KEY: str = config("API_KEY")
CALC_SYSTEM = get_system(config("CALC_SYSTEM"))()

# Setup session for HTTPX
logger.info("Configuring HTTPX.")
request.setup_session(SITE_SESSION, API_KEY)

# Routes
logger.info("Configuring routes.")
routes = [
    Route("/", home.homepage, name="home"),
    Mount("/users", users.router, name="users"),
    Mount("/qat", qat.router, name="qat"),
    Mount("/score", score.router, name="score"),
    Mount("/static", StaticFiles(directory="bnstats/static")),
]

try:
    from bnstats.routes import secret

    logger.info("Secret found, adding secret route.")
    routes.append(Mount("/secret", secret.router, name="secret"))
except ImportError:
    pass
finally:
    routes.append(Mount("/", StaticFiles(directory="bnstats/root")))

# Middlewares
middlewares = [
    Middleware(MaintenanceMiddleware),
    Middleware(SessionMiddleware, secret_key=SECRET),
    Middleware(GZipMiddleware, minimum_size=1000),
]

# Sentry
sentry_url = config("SENTRY_URL", default="")
if sentry_url:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    sentry_sdk.init(sentry_url)
    middlewares.append(Middleware(SentryAsgiMiddleware))

# Application setup
app: Starlette = Starlette(debug=DEBUG, routes=routes, middleware=middlewares)
app.state.calc_system: CalculatorABC = CALC_SYSTEM  # type: ignore

# Database setup
logger.info("Setting up database.")
tortoise_config = {
    "connections": {"default": DB_URL},
    "apps": {
        "models": {
            "models": ["bnstats.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}

register_tortoise(
    app,
    tortoise_config,
    generate_schemas=True,
)