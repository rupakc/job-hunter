# job-hunter

A [Claude Code](https://claude.com/claude-code) plugin that runs your entire job
application pipeline: it parses your resume, finds matching jobs, tailors a
**distinct resume for each job**, renders it as a polished PDF that **looks like
your original** and **matches its length**, invents **nothing**, and then
**auto-fills the application** — either pausing for you to submit (assisted) or
submitting on its own (autonomous).

---

## What it does

Give it your resume (PDF, DOCX, or TXT). It will:

1. **Parse** the resume into a structured profile (titles, skills, employers,
   dates, metrics, education, contact).
2. **Search** for matching jobs across web boards, your logged-in LinkedIn
   session, and/or job URLs you supply, then rank and show you the top **K**
   (configurable, default 10) for confirmation.
3. **Capture the original's design** — fonts, colors, layout, section order —
   into a per-resume template so every tailored version looks identical to your
   original.
4. **Tailor** the resume to each chosen job, reordering and rephrasing your real
   content to surface the job's requirements — never adding anything you didn't
   already have.
5. **Verify + render** a length-matched PDF. A fact-checker hard-fails on any
   invented number, date, or contact; a page-count gate re-renders until the
   length matches the original.
6. **Apply** — fills the portal form and uploads the tailored PDF, then either
   pauses for your review (assisted) or submits and retries transient failures
   (autonomous).

### Guarantees (enforced mechanically, not by vibes)

| Guarantee | How it's enforced |
|-----------|-------------------|
| **Looks like your original** | `style-capture` reproduces the original's formatting/colors/layout; `render_pdf.py` uses `prefer_css_page_size` so the template's CSS `@page` fully controls page geometry |
| **Same length as the original** | `render_pdf.py` counts rendered pages and exits non-zero on overflow → the tailoring loop trims and re-renders until it matches |
| **No invented facts** | `verify_facts.py` extracts every number, date, and contact from the tailored resume and hard-fails if any is absent from the original |

---

## Architecture

```
                                 ┌─────────────────────────────┐
   resume.(pdf|docx|txt) ───────▶│  /job-hunt  (orchestrator)  │
                                 └──────────────┬──────────────┘
                                                │  drives the pipeline
        ┌───────────────────────────────────────┼───────────────────────────────────────┐
        ▼                    ▼                    ▼                    ▼                    ▼
 ┌────────────┐      ┌─────────────┐      ┌─────────────┐     ┌──────────────┐     ┌──────────────┐
 │/parse-     │      │/find-jobs   │      │style-capture│     │/tailor-      │     │/apply        │
 │ resume     │      │             │      │  (skill)    │     │ resume       │     │              │
 └─────┬──────┘      └──────┬──────┘      └──────┬──────┘     └──────┬───────┘     └──────┬───────┘
       │ skill:            │ skill:              │                   │ skills:            │ skill:
       │ resume-parsing    │ job-matching        │                   │ resume-tailoring   │ application-
       ▼                   ▼                     ▼                   │ + pdf-rendering    │ filling
 ┌────────────┐     ┌──────────────┐      ┌───────────────┐         ▼                    ▼
 │extract_    │     │ WebSearch /  │      │ Read original │  ┌────────────────┐   ┌──────────────┐
 │resume.py   │     │ WebFetch  +  │      │  (visual) →   │  │ verify_facts.py│   │ Playwright   │
 │            │     │ Playwright   │      │ resume_       │  │  (hallucination│   │ MCP browser  │
 │ PDF/DOCX/  │     │ (LinkedIn) + │      │ template.j2   │  │   gate, exit 1)│   │ fills form + │
 │ TXT → text │     │ user URLs    │      │ (matches look)│  └───────┬────────┘   │ uploads PDF  │
 └─────┬──────┘     └──────┬───────┘      └───────┬───────┘          │            └──────┬───────┘
       ▼                   ▼                      │                  ▼                   │
  profile.json      ranked top-K  ───────────────┘          ┌────────────────┐          │
  (structured)      [you confirm]                           │ render_pdf.py  │          ▼
                                                             │ Jinja+Chromium │   assisted → you submit
                                                             │ → PDF, page-   │   autonomous → submit
                                                             │ count gate     │              + retry
                                                             │ (exit 2 = trim)│
                                                             └───────┬────────┘
                                                                     ▼
                                        applications/<company>-<role>/tailored_resume.pdf
```

**Layers**

- **Commands** (`commands/*.md`) — the slash-command entry points you invoke.
- **Skills** (`skills/*/SKILL.md`) — the "how-to" each step follows.
- **Scripts** (`scripts/*.py`) — deterministic mechanical work (extraction,
  rendering + length gate, fact verification).
- **Playwright MCP** — one Chromium powers both browser automation (LinkedIn,
  form filling) and HTML→PDF rendering.

---

## Prerequisites

- **Claude Code** (CLI, desktop, or IDE extension).
- **Python 3.9+** with `pip`.
- **Node.js / `npx`** — for the Playwright MCP server (auto-run on first use).

---

## Installation

### 1. Install the plugin from the marketplace (recommended)

Install directly from this GitHub repo — no cloning required:

```bash
# Add the marketplace, then install the plugin
claude plugin marketplace add rupakc/job-hunter
claude plugin install job-hunter@job-hunter
```

Or, from inside a Claude Code session:

```
/plugin marketplace add rupakc/job-hunter
/plugin install job-hunter@job-hunter
```

This installs at **user scope** by default (available across all your projects).
Use `--scope project` to install it only for the current project. Verify with:

```bash
claude plugin list          # job-hunter@job-hunter → Status: ✔ enabled
```

> **Restart Claude Code / start a new session** after installing — plugins load
> at session start, so the `/job-hunt` commands appear in the next session.

### 2. Install the runtime dependencies

The plugin's scripts need Python packages and a Chromium browser (used for both
PDF rendering and browser automation):

```bash
pip install pdfplumber python-docx jinja2 pyyaml
playwright install chromium
```

On first use, **approve the `playwright` MCP server** when Claude Code prompts.

### Alternative: install from a local clone

```bash
git clone https://github.com/rupakc/job-hunter.git
claude plugin marketplace add ./job-hunter          # local path is also a valid marketplace
claude plugin install job-hunter@job-hunter
pip install -r job-hunter/job-hunter/requirements.txt
playwright install chromium
```

Verify the scripts pass their tests:

```bash
cd job-hunter/job-hunter && python -m pytest -q      # expect: all tests passing
```

---

## Usage

### One-shot: the full pipeline

```
/job-hunt path/to/resume.pdf --top-k 10 --mode assisted
```

Runs parse → style-capture → find-jobs → (you confirm the list) → tailor → verify
→ render → apply, for each confirmed job.

**Flags**

| Flag | Default | Meaning |
|------|---------|---------|
| `--top-k N` | `10` | How many ranked matches to present for confirmation |
| `--mode assisted\|autonomous` | `assisted` | Fill-and-pause vs. fill-and-submit |
| `--sources web,linkedin,urls` | `web` | Which job sources to search |
| `[urls...]` | — | Specific job posting URLs to tailor/apply to directly |

### Step-by-step (run or rerun any stage)

```
/parse-resume path/to/resume.pdf
/find-jobs --top-k 15 --sources web,linkedin
/find-jobs https://boards.greenhouse.io/acme/jobs/123   # or apply to a specific URL
/tailor-resume applications/acme-senior-engineer
/apply applications/acme-senior-engineer --mode assisted
```

### Examples

```
# Broad hunt across web boards, review 10, fill forms but you click submit
/job-hunt ~/Documents/resume.pdf

# Include your logged-in LinkedIn, look at 20, hand-pick, then autonomous submit
/job-hunt ~/resume.docx --top-k 20 --sources web,linkedin --mode autonomous

# Tailor + apply to three specific postings you already found
/job-hunt ~/resume.txt https://job1 https://job2 https://job3
```

---

## Modes

- **assisted** (default) — opens the portal in a browser you're logged into,
  fills every field and uploads the tailored PDF, then **stops for you to review
  and click Submit**. Handles login / CAPTCHA / 2FA naturally.
- **autonomous** (opt-in) — fills and submits, retrying transient failures
  (network, stale element) with a bounded retry count. **Never** bypasses
  CAPTCHA/2FA (pauses and hands to you). Shows a ToS/account-risk warning first.

> ⚠️ **LinkedIn & portal automation carries ToS and account-ban risk.** Assisted
> mode is the safe default. Use autonomous mode and logged-in LinkedIn scraping
> at your own discretion.

---

## Output layout

Each application gets its own folder:

```
applications/<company>-<role>/
├── job.md                    # the job posting content
├── resume_template.html.j2   # design captured from your original resume
├── resume_data.json          # tailored, fact-verified content
├── tailored_resume.html      # rendered source
├── tailored_resume.pdf       # the polished, length-matched resume you submit
├── answers.md                # screening / cover-letter answers
└── status.json               # application state + action log
```

---

## Repository layout

```
job-hunter/
├── .claude-plugin/plugin.json     # plugin manifest
├── .mcp.json                      # Playwright MCP server declaration
├── commands/                      # /job-hunt, /parse-resume, /find-jobs, /tailor-resume, /apply
├── skills/                        # resume-parsing, style-capture, job-matching,
│                                  #   resume-tailoring, pdf-rendering, application-filling
├── scripts/                       # extract_resume.py, render_pdf.py, verify_facts.py
├── templates/resume.html.j2       # fallback template (used only if design can't be captured)
├── tests/                         # pytest suite + fixtures
├── requirements.txt
└── README.md
docs/superpowers/                  # design spec + implementation plan
```

---

## Known limitations

- **DOCX/TXT page count** is a line-count heuristic; **PDF** originals are exact.
- The numeric anti-hallucination check is **set-based** — e.g. "led 40 engineers"
  passes if `40` appears anywhere in your original. It catches invented values,
  not every reassignment of existing ones.
- Pixel-perfect visual fidelity isn't guaranteed for complex multi-column PDF
  originals; style-capture reproduces the design faithfully but approximately.
- The length gate only flags **overflow** (too long); it doesn't force a shorter
  resume up to the original's page count.

---

## Development

```bash
cd job-hunter
python -m pytest -v          # run the full test suite
```

Design spec and implementation plan live under `docs/superpowers/`.

---

## License

No license file yet — add one before distributing.
