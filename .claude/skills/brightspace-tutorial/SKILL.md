---
name: brightspace-tutorial
description: Attempt a tutorial/homework sheet from the user's own revision notes, showing which note section each answer comes from and flagging assumptions, so the user can compare with their own answers and the lecturer's model answers. Use when the user shares a tutorial worksheet (.docx/.pdf) and wants drafted answers.
---

# Tutorial helper

Prerequisite: the topic's notes exist (`brightspace-notes` skill). If they don't, capture the topic's videos first.

1. Convert the sheet: `python scripts/docs.py "<tutorial file>" work/tutorial` and read the .md. Note links (e.g. article URLs) and any "not in student copy" remarks.
2. **List missing information before answering.** If a question refers to something you can't see (an article, a figure, group-discussion text the tutor hands out), say so and ask; don't invent the question. Offer a clearly labelled "likely angle" at most.
3. Read the topic's notes (`notes/<course>/<module>/*.md`, plus GLOSSARY/EXAM_FOCUS if present). Answer **only from the notes and slides** (optionally the lecture-notes document). If the notes don't cover something, say "not covered in notes" instead of filling from general knowledge, then optionally add the general answer marked as such.
4. Write `notes/<course>/<module>/tutorial-N-answers.md`:
   - Per question: the answer in the style the module teaches (named determinant, direction of shift, "change in quantity demanded vs demand", axes labelled, etc.), a text graph where graphs are asked for (generate it with `python scripts/graph.py <preset>`, presets listed when run with no argument: ppc, supply-shift, supply-move, market, d-up-s-down, d-down-s-up, d-small-s-down, adas-demand, adas-cost; paste the output in a code block; add a preset to the script if none fits, don't hand-draw), and a `*(Notes: Part 3, Part 5)*` pointer to the sections used (link the note files).
   - Multiple choice: the letter, then a rationale that also says why each wrong option is wrong.
   - An **"Items to double-check"** list at the end: every judgement call, ambiguous wording or assumption (e.g. which platform a software question assumes), stated as a choice between readings.
5. Tell the user plainly which answers are solid and which are judgement calls. The user compares with their own and the model answers; offer to explain any difference.

Answer style follows what the user asks for: if they say a question matters and they don't want the answer handed over, point to the note sections and walk them through how to think about it instead. When they haven't said, give the answer with the reasoning and note references.
