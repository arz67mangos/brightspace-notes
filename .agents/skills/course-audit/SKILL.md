---
name: course-audit
description: Full audit of the user's Brightspace courses for content that was never captured, failed, or is new since the last capture, then capture or work around each gap. Use when the user says "check for new content", "did I miss anything", "audit my courses", or runs /course-audit. Scoped to the courses the user names; never touches quizzes, surveys or assignments.
---

# Course audit: find what is new, missed or broken, then fix it

Repo root = folder with `scripts/` and `notes/`. Read `AGENTS.md` rules first. One course per pass; in Claude Code one session per course, in Codex one thread per course (see `docs/course-session-kickoff.md`).

## 0. Agree the scope (ask, don't assume)
Ask which courses to audit and which to ignore (done or not needed yet). Ask once about anything unclear: terms/courses that look like another cohort, content you were told to exclude earlier, items that are not Lessons (see Known limits). Never audit a course the user did not name.

## 1. Fresh login and outline
1. `python scripts/doctor.py`. If the session may have expired, `python scripts/bs.py login <base>` (user signs in; one browser script at a time).
2. Keep the old outline: copy `notes/<ou>/toc.md` to `notes/<ou>/toc.prev.md` before re-running `python scripts/bs.py toc <base> <ou>`.
3. Diff `toc.prev.md` against the new `toc.md`: **new topics/modules**, renamed or moved topics, and items that disappeared.

## 2. Coverage gaps
`python scripts/verify.py <ou> notes/<course>` -> `notes/<ou>/COVERAGE.md`. Build one list per course:
- **new** (in the new outline, not captured), **FAILED** (attempted, no result), **not captured** (never requested), **flagged** (transcript stops early, missing frames, unconverted files, page-count mismatch).
- **Skipped on purpose:** quizzes, surveys, dropboxes, discussions. List them, never open them. Reminder pages are read for dates only.
Show the list and ask which items to capture. Never capture a whole course silently.

## 3. Capture and workarounds (in this order, only for approved items)
Follow `course-capture` for the normal path (video, doc, page). When one fails, try the next:
1. Video: retry once headless/visible (the script already does), then `bs.py page` to find the real player URL, `bs.py yuja <url>` for a direct YuJa link, or `video.py` on an exposed m3u8/mp4/vtt.
2. Multi-lesson SCORM/Rise course: `bs.py course`. Open accordions/tabs are handled; knowledge checks are skipped.
3. Document: `bs.py doc`, then `docs.py <file> <dir> --images`; scanned or garbled PDF: `ocr.ps1` on the page images; HTML topic: also fetch the files it links.
4. Anything else (games, unfamiliar embeds): stop, describe it, give 2-3 options with a recommendation, wait.
Every `bs.py video/doc` attempt is logged; items still failing after this go under **Gaps** with the reason, not silently dropped.

## 4. Close the loop
For every course touched: write/update notes, `linkify.py`, `verify.py` again, `rollup.py`, `master.py notes/<course> --ou <ou>`, update `TIMELINE.md` if dates changed. Report per course: new found, captured now, still failing (with reason), skipped on purpose, and what the audit cannot see (Assignments, Quizzes, Discussions, Media Library, unreleased items). Do not commit anything under `notes/`.
