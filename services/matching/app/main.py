import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import (
    ALGORITHM_VERSION,
    CATEGORY_WEIGHTS,
    QUESTION_SCHEMA_VERSION,
    WEIGHTS_VERSION,
    get_settings,
)
from app.core.logging import configure_logging, request_id_ctx
from app.core.security import verify_internal_service_token

logger = logging.getLogger("matching.http")


class HealthResponse(BaseModel):
    status: str


class MatchingMetaResponse(BaseModel):
    service: str
    algorithm_version: str
    weights_version: str
    question_schema_version: int
    category_weights: dict[str, int]


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    field_errors: dict[str, list[str]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "field_errors": field_errors or {},
                "details": {},
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(environment=settings.environment, level=settings.log_level)

    # Private compute service only — no CORS middleware (TDD.md §9.7)
    app = FastAPI(
        title="RoomSync Private Matching Engine",
        version="0.1.0",
        docs_url="/internal/docs" if settings.environment == "local" else None,
        redoc_url=None,
        openapi_url="/internal/openapi.json" if settings.environment == "local" else None,
    )

    @app.middleware("http")
    async def request_context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        raw_id = request.headers.get("X-Request-ID", "").strip()
        req_id = raw_id if raw_id else str(uuid.uuid4())
        token = request_id_ctx.set(req_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "Unhandled matching service error",
                extra={
                    "structured": {
                        "route": request.url.path,
                        "method": request.method,
                        "status_code": 500,
                        "latency_ms": latency_ms,
                    }
                },
            )
            request_id_ctx.reset(token)
            return _error_response(
                status_code=500,
                code="INTERNAL_ERROR",
                message="Internal compatibility service failure.",
                request_id=req_id,
            )

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        logger.info(
            "Request completed",
            extra={
                "structured": {
                    "route": request.url.path,
                    "method": request.method,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                }
            },
        )
        request_id_ctx.reset(token)
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        code = "AUTH_REQUIRED" if exc.status_code == status.HTTP_401_UNAUTHORIZED else "HTTP_ERROR"
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
            request_id=request_id_ctx.get(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        field_errors: dict[str, list[str]] = {}
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", [])) or "body"
            field_errors.setdefault(loc, []).append(str(err.get("msg", "Invalid value.")))
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="VALIDATION_ERROR",
            message="One or more fields are invalid.",
            request_id=request_id_ctx.get(),
            field_errors=field_errors,
        )

    @app.get("/health/live", response_model=HealthResponse, tags=["Health"])
    async def health_live() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get("/health/ready", response_model=HealthResponse, tags=["Health"])
    async def health_ready(response: Response) -> HealthResponse:
        current = get_settings()
        if not current.is_ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return HealthResponse(status="unavailable")
        return HealthResponse(status="ok")

    internal_router = APIRouter(
        prefix="/internal/v1",
        dependencies=[Depends(verify_internal_service_token)],
        tags=["Internal"],
    )

    @internal_router.get("/meta", response_model=MatchingMetaResponse)
    async def internal_meta() -> MatchingMetaResponse:
        return MatchingMetaResponse(
            service="matching",
            algorithm_version=ALGORITHM_VERSION,
            weights_version=WEIGHTS_VERSION,
            question_schema_version=QUESTION_SCHEMA_VERSION,
            category_weights=CATEGORY_WEIGHTS,
        )

    app.include_router(internal_router)
    return app


app = create_app()
