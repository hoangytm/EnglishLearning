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

## Shared entry points

- Both Codex and GitHub Copilot use this root `AGENTS.md` and the same `.agents/skills/english-coach/SKILL.md`. For a learning or progress request, read that Skill file in full even if the host has not automatically discovered or activated it.
- `start-english` means start or resume the learning workflow. `english-progress` means the read-only progress workflow, not translation practice. Recognise these plain-text requests in either host; merely discussing or editing these commands does not start a session.
- Copilot in VS Code provides `/start-english` and `/english-progress` through `.github/prompts/`. Codex uses `$start-english` or `$english-progress` (thin Skills in `.agents/skills/` that delegate to `english-coach`); `$english-coach start-english` and `$english-coach english-progress` also work. Do not assume Copilot prompt files register Codex slash commands.
- Use the current host's native file-reading, editing, and terminal tools. Resolve all workspace-relative paths from the folder containing this file, not from the Skill folder or an unrelated current directory. Follow the Skill's portable-runtime rules.
- Only one agent may write learning data at a time. When changing hosts, reread the saved plan and actual assessed history before continuing; do not generate a parallel lesson or infer unsaved answers from another host's chat.

## Non-negotiable rules

- One Vietnamese sentence at a time; no answer, keyword, or hint before the learner responds.
- Never invent learning history, review results, errors, or learner-profile data. Record only what was observed or stated.
- Never delete or overwrite history: monthly attempt files in `data/history/` are append-only; daily question plans in `data/history/lessons/` and existing rows in `data/sentences/` are immutable. Only `review_schedule.md` rows, `weak_patterns.md` rows, `learner_profile.md` fields, and the `streak.md` snapshot are updated in place.
- A generated lesson plan is not learning history: save questions without answers or hints, and record study results only after a real learner response has been assessed.
- Run the Skill's read-only validator at its required checkpoints. Report failures honestly; never modify immutable history or invent results to make validation pass.
- Seeing an answer does not count as knowing it.
- Use UTF-8 Markdown and keep every existing ID unique and unchanged.
