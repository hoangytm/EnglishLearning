---
name: english-coach
description: "Prepare a saved daily lesson, then run Vietnamese-to-English practice using Markdown records: 7 new sentences and 10 reviews from real prior records when available; also use for requested review, progress, or recurring-error checks, not ordinary language questions."
---

# English Coach

Use this skill for daily English-learning sessions, Vietnamese-to-English translation practice, reviews of previously incorrect sentences or learned structures, and checks of progress or recurring errors in the current workspace. Do not use it for ordinary non-practice questions, such as a standalone word-meaning request or a technical explanation. Read `AGENTS.md` before starting and read the Markdown learning records in `data/` as the source of learning state; never invent learning history or review results.

## Files

Learning records are Markdown tables, one row per record. Dates are encoded in IDs (`S-YYYYMMDD-NNN`, `A-YYYYMMDD-NNN`), so the month file for an assessed sentence or attempt is `YYYY-MM.md`. Daily lesson plans use a separate date-based file.

- `data/learner_profile.md`: level, goals, preferred topics. Only record what the learner states; leave `not set` otherwise.
- `data/review_schedule.md`: one row per sentence, sorted by `Next review` then ID; the single source of truth for current level, status, and next review date.
- `data/weak_patterns.md`: one row per observed error pattern.
- `data/sentences/YYYY-MM.md`: one immutable row per sentence first studied that month.
- `data/history/YYYY-MM.md`: append-only, one row per assessed attempt that month. The `new` attempt row holds the immutable first learner answer.
- `data/history/lessons/YYYY-MM-DD.md`: the immutable daily question plan, prepared before the first sentence; it is not evidence of study or recall and contains no answers or hints.
- `logs/daily_log.md`: one row per completed session.
- `data/streak.md`: one current snapshot of consecutive completed learning days, rebuilt from `logs/daily_log.md`.

Keep cells on one line and never use `|` inside a cell. Keep `Note` cells short (about 20 words).

## Start or resume the session

- When the user starts a daily session (for example, "start today's lesson", "help me study English", or "start today's 17 questions"), read before asking anything: `learner_profile.md`, `weak_patterns.md`, `streak.md`, the last rows of `daily_log.md`, the top of `review_schedule.md` (rows due up to today plus a few after), and the current month's `sentences/` and `history/` files. Refresh the streak snapshot using the rules below, so a missed day is reflected before learning starts.
- Do not read older month files in full. Search them by ID only when a review needs a sentence's text or previous answers.
- If today's session is already recorded as completed in `daily_log.md`, report that it is complete rather than regenerating a lesson or recording another completion.
- If the learner profile is unset, use the default work-communication context to prepare the lesson without blocking its creation. Offer to fill in the profile later; record only what the learner states.
- Prepare or reuse today's saved lesson using the rules below. **Resume check:** match today's assessed history rows to the plan by sentence ID and attempt type. Report completed counts against the saved targets, then continue with the first unassessed row. Reconcile any missing data updates for an existing attempt before advancing; never assess or append that attempt again just to recover progress.
- Follow the saved order: 7 new sentences first, then the planned reviews (up to 10). Present exactly one Vietnamese sentence at a time and wait for the English response. Do not reveal a model translation, keywords, or hints that undermine recall.

## Prepare today's lesson

- Use `data/history/lessons/YYYY-MM-DD.md`, where the date is today's local calendar date. Create the directory if missing. Generate all remaining new questions and select all review questions in one preparation step, save the complete plan, and validate it before presenting the first unassessed sentence.
- If the plan already exists, reuse it without replacing its questions, IDs, order, or targets. Do not select new questions between attempts. Leave earlier days' plans unchanged.
- If no plan exists but today's assessed attempts already exist, reconstruct their question rows from the real sentence bank and history first, retaining their IDs and type. Include these completed rows in the targets, then fill only the remaining slots. Do not restart a partially completed day.
- Reserve unique `S-YYYYMMDD-NNN` IDs for planned new sentences, checking both the sentence bank and existing lesson plans for collisions. A reserved ID does not mean the sentence has been studied. Reuse its exact ID and Vietnamese text when it is later assessed.
- Choose all new questions using the new-sentence rules below, checking for near-duplicates both in the bank and within the planned batch. Choose reviews only from real assessed sentences using the review rules below; never from an unassessed draft plan.
- Set `New target` to 7. Set `Review target` to the smaller of 10 and the eligible distinct earlier-sentence count, including any already reviewed today. Save `Unavailable reviews` as 10 minus that target. Freeze these targets for this daily session.
- Store the date, targets, and an ordered table with columns `Order | Type | Sentence ID | Vietnamese`. Use `new` or `review` for `Type`. Do not store English translations, structures, learner answers, results, or explanations in the plan. Do not show the full question list in chat; only present the current sentence.
- Before starting, check that orders are sequential, sentence IDs are unique, the plan has exactly 7 new rows and exactly `Review target` review rows, new rows precede reviews, and every review ID resolves to an assessed sentence first studied before today. Check that reconstructed completed rows match the existing history. Do not start an invalid or incomplete plan.
- Preparation alone must not add rows to the sentence bank, assessed answer history, review schedule, weak patterns, or completed-session log, and must not increase the streak. Only assessed answers trigger learning-data updates.

Plan format (placeholders below describe the schema, not learning records):

```markdown
# Lesson YYYY-MM-DD

- Lesson date: YYYY-MM-DD
- New target: 7
- Review target: <eligible count capped at 10>
- Unavailable reviews: <10 minus review target>

| Order | Type | Sentence ID | Vietnamese |
| --- | --- | --- | --- |
```

## Choose new sentences

- Choose useful, common communication or work sentences that fit the learner profile's topics and level.
- Rotate topics: avoid reusing the topic of the previous new item when alternatives exist, and check the `Topic` column of the current month's `sentences/` file to avoid near-duplicates.
- Occasionally (about 1 in 3) target a structure from a weak pattern with count ≥ 2, using a fresh sentence.
- Raise difficulty gradually when most recent results are "correct and natural"; keep it steady otherwise.
- Append the `sentences/` row only after the sentence has actually been presented and assessed.

## Choose reviews

- Eligible: sentences whose ID date is before today. Never present a current-session new item as a review.
- Review each sentence at most once per daily session. On resume, skip sentence IDs already assessed as reviews today; those attempts count toward the planned review target.
- Order from `review_schedule.md`: overdue rows first (oldest `Next review` first), then lowest `Level`, then sentences listed in weak patterns with count ≥ 2. Skip sentences last studied yesterday when other eligible rows exist.
- Get the Vietnamese text and standard version from the sentence's month file by searching its ID.
- During preparation, copy only the Vietnamese text into the plan. Retrieve the standard version for feedback after the learner answers; do not expose it in the saved question plan.
- If fewer than 10 eligible sentences exist, review every eligible real record, tell the learner exactly how many reviews are unavailable (10 minus the eligible count), and do not manufacture old records or repeat sentences to fill the quota. Otherwise, complete all 10 distinct reviews.

## Assess the response

After every new or review answer, explain in Vietnamese, with English sentences and phrases as examples. Give enough detail to understand why, not just a corrected answer. Use this order:

1. Quote the learner's exact answer and give a clear label: "incorrect", "correct but less natural/uncertain", or "correct and natural".
2. Give a natural version a native speaker would commonly use in the likely context. State the context or register when it matters (for example, a work email versus casual conversation). Do not imply that there is only one valid native-speaker version.
3. Compare the answer phrase by phrase where correction is needed: quote the problematic phrase, show its replacement, and explain why. Cover each meaningful error in grammar, meaning, vocabulary, collocation, preposition, tense, or phrasing. For each main issue, use roughly 2-4 explanatory sentences describing the rule or meaning difference and how it applies here; do not merely name the error.
4. Explain why the suggested native-speaker phrasing fits the context. Clearly separate genuine errors from valid but less-natural or differently formal alternatives. If the learner's answer is already natural, say so and explain what works instead of inventing corrections.
5. Give 1-2 short additional examples when useful, explaining the relevant contrast, then finish with 1-2 takeaways to remember.

Keep the detailed explanation in chat; retain only the short `Note` in learning history. Persist the assessment immediately according to the data-update rules below.

## Pause before the next sentence

- Do not include the next Vietnamese sentence in the same message as an assessment. When questions remain, finish by asking the learner to say they are ready or ask about the explanation, then wait for their response.
- If the learner asks a follow-up question, clarify the same answer and wait again. Present the next sentence only after they indicate readiness (for example, "tiep", "next", or "OK"). This pause does not abandon the planned session.
- Follow-up discussion or repeating the correction after seeing it is not a new recall attempt: do not append another assessed attempt or change counts or levels for it.
- After the final planned answer, provide the explanation and the completed-session summary; there is no next sentence to wait for.

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
- Keep the daily lesson plan unchanged. Its row is complete only when the matching assessed attempt exists in the monthly history; never write simulated answers or placeholder results to mark progress.
- `review_schedule.md` → add a row for a new sentence or update the existing row: level, status, latest result, last studied, next review, and the correct/incorrect/uncertain/review counts. `Reviews` counts review attempts only. Move the row so the table stays sorted by `Next review`, then ID.
- `weak_patterns.md` → for each observed error, increment the matching row (or add one with count 1), update `Last seen`, and add the sentence ID to `Recent sentences`, keeping only the 5 most recent. A pattern with count ≥ 2 is recurring and gets priority.
- `logs/daily_log.md` → append one row only after all planned questions are completed.

## Update the streak

- A day qualifies only after every row in the saved daily lesson plan (7 new sentences and its saved review target, up to 10) has a matching assessed attempt, the related learning-data updates are complete, and its completed-session row has been saved in `logs/daily_log.md`. A shortage of eligible reviews does not prevent completion. Partial sessions, explanations, and follow-up questions do not count.
- Use the learner's local calendar date (the current date in the conversation unless the learner specifies otherwise), not elapsed 24-hour periods or UTC dates.
- Read the `Date` column from the completed-session log, deduplicate dates, and sort them chronologically. Count each day once, even if multiple sessions or repeated summaries occur on that date. Never create log entries to fill gaps.
- With no completed dates, write `Current streak = 0`, `Best streak = 0`, and `Last completed = -`.
- Otherwise, `Last completed` is the latest completed date. `Best streak` is the longest consecutive-day run across all completed dates. `Current streak` is the length of the run ending on `Last completed` when it is today or yesterday; if it is older than yesterday, set `Current streak = 0` without losing the best streak. Completing a session after a gap starts a new current streak at 1.
- Update the single row in `data/streak.md` in place. Rebuild from the log rather than incrementing blindly, so repeating a summary or recovering after an interrupted write cannot count a day twice. If the file is missing, recreate it from the log with the same columns.

## Complete the session

Save the completed-session log row first, unless the session has already been logged, then rebuild `data/streak.md`. If all planned answers were saved before an interruption but the completion log or streak was not, finish these updates on resume without asking extra questions or recording extra attempts.

After all saved lesson rows have been assessed, state the number of new and review items completed against the saved targets, any unavailable reviews, totals for correct, incorrect, and less-natural/uncertain answers, recurring errors, the sentences due next with their dates, and confirm the files updated. Do not end a normal daily session after only a few explained items.

Include the updated streak in the Vietnamese summary: "Streak hien tai: X ngay lien tiep. Ky luc: Y ngay." Display the actual values from `data/streak.md`, not example numbers.

If the workspace is a git repository, commit the data with `git add data logs` and `git commit -m "Session YYYY-MM-DD"`. Never push.
