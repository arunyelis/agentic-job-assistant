from backend.artifacts import safe_name, save_artifact


def test_save_artifact_uses_safe_markdown_name(tmp_path):
    file_name, file_path = save_artifact(tmp_path, "../My Cover Letter!", "Hello")

    assert file_name == "my-cover-letter.md"
    assert file_path.parent == tmp_path
    assert file_path.read_text(encoding="utf-8") == "Hello\n"


def test_safe_name_has_a_fallback():
    assert safe_name("!!!") == "application-note"
