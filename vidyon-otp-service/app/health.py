from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness probe for Render and orchestrators."""
    return {
        "status": "ok",
        "environment": settings.environment,
        "provider": settings.provider,
    }
