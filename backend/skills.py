from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    instructions: str
    file_name: str


def parse_skill(source: str, file_name: str) -> Skill:
    if not source.startswith("---\n") or "\n---\n" not in source[4:]:
        raise ValueError(f"Skill {file_name} is missing front matter")

    front_matter, instructions = source[4:].split("\n---\n", 1)
    metadata: dict[str, str] = {}
    for line in front_matter.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip()

    if not metadata.get("name") or not metadata.get("description"):
        raise ValueError(f"Skill {file_name} needs a name and description")

    return Skill(
        name=metadata["name"],
        description=metadata["description"],
        instructions=instructions.strip(),
        file_name=file_name,
    )


def load_skills(skills_dir: Path) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for file_path in sorted(skills_dir.glob("*.md")):
        skill = parse_skill(file_path.read_text(encoding="utf-8"), file_path.name)
        if skill.name in skills:
            raise ValueError(f"Duplicate skill name: {skill.name}")
        skills[skill.name] = skill
    return skills


def skill_catalog(skills: dict[str, Skill]) -> str:
    return "\n".join(
        f"- {skill.name}: {skill.description}" for skill in skills.values()
    )
