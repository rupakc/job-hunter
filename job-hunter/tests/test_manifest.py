import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_plugin_manifest_valid():
    data = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert data["name"] == "job-hunter"
    for key in ("description", "version", "author"):
        assert key in data, f"missing {key}"

def test_mcp_declares_playwright():
    data = json.loads((ROOT / ".mcp.json").read_text())
    assert "playwright" in data
    assert data["playwright"]["command"]

def test_requirements_present():
    reqs = (ROOT / "requirements.txt").read_text()
    for pkg in ("pdfplumber", "python-docx", "playwright", "jinja2"):
        assert pkg in reqs
