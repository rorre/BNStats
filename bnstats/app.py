from datetime import datetime

from starlette.applications import Starlette
from starlette.config import Config
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles
from tortoise.contrib.starlette import register_tortoise

from bnstats.bnsite import request
from bnstats.routes import home, users
from bnstats.routine import setup_routine

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)
SECRET = config("SECRET")
DB_URL = config("DB_URL")
SITE_SESSION = config("BNSITE_SESSION")
API_KEY = config("API_KEY")

request.setup_session(SITE_SESSION, API_KEY)

# Routes
routes = [
    Route("/", home.homepage, name="home"),
    Mount("/users", users.router, name="users"),
    Mount("/static", StaticFiles(directory="bnstats/static")),
]

# Middlewares
middlewares = [
    Middleware(SessionMiddleware, secret_key=SECRET),
    Middleware(GZipMiddleware, minimum_size=1000),
]

# Application setup
app = Starlette(debug=DEBUG, routes=routes, middleware=middlewares)
app.state.last_update = {
    "user-list": datetime.min,  # User listing
    "user": {},  # Per user activity updates
}
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
setup_routine(app)
