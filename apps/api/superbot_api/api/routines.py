from fastapi import APIRouter

router = APIRouter(prefix="/routines", tags=["routines"])


@router.get("")
async def list_routines() -> list:
    return []
