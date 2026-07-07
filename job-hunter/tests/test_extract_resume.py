import json, subprocess, sys, pathlib, importlib.util

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "extract_resume.py"

def _load():
    spec = importlib.util.spec_from_file_location("extract_resume", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_estimate_pages_minimum_one():
    m = _load()
    assert m.estimate_pages_from_text("") == 1
    assert m.estimate_pages_from_text("\n" * 90) >= 2

def test_extract_txt(tmp_path):
    m = _load()
    f = tmp_path / "r.txt"
    f.write_text("Jane Doe\nSenior Engineer\nPython, SQL\n")
    result = m.extract(str(f))
    assert "Senior Engineer" in result["raw_text"]
    assert result["original_page_count"] >= 1

def test_cli_writes_profile(tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("Hello world resume")
    out = tmp_path / "profile.json"
    subprocess.run([sys.executable, str(SCRIPT), str(f), "-o", str(out)], check=True)
    data = json.loads(out.read_text())
    assert data["raw_text"].startswith("Hello world")

def test_unsupported_extension(tmp_path):
    m = _load()
    f = tmp_path / "r.rtf"
    f.write_text("x")
    try:
        m.extract(str(f))
        assert False, "should raise"
    except ValueError:
        pass
