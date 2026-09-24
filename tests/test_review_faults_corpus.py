"""Whole sanitized deployment calls; labels follow lane specification item 22."""
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/review-faults'))
import run_reviews
from testing import temporary


class CorpusTests(unittest.TestCase):
    def test_honest_call_corpus(self):
        root = temporary(self)
        home = root / 'h'
        kit = home / 'k'
        (kit / 'tmp').mkdir(parents=True)
        session = '00000000-0000-4000-8000-000000000019'
        rows = [json.loads(line) for line in
                (REPO / 'tests/data/review_faults_honest_calls.jsonl').read_text().splitlines()]
        scored = 0
        with mock.patch.object(run_reviews.pwd, 'getpwuid',
                               return_value=SimpleNamespace(pw_dir=str(home))):
            store = run_reviews.session_output_store(kit, session)
            replacements = [('<KIT>', str(kit.resolve())), ('<STORE>', str(store)),
                            ('<KITNAME>', store.parents[1].name), ('<HOME>', str(home)),
                            ('<UID>', str(os.getuid())),
                            ('<REVIEWER-ACCOUNT>', 'reviewer1'), ('<PRODUCER-ACCOUNT>', 'producer1'),
                            ('<HOST>', 'hostone'), ('<ACCOUNT-PREFIX>', 'acctprefix'),
                            ('<OWNER-FIRST>', 'ownerfirst'), ('<OWNER-LAST>', 'ownerlast'),
                            ('<OWNER-LAST2>', 'ownerlasttwo'), ('<OWNER-LOGIN-PREFIX>', 'ownerpfx'),
                            ('<OWNER-LOGIN>', 'ownerlogin'), ('<OWNER-GH>', 'ownergh'),
                            ('<NUM-A>', '12345')]

            def substitute(value):
                if isinstance(value, str):
                    for old, new in replacements:
                        value = value.replace(old, new)
                elif isinstance(value, dict):
                    value = {key: substitute(item) for key, item in value.items()}
                elif isinstance(value, list):
                    value = [substitute(item) for item in value]
                return value

            for row in rows:
                event = {'type': 'tool_use', 'name': row['tool'], 'input': substitute(row['fields'])}
                result = run_reviews.blindness([event], kit, session)
                scored += result['calls']
                with self.subTest(call=row['id'], label=row['expect']):
                    self.assertEqual(result['calls'], 1)
                    if row['expect'] == 'honest':
                        self.assertEqual(result['hits'], 0, row['id'])
                    else:
                        self.assertEqual(row['expect'], 'contract_hit')
                        self.assertGreaterEqual(result['hits'], 1, row['id'])
        print('honest-call corpus graded-against-seen: %d/%d' % (scored, len(rows)))
        self.assertEqual(scored, len(rows))
        self.assertEqual(len(rows), 278)
        self.assertEqual(sum(row['expect'] == 'honest' for row in rows), 277)


if __name__ == '__main__':
    unittest.main(verbosity=2)
