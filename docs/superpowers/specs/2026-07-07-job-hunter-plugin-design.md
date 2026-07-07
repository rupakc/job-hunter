# Job-Hunter Plugin — Design

**Date:** 2026-07-07
**Status:** Approved (design)

## Purpose

A Claude Code plugin, `job-hunter`, that automates the end-to-end job-application
workflow: parse a candidate resume, extract a searchable profile, find matching
jobs across the web / LinkedIn / user-supplied URLs, tailor a distinct resume for
each job, render it as a polished PDF that matches the original's length and
invents nothing, then auto-fill the application form (assisted or autonomous).

## Non-negotiable constraints

1. **Same length** — the tailored PDF must occupy the same number of pages as the
   original resume. Enforced mechanically (render → count pages → trim → re-render).
2. **No hallucination** — the tailored resume may only reorder, rephrase, and
   re-emphasize facts present in the original. Every company, title, date, degree,
   and metric in the output must exist in the parsed profile. Enforced by a fact
   verifier that hard-fails on any new fact.
3. **Matches the original's look** — the tailored resume must reproduce the
   original resume's formatting, color scheme, and layout. A `style-capture` step
   inspects the original (visually, via the Read tool for PDFs) and generates a
   per-resume `resume_template.html.j2` mirroring its design; tailored content
   fills that template. `render_pdf.py` uses `prefer_css_page_size=True` so the
   template's CSS `@page` size and margins fully control page geometry. The
   shared `templates/resume.html.j2` is a fallback when the original's design
   cannot be determined.

## Tech stack

- **Language:** Python 3 for all helper scripts.
- **Browser + PDF engine:** Playwright (Chromium). Declared as a Playwright MCP
  server dependency for interactive browser automation (LinkedIn, portal filling);
  the same Chromium renders resume HTML → PDF via a standalone Python script.
- **Parsing:** `pdfplumber` (PDF), `python-docx` (DOCX), plain read (TXT).
- **Templating:** Jinja2 for the resume HTML template.

## Plugin structure

```
job-hunter/
├── .claude-plugin/plugin.json         # manifest (name, version, MCP deps)
├── commands/
│   ├── job-hunt.md                    # orchestrator (end-to-end)
│   ├── parse-resume.md
│   ├── find-jobs.md
│   ├── tailor-resume.md
│   └── apply.md
├── skills/
│   ├── resume-parsing/SKILL.md
│   ├── job-matching/SKILL.md
│   ├── resume-tailoring/SKILL.md      # includes anti-hallucination rules
│   ├── pdf-rendering/SKILL.md
│   └── application-filling/SKILL.md   # assisted + autonomous modes
├── scripts/
│   ├── extract_resume.py              # PDF/DOCX/TXT -> profile.json + page count
│   ├── render_pdf.py                  # HTML/CSS -> Chromium -> PDF, page-count check
│   └── verify_facts.py                # tailored-vs-original fact diff (hard fail)
├── templates/resume.html.j2           # professional resume template + print CSS
├── requirements.txt
└── README.md
```

## Data flow

```
resume file ──▶ extract_resume.py ──▶ profile.json
                 (titles, skills, employers, dates, metrics, education,
                  location, contact, original_page_count)
profile.json ──▶ find-jobs (WebSearch/WebFetch + LinkedIn + user URLs)
             ──▶ ranked matches ──▶ [USER CONFIRMS top-K] 
per job ──▶ tailor-resume ──▶ tailored_resume.html
                          ──▶ verify_facts.py (BLOCKS on new facts)
                          ──▶ render_pdf.py ──▶ tailored_resume.pdf (length-checked)
                          ──▶ apply ──▶ Playwright fills form + uploads PDF
                                     ──▶ assisted: pause for user
                                     ──▶ autonomous: submit + bounded retry
```

Output per job: `applications/<company>-<role>/` containing:
- `job.md` — the job posting content
- `tailored_resume.pdf` — the tailored, length-matched resume
- `tailored_resume.html` — source used to render the PDF
- `answers.md` — screening-question / cover-letter answers
- `status.json` — application state and action log

## Components

### extract_resume.py
- Input: path to `.pdf` / `.docx` / `.txt`.
- Detects type by extension; extracts full text; records original page count
  (for PDF, actual page count; for DOCX/TXT, rendered page count via a probe
  render of the source text).
- Output: `profile.json` with raw text plus a structured breakdown that Claude
  fills semantically (titles, skills, employers, dates, metrics, education,
  contact, location). Script provides text + page count; Claude does semantic
  structuring in the parse-resume command.

### render_pdf.py
- Input: HTML file, output PDF path, target page count.
- Renders with Chromium `page.pdf()` using the template's print CSS.
- Counts resulting pages; if it exceeds the target, returns an overflow signal so
  the tailoring step can trim and re-render. Deterministic, not heuristic.

### verify_facts.py
- Input: tailored resume text (or HTML) + `profile.json`.
- Extracts candidate facts (companies, titles, dates, degrees, numeric metrics)
  from the tailored output and confirms each appears in the profile.
- Exit non-zero + JSON report listing any unverified facts → tailoring regenerates.

### Commands
- `/job-hunt` — orchestrator: runs parse → find → confirm → (per job) tailor →
  verify → render → apply. Accepts resume path, optional job URLs, `--top-k N`
  (default 10, **configurable, never hardcoded**), and `--mode assisted|autonomous`.
- `/parse-resume`, `/find-jobs`, `/tailor-resume`, `/apply` — each step runnable
  and rerunnable standalone.

### Skills
- `resume-parsing` — how to turn extracted text into a faithful structured profile.
- `job-matching` — how to search (web boards, LinkedIn logged-in, user URLs), rank
  by fit, and present the top-K for confirmation.
- `resume-tailoring` — how to reorder/rephrase/re-emphasize only; the
  anti-hallucination rules; how to respond to a verify_facts failure.
- `pdf-rendering` — how to render and enforce the length constraint loop.
- `application-filling` — mapping profile fields to form fields; assisted vs.
  autonomous behavior and guardrails.

## Ranked matches (configurable K)

`find-jobs` searches all three sources, ranks candidates by fit against the
profile, and presents the top **K** (default 10) for the user to confirm before
any tailoring or applying. K is a command flag / config value, never hardcoded.

## Apply modes

- **Assisted (default):** opens the portal in a browser the user is logged into,
  fills all fields + uploads the PDF, then stops and asks the user to review and
  submit. Handles login / CAPTCHA / 2FA naturally.
- **Autonomous (opt-in `--mode autonomous`):** fills and submits, retrying on
  transient failures (network, stale element) up to a bounded retry count.
  Guardrails: never attempts to bypass CAPTCHA/2FA (pauses and hands to user);
  stops on ambiguous required fields rather than guessing; logs every action to
  `status.json`. Shows an explicit ToS/account-risk warning on invocation.

## Job sources

1. Web search across boards (Google, Indeed, Greenhouse, Lever, Workday, public
   LinkedIn posts) via WebSearch/WebFetch — discovery only.
2. LinkedIn logged-in session via Playwright (higher relevance; ToS/account risk
   surfaced to the user).
3. User-provided job URLs — skip search, tailor + apply directly.

## Testing

- Unit tests for the three scripts:
  - `extract_resume.py` on sample PDF/DOCX/TXT fixtures.
  - `render_pdf.py` page-count enforcement.
  - `verify_facts.py` catching an injected fake company/metric.
- End-to-end validation with a sample resume fixture in assisted mode against a
  couple of real public postings.

## Risks & mitigations

- **LinkedIn / portal ToS & bot detection:** default to assisted mode; surface
  risk warnings; never bypass CAPTCHA/2FA.
- **Portal variety (Greenhouse/Lever/Workday/etc.):** field-mapping in the
  application-filling skill is driven by reading the live DOM each time, not a
  fixed per-portal script, so it adapts.
- **Playwright/Chromium install:** documented in README; `requirements.txt` +
  `playwright install chromium`.
