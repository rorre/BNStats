import functools
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from bnstats.config import DEFAULT_CALC_SYSTEM
from bnstats.score import get_system, _AVAILABLE


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
        system_name = request.session.get("calc_system", "")
        if system_name in _AVAILABLE:
            request.scope["calculator"] = init_system(system_name)
        else:
            request.scope["calculator"] = DEFAULT_CALC_SYSTEM()

        return await call_next(request)
