import functools
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from bnstats.config import DEFAULT_CALC_SYSTEM
from bnstats.score import get_system


@functools.cache
def init_system(name: str):
    calc_system_type = get_system(name)
    if not calc_system_type:
        calc_system_type = DEFAULT_CALC_SYSTEM

    return calc_system_type()


class CalculatorMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request.scope["calculator"] = init_system(
            request.session.get("calc_system", "")
        )
        return await call_next(request)
