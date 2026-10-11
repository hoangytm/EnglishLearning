---
name: english-coach
description: "Run the EnglishLearning daily Vietnamese-to-English practice workflow using Markdown records: 7 new sentences, then 7 reviews from real prior records when available; also use for requested review, progress, or recurring-error checks, not ordinary language questions."
---

# English Coach

Use this skill for daily English-learning sessions, Vietnamese-to-English translation practice, reviews of previously incorrect sentences or learned structures, and checks of progress or recurring errors in the current workspace. Do not use it for ordinary non-practice questions, such as a standalone word-meaning request or a technical explanation. Read `AGENTS.md` before starting and read the Markdown learning records in `data/` as the source of learning state; never invent learning history or review results.

## Files

- `data/learner_profile.md`: level, goals, preferred topics. Only record what the learner states; leave `not set` otherwise.
- `data/sentence_bank.md`: one immutable section per sentence, a snapshot of its first attempt. Current state does not live here.
- `data/review_schedule.md`: one table row per sentence; the single source of truth for current level, status, and next review date.
- `data/answer_history.md`: append-only, one section per assessed attempt.
- `data/weak_patterns.md`: observed error patterns with counts and related sentence IDs.
- `logs/daily_log.md`: one entry per completed session.

## Start or resume the session

- When the user starts a daily session (for example, "start today's lesson", "help me study English", or "start today's 14 questions"), read every file above before asking anything.
- If `learner_profile.md` has `not set` for level or goals, ask the learner once, briefly, save the answers, then continue. Do not block the session if they decline.
- **Resume check:** count today's sections in `answer_history.md` by attempt type. If any exist and `daily_log.md` has no entry for today, the session is unfinished: tell the learner the progress (for example, "Resuming: 3/7 new, 0/7 review done") and continue from the next item instead of restarting.
- Run 7 new sentences first, then 7 reviews. Present exactly one Vietnamese sentence at a time and wait for the English response. Do not reveal a model translation, keywords, or hints that undermine recall.

## Choose new sentences

- Choose useful, common communication or work sentences that fit the learner profile's topics and level.
- Rotate topics: avoid reusing the topic of the previous new item when alternatives exist, and check the `Topic` fields in `sentence_bank.md` to avoid near-duplicates.
- Occasionally (about 1 in 3) target a structure from a weak pattern with count ≥ 2, using a fresh sentence.
- Raise difficulty gradually when most recent results are "correct and natural"; keep it steady otherwise.
- Append the `sentence_bank.md` section only after the sentence has actually been presented and assessed.

## Choose reviews

- Eligible: sentences whose first-study date is before today. Never present a current-session new item as a review.
- Order from `review_schedule.md`: overdue rows first (oldest `Next review` first), then lowest `Level`, then sentences linked to weak patterns with count ≥ 2. Skip sentences last studied yesterday when other eligible rows exist.
- If fewer than 7 eligible sentences exist, review every eligible real record, tell the learner exactly how many reviews are unavailable, and do not manufacture old records.

## Assess the response

After the learner answers, provide:

1. The most natural English version for a common context.
2. A direct comparison with their sentence.
3. Accurate explanations of grammar, vocabulary, collocation, preposition, tense, or phrasing errors.
4. A clear label: "incorrect", "correct but less natural/uncertain", or "correct and natural".
5. A short additional example when it reinforces the point.

Do not treat a stylistic choice as an error. Accept natural alternatives unless the context makes their meaning incorrect.

**Vietnamese ambiguity:** Vietnamese often leaves number, tense, articles, and subject implicit. Accept any reading the source reasonably allows (for example, `bản cập nhật` → `update` or `updates`) and mention the more likely reading as a note, not an error. Mark "incorrect" only when the answer changes the meaning (adds or drops information, for example `cuộc họp` → `all the meetings`), is ungrammatical, or is unidiomatic enough to mislead. Capitalisation or punctuation slips alone are not errors; mention them briefly.

## Spaced-repetition levels

| Level | Interval | Status |
| --- | --- | --- |
| 0 | 1 day | learning |
| 1 | 3 days | learning |
| 2 | 7 days | reviewing |
| 3 | 14 days | reviewing |
| 4 | 30 days | mastered |
| 5 | 60 days | mastered |

Apply after every independently produced attempt (new or review):

- incorrect → Level 0, next review = today + 1 day.
- correct but less natural/uncertain → Level 1, next review = today + 3 days.
- correct and natural → Level = max(current + 1, 2), capped at 5; next review = today + that level's interval.

Seeing the answer never counts as recall; do not raise a level or a correct count for it.

## Update learning data

After each assessment, immediately write UTF-8 Markdown data. Do not wait for the end of the session:

- New sentence → append one `sentence_bank.md` section: unique ID `S-YYYYMMDD-NNN`, Vietnamese, first learner answer, standard version, assessment, observed explanation/errors, structures/collocations, topic, first-study date. Never replace the first learner answer.
- Every assessed attempt → append one `answer_history.md` section: unique ID `A-YYYYMMDD-NNN`, sentence ID, date, attempt type (`new`/`review`), learner answer, standard version, result, explanation, observed structures/errors. Never edit earlier sections.
- `review_schedule.md` → add a row for a new sentence or update the existing row: level, status, latest result, last studied, next review, and the correct/incorrect/uncertain/review counts. `Reviews` counts review attempts only. Keep rows sorted by sentence ID.
- `weak_patterns.md` → for each observed error, increment the matching pattern (or add one with count 1), update the latest date, and append the sentence ID to `Related sentences`. A pattern with count ≥ 2 is recurring and gets priority.
- `logs/daily_log.md` → append a real session summary only after all planned questions are completed.

## Complete the session

After the 7 new items and all available planned reviews, state the number of new and review items completed, totals for correct, incorrect, and less-natural/uncertain answers, recurring errors, the sentences due next with their dates, and confirm the files updated. Do not end a normal daily session after only a few explained items.

If the workspace is a git repository, commit the data with `git add data logs` and `git commit -m "Session YYYY-MM-DD"`. Never push.
