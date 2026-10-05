#!/usr/bin/env python3
"""The one skip rule, held at each of the three readers that calls it (#769).

Its own file rather than cases in `test_grade_0751_isolation.py`, which is
several times this length and whose every append has been a merge conflict:
this is a suite about one question -- does each of the three readers actually
apply `skippable_row`, on a capture where each of them would not -- and it
stands in for nothing that suite already holds.

**Why it exists: one of the three was unprotected, and the way that was found
was by mutation rather than by reading.** `read_capture` and
`partition_capture_rows` each have cases that fail when their call to
`skippable_row` is deleted. `mark_labels_of` had none: deleting its call
failed no case in `test_grade_0751_isolation.py`, left
`measure_mark_provenance.py --self-test` exiting 0, and left that tool's own
run green -- because the fixture the preflight's cases share drops the same
rows by a second rule before the one under test is reached, so the assertion
was the same either way. That is the exact failure this suite's cases exist to
make impossible, and it is why the fixture below is *built* rather than copied
from a committed one: a committed fixture is free to hide the rule again the
moment a reader gains another filter, and nothing here would notice.

**The fixture is the operator's, and the reason the rule exists.** An operator
who wants a row not graded prefixes it with `#`, which is what
`skippable_row`'s own docstring says the `#` test is for. Commenting out a row
*of a mark* is the case that separates the two readers: a `#` annotation line
carries no `MARK` in its second field, so `mark_labels_of`'s branch below the
skip rule drops it anyway and the rule is not load-bearing there. Commenting out
a mark row puts `MARK` in the second field of a row that must not be graded,
and nothing but the skip rule stands between it and a label the notice would
print. The header is in the fixture for the two strict readers, which have no
`MARK` branch to hide behind.

Every fixture here is a `tempfile` file this checkout wrote. No EC is opened, no
register is read back and no capture is taken on the machine: the probes are
writes to a temporary file.
"""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    'grade', HERE / 'grade_0751_isolation.py')
grade = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grade)

MARK_TS = '2026-01-01T12:00:00.000+01:00'
MARK_LABEL = 'wrote 0x0751=0xA0'
MARK = f'{MARK_TS},MARK,,{MARK_LABEL}'


class SkipRuleAtEachReaderTests(unittest.TestCase):
    """One capture, three readers, one rule -- and the fixture is what makes
    each reader's call to it load-bearing rather than redundant.

    The four rows are a header, the commented-out mark, the mark itself, and a
    `#` annotation line that is *not* a commented row. The last is here so the
    fixture is a shape an operator would recognise rather than a purpose-built
    probe, and it earns its place by being the row the cases below show the
    two mark readers dropping for the *branch* rather than the rule.
    """

    ROWS = [
        'ts,addr,old,new',
        '#' + MARK,
        '# the operator noted the settle here',
        MARK,
    ]

    def capture(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / 'capture.csv'
        path.write_text(''.join(row + '\n' for row in self.ROWS))
        return str(path)

    # The rule at each reader, named after the reader rather than after the
    # test, because a suite that has to be read to find out which call site it
    # is holding is a suite whose answer moves when its cases are reordered.

    def test_mark_labels_of_drops_the_mark_the_operator_commented_out(self):
        # `mark_labels_of` itself rather than `existing_mark_labels` over it:
        # the preflight delegates, so the preflight's cases cannot say which of
        # the two lost the rule if it went. The row that must not come back is
        # named by its first field, which is what a commented row's is.
        path = self.capture()
        labels = grade.mark_labels_of(list(grade.capture_rows(
            path, errors='replace')))
        self.assertEqual(labels, [(MARK_TS, MARK_LABEL)])
        self.assertNotIn('#' + MARK_TS, [ts for ts, _ in labels])

    def test_the_preflight_does_not_list_the_mark_the_operator_commented_out(self):
        # The same rule one level up, through the published reader a watcher
        # asks at startup. It is the path the notice takes, so a rule that held
        # only at `mark_labels_of` would still let the notice print a label the
        # capture does not hold.
        self.assertEqual(grade.existing_mark_labels(self.capture()),
                         [(MARK_TS, MARK_LABEL)])

    def test_the_partition_does_not_refuse_the_mark_the_operator_commented_out(
            self):
        # The partition has no `MARK` branch either -- every row that reaches it
        # is a row `read_capture` would have graded -- so a commented mark comes
        # back as a *refused* row, which is the notice saying the grading will
        # not take a row that grades. Both halves, because a rule that dropped
        # it into `accepted` would satisfy neither.
        accepted, refused = grade.refused_capture_rows(self.capture())
        self.assertEqual(accepted, [(MARK_TS, MARK_LABEL)])
        self.assertEqual(refused, [])

    def test_a_capture_with_a_commented_mark_row_still_grades(self):
        # `read_capture`'s own rule, and the one the other two are written
        # against. Without it the commented row reaches `take_capture_row` and
        # the strict reader raises on a timestamp that opens with `#` -- which
        # is the whole harm the rule prevents, and the reason this catches the
        # rule rather than merely noticing it: a capture an operator annotated
        # would be *refused*, not mis-graded, and the refusal names a row they
        # never wrote.
        try:
            marks, changes = grade.read_capture(self.capture())
        except ValueError as e:
            self.fail(f'read_capture refused a capture whose only mark row is '
                      f'the live one: {e}')
        self.assertEqual([m.label for m in marks], [MARK_LABEL])
        self.assertEqual(changes, [])

    def test_the_fixture_reaches_each_reader_as_a_row_the_branch_would_keep(
            self):
        """Why this fixture and not the committed one, asserted rather than
        left in the docstring: the two rules that could drop the commented row
        are separated here.

        `mark_labels_of` drops a row twice over -- `skippable_row`, and then a
        `row[1] == "MARK"` branch. A `#` *annotation* line carries no `MARK` in
        its second field, so the branch drops it whatever the rule does, and a
        fixture made only of those cannot tell the two apart: a case written on
        one keeps passing when the rule it was written to hold is deleted. This
        asserts the property that makes the cases above meaningful -- over
        `capture_rows`, the commented *mark* is a row the branch below the rule
        would keep, so the rule is the only thing standing between it and a
        label, while the annotation line beside it is one the branch drops
        alone.

        If a future change to the row shape stops this holding, it fails here
        rather than quietly turning the cases above into assertions that are
        true for a second reason.
        """
        def survives_mark_branch(row):
            # `mark_labels_of`'s own test, restated rather than called: it is
            # three lines of that function's body and not a predicate of its
            # own, and a case that reached into it would hold nothing if the
            # body changed.
            return len(row) > 1 and row[1] == 'MARK'

        rows = list(grade.capture_rows(self.capture(), errors='replace'))
        commented = [row for row in rows if row and row[0] == '#' + MARK_TS]
        self.assertEqual(len(commented), 1,
                         'the fixture must hold exactly one commented mark row')
        self.assertTrue(grade.skippable_row(commented[0]),
                        'and it must be one the skip rule drops')
        self.assertTrue(survives_mark_branch(commented[0]),
                        'the branch alone must not drop it, or the case above '
                        'is true for a second reason')

        annotation = [row for row in rows
                      if row and row[0].startswith('#')
                      and row[0] != '#' + MARK_TS]
        self.assertEqual(len(annotation), 1)
        self.assertTrue(grade.skippable_row(annotation[0]))
        self.assertFalse(survives_mark_branch(annotation[0]),
                         'the annotation line is what the branch drops alone, '
                         'and it is why the committed fixture hides the rule')


class TheThreeReadersCallTheSameRuleTests(unittest.TestCase):
    """The claim the page rests on, at the level it is made at: one definition,
    three call sites, and no reader that can spell its own copy.

    Asserted as the property rather than as a count. What would be worth
    holding is that dropping the row is one rule's decision -- so that a reader
    that grew a second filter would have to disagree with the other two on
    some capture, which is the drift `skippable_row` was split out to stop
    (#548). The cases above are what hold each call; this one says the three
    answers are one answer.
    """

    def test_all_three_readers_agree_on_which_rows_a_capture_drops(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'capture.csv'
            path.write_text(''.join(row + '\n' for row in
                                    SkipRuleAtEachReaderTests.ROWS))
            labels = grade.existing_mark_labels(str(path))
            accepted, refused = grade.refused_capture_rows(str(path))
            marks, changes = grade.read_capture(str(path))
        # Compared as the label each reader names rather than as the timestamp
        # beside it: the two preflights hand back the timestamp as the text the
        # capture wrote and `read_capture` as a parsed `datetime`, so their
        # timestamps are not the same object and `isoformat()` is not the text
        # either -- it drops the milliseconds the preflights preserve. The label
        # is the part that identifies a mark to a reader of the notice.
        self.assertEqual([label for _, label in labels],
                         [label for _, label in accepted])
        self.assertEqual([label for _, label in labels],
                         [m.label for m in marks])
        self.assertEqual(refused, [])
        self.assertEqual(changes, [])


if __name__ == '__main__':
    unittest.main()
