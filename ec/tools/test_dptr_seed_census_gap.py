#!/usr/bin/env python3
"""Holds the `0x0400`-`0x0457` census-gap partition: which artifact carries each
of the ten addresses, and which method cannot see it and why.

Issue #429 asked for a per-address account of ten addresses that have main-EC
byte sites and no reference the decompiled tree can show, plus a decision on
whether the census needs a category for the DPTR-seed shape. The category
exists (`xdata-registers.csv`'s `spelled_as` / `pair_role`, added by #279) and
the per-address reasons exist (`registers.yaml`'s dated notes, `xdata_register_map.py`'s
`NOT_IN_TREE`, and `site-resolution.csv`), but nothing held them to each other
and nothing recorded *which* artifact carries *which* address. That is what this
suite holds.

**What it does not hold, on purpose.** `test_check_site_resolution.py` already
transcribes what each site of these addresses resolves to, off the committed
listings, and re-derives it through `register_ref_table.py`; duplicating that
here would be a second oracle for the same fact. This suite starts one level up:
it reads the committed artifacts and checks the *partition* -- eight carried by
the census, two not -- the reasons each of the ten carries, the four pair
accessors' identity held across the two CSVs that name them, and the correction
in `xdata-register-map.md` §7 that retires the "nothing here says why" claim.

**No count of the tree is asserted.** The number of write-ups, suites, tests or
census rows is a value every merge has to edit; the properties below are claims
about named addresses, and each one fails only when the claim it was written for
stops being true.

Read-only and offline: committed CSVs, the committed YAML, and two committed
markdown documents. No firmware image, no Ghidra, no network, no hardware.
"""
import csv
import importlib.util
import re
import unittest
from pathlib import Path

HERE = Path(__file__).parent
EC = HERE.parent
REPO = EC.parent

# The census tool is imported for `NOT_IN_TREE` and `NOT_IN_TREE_FORBIDDEN`
# rather than read with `ast`, because both are ordinary module-level constants
# and the census's own suite loads the module this way.
spec = importlib.util.spec_from_file_location(
    "xdata_register_map", HERE / "xdata_register_map.py")
xrm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(xrm)

REGISTERS_CSV = EC / "annotations" / "xdata-registers.csv"
SITES_CSV = EC / "annotations" / "site-resolution.csv"
FUNCTIONS_CSV = EC / "annotations" / "ghidra-functions.csv"
REGISTERS_YAML = EC / "annotations" / "registers.yaml"
MAP_MD = EC / "annotations" / "xdata-register-map.md"
FINDING = REPO / "docs" / "findings" / "dptr-seed-census-gap.md"
INDEX_MD = REPO / "docs" / "findings" / "INDEX.md"

# The eight addresses the census carries, and the two it does not. The split is
# the finding: #429 grouped nine addresses as seed-to-helper and the ninth is
# not that shape, so the partition is eight plus two and each half is checked
# against the committed CSV rather than restated from the write-up.
SEEDED = ("0x0402", "0x0404", "0x0408", "0x040A", "0x040C", "0x040E",
          "0x0410", "0x043A")
NOT_IN_CENSUS = ("0x0420", "0x0457")
TEN = SEEDED + NOT_IN_CENSUS

# The four bank1 pair accessors. Their identity is recorded in
# `ghidra-functions.csv` and their names are repeated per site in
# `site-resolution.csv`; nothing joined the two, which is the rot this checks.
PAIR_ACCESSORS = {
    "8886": "read_xdata_pair_to_r1r2",
    "888C": "write_r1r2_to_xdata_pair",
    "8892": "read_xdata_pair_to_r3r4",
    "889E": "write_r3r4_to_xdata_pair",
}


def rows(path, key="addr"):
    with open(path, newline="", encoding="utf-8") as handle:
        return {row[key]: row for row in csv.DictReader(handle)}


def census():
    return rows(REGISTERS_CSV)


def sites():
    out = {}
    with open(SITES_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out.setdefault(row["addr"], []).append(row)
    return out


def annotations():
    """`ghidra-functions.csv` keyed by address, both spellings normalised.

    The annotation CSV is not consistent about the prefix: the four pair
    accessors are keyed `8886`, a bank0 timer `0EA2` and a bank1 routine
    `0xE490`. The cross-check below is about the *name*, so the key is
    normalised here rather than the CSV being held to a spelling it never had.
    """
    out = {}
    with open(FUNCTIONS_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            out[normalise(row["addr"])] = row
    return out


def normalise(addr):
    return addr.upper().lstrip("0X").rjust(4, "0")


def not_in_tree(addr):
    """The `NOT_IN_TREE` entry for one address.

    Read by indexing rather than out of a filtered dict: a helper that dropped
    the addresses it could not find would turn the two wording tests below into
    passes over an empty set, which is the vacuous check
    `test_check_site_resolution.py` names.
    """
    return xrm.NOT_IN_TREE[int(addr, 16)]


def ec_side(rows_for):
    """The rows in one address's block that are in the main EC, not the PD.

    The two programs have separate XDATA maps, so a site in the other program
    is a different byte at a coincidentally equal address and is not evidence
    about this one.
    """
    return [r for r in rows_for if r["region"] != "pd-image"]


def register_entry(addr):
    """The `registers.yaml` entry for one address, or None."""
    import yaml
    with open(REGISTERS_YAML, encoding="utf-8") as handle:
        for entry in yaml.safe_load(handle)["registers"]:
            a = entry.get("addr")
            a = a[0] if isinstance(a, list) else a
            if a is not None and "0x%04X" % a == addr:
                return entry
    return None


def section(text, token):
    """The body of the `##`/`###` heading containing `token`, up to the next."""
    lines = text.split("\n")
    start = None
    level = None
    for number, line in enumerate(lines):
        if line.startswith("#"):
            found = len(line) - len(line.lstrip("#"))
            if start is None and token in line:
                start, level = number + 1, found
            elif start is not None and found <= level:
                return "\n".join(lines[start:number])
    return "\n".join(lines[start:]) if start is not None else ""


class EightCarryTheCensus(unittest.TestCase):
    """The eight: a census row, spelled the seed shape, with a direction."""

    def test_each_seeded_address_has_a_pair_literal_seed_row(self):
        table = census()
        for addr in SEEDED:
            with self.subTest(addr=addr):
                self.assertIn(addr, table,
                              "%s has no census row; the finding and the issue "
                              "both record it as one of the eight the census "
                              "carries" % addr)
                row = table[addr]
                self.assertIn("pair-literal", row["spelled_as"])
                self.assertEqual("seed", row["pair_role"],
                                 "%s is the byte a pair-accessor call passes, "
                                 "not the one its `inc DPTR` walks onto"
                                 % addr)

    def test_each_seeded_address_has_a_non_zero_main_ec_direction(self):
        table = census()
        for addr in SEEDED:
            with self.subTest(addr=addr):
                row = table[addr]
                directions = sum(int(row[column]) for column in
                                 ("read_main_ec", "write_main_ec",
                                  "read+write_main_ec"))
                self.assertGreater(directions, 0,
                                   "%s's census row counts no main-EC "
                                   "reference, which is the zero this issue "
                                   "is about" % addr)

    def test_the_partition_is_disjoint_and_exhaustive(self):
        # Every one of the ten has a site row (below, in TenAreAccountedFor);
        # what splits them is the census row, and it exists for the eight and
        # only for the eight.
        self.assertEqual(set(), set(SEEDED) & set(NOT_IN_CENSUS))
        self.assertEqual(len(TEN), len(set(TEN)))
        table = census()
        for addr in NOT_IN_CENSUS:
            with self.subTest(addr=addr):
                self.assertNotIn(addr, table,
                                 "%s now has a census row. Either answer is "
                                 "defensible, but a change has to come back "
                                 "to docs/findings/dptr-seed-census-gap.md "
                                 "and say why, because the partition is the "
                                 "finding" % addr)


class TenAreAccountedFor(unittest.TestCase):
    """Every address has a site row and a dated per-address reason."""

    def test_each_address_has_a_site_row(self):
        site_rows = sites()
        for addr in TEN:
            with self.subTest(addr=addr):
                self.assertTrue(site_rows.get(addr),
                                "%s has no row in site-resolution.csv, so the "
                                "issue's 'which artifact carries it' has no "
                                "answer for it" % addr)

    def test_each_address_has_a_dated_note(self):
        # A dated note is the shape registers.yaml uses for "this address was
        # re-derived on this date, and here is why". Its absence is what let
        # xdata-register-map.md §7 read as though nothing explained these ten.
        dated = re.compile(r"\*\*\*[^*]*\d{4}-\d\d-\d\d[^*]*#\d+")
        for addr in TEN:
            with self.subTest(addr=addr):
                entry = register_entry(addr)
                self.assertIsNotNone(entry, "no registers.yaml entry for %s"
                                     % addr)
                note = entry.get("note") or ""
                self.assertRegex(note, dated,
                                 "%s's note carries no dated per-address "
                                 "reason, so nothing records which method "
                                 "cannot see it and why" % addr)

    def test_a_note_never_claims_the_byte_is_gone(self):
        # The calibration rule, on the one file where a reader reads a verdict
        # per address rather than a census summary.
        forbidden = ("absent", "does not exist", "no such", "unused",
                     "never touched", "dead")
        for addr in TEN:
            with self.subTest(addr=addr):
                note = (register_entry(addr).get("note") or "").lower()
                hit = [w for w in forbidden if w in note]
                self.assertEqual([], hit,
                                 "%s's note contains %s; a scan that finds no "
                                 "reference has found no reference"
                                 % (addr, hit))


class TheTwoThatAreNotInTheCensus(unittest.TestCase):
    """`0x0420` and `0x0457`: which method cannot see each, and why."""

    def test_both_carry_a_not_in_tree_reason(self):
        # Tested against the key set rather than the dict, so a failure names
        # the missing address instead of printing every reason in the file.
        pinned = {"0x%04X" % a for a in xrm.NOT_IN_TREE}
        for addr in NOT_IN_CENSUS:
            with self.subTest(addr=addr):
                self.assertIn(addr, pinned,
                              "%s has no NOT_IN_TREE reason, so --self-test "
                              "has nothing pinning why the census misses it"
                              % addr)

    def test_a_reason_trips_none_of_the_forbidden_wording(self):
        forbidden = tuple(w.lower() for w in xrm.NOT_IN_TREE_FORBIDDEN)
        for addr in NOT_IN_CENSUS:
            with self.subTest(addr=addr):
                text = not_in_tree(addr)
                hit = [w for w in forbidden if w in text.lower()]
                self.assertEqual([], hit,
                                 "%s's NOT_IN_TREE reason contains %s, which "
                                 "claims the byte rather than the method"
                                 % (addr, hit))

    def test_a_reason_names_something_a_reader_can_go_and_look_at(self):
        # The other half of the same rule: a reason that cannot be
        # re-derived is the reason this check exists. An address or a committed
        # path is the shape every entry in the dict already has.
        anchor = re.compile(r"0x[0-9a-fA-F]{4}|\b[\w.-]+\.(?:c|asm|csv|py)\b")
        for addr in NOT_IN_CENSUS:
            with self.subTest(addr=addr):
                self.assertRegex(not_in_tree(addr), anchor,
                                 "%s's reason names no address and no "
                                 "committed file to re-derive it from" % addr)

    def test_0420_is_a_site_that_resolves_to_nothing(self):
        # Not a seed: the listing at ec/decompiled/bank1/E769.asm copies the
        # address into R1:R2 and returns, with no `lcall` anywhere in the
        # routine. `unresolved-none` is the verdict an instrument reaches when
        # it stops, and it is evidence of nothing in either direction.
        rows_0420 = ec_side(sites()["0x0420"])
        self.assertTrue(rows_0420)
        for row in rows_0420:
            with self.subTest(site=row["runtime"]):
                self.assertEqual("unresolved-none", row["resolution"])
                self.assertEqual("", row["callee"],
                                 "0x0420's site reaches no callee, which is "
                                 "what makes it a third mechanism")

    def test_0457_sits_in_no_exported_function(self):
        # Four sites, all read-modify-writes, none of them inside an export.
        # The census reads every `.c` in the tree, overlapping exports
        # included, so a missing export is why no `.c` spells the address --
        # the one that does (`bank1/8418.c`) names it in a comment, which
        # `strip_comments()` blanks.
        rows_0457 = ec_side(sites()["0x0457"])
        self.assertTrue(rows_0457)
        for row in rows_0457:
            with self.subTest(site=row["runtime"]):
                self.assertEqual("read+write", row["resolution"])
                self.assertEqual("not exported", row["function"])
                self.assertEqual("", row["callee"],
                                 "these sites are read-modify-writes, not "
                                 "handoffs")


class TheFourAccessorsAreOneIdentity(unittest.TestCase):
    """Two CSVs name the same four callees; nothing joined them."""

    def test_every_accessor_has_an_annotation_row(self):
        table = annotations()
        for addr in PAIR_ACCESSORS:
            with self.subTest(addr=addr):
                self.assertIn(addr, table,
                              "bank1 0x%s has no ghidra-functions.csv row, so "
                              "the census's seed direction rests on an "
                              "unnamed body" % addr)

    def test_the_two_csvs_spell_each_accessor_the_same_way(self):
        table, site_rows = annotations(), sites()
        for addr in SEEDED + NOT_IN_CENSUS:
            for row in ec_side(site_rows.get(addr, [])):
                callee = row["callee"]
                if not callee:
                    continue
                with self.subTest(addr=addr, callee=callee):
                    key = normalise(callee)
                    self.assertIn(key, table,
                                  "site-resolution.csv names callee %s but "
                                  "ghidra-functions.csv has no row at that "
                                  "address" % callee)
                    want = "%s %s" % (callee, table[key]["name"])
                    self.assertEqual(want, row["callee_function"],
                                     "the two CSVs name callee %s "
                                     "differently; a rename on one side has to "
                                     "reach the other" % callee)

    def test_every_named_callee_is_one_of_the_four_accessors(self):
        # The census resolves a seed by `pair_accessor()`, so a callee outside
        # this set resolving to a direction would mean the discriminator had
        # widened without anyone deciding it should.
        named = {normalise(row["callee"]) for addr in TEN
                 for row in ec_side(sites().get(addr, [])) if row["callee"]}
        self.assertEqual(set(PAIR_ACCESSORS), named)


class TheCorrectionIsInPlace(unittest.TestCase):
    """§7's "nothing here says why" is false; the correction says so."""

    def test_section_seven_carries_a_correction_naming_the_issue(self):
        with open(MAP_MD, encoding="utf-8") as handle:
            body = section(handle.read(), "## 7.")
        self.assertIn("#429", body,
                      "xdata-register-map.md §7 still carries the issue's "
                      "premise without a dated correction beside it")
        self.assertIn("site-resolution.csv", body,
                      "§7's correction does not point at the artifact that "
                      "answers 'why'")
        self.assertIn("2026-", body,
                      "§7's correction is undated, so the next reader cannot "
                      "tell it from the claim it corrects")

    def test_section_seven_still_carries_the_wrong_claim(self):
        # §4a-4d: the wrong text stays visible with the correction beside it.
        # Deleting it would be a silent retraction, and it is also the only
        # reason a reader can see what was corrected.
        with open(MAP_MD, encoding="utf-8") as handle:
            body = section(handle.read(), "## 7.")
        self.assertIn("Nothing here says why", body)

    def test_the_finding_exists_and_is_indexed(self):
        self.assertTrue(FINDING.is_file())
        title = next(line[2:].strip() for line
                     in FINDING.read_text(encoding="utf-8").split("\n")
                     if line.startswith("# "))
        self.assertTrue(title, "the finding's first `# ` heading is its claim")
        index = INDEX_MD.read_text(encoding="utf-8")
        self.assertTrue(FINDING.name in index,
                        "docs/findings/INDEX.md is out of date; regenerate it "
                        "with gen_findings_index.py")

    def test_the_finding_names_the_inversion_it_is_not(self):
        # #399's shape is the `movx` in the caller. Recording the difference
        # is what stops either issue being rediscovered as the other.
        text = FINDING.read_text(encoding="utf-8")
        self.assertIn("#399", text)
        self.assertIn("trace_xdata_refs.py", text,
                      "the finding does not name the tool #399 would extend")
        self.assertIn("check_site_census.py", text)
        self.assertIn("inverse", text.lower(),
                      "the finding does not state which way round the two "
                      "shapes are")


if __name__ == "__main__":
    unittest.main()