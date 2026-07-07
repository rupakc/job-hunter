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
