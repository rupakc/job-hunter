---
description: Tailor the resume to one job and render a verified length-matched PDF.
argument-hint: <applications/company-role dir>
---

For the job at directory `$1`:
Use the resume-tailoring skill to build a verified `resume_data.json` (must pass
verify_facts with exit 0), then the pdf-rendering skill to produce
`tailored_resume.pdf` matching `profile.json`'s `original_page_count`. Confirm the
final page count equals the original.
