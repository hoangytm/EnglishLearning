from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from validate_learning import (
    ATTEMPT_COLUMNS, CATEGORY_COLUMNS, DataError, LINK_COLUMNS, LOG_COLUMNS, PATTERN_COLUMNS,
    PLAN_COLUMNS, SCHEDULE_COLUMNS, SENTENCE_COLUMNS, STREAK_COLUMNS,
    load_data, progress_report, project_schedule, read_tables, review_candidates, streak_snapshot, validate,
)


ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 11)


def sample_data():
    sentences, attempts, schedule, questions = [], [], [], []
    for number in range(1, 8):
        identifier = f'S-20261011-{number:03}'
        sentences.append(dict(zip(SENTENCE_COLUMNS, (identifier, f'Question {number}', 'Example answer', 'example', 'work'))))
        attempt = dict(zip(ATTEMPT_COLUMNS, (f'A-20261011-{number:03}', identifier, 'new',
                                           'Learner answer', 'uncertain' if number == 7 else 'incorrect', 'Observed issue')))
        attempts.append(attempt)
        schedule.append(dict(project_schedule([attempt]), **{'Sentence ID': identifier}))
        questions.append(dict(zip(PLAN_COLUMNS, (str(number), 'new', identifier, f'Question {number}'))))
    return {'sentence_rows': sentences, 'attempts': attempts, 'schedule': schedule, 'links': [], 'patterns': [],
            'categories': [{'Category': name, 'Description': f'Description of {name}.'}
                           for name in ('tense-aspect', 'time-preposition', 'word-choice')],
            'plans': {TODAY: {'Lesson date': str(TODAY), 'New target': '7', 'Review target': '0',
                             'Unavailable reviews': '10', 'rows': questions}},
            'logs': [{'Date': str(TODAY), 'New': '7', 'Reviews': '0', 'Correct': '0', 'Incorrect': '6',
                      'Uncertain': '1', 'Notable errors': 'Observed issue', 'Next due': '2026-10-12'}],
            'streak': [streak_snapshot([TODAY], TODAY)]}


def write_table(path, schema, rows, prefix='', append=False):
    text = prefix + '\n| ' + ' | '.join(schema) + ' |\n| ' + ' | '.join(['---'] * len(schema)) + ' |\n'
    text += ''.join('| ' + ' | '.join(row[field] for field in schema) + ' |\n' for row in rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a' if append else 'w', encoding='utf-8') as stream:
        stream.write(text)


def write_fixture(root, data):
    write_table(root / 'data/sentences/2026-10.md', SENTENCE_COLUMNS, data['sentence_rows'])
    if data['links']:
        write_table(root / 'data/sentences/2026-10.md', LINK_COLUMNS, data['links'], append=True)
    write_table(root / 'data/history/2026-10.md', ATTEMPT_COLUMNS, data['attempts'])
    write_table(root / 'data/review_schedule.md', SCHEDULE_COLUMNS, data['schedule'])
    write_table(root / 'logs/daily_log.md', LOG_COLUMNS, data['logs'])
    write_table(root / 'data/streak.md', STREAK_COLUMNS, data['streak'])
    write_table(root / 'data/weak_patterns.md', PATTERN_COLUMNS, data['patterns'])
    write_table(root / 'data/pattern_categories.md', CATEGORY_COLUMNS, data['categories'])
    for lesson_date, plan in data['plans'].items():
        prefix = f'# Lesson {lesson_date}\n\n'
        prefix += ''.join(f'- {field}: {value}\n' for field, value in plan.items() if field != 'rows')
        write_table(root / f'data/history/lessons/{lesson_date}.md', PLAN_COLUMNS, plan['rows'], prefix)


class LearningValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = sample_data()

    def test_valid_fixture_is_consistent(self):
        self.assertEqual([], validate(self.data, TODAY)[0])

    def test_weak_pattern_must_be_a_known_category(self):
        self.data['patterns'] = [{'Pattern': 'Tense', 'Count': '1', 'Last seen': str(TODAY),
                                  'Example': 'Answer.', 'Recent sentences': 'S-20261011-001'}]
        self.assertTrue(any('not in data/pattern_categories.md' in error for error in validate(self.data, TODAY)[0]))
        self.data['patterns'][0]['Pattern'] = 'tense-aspect'
        self.assertEqual([], validate(self.data, TODAY)[0])
        self.data['categories'].append({'Category': 'Bad Name', 'Description': 'x'})
        self.data['categories'].append(dict(self.data['categories'][0]))
        errors = validate(self.data, TODAY)[0]
        self.assertTrue(any('lowercase words' in error for error in errors))
        self.assertTrue(any('duplicate tense-aspect' in error for error in errors))

    def test_duplicate_attempt_and_repeated_sentence(self):
        self.data['attempts'].append(deepcopy(self.data['attempts'][0]))
        errors = validate(self.data, TODAY)[0]
        self.assertTrue(any('duplicate' in error for error in errors))
        self.assertTrue(any('assessed twice' in error for error in errors))

    def test_unknown_sentence(self):
        self.data['attempts'][0]['Sentence'] = 'S-20261011-999'
        self.assertTrue(any('unknown sentence' in error for error in validate(self.data, TODAY)[0]))

    def test_schedule_count_and_missing_row(self):
        self.data['schedule'][0]['Incorrect'] = '99'
        self.data['schedule'].pop()
        errors = validate(self.data, TODAY)[0]
        self.assertTrue(any('Incorrect expected' in error for error in errors))
        self.assertTrue(any('missing schedule row' in error for error in errors))

    def test_wrong_streak_and_log(self):
        self.data['streak'][0]['Best streak'] = '99'
        self.data['logs'][0]['New'] = '0'
        errors = validate(self.data, TODAY)[0]
        self.assertTrue(any('streak:' in error for error in errors))
        self.assertTrue(any('totals differ' in error for error in errors))

    def test_readonly_report_handles_expired_streak_but_not_wrong_best(self):
        later = date(2026, 10, 13)
        self.assertTrue(any('streak:' in error for error in validate(self.data, later)[0]))
        errors, warnings = validate(self.data, later, allow_stale_streak=True)
        self.assertEqual([], errors)
        self.assertTrue(any('stale' in warning for warning in warnings))
        self.assertEqual('0', progress_report(self.data, later)['streak']['Current streak'])
        self.data['streak'][0]['Best streak'] = '99'
        self.assertTrue(any('streak:' in error for error in validate(self.data, later, allow_stale_streak=True)[0]))

    def test_ineligible_review_and_wrong_targets(self):
        plan = self.data['plans'][TODAY]
        plan['rows'][0]['Type'] = 'review'
        plan['New target'] = '6'
        errors = validate(self.data, TODAY)[0]
        self.assertTrue(any('ineligible review' in error for error in errors))
        self.assertTrue(any('invalid targets' in error for error in errors))

    def test_partial_lesson_does_not_require_completion(self):
        self.data['attempts'].pop()
        self.data['sentence_rows'].pop()
        self.data['schedule'].pop()
        self.data['patterns'] = self.data['patterns'][:-1]
        self.data['logs'] = []
        self.data['streak'] = [streak_snapshot([], TODAY)]
        self.assertEqual([], validate(self.data, TODAY)[0])
        self.assertTrue(any('not all planned' in error for error in validate(self.data, TODAY, True)[0]))

    def test_missing_legacy_plan_is_warning_until_completion(self):
        self.data['plans'] = {}
        self.data['logs'] = []
        self.data['streak'] = [streak_snapshot([], TODAY)]
        errors, warnings = validate(self.data, TODAY)
        self.assertEqual([], errors)
        self.assertTrue(warnings)
        self.assertTrue(validate(self.data, TODAY, True)[0])

    def test_schedule_levels_follow_actual_attempts(self):
        attempts = [{'Attempt': f'A-202610{12 + index}-001', 'Type': 'review', 'Result': result}
                    for index, result in enumerate(('correct', 'correct', 'correct', 'correct', 'correct'))]
        projected = project_schedule(attempts)
        self.assertEqual('5', projected['Level'])
        self.assertEqual('5', projected['Correct'])
        attempts.append({'Attempt': 'A-20261017-001', 'Type': 'review', 'Result': 'incorrect'})
        self.assertEqual('0', project_schedule(attempts)['Level'])

    def test_streak_deduplication_gap_and_best(self):
        completed = [date(2026, 10, day) for day in (5, 6, 6, 7, 10)]
        self.assertEqual({'Current streak': '1', 'Best streak': '3', 'Last completed': '2026-10-10'},
                         streak_snapshot(completed, TODAY))
        self.assertEqual('0', streak_snapshot(completed, date(2026, 10, 12))['Current streak'])
        completed.append(TODAY)
        self.assertEqual('2', streak_snapshot(completed, TODAY)['Current streak'])

    def test_report_separates_new_reviews_and_empty_periods(self):
        report = progress_report(self.data, TODAY)
        self.assertEqual(7, report['current_week']['new']['attempts'])
        self.assertEqual(0, report['current_week']['review']['attempts'])
        self.assertIsNone(report['current_week']['review']['correct_percent'])
        self.assertEqual(0, report['previous_week']['new']['attempts'])
        self.assertEqual(1, report['current_week']['completed_days'])

    def test_flexible_proposal_shifts_unused_review_slots_to_new(self):
        row = {'Sentence ID': 'S-20261001-001', 'Next review': '2026-10-10', 'Level': '0', 'Latest result': 'incorrect'}
        expected = {0: (17, 0), 10: (7, 10), 14: (3, 14), 30: (3, 14)}
        for count, (new, reviews) in expected.items():
            self.data['schedule'] = [dict(row, **{'Sentence ID': f'S-20261001-{index:03}'}) for index in range(1, count + 1)]
            proposal = progress_report(self.data, TODAY)['quota_proposal']
            self.assertEqual({'new': new, 'reviews': reviews, 'policy': 'flexible-17'}, proposal, count)

    def flexible_day(self, older, new_count):
        self.data['logs'] = []
        self.data['streak'] = [streak_snapshot([], TODAY)]
        keep = min(new_count, 7)
        self.data['attempts'] = self.data['attempts'][:keep]
        self.data['sentence_rows'] = self.data['sentence_rows'][:keep]
        self.data['schedule'] = self.data['schedule'][:keep]
        reviews = []
        for number in range(1, older + 1):
            identifier = f'S-20261001-{number:03}'
            self.data['sentence_rows'].append(dict(zip(SENTENCE_COLUMNS, (identifier, f'Old {number}', 'Answer', 'example', 'work'))))
            attempt = dict(zip(ATTEMPT_COLUMNS, (f'A-20261001-{number:03}', identifier, 'new', 'Answer', 'incorrect', 'Issue')))
            self.data['attempts'].append(attempt)
            self.data['schedule'].append(dict(project_schedule([attempt]), **{'Sentence ID': identifier}))
        self.data['schedule'].sort(key=lambda row: (row['Next review'], row['Sentence ID']))
        review_count = min(14, older)
        for number in range(1, review_count + 1):
            reviews.append(dict(zip(PLAN_COLUMNS, (str(new_count + number), 'review', f'S-20261001-{number:03}', f'Old {number}'))))
        news = [dict(zip(PLAN_COLUMNS, (str(number), 'new', f'S-20261011-{number:03}', f'Question {number}')))
                for number in range(1, new_count + 1)]
        plan = self.data['plans'][TODAY]
        plan.update({'New target': str(new_count), 'Review target': str(review_count),
                     'Unavailable reviews': str(14 - review_count), 'Review selection': 'due-and-weak',
                     'Quota policy': 'flexible-17', 'rows': news + reviews})
        return plan

    def test_flexible_plan_balances_new_and_reviews(self):
        for older, new_count in ((0, 17), (10, 7), (14, 3), (30, 3)):
            self.flexible_day(older, new_count)
            self.assertEqual([], validate(self.data, TODAY)[0], (older, new_count))
            self.setUp()

    def test_flexible_plan_rejects_wrong_split(self):
        for older, new_count in ((0, 7), (10, 8), (30, 4), (30, 2)):
            plan = self.flexible_day(older, new_count)
            plan['Unavailable reviews'] = str(14 - int(plan['Review target']))
            self.assertTrue(any('invalid targets' in error for error in validate(self.data, TODAY)[0]), (older, new_count))
            self.setUp()

    def test_exact_vietnamese_repeats_are_rejected(self):
        self.assertEqual([], validate(self.data, TODAY)[0])
        self.data['sentence_rows'][1]['Vietnamese'] = ' QUESTION 1!! '
        self.data['plans'][TODAY]['rows'][1]['Vietnamese'] = ' QUESTION 1!! '
        errors = validate(self.data, TODAY)[0]
        self.assertTrue(any('S-20261011-002: repeats the Vietnamese of S-20261011-001' in e for e in errors))
        self.assertTrue(any('lesson 2026-10-11: S-20261011-002 repeats' in e for e in errors))

    def test_planned_new_question_cannot_repeat_bank_or_batch(self):
        plan = self.flexible_day(2, 15)
        plan['rows'][12]['Vietnamese'] = 'Fresh A'
        plan['rows'][13]['Vietnamese'] = 'fresh a.'
        self.assertTrue(any('S-20261011-014 repeats the Vietnamese of S-20261011-013' in e
                            for e in validate(self.data, TODAY)[0]))
        plan['rows'][13]['Vietnamese'] = 'Old 1'
        self.assertTrue(any('S-20261011-014 repeats the Vietnamese of S-20261001-001' in e
                            for e in validate(self.data, TODAY)[0]))
        plan['rows'][13]['Vietnamese'] = 'Fresh B'
        self.assertEqual([], validate(self.data, TODAY)[0])

    def test_optional_related_link_and_future_link(self):
        self.data['links'] = [{'Sentence ID': 'S-20261011-007', 'Related sentence': 'S-20261011-001'}]
        self.assertTrue(any('earlier day' in error for error in validate(self.data, TODAY)[0]))

    def test_due_first_and_no_early_mastered_reviews(self):
        schedule = [
            {'Sentence ID': 'S-20261001-001', 'Next review': '2026-11-01', 'Level': '4', 'Latest result': 'correct'},
            {'Sentence ID': 'S-20261001-002', 'Next review': '2026-10-12', 'Level': '0', 'Latest result': 'incorrect'},
            {'Sentence ID': 'S-20261001-003', 'Next review': '2026-10-10', 'Level': '4', 'Latest result': 'correct'},
        ]
        due, candidates = review_candidates(schedule, TODAY)
        self.assertEqual(['S-20261001-003'], [row['Sentence ID'] for row in due])
        self.assertEqual(['S-20261001-003', 'S-20261001-002'], [row['Sentence ID'] for row in candidates])

    def test_question_plan_cannot_add_an_answer_table(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'tables.md'
            path.write_text('| ' + ' | '.join(PLAN_COLUMNS) + ' |\n| --- | --- | --- | --- |\n\n'
                            '| Answer |\n| --- |\n| An answer |\n', encoding='utf-8')
            with self.assertRaises(DataError):
                read_tables(path, (PLAN_COLUMNS,))

    def test_readonly_cli_report_and_complete_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.data['plans'][TODAY]['Review selection'] = 'due-and-weak'
            write_fixture(root, self.data)
            before = {path: path.read_bytes() for path in root.rglob('*.md')}
            command = [sys.executable, '-B', str(ROOT / 'scripts/validate_learning.py'),
                       '--root', str(root), '--date', str(TODAY), '--report', '--require-complete']
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertTrue(report['valid'])
            self.assertEqual(7, report['report']['current_week']['new']['attempts'])
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob('*.md')})

    def test_cli_default_root_from_unrelated_directory_with_spaces(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'shared learning workspace'
            script = root / 'scripts/validate_learning.py'
            write_fixture(root, self.data)
            script.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'scripts/validate_learning.py', script)
            cwd = Path(directory) / 'unrelated terminal directory'
            cwd.mkdir()
            before = {path: path.read_bytes() for path in root.rglob('*.md')}
            for root_args in ([], ['--root', str(root)]):
                command = [sys.executable, '-B', str(script), *root_args,
                           '--date', str(TODAY), '--report', '--require-complete']
                result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
                self.assertEqual(0, result.returncode, result.stderr + result.stdout)
                self.assertTrue(json.loads(result.stdout)['valid'])
            self.assertEqual(before, {path: path.read_bytes() for path in root.rglob('*.md')})

    def test_shared_entrypoints_load_the_same_skill(self):
        instructions = (ROOT / 'AGENTS.md').read_text(encoding='utf-8')
        skill_path = '.agents/skills/english-coach/SKILL.md'
        skill = (ROOT / skill_path).read_text(encoding='utf-8')
        self.assertIn(skill_path, instructions)
        self.assertIn('$english-coach start-english', instructions)
        self.assertIn('$english-coach english-progress', instructions)
        self.assertIn('## Portable runtime', skill)
        for name in ('start-english', 'english-progress'):
            entry = (ROOT / f'.agents/skills/{name}/SKILL.md').read_text(encoding='utf-8')
            self.assertIn(f'name: {name}', entry)
            self.assertIn(f'Request: `{name}`.', entry)
            self.assertIn(skill_path, entry)
            self.assertIn('in full', entry)
        self.assertFalse((ROOT / '.github/prompts').exists())

    def test_link_table_roundtrip_and_outside_plan_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.data['links'] = [{'Sentence ID': 'S-20261011-007', 'Related sentence': 'S-20261011-001'}]
            write_fixture(root, self.data)
            self.assertEqual(self.data['links'], load_data(root)['links'])
            path = root / f'data/history/lessons/{TODAY}.md'
            with path.open('a', encoding='utf-8') as stream:
                stream.write('\nAnswer: a leaked answer\n')
            with self.assertRaises(DataError):
                load_data(root)

    def test_repeated_attempt_order_is_detected(self):
        self.data['attempts'][0]['Attempt'], self.data['attempts'][1]['Attempt'] = (
            self.data['attempts'][1]['Attempt'], self.data['attempts'][0]['Attempt'])
        self.assertTrue(any('attempt sequence differs' in error for error in validate(self.data, TODAY)[0]))

    def test_adaptive_plan_is_valid_only_after_confirmation(self):
        self.data['logs'] = []
        self.data['streak'] = [streak_snapshot([], TODAY)]
        self.data['attempts'] = self.data['attempts'][:5]
        self.data['sentence_rows'] = self.data['sentence_rows'][:5]
        self.data['schedule'] = self.data['schedule'][:5]
        reviews = []
        for number in range(1, 22):
            identifier = f'S-20261001-{number:03}'
            self.data['sentence_rows'].append(dict(zip(SENTENCE_COLUMNS, (identifier, f'Old question {number}', 'Answer', 'example', 'work'))))
            attempt = dict(zip(ATTEMPT_COLUMNS, (f'A-20261001-{number:03}', identifier, 'new', 'Answer', 'incorrect', 'Issue')))
            self.data['attempts'].append(attempt)
            self.data['schedule'].append(dict(project_schedule([attempt]), **{'Sentence ID': identifier}))
            if number <= 12:
                reviews.append(dict(zip(PLAN_COLUMNS, (str(5 + number), 'review', identifier, f'Old question {number}'))))
        self.data['schedule'].sort(key=lambda row: (row['Next review'], row['Sentence ID']))
        plan = self.data['plans'][TODAY]
        plan.update({'New target': '5', 'Review target': '12', 'Unavailable reviews': '0', 'Review selection': 'due-and-weak'})
        plan['rows'] = plan['rows'][:5] + reviews
        self.assertTrue(any('requires confirmation' in error for error in validate(self.data, TODAY)[0]))
        plan['Quota adjustment approved'] = 'yes'
        self.assertEqual([], validate(self.data, TODAY)[0])
        self.data['links'] = [{'Sentence ID': 'S-20261011-001', 'Related sentence': 'S-20261001-001'}]
        self.assertEqual([], validate(self.data, TODAY)[0])

    def test_markdown_tables_reject_answer_columns_and_bad_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.md'
            path.write_text('| Order | Type | Sentence ID | Vietnamese | Answer |\n| --- | --- | --- | --- | --- |\n', encoding='utf-8')
            with self.assertRaises(DataError):
                read_tables(path, (PLAN_COLUMNS,))
            path.write_text('| ' + ' | '.join(ATTEMPT_COLUMNS) + ' |\n| ' + ' | '.join(['---'] * 6) + ' |\n| too | few |\n', encoding='utf-8')
            with self.assertRaises(DataError):
                read_tables(path, (ATTEMPT_COLUMNS,))

    def test_real_data_are_never_written(self):
        before = {path: path.read_bytes() for path in (ROOT / 'data').rglob('*.md')}
        validate(load_data(ROOT), TODAY)
        progress_report(load_data(ROOT), TODAY)
        self.assertEqual(before, {path: path.read_bytes() for path in before})


if __name__ == '__main__':
    unittest.main()