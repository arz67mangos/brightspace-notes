---
name: brightspace-quiz
description: Help with quizzes and self-tests from the user's own revision notes. Answers quiz questions the user pastes (with reasoning and note references), or guides them to the answer without giving it, quizzes them from the notes, saves pasted question types for future self-tests, and tracks weak spots. Use when the user wants to revise, be tested, "quiz me", or pastes quiz questions.
---

# Quiz help

Source material: `notes/<course>/<module>/*.md` (sections "Self-check questions", "Key ideas", "Likely exam/test points"), `GLOSSARY.md`, and `notes/<course>/question-bank.md` if present.

## 1. The user decides how much help they get
- **Default** (nothing said): answer pasted questions directly, with a one-line reason each and the note/slide it comes from, so they can double-check.
- **"Guide me" / "this one matters, don't give the answer" / "point me to the notes"**: do **not** state the answer. Point to the note sections (link them), explain the concept and how to reason about that question type, ask what they think, and confirm or correct after they answer.
- If it's unclear which they want and the quiz looks important (graded, timed, "Mandatory"), ask once: "Straight answers, or point me to the notes and walk me through it?" Then follow the choice for the rest of the session.
- Never open, start or submit a Brightspace quiz attempt yourself. Work only from text the user pastes or notes they have.

## 2. Pasted questions become a question bank
When the user pastes quiz questions, append them to `notes/<course>/question-bank.md` (gitignored, personal): question, options, the question **type** (MCQ single/multi, true-false, fill-in, short answer, calculation), topic, and the answer **only once the user has confirmed it** (otherwise mark "unverified"). Use the bank later to run self-tests in the **same question types and wording style**, writing fresh variants (new numbers/examples) instead of repeating the originals.

## 3. Quiz mode (self-test)
1. Ask scope and format (AskUserQuestion): topic(s), number of questions (default 8), style: matches the question bank types / short answer / multiple choice / mixed.
2. Read `notes/<course>/progress.md`; start with the weak topics there.
3. Ask **one question at a time**, wait for the answer, then say right / partly / wrong, give the correct answer from the notes with the note link (and slide link if present) and a one-line fix for the misconception. Draw from the self-check list and question bank first, then write new ones from Key ideas.
4. Re-ask a variant of anything missed later in the session.
5. At the end summarise score and weak concepts, and append to `notes/<course>/progress.md` (newest first): date, topic, score, concepts missed.

If the notes are thin for a topic, say so and suggest capturing more material instead of quizzing from general knowledge.
