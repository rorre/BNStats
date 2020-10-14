from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.routing import Route, Mount
from starlette.config import Config


def create_app(config_file=".env"):
    config = Config(config_file)

    DEBUG = config("DEBUG", cast=bool, default=False)
    # DATABASE_URL = config("DATABASE_URL")
    SECRET = config("SECRET")

    # Routes
    from bnstats.routes import home

    routes = [
        Route("/", home.router),
        Mount("/static", StaticFiles(directory="static")),
    ]

    # Middlewares
    middlewares = [
        Middleware(SessionMiddleware, secret_key=SECRET),
        Middleware(GZipMiddleware, minimum_size=1000),
    ]
    app = Starlette(debug=DEBUG, routes=routes, middleware=middlewares)
    return app