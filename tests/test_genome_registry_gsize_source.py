"""The GRCh38 MACS gsize and the sentence that names its source (decision 0256).

The registry's GRCh38 value, 2701495761, is deepTools' 50-bp effective genome size as printed in
the deepTools documentation of every release from 3.4.0 to 3.5.4; deepTools 3.5.5 and 3.5.6 print
2701495711, and nf-core/atacseq 2.1.2's iGenomes config lists 2701262066 for its NCBI GRCh38 at
read length 50.
These tests bind the registry's cell to the figure its sentence states, and the sentence to the
source it names, so the value can never again be called nf-core's.
"""
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GARS = REPO / 'gars'
REGISTRY = GARS / '_references' / 'genomes.md'
sys.path.insert(0, str(GARS / '_system'))
import configure  # noqa: E402

# The three published figures, read from their sources (decision 0256 gives the URLs and lines).
DEEPTOOLS_340_TO_354 = 2701495761
DEEPTOOLS_355_AND_356 = 2701495711
NFCORE_ATACSEQ_212 = 2701262066


def gsize_paragraph():
    """The registry's **MACS gsize** paragraph, joined into one line."""
    text = REGISTRY.read_text(encoding='utf-8')
    start = text.index('**MACS gsize**')
    end = text.find('\n\n', start)
    return ' '.join(text[start:end if end != -1 else len(text)].split())


def figures(paragraph):
    return [int(m.replace(',', '')) for m in re.findall(r'\b\d{1,3}(?:,\d{3}){2,}\b', paragraph)]


class GRCh38GsizeSourceTests(unittest.TestCase):
    def test_registry_value_is_the_figure_the_sentence_states(self):
        rows, err = configure.read_genomes(GARS)
        self.assertIsNone(err)
        grch38 = [r for r in rows if r['id'] == 'GRCh38']
        self.assertEqual(len(grch38), 1)
        value = int(grch38[0]['macs_gsize'])
        self.assertEqual(value, DEEPTOOLS_340_TO_354)
        stated = figures(gsize_paragraph())
        # The registry's value is stated exactly once, and so is each other source's figure.
        self.assertEqual(stated.count(value), 1, stated)
        self.assertEqual(stated.count(DEEPTOOLS_355_AND_356), 1, stated)
        self.assertEqual(stated.count(NFCORE_ATACSEQ_212), 1, stated)
        self.assertNotEqual(value, NFCORE_ATACSEQ_212)

    def test_sentence_names_deeptools_and_never_calls_the_value_nfcore(self):
        paragraph = gsize_paragraph()
        self.assertIn('deepTools documentation of every release from 3.4.0 to 3.5.4', paragraph)
        self.assertIn('nf-core/atacseq 2.1.2', paragraph)
        self.assertIn('not nf-core', paragraph)
        for claim in ('same value nf-core', "nf-core/atacseq's own iGenomes config uses",
                      'default read length'):
            with self.subTest(claim=claim):
                self.assertNotIn(claim, paragraph)


if __name__ == '__main__':
    unittest.main(verbosity=2)
