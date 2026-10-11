---
name: english-coach
description: "Prepare a saved daily Vietnamese-to-English lesson, normally 7 new sentences and 10 reviews; validate learning records, suggest backlog adjustments with permission, practise transfer, and report weekly progress or recurring errors without starting practice."
---

# English Coach

Use this skill for daily English-learning sessions, Vietnamese-to-English translation practice, reviews of previously incorrect sentences or learned structures, and checks of progress or recurring errors in the current workspace. Do not use it for ordinary non-practice questions, such as a standalone word-meaning request or a technical explanation. Read `AGENTS.md` before starting and read the Markdown learning records in `data/` as the source of learning state; never invent learning history or review results.

## Portable runtime

- This is the shared workflow for Codex and GitHub Copilot, not a host-specific agent. `start-english` selects learning; `english-progress` selects read-only reporting. Host prompt files are optional entry points, not additional workflow rules.
- Locate the workspace root containing `AGENTS.md` and `scripts/validate_learning.py`. Paths in this Skill are relative to that root. Use native tools available in the host, not a hard-coded Copilot or Codex tool API. Writing learning records requires workspace write permission; validation requires permission to execute Python. If the host blocks an operation, explain what permission is missing and stop that operation. Do not bypass sandbox restrictions, request secrets through chat, or claim a blocked operation succeeded.
- Select one available Python 3.9+ launcher and use it consistently for every command in this workflow: `python` or `py -3` on Windows, `python3` or `python` on Linux/macOS/WSL. Check its version first. A launcher that exists but is too old does not qualify; try another available launcher before reporting Python unavailable. The command examples below use `python` as a placeholder for the selected launcher.
- Run from the workspace root when possible. Otherwise, pass the quoted absolute script path and `--root` pointing to the same workspace, for example `<launcher> -B "<workspace>/scripts/validate_learning.py" --root "<workspace>" --date YYYY-MM-DD`. The script's default root is its own workspace, not the terminal's current directory. Quote paths containing spaces and use syntax appropriate to the active shell; do not assume PowerShell, Bash, or a Windows drive path.
- Use the learner's local calendar date for every `--date` flag. A conversation date takes precedence; without one, obtain the local date from the runtime rather than reusing a date from a previous report. On WSL, use the same workspace files as the other host, not a copied data directory.
- Learning requires file writes, while progress reports are read-only. Do not start a learning session in a read-only environment or write data during a report. Explain missing permissions rather than fabricating saved records. Switching hosts does not change the saved plan's targets or reset progress; reread the actual files and avoid concurrent writers.

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
- `scripts/validate_learning.py`: read-only data checks and rolling weekly metrics; requires Python 3.9 or newer and no third-party packages.

Keep cells on one line and never use `|` inside a cell. Keep `Note` cells short (about 20 words).

## Validate the records

- Run commands from the workspace root, supplying the learner's current local date explicitly instead of the example date: `python -B scripts/validate_learning.py --date YYYY-MM-DD`. The script reads records and returns a nonzero exit code on inconsistency; it never writes learning data or grades English.
- Refresh the streak snapshot from actual completed dates before the first check of a learning session. Run the validator before preparation, after saving the complete plan, after each assessed answer and all related updates, and after final log/streak updates. Run it with `--require-complete` before writing the completion log, so every saved question must have an actual assessed attempt.
- If validation fails, stop before the next question or completion. Diagnose the reported records and repair only mutable current fields using real history. Do not edit immutable plans or past answers, guess results, append an attempt twice, or change an old assessment to make a check pass. Ask the learner how to resolve an immutable conflict.
- Warnings about legacy attempts without a plan are not proof of completion; reconstruct the plan from real records before resuming. Existing valid older plans remain immutable and keep their saved targets and selection policy.
- Use the selected launcher from Portable runtime for all checks, including the report and completion commands. If no supported Python launcher works, report that automated checks cannot run and pause rather than silently claiming validation passed.

## Report progress without practice

- For progress, weekly summary, recurring-error checks, or `/english-progress`, run `python -B scripts/validate_learning.py --date YYYY-MM-DD --report`. Do not generate a lesson, ask translation questions, append attempts, write a completion log, update streak, or create report files for this request.
- If validation fails, report the inconsistency instead of presenting unreliable totals. Otherwise, explain the JSON metrics in Vietnamese: the last 7 calendar days ending today versus the preceding 7 days, completed learning days, new and review counts and correct percentages separately, and due/overdue counts.
- `correct` is independently correct and natural; `uncertain` must remain separate. Always include denominators. A percentage of `null` means no attempts, not 0% recall. Include unfinished-day attempts in attempt counts but not in completed-day counts.
- Use actual `observed_notes` and, if necessary, targeted history reads to identify repeated errors and compare equivalent patterns across periods. Different note wording is not automatically a different or identical error. The current weak-pattern counts are lifetime snapshots with only 5 recent IDs; they cannot establish weekly improvement on their own. Cite concrete attempt IDs for any claimed pattern change, and say when evidence is insufficient.
- Compare review recall only when both periods have review attempts; with fewer than 5 review attempts in either period, describe the sample as too small for a reliable trend. Even larger samples can differ in difficulty; avoid declaring mastery from a weekly percentage alone.
- Finish with one practical focus for the next week grounded in observed attempts or due backlog. If there is no such evidence, suggest continuing to collect real practice data. Do not invent study duration or guarantee the daily quota fits 30 minutes.

## Start or resume the session

- When the user starts a daily session (for example, "start today's lesson", "help me study English", or "start today's 17 questions"), read before asking anything: `learner_profile.md`, `weak_patterns.md`, `streak.md`, the last rows of `daily_log.md`, the top of `review_schedule.md` (rows due up to today plus a few after), and the current month's `sentences/` and `history/` files. Refresh the streak snapshot using the rules below, so a missed day is reflected before learning starts.
- Do not read older month files in full. Search them by ID only when a review needs a sentence's text or previous answers.
- If today's session is already recorded as completed in `daily_log.md`, report that it is complete rather than regenerating a lesson or recording another completion.
- If the learner profile is unset, use the default work-communication context to prepare the lesson without blocking its creation. Offer to fill in the profile later; record only what the learner states.
- Before creating a new plan, run the report command to obtain `due_count` and `review_candidate_ids`. With over 20 sentences due (including overdue), explain the backlog and ask whether to use 5 new + 12 reviews instead of 7 + 10. This is an initial trial threshold, not a validated learning optimum. Wait for explicit confirmation; declining keeps 7 + 10. Do not alter a plan that already exists or an already-started day.
- Prepare or reuse today's saved lesson using the rules below. **Resume check:** match today's assessed history rows to the plan by sentence ID and attempt type. Report completed counts against the saved targets, then continue with the first unassessed row. Reconcile any missing data updates for an existing attempt before advancing; never assess or append that attempt again just to recover progress.
- Follow the saved order and targets: all planned new sentences first, then the planned reviews. Present exactly one Vietnamese sentence at a time and wait for the English response. Do not reveal a model translation, keywords, or hints that undermine recall.

## Prepare today's lesson

- Use `data/history/lessons/YYYY-MM-DD.md`, where the date is today's local calendar date. Create the directory if missing. Generate all remaining new questions and select all review questions in one preparation step, save the complete plan, and validate it before presenting the first unassessed sentence.
- If the plan already exists, reuse it without replacing its questions, IDs, order, or targets. Do not select new questions between attempts. Leave earlier days' plans unchanged.
- If no plan exists but today's assessed attempts already exist, reconstruct their question rows from the real sentence bank and history first, retaining their IDs and type. Include these completed rows in the targets, then fill only the remaining slots. Do not restart a partially completed day.
- Reserve unique `S-YYYYMMDD-NNN` IDs for planned new sentences, checking both the sentence bank and existing lesson plans for collisions. A reserved ID does not mean the sentence has been studied. Reuse its exact ID and Vietnamese text when it is later assessed.
- Choose all new questions using the new-sentence rules below, checking for near-duplicates both in the bank and within the planned batch. Choose reviews only from real assessed sentences using the review rules below; never from an unassessed draft plan.
- Default to `New target = 7` and review capacity 10. Only with explicit approval of the backlog adjustment before this day has started, use `New target = 5` and capacity 12. Set `Review target` to the smaller of capacity and the distinct due-or-weak review pool at the start of the day, including already assessed reviews when reconstructing a legacy day. Set `Unavailable reviews` to capacity minus that target. Freeze the targets for this session, even if the schedule later changes after answers.
- Add `Review selection: due-and-weak` to new plans. For an approved 5 + 12 plan, also add `Quota adjustment approved: yes`; never claim confirmation without the learner's actual approval. To reconstruct an already-started day without a plan, keep 7 + 10 and the legacy all-earlier-sentences policy rather than retroactively applying the new selection rule; leave the optional selection field absent and retain its real attempts.
- Store the date, targets, and an ordered table with columns `Order | Type | Sentence ID | Vietnamese`. Use `new` or `review` for `Type`. Do not store English translations, structures, learner answers, results, or explanations in the plan. Do not show the full question list in chat; only present the current sentence.
- Before starting, check that orders are sequential, sentence IDs are unique, row counts match the saved targets, new rows precede reviews, and every review ID resolves to an assessed sentence first studied before today. Check that reconstructed completed rows match the existing history. Run the validator on the saved plan; do not start an invalid or incomplete plan.
- Preparation alone must not add rows to the sentence bank, assessed answer history, review schedule, weak patterns, or completed-session log, and must not increase the streak. Only assessed answers trigger learning-data updates.

Plan format (placeholders below describe the schema, not learning records):

```markdown
# Lesson YYYY-MM-DD

- Lesson date: YYYY-MM-DD
- New target: <7 by default, or 5 with explicit approval>
- Review target: <review pool capped at 10, or 12 with explicit approval>
- Unavailable reviews: <capacity minus review target>
- Review selection: due-and-weak

| Order | Type | Sentence ID | Vietnamese |
| --- | --- | --- | --- |
```

## Choose new sentences

- Choose useful, common communication or work sentences that fit the learner profile's topics and level.
- Rotate topics: avoid reusing the topic of the previous new item when alternatives exist, and check the `Topic` column of the current month's `sentences/` file to avoid near-duplicates.
- When there are real earlier sentences with observed errors, use 1-2 of the planned new slots for transfer: test the same structure in a different Vietnamese sentence and context. Prefer recurring patterns (count at least 2). These replace ordinary new slots, not add extra questions. If no real earlier source exists, use ordinary new questions instead.
- Do not reveal the target structure or the old answer before the response. A transfer item is a new sentence with a new ID; succeeding on it is not a successful review of the original sentence and must not change the original schedule. After assessing it, save its real earlier source as a related-sentence link in the bank. Do not invent a link if the intended source cannot be established.
- Raise difficulty gradually when most recent results are "correct and natural"; keep it steady otherwise.
- Append the `sentences/` row only after the sentence has actually been presented and assessed.

## Choose reviews

- Eligible: sentences whose ID date is before today. Never present a current-session new item as a review.
- Review each sentence at most once per daily session. On resume, skip sentence IDs already assessed as reviews today; those attempts count toward the planned review target.
- For new plans, select all due items first: `Next review` on or before the lesson date, oldest date first, then lowest level; recurring weak patterns can break further ties. Do not skip a due sentence merely because it was studied yesterday.
- Fill remaining slots only with earlier sentences at level 0 or 1, or with latest result `incorrect`/`uncertain`, prioritising low levels and recurring weak patterns. Do not review a retained level-2-or-higher correct sentence early just to fill the quota. If the due-or-weak pool is smaller than capacity, save the reduced review target and disclose the shortage. Use the state before today's attempts when reconstructing targets.
- An existing saved lesson keeps its exact review IDs even if the current schedule has changed or the lesson used the older all-earlier-sentences rule.
- Get the Vietnamese text and standard version from the sentence's month file by searching its ID.
- During preparation, copy only the Vietnamese text into the plan. Retrieve the standard version for feedback after the learner answers; do not expose it in the saved question plan.
- Review every planned distinct row, tell the learner the saved `Unavailable reviews` count, and do not manufacture records or repeat sentences to fill the quota.

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
- For an assessed transfer item, append one link row to a separate optional table at the end of its sentence-bank month file: `Sentence ID | Related sentence`. Create that table's header if absent; do not add a column to or rewrite old sentence rows. The child is the new assessed sentence ID and the parent is an actual sentence studied before today. Each child has at most one source link, and the link alone never updates the parent's counts or schedule.
- Every assessed attempt → append one row to `data/history/YYYY-MM.md`: `Attempt | Sentence | Type | Learner answer | Result | Note`. `Type` is `new` or `review`; `Note` is the short error explanation, or `-` when correct. Never edit earlier rows.
- Keep the daily lesson plan unchanged. Its row is complete only when the matching assessed attempt exists in the monthly history; never write simulated answers or placeholder results to mark progress.
- `review_schedule.md` → add a row for a new sentence or update the existing row: level, status, latest result, last studied, next review, and the correct/incorrect/uncertain/review counts. `Reviews` counts review attempts only. Move the row so the table stays sorted by `Next review`, then ID.
- `weak_patterns.md` → for each observed error, increment the matching row (or add one with count 1), update `Last seen`, and add the sentence ID to `Recent sentences`, keeping only the 5 most recent. A pattern with count ≥ 2 is recurring and gets priority.
- `logs/daily_log.md` → append one row only after all planned questions are completed.
- After each answer, save the attempt, new sentence/link if applicable, schedule and weak-pattern updates, then run the validator before advancing. If a write was interrupted, derive schedule counts from actual attempts rather than incrementing again; do not duplicate the immutable attempt.

## Update the streak

- A day qualifies only after every row in the saved daily lesson plan, using its saved new and review targets, has a matching assessed attempt, the related learning-data updates are complete, and its completed-session row has been saved in `logs/daily_log.md`. A shortage of eligible reviews does not prevent completion. Partial sessions, explanations, and follow-up questions do not count.
- Use the learner's local calendar date (the current date in the conversation unless the learner specifies otherwise), not elapsed 24-hour periods or UTC dates.
- Read the `Date` column from the completed-session log, deduplicate dates, and sort them chronologically. Count each day once, even if multiple sessions or repeated summaries occur on that date. Never create log entries to fill gaps.
- With no completed dates, write `Current streak = 0`, `Best streak = 0`, and `Last completed = -`.
- Otherwise, `Last completed` is the latest completed date. `Best streak` is the longest consecutive-day run across all completed dates. `Current streak` is the length of the run ending on `Last completed` when it is today or yesterday; if it is older than yesterday, set `Current streak = 0` without losing the best streak. Completing a session after a gap starts a new current streak at 1.
- Update the single row in `data/streak.md` in place. Rebuild from the log rather than incrementing blindly, so repeating a summary or recovering after an interrupted write cannot count a day twice. If the file is missing, recreate it from the log with the same columns.

## Complete the session

Run `python -B scripts/validate_learning.py --date YYYY-MM-DD --require-complete` first. On success, save the completed-session log row unless already logged, rebuild `data/streak.md`, and rerun the ordinary validator before displaying the summary. If all planned answers were saved before an interruption but the completion log or streak was not, finish these updates on resume without asking extra questions or recording extra attempts.

After all saved lesson rows have been assessed, state the number of new and review items completed against the saved targets, any unavailable reviews, totals for correct, incorrect, and less-natural/uncertain answers, recurring errors, the sentences due next with their dates, and confirm the files updated. Do not end a normal daily session after only a few explained items.

Include the updated streak in the Vietnamese summary: "Streak hien tai: X ngay lien tiep. Ky luc: Y ngay." Display the actual values from `data/streak.md`, not example numbers.

If the workspace is a git repository, commit the data with `git add data logs` and `git commit -m "Session YYYY-MM-DD"`. Never push.
