---
description: Find and rank jobs matching profile.json across web/LinkedIn/URLs.
argument-hint: [--top-k N] [--sources web,linkedin,urls] [urls...]
---

Ensure `profile.json` exists (run parse-resume first if not).

Use the job-matching skill. K comes from `--top-k` (default 10). Include LinkedIn
only if `--sources` lists it, and show the ToS/account-risk note first. Present
the ranked top-K and ask the user to confirm which postings to keep. Save chosen
postings to `applications/<company>-<role>/job.md`.
