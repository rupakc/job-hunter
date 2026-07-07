---
description: Fill and (assisted) or submit (autonomous) a job application.
argument-hint: <applications/company-role dir> [--mode assisted|autonomous]
---

For the job at directory `$1` (default `--mode assisted`):
Ensure `tailored_resume.pdf` exists (run tailor-resume first if not).
Use the application-filling skill with the Playwright MCP browser. In assisted
mode, fill everything and pause for the user to submit. In autonomous mode, show
the ToS/account-risk warning, then fill, submit, and retry transient failures up
to 3 times. Record outcome to `status.json`.
