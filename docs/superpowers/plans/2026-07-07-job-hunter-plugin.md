# Job-Hunter Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code plugin (`job-hunter`) that parses a resume, finds matching jobs, tailors a length-matched hallucination-free PDF resume per job, and auto-fills the application (assisted or autonomous).

**Architecture:** Three deterministic Python scripts (extract, render, verify) do the mechanical work; five Skills encode the "how-to"; five slash commands drive the flow. Playwright/Chromium (declared as an MCP server) handles both browser automation and HTML→PDF rendering.

**Tech Stack:** Python 3, Playwright (Chromium), pdfplumber, python-docx, Jinja2, Claude Code plugin (commands + skills + `.mcp.json`).

## Global Constraints

- **Language:** Python 3 for all scripts; no other runtime.
- **Same length:** tailored PDF page count MUST equal `original_page_count`; enforced by `render_pdf.py` exit code 2 on overflow.
- **No hallucination:** every numeric fact (years, %, currency, counts) and contact detail in the tailored resume MUST exist in the original; enforced by `verify_facts.py` exit code 1.
- **Top-K configurable:** the number of jobs presented is a flag (`--top-k`), default 10, NEVER hardcoded.
- **Plugin manifest format:** `.claude-plugin/plugin.json` with `name`, `description`, `version`, `author`; MCP servers in root `.mcp.json` as `{ "<name>": {"command","args"} }` (no `mcpServers` wrapper).
- **SKILL frontmatter:** `---\nname: <kebab>\ndescription: <when-to-use>\n---`.
- **Plugin root:** `job-hunter/` at repo root. All paths below are relative to it unless noted.
- **Tests:** `pytest`; test files under `job-hunter/tests/`.

---

## File Structure

- `job-hunter/.claude-plugin/plugin.json` — manifest
- `job-hunter/.mcp.json` — Playwright MCP server declaration
- `job-hunter/requirements.txt` — Python deps
- `job-hunter/scripts/extract_resume.py` — PDF/DOCX/TXT → `profile.json`
- `job-hunter/scripts/render_pdf.py` — Jinja/HTML → Chromium PDF + page-count gate
- `job-hunter/scripts/verify_facts.py` — tailored-vs-original fact diff
- `job-hunter/templates/resume.html.j2` — resume template + print CSS
- `job-hunter/skills/{resume-parsing,job-matching,resume-tailoring,pdf-rendering,application-filling}/SKILL.md`
- `job-hunter/commands/{parse-resume,find-jobs,tailor-resume,apply,job-hunt}.md`
- `job-hunter/tests/{test_extract_resume.py,test_render_pdf.py,test_verify_facts.py,fixtures/}`
- `job-hunter/README.md`

---

## Task 1: Plugin scaffolding & manifest

**Files:**
- Create: `job-hunter/.claude-plugin/plugin.json`
- Create: `job-hunter/.mcp.json`
- Create: `job-hunter/requirements.txt`
- Test: `job-hunter/tests/test_manifest.py`

**Interfaces:**
- Produces: a valid plugin directory that Claude Code can load; other tasks add files into it.

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_manifest.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_manifest.py -v`
Expected: FAIL (files do not exist / FileNotFoundError).

- [ ] **Step 3: Create the manifest, MCP config, and requirements**

```json
// job-hunter/.claude-plugin/plugin.json
{
  "name": "job-hunter",
  "description": "Parse a resume, find matching jobs, tailor a length-matched hallucination-free PDF per job, and auto-fill applications (assisted or autonomous).",
  "version": "0.1.0",
  "author": { "name": "job-hunter contributors" },
  "keywords": ["resume", "jobs", "applications", "pdf", "automation"]
}
```

```json
// job-hunter/.mcp.json
{
  "playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"]
  }
}
```

```
# job-hunter/requirements.txt
pdfplumber>=0.11
python-docx>=1.1
playwright>=1.44
jinja2>=3.1
pytest>=8.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter && python -m pytest tests/test_manifest.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add job-hunter/.claude-plugin/plugin.json job-hunter/.mcp.json job-hunter/requirements.txt job-hunter/tests/test_manifest.py
git commit -m "feat: scaffold job-hunter plugin manifest and MCP config"
```

---

## Task 2: extract_resume.py (PDF/DOCX/TXT → profile.json)

**Files:**
- Create: `job-hunter/scripts/extract_resume.py`
- Test: `job-hunter/tests/test_extract_resume.py`

**Interfaces:**
- Produces:
  - `extract(path: str) -> dict` returning `{"source_path", "raw_text", "original_page_count"}`.
  - `estimate_pages_from_text(text: str) -> int`.
  - CLI: `python extract_resume.py <input> -o profile.json` printing a JSON summary.
- Consumed by: Task 4 (`verify_facts` reads `profile.json`), parse-resume command.

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_extract_resume.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_extract_resume.py -v`
Expected: FAIL (module/file not found).

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Extract raw text and page count from a resume (PDF/DOCX/TXT) into profile.json."""
import argparse, json, os, sys

LINES_PER_PAGE = 45

def estimate_pages_from_text(text: str) -> int:
    lines = text.count("\n") + 1
    return max(1, (lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE)

def extract_pdf(path: str):
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts), page_count

def extract_docx(path: str):
    import docx
    doc = docx.Document(path)
    text = "\n".join(p.text for p in doc.paragraphs)
    return text, estimate_pages_from_text(text)

def extract_txt(path: str):
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    return text, estimate_pages_from_text(text)

def extract(path: str) -> dict:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text, pages = extract_pdf(path)
    elif ext == ".docx":
        text, pages = extract_docx(path)
    elif ext in (".txt", ".text"):
        text, pages = extract_txt(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return {"source_path": os.path.abspath(path), "raw_text": text,
            "original_page_count": pages}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Extract resume text + page count")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default="profile.json")
    args = ap.parse_args(argv)
    result = extract(args.input)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
    print(json.dumps({"page_count": result["original_page_count"],
                      "chars": len(result["raw_text"]), "output": args.output}))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter && python -m pytest tests/test_extract_resume.py -v`
Expected: PASS (4 tests). (PDF/DOCX branches exercised in Task 5's end-to-end; TXT path fully covered here.)

- [ ] **Step 5: Commit**

```bash
git add job-hunter/scripts/extract_resume.py job-hunter/tests/test_extract_resume.py
git commit -m "feat: add resume extraction script (PDF/DOCX/TXT)"
```

---

## Task 3: render_pdf.py (Jinja/HTML → Chromium PDF + length gate)

**Files:**
- Create: `job-hunter/scripts/render_pdf.py`
- Test: `job-hunter/tests/test_render_pdf.py`

**Interfaces:**
- Produces:
  - `is_overflow(pages: int, target_pages: int | None) -> bool`.
  - `build_html(template_path: str, data_path: str) -> str` (Jinja render).
  - `count_pages(pdf_path: str) -> int`.
  - `render(input_path: str, pdf_path: str, target_pages: int | None, data_path: str | None) -> dict` returning `{"pdf_path","page_count","target_pages","overflow","html_path"}`.
  - CLI: `python render_pdf.py <input.html|input.j2> <out.pdf> [--data data.json] [--target-pages N]`; exit 2 on overflow.
- Consumed by: tailor-resume / pdf-rendering skill (length loop), template task.

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_render_pdf.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_render_pdf.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Render a resume (HTML or Jinja template + data JSON) to PDF via Chromium.
Exit code 2 signals the PDF exceeds the target page count (length overflow)."""
import argparse, json, os, pathlib, sys

def is_overflow(pages: int, target_pages) -> bool:
    return target_pages is not None and pages > target_pages

def build_html(template_path: str, data_path: str) -> str:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    tdir = os.path.dirname(os.path.abspath(template_path)) or "."
    env = Environment(loader=FileSystemLoader(tdir),
                      autoescape=select_autoescape(["html", "j2"]))
    tmpl = env.get_template(os.path.basename(template_path))
    with open(data_path, encoding="utf-8") as fh:
        data = json.load(fh)
    return tmpl.render(**data)

def count_pages(pdf_path: str) -> int:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)

def render(input_path: str, pdf_path: str, target_pages, data_path=None) -> dict:
    if input_path.endswith(".j2"):
        if not data_path:
            raise ValueError("Jinja template requires --data")
        html = build_html(input_path, data_path)
        html_path = os.path.splitext(pdf_path)[0] + ".html"
        pathlib.Path(html_path).write_text(html, encoding="utf-8")
    else:
        html_path = input_path
    from playwright.sync_api import sync_playwright
    uri = pathlib.Path(html_path).resolve().as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(uri, wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    pages = count_pages(pdf_path)
    return {"pdf_path": pdf_path, "page_count": pages, "target_pages": target_pages,
            "overflow": is_overflow(pages, target_pages), "html_path": html_path}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Render resume HTML/template to PDF")
    ap.add_argument("input", help="path to .html or .j2 template")
    ap.add_argument("pdf", help="output PDF path")
    ap.add_argument("--data", default=None, help="JSON data for a .j2 template")
    ap.add_argument("--target-pages", type=int, default=None)
    args = ap.parse_args(argv)
    result = render(args.input, args.pdf, args.target_pages, args.data)
    print(json.dumps(result))
    sys.exit(2 if result["overflow"] else 0)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter && python -m pytest tests/test_render_pdf.py -v`
Expected: PASS for `test_is_overflow_logic` and `test_build_html_fills_template`; the integration test PASSES if chromium is installed (`playwright install chromium`) or SKIPS otherwise.

- [ ] **Step 5: Commit**

```bash
git add job-hunter/scripts/render_pdf.py job-hunter/tests/test_render_pdf.py
git commit -m "feat: add PDF renderer with page-count length gate"
```

---

## Task 4: verify_facts.py (anti-hallucination fact diff)

**Files:**
- Create: `job-hunter/scripts/verify_facts.py`
- Test: `job-hunter/tests/test_verify_facts.py`

**Interfaces:**
- Produces:
  - `extract_numbers(text: str) -> set[str]` — normalized numeric tokens (years, integers, decimals, percentages, currency digits).
  - `extract_contacts(text: str) -> dict` with `emails: set`, `phones: set`.
  - `verify(tailored_text: str, profile: dict) -> dict` returning `{"ok": bool, "new_numbers": [...], "new_contacts": [...]}`.
  - CLI: `python verify_facts.py --tailored tailored.txt --profile profile.json`; exit 1 on any unverified fact.
- Consumed by: resume-tailoring skill (regenerate on failure).

**Rationale:** numeric facts (metrics, dates, years) and contact details are the highest-value, lowest-false-positive hallucination signals. Employer/title/degree invention is additionally guarded by the tailoring skill's reuse-only rules and human review.

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_verify_facts.py
import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_facts.py"

def _load():
    spec = importlib.util.spec_from_file_location("verify_facts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_extract_numbers():
    m = _load()
    nums = m.extract_numbers("Grew revenue 40% in 2021 across 3 teams")
    assert "40" in nums and "2021" in nums and "3" in nums

def test_verify_passes_when_subset():
    m = _load()
    profile = {"raw_text": "Led 5 engineers, grew usage 40% in 2021. jane@x.com"}
    out = m.verify("Grew usage 40% in 2021 leading 5 engineers", profile)
    assert out["ok"] is True

def test_verify_flags_invented_metric():
    m = _load()
    profile = {"raw_text": "Grew usage 40% in 2021"}
    out = m.verify("Grew usage 250% in 2021", profile)
    assert out["ok"] is False
    assert "250" in out["new_numbers"]

def test_verify_flags_invented_email():
    m = _load()
    profile = {"raw_text": "Contact jane@x.com", "contact": {"email": "jane@x.com"}}
    out = m.verify("Contact fake@evil.com", profile)
    assert out["ok"] is False
    assert "fake@evil.com" in out["new_contacts"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_verify_facts.py -v`
Expected: FAIL (module not found).

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Fail (exit 1) if a tailored resume introduces numeric facts or contacts
absent from the original profile. Anti-hallucination gate."""
import argparse, json, re, sys

_NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")

def _norm_num(tok: str) -> str:
    return tok.replace(",", "").rstrip(".").lstrip("0") or "0"

def extract_numbers(text: str) -> set:
    return {_norm_num(m.group()) for m in _NUM_RE.finditer(text)}

def _norm_phone(tok: str) -> str:
    return re.sub(r"\D", "", tok)

def extract_contacts(text: str) -> dict:
    return {"emails": {e.lower() for e in _EMAIL_RE.findall(text)},
            "phones": {_norm_phone(p) for p in _PHONE_RE.findall(text)}}

def verify(tailored_text: str, profile: dict) -> dict:
    original = profile.get("raw_text", "")
    orig_nums = extract_numbers(original)
    new_numbers = sorted(extract_numbers(tailored_text) - orig_nums)

    orig_c = extract_contacts(original)
    tail_c = extract_contacts(tailored_text)
    new_emails = tail_c["emails"] - orig_c["emails"]
    new_phones = tail_c["phones"] - orig_c["phones"]
    new_contacts = sorted(new_emails) + sorted(new_phones)

    return {"ok": not new_numbers and not new_contacts,
            "new_numbers": new_numbers, "new_contacts": new_contacts}

def main(argv=None):
    ap = argparse.ArgumentParser(description="Anti-hallucination fact verifier")
    ap.add_argument("--tailored", required=True, help="tailored resume text file")
    ap.add_argument("--profile", required=True, help="profile.json path")
    args = ap.parse_args(argv)
    with open(args.tailored, encoding="utf-8") as fh:
        tailored = fh.read()
    with open(args.profile, encoding="utf-8") as fh:
        profile = json.load(fh)
    result = verify(tailored, profile)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter && python -m pytest tests/test_verify_facts.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add job-hunter/scripts/verify_facts.py job-hunter/tests/test_verify_facts.py
git commit -m "feat: add anti-hallucination fact verifier"
```

---

## Task 5: Resume HTML template + end-to-end render check

**Files:**
- Create: `job-hunter/templates/resume.html.j2`
- Test: `job-hunter/tests/test_template_render.py`
- Create: `job-hunter/tests/fixtures/sample_resume_data.json`

**Interfaces:**
- Consumes: `render_pdf.build_html`, `render_pdf.render` (Task 3).
- Produces: a template whose data contract is:
  `{name, title, contact{email,phone,location,links[]}, summary, skills[], experience[{company,role,dates,location,bullets[]}], education[{school,degree,dates}], extras[{heading,items[]}]}`.

**Design note:** Use the frontend-design skill for typography/layout. Single-column, print-optimized A4, system font stack, tight vertical rhythm so content controls page count. Template must degrade gracefully when optional sections are empty (`{% if %}` guards).

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_template_render.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_template_render.py -v`
Expected: FAIL (template/fixture missing).

- [ ] **Step 3: Create the fixture and template**

```json
// job-hunter/tests/fixtures/sample_resume_data.json
{
  "name": "Jane Doe",
  "title": "Senior Software Engineer",
  "contact": {"email": "jane@example.com", "phone": "555-0100",
              "location": "Berlin, DE", "links": ["github.com/janedoe"]},
  "summary": "Backend engineer with 8 years building scalable Python services.",
  "skills": ["Python", "PostgreSQL", "Kubernetes", "AWS", "Django"],
  "experience": [
    {"company": "Acme Corp", "role": "Senior Engineer", "dates": "2020-2025",
     "location": "Berlin", "bullets": ["Led 5 engineers.", "Cut latency 40%."]},
    {"company": "Beta Inc", "role": "Engineer", "dates": "2017-2020",
     "location": "Munich", "bullets": ["Built billing service."]}
  ],
  "education": [{"school": "TU Munich", "degree": "BSc CS", "dates": "2013-2017"}],
  "extras": [{"heading": "Languages", "items": ["English", "German"]}]
}
```

```html
{# job-hunter/templates/resume.html.j2 #}
<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
  @page { size: A4; margin: 14mm 16mm; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1a1a1a;
         font-size: 10.5pt; line-height: 1.32; }
  h1 { font-size: 20pt; margin: 0 0 2pt; letter-spacing: .3pt; }
  .title { font-size: 11pt; color: #444; margin: 0 0 6pt; }
  .contact { font-size: 9pt; color: #555; margin-bottom: 10pt; }
  .contact span::after { content: " · "; color: #bbb; }
  .contact span:last-child::after { content: ""; }
  h2 { font-size: 10.5pt; text-transform: uppercase; letter-spacing: 1pt;
       border-bottom: 1px solid #ccc; padding-bottom: 2pt;
       margin: 12pt 0 6pt; color: #222; }
  .summary { margin: 0 0 4pt; }
  .skills { margin: 0; padding: 0; list-style: none; }
  .skills li { display: inline-block; margin: 0 6pt 3pt 0; font-size: 9.5pt; }
  .job { margin-bottom: 7pt; }
  .job-head { display: flex; justify-content: space-between; font-weight: 600; }
  .job-sub { color: #555; font-size: 9pt; margin-bottom: 2pt; }
  ul.bullets { margin: 2pt 0 0; padding-left: 14pt; }
  ul.bullets li { margin-bottom: 1.5pt; }
  .edu-item { display: flex; justify-content: space-between; }
</style></head><body>
  <header>
    <h1>{{ name }}</h1>
    {% if title %}<div class="title">{{ title }}</div>{% endif %}
    <div class="contact">
      {% if contact.email %}<span>{{ contact.email }}</span>{% endif %}
      {% if contact.phone %}<span>{{ contact.phone }}</span>{% endif %}
      {% if contact.location %}<span>{{ contact.location }}</span>{% endif %}
      {% for link in contact.links or [] %}<span>{{ link }}</span>{% endfor %}
    </div>
  </header>
  {% if summary %}<section><h2>Summary</h2>
    <p class="summary">{{ summary }}</p></section>{% endif %}
  {% if skills %}<section><h2>Skills</h2>
    <ul class="skills">{% for s in skills %}<li>{{ s }}</li>{% endfor %}</ul>
  </section>{% endif %}
  {% if experience %}<section><h2>Experience</h2>
    {% for job in experience %}<div class="job">
      <div class="job-head"><span>{{ job.role }} — {{ job.company }}</span>
        <span>{{ job.dates }}</span></div>
      {% if job.location %}<div class="job-sub">{{ job.location }}</div>{% endif %}
      {% if job.bullets %}<ul class="bullets">
        {% for b in job.bullets %}<li>{{ b }}</li>{% endfor %}</ul>{% endif %}
    </div>{% endfor %}
  </section>{% endif %}
  {% if education %}<section><h2>Education</h2>
    {% for e in education %}<div class="edu-item">
      <span>{{ e.degree }}, {{ e.school }}</span><span>{{ e.dates }}</span>
    </div>{% endfor %}
  </section>{% endif %}
  {% for extra in extras or [] %}<section><h2>{{ extra.heading }}</h2>
    <p>{{ extra.items | join(", ") }}</p></section>{% endfor %}
</body></html>
```

- [ ] **Step 4: Run tests (unit + integration render)**

Run: `cd job-hunter && python -m pytest tests/test_template_render.py -v`
Expected: PASS (2 tests).
Then, if chromium is available, verify a real render is single page:
Run: `cd job-hunter && python scripts/render_pdf.py templates/resume.html.j2 /tmp/out.pdf --data tests/fixtures/sample_resume_data.json --target-pages 1`
Expected: JSON with `"page_count": 1, "overflow": false` and exit 0. (Requires `pip install -r requirements.txt && playwright install chromium`.)

- [ ] **Step 5: Commit**

```bash
git add job-hunter/templates/resume.html.j2 job-hunter/tests/test_template_render.py job-hunter/tests/fixtures/sample_resume_data.json
git commit -m "feat: add professional resume template with print CSS"
```

---

## Task 6: Skills (resume-parsing, job-matching, resume-tailoring, pdf-rendering, application-filling)

**Files:**
- Create: `job-hunter/skills/resume-parsing/SKILL.md`
- Create: `job-hunter/skills/job-matching/SKILL.md`
- Create: `job-hunter/skills/resume-tailoring/SKILL.md`
- Create: `job-hunter/skills/pdf-rendering/SKILL.md`
- Create: `job-hunter/skills/application-filling/SKILL.md`
- Test: `job-hunter/tests/test_skills.py`

**Interfaces:**
- Consumes: the three scripts + template from Tasks 2–5 (skills reference their CLIs).
- Produces: the "how-to" invoked by the commands in Task 7.

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_skills.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_skills.py -v`
Expected: FAIL (files missing).

- [ ] **Step 3: Write the five SKILL.md files**

`job-hunter/skills/resume-parsing/SKILL.md`:
```markdown
---
name: resume-parsing
description: Use when parsing a candidate resume file into a structured profile before job search or tailoring.
---

# Resume Parsing

1. Run `python scripts/extract_resume.py <resume_path> -o profile.json`. This
   fills `raw_text` and `original_page_count`.
2. Read `raw_text` and enrich `profile.json` in place with these keys, using
   ONLY facts present in the text (never infer or invent):
   - `contact`: `{name, email, phone, location, links[]}`
   - `titles[]`: job titles held (most recent first)
   - `skills[]`: concrete skills/tools named
   - `employers[]`: `{company, role, dates, location, bullets[]}`
   - `education[]`: `{school, degree, dates}`
   - `metrics[]`: quantified achievements verbatim
   - `keywords[]`: domain terms useful for search
3. Preserve `raw_text` and `original_page_count` unchanged — later steps depend
   on them.
4. If a field is absent in the resume, use an empty value; do NOT guess.
```

`job-hunter/skills/job-matching/SKILL.md`:
```markdown
---
name: job-matching
description: Use when searching for and ranking jobs that match a parsed candidate profile across web boards, LinkedIn, or user-supplied URLs.
---

# Job Matching

Sources (use whichever the command specifies):
1. **Web boards** — WebSearch queries built from `profile.titles`, top
   `profile.skills`, and `profile.contact.location`; WebFetch each promising
   posting (Greenhouse, Lever, Workday, Indeed, public LinkedIn). Discovery only.
2. **LinkedIn logged-in** — via the Playwright MCP browser, only if the user
   opted in. Surface the ToS/account-risk note before using it.
3. **User URLs** — WebFetch the provided posting URLs directly.

For each posting capture: `company, role, location, url, description, requirements`.

Rank by fit: overlap of required skills/titles with the profile, seniority match,
location/remote compatibility. Present the **top K** (K = `--top-k`, default 10,
NEVER hardcoded) as a numbered table and ask the user to confirm which to proceed
with before any tailoring or applying. Write chosen postings to
`applications/<company>-<role>/job.md`.
```

`job-hunter/skills/resume-tailoring/SKILL.md`:
```markdown
---
name: resume-tailoring
description: Use when tailoring a parsed resume to a specific job description, producing verified length-matched resume data.
---

# Resume Tailoring

Goal: maximize relevance to the job WITHOUT inventing anything.

Rules:
- You may ONLY reorder, rephrase, re-emphasize, and select from content already
  in `profile.json`. Never add a company, title, date, degree, metric, or skill
  the candidate does not already have.
- Surface the job's language: where the profile already supports a required
  skill, use the job posting's phrasing for it.
- Keep it to the profile's `original_page_count`.

Steps:
1. Build `resume_data.json` matching the template contract (name, title, contact,
   summary, skills[], experience[{company,role,dates,location,bullets[]}],
   education[], extras[]) using only profile facts, prioritized for this job.
2. Flatten the tailored text (summary + bullets + skills) to `tailored.txt`.
3. Run `python scripts/verify_facts.py --tailored tailored.txt --profile profile.json`.
   - Exit 1 → it introduced a number/contact not in the original (a
     hallucination). Fix `resume_data.json` and repeat. Do NOT proceed until exit 0.
4. Hand `resume_data.json` to the pdf-rendering skill.

Write outputs under `applications/<company>-<role>/`.
```

`job-hunter/skills/pdf-rendering/SKILL.md`:
```markdown
---
name: pdf-rendering
description: Use when rendering tailored resume data into a polished PDF that matches the original resume length.
---

# PDF Rendering

1. Render: `python scripts/render_pdf.py templates/resume.html.j2 \
   applications/<company>-<role>/tailored_resume.pdf \
   --data applications/<company>-<role>/resume_data.json \
   --target-pages <original_page_count>`
2. Exit code 2 = the PDF overflowed the target page count. Tighten
   `resume_data.json` — shorten bullets, drop the least-relevant bullets (never
   whole sections), trim the summary — then re-render. Repeat until exit 0.
3. Exit 0 = success. The polished, length-matched PDF and its `.html` source are
   written next to the data file.

Never relax `--target-pages`; the length constraint is non-negotiable.
```

`job-hunter/skills/application-filling/SKILL.md`:
```markdown
---
name: application-filling
description: Use when filling and submitting a job application form via the browser, in assisted or autonomous mode.
---

# Application Filling

Use the Playwright MCP browser. Read the live DOM each time — do not assume a
fixed per-portal layout.

Steps:
1. Navigate to the posting's application URL.
2. Map `profile` fields to form fields (name, email, phone, location, work
   authorization if present in profile, links). Upload
   `applications/<company>-<role>/tailored_resume.pdf` to the resume input.
3. For screening questions, answer only from profile facts; draft cover-letter /
   free-text answers and save them to `answers.md`. If a required field cannot be
   answered from the profile, STOP and ask the user.
4. Mode:
   - **assisted (default):** fill everything, then STOP and ask the user to review
     and click Submit. Do not submit.
   - **autonomous (`--mode autonomous`):** submit, then retry on transient errors
     (network, stale element) up to 3 attempts. NEVER attempt to bypass CAPTCHA or
     2FA — pause and hand control to the user. Stop on ambiguous required fields.
5. Record every action, the final state, and any screenshots path in
   `applications/<company>-<role>/status.json` (`{status, mode, url, attempts,
   actions[], submitted_at}`).

Always show the autonomous-mode ToS/account-risk warning before submitting.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter && python -m pytest tests/test_skills.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add job-hunter/skills job-hunter/tests/test_skills.py
git commit -m "feat: add job-hunter skills (parse, match, tailor, render, fill)"
```

---

## Task 7: Slash commands (parse-resume, find-jobs, tailor-resume, apply, job-hunt)

**Files:**
- Create: `job-hunter/commands/parse-resume.md`
- Create: `job-hunter/commands/find-jobs.md`
- Create: `job-hunter/commands/tailor-resume.md`
- Create: `job-hunter/commands/apply.md`
- Create: `job-hunter/commands/job-hunt.md`
- Test: `job-hunter/tests/test_commands.py`

**Interfaces:**
- Consumes: the five skills (Task 6).
- Produces: the user-facing entry points.

- [ ] **Step 1: Write the failing test**

```python
# job-hunter/tests/test_commands.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd job-hunter && python -m pytest tests/test_commands.py -v`
Expected: FAIL (files missing).

- [ ] **Step 3: Write the five command files**

`job-hunter/commands/parse-resume.md`:
```markdown
---
description: Parse a resume file (PDF/DOCX/TXT) into a structured profile.json.
argument-hint: <path-to-resume>
---

Parse the resume at `$1` (or ask the user for the path if empty).

Use the resume-parsing skill: run the extractor, then enrich `profile.json` with
structured fields using only facts present in the resume. Report the detected
page count and a summary of extracted titles and skills.
```

`job-hunter/commands/find-jobs.md`:
```markdown
---
description: Find and rank jobs matching profile.json across web/LinkedIn/URLs.
argument-hint: [--top-k N] [--sources web,linkedin,urls] [urls...]
---

Ensure `profile.json` exists (run parse-resume first if not).

Use the job-matching skill. K comes from `--top-k` (default 10). Include LinkedIn
only if `--sources` lists it, and show the ToS/account-risk note first. Present
the ranked top-K and ask the user to confirm which postings to keep. Save chosen
postings to `applications/<company>-<role>/job.md`.
```

`job-hunter/commands/tailor-resume.md`:
```markdown
---
description: Tailor the resume to one job and render a verified length-matched PDF.
argument-hint: <applications/company-role dir>
---

For the job at directory `$1`:
Use the resume-tailoring skill to build a verified `resume_data.json` (must pass
verify_facts with exit 0), then the pdf-rendering skill to produce
`tailored_resume.pdf` matching `profile.json`'s `original_page_count`. Confirm the
final page count equals the original.
```

`job-hunter/commands/apply.md`:
```markdown
---
description: Fill and (assisted) or submit (autonomous) a job application.
argument-hint: <applications/company-role dir> [--mode assisted|autonomous]
---

For the job at directory `$1` (default `--mode assisted`):
Ensure `tailored_resume.pdf` exists (run tailor-resume first if not).
Use the application-filling skill with the Playwright MCP browser. In assisted
mode, fill everything and pause for the user to submit. In autonomous mode, show
the ToS/account-risk warning, then fill, submit, and retry transient failures up
to 3 times. Record outcome to `status.json`.
```

`job-hunter/commands/job-hunt.md`:
```markdown
---
description: End-to-end job hunt — parse, find, tailor, and apply.
argument-hint: <resume-path> [--top-k N] [--mode assisted|autonomous] [--sources ...] [urls...]
---

Run the full pipeline for the resume at `$1`:
1. parse-resume → `profile.json` (resume-parsing skill).
2. find-jobs with `--top-k` (default 10, configurable) → ranked list; ask the user
   to confirm which postings to proceed with (job-matching skill).
3. For each confirmed posting: tailor-resume (resume-tailoring + pdf-rendering
   skills), producing a verified length-matched `tailored_resume.pdf`.
4. apply with `--mode` (default assisted). In autonomous mode, show the
   ToS/account-risk warning first.

Report a final summary table of every application and its `status.json` state.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd job-hunter && python -m pytest tests/test_commands.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add job-hunter/commands job-hunter/tests/test_commands.py
git commit -m "feat: add job-hunter slash commands"
```

---

## Task 8: README, full test run, and end-to-end smoke

**Files:**
- Create: `job-hunter/README.md`
- Test: full suite + manual end-to-end.

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Write the README**

```markdown
# job-hunter

A Claude Code plugin that parses a resume, finds matching jobs, tailors a
length-matched hallucination-free PDF resume per job, and auto-fills applications
(assisted or autonomous).

## Install
1. Add this plugin directory to Claude Code.
2. `pip install -r requirements.txt`
3. `playwright install chromium`
4. Approve the `playwright` MCP server on first use.

## Commands
- `/job-hunt <resume> [--top-k N] [--mode assisted|autonomous] [--sources web,linkedin,urls] [urls...]`
- `/parse-resume <resume>`
- `/find-jobs [--top-k N] [--sources ...] [urls...]`
- `/tailor-resume <applications/company-role>`
- `/apply <applications/company-role> [--mode assisted|autonomous]`

## Guarantees
- **Same length** as the original resume (enforced by `render_pdf.py`).
- **No invented facts** (enforced by `verify_facts.py`).

## Modes
- **assisted** (default): fills the form, you review and submit.
- **autonomous**: fills and submits with bounded retries; never bypasses
  CAPTCHA/2FA. Carries ToS/account risk — use at your own discretion.

## Outputs
`applications/<company>-<role>/`: `job.md`, `resume_data.json`,
`tailored_resume.html`, `tailored_resume.pdf`, `answers.md`, `status.json`.
```

- [ ] **Step 2: Run the full unit suite**

Run: `cd job-hunter && python -m pytest -v`
Expected: all non-integration tests PASS; render integration test PASSES (if chromium installed) or SKIPS.

- [ ] **Step 3: End-to-end smoke (assisted, manual)**

Run, with a real sample resume:
```bash
cd job-hunter
pip install -r requirements.txt && playwright install chromium
python scripts/extract_resume.py tests/fixtures/sample_resume.txt -o /tmp/profile.json
python scripts/render_pdf.py templates/resume.html.j2 /tmp/tr.pdf \
  --data tests/fixtures/sample_resume_data.json --target-pages 1
```
Expected: `profile.json` written; `/tmp/tr.pdf` is exactly 1 page (`overflow:false`).
Then in Claude Code run `/job-hunt tests/fixtures/sample_resume.txt --top-k 3` and
confirm it parses, presents ≤3 ranked jobs, and stops for confirmation. (Create
`tests/fixtures/sample_resume.txt` with a few lines of realistic resume content.)

- [ ] **Step 4: Commit**

```bash
git add job-hunter/README.md job-hunter/tests/fixtures/sample_resume.txt
git commit -m "docs: add README and end-to-end smoke fixture"
```

---

## Self-Review Notes

- **Spec coverage:** parse (T2/T6), extract profile fields (T6 resume-parsing),
  search web+LinkedIn+URLs (T6 job-matching/T7), per-job tailoring (T6/T7),
  PDF always (T3/T5), same length (T3 gate + T5/T6 loop), no hallucination
  (T4 + T6 rules), apply assisted+autonomous+retry (T6/T7), per-job folders
  (skills/commands), top-K configurable (Global Constraints + T6/T7), plugin best
  practices (T1 manifest/.mcp.json/skills/commands). All covered.
- **Deviation from spec:** `render_pdf.py` also does the Jinja template→HTML step
  (spec listed it as HTML→PDF only). Kept to three scripts; deterministic and
  template-driven rather than hand-written HTML. Intentional refinement.
- **Type consistency:** `extract`/`estimate_pages_from_text` (T2), `is_overflow`/
  `build_html`/`count_pages`/`render` (T3), `extract_numbers`/`extract_contacts`/
  `verify` (T4) referenced consistently by skills in T6.
- **Anti-hallucination scope:** verify_facts is deterministic on numbers+contacts
  (highest value, lowest false positive); employer/title/degree invention guarded
  by tailoring skill reuse-only rules + human review. Documented in T4.
