# EnglishLearning

Personal English-learning workspace based on Active Recall and Spaced Repetition, focused on Vietnamese-to-English translation.

## Start learning

Type `/start-english` in Copilot Chat, or ask: “Start an English learning session.” The default is seven new Vietnamese sentences and up to ten distinct due-or-weak reviews, one at a time. Due sentences come first; retained sentences are not reviewed early just to fill the quota. With over 20 sentences due, the assistant asks before adjusting to five new and up to twelve reviews. Existing saved lessons keep their original targets. No model answer is shown before you respond. An unfinished session is resumed automatically on the same day.

Before the first sentence, the assistant prepares and saves the complete question plan in `data/history/lessons/YYYY-MM-DD.md`. The plan contains no answers or hints and is reused on resume; assessed answer history determines progress. Preparation does not count as studying. This batches question preparation up front, but feedback and saving results still take place after each answer.

After each sentence, you receive a natural translation, a detailed comparison, a distinction between errors and merely less-natural wording, and examples where useful. The result is saved for future sessions.

When earlier errors exist, 1-2 new slots test a previously learned structure in a fresh context. These are new attempts, not reviews of the original sentence. Their source links are saved only after assessment in an optional second table in the sentence bank; old sentence rows are not rewritten.

## Copilot and Codex

Both hosts use root `AGENTS.md` and `.agents/skills/english-coach/SKILL.md`; no duplicate Skill or separate learning database is needed.

| Action | Copilot in VS Code | Codex CLI or IDE |
| --- | --- | --- |
| Start or resume | `/start-english` | `$start-english` |
| Weekly progress | `/english-progress` | `$english-progress` |

Plain-text `start-english` and `english-progress` requests work through the shared instructions as well. If automatic Skill discovery is disabled or unavailable, explicitly ask the agent to read `AGENTS.md` and `.agents/skills/english-coach/SKILL.md` and follow the desired workflow. Mentioning commands in a project-maintenance request does not start practice.

Open the same workspace in both hosts. Copilot learning needs Agent mode with file-editing and terminal tools; Codex learning needs workspace write access and permission to execute Python. Reports need file-reading and Python execution but do not write learning data. Respect each host's approval and sandbox settings; missing permissions must be reported rather than bypassed. Do not run two learning writers concurrently. Switching hosts resumes from the shared saved lesson and assessed history, not another host's unsaved conversation.

On Windows use an available Python 3.9+ launcher (`python` or `py -3`); on Linux/macOS/WSL use `python3` or `python`. Check the version and substitute that launcher in all example commands. Quote paths with spaces and use the same underlying workspace on WSL. The validator resolves its default data root from its script location; from another directory use the absolute script path, optionally with `--root` pointing to the same workspace.

## Checks and progress

Python 3.9+ is required for automated checks; there are no third-party dependencies. From the workspace root:

```powershell
python -B scripts/validate_learning.py --date 2026-10-11
python -B scripts/validate_learning.py --date 2026-10-11 --require-complete
python -B scripts/validate_learning.py --date 2026-10-11 --report
python -B scripts/learning_records.py status --date 2026-10-11
python -B -m unittest discover -s scripts -p "test_*.py" -v
```

The agent writes learning data only through `scripts/learning_records.py` (`refresh-streak`, `record`, `add-category`, `complete`). It accepts only the next planned question, appends the attempt, rebuilds the schedule row from actual attempts, updates weak patterns, logs completion once, and rebuilds the streak. Every write is validated before and after; on failure all touched files are restored.

Replace the example date with the learner's local date. The validator checks IDs, actual attempts, projected schedule counts/levels, plans, links, completion totals, and streak without writing data. It runs before/after preparation, after each saved assessment, and before/after completion. It checks structure and consistency, not whether an English assessment is linguistically correct. Test fixtures are isolated from learning history.

Use `/english-progress` in Copilot or `$english-progress` in Codex to report weekly progress. Reports compare the last 7 days with the preceding 7 days, separate new and review results with denominators, show backlog, and explain evidence limits. Reports are read-only and do not create files. No review attempts means unknown recall, not a 0% recall score.

The two thin entry-point Skills (`.agents/skills/start-english`, `.agents/skills/english-progress`) only select the shared workflow; they do not duplicate its rules. Both hosts read them from `.agents/skills/`, so they provide `/...` commands in Copilot and `$...` commands in Codex; there are no separate Copilot prompt files. `$english-coach` still works directly. Automated checks are explicit workflow commands, not host-specific enforced hooks. Passing the script tests establishes local data/CLI compatibility, not proof that either AI host will obey every instruction in a complete session.

## Data structure

- `data/learner_profile.md`: your level, goals, and preferred topics.
- `data/review_schedule.md`: one table row per sentence with its current level (0–5) and next review date; due items stay at the top.
- `data/weak_patterns.md`: one table row per observed error category, with a count.
- `data/pattern_categories.md`: the fixed list of error categories that `--pattern` accepts.
- `data/sentences/YYYY-MM.md`: one row per sentence (Vietnamese, standard version, structures, topic).
- `data/history/YYYY-MM.md`: append-only, one row per assessed answer (including your first answer).
- `data/history/lessons/YYYY-MM-DD.md`: a saved daily question plan, with no answers or assessment results.
- `logs/daily_log.md`: one row per completed learning session.
- `data/streak.md`: current and best streaks of consecutive completed learning days, shown at the end of each session. Each day counts once; incomplete sessions do not count.
- `.agents/skills/english-coach/SKILL.md`: the assistant workflow (single source of truth for the rules).
- `.agents/skills/start-english/` and `.agents/skills/english-progress/`: entry points for both hosts (`/start-english`, `/english-progress` in Copilot; `$start-english`, `$english-progress` in Codex) that delegate to `english-coach`.

Learning data is stored only in the Markdown records above and versioned with git; each completed session is committed locally.

## Note

Every sentence has a unique `sentence_id`. Seeing an answer is not the same as knowing it; review intervals (1, 3, 7, 14, 30, 60 days) expand only after successful independent recall.
