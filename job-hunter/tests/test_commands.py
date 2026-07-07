import pathlib, re
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
