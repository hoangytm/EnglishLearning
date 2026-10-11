---
name: english-coach
description: "Run the EnglishLearning daily Vietnamese-to-English practice workflow using Markdown records: 7 new sentences, then 7 reviews from real prior records when available; also use for requested review, progress, or recurring-error checks, not ordinary language questions."
---

# English Coach

Use this skill for daily English-learning sessions, Vietnamese-to-English translation practice, reviews of previously incorrect sentences or learned structures, and checks of progress or recurring errors in the current workspace. Do not use it for ordinary non-practice questions, such as a standalone word-meaning request or a technical explanation. Read `AGENTS.md` before starting and read the Markdown learning records in `data/` as the source of learning state; never invent learning history or review results.

## Files

All records are Markdown tables, one row per record. Dates are encoded in IDs (`S-YYYYMMDD-NNN`, `A-YYYYMMDD-NNN`), so the month file for any ID is `YYYY-MM.md`.

- `data/learner_profile.md`: level, goals, preferred topics. Only record what the learner states; leave `not set` otherwise.
- `data/review_schedule.md`: one row per sentence, sorted by `Next review` then ID; the single source of truth for current level, status, and next review date.
- `data/weak_patterns.md`: one row per observed error pattern.
- `data/sentences/YYYY-MM.md`: one immutable row per sentence first studied that month.
- `data/history/YYYY-MM.md`: append-only, one row per assessed attempt that month. The `new` attempt row holds the immutable first learner answer.
- `logs/daily_log.md`: one row per completed session.

Keep cells on one line and never use `|` inside a cell. Keep `Note` cells short (about 20 words).

## Start or resume the session

- When the user starts a daily session (for example, "start today's lesson", "help me study English", or "start today's 14 questions"), read before asking anything: `learner_profile.md`, `weak_patterns.md`, the last rows of `daily_log.md`, the top of `review_schedule.md` (rows due up to today plus a few after), and the current month's `sentences/` and `history/` files.
- Do not read older month files in full. Search them by ID only when a review needs a sentence's text or previous answers.
- If `learner_profile.md` has `not set` for level or goals, ask the learner once, briefly, save the answers, then continue. Do not block the session if they decline.
- **Resume check:** count today's rows (`A-YYYYMMDD-`) in the current `history/` file by type. If any exist and `daily_log.md` has no entry for today, the session is unfinished: tell the learner the progress (for example, "Resuming: 3/7 new, 0/7 review done") and continue from the next item instead of restarting.
- Run 7 new sentences first, then 7 reviews. Present exactly one Vietnamese sentence at a time and wait for the English response. Do not reveal a model translation, keywords, or hints that undermine recall.

## Choose new sentences

- Choose useful, common communication or work sentences that fit the learner profile's topics and level.
- Rotate topics: avoid reusing the topic of the previous new item when alternatives exist, and check the `Topic` column of the current month's `sentences/` file to avoid near-duplicates.
- Occasionally (about 1 in 3) target a structure from a weak pattern with count ≥ 2, using a fresh sentence.
- Raise difficulty gradually when most recent results are "correct and natural"; keep it steady otherwise.
- Append the `sentences/` row only after the sentence has actually been presented and assessed.

## Choose reviews

- Eligible: sentences whose ID date is before today. Never present a current-session new item as a review.
- Order from `review_schedule.md`: overdue rows first (oldest `Next review` first), then lowest `Level`, then sentences listed in weak patterns with count ≥ 2. Skip sentences last studied yesterday when other eligible rows exist.
- Get the Vietnamese text and standard version from the sentence's month file by searching its ID.
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

Stored result values: `correct` (correct and natural), `uncertain` (correct but less natural/uncertain), `incorrect`.

- New sentence → append one row to `data/sentences/YYYY-MM.md` (create the file from the previous month's header if missing): `ID | Vietnamese | Standard version | Structures | Topic`.
- Every assessed attempt → append one row to `data/history/YYYY-MM.md`: `Attempt | Sentence | Type | Learner answer | Result | Note`. `Type` is `new` or `review`; `Note` is the short error explanation, or `-` when correct. Never edit earlier rows.
- `review_schedule.md` → add a row for a new sentence or update the existing row: level, status, latest result, last studied, next review, and the correct/incorrect/uncertain/review counts. `Reviews` counts review attempts only. Move the row so the table stays sorted by `Next review`, then ID.
- `weak_patterns.md` → for each observed error, increment the matching row (or add one with count 1), update `Last seen`, and add the sentence ID to `Recent sentences`, keeping only the 5 most recent. A pattern with count ≥ 2 is recurring and gets priority.
- `logs/daily_log.md` → append one row only after all planned questions are completed.

## Complete the session

After the 7 new items and all available planned reviews, state the number of new and review items completed, totals for correct, incorrect, and less-natural/uncertain answers, recurring errors, the sentences due next with their dates, and confirm the files updated. Do not end a normal daily session after only a few explained items.

If the workspace is a git repository, commit the data with `git add data logs` and `git commit -m "Session YYYY-MM-DD"`. Never push.
