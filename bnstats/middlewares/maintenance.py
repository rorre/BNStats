import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


class MaintenanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if os.path.exists(".maintenance") and "/qat" not in request.url.path:
            return PlainTextResponse("Site in maintenance.", status_code=503)
        else:
            return await call_next(request)
