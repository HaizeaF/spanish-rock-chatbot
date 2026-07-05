"""Health check endpoint for uptime monitoring."""
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health() -> dict:
    """Report basic service health for uptime checks."""
    return {"status": "ok"}