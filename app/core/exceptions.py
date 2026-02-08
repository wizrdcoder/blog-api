from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import traceback
import structlog

logger = structlog.get_logger()


class CustomHTTPException(HTTPException):
    """Custom HTTP exception with additional fields"""

    def __init__(
        self, status_code: int, detail: str, error_code: str = "", extra: dict = {}
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}


def setup_exception_handlers(app: FastAPI):
    """Setup custom exception handlers"""

    @app.exception_handler(CustomHTTPException)
    async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
        error_response = {
            "error": {
                "code": exc.error_code or "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code,
                **exc.extra,
            }
        }
        return JSONResponse(status_code=exc.status_code, content=error_response)

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation error",
                    "errors": errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        # Log the full traceback
        logger.error(
            "unhandled_exception", error=str(exc), traceback=traceback.format_exc()
        )

        # Dont exppose internal erros in production
        if app.debug:
            detail = str(exc)
        else:
            detail = "Internal Server error"

        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": detail}},
        )
