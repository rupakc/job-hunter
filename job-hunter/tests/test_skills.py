import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
SKILLS = ["resume-parsing", "job-matching", "resume-tailoring",
          "pdf-rendering", "application-filling"]

def test_all_skills_have_valid_frontmatter():
    for s in SKILLS:
        p = ROOT / "skills" / s / "SKILL.md"
        assert p.exists(), f"missing {s}"
        text = p.read_text()
        m = re.match(r"^---\nname: (.+)\ndescription: (.+)\n---", text)
        assert m, f"bad frontmatter in {s}"
        assert m.group(1).strip() == s

def test_tailoring_skill_states_no_hallucination():
    text = (ROOT / "skills" / "resume-tailoring" / "SKILL.md").read_text().lower()
    assert "verify_facts" in text
    assert "hallucinat" in text or "invent" in text
