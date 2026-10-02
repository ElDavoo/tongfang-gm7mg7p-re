#!/usr/bin/env python3
"""Offline checks for `cross_decoder_sample()`'s selection rule.

`build_ec_decompile.py --self-test` already holds the rule against the sample
it returns on the committed tree: every stride row is reachable from its own
`(program, addr)`. What is here is the part a self-test cannot reach, because
it needs the sample *twice* — once as committed and once with an annotation
that is not there yet.

**The property is issue #648's.** The stride half used to be
`rest[::CROSS_DECODER_STRIDE]` over the sorted unannotated remainder, and the
backbone is a subset of the same list, so one added annotation removed one
element and shifted every later index: adding a single unrelated row moved
most of the sample onto different addresses and changed their verdicts. The
sampler now selects on a stable hash of the row instead, so membership is a
function of `(program, addr)` alone and an annotation moves at most the row it
names. That is asserted here as a relation between two derivations over the
same tree, not as a count.

**The negative control is the half that makes case one worth anything.** The
same property, run against the positional rule this replaced, has to *fail* —
and by a wide margin rather than by one row, since a control that failed by
one would pass just as well against a rule that merely shifts a little. The
house pattern is `test_cross_decoder_disagreement.py` and
`test_findings_4o_correction.py`: a guard exercised only on its positive case
cannot tell "the rule holds" from "the data was like that anyway".

**Nothing here asserts a count of the tree.** The sample's size follows from
the annotation layer, and a test that pinned it would be a number every merge
that annotates a function has to edit — the `CLAUDE.md` rule, and the reason
the churn being measured here is worth this suite at all. The figures belong
in `docs/findings/cross-decoder-sample-stability.md`, beside the derivation
that produced them.

**The two derivations are the real ones, not re-implementations.** "Before"
is `cross_decoder_sample()` itself, read off the committed annotations.
"After" is that rule over a backbone one row larger, which is the same
selection the tool performs and differs only in the annotation set — a case
that re-derived the rule from scratch here would be testing the copy.
"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import build_ec_decompile as bld


def listing_keys():
    """Every (program, addr) the listing index carries."""
    return {(r["program"], r["addr"])
            for r in bld.read_index(bld.LISTING_INDEX)}


def backbone():
    """The annotated half, as the sample derives it."""
    return {bld.annotation_key(r) for r in bld.annotation_rows()} & listing_keys()


def sample_keys():
    """The sample as committed. -> {key: how it was sampled}."""
    return {(r["program"], r["addr"]): kind
            for r, kind in bld.cross_decoder_sample()}


def stride_keys():
    """The stride half as committed, as a set."""
    return {key for key, kind in sample_keys().items() if kind == "stride"}


def firsts_per_program(keys):
    """Each program's first listing row, as `cross_decoder_sample()` takes it."""
    out = {}
    for key in sorted(keys):
        out.setdefault(key[0], key)
    return out


def sample_over(rows):
    """`cross_decoder_sample()`'s own output, over annotation `rows`.

    The tool's real function, called with its annotation source varied and
    nothing else -- `annotation_rows()` is the only seam that reaches the
    annotation set, and `cross_decoder_sample()` is what the report is derived
    from. Every stability case below goes through this rather than through a
    copy of the selection rule, because a case that re-derived the rule would
    keep passing against a sampler that had been reverted: the copy would still
    be the fixed one. That is the whole reason this is worth a helper.
    """
    with mock.patch.object(bld, "annotation_rows", return_value=rows):
        return {(r["program"], r["addr"]): kind
                for r, kind in bld.cross_decoder_sample()}


def annotation_row(key):
    """A minimal annotation row for `key`, in the CSV's own spelling.

    Only `scope` and `addr` reach `annotation_key()`, which is all
    `cross_decoder_sample()` reads; the rest of the columns exist so a row
    that grew a consumer would not silently read an empty field.
    """
    return {"scope": key[0], "addr": key[1], "name": "sample_stability_fixture",
            "signature": "", "type": "unresolved",
            "comment": "synthetic row, added by "
                       "ec/tools/test_cross_decoder_sample.py",
            "evidence": "ec/decompiled/%s/%s.asm" % key}


def positional_stride(bb):
    """The rule this replaced, verbatim, on the same inputs. -> set of keys."""
    keys = listing_keys()
    rest = sorted(keys - bb)
    picked = set(rest[::bld.CROSS_DECODER_STRIDE])
    picked |= set(firsts_per_program(keys).values()) - bb
    return picked


def one_per_program_remnant(bb=None):
    """One unannotated row per program that has a remainder. -> [(prog, key)].

    One per program rather than one in the whole tree, because the stride half
    is not spread evenly over the four: a case that annotated the same program
    every time would measure one program's behaviour and call it the rule's.
    """
    bb = backbone() if bb is None else bb
    seen = {}
    for key in sorted(listing_keys() - bb):
        seen.setdefault(key[0], key)
    return sorted(seen.items())


class Stability(unittest.TestCase):
    """Adding one annotation does not move the rest of the sample.

    Every case here derives both samples through `sample_over()`, which calls
    `cross_decoder_sample()` itself with a synthetic annotation added. Reverting
    the sampler to the positional rule turns these red, which is what makes
    them worth having.
    """

    def stride_over(self, extra=()):
        rows = bld.annotation_rows() + [annotation_row(key) for key in extra]
        return {k for k, kind in sample_over(rows).items() if kind == "stride"}

    def test_the_stride_half_is_unchanged_by_an_unrelated_annotation(self):
        """The issue's "every row keeps its verdict across an unrelated
        annotation", as a property over sets.

        The comparison is between the two *stride halves*, not between the two
        samples: the annotated row leaves the stride half by becoming an
        `annotation` row, which is correct and is what the `sample` column
        means. Asserting over the whole sample instead would fail on the row
        that was annotated and pass on one that was retired, which is the
        opposite of the claim.
        """
        for program, victim in one_per_program_remnant():
            with self.subTest(program=program):
                before = self.stride_over()
                after = self.stride_over([victim])
                # The annotated row is the only one allowed to leave, and
                # nothing is allowed to arrive: a row joining the stride half
                # would be the sample re-phasing in the other direction.
                self.assertEqual(after - before, set())
                self.assertEqual(before - after - {victim}, set())

    def test_a_sampled_row_keeps_its_label(self):
        """The `sample` column, not just membership.

        That column is what a reader treats as "nobody has read this one yet",
        so a row that silently changed it would be a claim about a function
        made by the sampler rather than by anyone who read the function.
        """
        for program, victim in one_per_program_remnant():
            with self.subTest(program=program):
                before = sample_over(bld.annotation_rows())
                after = sample_over(bld.annotation_rows()
                                    + [annotation_row(victim)])
                for key, kind in before.items():
                    if key != victim:
                        self.assertEqual(after[key], kind, "%s %s" % key)
                self.assertEqual(after[victim], "annotation")

    def test_it_holds_for_stride_rows_and_not_only_for_the_rows_picked(self):
        """It holds for the whole stride half, not for four chosen rows.

        A property that four hand-picked rows satisfy and the rest do not is a
        fact about those rows. Sampled rather than exhaustive so a run stays
        quick; the stride half is spread through the remainder, so this samples
        across every program rather than taking one end of one list.
        """
        victims = sorted(stride_keys())
        self.assertTrue(victims, "no stride row to annotate, so nothing is tested")
        before = self.stride_over()
        step = max(1, len(victims) // 16)
        for victim in victims[::step]:
            with self.subTest(victim=victim):
                after = self.stride_over([victim])
                self.assertEqual(before - after - {victim}, set())
                self.assertEqual(after - before, set())

    def test_the_first_row_fallback_does_not_re_anchor(self):
        """The fallback's own half of the stability property.

        A first row is the program's *lowest listing address*, not its lowest
        unannotated one, so annotating it does not promote the next row into
        the fallback -- which is why a stride row can be lost by being
        annotated and one can never be gained. Asserted because the fallback
        is the one clause that could plausibly re-phase the sample on its own:
        had it been the lowest *unannotated* row, every annotation in a program
        would have moved it, and the property above would have been true only
        for the rows that happened not to be a program's first.
        """
        keys = listing_keys()
        bb = backbone()
        for program, victim in sorted(firsts_per_program(keys).items()):
            if victim in bb:
                continue
            with self.subTest(program=program):
                after = sample_over(bld.annotation_rows()
                                    + [annotation_row(victim)])
                next_up = sorted(k for k in keys
                                 if k[0] == program and k > victim)[:1]
                for key in next_up:
                    self.assertNotEqual(after.get(key), "stride")


class ThePositionalRuleItReplaced(unittest.TestCase):
    """The negative control: the rule this replaced fails those properties."""

    def test_it_loses_rows_an_annotation_did_not_name(self):
        for program, victim in one_per_program_remnant():
            with self.subTest(program=program):
                before = positional_stride(backbone())
                after = positional_stride(backbone() | {victim})
                self.assertNotEqual(before - after - {victim}, set())

    def test_it_loses_most_of_itself_not_a_row_or_two(self):
        """A control that failed by one row would not be a control.

        A rule that merely shifted slightly would also fail the case above, so
        the margin is asserted too: the positional rule loses a large share of
        its own stride rows to a single annotation, and that share is what
        makes the new rule's zero a measurement rather than an accident of this
        tree. Bounded rather than asserted as a count — the claim is "most of
        it", and the exact figure belongs in the write-up.
        """
        bb = backbone()
        before = positional_stride(bb)
        worst = max(len(before - positional_stride(bb | {victim}) - {victim})
                    for victim in sorted(before))
        self.assertGreater(worst, len(before) // 2,
                           "the control barely moved, so the positive case "
                           "above is not measuring the change")

    def test_it_moves_the_sample_in_every_program_that_has_a_remainder(self):
        """Not one program's behaviour standing in for the rule's."""
        bb = backbone()
        before = positional_stride(bb)
        for program, _victim in one_per_program_remnant(bb):
            victim = sorted(k for k in before if k[0] == program)
            if not victim:
                continue
            with self.subTest(program=program):
                after = positional_stride(bb | {victim[0]})
                self.assertNotEqual(before - after, before)


class TheKey(unittest.TestCase):
    """What the selection is a function of, and of what it is not."""

    def test_every_stride_row_is_the_bucket_or_the_first_row_fallback(self):
        """The rule's own two clauses, over the rows the rule selected.

        Not "every stride row is in bucket zero": a program's first row is a
        stride row whether or not its bucket is zero, and that fallback is the
        reason a program with a tiny remainder is covered at all. Asserted as
        the disjunction rather than as the bucket alone because the two clauses
        are what the rule says, and a case that only checked one would pass
        against a sampler that had lost the other.
        """
        firsts = set(firsts_per_program(listing_keys()).values())
        for key in sorted(stride_keys()):
            with self.subTest(key=key):
                self.assertEqual(bld.cross_decoder_bucket(key) == 0 or key in firsts,
                                 True)

    def test_the_bucket_clause_selects_more_than_the_fallback_could(self):
        """The fallback is not doing the work on its own.

        A sampler whose fallback supplied every stride row would satisfy the
        case above -- four rows, one per program -- and sample nothing else,
        which is the degenerate sample `degenerate_sample_problems()` exists to
        catch one shape up. The fallback can contribute at most one row per
        program, so a stride half larger than the program count cannot have
        come from it alone. That is the relationship; the size itself is the
        run's to report.
        """
        firsts = set(firsts_per_program(listing_keys()).values())
        by_bucket = stride_keys() - firsts
        self.assertTrue(by_bucket, "every stride row is a first-row fallback")
        self.assertGreater(len(by_bucket),
                           len({k[0] for k in listing_keys()}))

    def test_the_two_halves_are_disjoint(self):
        """One label per row, and a row is never both.

        The reading this rules out is a row that is annotated *and* reads
        "nobody has read this one" — which is what `setdefault` would produce
        if the halves were unioned rather than labelled. The label sets are
        compared as sets because a single key in both would make the union
        smaller than the sample.
        """
        sample = sample_keys()
        annotated = {key for key, kind in sample.items() if kind == "annotation"}
        stride = {key for key, kind in sample.items() if kind == "stride"}
        self.assertEqual(annotated & stride, set())
        self.assertEqual(annotated | stride, set(sample))

    def test_the_key_is_not_the_salted_builtin(self):
        """A `hash()` here would silently pass every other case in this suite.

        `hash()` of a tuple of strings is stable within one process, so the
        membership cases above would all still hold; what it would not survive
        is being run twice. Held against the key's own derivation rather than
        by importing `hash` and comparing, so the failure names the mechanism
        rather than a coincidence.
        """
        for key in sorted(listing_keys()):
            with self.subTest(key=key):
                self.assertEqual(bld.cross_decoder_bucket(key),
                                 zlib.crc32(("%s:%s" % key).encode())
                                 % bld.CROSS_DECODER_STRIDE)

    def test_the_key_does_not_depend_on_what_was_asked_before_it(self):
        """A function of the row alone, asked in two orders.

        The question a reader actually has about a sampler is whether its
        answer depends on anything but the row, and asking twice in the same
        order cannot see an answer that depends on the order.
        """
        forward = {k: bld.cross_decoder_bucket(k)
                   for k in sorted(listing_keys())}
        backward = {k: bld.cross_decoder_bucket(k)
                    for k in sorted(listing_keys(), reverse=True)}
        self.assertEqual(forward, backward)

    def test_the_bucket_is_a_range_the_stride_can_be_a_fraction_of(self):
        for key in sorted(listing_keys()):
            bucket = bld.cross_decoder_bucket(key)
            with self.subTest(key=key):
                self.assertIsInstance(bucket, int)
                self.assertGreaterEqual(bucket, 0)
                self.assertLess(bucket, bld.CROSS_DECODER_STRIDE)

    def test_the_key_spreads_rather_than_piling_into_one_bucket(self):
        """A key that put every row in one bucket would pass everything above.

        The stability property is what a one-bucket key is *for* — it is
        stable — so nothing else in this file would notice a rule that stopped
        sampling. Held as a relationship between the eight buckets rather than
        as any one bucket's size, so it survives a change of key: every bucket
        has to carry some of the remainder, and no bucket more than a multiple
        of what an even split would give.
        """
        rest = sorted(listing_keys() - backbone())
        counts = [sum(1 for key in rest if bld.cross_decoder_bucket(key) == n)
                  for n in range(bld.CROSS_DECODER_STRIDE)]
        self.assertTrue(all(counts), "a bucket carries none of the remainder: "
                                     "%r" % counts)
        mean = sum(counts) / float(len(counts))
        for n, count in enumerate(counts):
            with self.subTest(bucket=n):
                self.assertLess(count, mean * 2)


class Verdicts(unittest.TestCase):
    """A sampled function's verdict is about its bytes, not its membership."""

    def test_a_row_sampled_under_both_rules_reads_the_same_outcome(self):
        """The claim the write-up rests on, measured rather than argued from a
        signature.

        `compare_function()` takes no `kind` argument, so a row's cells are a
        function of its listing row and its firmware bytes. That is a fact
        about a signature, and this is the same fact measured over the rows
        both rules sample: it is what makes re-sampling the report a move of
        *which* rows are recorded rather than of what any of them says.
        """
        bb = backbone()
        both = stride_keys() & positional_stride(bb)
        self.assertTrue(both, "no row is sampled by both rules, so this is vacuous")
        committed = {(r["program"], r["addr"]): r
                     for r in bld.read_index(bld.CROSS_DECODER)}
        listing = {(r["program"], r["addr"]): r
                   for r in bld.read_index(bld.LISTING_INDEX)}
        with open(bld.FIRMWARE, "rb") as f:
            fw = f.read()
        for key in sorted(both & set(committed)):
            with self.subTest(key=key):
                outcome = bld.compare_function(
                    key[0], int(key[1], 16), int(listing[key]["size"]),
                    listing[key]["out_file"], fw)[0]
                self.assertEqual(outcome, committed[key]["outcome"])


class NoRegression(unittest.TestCase):
    """The rest of the comparison still means what it meant."""

    def test_build_ec_decompiles_self_test_still_passes(self):
        with tempfile.TemporaryDirectory() as work:
            proc = subprocess.run(
                [sys.executable, str(HERE / 'build_ec_decompile.py'),
                 '--work', work, '--self-test'],
                capture_output=True, text=True, cwd=str(HERE.parent.parent))
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("all assertions passed", proc.stdout)

    def test_the_outcome_vocabulary_is_held_by_name(self):
        self.assertEqual(set(bld.CROSS_DECODER_SAMPLES), {"annotation", "stride"})
        self.assertEqual(bld.CROSS_DECODER_OUTCOMES,
                         ("agree", "disagree", "vacuous", "no-export"))

    def test_every_program_is_represented_in_the_sample(self):
        # A consequence of the backbone rather than of the bucket, and the one
        # coverage guarantee this sample makes. It is what the change had to
        # keep: a hash over addresses could in principle have left a program
        # with a large remainder unrepresented.
        self.assertEqual({p for p, _ in sample_keys()},
                         {"bank0", "bank1", "common", "pd"})

    def test_stride_rows_come_only_from_the_remainder_or_the_fallback(self):
        """`pd`'s listing rows are all annotated, so it has no stride rows.

        Held as the property rather than as a fact about `pd`, because it reads
        as a gap in the sample and is not one the sampler can close: under any
        key, an empty remainder selects nothing, and the fallback cannot add a
        row either because `setdefault` will not demote an annotated one. A
        program that later gains a remainder satisfies the same assertion, so
        this does not go red on the tree moving under it.
        """
        keys = listing_keys()
        bb = backbone()
        firsts = set(firsts_per_program(keys).values())
        for program in sorted({p for p, _ in keys}):
            listed = {k for k in keys if k[0] == program}
            remainder = listed - bb
            first = {k for k in firsts if k[0] == program} - bb
            expected = {k for k in remainder
                        if bld.cross_decoder_bucket(k) == 0} | first
            with self.subTest(program=program):
                self.assertEqual(
                    {k for k in stride_keys() if k[0] == program}, expected)

    def test_each_sidecar_carries_exactly_the_report_s_rows(self):
        # Both sidecars read the parent's rows rather than re-deriving the
        # sample, so a report regenerated under the new rule carries them with
        # it and nothing else has to know the rule changed. Asserted as a
        # key-set identity in both directions rather than as a count, for the
        # reason the sibling suites give.
        for module, path_name in (("cross_decoder_blindness", "BLINDNESS"),
                                  ("cross_decoder_disagreement", "DISAGREEMENT")):
            with self.subTest(tool=module):
                spec = importlib.util.spec_from_file_location(
                    module, HERE / (module + ".py"))
                tool = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tool)
                parent = [(r["program"], r["addr"])
                          for r in bld.read_index(bld.CROSS_DECODER)]
                sidecar = [(r["program"], r["addr"])
                           for r in bld.read_index(getattr(tool, path_name))]
                self.assertEqual(sidecar, parent)


if __name__ == "__main__":
    unittest.main()