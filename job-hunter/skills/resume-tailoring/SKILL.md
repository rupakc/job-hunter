---
name: resume-tailoring
description: Use when tailoring a parsed resume to a specific job description, producing verified length-matched resume data.
---

# Resume Tailoring

Goal: maximize relevance to the job WITHOUT inventing anything.

Rules:
- You may ONLY reorder, rephrase, re-emphasize, and select from content already
  in `profile.json`. Never add a company, title, date, degree, metric, or skill
  the candidate does not already have.
- Surface the job's language: where the profile already supports a required
  skill, use the job posting's phrasing for it.
- Keep it to the profile's `original_page_count`.

Steps:
0. Ensure a captured template exists at `<appdir>/resume_template.html.j2`. If it
   does not, run the style-capture skill first so the tailored resume will match
   the original's formatting, colors, and layout.
1. Build `resume_data.json` matching the template contract (name, title, contact,
   summary, skills[], experience[{company,role,dates,location,bullets[]}],
   education[], extras[]) using only profile facts, prioritized for this job.
2. Flatten ALL text from `resume_data.json` to `tailored.txt`: the summary;
   every experience entry INCLUDING its dates and location, plus its bullets;
   every education entry INCLUDING its dates; all skills; all extras items;
   and the contact email and phone. Dates and contact details must be
   included so `verify_facts.py` can catch any invented ones.
3. Run `python scripts/verify_facts.py --tailored tailored.txt --profile profile.json`.
   - Exit 1 → it introduced a number/contact not in the original (a
     hallucination). Fix `resume_data.json` and repeat. Do NOT proceed until exit 0.
4. Hand `resume_data.json` to the pdf-rendering skill.

Write outputs under `applications/<company>-<role>/`.
