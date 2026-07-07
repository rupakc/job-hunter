---
name: style-capture
description: Use when reproducing the original resume's visual design so every tailored resume looks identical in formatting, color scheme, and layout.
---

# Style Capture

Goal: produce a per-resume Jinja template whose formatting, color scheme, and
layout match the ORIGINAL resume, so every tailored version looks identical to
it. Run this once per candidate, before tailoring; all that resume's tailored
versions reuse the captured template.

1. Inspect the original resume's design:
   - **PDF:** open the original file with the Read tool (it renders the pages
     visually) so you can SEE the layout, colors, and fonts. Also use
     `profile.json` `raw_text` for exact wording.
   - **DOCX/TXT:** read the text; for DOCX use any styling cues available.
   Record: column layout (single vs. two-column), color scheme as hex values
   (headings, accents, rules), font families and sizes, name/header treatment,
   section order and heading style, spacing, use of horizontal rules/lines, and
   bullet style.
2. Write `<appdir>/resume_template.html.j2` reproducing that design with print
   CSS (`@page { size: A4 }` and margins matching the original's). It MUST
   consume the standard data contract so tailored data fills it:
   `name, title, contact{email,phone,location,links[]}, summary, skills[],
   experience[{company,role,dates,location,bullets[]}], education[{school,degree,
   dates}], extras[{heading,items[]}]`.
   Arrange and style those fields to match the original — same colors, fonts,
   column layout, section order, and headings. Guard optional sections with
   `{% if %}` so empty data never breaks rendering. Remember `extra['items']`
   (subscript), since `.items` collides with the dict method in Jinja.
3. Reproduce ONLY what the original shows — never invent visual content. If a
   detail is unclear, use the closest faithful approximation.
4. Fallback: if the original's design genuinely cannot be determined, use the
   shared `templates/resume.html.j2` instead.

The pdf-rendering skill renders THIS captured template
(`<appdir>/resume_template.html.j2`), not the shared default.
