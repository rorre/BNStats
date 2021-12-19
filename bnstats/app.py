import logging

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from tortoise.contrib.starlette import register_tortoise

from bnstats.config import DB_URL, DEBUG, SECRET, SENTRY_URL
from bnstats.middlewares.calculator import CalculatorMiddleware
from bnstats.middlewares.maintenance import MaintenanceMiddleware
from bnstats.routes import home, qat, score, users

logger = logging.getLogger("bnstats")

# Routes
logger.info("Configuring routes.")
routes = [
    Route("/", home.homepage, name="home"),
    Route("/switch", home.switch, name="switch"),
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
    Middleware(CalculatorMiddleware),
    Middleware(GZipMiddleware, minimum_size=1000),
]

# Sentry
if SENTRY_URL:
    import sentry_sdk
    from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

    sentry_sdk.init(SENTRY_URL)
    middlewares.append(Middleware(SentryAsgiMiddleware))

# Application setup
app: Starlette = Starlette(debug=DEBUG, routes=routes, middleware=middlewares)

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
    "use_tz": True,
    "timezone": "UTC",
}

register_tortoise(
    app,
    tortoise_config,
    generate_schemas=True,
)
