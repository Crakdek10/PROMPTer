from __future__ import annotations
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api import health, stt_ws
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.providers import router as providers_router
from app.api.llm import router as llm_router
from app.core.errors import AppError

logger = logging.getLogger("app")

def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)

    app = FastAPI(title=settings.APP_NAME)

    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(stt_ws.router)
    app.include_router(providers_router)
    app.include_router(llm_router)
    
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "AppError: %s %s -> %s (%s)",
            request.method,
            request.url.path,
            exc.message,
            exc.code,
            extra={"details": exc.details},
        )
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.warning("RequestValidationError: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "REQUEST_VALIDATION_ERROR","message": "Invalid request","details": exc.errors(),}},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
        )

    return app

app = create_app()