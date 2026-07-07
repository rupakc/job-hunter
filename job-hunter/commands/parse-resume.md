---
description: Parse a resume file (PDF/DOCX/TXT) into a structured profile.json.
argument-hint: <path-to-resume>
---

Parse the resume at `$1` (or ask the user for the path if empty).

Use the resume-parsing skill: run the extractor, then enrich `profile.json` with
structured fields using only facts present in the resume. Report the detected
page count and a summary of extracted titles and skills.
