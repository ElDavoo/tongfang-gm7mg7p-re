#!/usr/bin/env python3
"""What verify_gap_text.py claims about the sdas8051-declined instructions.

Issue #775 was filed against a red `--self-test`, and the pin behind that red
was `EXPECT_CHECKED` -- a hand-kept count of the whole instruction stream that
every listing export moved. That pin is gone, and `--self-test` and `--check`
are both green; the question the issue also asked, and the one still open, is
what holds them there. Nothing did. `--check` was in a patch that was prepared
and not landed (`docs/ci/agent-gates-gap-text-check.patch`), `--self-test` was
in no gate at all, and the red went unnoticed from #229 to #1498 for exactly
that reason. This file is the part of the answer that does not need a human to
apply a patch.

What it holds, and what it deliberately does not:

- **Both modes exit zero on the committed tree.** Run as subprocesses rather
  than called, so what is under test is the mode a reader reaches for --
  `python3 ec/tools/verify_gap_text.py --check` -- and not the functions
  behind it. `verify_gap_text.self_test()` drives `collect()` on its own tree
  already, and a suite that called the same functions would be the same
  coverage with a different caller.
- **The decline predicates, driven through `cross_listing()`.** The
  self-test names a reason by calling `why()` with arguments it chose; that
  proves `why()` maps an instruction to a reason, not that the walk over a
  listing reaches it. These go through the path `--check` uses, on a synthetic
  listing and a synthetic image, so a regression in the walk cannot hide behind
  a test that builds its own call. (This test suite now tests three declining
  forms; AJMP and ACALL are no longer declined as of issue #1727.)
- **A sixth form fails rather than joining silently.** The guarantee is only
  worth something if it is exercised, so it is: an exclusion no predicate
  explains has to surface in `unclassified`, and must not acquire a verdict.
- **The `row_name` join.** The one real defect in this tool's history was a
  CSV cell naming a function the listing index had renamed, which nothing
  noticed while `--check` was out of every gate. Asserting only that the
  committed report passes would leave that class of bug with no test at all,
  so this drives the failure the other way: one rewritten cell has to fail the
  check and be named.
- **That the readers of a listing agree on the census.** `EXPECT_INSTRUCTIONS`
  and every figure derived from it rest on `verify_reassembly.parse_listing()`
  reading the committed `.asm` files. More than one other module reads the same
  column by a rule of its own, and `opcode_coverage.listing_rows()` exists
  because a parser that quietly reads a third of a file reports no disagreement
  and looks like a pass. They agree here, on every listing and on every row;
  that is a claim about the committed disassembly rather than a count of this
  repository's text, so it is stated as an agreement rather than as a figure
  that goes stale on the next seeded listing. The claim is deliberately *not*
  that these are the only two, which would be an assertion about the tree's
  tool inventory; the two census readers are named because the census rests on
  them, and the rest because they can disagree about how many instructions a
  listing holds, which is the disagreement that would move a figure.

No assembler, no Ghidra, no hardware and no network: the two modes need none of
them, and the synthetic listings are decoded by `disasm8051.py` rather than by
anything installed. `--r2-diff` and the rest of `opcode_coverage.py`'s oracles
are out of scope here.
"""
import contextlib
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

import opcode_coverage                                             # noqa: E402
import counter_sweep_entry as S                                    # noqa: E402
import merge_annotation_shards as SH                               # noqa: E402
import pd_entry_forms as PE                                       # noqa: E402
import pd_no_ret_fallthrough as PN                                # noqa: E402
import reassembly_checked_bound as B                               # noqa: E402
import verify_gap_text as G                                        # noqa: E402
import verify_reassembly as V                                      # noqa: E402


def read_rows(path):
    """One CSV's rows, with the handle closed.

    `verify_reassembly.parse_listing()` grew a `with` for exactly this reason
    and three suites carry a comment about it: `verbosity=2` prints a
    `ResourceWarning` per unclosed handle, and a suite that adds its own to a
    shared tool's is a merge hazard on a file other branches are touching.
    """
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def victim_name():
    """The first row's `row_name` as committed, for the control case."""
    return read_rows(G.REPORT)[0]['row_name']


@contextlib.contextmanager
def quiet_shared_tool():
    """Filter the ResourceWarnings these calls raise on other modules' handles.

    `verify_gap_text.load_images()` and `collect()` open without a `with`, and
    `merge_annotation_shards._read()` does too, so calling any of them
    in-process prints one per handle at `verbosity=2`. Filtered here rather
    than fixed there: the handle is released when the reference drops, and a
    suite that widens its subject into someone else's file is the merge
    hazard the filter exists to avoid. The reader cases below are why it now
    covers a second module and not only this one's.
    """
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', ResourceWarning)
        yield


def run_mode(flag):
    """`python3 ec/tools/verify_gap_text.py <flag>`, as a reader runs it.

    A subprocess rather than a call, so the exit code under test is the one the
    shell sees. It is also slower than calling `G.self_test()` directly, and
    that is the trade being made on purpose: the gap this suite closes is that
    these two modes were reachable only by a human typing them, and a test
    that reached them the way its author reaches them would not have caught
    the mode being wired to the wrong function.
    """
    proc = subprocess.run([sys.executable, str(HERE / 'verify_gap_text.py'), flag],
                          capture_output=True, text=True, cwd=str(ROOT))
    return proc.returncode, proc.stdout + proc.stderr


def listing_rows(program=None):
    """Every `.asm` the committed listing index names, as a path.

    The index's own filter rather than a copy of it: some rows name no file (a
    region with no instructions) and a suite that walked them anyway would be
    testing an empty read. `program` narrows to one of the four the index
    names, because the directory-walking readers take a program rather than a
    file and comparing the two means comparing like with like.
    """
    for row in read_rows(V.LISTING_INDEX):
        rel = row['out_file']
        if not rel or rel.startswith('('):
            continue
        if program is not None and rel.split('/')[0] != program:
            continue
        path = os.path.join(V.DECOMPILED, rel)
        if os.path.isfile(path):
            yield path


def listing_programs():
    """The programs the committed listing index names, in its own spelling.

    Derived from the index rather than written out, for the same reason
    `listing_rows()` takes the index's own filter: a program the index stopped
    naming would otherwise be one this suite silently stopped checking, which
    is the failure it exists to catch.
    """
    return sorted({rel.split('/')[0]
                  for rel in (row['out_file'] for row in read_rows(V.LISTING_INDEX))
                  if rel and not rel.startswith('(')})


def walk_one(addr, hexbytes, text, image_len=0x10000):
    """`cross_listing()` over one synthetic listing, with an image to decode it.

    The image is a zeroed buffer with the listing's own bytes written at the
    listing's own address, so `disasm8051.mnemonic()` reads what the listing
    says rather than being handed the text. `image_len` covers the highest
    address any case below uses; a shorter one would let `cross_listing()`
    answer `undecodable` for want of bytes and quietly pass a case that was
    supposed to be about classification.
    """
    body = bytes.fromhex(hexbytes.replace(' ', ''))
    image = bytearray(image_len)
    image[addr:addr + len(body)] = body
    row = {'program': 'bank0', 'addr': '%04X' % addr, 'name': 'synthetic',
           'out_file': 'verify_gap_text.test.asm'}
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'synthetic.asm')
        with open(path, 'w') as f:
            f.write('%04x  %s -     %s\n' % (addr, hexbytes, text))
        return G.cross_listing(row, bytes(image), path)


# The three forms `to_sdas()` still declines across the committed listings, with
# the bytes disasm8051 decodes at each address. Byte columns and listing text are
# the 8051's, not this file's invention. The `djnz` is the set's single DJNZ
# direct, whose displacement is 0xA581 - 0xA59C = -27, or 0xE5. Each therefore
# reaches `agree` rather than a disagreement, which is the point: what is under
# test is which predicate declined it and that it was given a verdict at all, and
# a disagreement here would mean this suite had mis-transcribed an opcode.
# (AJMP and ACALL are no longer declined; they are now arbitrated via
# disasm8051.py in verify_reassembly.py.)
DECLINED = (
    ('mov-bit-carry', 0x0040, '92 d5', 'mov 0xd5, CY',
     'BIT_UNSUPPORTED 0x92'),
    ('cpl-bit', 0x0044, 'b2 d5',  'cpl 0xd5',       'BIT_UNSUPPORTED 0xB2'),
    ('djnz-direct', 0xA599, 'd5 e0 e5', 'djnz A, 0xa581',
     'GAP_FORMS "djnz a,"'),
)


class ModeTests(unittest.TestCase):
    """The two modes, on the committed tree, as the exit code a CI would read."""

    def test_self_test_exits_zero(self):
        code, out = run_mode('--self-test')
        self.assertEqual(code, 0, '--self-test failed on the committed tree:\n%s'
                         % out)

    def test_check_exits_zero(self):
        code, out = run_mode('--check')
        self.assertEqual(code, 0, '--check failed on the committed tree:\n%s'
                         % out)


class DeclinedFormTests(unittest.TestCase):
    """Each of the three forms, through the walk `--check` uses."""

    def test_each_declined_form_is_named_and_given_a_verdict(self):
        for name, addr, hexbytes, text, reason in DECLINED:
            with self.subTest(form=name):
                rows, unclassified, parsed, unchecked = walk_one(
                    addr, hexbytes, text)
                self.assertEqual(unclassified, [],
                                 '%s reached no verdict and no reason: %r'
                                 % (name, unclassified))
                self.assertEqual(len(rows), 1, '%s produced %d row(s)'
                                 % (name, len(rows)))
                self.assertEqual((parsed, unchecked), (1, 1),
                                 '%s: to_sdas() did not decline it' % name)
                self.assertEqual(rows[0]['reason'], reason)
                self.assertEqual(rows[0]['verdict'], 'agree',
                                 '%s: the image holds %r against the '
                                 "listing's %r, so this case is mis-transcribed"
                                 % (name, rows[0]['disasm_text'], text))

    def test_a_form_no_predicate_explains_is_reported_not_verdicted(self):
        # `sjmp label` is declined by to_sdas() -- it cannot read a symbolic
        # target and returns None rather than emitting a plausible line -- and
        # nothing in why()'s list explains why, because no committed listing
        # contains it. That is what a sixth form looks like from here, and the
        # whole point of the guard is that it arrives as a failure rather than
        # as one more instruction with a verdict nobody computed.
        rows, unclassified, parsed, unchecked = walk_one(
            0x0040, '80 0a', 'sjmp label')
        self.assertEqual((parsed, unchecked), (1, 1))
        self.assertEqual(rows, [], 'an unexplained exclusion was given a '
                                   'verdict instead of being reported')
        self.assertEqual(len(unclassified), 1)
        self.assertEqual(unclassified[0][5], 'label',
                         'the operand has to be named: a reader who cannot see '
                         'which form arrived cannot teach why() about it')


class CensusTests(unittest.TestCase):
    """What the tool's counts rest on, held as an agreement rather than a figure.

    `verify_gap_text.self_test()` already asserts that this tool's walk and
    `reassembly_checked_bound.py`'s reading of the committed report divide the
    instruction stream the same way. Re-asserting it here is not redundancy:
    that assertion runs only when someone types `--self-test`, which no gate
    does, and this suite is what puts it on every commit. The one leg added is
    `unchecked`, which the self-test holds against `EXPECT_INSTRUCTIONS` but
    never against the report's own column.

    Asserting the absolute figures instead would re-base them silently on
    every listing edit, which is the failure the constant's own comment
    records; asserting that independent readings of the same committed files
    agree does not move on any edit.

    The reader cases below do not stop at the pair the census rests on.
    `verify_reassembly` and `opcode_coverage` are those two; the rest are named
    because they are the ones that could move a figure without the census
    noticing -- a reader that quietly reads part of a listing and disagrees
    about nothing is indistinguishable from one that read all of it. Each gets
    its own case, because two readers can share a rule and a third cannot.
    """

    def test_both_listing_parsers_read_the_same_instructions(self):
        # Both find a listing's byte column by the same rule -- walk the
        # fixed-width slots, stop at the `-` padding or at a token that is not
        # a byte -- and then part company: `verify_reassembly.parse_listing()`
        # goes on to read the mnemonic after the padding and drops a row that
        # has bytes but no text, while `opcode_coverage.parse_listing()` never
        # looks at the text and keeps the row. So they could disagree on such a
        # listing, and there is none, which is what this asserts: the same
        # addresses, bytes and order for every listing, compared as full
        # sequences rather than as counts so a parser that dropped a row and
        # invented another could not pass.
        differing = []
        for path in listing_rows():
            mine = [(addr, bytes.fromhex(hexbytes))
                    for addr, hexbytes, _mnem, _ops in V.parse_listing(path)]
            theirs = opcode_coverage.parse_listing(path)
            if mine != theirs:
                differing.append(os.path.relpath(path, str(ROOT)))
        self.assertEqual(differing, [],
                         'the two parsers disagree on %d listing(s):\n  %s'
                         % (len(differing), '\n  '.join(differing)))

    def test_the_column_slicing_reader_reads_the_same_rows(self):
        # A third rule, and the only other whole-corpus reader that is not
        # keyed by program. `merge_annotation_shards.parse_listing()` takes the
        # columns at fixed offsets instead of walking the slots -- which is why
        # it exists, because a whitespace split reads a listing's own `da`
        # mnemonic as a fourth byte -- and it drops a row with no mnemonic the
        # way the census reader does. It reports no byte column, so this
        # compares the two things both of it reports and says so, rather than
        # pretending to a three-column agreement it cannot make.
        differing = []
        with quiet_shared_tool():
            for path in listing_rows():
                mine = [(addr, mnem)
                        for addr, _hexbytes, mnem, _ops in V.parse_listing(path)]
                theirs = [(int(addr, 16), mnem)
                          for addr, mnem, _ops in SH.parse_listing(path)]
                if mine != theirs:
                    differing.append(os.path.relpath(path, str(ROOT)))
        self.assertEqual(differing, [],
                         'the column-slicing reader disagrees with the census '
                         'reader on %d listing(s):\n  %s'
                         % (len(differing), '\n  '.join(differing)))

    def test_the_regex_reader_reads_the_same_rows(self):
        # A fourth rule, and the one that reads bytes by regex rather than by
        # position: `counter_sweep_entry.read_listings()` matches the byte
        # column out of a single `LINE_RE` and keys it by address. It walks a
        # program *directory* where the census reader walks the listing index,
        # so this asserts the two also agree on which files there are -- the
        # question a seeded listing answers. Called once per program rather
        # than per listing, which is the shape of its own API.
        differing = []
        for program in listing_programs():
            mine = [(addr, bytes.fromhex(hexbytes))
                    for path in listing_rows(program)
                    for addr, hexbytes, _mnem, _ops in V.parse_listing(path)]
            _starts, theirs = S.read_listings(program)
            # `(address, bytes)` on both sides, taken out of the dict rather
            # than compared as one: this reader also reports the listing's
            # text, and `dict.items()` would compare that against the census
            # reader's byte column, which is a column disagreement of zero
            # length and a failure message nobody could read.
            theirs_as_rows = [(addr, bytes(value[0]))
                              for addr, value in theirs.items()]
            if mine != theirs_as_rows:
                differing.append(program)
        self.assertEqual(differing, [],
                         'the regex reader disagrees with the census reader on '
                         'program(s): %s' % ', '.join(differing))

    def test_the_pd_restatements_agree_with_the_reader_they_restate(self):
        # `pd_no_ret_fallthrough.read_listings()` carries its own copy of the
        # regex `pd_entry_forms.read_listings()` uses, and says so -- "kept so
        # the two tools cannot disagree about what a committed listing says".
        # That is the same claim the cases above make, made in prose by another
        # module, and it is checkable: three copies of one pattern that have
        # never been compared against each other.
        #
        # Compared as a list of differing addresses rather than with
        # assertEqual, because the two shapes are deliberately different --
        # both pd readers carry the file each line came from and
        # `counter_sweep_entry`'s does not -- and assertEqual on two unequal
        # dicts of this size spends the failure budget in difflib rather than
        # in saying what differs. The file column is the evidence half of what
        # the pd tools report, so dropping it here is dropping the one column
        # that reader was never going to have.
        _starts, original = S.read_listings('pd')
        for module in (PE, PN):
            # `pd_no_ret_fallthrough` returns a third value -- the per-listing
            # head and last, which is what its `contiguous()` is measured
            # against -- so the dict is taken by position rather than unpacked.
            restated = module.read_listings()[1]
            self.assertEqual(list(restated), list(original),
                             '%s.read_listings() reads a different set of '
                             'addresses' % module.__name__)
            differing = [a for a in original
                         if restated[a][:2] != original[a]]
            self.assertEqual(differing, [],
                             '%s.read_listings() disagrees with the reader it '
                             'restates at %d address(es), first at %s'
                             % (module.__name__, len(differing),
                                hex(differing[0]) if differing else '-'))

    def test_the_walk_and_the_report_divide_the_stream_the_same_way(self):
        reach = B.census(B.read_report(), B.read_anchors())
        with quiet_shared_tool():
            _rows, unclassified, totals = G.collect()
        self.assertEqual(unclassified, [])
        # The unchecked leg is the one the self-test does not take: it holds
        # its count against EXPECT_INSTRUCTIONS, a known answer, and never
        # against the report's own `instructions_unchecked`.
        self.assertEqual(totals['unchecked'], reach['unchecked'],
                         'the walk and the report disagree on what to_sdas() '
                         'declines')
        self.assertEqual(totals['checked'], reach['checked'],
                         'the walk and the report disagree on what it accepts')
        self.assertEqual(totals['parsed'], reach['total'],
                         'the walk and the report disagree on the size of the '
                         'stream they divide')
        self.assertEqual(totals['parsed'],
                         totals['checked'] + totals['unchecked'])


class ReportJoinTests(unittest.TestCase):
    """`check()`'s join, driven so that a failure is shown to happen.

    Every other case here can only notice a defect that has already landed. A
    suite that asserts the committed report passes still says nothing about
    whether the check would have caught it going stale, and the one real
    incident in this tool's history -- a `row_name` cell naming a function the
    listing index had since renamed -- was invisible precisely because nothing
    ran the mode.
    """

    def rewrite_one_row_name(self, rewrite):
        """A temporary copy of the committed report with one cell rewritten.

        The committed CSV is never written. `verify_reassembly.refuses_committed_report()`
        exists to keep `reassembly.csv` single-writer, and this tool's own
        `--report` is the only thing that writes this one; a test that touched
        either would break the property it is not trying to test.
        """
        committed = read_rows(G.REPORT)
        self.assertTrue(committed, 'the committed report is empty')
        victim = committed[0]
        copy = committed[:]
        copy[0] = dict(victim, row_name=rewrite)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, 'gap-text-check.csv')
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=G.COLUMNS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(copy)
        return victim, path

    def call_check_against(self, path):
        """`check()` reading `path` as the report, with stdout captured."""
        original, G.REPORT = G.REPORT, path
        self.addCleanup(setattr, G, 'REPORT', original)
        buf = io.StringIO()
        with quiet_shared_tool():
            with contextlib.redirect_stdout(buf):
                code = G.check()
        return code, buf.getvalue()

    def test_a_rewritten_row_name_fails_the_check_and_is_named(self):
        victim, path = self.rewrite_one_row_name('renamed_by_this_suite')
        code, out = self.call_check_against(path)
        self.assertEqual(code, 1, '--check passed a report that disagrees '
                                   'with the live set:\n%s' % out)
        key = G.key(victim)
        self.assertIn(key, out, 'the failure did not name the row it is about')
        self.assertIn('renamed_by_this_suite', out,
                      'the failure did not report the value it found')
        self.assertIn(victim['row_name'], out,
                      'the failure did not report the value the live listing '
                      'index carries')

    def test_the_unmodified_copy_still_passes(self):
        # The control for the case above. Without it, a check that failed on
        # every input would satisfy that one, and the row_name assertion would
        # be asserting that the tool is broken. Rewriting a cell with the value
        # it already holds is what makes this a control: the copy is written
        # and read the same way, and nothing about it differs.
        _victim, path = self.rewrite_one_row_name(victim_name())
        code, out = self.call_check_against(path)
        self.assertEqual(code, 0, '--check failed on an unmodified copy of the '
                                   'committed report:\n%s' % out)

    def test_a_report_with_a_row_dropped_is_reported_stale(self):
        # The key-set half of the join, where the row_name case above is the
        # per-column half. A row removed from the report is a row the committed
        # file no longer describes, and `check()` says so by key rather than by
        # a count, which is why removing one is enough to be noticed.
        committed = read_rows(G.REPORT)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, 'gap-text-check.csv')
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=G.COLUMNS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(committed[1:])
        code, out = self.call_check_against(path)
        self.assertEqual(code, 1)
        self.assertIn(G.key(committed[0]), out)
        self.assertIn('has no row in', out,
                      'a dropped row has to be named as one the live set has '
                      'and the report does not')


if __name__ == '__main__':
    unittest.main()