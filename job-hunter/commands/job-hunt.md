---
description: End-to-end job hunt — parse, find, tailor, and apply.
argument-hint: <resume-path> [--top-k N] [--mode assisted|autonomous] [--sources ...] [urls...]
---

Run the full pipeline for the resume at `$1`:
1. parse-resume → `profile.json` (resume-parsing skill).
2. Capture the original's design into `resume_template.html.j2` (style-capture
   skill) so every tailored resume matches its formatting, colors, and layout.
3. find-jobs with `--top-k` (default 10, configurable) → ranked list; ask the user
   to confirm which postings to proceed with (job-matching skill).
4. For each confirmed posting: tailor-resume (resume-tailoring + pdf-rendering
   skills), producing a verified length-matched `tailored_resume.pdf` that looks
   like the original.
5. apply with `--mode` (default assisted). In autonomous mode, show the
   ToS/account-risk warning first.

Report a final summary table of every application and its `status.json` state.
