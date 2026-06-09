from fastapi import APIRouter, HTTPException

from app.db.session import check_database_connection

router = APIRouter(tags=["database"])


@router.get("/health/db")
def database_health_check() -> dict[str, str]:
    try:
        is_connected = check_database_connection()

        if not is_connected:
            raise HTTPException(
                status_code=503,
                detail="Database health check failed",
            )

        return {
            "status": "ok",
            "database": "postgresql",
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {error}",
        ) from error
