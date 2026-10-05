#!/usr/bin/env python3
"""The four charge-derating counters' `registers.yaml` rows, and the oracle fact
the rename they cause had to stop breaking (issue #299).

Stands in for the part of [issue
#299](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/299) that the cheap
tier can reach: that `ec/annotations/registers.yaml` carries `0x09C7`-`0x09CA`
at the status the static evidence warrants, that the generated symbol table and
the per-site census agree with it, that the committed export spells those four
bytes by the symbol rather than the exporter's placeholder, and that
`build_ec_decompile.py`'s oracle fact holds under **either** spelling.

That last one is the half this suite exists for. `opt_in_ghidra_oracle()` runs
the fact against a fresh Ghidra export and takes it out again, which is the
discipline that makes the check a check -- but it needs Ghidra and minutes, so
it is a procedure rather than a gate, and the negative case had never been
runnable without one. `charge_target_facts_problems()` is pure, so the same
three fixtures the oracle uses by way of a real export are built here as
strings: the old spelling, the new spelling, and the new spelling with the
fact removed. The first two must report nothing and the third must report
exactly the increment/compare fact and not the `lcall`.

**Every case here is a property of the tree, never a census of it.** The four
reference counts are checked by `check_register_counts.py` against the image
and are not repeated as constants here; what is held is that each row carries
all three keys, that no `static_refs_pd_image` is above zero, and that the
census resolves each address to a direction. A row that lost a key is not a row
with a zero in it, and that distinction is the one worth a test.
"""
import csv
import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

REGISTERS = HERE.parent / "annotations" / "registers.yaml"
SYMBOLS = HERE.parent / "ghidra" / "xdata-symbols.csv"
SITE_CSV = HERE.parent / "annotations" / "site-resolution.csv"
DECOMPILED = HERE.parent / "decompiled"

# The block this issue is about, and the only one any case here is about.
ADDRS = (0x09C7, 0x09C8, 0x09C9, 0x09CA)

# Both spellings of the byte, as the exporter has written it and as the
# generated symbol table now names it. `DAT_EXTMEM_09c7` is the exporter's own
# placeholder, which is what an address gets while `registers.yaml` has no row
# for it; adding the row is what moves it to `XDATA_09C7`. The alternation
# lives in `ORACLE_FACTS`, and these two spellings are what it accepts.
OLD_TOKEN = "DAT_EXTMEM_09c7"
NEW_TOKEN = "XDATA_09C7"


def register_rows():
    """{address: entry} over the committed `registers.yaml`."""
    with REGISTERS.open(encoding="utf-8") as handle:
        entries = yaml.safe_load(handle)["registers"]
    out = {}
    for entry in entries:
        addrs = entry["addr"] if isinstance(entry["addr"], list) else [entry["addr"]]
        for addr in addrs:
            out[addr] = entry
    return out


# Both sibling tools are loaded by path rather than off `sys.path`, the way
# test_xdata_register_map.py loads xdata_register_map.py: they are scripts
# beside this suite, not installed modules. `sys.path` still gains the tool
# directory first, because check_status_vocabulary.py and
# check_site_resolution.py import their own siblings by bare module name.
def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(HERE))
build = load("build_ec_decompile")
csr = load("check_site_resolution")
vocab = load("check_status_vocabulary")


class TheFourRowsArePresent(unittest.TestCase):
    """Each address has a row, and the row says what the evidence warrants."""

    @classmethod
    def setUpClass(cls):
        cls.rows = register_rows()

    def test_each_address_is_carried(self):
        """All four are in the file at all.

        The other three cases are vacuous without it, so it is stated first and
        on its own: a suite that skips every assertion because the subject is
        absent is a green suite.
        """
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertIn(addr, self.rows)

    def test_each_row_carries_all_three_reference_keys(self):
        """A missing key is not a zero.

        `check_register_counts.py` requires both split keys to be present for
        the same reason: "not audited" and "audited, no site" have to stay
        distinguishable, and only the second one is a claim.
        """
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                entry = self.rows[addr]
                for key in ("static_refs", "static_refs_main_ec",
                            "static_refs_pd_image"):
                    self.assertIn(key, entry,
                                  f"0x{addr:04X} has no {key}; a missing count "
                                  f"is not a zero one")

    def test_the_status_is_declared_by_the_file_its_own_header(self):
        """`status:` is one of the values the header comment declares.

        Read out of the header rather than written here, so a vocabulary that
        gains or loses a value does not need this file edited to agree -- the
        same reason `check_status_vocabulary.py` parses it instead of copying
        it. Both shapes matter: the value, and the `-DO-NOT-WRITE-BLIND` suffix
        convention, are told apart by case.
        """
        declared = vocab.parse_declared(REGISTERS.read_text(encoding="utf-8"))
        self.assertIsNotNone(declared,
                             "registers.yaml's header no longer declares a "
                             "status vocabulary")
        values, suffixes = declared
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                status = self.rows[addr]["status"]
                base, suffix = vocab.split_status(status, suffixes)
                self.assertIn(base, values)
                if suffix is not None:
                    self.assertIn(suffix, suffixes)

    def test_no_row_claims_a_live_source(self):
        """None of the four names `live`, and each note says so.

        The block's whole grade rests on a static scan. A row that quietly
        acquired a `live` source would claim a host read of bytes the host's
        `0xFE410000` window cannot reach, and the note is the half a reader
        takes the grade from.
        """
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                entry = self.rows[addr]
                self.assertNotIn("live", entry.get("sources") or [])
                self.assertIn("read back", entry["note"].lower())

    def test_no_row_claims_a_pd_image_site(self):
        """`static_refs_pd_image` is zero for all four.

        Not the count itself -- `check_register_counts.py` recomputes that from
        the image -- but that the key is present and zero, since a PD-image
        site would be a reference to a different program's XDATA map and would
        make `present-untested` a claim about the wrong firmware.
        """
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertEqual(self.rows[addr]["static_refs_pd_image"], 0)


class RuleThreeIsSatisfiedByEvidence(unittest.TestCase):
    """Each address has a site the census resolves to a direction.

    Rule 3 of `registers.yaml`'s own vocabulary refuses a `present-untested`
    entry with no EC-side site that resolves to `read`, `write` or `read+write`
    -- and `XDATA_0420` is the one committed exemption. Stated here as a
    property of the committed pair rather than of a census total: the refusal is
    `check_status_vocabulary.py`'s to make, and what is worth holding here is
    that these four are not carried by an exemption they do not need.
    """

    @classmethod
    def setUpClass(cls):
        with SITE_CSV.open(encoding="utf-8", newline="") as handle:
            cls.tally = {}
            for row in csv.DictReader(handle):
                addr = int(row["addr"], 16)
                cls.tally.setdefault(addr, []).append(row["resolution"])

    def test_each_address_has_a_row_in_the_census(self):
        """A missing census row is not a resolved one, in either direction."""
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertIn(addr, self.tally,
                              f"0x{addr:04X} has no row in site-resolution.csv; "
                              f"rule 3 refuses an address it cannot see")

    def test_each_address_resolves_to_a_direction(self):
        """At least one site per address lands in the resolved vocabulary."""
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertTrue(
                    any(label in csr.RESOLVED for label in self.tally[addr]),
                    f"no site of 0x{addr:04X} resolves to a direction; "
                    f"got {self.tally[addr]}")

    def test_none_of_them_is_carried_by_the_named_exemption(self):
        """`RESOLUTION_EXEMPT` names `XDATA_0420`, and these are not it.

        The exemption is a limit of the instrument at one address, held by
        name. An entry that acquired it by accident would stop being checked
        without anything saying so, and `check_status_vocabulary.py` reports a
        stale exemption rather than ignoring it -- this is the half that holds
        the other way.
        """
        rows = register_rows()
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertNotIn(rows[addr].get("name"), vocab.RESOLUTION_EXEMPT)


class TheGeneratedTablesAgree(unittest.TestCase):
    """The symbol table and the site census are regenerated, not hand-set."""

    def test_the_symbol_table_names_all_four(self):
        """One row per address, carrying the row's own status through.

        `register_status` is copied verbatim from `registers.yaml` by the
        generator so a reader can see what the entry said; matching the two is
        what makes a stale CSV fail rather than mislead.
        """
        with SYMBOLS.open(encoding="utf-8", newline="") as handle:
            by_addr = {int(r["addr"], 16): r
                       for r in csv.DictReader(handle)}
        rows = register_rows()
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                self.assertIn(addr, by_addr,
                              "xdata-symbols.csv does not name this address, so "
                              "the export would still spell it DAT_EXTMEM_")
                self.assertEqual(by_addr[addr]["register_status"],
                                 rows[addr]["status"],
                                 "the symbol table's copy of the status has "
                                 "drifted from registers.yaml")

    def test_the_symbol_table_is_byte_identical_to_a_fresh_generation(self):
        """`gen_xdata_symbols.py --check`, run rather than reimplemented.

        The generator reads `registers.yaml` and never writes it, so a CSV that
        disagrees is a stale CSV -- and it is the only thing that decides what
        the next export spells the byte. Held as a subprocess so the check under
        test is the one the gate runs, not a copy of its logic.
        """
        proc = subprocess.run(
            [sys.executable, str(HERE / "gen_xdata_symbols.py"), "--check"],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0,
                         f"gen_xdata_symbols.py --check failed:\n"
                         f"{proc.stdout}\n{proc.stderr}")


class TheCommittedExportSpellsThemBySymbol(unittest.TestCase):
    """The four bytes are written by name in the committed `.c`.

    Being *in* `xdata-symbols.csv` and being *spelled* by it in the committed
    export are two facts, and only the second one is this case -- the gap
    between them is what `docs/findings.md` §3c's correction is about, and an
    address can carry a name and still be written `DAT_EXTMEM_xxxx` until the
    next export runs.
    """

    def symbol_or_placeholder(self, pattern):
        """The `.c` files whose text matches `pattern`, by relative path."""
        rx = re.compile(pattern)
        hits = set()
        for path in sorted(DECOMPILED.rglob("*.c")):
            if rx.search(path.read_text(encoding="utf-8", errors="replace")):
                hits.add(str(path.relative_to(DECOMPILED)))
        return hits

    def test_no_committed_c_still_spells_a_placeholder_for_them(self):
        """The old spelling is gone from the export.

        Per address rather than as one pattern, so the failure names which byte
        is still spelled the old way.
        """
        for addr in ADDRS:
            with self.subTest(addr=f"0x{addr:04X}"):
                token = f"DAT_EXTMEM_{addr:04x}"
                self.assertEqual(self.symbol_or_placeholder(re.escape(token)),
                                 set(),
                                 f"{token} is still in the committed export; "
                                 f"the re-export that names it by symbol has "
                                 f"not landed")

    def test_the_listing_never_names_an_xdata_byte(self):
        """No `.asm` carries either spelling, so no listing is expected to.

        Stated as a property rather than as a count of the files a rename
        moves: which `.c` files those are is this change's own diff, while
        "no listing names an XDATA byte" is a fact about how the exporter
        works that a re-export either keeps or breaks loudly. A listing that
        did carry one would be a change in what Ghidra emits, not in what this
        repository annotates.
        """
        for addr in ADDRS:
            for token in (f"DAT_EXTMEM_{addr:04x}", f"XDATA_{addr:04X}"):
                with self.subTest(token=token):
                    hits = {str(p.relative_to(DECOMPILED))
                            for p in sorted(DECOMPILED.rglob("*.asm"))
                            if token in p.read_text(encoding="utf-8",
                                                    errors="replace")}
                    self.assertEqual(hits, set())


class TheOracleFactSurvivesTheRename(unittest.TestCase):
    """`ORACLE_FACTS`' second entry, under both spellings and broken.

    This is the issue's item 1 and 4, made runnable without Ghidra.
    `charge_target_facts_problems()` is pure by design -- it reads two strings
    and nothing else, which is what lets `opt_in_ghidra_oracle()` hand it a
    deliberately broken copy of its own export. These fixtures are the same
    three states the oracle produces by way of a real export, built as strings
    so the cheap tier can watch the negative case it has never been able to.
    """

    ASM = "B200 12 bf08  lcall 0xbf08\n"

    def c_export(self, token):
        """A `B1F0.c` carrying the increment/compare fact under `token`."""
        return (f"  {token} = {token} + 1;\n"
                f"  if (0x3b < {token}) {{\n"
                f"    {token} = 0;\n"
                f"  }}\n")

    def fact(self):
        """The increment/compare entry, by its own label rather than its index."""
        for label, which, pattern in build.ORACLE_FACTS:
            if which == "c":
                return label, which, pattern
        self.fail("ORACLE_FACTS carries no C fact, so this suite tests nothing")

    def test_both_spellings_report_no_problems(self):
        """The old and the new spelling are the same fact."""
        _label, _which, _pattern = self.fact()
        for token in (OLD_TOKEN, NEW_TOKEN):
            with self.subTest(token=token):
                self.assertEqual(
                    build.charge_target_facts_problems(self.ASM,
                                                       self.c_export(token)),
                    [])

    def test_each_spelling_matches_exactly_once(self):
        """One hit, so taking it out is a break rather than a no-op.

        This is the precondition the oracle's negative case rests on, and it is
        a property of the *pattern*: an alternation that matched the same
        increment twice would satisfy `findall() == 2` and make the removal a
        silent no-op that still passes.
        """
        _label, _which, pattern = self.fact()
        for token in (OLD_TOKEN, NEW_TOKEN):
            with self.subTest(token=token):
                self.assertEqual(len(pattern.findall(self.c_export(token))), 1)

    def test_removing_the_fact_is_reported_under_either_spelling(self):
        """The negative case, for both spellings.

        The removed fixture is built by the pattern itself, exactly as
        `opt_in_ghidra_oracle()` does it, so this is the same operation the
        oracle performs and not a lookalike.
        """
        label, _which, pattern = self.fact()
        for token in (OLD_TOKEN, NEW_TOKEN):
            with self.subTest(token=token):
                text = self.c_export(token)
                broken = pattern.sub("", text, 1)
                self.assertNotEqual(broken, text,
                                    "the substitution was a no-op, so this case "
                                    "would pass for the wrong reason")
                problems = build.charge_target_facts_problems(self.ASM, broken)
                self.assertEqual(len(problems), 1, str(problems))
                self.assertIn(label, problems[0])

    def test_the_other_fact_is_not_reported_when_this_one_is_broken(self):
        """Each fact is measured separately.

        Without this, a helper that reported everything would satisfy the case
        above and the oracle would only be evidence that it read the files --
        which is the failure the oracle's own two-fact loop is written against.
        """
        _label, _which, pattern = self.fact()
        asm_label = next(l for l, w, _p in build.ORACLE_FACTS if w == "asm")
        broken = pattern.sub("", self.c_export(NEW_TOKEN), 1)
        problems = build.charge_target_facts_problems(self.ASM, broken)
        self.assertNotIn(asm_label, " ".join(problems))

    def test_each_fact_is_stated_exactly_once_in_the_table(self):
        """No two entries carry the same label, and no two read the same file.

        This is the issue's own reason for putting the alternation *inside* the
        pattern rather than adding a second entry: a second entry would report
        the same code as two facts. Nothing else here catches that -- a
        duplicated entry matches the export, matches once, is removable, and
        reports itself, so every case above stays green with the table
        double-stating one fact and the oracle reporting it twice.
        """
        labels = [label for label, _which, _pattern in build.ORACLE_FACTS]
        self.assertEqual(len(labels), len(set(labels)),
                         f"ORACLE_FACTS states a label twice: {labels}")
        whichs = [which for _label, which, _pattern in build.ORACLE_FACTS]
        for which in set(whichs):
            with self.subTest(which=which):
                self.assertEqual(whichs.count(which), 1,
                                 f"two ORACLE_FACTS entries read {which}, so "
                                 f"one of them is not a separate fact")

    def test_the_lcall_fact_is_matched_on_the_address_not_the_name(self):
        """The first entry's warrant survives a callee rename too.

        Not this issue's change -- it is here because both facts share one
        table, and the second's pattern was widened by name-agnostic means
        that would not catch a narrowing of the first back to a name. The
        committed export calls `0xbf08` `sub_0a4e_against_4d_with_borrow`,
        while an un-annotated one calls it `FUN_CODE_bf08`, so the fixture
        spells it the second way and the match has to survive either.
        """
        asm_label, _which, pattern = next(
            (l, w, p) for l, w, p in build.ORACLE_FACTS if w == "asm")
        renamed = "B200 12 bf08  lcall 0xbf08  sub_0a4e_against_4d_with_borrow\n"
        self.assertEqual(len(pattern.findall(self.ASM)), 1)
        self.assertEqual(pattern.findall(renamed), pattern.findall(self.ASM),
                         "the lcall fact stopped matching once the callee was "
                         "spelled by its annotated name")
        self.assertEqual(
            build.charge_target_facts_problems(self.ASM, self.c_export(NEW_TOKEN)),
            [], f"{asm_label} was not reported against a complete export")


if __name__ == "__main__":
    unittest.main()
