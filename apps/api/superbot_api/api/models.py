from __future__ import annotations

from fastapi import APIRouter

from superbot_api.models.catalog import ModelSpec, built_in_catalog

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelSpec])
async def list_models() -> list[ModelSpec]:
    return built_in_catalog().list()
