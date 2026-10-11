# EnglishLearning

Personal English-learning workspace based on Active Recall and Spaced Repetition, focused on Vietnamese-to-English translation.

## Start learning

Type `/start-english` in Copilot Chat, or ask: “Start an English learning session.” The assistant presents seven new Vietnamese sentences, then ten distinct reviews from earlier sessions (or all eligible sentences if fewer than ten exist), one at a time. No model answer is shown before you respond. An unfinished session is resumed automatically on the same day.

Before the first sentence, the assistant prepares and saves the complete question plan in `data/history/lessons/YYYY-MM-DD.md`. The plan contains no answers or hints and is reused on resume; assessed answer history determines progress. Preparation does not count as studying. This batches question preparation up front, but feedback and saving results still take place after each answer.

After each sentence, you receive a natural translation, a detailed comparison, a distinction between errors and merely less-natural wording, and examples where useful. The result is saved for future sessions.

## Data structure

- `data/learner_profile.md`: your level, goals, and preferred topics.
- `data/review_schedule.md`: one table row per sentence with its current level (0–5) and next review date; due items stay at the top.
- `data/weak_patterns.md`: one table row per observed error pattern.
- `data/sentences/YYYY-MM.md`: one row per sentence (Vietnamese, standard version, structures, topic).
- `data/history/YYYY-MM.md`: append-only, one row per assessed answer (including your first answer).
- `data/history/lessons/YYYY-MM-DD.md`: a saved daily question plan, with no answers or assessment results.
- `logs/daily_log.md`: one row per completed learning session.
- `data/streak.md`: current and best streaks of consecutive completed learning days, shown at the end of each session. Each day counts once; incomplete sessions do not count.
- `.agents/skills/english-coach/SKILL.md`: the assistant workflow (single source of truth for the rules).
- `.github/prompts/start-english.prompt.md`: the `/start-english` prompt.

Learning data is stored only in the Markdown records above and versioned with git; each completed session is committed locally.

## Note

Every sentence has a unique `sentence_id`. Seeing an answer is not the same as knowing it; review intervals (1, 3, 7, 14, 30, 60 days) expand only after successful independent recall.
