---
name: brightspace-quiz
description: Quiz the user from their own revision notes (self-check questions and key ideas), adapt to what they get wrong, and keep a progress file of weak spots. Use when the user wants to revise, be tested, or "quiz me" on a topic/module from their notes.
---

# Quiz mode

Source material: `notes/<course>/<module>/*.md` (sections "Self-check questions", "Key ideas", "Likely exam/test points") and `GLOSSARY.md` if present. Never use or reveal the contents of graded Brightspace quizzes; this quizzes the user on **their notes only**.

1. Ask scope and format (AskUserQuestion): which topic(s)/module, number of questions (default 8), and style: short answer / multiple choice / mixed / "explain it to me".
2. Read `notes/<course>/progress.md` if it exists: start with the weak topics listed there (past misses first, then new material).
3. Ask **one question at a time**, wait for the answer, then: say right / partly / wrong, give the correct answer from the notes with the link to the note (and the slide link if the note has one), and a one-line explanation of the misconception when wrong. Draw questions from the self-check list first, then write new ones from Key ideas/exam points (same style as the course: "which determinant and which way does the curve shift?").
4. Keep a running score. After a wrong or partial answer, re-ask a variant later in the same session.
5. At the end, summarise: score, weak concepts, and update `notes/<course>/progress.md` (append, newest first): date, topic, score, concepts missed (one line each). Offer a follow-up round on only the misses.

If the notes are thin for a topic, say so and suggest capturing more material instead of quizzing from general knowledge.
