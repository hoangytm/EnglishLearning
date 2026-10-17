from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import learning_records
from learning_records import RecordError, complete_session, record_attempt, refresh_streak, session_status
from test_validate_learning import ROOT, sample_data, write_fixture
from validate_learning import load_data, validate


NEXT = date(2026, 10, 12)
NEW_IDS = [f'S-20261012-{number:03}' for number in range(1, 8)]
REVIEW_IDS = [f'S-20261011-{number:03}' for number in range(1, 8)]


def plan_for(lesson_date, new_ids, review_ids):
    rows = [{'Order': str(index), 'Type': 'new', 'Sentence ID': identifier, 'Vietnamese': f'New question {index}'}
            for index, identifier in enumerate(new_ids, 1)]
    rows += [{'Order': str(len(new_ids) + index), 'Type': 'review', 'Sentence ID': identifier,
              'Vietnamese': f'Question {int(identifier[-3:])}'} for index, identifier in enumerate(review_ids, 1)]
    return {'Lesson date': str(lesson_date), 'New target': '7', 'Review target': str(len(review_ids)),
            'Unavailable reviews': str(10 - len(review_ids)), 'Review selection': 'due-and-weak', 'rows': rows}


def snapshot(root):
    return {path: path.read_bytes() for path in root.rglob('*.md')}


class LearningRecordsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        data = sample_data()
        data['plans'][NEXT] = plan_for(NEXT, NEW_IDS, REVIEW_IDS)
        write_fixture(self.root, data)

    def tearDown(self):
        self.directory.cleanup()

    def record_new(self, index, result='incorrect', **extra):
        values = {'standard': f'Answer {index}.', 'structures': 'example structure', 'topic': 'work',
                  'note': '-' if result == 'correct' else 'Observed issue'}
        values.update(extra)
        return record_attempt(self.root, NEXT, NEW_IDS[index - 1], 'new', f'my answer {index}', result, **values)

    def test_fixture_plan_is_valid(self):
        self.assertEqual([], validate(load_data(self.root), NEXT)[0])

    def test_record_new_updates_all_related_records(self):
        output = self.record_new(1, patterns=['tense-aspect'])
        self.assertEqual('A-20261012-001', output['attempt'])
        self.assertEqual('1/14', output['progress'])
        self.assertEqual(NEW_IDS[1], output['next']['sentence_id'])
        data = load_data(self.root)
        self.assertEqual('New question 1', next(row for row in data['sentence_rows'] if row['ID'] == NEW_IDS[0])['Vietnamese'])
        schedule = next(row for row in data['schedule'] if row['Sentence ID'] == NEW_IDS[0])
        self.assertEqual(('0', '2026-10-13'), (schedule['Level'], schedule['Next review']))
        pattern = next(row for row in data['patterns'] if row['Pattern'] == 'tense-aspect')
        self.assertEqual(('1', NEW_IDS[0], 'Answer 1.'), (pattern['Count'], pattern['Recent sentences'], pattern['Example']))
        self.assertEqual([], validate(data, NEXT)[0])

    def test_pipe_and_whitespace_are_sanitised(self):
        record_attempt(self.root, NEXT, NEW_IDS[0], 'new', "I'll send\nit | today", 'incorrect', 'Bad | note',
                       standard='I will send it today.', structures='send', topic='work')
        attempt = load_data(self.root)['attempts'][-1]
        self.assertEqual(("I'll send it / today", 'Bad / note'), (attempt['Learner answer'], attempt['Note']))

    def test_rejections_leave_files_unchanged(self):
        self.record_new(1)
        before = snapshot(self.root)
        with self.assertRaisesRegex(RecordError, 'order 2'):
            self.record_new(3)
        with self.assertRaisesRegex(RecordError, 'order 2'):
            self.record_new(1)
        with self.assertRaisesRegex(RecordError, 'only recorded'):
            self.record_new(2, result='correct', patterns=['tense-aspect'])
        with self.assertRaisesRegex(RecordError, 'unknown pattern category: Tense; use one of: tense-aspect'):
            self.record_new(2, patterns=['Tense'])
        with self.assertRaisesRegex(RecordError, 'require'):
            self.record_new(2, topic='')
        with self.assertRaisesRegex(RecordError, 'earlier day'):
            self.record_new(2, related=NEW_IDS[0])
        with self.assertRaisesRegex(RecordError, 'resolve before recording'):
            record_attempt(self.root, date(2026, 10, 13), 'S-20261013-001', 'new', 'x', 'correct',
                           standard='x', structures='x', topic='x')
        self.assertEqual(before, snapshot(self.root))

    def test_failed_post_write_validation_rolls_back(self):
        before = snapshot(self.root)
        with mock.patch.object(learning_records, 'check_errors', return_value=['forced failure']):
            with self.assertRaisesRegex(RecordError, 'rolled back'):
                self.record_new(1, patterns=['tense-aspect'])
        self.assertEqual(before, snapshot(self.root))

    def test_add_category_then_use_it(self):
        output = learning_records.add_category(self.root, NEXT, 'phrasal-verb', 'Wrong or missing particle.')
        self.assertEqual('phrasal-verb', output['category']['Category'])
        self.assertIn('phrasal-verb', session_status(self.root, NEXT)['categories'])
        self.record_new(1, patterns=['phrasal-verb'])
        self.assertEqual(['phrasal-verb'], [row['Pattern'] for row in load_data(self.root)['patterns']])
        before = snapshot(self.root)
        for name, description in (('phrasal-verb', 'again'), ('Bad Name', 'x'), ('new-one', ' ')):
            with self.assertRaises(RecordError):
                learning_records.add_category(self.root, NEXT, name, description)
        self.assertEqual(before, snapshot(self.root))

    def test_full_session_completion_and_streak(self):
        for index in range(1, 8):
            extra = {'related': REVIEW_IDS[1]} if index == 7 else {}
            self.record_new(index, result='correct' if index == 7 else 'incorrect', **extra)
        for index, identifier in enumerate(REVIEW_IDS):
            output = record_attempt(self.root, NEXT, identifier, 'review', 'review answer',
                                    'correct' if index == 0 else 'uncertain', '-' if index == 0 else 'Less natural')
        self.assertIsNone(output['next'])
        reviewed = next(row for row in load_data(self.root)['schedule'] if row['Sentence ID'] == REVIEW_IDS[0])
        self.assertEqual(('2', '2026-10-19', '1'), (reviewed['Level'], reviewed['Next review'], reviewed['Reviews']))
        self.assertEqual({'Sentence ID': NEW_IDS[6], 'Related sentence': REVIEW_IDS[1]}, load_data(self.root)['links'][0])
        self.assertIsNone(session_status(self.root, NEXT)['plan']['next'])

        result = complete_session(self.root, NEXT)
        self.assertEqual(('7', '7', '2', '6', '6'), tuple(result['log'][field] for field in
                                                         ('New', 'Reviews', 'Correct', 'Uncertain', 'Incorrect')))
        self.assertEqual({'Current streak': '2', 'Best streak': '2', 'Last completed': '2026-10-12'}, result['streak'])
        self.assertEqual([], validate(load_data(self.root), NEXT, require_complete=True)[0])
        before = snapshot(self.root)
        self.assertTrue(complete_session(self.root, NEXT)['already_completed'])
        self.assertEqual(before, snapshot(self.root))
        with self.assertRaisesRegex(RecordError, 'already completed'):
            record_attempt(self.root, NEXT, REVIEW_IDS[0], 'review', 'again', 'correct')

    def test_incomplete_session_cannot_complete(self):
        self.record_new(1)
        before = snapshot(self.root)
        with self.assertRaisesRegex(RecordError, 'not all planned'):
            complete_session(self.root, NEXT)
        self.assertEqual(before, snapshot(self.root))

    def test_new_quota_sessions_resume_and_complete_with_saved_targets(self):
        for policy, total, capacity in (('standard-20', 20, 17), ('weekend-30', 30, 25)):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                data = sample_data()
                due_ids = REVIEW_IDS[:6]
                new_ids = [f'S-20261012-{number:03}' for number in range(1, total - len(due_ids) + 1)]
                plan = plan_for(NEXT, new_ids, due_ids)
                plan.update({'New target': str(len(new_ids)), 'Unavailable reviews': str(capacity - len(due_ids)),
                             'Review selection': 'due-only', 'Quota policy': policy})
                data['plans'][NEXT] = plan
                write_fixture(root, data)
                plan_path = root / f'data/history/lessons/{NEXT}.md'
                saved_plan = plan_path.read_bytes()
                for index, identifier in enumerate(new_ids, 1):
                    output = record_attempt(root, NEXT, identifier, 'new', f'Answer {index}', 'correct',
                                            standard=f'Answer {index}', structures='example', topic='work')
                    self.assertEqual(f'{index}/{total}', output['progress'])
                    state = session_status(root, NEXT)
                    self.assertTrue(state['ok'])
                    self.assertEqual({'new': len(new_ids), 'review': len(due_ids),
                                      'unavailable_reviews': capacity - len(due_ids)}, state['plan']['targets'])
                    self.assertEqual(index, state['plan']['done']['new'])
                before = snapshot(root)
                with self.assertRaisesRegex(RecordError, 'not all planned'):
                    complete_session(root, NEXT)
                self.assertEqual(before, snapshot(root))
                for identifier in due_ids:
                    output = record_attempt(root, NEXT, identifier, 'review', 'Review answer', 'correct')
                self.assertEqual(f'{total}/{total}', output['progress'])
                result = complete_session(root, NEXT)
                self.assertTrue(result['ok'])
                self.assertEqual((str(len(new_ids)), str(len(due_ids))),
                                 (result['log']['New'], result['log']['Reviews']))
                self.assertEqual('2', result['streak']['Current streak'])
                self.assertEqual(saved_plan, plan_path.read_bytes())
                self.assertEqual([], validate(load_data(root), NEXT, require_complete=True)[0])
                self.assertTrue(complete_session(root, NEXT)['already_completed'])

    def test_refresh_streak_after_gap_and_new_month_files(self):
        later = date(2026, 11, 1)
        data = load_data(self.root)
        data['plans'] = {date(2026, 10, 11): data['plans'][date(2026, 10, 11)],
                         later: plan_for(later, [f'S-20261101-{n:03}' for n in range(1, 8)], REVIEW_IDS)}
        write_fixture(self.root, data)
        (self.root / 'data/history/lessons/2026-10-12.md').unlink()
        self.assertTrue(validate(load_data(self.root), later)[0])
        refreshed = refresh_streak(self.root, later)
        self.assertTrue(refreshed['ok'] and refreshed['changed'])
        self.assertEqual({'Current streak': '0', 'Best streak': '1', 'Last completed': '2026-10-11'}, refreshed['streak'])
        record_attempt(self.root, later, 'S-20261101-001', 'new', 'answer', 'incorrect', 'Issue',
                       standard='Answer.', structures='x', topic='work')
        self.assertTrue((self.root / 'data/sentences/2026-11.md').read_text(encoding='utf-8').startswith('# Sentences 2026-11'))
        self.assertTrue((self.root / 'data/history/2026-11.md').exists())
        self.assertEqual([], validate(load_data(self.root), later)[0])

    def test_cli_status_and_record(self):
        script = str(ROOT / 'scripts/learning_records.py')
        base = [sys.executable, '-B', script, '--root', str(self.root)]
        status = subprocess.run(base + ['status', '--date', str(NEXT)], capture_output=True, text=True, check=False)
        self.assertEqual(0, status.returncode, status.stdout + status.stderr)
        self.assertEqual(NEW_IDS[0], json.loads(status.stdout)['plan']['next']['sentence_id'])
        record = subprocess.run(base + ['record', '--date', str(NEXT), '--sentence', NEW_IDS[0], '--type', 'new',
                                        '--answer', "I'll do it", '--result', 'incorrect', '--note', '`on tomorrow` again',
                                        '--standard', "I'll do it tomorrow.", '--structures', 'do it', '--topic', 'work',
                                        '--pattern', 'time-preposition'], capture_output=True, text=True, check=False)
        self.assertEqual(0, record.returncode, record.stdout + record.stderr)
        self.assertEqual('`on tomorrow` again', load_data(self.root)['attempts'][-1]['Note'])
        wrong = subprocess.run(base + ['record', '--date', str(NEXT), '--sentence', NEW_IDS[0], '--type', 'new',
                                       '--answer', 'x', '--result', 'correct'], capture_output=True, text=True, check=False)
        self.assertEqual(1, wrong.returncode)
        self.assertFalse(json.loads(wrong.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
