from fastapi import APIRouter

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills() -> list:
    return []
