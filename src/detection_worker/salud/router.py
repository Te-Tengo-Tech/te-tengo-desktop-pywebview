from fastapi import APIRouter

from detection_worker import __version__

router = APIRouter(tags=["salud"])


@router.get("/health")
async def salud() -> dict[str, str]:
    """Liveness para Docker y el proxy inverso."""
    return {"estado": "ok", "version": __version__}
