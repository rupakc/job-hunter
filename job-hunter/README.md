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
- **Looks like your original** — the style-capture skill reproduces the original
  resume's formatting, color scheme, and layout into a per-resume template that
  each tailored version fills, so the output matches the original's look.
- **Same length** as the original resume (enforced by `render_pdf.py`).
- **No invented facts** (enforced by `verify_facts.py`).

## Modes
- **assisted** (default): fills the form, you review and submit.
- **autonomous**: fills and submits with bounded retries; never bypasses
  CAPTCHA/2FA. Carries ToS/account risk — use at your own discretion.

## Outputs
`applications/<company>-<role>/`: `job.md`, `resume_template.html.j2` (design
captured from the original), `resume_data.json`, `tailored_resume.html`,
`tailored_resume.pdf`, `answers.md`, `status.json`.
