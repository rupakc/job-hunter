import pathlib, re
import pytest
ROOT = pathlib.Path(__file__).resolve().parents[1]
CMDS = ["parse-resume", "find-jobs", "tailor-resume", "apply", "job-hunt"]

def test_commands_exist_with_description():
    for c in CMDS:
        p = ROOT / "commands" / f"{c}.md"
        assert p.exists(), f"missing command {c}"
        assert re.match(r"^---\ndescription: .+\n", p.read_text()), f"no frontmatter {c}"

def test_job_hunt_references_top_k_and_modes():
    text = (ROOT / "commands" / "job-hunt.md").read_text()
    assert "--top-k" in text
    assert "assisted" in text and "autonomous" in text

def test_command_frontmatter_is_valid_yaml():
    """Frontmatter must parse as YAML. Catches unquoted values that start with
    a flow-sequence char (e.g. argument-hint: [--top-k N]) which load as empty
    metadata in Claude Code."""
    yaml = pytest.importorskip("yaml")
    for c in CMDS:
        block = re.match(r"^---\n(.*?)\n---", (ROOT / "commands" / f"{c}.md").read_text(), re.DOTALL)
        assert block, f"no frontmatter block in {c}"
        meta = yaml.safe_load(block.group(1))
        assert isinstance(meta, dict), f"frontmatter not a mapping in {c}"
        assert meta.get("description"), f"missing/empty description in {c}"
