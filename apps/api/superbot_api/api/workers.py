from fastapi import APIRouter

router = APIRouter(prefix="/workers", tags=["workers"])


@router.get("")
async def list_workers() -> list:
    return []
