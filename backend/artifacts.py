from pathlib import Path


def safe_name(name: str) -> str:
    clean = "".join(character.lower() if character.isalnum() else "-" for character in name)
    clean = "-".join(part for part in clean.split("-") if part)[:70]
    return clean or "application-note"


def save_artifact(output_dir: Path, name: str, content: str) -> tuple[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{safe_name(name)}.md"
    file_path = output_dir / file_name
    file_path.write_text(f"{content.strip()}\n", encoding="utf-8")
    return file_name, file_path
