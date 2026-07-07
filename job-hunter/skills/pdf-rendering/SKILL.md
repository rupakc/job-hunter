---
name: pdf-rendering
description: Use when rendering tailored resume data into a polished PDF that matches the original resume length.
---

# PDF Rendering

Render with the per-resume template captured by the style-capture skill
(`applications/<company>-<role>/resume_template.html.j2`), so the output matches
the original resume's formatting, colors, and layout. Fall back to the shared
`templates/resume.html.j2` only if no captured template exists.

1. Render: `python scripts/render_pdf.py \
   applications/<company>-<role>/resume_template.html.j2 \
   applications/<company>-<role>/tailored_resume.pdf \
   --data applications/<company>-<role>/resume_data.json \
   --target-pages <original_page_count>`
2. Exit code 2 = the PDF overflowed the target page count. Tighten
   `resume_data.json` — shorten bullets, drop the least-relevant bullets (never
   whole sections), trim the summary — then re-render. Repeat until exit 0.
3. Exit 0 = success. The polished, length-matched PDF and its `.html` source are
   written next to the data file.

Never relax `--target-pages`; the length constraint is non-negotiable.
