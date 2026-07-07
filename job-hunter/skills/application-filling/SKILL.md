---
name: application-filling
description: Use when filling and submitting a job application form via the browser, in assisted or autonomous mode.
---

# Application Filling

Use the Playwright MCP browser. Read the live DOM each time — do not assume a
fixed per-portal layout.

Steps:
1. Navigate to the posting's application URL.
2. Map `profile` fields to form fields (name, email, phone, location, work
   authorization if present in profile, links). Upload
   `applications/<company>-<role>/tailored_resume.pdf` to the resume input.
3. For screening questions, answer only from profile facts; draft cover-letter /
   free-text answers and save them to `answers.md`. If a required field cannot be
   answered from the profile, STOP and ask the user.
4. Mode:
   - **assisted (default):** fill everything, then STOP and ask the user to review
     and click Submit. Do not submit.
   - **autonomous (`--mode autonomous`):** submit, then retry on transient errors
     (network, stale element) up to 3 attempts. NEVER attempt to bypass CAPTCHA or
     2FA — pause and hand control to the user. Stop on ambiguous required fields.
5. Record every action, the final state, and any screenshots path in
   `applications/<company>-<role>/status.json` (`{status, mode, url, attempts,
   actions[], submitted_at}`).

Always show the autonomous-mode ToS/account-risk warning before submitting.
