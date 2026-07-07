---
name: job-matching
description: Use when searching for and ranking jobs that match a parsed candidate profile across web boards, LinkedIn, or user-supplied URLs.
---

# Job Matching

Sources (use whichever the command specifies):
1. **Web boards** — WebSearch queries built from `profile.titles`, top
   `profile.skills`, and `profile.contact.location`; WebFetch each promising
   posting (Greenhouse, Lever, Workday, Indeed, public LinkedIn). Discovery only.
2. **LinkedIn logged-in** — via the Playwright MCP browser, only if the user
   opted in. Surface the ToS/account-risk note before using it.
3. **User URLs** — WebFetch the provided posting URLs directly.

For each posting capture: `company, role, location, url, description, requirements`.

Rank by fit: overlap of required skills/titles with the profile, seniority match,
location/remote compatibility. Present the **top K** (K = `--top-k`, default 10,
NEVER hardcoded) as a numbered table and ask the user to confirm which to proceed
with before any tailoring or applying. Write chosen postings to
`applications/<company>-<role>/job.md`.
