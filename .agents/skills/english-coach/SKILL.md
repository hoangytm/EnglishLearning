---
name: english-coach
description: "Prepare a saved Vietnamese-to-English lesson of 20 questions (at least 3 new), or 30 with --weekend (at least 5 new), prioritising due reviews; validate records, practise transfer, and report progress without starting practice."
---

# English Coach

Use this skill for daily English-learning sessions, Vietnamese-to-English translation practice, reviews of previously incorrect sentences or learned structures, and checks of progress or recurring errors in the current workspace. Do not use it for ordinary non-practice questions, such as a standalone word-meaning request or a technical explanation. Read `AGENTS.md` before starting and read the Markdown learning records in `data/` as the source of learning state; never invent learning history or review results.

## Portable runtime

- This is the shared workflow for Codex and GitHub Copilot, not a host-specific agent. `start-english` selects learning; `english-progress` selects read-only reporting. The entry-point Skills only select a workflow and forward arguments; they add no rules.
- Locate the workspace root containing `AGENTS.md` and `scripts/validate_learning.py`. Paths in this Skill are relative to that root. Use native tools available in the host, not a hard-coded Copilot or Codex tool API. Writing learning records requires workspace write permission; validation requires permission to execute Python. If the host blocks an operation, explain what permission is missing and stop that operation. Do not bypass sandbox restrictions, request secrets through chat, or claim a blocked operation succeeded.
- Select one available Python 3.9+ launcher and use it consistently for every command in this workflow: `python` or `py -3` on Windows, `python3` or `python` on Linux/macOS/WSL. Check its version first. A launcher that exists but is too old does not qualify; try another available launcher before reporting Python unavailable. The command examples below use `python` as a placeholder for the selected launcher.
- Run from the workspace root when possible. Otherwise, pass the quoted absolute script path and `--root` pointing to the same workspace, for example `<launcher> -B "<workspace>/scripts/validate_learning.py" --root "<workspace>" --date YYYY-MM-DD`. The script's default root is its own workspace, not the terminal's current directory. Quote paths containing spaces and use syntax appropriate to the active shell; do not assume PowerShell, Bash, or a Windows drive path.
- Use the learner's local calendar date for every `--date` flag. A conversation date takes precedence; without one, obtain the local date from the runtime rather than reusing a date from a previous report. On WSL, use the same workspace files as the other host, not a copied data directory.
- Learning requires file writes, while progress reports are read-only. Do not start a learning session in a read-only environment or write data during a report. Explain missing permissions rather than fabricating saved records. Switching hosts does not change the saved plan's targets or reset progress; reread the actual files and avoid concurrent writers.

## Files

Learning records are Markdown tables, one row per record. Dates are encoded in IDs (`S-YYYYMMDD-NNN`, `A-YYYYMMDD-NNN`), so the month file for an assessed sentence or attempt is `YYYY-MM.md`. Daily lesson plans use a separate date-based file.

- `data/learner_profile.md`: level, goals, preferred topics. Only record what the learner states; leave `not set` otherwise.
- `data/review_schedule.md`: one row per sentence, sorted by `Next review` then ID; the single source of truth for current level, status, and next review date.
- `data/weak_patterns.md`: one row per error category that has been observed.
- `data/pattern_categories.md`: the fixed list of error categories; `--pattern` accepts only these names.
- `data/sentences/YYYY-MM.md`: one immutable row per sentence first studied that month.
- `data/history/YYYY-MM.md`: append-only, one row per assessed attempt that month. The `new` attempt row holds the immutable first learner answer.
- `data/history/lessons/YYYY-MM-DD.md`: the immutable daily question plan, prepared before the first sentence; it is not evidence of study or recall and contains no answers or hints.
- `logs/daily_log.md`: one row per completed session.
- `data/streak.md`: one current snapshot of consecutive completed learning days, rebuilt from `logs/daily_log.md`.
- `scripts/validate_learning.py`: read-only data checks and rolling weekly metrics; requires Python 3.9 or newer and no third-party packages.
- `scripts/learning_records.py`: the only writer for attempts, sentence bank, schedule, weak patterns, completion log, and streak. It validates before and after every write and rolls back on failure.

Keep cells on one line and never use `|` inside a cell. Keep `Note` cells short (about 20 words).

## Validate the records

- Run commands from the workspace root, supplying the learner's current local date explicitly instead of the example date: `python -B scripts/validate_learning.py --date YYYY-MM-DD`. The script reads records and returns a nonzero exit code on inconsistency; it never writes learning data or grades English.
- At the start of a learning session, run `python -B scripts/learning_records.py refresh-streak --date YYYY-MM-DD`. Run the validator before preparation and after saving the complete plan. The `record` and `complete` commands validate before and after writing and roll back on failure, so no separate validator run is needed after each answer.
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

## Sync with git before learning

For `start-english` and any daily-session start, do this before reading learning records, so data pulled from the other host is what you read. Skip it for progress reports. Use the native terminal, quote for the active shell (PowerShell needs `'@{u}'`), and never run Git commands that discard work.

1. If this is not a git repository or Git is unavailable, tell the learner once and skip the rest of this section.
2. Run `git status --porcelain` (it includes untracked files). If it prints anything, show the changed files and ask the learner whether to commit them. Wait for the answer.
   - Yes: `git add -A`, then commit with a short message describing the changes (for example `Learning data update YYYY-MM-DD` when only `data/` and `logs/` changed). Report the commit.
   - No: do not pull, because a pull on a dirty tree can fail or mix changes. Tell the learner that local data may be behind GitHub, then continue the session. Never stash, reset, checkout, or discard their changes.
3. If the tree is clean (or was just committed) and `git rev-parse --abbrev-ref '@{u}'` shows an upstream, run `git pull --ff-only` and report the result in one line (already up to date, or how many commits arrived). With no upstream, tell the learner and skip the pull.
   - If the pull fails because of the network or sign-in, report the error and continue the session with local data.
   - If it fails because the branches diverged, stop and ask how to proceed. Do not merge, rebase, force, or reset unless the learner asks.
4. If `git rev-list --count '@{u}..HEAD'` is above 0, mention the number of local commits that are not pushed yet. Do not ask about it here.

## Start or resume the session

- When the user starts a daily session (for example, "start today's lesson", "help me study English", or "start today's 20 questions"), first complete **Sync with git before learning**, then read before asking anything: `learner_profile.md`, `weak_patterns.md`, `pattern_categories.md`, `streak.md`, the last rows of `daily_log.md`, the top of `review_schedule.md` (rows due up to today plus a few after), and the current month's `sentences/` and `history/` files. Run `refresh-streak` first, so a missed day is reflected before learning starts.
- Recognise `start-english --weekend` in either host (including `/start-english --weekend`, `$start-english --weekend`, and `$english-coach start-english --weekend`). In chat, also accept `-- weekend` as `--weekend`. This explicitly selects the 30-question mode for a new plan on any calendar day; never enable it just because today is Saturday or Sunday. Without the flag, use the 20-question mode.
- Do not read older month files in full. Search them by ID only when a review needs a sentence's text or previous answers.
- If today's session is already recorded as completed in `daily_log.md`, report that it is complete rather than regenerating a lesson or recording another completion.
- If the learner profile is unset, use the default work-communication context to prepare the lesson without blocking its creation. Offer to fill in the profile later; record only what the learner states.
- Before creating a new plan, run `python -B scripts/validate_learning.py --date YYYY-MM-DD --report`, adding `--weekend` only when requested, to obtain `review_candidate_ids` and `quota_proposal`. No confirmation is needed for the split. If a plan already exists, reuse its saved mode, counts, and order regardless of the current flag; explain a differing request without rewriting the plan or adding questions. Do not alter an already-started day.
- Prepare or reuse today's saved lesson using the rules below. **Resume check:** run `python -B scripts/learning_records.py status --date YYYY-MM-DD`. It reports completed counts against the saved targets and the next unassessed plan row (order, type, sentence ID); read that row's Vietnamese text from the plan file.
- Follow the saved order and targets: all planned new sentences first, then the planned reviews. Present exactly one Vietnamese sentence at a time and wait for the English response. Do not reveal a model translation, keywords, or hints that undermine recall.

## Prepare today's lesson

- Use `data/history/lessons/YYYY-MM-DD.md`, where the date is today's local calendar date. Create the directory if missing. Generate all remaining new questions and select all review questions in one preparation step, save the complete plan, and validate it before presenting the first unassessed sentence.
- If the plan already exists, reuse it without replacing its questions, IDs, order, or targets. Do not select new questions between attempts. Leave earlier days' plans unchanged.
- If no plan exists but today's assessed attempts already exist, reconstruct their question rows from the real sentence bank and history first, retaining their IDs and type. Include these completed rows in the targets, then fill only the remaining slots. Do not restart a partially completed day.
- Reserve unique `S-YYYYMMDD-NNN` IDs for planned new sentences, checking both the sentence bank and existing lesson plans for collisions. A reserved ID does not mean the sentence has been studied. Reuse its exact ID and Vietnamese text when it is later assessed.
- Choose all new questions using the new-sentence rules below, checking for near-duplicates both in the bank and within the planned batch. The validator rejects an exact repeat of any earlier or planned Vietnamese sentence (ignoring case, punctuation, and spacing); near-duplicates remain your judgment, so search older month files by key words as well. Choose reviews only from real assessed sentences using the review rules below; never from an unassessed draft plan.
- Every new default plan has 20 questions: reserve 3 new slots and fill up to 17 review slots from distinct sentences due at the start of the day. `Review target` = min(17, due pool size); `New target` = 20 minus `Review target`; `Unavailable reviews` = 17 minus `Review target`. With enough due sentences, use exactly 3 new and 17 reviews. If reviews are insufficient, their unused slots become new sentences.
- For an explicitly requested `--weekend` plan, use 30 questions: `Review target` = min(25, due pool size); `New target` = 30 minus `Review target`; `Unavailable reviews` = 25 minus `Review target`. This guarantees at least 5 new (exactly 5 when 25 or more reviews are due). Freeze either mode's targets for this session, even if the schedule later changes after answers.
- Add `Review selection: due-only` and `Quota policy: standard-20` (default) or `Quota policy: weekend-30` (with the flag) to new plans; use the report's exact split. To reconstruct an already-started day without a plan, keep 7 + 10 and the legacy all-earlier-sentences policy rather than retroactively applying the new rules; leave both optional fields absent and retain its real attempts. Older saved plans (7 + 10, an approved 5 + 12, or `flexible-17` with `due-and-weak`) stay valid and unchanged.
- Store the date, targets, and an ordered table with columns `Order | Type | Sentence ID | Vietnamese`. Use `new` or `review` for `Type`. Do not store English translations, structures, learner answers, results, or explanations in the plan. Do not show the full question list in chat; only present the current sentence.
- Run the validator on the saved plan; do not start an invalid or incomplete plan. It checks order, unique IDs, row counts, new-before-review order, review eligibility, and that reconstructed rows match the existing history.
- Preparation alone must not add learning records or increase the streak. Only assessed answers trigger learning-data updates.

Plan format (placeholders below describe the schema, not learning records):

```markdown
# Lesson YYYY-MM-DD

- Lesson date: YYYY-MM-DD
- New target: <total minus review target; at least 3, or 5 with --weekend>
- Review target: <due pool capped at 17, or 25 with --weekend>
- Unavailable reviews: <review capacity minus review target>
- Review selection: due-only
- Quota policy: <standard-20 or weekend-30>

| Order | Type | Sentence ID | Vietnamese |
| --- | --- | --- | --- |
```

## Choose new sentences

- Base every new question on `data/learner_profile.md`; its level, goals, and preferred topics are required inputs, not decoration. Profile changes affect only plans created afterwards.
- **Topics:** pick each new question from the profile's topic list. Spread a day's new questions across different topics, include both work and daily-life topics when the list has both, and favour the topics least used in recent sentences (count the `Topic` column over the last 2 weeks of `sentences/` files). Older labels such as `work – scheduling` count toward the closest profile topic. Within a topic, vary the situation instead of repeating a scenario. If the profile has no topics, use everyday work communication.
- **Level:** write for the profile level. For B1-B2, use roughly 10-22 words, natural spoken or written Vietnamese that a real person would say (no word-for-word translationese), and common vocabulary. Include a mix of structures such as past/present perfect, conditionals, modals, passive, relative clauses, reported speech, phrasal verbs, and linking words. Avoid very basic one-clause sentences, rare idioms, niche jargon, and content needing cultural explanation. If the level is unset, assume B1-B2.
- **Goals:** for a goal of confident, grammatically correct communication, give each question one clear target structure (record it in `--structures`) and rotate grammar areas across days: tense and aspect, conditionals, modals, passive voice, prepositions, articles and countability, word order, relative clauses, reported speech, phrasal verbs and collocations. Weight areas by `weak_patterns.md` and recent errors. Make the situation and tone fit the topic (neutral-professional for work, relaxed for daily life).
- **Clear source:** Vietnamese often leaves number, tense, and articles implicit. Add context (a time word, a quantity, who or what is meant) so one natural English version is clearly intended, rather than relying on the assessment rule that accepts reasonable readings.
- Rotate topics: avoid reusing the topic of the previous new item when alternatives exist, and check the `Topic` column of the current month's `sentences/` file to avoid near-duplicates.
- When there are real earlier sentences with observed errors, use 1-2 of the planned new slots for transfer: test the same structure in a different Vietnamese sentence and context. Prefer recurring patterns (count at least 2). These replace ordinary new slots, not add extra questions. If no real earlier source exists, use ordinary new questions instead.
- Do not reveal the target structure or the old answer before the response. A transfer item is a new sentence with a new ID; succeeding on it is not a successful review of the original sentence and must not change the original schedule. After assessing it, save its real earlier source as a related-sentence link in the bank. Do not invent a link if the intended source cannot be established.
- Raise difficulty gradually when most recent results are "correct and natural"; keep it steady otherwise. Within the profile level, use the lower end (B1 structures, shorter sentences) after sessions with mostly incorrect new answers, and move toward B2 (longer, multi-clause sentences) when new answers are mostly correct. Do not drop below the profile level or leave the profile topics because of errors.
- Append the `sentences/` row only after the sentence has actually been presented and assessed.

## Choose reviews

- Eligible: sentences whose ID date is before today. Never present a current-session new item as a review.
- Review each sentence at most once per daily session. On resume, skip sentence IDs already assessed as reviews today; those attempts count toward the planned review target.
- For new plans, select all due items first: `Next review` on or before the lesson date, oldest date first, then lowest level; recurring weak patterns can break further ties. Do not skip a due sentence merely because it was studied yesterday.
- For new plans, select only sentences whose `Next review` is on or before the lesson date. Do not fill review slots with not-yet-due sentences, even if their level is 0 or 1 or their latest result is `incorrect`/`uncertain`. If fewer than 17 (default) or 25 (`--weekend`) are due, save the reduced review target and turn the shortage into new sentences. Use the state before today's attempts when reconstructing targets. Resume older saved plans under their original selection policy.
- Get the Vietnamese text and standard version from the sentence's month file by searching its ID. Copy only the Vietnamese text into the plan; retrieve the standard version for feedback after the learner answers.
- Review every planned distinct row, tell the learner how many review slots became new sentences (`Unavailable reviews`), and do not manufacture records or repeat sentences to fill the quota.

## Assess the response

After every new or review answer, explain in Vietnamese like a teacher explaining to a student, with English sentences and phrases as examples. Be thorough about what went wrong: the learner wants to understand the rule and the word meaning, not only see a corrected answer. Use this order:

1. Quote the learner's exact answer and give a clear label: "incorrect", "correct but less natural/uncertain", or "correct and natural".
2. Give a natural version a native speaker would commonly use in the likely context. State the context or register when it matters (for example, a work email versus casual conversation). Do not imply that there is only one valid native-speaker version.
3. **Grammar and structure:** for each grammar or structure error, quote the problematic phrase, show the replacement, name the rule in plain terms, explain why it applies here and what the learner's version would mean or sound like instead, and add a common pattern to apply next time (for example, `help + object + verb`). Use roughly 3-5 sentences per main issue.
4. **Word choice:** for each vocabulary, collocation, preposition, or register issue, say what the learner's word means, why it does not fit this context, and how the better word or phrase differs in meaning, tone, or usage. Compare similar words when useful.
5. Explain why the suggested native-speaker phrasing fits the context. Clearly separate genuine errors from valid but less-natural or differently formal alternatives. If the learner's answer is already natural, say so and explain what works instead of inventing corrections.
6. Give 2-3 short additional examples that reuse the corrected structure or word in different situations, each with a one-line explanation of the contrast. Finish with 1-2 takeaways to remember.

Keep the detailed explanation in chat; retain only the short `Note` in learning history. Persist the assessment immediately according to the data-update rules below.

## Pause before the next sentence

- Do not include the next Vietnamese sentence in the same message as an assessment. When questions remain, end the message with exactly this line and nothing after it: `Gõ 1 để sang câu tiếp theo.` Never ask the learner to type "tiếp", "next", or any other word; the learner continues by typing only `1`. Then wait for the learner's response.
- If the learner asks a follow-up question, clarify the same answer, end with the same line, and wait again. Treat `1` (also "tiep", "tiếp", "next", or "OK") as the learner being ready and present the next sentence immediately, without asking for further confirmation. This pause does not abandon the planned session.
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

Apply after every independently produced attempt (new or review); the script computes the level and next review date from `--result`:

- incorrect → Level 0.
- correct but less natural/uncertain → Level 1.
- correct and natural → Level = max(current + 1, 2), capped at 5.

Next review = today + the level's interval. Seeing the answer never counts as recall; do not raise a level or a correct count for it.

## Update learning data

After each assessment, save it immediately with one command. Do not wait for the end of the session, and do not hand-edit the history, sentence bank, schedule, weak patterns, log, or streak files:

```text
python -B scripts/learning_records.py record --date YYYY-MM-DD --sentence <ID> --type new|review --answer <learner answer> --result correct|uncertain|incorrect --note <short note> [--standard <natural English> --structures <structures> --topic <topic>] [--related <earlier ID>] [--pattern <pattern>]...
```

- `--result`: `correct` (correct and natural), `uncertain` (correct but less natural/uncertain), `incorrect`.
- `--answer`: the learner's exact answer. `--note`: the short error explanation (about 20 words), or `-` when correct.
- New sentences also require `--standard`, `--structures`, and `--topic`; the Vietnamese text is taken from the plan. Set `--topic` to the profile topic's title (for example `Travel and transport`), optionally followed by ` – ` and a short situation, so topic counts stay consistent.
- `--related`: only for an assessed transfer item; the real earlier source sentence it tests. The link never changes the source sentence's counts or schedule.
- `--pattern`: once per observed error, for incorrect or uncertain answers only. Use exactly one category name from `data/pattern_categories.md` (also listed in the `status` output); the script rejects any other text. Put the specific detail of the mistake in `--note`. If no category fits and the error is clearly a distinct kind, run `python -B scripts/learning_records.py add-category --date YYYY-MM-DD --name <lowercase-words-with-hyphens> --description <one sentence>` first and tell the learner; otherwise pick the closest existing category.
- The script accepts only the next unassessed plan row, updates every related record, and validates. Read its JSON output. If `ok` is false, nothing was written: fix the cause and do not present the next question until the answer is saved.
- Quote every value for the active shell. In PowerShell use single quotes and double any apostrophe (`'I''ll send it'`). In Bash use single quotes and write an apostrophe as `'\''`. Single quotes keep backticks and `$` literal in both.

## Update the streak

- A day qualifies only after every row in the saved daily lesson plan has a matching assessed attempt and its completed-session row has been saved in `logs/daily_log.md`. A shortage of eligible reviews does not prevent completion. Partial sessions, explanations, and follow-up questions do not count.
- Use the learner's local calendar date (the current date in the conversation unless the learner specifies otherwise), not elapsed 24-hour periods or UTC dates.
- `refresh-streak` and `complete` rebuild `data/streak.md` from the log. Never edit the streak file by hand or create log entries to fill gaps.

## Complete the session

Run `python -B scripts/learning_records.py complete --date YYYY-MM-DD` (optionally `--notable <text>`; the default lists weak patterns seen today). It refuses unless every planned row has a real assessed attempt, appends the log row once, rebuilds the streak, and validates. Rerunning it after an interruption is safe and never logs a day twice.

After all saved lesson rows have been assessed, state the number of new and review items completed against the saved targets, any unavailable reviews, totals for correct, incorrect, and less-natural/uncertain answers, recurring errors, the sentences due next with their dates, and confirm the files updated. Do not end a normal daily session after only a few explained items.

Include the updated streak in the Vietnamese summary: "Streak hien tai: X ngay lien tiep. Ky luc: Y ngay." Display the actual values from the `complete` output, not example numbers.

## Commit and push

After the completion summary, if this is a git repository:

1. Commit the session without asking, because the learner has approved it in advance: `git add -- data logs`, then `git commit -m "Session YYYY-MM-DD"`. Stage only `data/` and `logs/`; if other files are changed, leave them and say so. If there is nothing to commit (for example, an interrupted run already committed), skip the commit. Report the commit. If the commit fails, report the error; do not use `--no-verify` or change git config.
2. If the branch now has unpushed commits (`git rev-list --count '@{u}..HEAD'` above 0), end the message by asking whether to push to GitHub, then stop and wait. Run `git push` only after the learner clearly says yes. With no upstream, say so and ask before running `git push -u origin <current branch>`.
3. If the learner declines or does not answer, do not push; the next `start-english` will mention the unpushed commits. If a push is rejected or fails, report it and suggest `git pull --ff-only`; never force-push.
4. If there is nothing to push, say that everything is already on GitHub.

Never push without the learner's explicit confirmation in the current conversation.
