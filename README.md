# EnglishLearning

Personal English-learning workspace based on Active Recall and Spaced Repetition, focused on Vietnamese-to-English translation.

## Start learning

Type `/start-english` in Copilot Chat, or ask: “Start an English learning session.” The assistant presents seven new Vietnamese sentences, then up to seven reviews from earlier sessions, one at a time. No model answer is shown before you respond. An unfinished session is resumed automatically on the same day.

After each sentence, you receive a natural translation, a detailed comparison, a distinction between errors and merely less-natural wording, and examples where useful. The result is saved for future sessions.

## Data structure

- `data/learner_profile.md`: your level, goals, and preferred topics.
- `data/sentence_bank.md`: first-attempt snapshot for each sentence: source sentence, your first answer, standard version, feedback, topic.
- `data/review_schedule.md`: one table row per sentence with its current level (0–5) and next review date.
- `data/weak_patterns.md`: observed error patterns with counts and related sentences.
- `data/answer_history.md`: append-only history of every assessed answer.
- `logs/daily_log.md`: concise log of each completed learning session.
- `.agents/skills/english-coach/SKILL.md`: the assistant workflow (single source of truth for the rules).
- `.github/prompts/start-english.prompt.md`: the `/start-english` prompt.

Learning data is stored only in the Markdown records above and versioned with git; each completed session is committed locally.

## Note

Every sentence has a unique `sentence_id`. Seeing an answer is not the same as knowing it; review intervals (1, 3, 7, 14, 30, 60 days) expand only after successful independent recall.
