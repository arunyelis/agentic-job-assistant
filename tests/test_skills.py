from pathlib import Path

import pytest

from backend.skills import load_skills, parse_skill, skill_catalog


def test_load_skills_from_markdown(tmp_path: Path):
    (tmp_path / "match.md").write_text(
        "---\nname: match\ndescription: Compare a role\n---\nUse real evidence.",
        encoding="utf-8",
    )

    skills = load_skills(tmp_path)

    assert skills["match"].instructions == "Use real evidence."
    assert skill_catalog(skills) == "- match: Compare a role"


def test_skill_requires_front_matter():
    with pytest.raises(ValueError, match="missing front matter"):
        parse_skill("Just instructions", "broken.md")
