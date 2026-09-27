#!/usr/bin/env python3
"""The refusal contract and the structural shape of
`ec/annotations/data-regions.yaml` (issue #50).

`data_regions.py --self-test` holds the same refusals as a run of its own, and
this suite exists because a `--self-test` is a thing a person runs and this is
a thing `tools/run-tests.sh` collects. Both read the committed image and the
committed YAML, so they cannot disagree about which refusals exist.

**Neither is in the committed `.github/scripts/agent-gates.sh`, and the reason
is that a branch cannot edit it** — it is a template copy and the push token has
no `workflow` scope, so a branch editing it fails at the end of the PR. That is
not an unwritten state: `--check` and `--self-test` fold into the prepared
`docs/ci/agent-gates-disasm8051-self-test.patch`, per the collision table in
`docs/findings/prepared-gate-patches.md`, and all four of that patch's strings
are in `ArmRetentionTests.REQUIRED` in `tools/test_agent_gates_patches.py` so a
re-cut that lands one tool's halves and drops this one's goes red. This suite
is the ungated check that runs today, not the whole of the checking.

**What is deliberately not here.** No case asserts that a region *means*
anything. `data_regions.yaml` records extent, stride and shape; what a dispatch
table dispatches to is not in it, and `bank-call-audit.md` §5's 140 sites stay
`None` on the strength of `trace_xdata_refs.offset_for_runtime()`'s
same-bank assumption, which none of this touches. A test that said "0x055DC is
a table entry" would be asserting a reading; what is asserted is that the
bytes at the declared offset and stride are the bytes the file says, which is
a fact.

**Every mutation case is written against the error it is meant to catch**, and
each was run once with the mutation in place to confirm it goes red. Two of
them are the mistakes issue #50 itself made — `0x6940` for `0x690B` and
`0x6E78` for `0x6E65` — because the file this suite guards was written by
someone who read those addresses off a scan site, and a check that cannot catch
the mistake its own provenance is full of is not much of a check.
"""
import copy
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).parent
EC = HERE.parent
REPO = EC.parent
TOOL = HERE / "data_regions.py"
REGIONS_YAML = EC / "annotations" / "data-regions.yaml"
FIRMWARE = EC / "firmware" / "GMxMGxx_11.800"

spec = importlib.util.spec_from_file_location("data_regions", TOOL)
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)


def write_yaml(regions) -> str:
    """A throwaway YAML file holding `regions`, for the refusal cases."""
    fh = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    yaml.safe_dump({"regions": regions}, fh)
    fh.close()
    return fh.name


class RegionFileTests(unittest.TestCase):
    """The committed file's structure, and the numbers it declares.

    Reads `FIRMWARE` once for the class. It is a committed input and this is
    static analysis of it: no capture is opened, no EC is opened, and nothing
    here is evidence about the laptop.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.regions = dr.load(str(REGIONS_YAML))
        cls.by_name = {r["name"]: r for r in cls.regions}

    # --- the structure ----------------------------------------------------

    def test_the_file_carries_the_calibration_caveat(self):
        # The file is a record of one method's findings, so the "a zero is not
        # found, never absent" rule is the one that governs it most. Asserted
        # here because it is the sentence a future editor most plausibly drops
        # to save a line, and its absence is invisible in a diff.
        #
        # Matched on short phrases that survive the header's line wrapping
        # rather than whole sentences: this file is hand-edited, so pinning
        # the exact wording of a paragraph would turn an ordinary rewrap into
        # a red suite, and a test that punishes rewrapping is a test that gets
        # deleted rather than fixed.
        head = REGIONS_YAML.read_text().split("regions:")[0]
        for phrase in ('never "absent."',
                       "not a claim that the",
                       "HALF-OPEN",
                       "FILE OFFSETS",
                       "record of *what was read*"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, head)

    def test_every_region_carries_every_required_key(self):
        for r in self.regions:
            with self.subTest(region=r["name"]):
                for k in dr.REQUIRED:
                    self.assertIn(k, r)

    def test_names_are_unique_and_evidence_is_repo_relative(self):
        # An evidence path is a pointer a reader can click, so a path that
        # does not resolve is a broken claim rather than a stale one.
        self.assertEqual(len(self.by_name), len(self.regions),
                         "two regions share a name")
        for r in self.regions:
            for path in str(r["evidence"]).split(";"):
                path = path.strip()
                with self.subTest(region=r["name"], path=path):
                    self.assertTrue((REPO / path).exists(),
                                    f"evidence path does not resolve: {path}")

    def test_established_by_names_a_command_someone_can_paste(self):
        # CLAUDE.md's bar for anything upstream is meant to hold up to:
        # "reproducible from committed inputs". Asserting that the field
        # *mentions* the firmware path is not that -- the seven fields did,
        # while every one of them was a folded YAML block whose newlines had
        # been joined into spaces, so each was a `SyntaxError` on paste. So the
        # payload is extracted and run, and what it prints is held against the
        # entry's own numbers: a `SyntaxError` (a folded block, a typo), and a
        # command that walks a different span (a wrong `o=` seed) are both
        # caught, where either would pass a substring check.
        #
        # The end each derivation reports is its own convention, not a rule the
        # file states: a run stopped by the byte after the last entry prints
        # that offset, and a descending run stopped by the first non-descending
        # word prints the *last entry's* offset, one stride back. Both are the
        # entry's `file_hi` and both are accepted here, so the assertion is on
        # the span being walked rather than on which of the two stopped it.
        #
        # Running the command checks where it *stops* and not where it *starts*,
        # and that gap is worth naming: seeding a `common-032f-ljmp-table` walk
        # at 0x38F instead of 0x32F still runs to 0x497, and still divides by
        # the literal 0x32f in its own print, so it prints `0x497 120` and would
        # pass on the output alone while walking a span 32 entries shorter.
        # So the seed is pinned to this entry's own `file_lo` as well, which is
        # the other half of "walks this span".
        for r in self.regions:
            with self.subTest(region=r["name"]):
                cmd = r["established_by"]
                self.assertIn("ec/firmware/GMxMGxx_11.800", cmd,
                              "an entry that cannot be re-derived from the "
                              "committed image is not evidence, it is a claim")
                payload = self.command_payload(cmd)
                self.assertEqual(
                    self.command_seed(payload), r["file_lo"],
                    "the command starts its walk at an offset other than this "
                    "entry's file_lo, so it re-derives a different span -- an "
                    "in-run seed still stops in the right place and would pass "
                    "on the output alone")
                run = subprocess.run([sys.executable, "-c", payload],
                                     cwd=REPO, capture_output=True, text=True)
                self.assertEqual(
                    run.returncode, 0,
                    f"established_by does not run: {run.stderr.strip()}\n"
                    f"  command: {payload}")
                out = run.stdout.split()
                self.assertEqual(len(out), 2,
                                 f"expected one '<end> <count>' line, got "
                                 f"{run.stdout!r}")
                end, count = int(out[0], 16), int(out[1])
                self.assertIn(end, (r["file_hi"], r["file_hi"] - r["stride"]),
                              f"the command walks a different span than this "
                              f"entry's 0x{r['file_hi']:05X}")
                self.assertEqual(
                    count, r["entries"],
                    "the command counts a different number of entries than "
                    "this entry declares")

    def test_established_by_naming_no_command_is_refused(self):
        # The guard the case above reaches only with a field that keeps the
        # firmware path and loses the command -- "derived by hand; see
        # ec/firmware/GMxMGxx_11.800 §2.1" -- which is prose that reads like a
        # pointer. Held as its own case so the refusal is reached by something
        # rather than sitting in a branch nothing runs.
        for field in ("docs/findings/ec-data-regions.md §2.1; derived by hand "
                      "from ec/firmware/GMxMGxx_11.800",
                      "ec/firmware/GMxMGxx_11.800 is walked by "
                      "docs/findings/ec-data-regions.md §2.1"):
            with self.subTest(field=field):
                with self.assertRaises(AssertionError):
                    self.command_payload(field)

    @staticmethod
    def command_seed(payload: str) -> int:
        """The offset the command's walk starts from.

        Every derivation in the file seeds its own cursor from a literal
        (`o=0x32f`, `o=0x6e7d`), so that literal is where the walk starts and
        is what has to agree with the entry's `file_lo`. It is read out of the
        source rather than out of a run, because what a run reports is where the
        walk *stopped*; the start is not observable any other way without
        re-implementing the derivation, which is the thing being checked.
        """
        seeds = re.findall(r"\bo=0x([0-9a-fA-F]+)", payload)
        if len(seeds) != 1:
            raise AssertionError(
                f"expected exactly one `o=0x...` seed in the command, found "
                f"{len(seeds)}: {payload}")
        return int(seeds[0], 16)

    @staticmethod
    def command_payload(field: str) -> str:
        """The script inside the field's `python3 -c "..."`.

        The field is a prose pointer followed by the command -- `... §2.1;
        python3 -c "d=open(...)"` -- so the payload is taken from the opening
        quote to the last one rather than by splitting on whitespace, which
        would also cut the multi-line script in half. Run as an argv list with
        no shell, so nothing in the script is re-quoted on the way in. A field
        with no `python3 -c "..."` in it names no command, and that is reported
        rather than worked around by executing whatever the field happens to
        say.
        """
        m = re.search(r'python3\s+-c\s+"(.*)"', field, re.DOTALL)
        if not m:
            raise AssertionError(
                "established_by names no `python3 -c \"...\"` command, so it "
                "is prose about a derivation rather than one")
        return m.group(1)

    def test_spans_are_ordered_non_overlapping_and_inside_the_image(self):
        # Two regions sharing a byte would make `region_at()`'s answer depend
        # on the order of the list, which is the one thing a lookup must not
        # do. `common-6e65-repeat-bytes` and `common-6e7d-be-words` are
        # adjacent by design -- different strides, different checks -- and
        # this is what holds them to being adjacent rather than overlapping.
        seen = []
        for r in self.regions:
            self.assertLess(r["file_lo"], r["file_hi"], r["name"])
            self.assertLessEqual(r["file_hi"], len(self.d), r["name"])
            seen.append((r["file_lo"], r["file_hi"], r["name"]))
        for (a_lo, a_hi, a), (b_lo, b_hi, b) in zip(sorted(seen), sorted(seen)[1:]):
            self.assertLessEqual(a_hi, b_lo, f"{a} and {b} overlap")

    def test_vocabularies_are_the_ones_the_header_documents(self):
        # A shape or confidence value added to the YAML but not to the tool's
        # tuple would be refused on the next `--check`, so the file header's
        # list and the tool's tuple have to move together.
        head = REGIONS_YAML.read_text().split("regions:")[0]
        for shape in dr.SHAPES:
            self.assertIn(shape, head)
        for c in dr.CONFIDENCES:
            self.assertIn(c, head)

    # --- the numbers ------------------------------------------------------

    def test_the_committed_regions_re_derive_from_the_image(self):
        self.assertEqual(dr.check(self.d, self.regions), 0)

    def test_no_region_is_unchecked_today(self):
        # `inferred-unchecked` exists in the vocabulary so a future entry can
        # say out loud that `--check` cannot reach it. Nothing uses it yet, and
        # this is what makes "yet" a fact rather than a hope.
        self.assertEqual(dr.unchecked(self.regions), [])

    def test_the_issue_s_own_addresses_are_not_where_the_regions_are(self):
        # Four of issue #50's six ranges moved. Asserted as a set of
        # inequalities so a future re-cut that slid one of them back onto the
        # issue's figure goes red here rather than looking like a correction.
        self.assertNotEqual(self.by_name["common-032f-ljmp-table"]["file_lo"],
                            0x035C, "the issue's 0x035C is entry 15 of 120")
        self.assertNotEqual(self.by_name["common-055a8-be-words"]["file_lo"],
                            0x55D0, "the issue's 0x55D0 is mid-table")
        self.assertNotEqual(self.by_name["common-0656-address-table"]["file_lo"],
                            0x066C, "the issue's 0x066C is 0x16 bytes in")
        self.assertNotEqual(self.by_name["common-690b-ff-triples"]["file_lo"],
                            0x6940, "d[0x6940]=0xDE is the address byte of the "
                                    "entry at 0x693E, not an entry boundary")
        self.assertNotEqual(self.by_name["common-6e65-repeat-bytes"]["file_lo"],
                            0x6E78, "0x6E78 is 3.17 repeats into a repeating "
                                    "byte pattern, not a word table")
        # ...and the one that did not move is still there, unchanged.
        self.assertEqual(self.by_name["common-219c-ff-triples"]["file_lo"],
                         0x219C)

    def test_0x021C6_is_outside_every_listed_region(self):
        # The load-bearing correction to bank-call-audit.md §5. It is a
        # 24-of-24 site that no region covers, which is exactly the
        # population the follow-up census is about, so it has to stay
        # uncovered rather than be absorbed by a region that does not hold it.
        self.assertIsNone(dr.region_at(self.regions, 0x021C6))
        self.assertEqual(0x021C6 - self.by_name["common-219c-ff-triples"]["file_hi"],
                         0x12, "0x021C6 is 0x12 bytes past the 0x219C triples")

    def test_the_regions_do_not_overlap_the_endpoints_of_each_other(self):
        # A lookup is half-open, so file_hi of one region must resolve to the
        # next region or to nothing -- never to the region it just left.
        for r in self.regions:
            with self.subTest(region=r["name"]):
                got = dr.region_at(self.regions, r["file_hi"])
                self.assertNotEqual(got["name"] if got else None, r["name"])

    # --- the mutations ----------------------------------------------------

    def mutate_and_check(self, region_name, **changes) -> int:
        """`check()` on a copy of the file with `changes` applied to one region.

        Diagnostics are discarded so a mutation that produces four problems
        does not bury the ones it did not cause; the count is what is asserted.
        """
        mutated = copy.deepcopy(self.regions)
        for r in mutated:
            if r["name"] == region_name:
                r.update(changes)
        saved = os.devnull
        devnull = open(saved, "w")
        import sys as _sys
        real, _sys.stderr = _sys.stderr, devnull
        try:
            return dr.check(self.d, mutated)
        finally:
            _sys.stderr = real
            devnull.close()

    def test_a_span_shifted_by_one_byte_is_refused(self):
        # The mutation this whole file exists to catch: a scan-site address
        # mistaken for a table boundary. Both directions, because they fail
        # for different reasons -- one is not a whole number of entries, the
        # other decodes to a different value.
        for r in self.regions:
            with self.subTest(region=r["name"]):
                self.assertGreater(
                    self.mutate_and_check(r["name"], file_lo=r["file_lo"] + 1), 0)
                self.assertGreater(
                    self.mutate_and_check(r["name"], file_lo=r["file_lo"] - 1), 0)

    def test_a_span_cut_or_grown_by_one_entry_is_refused(self):
        for r in self.regions:
            with self.subTest(region=r["name"]):
                self.assertGreater(
                    self.mutate_and_check(
                        r["name"], file_hi=r["file_hi"] - r["stride"]), 0)
                self.assertGreater(
                    self.mutate_and_check(
                        r["name"], file_hi=r["file_hi"] + r["stride"]), 0)

    def test_a_wrong_count_or_value_is_refused(self):
        for r in self.regions:
            with self.subTest(region=r["name"]):
                self.assertGreater(
                    self.mutate_and_check(r["name"], entries=r["entries"] - 1), 0)
                self.assertGreater(
                    self.mutate_and_check(r["name"],
                                          first_value=r["first_value"] + 1), 0)
                self.assertGreater(
                    self.mutate_and_check(r["name"],
                                          last_value=r["last_value"] + 1), 0)

    def test_a_shape_the_image_does_not_have_is_refused(self):
        # The `ljmp-table` row claimed as a `be-words` one: the stride still
        # divides the span, so only the decoded value catches it.
        self.assertGreater(
            self.mutate_and_check("common-032f-ljmp-table", shape="be-words"), 0)
        self.assertGreater(
            self.mutate_and_check("common-055a8-be-words", shape="ljmp-table"), 0)
        self.assertGreater(
            self.mutate_and_check("common-690b-ff-triples", shape="be-words"), 0)

    def test_a_null_stride_is_reported_rather_than_passed(self):
        # `inferred-unchecked` exists so an unreachable span can say so. The
        # check must report it as unchecked, not as a pass -- a green run that
        # silently skipped a region is the failure mode this repository's §4c
        # corrections are about.
        problems = self.mutate_and_check("common-0656-address-table", stride=None)
        self.assertGreater(problems, 0)

    def test_a_descending_run_is_judged_from_its_own_first_entry(self):
        # A `be-words` entry is defined by the entry before it, and at a
        # region's `file_lo` there is none. Comparing entry 0 against the two
        # bytes *in front of the span* instead makes the table's validity a
        # function of the instruction that happens to precede it, so a
        # well-formed run is rejected whenever those bytes happen to be small.
        # The committed regions pass either way, which is exactly why it
        # needs a case: the bug is invisible from the tree.
        small_preceding = bytes([0x00, 0x10]) + bytes([0x03, 0xE8, 0x03, 0xDF])
        self.assertEqual(dr.entry_value(small_preceding, 2, 2, 2, "be-words"),
                         0x03E8,
                         "a descending run whose first word follows small bytes "
                         "is rejected, so the check reads the wrong 2 bytes")
        self.assertEqual(dr.entry_value(small_preceding, 2, 4, 2, "be-words"),
                         0x03DF, "and the second entry is not read at all")
        # The same shape with the bytes in front raised above the first word
        # must not change the verdict, which is the whole claim.
        large_preceding = bytes([0xF0, 0x22]) + bytes([0x03, 0xE8, 0x03, 0xDF])
        self.assertEqual(dr.entry_value(large_preceding, 2, 2, 2, "be-words"),
                         0x03E8)

    def test_the_committed_be_words_regions_do_not_depend_on_their_neighbours(self):
        # The committed two `be-words` regions happen to be preceded by large
        # bytes (`f0 22` and `10 40`), so the bug above was invisible here.
        # Pinned so a re-cut that starts a region where the preceding bytes
        # are small is caught by the check rather than by luck.
        for name in ("common-055a8-be-words", "common-6e7d-be-words"):
            r = self.by_name[name]
            before = int.from_bytes(self.d[r["file_lo"] - 2:r["file_lo"]], "big")
            with self.subTest(region=name, preceding=hex(before)):
                self.assertEqual(
                    dr.entry_value(self.d, r["file_lo"], r["file_lo"],
                                   r["stride"], "be-words"),
                    r["first_value"],
                    f"{name} decodes differently depending on the two bytes in "
                    "front of it, so its first entry is not self-anchored")


class RefusalTests(unittest.TestCase):
    """What the loader and the tool refuse, each against its own mutation.

    The same refusals `--self-test` runs, held as `unittest` cases so
    `tools/run-tests.sh` collects them with no gate edit.
    """

    def assertRefused(self, regions, why):
        path = write_yaml(regions)
        try:
            with self.assertRaises(SystemExit, msg=why):
                dr.load(path)
        finally:
            os.unlink(path)

    def setUp(self):
        self.base = copy.deepcopy(dr.load(str(REGIONS_YAML)))

    def test_a_region_with_no_evidence_is_refused(self):
        self.assertRefused([dict(self.base[0], evidence="")],
                           "a claim with nothing behind it is not a finding")
        self.assertRefused([{k: v for k, v in self.base[0].items()
                             if k != "evidence"}],
                           "the key itself is mandatory")

    def test_a_region_with_no_established_by_is_refused(self):
        # CLAUDE.md's "reproducible from committed inputs" bar. An entry
        # nobody can re-derive is the thing upstream would not hold up to.
        self.assertRefused([dict(self.base[0], established_by="")],
                           "not re-derivable with a command line")

    def test_a_confidence_outside_the_vocabulary_is_refused(self):
        self.assertRefused([dict(self.base[0], confidence="probably")],
                           "an open-ended confidence is not a tier")

    def test_a_shape_outside_the_vocabulary_is_refused(self):
        # Refused rather than guessed at: a decoder this tool does not have
        # would have to invent one, and an invented decoder checking a
        # committed file is worse than no check.
        self.assertRefused([dict(self.base[0], shape="mystery-bytes")],
                           "the shape decides how the bytes are read")

    def test_a_missing_required_key_is_refused(self):
        for k in dr.REQUIRED:
            with self.subTest(key=k):
                self.assertRefused(
                    [{kk: v for kk, v in self.base[0].items() if kk != k}],
                    f"{k} is required")

    def test_the_annotate_never_suppress_rule_is_a_refusal(self):
        # The rule the issue states, as a function that raises rather than a
        # sentence in a docstring. A future edit that adds a filtering mode
        # has to delete this, which is the point of it existing.
        with self.assertRaises(SystemExit) as cm:
            dr.refuse_filtering()
        self.assertIn("absence", str(cm.exception))

    def test_no_module_level_filter_of_a_region_site_exists(self):
        # Belt to the refusal's braces: a `filter_regions` or `without_regions`
        # helper would be the other half of the same mistake, and naming the
        # two shapes it would take is cheaper than a comment forbidding them.
        public = [n for n in dir(dr) if not n.startswith("_")]
        for banned in ("filter_regions", "without_regions", "exclude_regions",
                       "suppress_regions", "only_in_regions"):
            self.assertNotIn(banned, public)


class OracleTests(unittest.TestCase):
    """The audit's named phantoms, resolved the way the corrected audit says.

    Transcribed from `ec/annotations/bank-call-audit.md` rather than from
    `data-regions.yaml`, so the tool cannot grade its own homework: a map that
    put every one of these on the wrong side would fail here, and a map that
    put them on the right side for the wrong reason still passes `--check` and
    fails this.
    """

    @classmethod
    def setUpClass(cls):
        cls.regions = dr.load(str(REGIONS_YAML))

    def test_the_two_named_table_phantoms_are_inside_a_region(self):
        # §2: 0x055DC, the ljmp scoring 23 of 24 that is a table entry.
        # §5: 0x00381, the lcall read one byte out of the ljmp frame.
        for off, name in ((0x055DC, "common-055a8-be-words"),
                          (0x00381, "common-032f-ljmp-table")):
            with self.subTest(offset=hex(off)):
                self.assertEqual(dr.region_at(self.regions, off)["name"], name)

    def test_0x021C6_is_outside_one(self):
        # §5 as corrected: 0x021C6 is 0x12 bytes past the 0x219C triples, not
        # inside them. It is also the strongest site in bucket C that no
        # region explains, which is the population the follow-up is about.
        self.assertIsNone(dr.region_at(self.regions, 0x021C6))

    def test_the_other_bucket_C_table_sites_land_where_the_audit_read_them(self):
        # §1's table, site by site. 0x00686 and 0x0067E are entry-aligned in
        # the 0x0656 address table; 0x06952 is inside the 0x690B triples but
        # NOT entry-aligned, which is the distinction the column exists to
        # make visible rather than a single yes/no.
        for off, name in ((0x00686, "common-0656-address-table"),
                          (0x0067E, "common-0656-address-table"),
                          (0x06952, "common-690b-ff-triples"),
                          (0x06E83, "common-6e7d-be-words")):
            with self.subTest(offset=hex(off)):
                self.assertEqual(dr.region_at(self.regions, off)["name"], name)
        r = dr.region_at(self.regions, 0x06952)
        self.assertNotEqual((0x06952 - r["file_lo"]) % r["stride"], 0)

    def test_0x006E78_is_in_the_repeat_pattern_not_a_word_table(self):
        # The issue's `0x006E78` word-table claim, corrected. The word table
        # the reading was probably reaching for starts five bytes later.
        r = dr.region_at(self.regions, 0x006E78)
        self.assertEqual(r["name"], "common-6e65-repeat-bytes")
        self.assertEqual(r["shape"], "repeat-bytes")
        self.assertEqual(dr.region_at(self.regions, 0x06E7D)["name"],
                         "common-6e7d-be-words")


class ConsumerTests(unittest.TestCase):
    """The two scanning tools label a region site; neither filters it.

    The issue's rule is *annotate, never suppress*, and it is the rule a
    future edit is most likely to break by accident -- a `--only-real-sites`
    flag reads as an improvement and makes every later scan's zero
    unauditable. So these cases hold the *counts*, not just the column: a
    tool that started dropping region sites would keep printing
    `in_data_region=` and still pass a test that only checked for it.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = FIRMWARE.read_bytes()
        cls.regions = dr.load(str(REGIONS_YAML))

    def test_scan_refs_labels_sites_without_changing_any_count(self):
        import importlib
        sr_spec = importlib.util.spec_from_file_location(
            "scan_refs", HERE / "scan_refs.py")
        sr = importlib.util.module_from_spec(sr_spec)
        sys.path.insert(0, str(HERE))
        try:
            sr_spec.loader.exec_module(sr)
        finally:
            sys.path.pop(0)

        from trace_xdata_refs import PD_MARKER
        off, magic = PD_MARKER
        pd_verified = self.d[off:off + len(magic)] == magic
        hits = sr.scan(self.d, pd_verified)

        # Every site is still counted: the four slots are the three counts
        # plus the site list, and the list length is the file-wide count.
        self.assertTrue(all(len(c[3]) == c[0] for c in hits.values()),
                        "a site is no longer counted once per match")
        self.assertTrue(all(sum(c[:3]) >= 0 for c in hits.values()))

        # ...and at least one site is labelled, so the column is not vacuous.
        labelled = sum(sr.sites_in_data_regions(c[3], self.regions)
                       for c in hits.values())
        self.assertGreater(labelled, 0,
                           "no MOV DPTR site in the whole image lands in a "
                           "listed region, so the column proves nothing")
        self.assertLess(labelled, sum(c[0] for c in hits.values()),
                        "every site labelled would mean the column is not "
                        "discriminating")

    def test_a_region_site_does_not_change_a_referenced_address_verdict(self):
        # 0x0496 is referenced six times and sits inside the ljmp table; the
        # verdict must still be `referenced`, because a site in a table is
        # not a reason to doubt that the register is referenced.
        import importlib
        sr_spec = importlib.util.spec_from_file_location(
            "scan_refs2", HERE / "scan_refs.py")
        sr = importlib.util.module_from_spec(sr_spec)
        sys.path.insert(0, str(HERE))
        try:
            sr_spec.loader.exec_module(sr)
        finally:
            sys.path.pop(0)
        from trace_xdata_refs import PD_MARKER
        off, magic = PD_MARKER
        hits = sr.scan(self.d, self.d[off:off + len(magic)] == magic)
        total, ec, pd, _sites = hits[0x0496]
        self.assertEqual((total, ec, pd), (6, 6, 0))
        self.assertGreater(ec, 0)

    def test_audit_call_targets_still_counts_every_bucket_c_site(self):
        # 140 is the audit's own published upper bound. If a region site were
        # being suppressed rather than labelled, this is the number that
        # would move -- and it is the number `bank-call-audit.md` §5 and its
        # 140/83 verdict rest on.
        import importlib
        a_spec = importlib.util.spec_from_file_location(
            "audit_call_targets", HERE / "audit_call_targets.py")
        act = importlib.util.module_from_spec(a_spec)
        sys.path.insert(0, str(HERE))
        try:
            a_spec.loader.exec_module(act)
        finally:
            sys.path.pop(0)

        rows, _stubs, _tramp = act.survey(self.d)
        bucket_c = [r for r in rows if r["bucket"] == "C"]
        self.assertEqual(len(bucket_c), 140,
                         "bucket C's site count moved, so something filtered "
                         "rather than labelled")
        self.assertEqual(sum(1 for r in bucket_c if r["anchored"]), 83)
        self.assertGreater(
            sum(1 for r in bucket_c
                if dr.region_at(self.regions, r["file_offset"])),
            0, "no bucket-C site is labelled, so the column is not wired")

    def test_audit_call_targets_leaves_write_csv_untouched(self):
        # The issue named bank-call-targets.csv; this diff does not add a
        # column to it, deliberately, because build_ec_decompile.py:206 holds
        # a hard-coded 12-name CALL_TARGET_COLUMNS list whose --self-test runs
        # in the cheap gate. Held here so a future edit that "just adds it"
        # meets a red test naming the reason.
        import ast
        tree = ast.parse((HERE / "audit_call_targets.py").read_text())
        write_csv = next(n for n in ast.walk(tree)
                         if isinstance(n, ast.FunctionDef) and n.name == "write_csv")
        names = {t.value for t in ast.walk(write_csv)
                 if isinstance(t, ast.Constant) and isinstance(t.value, str)}
        self.assertNotIn("in_data_region", names,
                         "adding the column to the committed CSV needs "
                         "build_ec_decompile.py's CALL_TARGET_COLUMNS edited "
                         "too, and its --self-test runs in the cheap gate")

    def test_the_console_tables_carry_the_column(self):
        # Matched on the header line rather than a bare cell string: the column
        # header is emitted as one literal row string, so looking for the cell
        # text alone would not find it.
        import ast
        tree = ast.parse((HERE / "audit_call_targets.py").read_text())
        for fn in ("print_bucket_b", "print_bucket_c"):
            node = next(n for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef) and n.name == fn)
            names = {t.value for t in ast.walk(node)
                     if isinstance(t, ast.Constant) and isinstance(t.value, str)}
            with self.subTest(function=fn):
                self.assertTrue(
                    any(n.startswith("|") and "in listed region" in n
                        for n in names),
                    f"{fn} emits no table header carrying the column")
        sig_b = next(n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef) and n.name == "print_bucket_b")
        self.assertTrue(any(a.arg == "regions" for a in sig_b.args.args),
                        "print_bucket_b cannot label without the regions")


if __name__ == "__main__":
    unittest.main()
