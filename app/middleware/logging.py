import time
import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests"""

    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log request
        log_data = {
            "method": request.method,
            "url": str(request.url),
            "status_code": response.status_code,
            "process_time": process_time,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        # Add user info if available
        if hasattr(request.state, "user"):
            log_data["user_id"] = request.state.user.id
            log_data["user_email"] = request.state.user.email

        # Log based on status code
        if response.status_code >= 500:
            logger.error("server_error", **log_data)
        elif response.status_code >= 400:
            logger.warning("client_error", **log_data)
        else:
            logger.info("request", **log_data)

        return response
