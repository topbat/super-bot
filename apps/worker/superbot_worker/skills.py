from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class InvalidSkill(ValueError):
    pass


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    description: str = Field(min_length=3, max_length=500)
    tools: list[str] = Field(default_factory=list)
    model_requirements: dict[str, bool] = Field(default_factory=dict)


class LoadedSkill(SkillMetadata):
    instructions: str
    version: str
    source_path: Path


def load_skill(path: Path) -> LoadedSkill:
    resolved = path.resolve()
    try:
        source = resolved.read_text(encoding="utf-8")
    except OSError as error:
        raise InvalidSkill(f"cannot read skill: {error}") from error
    if not source.startswith("---\n"):
        raise InvalidSkill("skill must start with YAML metadata")
    try:
        raw_metadata, instructions = source[4:].split("\n---\n", maxsplit=1)
    except ValueError as error:
        raise InvalidSkill("skill metadata is not terminated") from error
    try:
        parsed = yaml.safe_load(raw_metadata)
        metadata = SkillMetadata.model_validate(parsed)
    except (yaml.YAMLError, ValidationError, TypeError) as error:
        raise InvalidSkill(f"invalid skill metadata: {error}") from error
    instructions = instructions.strip()
    if not instructions:
        raise InvalidSkill("skill instructions must not be empty")
    return LoadedSkill(
        **metadata.model_dump(),
        instructions=instructions,
        version=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        source_path=resolved,
    )
