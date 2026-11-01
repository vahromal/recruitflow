"""Unified error format: {"error": {"code": "...", "message": "...", "details": ...}}."""
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


def _json_safe(value, depth: int = 0):
    """Make error details JSON-serializable.

    Pydantic validation errors keep the raw exception in `ctx` (e.g. a ValueError
    raised by a custom validator). Passing it straight to JSONResponse raised
    TypeError -> the error handler itself failed with HTTP 500 instead of 422.
    """
    if depth > 8:
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v, depth + 1) for k, v in value.items()}
    return str(value)


def error_response(
    status_code: int, code: str, message: str, details: object = None
) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = _json_safe(details)
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Wrap HTTPException detail into the unified error envelope."""
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail:
            code = str(detail.get("code", "http_error"))
            message = str(detail.get("message", ""))
            extra = detail.get("details")
        else:
            code = "http_error"
            message = str(detail)
            extra = None
        return error_response(exc.status_code, code, message, details=extra)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        # Never leak SQL details to the client.
        return error_response(
            status.HTTP_409_CONFLICT,
            "integrity_error",
            "The operation conflicts with existing data (possible duplicate).",
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "Internal server error",
        )
