from __future__ import annotations

from pathlib import Path

import pytest
from superbot_worker.skills import InvalidSkill, load_skill


def test_skill_frontmatter_is_parsed_and_versioned(tmp_path: Path) -> None:
    skill_path = tmp_path / "research" / "SKILL.md"
    skill_path.parent.mkdir()
    skill_path.write_text(
        """---
name: source-research
description: Research primary sources
tools:
  - http.get
model_requirements:
  tool_calling: true
---
# Workflow

Find primary sources and cite them.
""",
        encoding="utf-8",
    )

    skill = load_skill(skill_path)

    assert skill.name == "source-research"
    assert skill.tools == ["http.get"]
    assert skill.instructions.startswith("# Workflow")
    assert len(skill.version) == 64
    assert skill.version == load_skill(skill_path).version


def test_skill_rejects_unknown_metadata(tmp_path: Path) -> None:
    skill_path = tmp_path / "SKILL.md"
    skill_path.write_text(
        "---\nname: unsafe\ndescription: no\nshell: unrestricted\n---\nDo it.",
        encoding="utf-8",
    )

    with pytest.raises(InvalidSkill, match="metadata"):
        load_skill(skill_path)
