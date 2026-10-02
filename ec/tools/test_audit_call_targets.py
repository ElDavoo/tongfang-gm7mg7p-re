#!/usr/bin/env python3
"""Give the region-bound check in `audit_call_targets.py --self-test` a runner.

`docs/findings/rel8-displacement-bound.md` closed its hand-off with the claim
that the `--self-test` line it added is what keeps it closed -- "if a future
image breaks `hi <= len(d)`, the suite says so" -- and that sentence named no
mechanism. This file is the mechanism, and it exists because the sentence was
wrong in a way a reader could not see: `--self-test` did run from another suite,
`test_relative_edge_guard.py`, but for #1093's region-edge window, and it
treats every other line of the transcript as fixture -- `unmoved by the plant`
is one of its cases -- so the bound line was covered only as a side effect of
that suite's subject and was named nowhere. A line covered by accident is a
line whose coverage ends when the accident does.

  * **the line, by name.** The invariant check is matched on the half of it
    that is the claim rather than the half that is a count, the same
    `EDGE_LINE` idiom `test_relative_edge_guard.py` uses for its own line, and
    a line that stops being printed is a red run here instead of a document
    quoting a check that is no longer there under the name it quotes. The
    fragment is short and stable on purpose: the whole sentence carries the
    image's length, so pinning it would make a wording change a red run.
  * **the invariant, as arithmetic.** `hi <= len(d)` is stated here where a
    failure names the suite rather than a tool's exit status, and against the
    table the bound comes out of rather than against a restated figure.
  * **the failure branch, run and seen to fire.** The `-- exceeded` text this
    change removes used to assert a counterfactual about `main()` from inside
    `main()`'s own callee. Deleting it on the strength of an argument would
    have been the wrong kind of change, so the case below measures the branch
    instead: a buffer one byte short of the largest audited bound reaches the
    check with its comparison false on this image, prints `FAIL`, and says
    nothing about `main()`. That is where the old text was reachable and wrong
    rather than unreachable -- nothing had refused the buffer, because `main()`
    was never called on that path. The reachability is one byte deep and the
    case below says which byte, rather than leaving it as a general claim about
    short buffers.

**What this suite pins, and what it does not.** It pins the invariant against
whatever is at `ec/firmware/GMxMGxx_11.800`. A second image landing beside that
one is not covered, and `rel8-displacement-bound.md` says so where the claim is
made; "a future image" is not broader than the path this names.

**No figure is written into an asserting call.** `check_doc_figure_pins.py`
reads every int constant inside a `check()` or the numeric half of `unittest`
across `ec/tools/*.py` as a pin for a figure in some document, so a bare number
here would silently become evidence for whichever write-up happens to cite it.
Every figure below is derived from `REGIONS` and `AUDITED` or compared by region
*name*.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
# audit_call_targets imports data_regions, disasm8051, find_banks and
# trace_xdata_refs by bare module name, so the tool directory has to be on the
# path before it is loaded rather than after -- the shape
# test_earlier_record_column.py and test_relative_edge_guard.py use for the
# same reason.
sys.path.insert(0, str(HERE))

import trace_xdata_refs

_spec = importlib.util.spec_from_file_location(
    "audit_call_targets", HERE / "audit_call_targets.py")
act = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(act)

FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"

# The claim rather than the count, the way `EDGE_LINE` is in
# test_relative_edge_guard.py. A rename of the line is a red run here.
BOUND_LINE = "the largest audited region bound"

# What check() prefixes an honest line with, and what it prefixes a broken one
# with. Named so a case reads as "which of the two did it see" rather than
# spelling the indentation out at each use.
OK_PREFIX = "  ok "
FAIL_PREFIX = "  FAIL "

# The exit status self_test() returns when every check holds. A module-level
# constant rather than a literal in the asserting call for the reason the
# docstring gives: check_doc_figure_pins.py reads an int constant there as a
# figure pin.
PASSED = 0

# The region whose bound is the largest of the audited ones, by name. The
# write-up argues the bound is a table read rather than anything about the
# buffer, and this is that claim stated the way it can be checked -- against
# the name in the table, not against a restated address.
LARGEST = "bank1"


def run_self_test(d):
    """`--self-test` over `d`, as (exit status, the lines it printed).

    `self_test()` raises rather than returning on a buffer shorter than the
    region walks can serve, and the transcript is read out of the buffer as it
    stands at that raise: `redirect_stdout` has already taken every line
    printed before it, which is the whole of why the transcript below can be
    compared against a committed run. A `None` status is a raise, not a
    failure count.
    """
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            status = act.self_test(d)
    except IndexError:
        status = None
    return status, buf.getvalue().splitlines()


def bound_line_of(lines):
    """The bound check's line out of a `--self-test` transcript, or ""."""
    return next((line for line in lines if BOUND_LINE in line), "")


def bound_of(line):
    """The hex bound a transcript line carries, or "".

    The token immediately after the claim, which is the number the sentence is
    about; the image's length beside it is the half that does move with the
    buffer. "" on a line that carries neither, so a comparison below fails on
    an empty operand rather than passing on two of them.
    """
    if BOUND_LINE not in line:
        return ""
    words = line.split(BOUND_LINE, 1)[1].split()
    return words[0] if words else ""


def one_byte_short():
    """The length of a buffer the CLI path cannot produce but a direct caller
    can hand self_test(): one byte below the largest audited bound.

    Derived from the table rather than written down, so a region map that
    moved would move this with it.
    """
    return max(act.region_bounds(n)[1] for n in act.AUDITED) - 1


class TheRegionBoundIsReported(unittest.TestCase):
    """The `hi <= len(d)` line, which this file is the runner that
    `rel8-displacement-bound.md`'s hand-off named and did not have."""

    def setUp(self):
        # A missing image is a failure rather than a skip. `tools/run-tests.sh`
        # treats an empty discovery as a failure for the same reason, and a
        # suite that quietly stops running is the failure mode both name.
        if not FIRMWARE.is_file():
            self.fail(f'{FIRMWARE} is not there. Every case in this file reads '
                      'the committed image; nothing here can be measured '
                      'without it, and a skip would hide that.')
        self.image = FIRMWARE.read_bytes()

    def test_the_bound_line_is_printed_and_holds_over_the_committed_image(self):
        # The runner. A line that stops being printed reddens this case, which
        # is stronger than the sentence it replaces ever could have been: that
        # sentence named a suite without naming a check.
        status, lines = run_self_test(self.image)
        line = bound_line_of(lines)
        self.assertIn(BOUND_LINE, line,
                      f'no --self-test line carries {BOUND_LINE!r}; the '
                      f'transcript was:\n' + '\n'.join(lines))
        self.assertTrue(line.startswith(OK_PREFIX), line)
        self.assertEqual(status, PASSED, line)

    def test_the_bound_is_the_regions_tables_own_and_not_a_function_of_the_buffer(self):
        # `region_bounds()` is a `next()` over REGIONS and nothing else, so the
        # bound the check reports is the largest audited `hi` in that table.
        # Compared to the table rather than to a number, so this is the
        # structural fact the write-up argues from and not a pinned figure.
        from_bounds = max(act.region_bounds(n)[1] for n in act.AUDITED)
        from_table = max(hi for n, _lo, hi, _base, _ in trace_xdata_refs.REGIONS
                         if n in act.AUDITED)
        self.assertEqual(from_bounds, from_table)
        supplying = [n for n, _lo, hi, _base, _ in trace_xdata_refs.REGIONS
                     if n in act.AUDITED and hi == from_table]
        self.assertEqual(supplying, [LARGEST])

    def test_the_bound_does_not_move_with_the_buffer(self):
        # The other half of the same sentence, and the one `hi` being a table
        # read actually buys: a buffer shorter than the bound carries the same
        # bound as the committed image, with only the image's length beside it
        # moving. Both transcripts are read rather than recomputed, so this
        # says what the tool printed and not what a reading of the tool would
        # have printed.
        _status, whole = run_self_test(self.image)
        _short, cut = run_self_test(self.image[:one_byte_short()])
        self.assertTrue(bound_of(bound_line_of(whole)),
                        'the committed transcript carried no bound to compare')
        self.assertEqual(bound_of(bound_line_of(cut)),
                         bound_of(bound_line_of(whole)),
                         'the bound moved with the buffer')
        self.assertNotEqual(bound_line_of(cut), bound_line_of(whole),
                            'the sentence did not move with the buffer either, '
                            'so the half above was not read off a transcript '
                            'that stayed the same')

    def test_the_invariant_holds_against_the_committed_image(self):
        # The assertion the check line makes, stated where a failure names
        # this suite rather than the tool's exit status.
        hi = max(act.region_bounds(n)[1] for n in act.AUDITED)
        self.assertLessEqual(hi, len(self.image))

    def test_the_failure_clause_fires_and_claims_nothing_about_main(self):
        # The other direction, and the reason the `-- exceeded` text could go.
        # It named what main() would have done about a buffer that broke the
        # bound; on this path main() was never called, so nothing had refused
        # anything and the walk below raised. Running the branch is what makes
        # deleting the claim a measurement rather than an argument.
        #
        # There is one byte of slack in this and it is worth naming:
        # `paged_sites()` reads an operand at `d[i + 1]` for every offset it
        # admits, and the last one it admits on a buffer this short is the
        # buffer's last index. This image's is not paged-shaped, so the walk
        # gets past it and the check is reached; a dump whose top byte were
        # would raise there first and redden this case, which is the ordering
        # the case is testing rather than a fluke it would be happy to pass.
        status, lines = run_self_test(self.image[:one_byte_short()])
        line = bound_line_of(lines)
        self.assertTrue(line.startswith(FAIL_PREFIX),
                        'the failure clause did not fire, so nothing was '
                        'measured about what it says')
        self.assertNotIn("main()", line)
        # And the walk after it is what refuses the buffer, not a caller.
        self.assertIsNone(status)


if __name__ == '__main__':
    unittest.main()