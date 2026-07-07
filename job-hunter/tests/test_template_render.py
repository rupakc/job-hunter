import importlib.util, json, pathlib, pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_pdf.py"
TMPL = ROOT / "templates" / "resume.html.j2"
DATA = ROOT / "tests" / "fixtures" / "sample_resume_data.json"

def _load():
    spec = importlib.util.spec_from_file_location("render_pdf", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_template_renders_core_fields():
    m = _load()
    html = m.build_html(str(TMPL), str(DATA))
    data = json.loads(DATA.read_text())
    assert data["name"] in html
    assert data["experience"][0]["company"] in html
    assert data["skills"][0] in html

def test_template_handles_missing_optionals(tmp_path):
    m = _load()
    minimal = tmp_path / "min.json"
    minimal.write_text(json.dumps({"name": "X", "title": "Y",
        "contact": {"email": "x@y.com"}, "summary": "", "skills": [],
        "experience": [], "education": [], "extras": []}))
    html = m.build_html(str(TMPL), str(minimal))
    assert "X" in html  # renders without KeyError
