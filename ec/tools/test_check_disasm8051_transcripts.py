#!/usr/bin/env python3
"""Does `check_disasm8051_transcripts.py` hold the committed `--self-test`
transcripts to the run, and refuse when it should?

The check exists because every fence under `ec/annotations/` quoting the mode's
summary line was quoting a line the run no longer prints, and nothing compared
them to it -- `test_disasm8051_oracle.py`'s `TranscriptContract` holds the
*producer*. A check that has never been seen to refuse is not evidence of
anything, so **the mutations are most of this file**: each takes the committed
tree, changes one transcript in one specific way, and requires a named failure.
A summary re-transcribed with a clause dropped, a prompt deleted so the block
stops being findable, a summary deleted so a `console` fence quotes nothing at
all, and a corpus with no transcript in it.

The two that shrink the corpus without changing a word are the interesting
ones. Deleting a prompt or a summary leaves every remaining transcript correct,
so a check that only compared what it found would report a clean run over a
corpus one smaller -- and a corpus that shrinks silently is how the originals
went stale in the first place.

**What is asserted about the committed tree is a claim about named files, never
a count.** Which files this branch corrected, and which were already current,
are statements about files a reader can open; how many transcripts exist is a
value every merge adding one has to edit, and this repository has been bitten by
that shape enough to refuse it in new code. The cases name files; none of them
counts them.

Nothing here reads firmware beyond the one `self_test()` call the check itself
makes, over the committed image. No capture, no EC, no register read back,
nothing deferred to a human at the machine.
"""
import contextlib
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location(
    'check_disasm8051_transcripts', HERE / 'check_disasm8051_transcripts.py')
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)

ANNOTATIONS = HERE.parent / 'annotations'
FIRMWARE = str(HERE.parent / 'firmware' / 'GMxMGxx_11.800')

# Transcripts that were already current when this check was written, so the
# corpus is not only the files this branch touched. Named as files rather than
# asserted as a count: a merge that adds a transcript must not break this case,
# and one that deletes one should.
ALREADY_CURRENT = ('ec-07d6-07d7-sites.md', 'ec-09e9-09eb-sites.md')

# The one file the oracle opens on every run, whose transcript the check holds
# for the same reason: a file `--self-test` re-reads is a file whose transcript
# is worth being right about.
ORACLE_FILE = 'bank-call-audit.md'


def run(annotations):
    """(exit code, stdout, stderr) from the check as a subprocess.

    A subprocess rather than `main()` in-process because the exit code is part
    of what is under test: `main()` is three different verdicts and a case that
    only called it would be asserting the return value, not what a caller in
    `agent-gates.sh` reads.
    """
    proc = subprocess.run(
        [sys.executable, str(HERE / 'check_disasm8051_transcripts.py'),
         '--firmware', FIRMWARE, '--annotations', str(annotations)],
        capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


@contextlib.contextmanager
def scratch(mutate=None):
    """A copy of `ec/annotations/`, optionally mutated, for one run.

    Copied whole rather than reduced to the two files a case needs, because the
    corpus is the thing being tested: a scratch directory holding one file would
    pass for reasons that say nothing about the tree.
    """
    tmp = tempfile.mkdtemp()
    dst = Path(tmp) / 'annotations'
    shutil.copytree(ANNOTATIONS, dst)
    if mutate is not None:
        mutate(dst)
    try:
        yield dst
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def edit(path, old, new):
    """Replace `old` with `new` in `path`, refusing a no-op.

    A mutation that does not apply is the failure mode that makes a mutation
    suite lie: the case would be asserting the tool's behaviour on a tree the
    mutation never reached.
    """
    text = path.read_text()
    if old not in text:
        raise AssertionError(f'{path.name} does not contain {old!r}')
    path.write_text(text.replace(old, new))


class CommittedTree(unittest.TestCase):
    """The check over the tree as committed."""

    def test_the_committed_transcripts_agree_with_the_run(self):
        rc, out, err = run(ANNOTATIONS)
        self.assertEqual(rc, 0, f'the committed tree is red:\n{err}')
        self.assertNotIn('problem', err)

    def test_a_red_mode_is_reported_as_a_red_mode_not_as_drift(self):
        # The direction that matters: a mode disagreeing with its own
        # transcriptions is a different defect, and reporting it as a list of
        # stale `.md` files would be wrong in the direction that is hardest to
        # diagnose from the message alone. Driven by pointing the check at a
        # directory holding no annotations at all, which turns the mode red
        # rather than stubbing it.
        with tempfile.TemporaryDirectory() as empty:
            rc, _out, err = run(empty)
        self.assertEqual(rc, 2, 'a red mode must not be exit 1')
        self.assertIn('no transcript was compared', err)
        self.assertNotIn('quotes\n', err)

    def test_the_transcripts_this_branch_did_not_touch_are_still_found(self):
        # Not a claim about how large the corpus is -- that is a figure every
        # merge adding a transcript has to edit. The claim is that the corpus
        # reaches past the files this branch corrected, and it holds whichever
        # way a later merge moves the total.
        found, _p, _d, _u = C.scan(ANNOTATIONS)
        names = {rel for rel, _n, _pr, _line in found}
        for name in ALREADY_CURRENT:
            self.assertIn(name, names)

    def test_the_oracles_own_transcript_is_one_of_the_files_held(self):
        found, _p, _d, _u = C.scan(ANNOTATIONS)
        self.assertIn(ORACLE_FILE, {rel for rel, _n, _pr, _l in found})


class TheCorpusRefuses(unittest.TestCase):
    """The mutations. Each is a named failure, and none may pass quietly."""

    def test_a_summary_re_transcribed_with_a_clause_dropped_fails(self):
        with scratch(lambda d: edit(d / ORACLE_FILE,
                                    'decode identically, all 4',
                                    'decode identically')) as d:
            rc, _out, err = run(d)
        self.assertEqual(rc, 1)
        self.assertIn(f'{ORACLE_FILE}:', err)
        self.assertIn('and the run prints', err)

    def test_a_transcript_whose_prompt_is_deleted_fails(self):
        # The block stops being findable, so a check that only compared what it
        # found would report a clean run over a corpus one smaller. The summary
        # line is still there and is held by nothing.
        def drop_prompt(d):
            edit(d / 'ec-0x07d1-sites.md',
                 '$ python3 ec/tools/disasm8051.py --self-test\n...\n', '')
        with scratch(drop_prompt) as d:
            rc, _out, err = run(d)
        self.assertEqual(rc, 1)
        self.assertIn('no prompt above it at all', err)

    def test_a_transcript_whose_summary_is_deleted_fails(self):
        # Every remaining transcript is correct and the block now quotes
        # nothing: a `console` fence is written to quote a session, so a
        # summary it does not quote is one that was deleted.
        def drop_summary(d):
            path = d / 'ec-0x07d1-sites.md'
            path.write_text('\n'.join(
                l for l in path.read_text().splitlines()
                if not l.startswith('self-test passed')))
        with scratch(drop_summary) as d:
            rc, _out, err = run(d)
        self.assertEqual(rc, 1)
        self.assertIn('quotes no `self-test passed:` line at all', err)

    def test_an_empty_corpus_fails(self):
        # The vacuity guard, and the same one `disasm8051_oracle.py` applies to a
        # span its parser covers no row of. A corpus that matched nothing must
        # not pass: without this, renaming every transcript out of the scanned
        # directory would report the check working.
        #
        # Driven by deleting the summary lines too, so the mode stays green and
        # the guard is what answers. A directory holding no annotation at all
        # turns the *mode* red first and would exit 2 without reaching it --
        # still not a pass, but not the thing under test.
        def strip_transcripts(d):
            for path in d.glob('*.md'):
                kept = [l for l in path.read_text().splitlines()
                        if not l.startswith('self-test passed')]
                path.write_text('\n'.join(kept) + '\n')
        with scratch(strip_transcripts) as d:
            rc, _out, err = run(d)
        self.assertEqual(rc, 1, 'a corpus with no transcript must not pass')
        self.assertIn('no `disasm8051.py --self-test` transcript was found', err)
        self.assertIn('red run', err)

    def test_a_summary_with_no_prompt_at_all_is_reported_not_declined(self):
        # The distinction the three-way prompt scan exists for. A summary under
        # another tool's prompt is that tool's mode and is declined; the same
        # line with no prompt above it is claimed by nobody, and declining it
        # would pass a transcript that nothing holds.
        found, problems, declined = C.transcripts(
            '```console\nself-test passed: some other tool\n```\n')
        self.assertEqual(found, [])
        self.assertEqual([why for _n, why in declined], [])
        self.assertEqual([why for _n, why in problems], [C._NO_PROMPT])

    def test_an_indented_transcript_that_disagrees_is_still_refused(self):
        # The half of the guarantee that found-and-agrees does not cover: an
        # indented transcript that disagrees has to be refused. Widening the
        # reader has to widen the corpus *and* the comparison with it, or a
        # transcript nobody can see is a transcript nothing holds.
        with scratch(lambda d: (d / 'indented-transcript.md').write_text(
                '- a claim:\n\n'
                '  ```console\n'
                '  $ python3 ec/tools/disasm8051.py --self-test\n'
                '  self-test passed: and the rest of the run\n'
                '  ```\n')) as d:
            rc, _out, err = run(d)
        self.assertEqual(rc, 1, 'a stale indented transcript must not pass')
        self.assertIn('indented-transcript.md:', err)
        self.assertIn('and the run prints', err)


class FenceShapes(unittest.TestCase):
    """Which fences are read, not only which lines are held.

    Several files under `ec/annotations/` write fenced blocks inside list items
    and blockquotes, so a fence marker at column one is only one of the shapes
    the directory uses. A reader matching only that one would return nothing at
    all for the other two -- no transcript, no decline, no failure -- and a
    `console` transcript written inside a list item would drop out of the corpus
    with the run still green. That is the same quiet shrinkage the corpus-level
    guards exist to prevent, at the shape level rather than the file level, so
    the shapes are driven directly.
    """

    # One transcript body, in the three shapes it can be written in. The
    # asserted line is the run's own, with no indentation: the reader dedents a
    # block body by the prefix its opening marker carried, so an indented
    # transcript has to compare equal to the column-one one or it is not being
    # read at all, just found.
    BODY = 'self-test passed: and the rest of the run'
    PROMPT = '$ python3 ec/tools/disasm8051.py --self-test\n'

    def shapes(self):
        return (
            ('column one', '```console\n' + self.PROMPT + self.BODY + '\n```\n'),
            ('indented into a list item',
             '- a claim:\n\n  ```console\n  ' + self.PROMPT + '  ' + self.BODY
             + '\n  ```\n'),
            ('inside a blockquote',
             '> ```console\n> ' + self.PROMPT + '> ' + self.BODY + '\n> ```\n'),
        )

    def test_every_fence_shape_yields_the_same_single_transcript(self):
        for name, text in self.shapes():
            with self.subTest(shape=name):
                found, problems, declined = C.transcripts(text)
                self.assertEqual(problems, [], f'{name}: not found')
                self.assertEqual(declined, [], f'{name}: declined')
                self.assertEqual(len(found), 1, f'{name}: found {found!r}')
                self.assertEqual(found[0][2], self.BODY, f'{name}: body not dedented')


class Declines(unittest.TestCase):
    """The shapes this reader refuses, counted and never failed."""

    def test_a_shell_fence_naming_the_command_is_declined_not_failed(self):
        # `pd-index-geometry.md` 8.2 does exactly this. Editing it into a
        # transcript would be a fix to nothing, and the check must not ask for
        # one.
        _f, problems, declined = C.transcripts(
            '```sh\npython3 ec/tools/disasm8051.py --self-test\ncmp a b\n```\n')
        self.assertEqual(problems, [])
        self.assertEqual([why for _n, why in declined], [C._RECIPE])

    def test_a_summary_under_another_tools_prompt_is_that_tools_mode(self):
        _f, problems, declined = C.transcripts(
            '```console\n$ python3 ec/tools/pd_index_geometry.py --self-test\n'
            'self-test passed: the helper bodies match\n```\n')
        self.assertEqual(problems, [])
        self.assertEqual([why for _n, why in declined], [C._OTHER_MODE])

    def test_the_committed_tree_declines_are_the_two_shapes_it_documents(self):
        # Not a count of declines: the claim is that every decline the
        # committed tree produces is one this reader has a reason for, and that
        # the reasons are the documented ones. A new shape appearing is a red
        # run; an existing one being edited away is not this case's business.
        _f, _p, declined, _u = C.scan(ANNOTATIONS)
        self.assertTrue(declined, 'the committed tree has no declines to '
                                   'check the reasons against')
        for _rel, _n, why in declined:
            self.assertIn(why, (C._RECIPE, C._OTHER_MODE))


if __name__ == '__main__':
    unittest.main()
