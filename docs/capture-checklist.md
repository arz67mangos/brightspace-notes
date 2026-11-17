# Capture checklist (per course)

Tick every line, or write why it is not possible (not released yet, not available to me, failed with reason). Do not tick from memory: look at the files.

## Material captured
- [ ] Outline: `notes/<OU>/toc.md` exists and matches Brightspace's Lessons page.
- [ ] Every approved module has a folder `notes/<COURSE>/<module-title-slug>/`.
- [ ] Every lecture video has an `assets/<slug>/` with `slides.md`, `sheets/`, `frames/`, `transcript.md`, `frames.txt`.
- [ ] Every lecture-notes file, slide deck, PDF, Word, PowerPoint, zip, spreadsheet and data file is downloaded in `work/` and converted to markdown in `assets/<slug>/`.
- [ ] Every assessment brief, rubric, template, FAQ, module outline and schedule is captured as full text.
- [ ] SCORM / Rise lesson courses captured with `bs.py course` (lessons.json present).
- [ ] No quizzes, surveys, dropboxes or discussions were opened (they appear as "skipped on purpose" in COVERAGE.md).

## Notes written
- [ ] One note per captured topic with front matter, Key ideas, Details, Likely exam/test points, Self-check questions (`N. Question? *answer*`) and Gaps.
- [ ] `[mm:ss]` cites are linked (`linkify.py`); ASR errors are corrected and listed under Gaps.
- [ ] `INDEX.md` has one line per note.

## Verified
- [ ] `python scripts/verify.py <OU> notes/<COURSE>` ran; COVERAGE.md has no FAILED and every flagged item is fixed or explained.
- [ ] Item counts reported: topics found / captured / skipped on purpose / failed.

## Context files
- [ ] `rollup.py` ran: `EXAM_FOCUS.md`, `GLOSSARY.md`, per-module `CHEATSHEET.md`.
- [ ] `master.py` ran: `MASTER.md` lists every note, key terms and source files, and carries the no-inventing and Parked / Reminders rules.
- [ ] `TIMELINE.md` lists dates, weightings and sources from the schedule/assessment pages only; unknown dates are under "Not stated / to confirm".

## Compare against a reference
- [ ] If given a manifest: `python scripts/manifest.py check notes <manifest.json>`; every gap is captured, or explained (named differently, not released, failed).
