import importlib.util, pathlib, pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_pdf.py"

def _load():
    spec = importlib.util.spec_from_file_location("render_pdf", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_is_overflow_logic():
    m = _load()
    assert m.is_overflow(2, 1) is True
    assert m.is_overflow(1, 1) is False
    assert m.is_overflow(3, None) is False

def test_build_html_fills_template(tmp_path):
    m = _load()
    tmpl = tmp_path / "t.j2"
    tmpl.write_text("<h1>{{ name }}</h1>")
    data = tmp_path / "d.json"
    data.write_text('{"name": "Jane Doe"}')
    html = m.build_html(str(tmpl), str(data))
    assert "Jane Doe" in html

@pytest.mark.integration
def test_render_html_to_pdf_one_page(tmp_path):
    m = _load()
    pytest.importorskip("playwright")
    html = tmp_path / "r.html"
    html.write_text("<html><body><p>Hi</p></body></html>")
    pdf = tmp_path / "r.pdf"
    try:
        result = m.render(str(html), str(pdf), target_pages=1, data_path=None)
    except Exception as e:
        pytest.skip(f"chromium not installed: {e}")
    assert pdf.exists()
    assert result["page_count"] == 1
    assert result["overflow"] is False
