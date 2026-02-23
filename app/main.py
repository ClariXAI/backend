import structlog
from fastapi import FastAPI

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middlewares

logger = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    register_middlewares(app)
    register_exception_handlers(app)

    # Routers will be included here as they are implemented
    # from app.api.v1 import auth, onboarding, ...
    # app.include_router(auth.router, prefix=settings.API_V1_PREFIX)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "version": settings.APP_VERSION}

    logger.info("app_started", name=settings.APP_NAME, version=settings.APP_VERSION)
    return app


app = create_app()
