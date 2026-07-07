---
description: Tailor the resume to one job and render a verified length-matched PDF.
argument-hint: <applications/company-role dir>
---

For the job at directory `$1`:
First use the style-capture skill to produce `resume_template.html.j2` mirroring
the original resume's formatting, colors, and layout (skip if it already exists
for this candidate). Then use the resume-tailoring skill to build a verified
`resume_data.json` (must pass verify_facts with exit 0), and the pdf-rendering
skill to render that captured template into `tailored_resume.pdf` matching
`profile.json`'s `original_page_count`. Confirm the final PDF matches the
original's look and its page count equals the original.
