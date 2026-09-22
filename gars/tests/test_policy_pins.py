"""R-099 pin refusal, including positive reviewed control in disposable fixtures."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from support import GARS, run
from tools import pins


class PolicyPinsTests(unittest.TestCase):
    def test_unreviewed_altered_missing_and_rejected(self):
        with tempfile.TemporaryDirectory(prefix='policy-pins-') as tmp:
            root=Path(tmp); (root/'_references').mkdir()
            skill=root/'SKILL.md'; skill.write_text('synthetic skill\n')
            entry={'path':'SKILL.md','sha256':hashlib.sha256(skill.read_bytes()).hexdigest(),'review_status':'reviewed'}
            def write():
                (root/'_references/tool_pins.json').write_text(json.dumps({'pins':[entry]}))
            write(); self.assertEqual(pins.check(root),[])
            entry['review_status']='unreviewed'; write(); self.assertTrue(pins.check(root))
            entry['review_status']='rejected'; write(); self.assertTrue(pins.check(root))
            entry['review_status']='reviewed'; write()
            skill.write_text('changed\n'); self.assertTrue(pins.check(root))
            skill.unlink(); self.assertTrue(pins.check(root))

    def test_inventory_covers_shipped_skills(self):
        manifest=json.loads((GARS/'_references/tool_pins.json').read_text())
        self.assertEqual({p.relative_to(GARS).as_posix() for p in pins.inventory(GARS)},
                         {p['path'] for p in manifest['pins']})
        self.assertEqual(manifest['mcp_servers'],[])

    def test_session_start_refuses_unreviewed(self):
        result=run(['bash',GARS/'_system/session_state.sh'])
        self.assertEqual(result.returncode,2)
        self.assertIn(b'R-099',result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
