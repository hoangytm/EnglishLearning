import argparse
from collections import Counter
from datetime import date
import json
import os
from pathlib import Path
import sys
import tempfile

from validate_learning import (
    ATTEMPT_COLUMNS, CATEGORY_COLUMNS, CATEGORY_NAME, LINK_COLUMNS, LOG_COLUMNS, PATTERN_COLUMNS, RESULTS,
    SCHEDULE_COLUMNS, SENTENCE_COLUMNS, STREAK_COLUMNS, id_date, load_data, project_schedule, streak_snapshot,
    validate,
)


SENTENCE_INTRO = (
    '# Sentences {month}\n\nOne immutable row per sentence first studied this month. First-study date is '
    'the date in the ID. The first learner answer and assessment are the `new` row in '
    '`data/history/{month}.md`.\n'
)
HISTORY_INTRO = (
    '# Answer History {month}\n\nAppend-only: one row per independently assessed attempt. Never edit '
    'existing rows. Attempt date is the date in the ID. Result: `correct`, `uncertain`, or `incorrect`.\n'
)


class RecordError(ValueError):
    pass


def cell(value):
    text = ' '.join(str(value or '').replace('|', '/').split())
    return text or '-'


def render(schema, rows):
    lines = ['| ' + ' | '.join(schema) + ' |', '| ' + ' | '.join('---' for _ in schema) + ' |']
    return lines + ['| ' + ' | '.join(row[field] for field in schema) + ' |' for row in rows]


def with_table(text, schema, rows):
    lines = text.splitlines()
    rendered = render(schema, rows)
    for start, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('|') and tuple(part.strip() for part in stripped.strip('|').split('|')) == schema:
            end = start
            while end < len(lines) and lines[end].strip().startswith('|'):
                end += 1
            lines[start:end] = rendered
            break
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ([''] if lines else []) + rendered
    return '\n'.join(lines) + '\n'


def write_atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


class Changes:
    def __init__(self, root):
        self.root = root
        self.texts = {}

    def table(self, relative, schema, rows, intro=''):
        path = self.root / relative
        if relative not in self.texts:
            self.texts[relative] = path.read_text(encoding='utf-8-sig') if path.exists() else intro
        self.texts[relative] = with_table(self.texts[relative], schema, rows)

    def commit(self, check):
        originals = {relative: (self.root / relative).read_bytes() if (self.root / relative).exists() else None
                     for relative in self.texts}
        try:
            for relative, text in self.texts.items():
                write_atomic(self.root / relative, text.encode('utf-8'))
            errors = check()
            if errors:
                raise RecordError('validation failed after writing; changes rolled back: ' + '; '.join(errors))
        except BaseException:
            for relative, original in originals.items():
                if original is None:
                    (self.root / relative).unlink(missing_ok=True)
                else:
                    write_atomic(self.root / relative, original)
            raise


def check_errors(root, today, require_complete=False):
    try:
        return validate(load_data(root), today, require_complete)[0]
    except (OSError, ValueError) as error:
        return [str(error)]


def day_attempts(data, today):
    return [row for row in data['attempts'] if id_date(row['Attempt'], 'A') == today]


def progress(data, today):
    plan = data['plans'].get(today)
    if plan is None:
        return None
    done = {(row['Sentence'], row['Type']) for row in day_attempts(data, today)}
    remaining = [row for row in plan['rows'] if (row['Sentence ID'], row['Type']) not in done]
    return {
        'targets': {'new': int(plan['New target']), 'review': int(plan['Review target']),
                    'unavailable_reviews': int(plan['Unavailable reviews'])},
        'done': {kind: sum(1 for _, done_kind in done if done_kind == kind) for kind in ('new', 'review')},
        'remaining': remaining,
        # The Vietnamese text is read from the plan file to avoid console-encoding issues.
        'next': {'order': remaining[0]['Order'], 'type': remaining[0]['Type'],
                 'sentence_id': remaining[0]['Sentence ID']} if remaining else None,
    }


def session_status(root, today):
    data = load_data(root)
    errors, warnings = validate(data, today)
    state = progress(data, today)
    if state:
        state.pop('remaining')
    return {'ok': not errors, 'date': str(today), 'errors': errors, 'warnings': warnings,
            'completed': any(row['Date'] == str(today) for row in data['logs']),
            'categories': [row['Category'] for row in data['categories']],
            'plan': state}


def refresh_streak(root, today):
    data = load_data(root)
    streak = streak_snapshot([date.fromisoformat(row['Date']) for row in data['logs']], today)
    changed = data['streak'] != [streak]
    if changed:
        changes = Changes(root)
        changes.table('data/streak.md', STREAK_COLUMNS, [streak])
        changes.commit(lambda: [])
    errors = check_errors(root, today)
    return {'ok': not errors, 'changed': changed, 'streak': streak, 'errors': errors}


def record_attempt(root, today, sentence_id, kind, answer, result, note='-', standard=None,
                   structures=None, topic=None, related=None, patterns=()):
    if kind not in ('new', 'review') or result not in RESULTS:
        raise RecordError('type must be new/review and result must be correct/uncertain/incorrect')
    if result == 'correct' and patterns:
        raise RecordError('weak patterns are only recorded for incorrect or uncertain answers')
    if not str(answer or '').strip():
        raise RecordError('a real learner answer is required')
    data = load_data(root)
    known = [row['Category'] for row in data['categories']]
    unknown = [name for name in dict.fromkeys(cell(pattern) for pattern in patterns) if name not in known]
    if unknown:
        raise RecordError(f"unknown pattern category: {', '.join(unknown)}; use one of: {', '.join(known)}")
    errors, _ = validate(data, today)
    if errors:
        raise RecordError('existing records are invalid; resolve before recording: ' + '; '.join(errors))
    if any(row['Date'] == str(today) for row in data['logs']):
        raise RecordError(f'{today} is already completed')
    state = progress(data, today)
    if state is None:
        raise RecordError(f'no saved lesson plan for {today}')
    if state['next'] is None:
        raise RecordError('all planned questions are already assessed')
    expected = state['remaining'][0]
    if (expected['Sentence ID'], expected['Type']) != (sentence_id, kind):
        raise RecordError(f"next planned question is order {expected['Order']}: "
                          f"{expected['Type']} {expected['Sentence ID']}")

    month = today.strftime('%Y-%m')
    sentences = {row['ID']: row for row in data['sentence_rows']}
    changes = Changes(root)
    if kind == 'new':
        if sentence_id in sentences:
            raise RecordError(f'{sentence_id} is already in the sentence bank')
        if not all(str(value or '').strip() for value in (standard, structures, topic)):
            raise RecordError('new sentences require --standard, --structures and --topic')
        sentence = {'ID': sentence_id, 'Vietnamese': expected['Vietnamese'], 'Standard version': cell(standard),
                    'Structures': cell(structures), 'Topic': cell(topic)}
        bank_file = f'data/sentences/{month}.md'
        month_rows = [row for row in data['sentence_rows'] if id_date(row['ID'], 'S').strftime('%Y-%m') == month]
        changes.table(bank_file, SENTENCE_COLUMNS, month_rows + [sentence], SENTENCE_INTRO.format(month=month))
        if related:
            if related not in sentences or id_date(related, 'S') >= today:
                raise RecordError('--related must be an assessed sentence from an earlier day')
            links = [link for link in data['links'] if id_date(link['Sentence ID'], 'S').strftime('%Y-%m') == month]
            changes.table(bank_file, LINK_COLUMNS, links + [{'Sentence ID': sentence_id, 'Related sentence': related}])
        example = sentence['Standard version']
    else:
        if related:
            raise RecordError('--related applies only to new transfer sentences')
        if sentence_id not in sentences:
            raise RecordError(f'{sentence_id} is not in the sentence bank')
        example = sentences[sentence_id]['Standard version']

    numbers = [int(row['Attempt'].rsplit('-', 1)[1]) for row in day_attempts(data, today)]
    attempt = {'Attempt': f"A-{today:%Y%m%d}-{max(numbers, default=0) + 1:03}", 'Sentence': sentence_id,
               'Type': kind, 'Learner answer': cell(answer), 'Result': result, 'Note': cell(note)}
    history = [row for row in data['attempts'] if id_date(row['Attempt'], 'A').strftime('%Y-%m') == month]
    changes.table(f'data/history/{month}.md', ATTEMPT_COLUMNS, history + [attempt], HISTORY_INTRO.format(month=month))

    attempts = [row for row in data['attempts'] if row['Sentence'] == sentence_id] + [attempt]
    schedule_row = dict(project_schedule(attempts), **{'Sentence ID': sentence_id})
    schedule = [row for row in data['schedule'] if row['Sentence ID'] != sentence_id] + [schedule_row]
    schedule.sort(key=lambda row: (row['Next review'], row['Sentence ID']))
    changes.table('data/review_schedule.md', SCHEDULE_COLUMNS, schedule)

    if patterns:
        rows = [dict(row) for row in data['patterns']]
        for name in dict.fromkeys(cell(pattern) for pattern in patterns):
            row = next((row for row in rows if row['Pattern'] == name), None)
            if row is None:
                row = {'Pattern': name, 'Count': '0', 'Last seen': str(today), 'Example': example,
                       'Recent sentences': '-'}
                rows.append(row)
            recent = [] if row['Recent sentences'] == '-' else [item.strip() for item in row['Recent sentences'].split(',')]
            recent = [item for item in recent if item != sentence_id] + [sentence_id]
            row.update({'Count': str(int(row['Count']) + 1), 'Last seen': str(today),
                        'Recent sentences': ', '.join(recent[-5:])})
        changes.table('data/weak_patterns.md', PATTERN_COLUMNS, rows)

    changes.commit(lambda: check_errors(root, today))
    total = len(data['plans'][today]['rows'])
    following = state['remaining'][1] if len(state['remaining']) > 1 else None
    return {'ok': True, 'attempt': attempt['Attempt'], 'schedule': schedule_row,
            'progress': f"{total - len(state['remaining']) + 1}/{total}",
            'next': {'order': following['Order'], 'type': following['Type'], 'sentence_id': following['Sentence ID']}
            if following else None}


def add_category(root, today, name, description):
    if not CATEGORY_NAME.fullmatch(name or ''):
        raise RecordError('category must be lowercase words joined by hyphens, for example word-choice')
    if not str(description or '').strip():
        raise RecordError('a category description is required')
    data = load_data(root)
    if any(row['Category'] == name for row in data['categories']):
        raise RecordError(f'category {name} already exists')
    row = {'Category': name, 'Description': cell(description)}
    changes = Changes(root)
    changes.table('data/pattern_categories.md', CATEGORY_COLUMNS, data['categories'] + [row])
    changes.commit(lambda: check_errors(root, today))
    return {'ok': True, 'category': row}


def complete_session(root, today, notable=None):
    data = load_data(root)
    if any(row['Date'] == str(today) for row in data['logs']):
        refreshed = refresh_streak(root, today)
        return dict(refreshed, already_completed=True)
    errors, _ = validate(data, today, require_complete=True)
    if errors:
        raise RecordError('cannot complete: ' + '; '.join(errors))
    attempts = day_attempts(data, today)
    counts = Counter(row['Result'] for row in attempts)
    if notable is None:
        notable = '; '.join(row['Pattern'] for row in data['patterns'] if row['Last seen'] == str(today))
    upcoming = Counter(row['Next review'] for row in data['schedule'])
    log = {'Date': str(today), 'New': str(sum(row['Type'] == 'new' for row in attempts)),
           'Reviews': str(sum(row['Type'] == 'review' for row in attempts)), 'Correct': str(counts['correct']),
           'Uncertain': str(counts['uncertain']), 'Incorrect': str(counts['incorrect']), 'Notable errors': cell(notable),
           'Next due': '; '.join(f'{day} ({upcoming[day]})' for day in sorted(upcoming)[:2]) or '-'}
    streak = streak_snapshot([date.fromisoformat(row['Date']) for row in data['logs']] + [today], today)
    changes = Changes(root)
    changes.table('logs/daily_log.md', LOG_COLUMNS, data['logs'] + [log])
    changes.table('data/streak.md', STREAK_COLUMNS, [streak])
    changes.commit(lambda: check_errors(root, today))
    return {'ok': True, 'already_completed': False, 'log': log, 'streak': streak}


def main():
    parser = argparse.ArgumentParser(description='Write validated EnglishLearning records after real assessments.')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest='command', required=True)
    for name, text in (('status', 'Read-only progress and next planned question'),
                       ('refresh-streak', 'Rebuild data/streak.md from completed sessions'),
                       ('record', 'Append one assessed attempt and update derived records'),
                       ('add-category', 'Add an error category that no existing one fits'),
                       ('complete', 'Log a fully assessed session and rebuild the streak')):
        command = commands.add_parser(name, help=text)
        command.add_argument('--date', type=date.fromisoformat, required=True, help='Learner local date, YYYY-MM-DD')
        if name == 'record':
            command.add_argument('--sentence', required=True)
            command.add_argument('--type', choices=('new', 'review'), required=True)
            command.add_argument('--answer', required=True, help="The learner's exact answer")
            command.add_argument('--result', choices=RESULTS, required=True)
            command.add_argument('--note', default='-')
            command.add_argument('--standard')
            command.add_argument('--structures')
            command.add_argument('--topic')
            command.add_argument('--related', help='Earlier source sentence of a transfer item')
            command.add_argument('--pattern', action='append', default=[],
                                 help='Error category from data/pattern_categories.md; repeatable')
        if name == 'add-category':
            command.add_argument('--name', required=True, help='Lowercase words joined by hyphens')
            command.add_argument('--description', required=True)
        if name == 'complete':
            command.add_argument('--notable', help='Notable errors; defaults to patterns seen today')
    args = parser.parse_args()
    try:
        if args.command == 'status':
            output = session_status(args.root, args.date)
        elif args.command == 'refresh-streak':
            output = refresh_streak(args.root, args.date)
        elif args.command == 'record':
            output = record_attempt(args.root, args.date, args.sentence, args.type, args.answer, args.result,
                                    args.note, args.standard, args.structures, args.topic, args.related, args.pattern)
        elif args.command == 'add-category':
            output = add_category(args.root, args.date, args.name, args.description)
        else:
            output = complete_session(args.root, args.date, args.notable)
    except (OSError, ValueError) as error:
        output = {'ok': False, 'error': str(error)}
    print(json.dumps(output, ensure_ascii=True, indent=2))
    return 0 if output.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main())
