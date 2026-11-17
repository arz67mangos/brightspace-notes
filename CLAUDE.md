# CLAUDE.md

@AGENTS.md

## Claude Code specifics
- Skills load from `.claude/skills/` (authored here); `python scripts/sync_agents.py` copies them to `.agents/skills/` for Codex. Edit `.claude/skills/` and `AGENTS.md`, never the `.agents/skills/` copies.
- Claude Code can start one session per course itself (the standard workflow's step 2): give each a brief from `docs/course-session-kickoff.md` and the course's `MASTER.md` path. Sessions share this checkout, so `notes/`, `.profile/` and `work/` (gitignored) are visible to all; run only one browser script at a time.
- Keep `AGENTS.md` and this file consistent: rules live in `AGENTS.md` only.
