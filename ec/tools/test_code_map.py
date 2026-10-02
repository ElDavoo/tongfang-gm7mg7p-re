#!/usr/bin/env python3
"""Unit checks for `code_map.py`'s region map and for the `map` column
`audit_call_targets.py --map-column` adds (issue #53).

The map's own write-up is `../annotations/code-map.md`. What this suite is for
is the three things a coverage figure cannot be trusted without: that the walk
terminates and its runs really tile the image, that each edge class the walk has
to get right *is* exercised rather than assumed to work, and that the two named
sites come out `operand` for a reason that is checked against the image bytes
rather than against the tool's own output.

Three things it deliberately does not do. It does not re-run the scan that
wrote `bank-paged-call-targets.csv` to decide whether `0x15BA` is a phantom --
that would assert the tool against itself. It does not assert a coverage
percentage, because a percentage of this tree moves whenever the firmware or the
seed set does; where a figure is load-bearing the test asserts the *direction*
(`wide` reaches more than `narrow`), which re-derives instead of inheriting. And
it does not assert that an `unreached` byte is data, because `code_map.py`'s own
docstring says `unreached` is "not reached by this method" and nothing here can
promote that to a claim about the bytes.

Every edge-class case runs on a hand-built `common`-region buffer rather than on
the firmware, for the reason `audit_call_targets.EARLIER_FIXTURES` gives: a
fixture anchored in the image keeps testing what it was written to test only
until those bytes change, and these are about the *rules*, not about this dump.
The two acceptance sites are the exception and are checked in the image, because
the whole of their claim is about two specific addresses in it.
"""
import csv
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import audit_call_targets
import code_map

ANNOTATIONS = HERE.parent / "annotations"
FIRMWARE = HERE.parent / "firmware" / "GMxMGxx_11.800"
CODE_MAP_CSV = ANNOTATIONS / "code-map.csv"

# The committed censuses `--map-column` annotates, with the flag that writes
# each. Pinned here so a suite that cannot find one of them says which.
CENSUSES = (("bank-call-targets.csv", "--csv"),
            ("bank-paged-call-targets.csv", "--paged-csv"),
            ("bank-relative-branch-targets.csv", "--relative-csv"))

# One buffer for the edge-class cases. `common` is the right region to build a
# fixture in because its file offset and its runtime address are the same
# number, so an offset written in a case reads as both.
FIXTURE = bytearray(b"\x00" * 0x10000)

# One walk and one read of the committed table for the whole suite. The descent
# is deterministic and the committed file does not change under a run, so
# recomputing it per case would only make the suite slower without testing
# anything a second computation could catch.
_WALK = {}


def image():
    if "d" not in _WALK:
        _WALK["d"] = FIRMWARE.read_bytes()
    return _WALK["d"]


def narrow_map():
    if "m" not in _WALK:
        _WALK["m"] = code_map.descend(image(), code_map.narrow_seeds(image())[0])
    return _WALK["m"]


def put(off, raw):
    """Write `raw` at file offset `off` in the fixture buffer."""
    FIXTURE[off:off + len(raw)] = raw
    return bytes(FIXTURE)


class EdgeCases(unittest.TestCase):
    """One case per way `edge_after()` can be wrong.

    Each names the mistake it is there to catch, because a suite whose cases all
    passed for the same reason would say nothing about the other six.
    """

    def edges(self, off, raw, region="common"):
        buf = put(off, raw)
        return code_map.edge_after(buf, off, region)

    def test_sjmp_branches_and_does_not_fall_through(self):
        # `sjmp` is unconditional. Reading it as a conditional would walk two
        # arms where the firmware has one, and the walk would decode whatever
        # sits past the branch as code it is not.
        cont, targets, reasons = self.edges(0x0100, b"\x80\x05")
        self.assertIsNone(cont)
        self.assertEqual(targets, [("common", 0x0107)])
        self.assertEqual(reasons, [])

    def test_conditional_branches_and_falls_through(self):
        # The mirror of the case above, and the one the issue's own "depends on"
        # clause is about: without it a descent stops at every conditional.
        cont, targets, reasons = self.edges(0x0200, b"\x60\x03")
        self.assertEqual(cont, 0x0202)
        self.assertEqual(targets, [("common", 0x0205)])
        self.assertEqual(reasons, [])

    def test_ajmp_branches_and_does_not_fall_through(self):
        cont, targets, reasons = self.edges(0x06FE, b"\x01\xff")
        self.assertIsNone(cont)
        # The page comes from the *next* instruction: 0x0700, so the target is
        # in page 0 and not in the 0x0600 page the site sits in.
        self.assertEqual(targets, [("common", 0x00FF)])
        self.assertEqual(reasons, [])

    def test_ajmp_in_the_last_two_bytes_of_a_page(self):
        # The page rule's edge. 0x07FE is followed by 0x0800, in the *next*
        # page, so the target is 0x08FF. Reading the page off the site's own
        # address instead would give 0x00FF -- a whole 2 KiB page away, still
        # inside the common area, so still a "valid" edge, and still wrong. The
        # assertion that catches it is the exact address, not the fact that the
        # edge resolved.
        buf = put(0x07FE, b"\x01\xff")
        cont, targets, reasons = code_map.edge_after(buf, 0x07FE, "common")
        self.assertIsNone(cont)
        self.assertEqual(targets, [("common", 0x08FF)])
        self.assertEqual(reasons, [])

    def test_ret_ends_the_arm(self):
        buf = put(0x0300, b"\x22")
        cont, targets, reasons = code_map.edge_after(buf, 0x0300, "common")
        self.assertIsNone(cont)
        self.assertEqual(targets, [])
        self.assertEqual(reasons, [])
        self.assertEqual(code_map.arm_end(buf, 0x0300), "ret")

    def test_computed_jump_records_no_target(self):
        # `jmp @a+dptr` is a real transfer this walk never follows. Asserting
        # that it yields *no* target is the anti-overclaim check: a descent that
        # invented one would be guessing a bank and a address from a register.
        buf = put(0x0400, b"\x73")
        cont, targets, reasons = code_map.edge_after(buf, 0x0400, "common")
        self.assertIsNone(cont)
        self.assertEqual(targets, [])
        self.assertEqual(reasons, [])
        self.assertEqual(code_map.arm_end(buf, 0x0400), "jmp @a+dptr")

    def test_lcall_branches_and_returns(self):
        cont, targets, reasons = self.edges(0x0500, b"\x12\x03\x00")
        self.assertEqual(cont, 0x0503)
        self.assertEqual(targets, [("common", 0x0300)])
        self.assertEqual(reasons, [])

    def test_ljmp_branches_and_does_not_return(self):
        cont, targets, reasons = self.edges(0x0506, b"\x02\x03\x00")
        self.assertIsNone(cont)
        self.assertEqual(targets, [("common", 0x0300)])
        self.assertEqual(reasons, [])

    def test_a_bank_edge_into_the_common_area_lands_in_common(self):
        # A bank0 `lcall 0x0200` names the common area, which is mapped at the
        # same runtime address in every bank. Filing the edge under the caller's
        # own region would refuse every bucket-A edge out of a bank, which is
        # most of the common area's inbound calls.
        buf = put(0x9200, b"\x12\x02\x00")
        cont, targets, reasons = code_map.edge_after(buf, 0x9200, "bank0")
        self.assertEqual(cont, 0x9203)
        self.assertEqual(targets, [("common", 0x0200)])
        self.assertEqual(reasons, [])

    def test_the_walk_steps_over_an_inline_case_table(self):
        # `0x7151 switch_case_dispatch` reads the bytes after each `lcall` as a
        # 3-byte-per-entry table terminated by `00 00`. A walk that decodes
        # them as instructions is misframed from the call to the end of the
        # region, so `disasm8051.case_table_len()` is what stops it and the
        # walk has to resume on the far side.
        raw = (b"\x12\x71\x51"          # lcall 0x7151
               b"\x01\x20\x00"          # entry: ajmp page+0x20, selector 0
               b"\x01\x30\x00"          # entry: ajmp page+0x30, selector 0
               b"\x00\x00"              # terminator
               b"\x02\x03\x00\x00")     # 4-byte tail: the default and its filler
        cont, targets, reasons = self.edges(0x0600, raw)
        self.assertEqual(targets, [("common", 0x7151)])
        self.assertEqual(cont, 0x060D)
        self.assertEqual(reasons, [])

    def test_an_edge_that_does_not_resolve_is_a_named_cut(self):
        # A common-area call to a banked address is bucket C. The map must
        # decline it, not place it in a bank: `bank-call-audit.md` 3 is the
        # reason that is the honest answer and not a limitation of this tool.
        buf = put(0x0700, b"\x12\x90\x00")
        cont, targets, reasons = code_map.edge_after(buf, 0x0700, "common")
        self.assertEqual(cont, 0x0703)
        self.assertEqual(targets, [])
        self.assertEqual(reasons, [code_map.CUT_UNRESOLVED])


class AcceptanceSites(unittest.TestCase):
    """The issue's two named sites, checked against the image bytes."""

    @classmethod
    def setUpClass(cls):
        cls.d = image()
        cls.map = narrow_map()

    def test_each_site_is_the_operand_byte_of_a_named_instruction(self):
        for site, owner, raw, text in code_map.ACCEPTANCE_SITES:
            with self.subTest(site=f"0x{site:04X}"):
                self.assertEqual(self.d[owner:owner + len(raw)], raw,
                                 "the image does not hold the bytes the hand "
                                 "read in paged-trampoline-hits-by-hand.md cites")
                self.assertEqual(self.map.verdict("common", site),
                                 code_map.IS_OPERAND)
                self.assertEqual(self.map.owner[("common", site)], owner)
                self.assertEqual(
                    " ".join(code_map.mnemonic(self.d, owner, owner).split()),
                    text)

    def test_the_owning_instructions_are_themselves_code(self):
        # The other half of the three-state claim. `operand` only means
        # anything if the instruction that consumed the byte is one the walk
        # decoded; if the owner were `unreached` the pair would be consistent
        # with a byte inside a table nobody entered.
        for _site, owner, _raw, _text in code_map.ACCEPTANCE_SITES:
            with self.subTest(owner=f"0x{owner:04X}"):
                self.assertEqual(self.map.verdict("common", owner),
                                 code_map.IS_INSTRUCTION)

    def test_a_two_state_map_would_have_given_the_other_answer(self):
        # The reason there are three verdicts, asserted rather than argued. Any
        # map whose vocabulary is {code, unreached} calls both sites `code`,
        # because both are inside an instruction the descent decodes -- which is
        # the opposite of the hand read and would have looked like a
        # confirmation of it.
        for site, _owner, _raw, _text in code_map.ACCEPTANCE_SITES:
            with self.subTest(site=f"0x{site:04X}"):
                two_state = ("code" if self.map.verdict("common", site)
                             != code_map.NOT_REACHED else "unreached")
                self.assertEqual(two_state, "code")
                self.assertNotEqual(self.map.verdict("common", site), two_state)


class MapProperties(unittest.TestCase):
    """Totality, termination, and the partition the committed CSV claims."""

    @classmethod
    def setUpClass(cls):
        cls.d = image()
        cls.seeds, cls.unresolved = code_map.narrow_seeds(cls.d)
        cls.map = narrow_map()

    def test_every_region_byte_is_in_exactly_one_maximal_run(self):
        for region in audit_call_targets.AUDITED:
            with self.subTest(region=region):
                rs = code_map.runs(self.map, region)
                lo, hi = audit_call_targets.region_bounds(region)
                self.assertEqual(rs[0][0], lo)
                self.assertEqual(rs[-1][1], hi)
                self.assertEqual(sum(e - s for s, e, _ in rs), hi - lo)
                for a, b in zip(rs, rs[1:]):
                    self.assertEqual(a[1], b[0], "a gap or an overlap between runs")
                for a, b in zip(rs, rs[1:]):
                    self.assertNotEqual(a[2], b[2], "two adjacent runs of one "
                                        "verdict were not merged")
                self.assertLessEqual({v for _, _, v in rs}, set(code_map.VERDICTS))

    def test_the_walk_finishes_inside_its_budget(self):
        cuts = [why for reasons in self.map.cuts.values()
                for why in reasons if "budget" in why]
        self.assertEqual(cuts, [], "an arm ended on the instruction budget, so "
                                   "the map is a cut and not a finished walk")

    def test_a_budget_that_fires_is_reported_as_a_cut(self):
        # The other half of the case above: the guard has to *say* when it
        # stops, or a cut reads as a finished map -- the failure
        # `docs/findings/count-bounded-walk-invariant.md` is about, and the one
        # the plan this suite came from named.
        saved = code_map.WALK_BUDGET
        code_map.WALK_BUDGET = 64
        try:
            cut = code_map.descend(self.d, self.seeds)
            # Read inside the context: the cut names the budget that fired, and
            # the budget is restored the moment after.
            reasons = [why for rs in cut.cuts.values() for why in rs
                       if "budget" in why]
        finally:
            code_map.WALK_BUDGET = saved
        self.assertEqual(sum(cut.insns.values()), 64)
        self.assertEqual(reasons, ["instruction budget of 64 exhausted"])

    def test_no_byte_is_left_in_no_run(self):
        for region in audit_call_targets.AUDITED:
            lo, hi = audit_call_targets.region_bounds(region)
            unaccounted = [i for i in range(lo, hi)
                           if self.map.verdict(region, i) not in code_map.VERDICTS]
            self.assertEqual(unaccounted, [],
                             f"{region} has bytes in no run at all")

    def test_the_narrow_seed_set_is_the_default_and_needs_no_other_input(self):
        # Every narrow seed is a vector-table entry, a vector target, a
        # trampoline entry, or a trampoline target -- no census row, which is
        # what separates it from the wide set.
        bases = {b for b in self.seeds.values()}
        self.assertTrue(bases <= {"vector", "vector-target", "trampoline",
                                  "trampoline-target"}, bases)
        self.assertEqual(self.unresolved, 0,
                         "a vector target could not be placed; the seed set "
                         "guesses no bank, so a non-zero here is a bucket-C "
                         "vector this map leaves unreached on purpose")

    def test_the_wide_seed_set_reaches_strictly_more(self):
        wide = code_map.descend(
            self.d, code_map.wide_seeds(self.d, self.seeds, str(ANNOTATIONS)))
        reached = lambda m: sum(m.count(r, code_map.IS_INSTRUCTION)
                                + m.count(r, code_map.IS_OPERAND)
                                for r in audit_call_targets.AUDITED)
        self.assertGreater(reached(wide), reached(self.map))

    def test_a_bank_seed_does_not_reach_the_other_bank(self):
        # The common area is deliberately *not* in this assertion: it is mapped
        # at the same runtime address in every bank, so a bank walk must reach
        # it. What must never happen is a bank0 seed marking a bank1 byte.
        for seeded, foreign in (("bank0", "bank1"), ("bank1", "bank0")):
            with self.subTest(seeded=seeded):
                only = code_map.descend(
                    self.d, {k: v for k, v in self.seeds.items() if k[0] == seeded})
                lo, hi = audit_call_targets.region_bounds(foreign)
                self.assertEqual(
                    [i for i in range(lo, hi)
                     if only.verdict(foreign, i) != code_map.NOT_REACHED], [])

    def test_regions_are_disjoint_whole_page_ranges(self):
        # Two properties in one: the mapped regions do not overlap, so a byte
        # belongs to exactly one of them, and each is a whole number of 2 KiB
        # pages aligned the same way in file offset and runtime base, which is
        # what lets a paged target never leave its caller's region.
        bounds = sorted(audit_call_targets.region_bounds(n)
                        for n in audit_call_targets.AUDITED)
        for (lo, hi), (nlo, nhi) in zip(bounds, bounds[1:]):
            self.assertLessEqual(hi, nlo, "regions overlap")
        for name, lo, hi, base, _how in code_map.REGIONS:
            if base is None or name not in audit_call_targets.AUDITED:
                continue
            with self.subTest(region=name):
                self.assertEqual((lo - base) % 0x800, 0)
                self.assertEqual((hi - lo) % 0x800, 0)


class CommittedCsv(unittest.TestCase):
    """The artefact a reader reads, not the walk that wrote it."""

    @classmethod
    def setUpClass(cls):
        with CODE_MAP_CSV.open(newline="") as fh:
            cls.rows = list(csv.DictReader(fh))

    def test_the_committed_map_matches_a_fresh_walk(self):
        with redirect_stdout(io.StringIO()) as out:
            rc = code_map.check_table(narrow_map(), str(CODE_MAP_CSV))
        self.assertEqual(rc, 0, out.getvalue())

    def test_check_fails_on_a_diff(self):
        # A `--check` that cannot fail is not a check. One byte of the header
        # is changed and the comparison has to notice.
        broken = CODE_MAP_CSV.read_text().replace("region,start", "REGION,start")
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
            fh.write(broken)
            path = fh.name
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = code_map.check_table(narrow_map(), path)
            self.assertEqual(rc, 1)
        finally:
            os.unlink(path)

    def test_the_table_is_header_only_and_reads_with_dictreader(self):
        # The convention `ec/annotations/README.md` sets out: no comment lines,
        # so `csv.DictReader` reads it without a special case.
        first = CODE_MAP_CSV.read_text().splitlines()[0]
        self.assertEqual(first, "region,start,end,bytes,verdict")
        self.assertTrue(self.rows)
        self.assertLessEqual({r["verdict"] for r in self.rows},
                             set(code_map.VERDICTS))

    def test_the_table_tiles_each_region_exactly_once(self):
        for region in audit_call_targets.AUDITED:
            with self.subTest(region=region):
                lo, hi = audit_call_targets.region_bounds(region)
                rs = [(int(r["start"], 16), int(r["end"], 16), r["verdict"])
                      for r in self.rows if r["region"] == region]
                self.assertEqual(rs[0][0], lo)
                self.assertEqual(rs[-1][1], hi)
                self.assertEqual(sum(e - s for s, e, _ in rs), hi - lo)
                for r, nxt in zip(rs, rs[1:]):
                    self.assertEqual(r[1], nxt[0])
                    self.assertNotEqual(r[2], nxt[2])
                widths = {r["start"]: int(r["bytes"]) for r in self.rows
                          if r["region"] == region}
                for s, e, _v in rs:
                    self.assertEqual(widths[f"0x{s:05X}"], e - s,
                                     "the `bytes` column disagrees with the "
                                     "run's own start and end")

    def test_every_row_agrees_with_a_fresh_walk(self):
        m = narrow_map()
        wrong = [r["start"] for r in self.rows
                 if any(m.verdict(r["region"], i) != r["verdict"]
                        for i in range(int(r["start"], 16), int(r["end"], 16)))]
        self.assertEqual(wrong, [], "a committed row disagrees with the walk")


class InlineCaseTables(unittest.TestCase):
    """The step-over, checked against the span list issue #50 derived.

    `../annotations/index-table-spans.csv` is a committed census of the
    `0x7151 switch_case_dispatch` tables, and `decode_index_table.py` derives it
    by a route that never calls `disasm8051.case_table_len()`. So the two
    agreeing on a span's extent is corroboration rather than a restatement, and
    it is worth a case: a step-over whose length drifted would leave the table's
    bytes looking like the first instructions of the next routine, and the map
    would keep saying `code` with nothing to notice.
    """

    @classmethod
    def setUpClass(cls):
        cls.d = image()
        cls.map = narrow_map()
        with (ANNOTATIONS / "index-table-spans.csv").open(newline="") as fh:
            cls.spans = list(csv.DictReader(fh))

    def site_offset(self, row):
        """File offset of a span's dispatch call, from the row's own region and
        runtime address through `trace_xdata_refs.offset_for_runtime()` -- the
        same resolver `code_map.py` uses, so a span that moved is followed
        rather than missed, and no offset list is written here to fall behind."""
        return code_map.offset_for_runtime(int(row["site_runtime"], 16),
                                           row["region"])

    def test_every_span_is_reached_at_its_dispatch_call(self):
        # The call is code. A span whose dispatch call no walk reached would say
        # nothing about the table, only about the seed set.
        unreached = [r["site"] for r in self.spans
                     if self.map.verdict(r["region"], self.site_offset(r))
                     != code_map.IS_INSTRUCTION]
        self.assertEqual(unreached, [])

    def test_every_span_matches_the_block_the_walk_steps_over(self):
        wrong = []
        for r in self.spans:
            off = self.site_offset(r)
            lo, hi = int(r["table_file_offset"], 16), int(r["table_end"], 16)
            if code_map.case_table_len(self.d, off) != hi - lo:
                wrong.append(f"{r['site']}: the walk steps over "
                             f"{code_map.case_table_len(self.d, off)} byte(s), "
                             f"the span list records {hi - lo}")
            if {self.map.verdict(r["region"], i) for i in range(lo, hi)} != {code_map.NOT_REACHED}:
                wrong.append(f"{r['site']}: the span's own bytes are not all unreached")
        self.assertEqual(wrong, [])


class MapColumn(unittest.TestCase):
    """`audit_call_targets.py --map-column`: opt-in, and inert without it."""

    @staticmethod
    def census(name, flag, extra=()):
        """One census render, cached. Each is a full pass over three regions and
        the suite asks for six, so recomputing is the difference between a fast
        suite and a slow one for no extra coverage."""
        key = (name, flag, tuple(extra))
        if key not in _WALK:
            cmd = [sys.executable, str(HERE / "audit_call_targets.py"),
                   str(FIRMWARE), flag, *extra]
            _WALK[key] = subprocess.run(cmd, capture_output=True, text=True,
                                        check=True).stdout
        return _WALK[key]

    def test_the_committed_censuses_are_unchanged_without_the_flag(self):
        # The property that makes "no count moves" structural rather than a
        # claim: the three CSVs other tools read as inputs are byte-identical
        # whatever this column does, because the column is off by default.
        for name, flag in CENSUSES:
            with self.subTest(census=name):
                self.assertEqual(self.census(name, flag),
                                 (ANNOTATIONS / name).read_text())

    def test_the_column_renders_for_a_site_in_each_family(self):
        for name, flag in CENSUSES:
            with self.subTest(census=name):
                plain = list(csv.DictReader(io.StringIO(self.census(name, flag))))
                mapped = list(csv.DictReader(
                    io.StringIO(self.census(name, flag, ("--map-column",)))))
                self.assertEqual(len(plain), len(mapped), "a row was added or "
                                                          "dropped by the column")
                self.assertIn("map", mapped[0])
                self.assertNotIn("map", plain[0])
                self.assertLessEqual({r["map"] for r in mapped},
                                     set(code_map.VERDICTS))
                self.assertTrue(any(r["map"] == code_map.IS_OPERAND
                                    for r in mapped),
                                "no site in this family came out `operand`, so "
                                "the column is not actually reading the map")

    def test_the_column_matches_the_committed_map_row_for_row(self):
        # The column and `code-map.csv` are one map read two ways. If they ever
        # disagree the column is quoting something other than the artefact a
        # reader would check it against.
        m = narrow_map()
        mapped = list(csv.DictReader(io.StringIO(
            self.census("bank-paged-call-targets.csv", "--paged-csv",
                        ("--map-column",)))))
        wrong = [r["file_offset"] for r in mapped
                 if r["map"] != m.verdict(r["region"], int(r["file_offset"], 16))]
        self.assertEqual(wrong, [])


class ToolSelfTest(unittest.TestCase):
    """`--self-test` exists and passes, rather than merely being defined."""

    def test_self_test_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(HERE / "code_map.py"), str(FIRMWARE), "--self-test"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("self-test passed", proc.stdout)


if __name__ == "__main__":
    unittest.main()