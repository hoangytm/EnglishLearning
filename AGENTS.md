# EnglishLearning Workspace Rules

## Goal

Practise active translation from Vietnamese to English with Active Recall and Spaced Repetition. Present **one** Vietnamese sentence at a time; never reveal a model answer or translation hint before the learner responds.

## Skill activation

- When the user asks to study English, start a learning session, review, practise Vietnamese-to-English translation, or check previously learned English errors, proactively use the available `english-coach` Skill. The user does not need to invoke `$english-coach`.
- For a recognised English-learning request, read the current learning data before presenting a question. Never invent learning history or review results.
- On starting a learning session, follow the Skill workflow automatically: present one sentence at a time and wait for the learner's response.
- Do not start this learning workflow for ordinary, non-practice questions, such as asking for a word meaning or an explanation of a technical topic.

## Workflow

The session flow, resume check, grading, spaced-repetition levels, and data-update rules live in `.agents/skills/english-coach/SKILL.md`. That file is the single source of truth; follow it exactly and do not duplicate its rules here.

## Non-negotiable rules

- One Vietnamese sentence at a time; no answer, keyword, or hint before the learner responds.
- Never invent learning history, review results, errors, or learner-profile data. Record only what was observed or stated.
- Never delete or overwrite history: `answer_history.md` is append-only, and first learner answers in `sentence_bank.md` are immutable. Only `review_schedule.md` rows, `weak_patterns.md` counts, and `learner_profile.md` fields are updated in place.
- Seeing an answer does not count as knowing it.
- Use UTF-8 Markdown and keep every existing ID unique and unchanged.
