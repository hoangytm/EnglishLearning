import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import json
from pathlib import Path
import re
import sys


SENTENCE_COLUMNS = ('ID', 'Vietnamese', 'Standard version', 'Structures', 'Topic')
LINK_COLUMNS = ('Sentence ID', 'Related sentence')
ATTEMPT_COLUMNS = ('Attempt', 'Sentence', 'Type', 'Learner answer', 'Result', 'Note')
PLAN_COLUMNS = ('Order', 'Type', 'Sentence ID', 'Vietnamese')
SCHEDULE_COLUMNS = (
    'Sentence ID', 'Level', 'Status', 'Latest result', 'Last studied', 'Next review',
    'Correct', 'Incorrect', 'Uncertain', 'Reviews',
)
LOG_COLUMNS = ('Date', 'New', 'Reviews', 'Correct', 'Uncertain', 'Incorrect', 'Notable errors', 'Next due')
STREAK_COLUMNS = ('Current streak', 'Best streak', 'Last completed')
PATTERN_COLUMNS = ('Pattern', 'Count', 'Last seen', 'Example', 'Recent sentences')
CATEGORY_COLUMNS = ('Category', 'Description')
CATEGORY_NAME = re.compile(r'[a-z]+(-[a-z]+)*')
INTERVALS = (1, 3, 7, 14, 30, 60)
RESULTS = ('correct', 'incorrect', 'uncertain')


class DataError(ValueError):
    pass


def read_tables(path, schemas):
    text = path.read_text(encoding='utf-8-sig')
    tables = {schema: [] for schema in schemas}
    seen = set()
    header = None
    needs_separator = False
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith('|'):
            if needs_separator:
                raise DataError(f'{path}:{number}: missing table separator')
            header = None
            continue
        if not line.strip().endswith('|'):
            raise DataError(f'{path}:{number}: table row must end with |')
        cells = tuple(cell.strip() for cell in line.strip()[1:-1].split('|'))
        if header is None:
            if cells not in tables or cells in seen:
                raise DataError(f'{path}:{number}: unexpected or repeated table header')
            header = cells
            seen.add(header)
            needs_separator = True
        elif needs_separator:
            if len(cells) != len(header) or not all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells):
                raise DataError(f'{path}:{number}: invalid table separator')
            needs_separator = False
        else:
            if len(cells) != len(header) or not all(cells):
                raise DataError(f'{path}:{number}: invalid cell count or empty cell; use - for missing values')
            tables[header].append(dict(zip(header, cells)))
    if schemas[0] not in seen or needs_separator:
        raise DataError(f'{path}: missing complete primary table')
    return text, tables


def read_rows(path, schema):
    return read_tables(path, (schema,))[1][schema]


def integer(value):
    if not re.fullmatch(r'\d+', value):
        raise DataError(f'expected a nonnegative integer, got {value!r}')
    return int(value)


def id_date(identifier, prefix):
    match = re.fullmatch(rf'{prefix}-(\d{{8}})-(\d{{3,}})', identifier)
    if not match or int(match[2]) == 0:
        raise DataError(f'invalid ID: {identifier}')
    return date.fromisoformat(f'{match[1][:4]}-{match[1][4:6]}-{match[1][6:]}')


def unique(rows, column, label, errors):
    indexed = {}
    for row in rows:
        identifier = row[column]
        if identifier in indexed:
            errors.append(f'{label}: duplicate {identifier}')
        indexed[identifier] = row
    return indexed


def project_schedule(attempts):
    level = -1
    counts = Counter()
    for attempt in sorted(attempts, key=lambda row: row['Attempt']):
        result = attempt['Result']
        if result not in RESULTS:
            raise DataError(f"invalid result: {result}")
        level = 0 if result == 'incorrect' else 1 if result == 'uncertain' else min(5, max(level + 1, 2))
        counts[result] += 1
        counts['reviews'] += attempt['Type'] == 'review'
    last = id_date(attempt['Attempt'], 'A')
    return {
        'Level': str(level),
        'Status': 'learning' if level < 2 else 'reviewing' if level < 4 else 'mastered',
        'Latest result': attempt['Result'],
        'Last studied': last.isoformat(),
        'Next review': (last + timedelta(days=INTERVALS[level])).isoformat(),
        'Correct': str(counts['correct']), 'Incorrect': str(counts['incorrect']),
        'Uncertain': str(counts['uncertain']), 'Reviews': str(counts['reviews']),
    }


def streak_snapshot(completed_dates, today):
    ordered = sorted(set(completed_dates))
    run = best = 0
    previous = None
    for completed in ordered:
        run = run + 1 if previous and completed == previous + timedelta(days=1) else 1
        best = max(best, run)
        previous = completed
    current = run if previous in (today, today - timedelta(days=1)) else 0
    return {'Current streak': str(current), 'Best streak': str(best),
            'Last completed': previous.isoformat() if previous else '-'}


def load_data(root):
    sentence_rows = []
    links = []
    for path in sorted((root / 'data/sentences').glob('????-??.md')):
        _, tables = read_tables(path, (SENTENCE_COLUMNS, LINK_COLUMNS))
        for row in tables[SENTENCE_COLUMNS]:
            if id_date(row['ID'], 'S').strftime('%Y-%m') != path.stem:
                raise DataError(f'{path}: sentence ID belongs to another month')
        sentence_rows.extend(tables[SENTENCE_COLUMNS])
        links.extend(tables[LINK_COLUMNS])
    attempts = []
    for path in sorted((root / 'data/history').glob('????-??.md')):
        rows = read_rows(path, ATTEMPT_COLUMNS)
        if any(id_date(row['Attempt'], 'A').strftime('%Y-%m') != path.stem for row in rows):
            raise DataError(f'{path}: attempt ID belongs to another month')
        attempts.extend(rows)
    plans = {}
    for path in sorted((root / 'data/history/lessons').glob('????-??-??.md')):
        text, tables = read_tables(path, (PLAN_COLUMNS,))
        fields = {}
        for name in ('Lesson date', 'New target', 'Review target', 'Unavailable reviews'):
            values = re.findall(rf'^- {re.escape(name)}: (.+)$', text, re.MULTILINE)
            if len(values) != 1:
                raise DataError(f'{path}: expected one {name} field')
            fields[name] = values[0].strip()
        for name, allowed in (('Review selection', 'due-and-weak'), ('Quota adjustment approved', 'yes')):
            values = re.findall(rf'^- {re.escape(name)}: (.+)$', text, re.MULTILINE)
            if values and (len(values) != 1 or values[0].strip() != allowed):
                raise DataError(f'{path}: invalid {name} field')
            if values:
                fields[name] = allowed
        if fields['Lesson date'] != path.stem:
            raise DataError(f'{path}: lesson date differs from filename')
        allowed_lines = {f'# Lesson {path.stem}', *(f'- {name}: {value}' for name, value in fields.items())}
        if any(line.strip() and not line.strip().startswith('|') and line.strip() not in allowed_lines
               for line in text.splitlines()):
            raise DataError(f'{path}: plan contains text outside the question schema')
        fields['rows'] = tables[PLAN_COLUMNS]
        plans[date.fromisoformat(path.stem)] = fields
    return {
        'sentence_rows': sentence_rows, 'links': links, 'attempts': attempts, 'plans': plans,
        'schedule': read_rows(root / 'data/review_schedule.md', SCHEDULE_COLUMNS),
        'logs': read_rows(root / 'logs/daily_log.md', LOG_COLUMNS),
        'streak': read_rows(root / 'data/streak.md', STREAK_COLUMNS),
        'patterns': read_rows(root / 'data/weak_patterns.md', PATTERN_COLUMNS),
        'categories': read_rows(root / 'data/pattern_categories.md', CATEGORY_COLUMNS),
    }


def review_candidates(schedule, today):
    earlier = [row for row in schedule if id_date(row['Sentence ID'], 'S') < today]
    due = sorted((row for row in earlier if date.fromisoformat(row['Next review']) <= today),
                 key=lambda row: (row['Next review'], integer(row['Level']), row['Sentence ID']))
    weak = sorted((row for row in earlier if date.fromisoformat(row['Next review']) > today
                   and (integer(row['Level']) <= 1 or row['Latest result'] in ('incorrect', 'uncertain'))),
                  key=lambda row: (integer(row['Level']), row['Next review'], row['Sentence ID']))
    return due, due + weak


def validate(data, today, require_complete=False, allow_stale_streak=False):
    errors = []
    warnings = []
    sentences = unique(data['sentence_rows'], 'ID', 'sentence bank', errors)
    unique(data['attempts'], 'Attempt', 'history', errors)
    schedules = unique(data['schedule'], 'Sentence ID', 'schedule', errors)
    logs = unique(data['logs'], 'Date', 'completed log', errors)
    grouped = defaultdict(list)
    by_day = defaultdict(list)
    daily_keys = set()
    for attempt in data['attempts']:
        studied = id_date(attempt['Attempt'], 'A')
        identifier = attempt['Sentence']
        first_date = id_date(identifier, 'S')
        if attempt['Type'] not in ('new', 'review') or attempt['Result'] not in RESULTS:
            errors.append(f"{attempt['Attempt']}: invalid type or result")
            continue
        if identifier not in sentences:
            errors.append(f"{attempt['Attempt']}: unknown sentence {identifier}")
        if studied > today or first_date > studied:
            errors.append(f"{attempt['Attempt']}: future or inconsistent study date")
        if (attempt['Type'] == 'new' and first_date != studied) or (attempt['Type'] == 'review' and first_date >= studied):
            errors.append(f"{attempt['Attempt']}: invalid new/review study date")
        key = (studied, identifier)
        if key in daily_keys:
            errors.append(f"{attempt['Attempt']}: sentence assessed twice on the same day")
        daily_keys.add(key)
        grouped[identifier].append(attempt)
        by_day[studied].append(attempt)
    for identifier in sentences:
        attempts = grouped[identifier]
        ordered = sorted(attempts, key=lambda row: row['Attempt'])
        if sum(row['Type'] == 'new' for row in attempts) != 1 or not ordered or ordered[0]['Type'] != 'new':
            errors.append(f'{identifier}: must have exactly one first new attempt')
        if not attempts:
            continue
        expected = project_schedule(attempts)
        if identifier not in schedules:
            errors.append(f'{identifier}: missing schedule row')
        else:
            for field, value in expected.items():
                if schedules[identifier][field] != value:
                    errors.append(f'{identifier}: {field} expected {value}, got {schedules[identifier][field]}')
    for identifier in schedules.keys() - sentences.keys():
        errors.append(f'{identifier}: schedule has no assessed sentence')
    schedule_order = [(date.fromisoformat(row['Next review']), row['Sentence ID']) for row in data['schedule']]
    if schedule_order != sorted(schedule_order):
        errors.append('schedule: rows must be sorted by Next review then ID')
    link_ids = set()
    for link in data['links']:
        child, parent = link['Sentence ID'], link['Related sentence']
        if child in link_ids or child == parent or child not in sentences or parent not in sentences:
            errors.append(f'{child}: duplicate or invalid related-sentence link')
        elif id_date(parent, 'S') >= id_date(child, 'S'):
            errors.append(f'{child}: related sentence must come from an earlier day')
        link_ids.add(child)
    categories = unique(data['categories'], 'Category', 'pattern categories', errors)
    for name in categories:
        if not CATEGORY_NAME.fullmatch(name):
            errors.append(f'pattern category {name}: use lowercase words joined by hyphens')
    unique(data['patterns'], 'Pattern', 'weak patterns', errors)
    for pattern in data['patterns']:
        if pattern['Pattern'] not in categories:
            errors.append(f"weak pattern {pattern['Pattern']}: not in data/pattern_categories.md")
        recent = [] if pattern['Recent sentences'] == '-' else [item.strip() for item in pattern['Recent sentences'].split(',')]
        last_seen = date.fromisoformat(pattern['Last seen'])
        if integer(pattern['Count']) < max(1, len(recent)) or len(recent) > 5 or len(set(recent)) != len(recent):
            errors.append(f"weak pattern {pattern['Pattern']}: invalid count or recent IDs")
        if last_seen > today or any(identifier not in sentences for identifier in recent):
            errors.append(f"weak pattern {pattern['Pattern']}: invalid date or unknown sentence")
        elif recent and not any(id_date(attempt['Attempt'], 'A') == last_seen and attempt['Result'] != 'correct'
                                for identifier in recent for attempt in grouped[identifier]):
            errors.append(f"weak pattern {pattern['Pattern']}: last seen has no non-correct attempt")
    reserved = {}
    for lesson_date, plan in data['plans'].items():
        rows = plan['rows']
        indexed = unique(rows, 'Sentence ID', f'lesson {lesson_date}', errors)
        new_target, review_target = integer(plan['New target']), integer(plan['Review target'])
        missing = integer(plan['Unavailable reviews'])
        eligible = {identifier for identifier in sentences if id_date(identifier, 'S') < lesson_date}
        prior_schedule = [dict(project_schedule(prior), **{'Sentence ID': identifier})
                          for identifier, attempts in grouped.items()
                          if (prior := [row for row in attempts if id_date(row['Attempt'], 'A') < lesson_date])]
        prior_due, candidates = review_candidates(prior_schedule, lesson_date)
        selectable = {row['Sentence ID'] for row in candidates} if plan.get('Review selection') else eligible
        capacity = review_target + missing
        if (new_target, capacity) not in ((7, 10), (5, 12)) or review_target != min(capacity, len(selectable)):
            errors.append(f'lesson {lesson_date}: invalid targets or unavailable-review count')
        if new_target == 5 and (plan.get('Quota adjustment approved') != 'yes' or len(prior_due) <= 20):
            errors.append(f'lesson {lesson_date}: adaptive quota requires confirmation and over 20 due sentences')
        if lesson_date > today:
            errors.append(f'lesson {lesson_date}: future lesson date')
        expected_types = ['new'] * new_target + ['review'] * review_target
        if [row['Type'] for row in rows] != expected_types or [integer(row['Order']) for row in rows] != list(range(1, len(rows) + 1)):
            errors.append(f'lesson {lesson_date}: invalid row count, order or types')
        for row in rows:
            identifier = row['Sentence ID']
            first_date = id_date(identifier, 'S')
            if row['Type'] == 'new':
                if first_date != lesson_date or identifier in reserved:
                    errors.append(f'lesson {lesson_date}: invalid or duplicated reserved ID {identifier}')
                reserved[identifier] = lesson_date
            elif row['Type'] == 'review' and identifier not in selectable:
                errors.append(f'lesson {lesson_date}: ineligible review {identifier}')
            if identifier in sentences and row['Vietnamese'] != sentences[identifier]['Vietnamese']:
                errors.append(f'lesson {lesson_date}: source differs from bank for {identifier}')
        for attempt in by_day[lesson_date]:
            question = indexed.get(attempt['Sentence'])
            if question is None or question['Type'] != attempt['Type']:
                errors.append(f"lesson {lesson_date}: attempt {attempt['Attempt']} not in plan")
        assessed = {attempt['Sentence'] for attempt in by_day[lesson_date]}
        assessed_positions = [row['Sentence ID'] in assessed for row in rows]
        if assessed_positions != sorted(assessed_positions, reverse=True):
            errors.append(f'lesson {lesson_date}: answers do not follow saved order')
        actual_order = [row['Sentence'] for row in sorted(by_day[lesson_date], key=lambda row: row['Attempt'])]
        if actual_order != [row['Sentence ID'] for row in rows[:len(actual_order)]]:
            errors.append(f'lesson {lesson_date}: attempt sequence differs from saved order')
        if str(lesson_date) in logs or (require_complete and lesson_date == today):
            if assessed != set(indexed):
                errors.append(f'lesson {lesson_date}: not all planned questions are assessed')
    if require_complete and today not in data['plans']:
        errors.append(f'lesson {today}: missing plan before completion')
    for value, log in logs.items():
        completed = date.fromisoformat(value)
        attempts = by_day[completed]
        if completed > today:
            errors.append(f'log {value}: future completion date')
        if completed not in data['plans']:
            errors.append(f'log {value}: completed session has no saved plan')
        counts = Counter(row['Result'] for row in attempts)
        expected = {'New': sum(row['Type'] == 'new' for row in attempts),
                    'Reviews': sum(row['Type'] == 'review' for row in attempts),
                    'Correct': counts['correct'], 'Incorrect': counts['incorrect'], 'Uncertain': counts['uncertain']}
        if not attempts or any(integer(log[field]) != total for field, total in expected.items()):
            errors.append(f'log {value}: totals differ from actual attempts')
    completed_dates = [date.fromisoformat(value) for value in logs]
    expected_streak = streak_snapshot(completed_dates, today)
    if data['streak'] != [expected_streak]:
        if (allow_stale_streak and completed_dates and expected_streak['Current streak'] == '0'
                and data['streak'] == [streak_snapshot(completed_dates, max(completed_dates))]):
            warnings.append('streak snapshot is stale after missed days; report computes streak from completed dates without writing')
        else:
            errors.append(f'streak: expected {expected_streak}')
    for studied in by_day:
        if studied not in data['plans']:
            warnings.append(f'{studied}: legacy attempts have no plan; reconstruct it before resuming')
    return errors, warnings


def progress_report(data, today):
    def period(start, end):
        attempts = [row for row in data['attempts'] if start <= id_date(row['Attempt'], 'A') <= end]
        stats = {}
        for kind in ('new', 'review'):
            rows = [row for row in attempts if row['Type'] == kind]
            counts = Counter(row['Result'] for row in rows)
            stats[kind] = {'attempts': len(rows), **{result: counts[result] for result in RESULTS},
                           'correct_percent': round(100 * counts['correct'] / len(rows), 1) if rows else None}
        notes = Counter(row['Note'] for row in attempts if row['Result'] != 'correct' and row['Note'] != '-')
        stats.update({'start': str(start), 'end': str(end),
                      'completed_days': len({row['Date'] for row in data['logs'] if start <= date.fromisoformat(row['Date']) <= end}),
                      'observed_notes': [{'note': note, 'attempts': count} for note, count in notes.most_common()]})
        return stats

    start = today - timedelta(days=6)
    due, candidates = review_candidates(data['schedule'], today)
    return {
        'as_of': str(today), 'current_week': period(start, today),
        'previous_week': period(start - timedelta(days=7), start - timedelta(days=1)),
        'streak': streak_snapshot([date.fromisoformat(row['Date']) for row in data['logs']], today),
        'due_count': len(due),
        'overdue_count': sum(date.fromisoformat(row['Next review']) < today for row in due),
        'due_ids': [row['Sentence ID'] for row in due],
        'review_candidate_ids': [row['Sentence ID'] for row in candidates],
        'quota_proposal': {'new': 5, 'reviews': 12, 'requires_confirmation': True} if len(due) > 20
                          else {'new': 7, 'reviews': 10, 'requires_confirmation': False},
        'related_sentence_links': data['links'],
        'limitations': ['No study-duration measurements.', 'Notes describe attempts, not stable error categories.',
                        'Weak-pattern snapshots cannot prove weekly improvement; use actual attempt evidence.'],
    }


def main():
    parser = argparse.ArgumentParser(description='Read-only validation and weekly metrics for EnglishLearning Markdown records.')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--date', type=date.fromisoformat, default=date.today(), help='Learner local date, YYYY-MM-DD')
    parser.add_argument('--require-complete', action='store_true', help='Require every row of today\'s plan to have a real assessed attempt')
    parser.add_argument('--report', action='store_true', help='Print JSON metrics for the last 7 days and preceding 7 days')
    args = parser.parse_args()
    try:
        data = load_data(args.root)
        errors, warnings = validate(data, args.date, args.require_complete, allow_stale_streak=args.report)
    except (OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1
    if args.report:
        output = {'valid': not errors, 'errors': errors, 'warnings': warnings}
        if not errors:
            output['report'] = progress_report(data, args.date)
        print(json.dumps(output, ensure_ascii=True, indent=2))
    else:
        for issue in errors:
            print(f'ERROR: {issue}')
        for issue in warnings:
            print(f'WARNING: {issue}')
        print('Validation passed.' if not errors else f'Validation failed: {len(errors)} issue(s).')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())