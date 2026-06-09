from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.incidents import router as incidents_router
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Decision Intelligence API for converting SRE observability signals "
            "into actionable incident context."
        ),
    )

    app.include_router(health_router)
    app.include_router(incidents_router)

    return app


app = create_app()
