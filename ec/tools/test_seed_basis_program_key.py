#!/usr/bin/env python3
"""The seed-basis map is keyed on `(program, addr)`, and the committed index
says so (issue #393).

Stands in for two things nothing else holds together. The first is the Java:
`readBasis()` exists twice -- `ExportDecompile`'s private copy and `TongFang`'s,
the one `ExportListing` calls -- and both carried the address-only key, so a
check that reads one file cannot fail on the other. That is the general shape
`docs/findings/entry-namespace-two-copies.md` §6 makes about a different
predicate, and it is why there is one case per copy here and they are not the
same case: the two files are what let this go unfixed in one of them.

The second is the derivation. `seed_basis_projection.py` decides what a
`(program, addr)` *should* record, and `build_ec_decompile.py --check` asserts
the committed indexes against it. That assertion needs no Ghidra, so it is
reachable here too -- a re-export cannot be what makes this file pass or fail.

**The fixtures are the defect.** One address, two programs, two different bases,
and one lookup that must return the caller's program's answer and not the other
one's. Under the address-only keying it returned whichever program's row came
last, which is a property of the CSV's row order and reads identically to a
correct answer on a tree where the two happen to agree -- which is most of it.
The agreeing fixture is here for the same reason: a case that only ever fails is
a case that cannot tell a fix from a lookup that returns nothing.

**No case asserts a count of the tree.** Not how many addresses are seeded into
more than one program, not how many rows move, not how many rows the index has.
Those move on every annotation and every re-export, and the derivation asserts
relations instead: every committed row against its own program's seed, and the
seed set against its own duplicate keys.

**Nothing here observed hardware.** The derivation reads the committed firmware
and two committed CSVs, and the Java cases read committed text.
"""
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
SCRIPTS = os.path.join(REPO, "ghidra", "scripts")

sys.path.insert(0, HERE)
import seed_basis_projection as sbp  # noqa: E402

# The two copies of `readBasis`, each with the file that reads the map it
# builds. Naming both together is the point: a list of one would have let the
# second copy drift again silently. The caller differs between them --
# `ExportDecompile` looks up its own map, `ExportListing` calls `TongFang`'s --
# so the lookup site is a third file for one of the two rows.
COPIES = (
    ("ExportDecompile.java", "ExportDecompile.java"),
    ("TongFang.java", "ExportListing.java"),
)

# `basisKey(program, addr)` is what both copies must build their key with, and
# the lookup site is what must pass a program to it. Matched on the call rather
# than on the key's spelling, so renaming the helper does not silently stop this
# finding it -- a check that greps for one spelling is a check that goes quiet
# on a rename rather than one that goes red.
_LOOKUP = re.compile(r"basis\s*\.\s*get\(\s*(?:TongFang\.)?basisKey\(\s*\w+\s*,")
# The map's own construction: the key must carry the program column (`f[0]`),
# not the address column alone. Anchored on the `m.put(` inside readBasis, and
# the address column alone is the exact regression, so both halves are named.
_PUT = re.compile(r"m\.put\(\s*basisKey\(\s*f\[0\]\s*,\s*f\[1\]\s*\)")


def _java_text(name):
    with open(os.path.join(SCRIPTS, name), errors="replace") as handle:
        return handle.read()


def _read_basis_body(text):
    """The body of this file's `readBasis` *definition*, bounded on its own
    closing brace.

    Anchored on the declaration rather than on the first mention of the name,
    because the call site comes first in both exporters and reading that would
    bound the body on whatever brace happened to follow it. Bounded rather than
    searched across the whole file so a `basisKey` defined for some other reason
    cannot satisfy the put-site check. A body that does not parse yields the
    empty string, and the assertions fail on it -- which is the reading a
    renamed or deleted method should produce, not an exception out of a reader
    that was only ever meant to look.
    """
    start = text.find("readBasis(String path)")
    if start < 0:
        return ""
    end = text.find("\n    }", start)
    return text[start:end] if end > start else ""


class JavaIsKeyedOnBothParts(unittest.TestCase):
    """One case per copy, because the copies are what let this drift apart."""

    def test_each_copy_keys_the_map_on_the_program_column(self):
        for name, _caller in COPIES:
            with self.subTest(copy=name):
                body = _read_basis_body(_java_text(name))
                self.assertIn("readBasis(String path)", body,
                              "%s carries no readable readBasis definition" % name)
                self.assertRegex(
                    body, _PUT,
                    "%s's readBasis does not put its row under a key built from "
                    "the program column; an address-only key records whichever "
                    "program's row the CSV wrote last" % name)

    def test_each_copy_is_looked_up_with_a_program(self):
        # The put site alone would pass on a map that is built correctly and
        # then read by address, which is the same defect wearing the other half.
        for name, caller in COPIES:
            with self.subTest(caller=caller):
                self.assertRegex(
                    _java_text(caller), _LOOKUP,
                    "%s looks a basis up without passing the program, so the "
                    "map's program half is never used" % caller)


class TheMapIsAskedForOneProgramsAnswer(unittest.TestCase):
    """The defect itself, on fixtures, with the lookup written out.

    The exporter's lookup is a dict `get`; this is the same expression over a
    map the module builds, so a fixture is enough to say what the Java does
    with the CSV it is handed -- no Ghidra, and no committed row has to happen
    to carry the shape.
    """

    @staticmethod
    def build(rows):
        """The map `readBasis` builds, from `program,addr,basis` CSV lines.

        Keyed through the module's own `seed_pairs()`, so a change to how the
        pair is spelled cannot leave this fixture building a map the exporter
        would not.
        """
        parsed = [(program, int(addr, 16), why) for program, addr, why in
                  (line.split(",", -1) for line in rows)]
        return sbp.seed_pairs(parsed)[0]

    def test_two_programs_one_address_read_each_its_own(self):
        # The regression: bank0's row is `annotation`, bank1's is `call-target`,
        # and an address-only key gives both of them whichever came last.
        m = self.build(["bank0,0x2BD5,annotation", "bank1,0x2BD5,call-target"])
        self.assertEqual(sbp.expected_basis("bank0", 0x2BD5, m), "annotation")
        self.assertEqual(sbp.expected_basis("bank1", 0x2BD5, m), "call-target")

    def test_the_row_order_does_not_decide_the_answer(self):
        # The same two rows the other way round, because an address-only map
        # answers this correctly by accident and a case that only ever saw one
        # order could not tell the two apart.
        m = self.build(["bank1,0x2BD5,call-target", "bank0,0x2BD5,annotation"])
        self.assertEqual(sbp.expected_basis("bank0", 0x2BD5, m), "annotation")
        self.assertEqual(sbp.expected_basis("bank1", 0x2BD5, m), "call-target")

    def test_programs_that_agree_are_untouched(self):
        m = self.build(["bank0,0x2BD5,annotation", "bank1,0x2BD5,annotation"])
        self.assertEqual(sbp.expected_basis("bank0", 0x2BD5, m), "annotation")
        self.assertEqual(sbp.expected_basis("bank1", 0x2BD5, m), "annotation")

    def test_a_program_the_csv_never_names_reads_auto(self):
        # The honest answer, and the one the committed tree needed at bank0
        # 0xE722: no seed of its own, so nothing is claimed about how the entry
        # was found. `auto` is the exporter's own fallback and is asserted
        # here so a reader comparing this against the Java is comparing against
        # one definition of it.
        m = self.build(["bank1,0xE722,annotation"])
        self.assertEqual(sbp.expected_basis("bank0", 0xE722, m), sbp.AUTO)

    def test_a_duplicate_pair_is_reported_rather_than_silently_dropped(self):
        # A program-keyed map cannot express "which of these two rows is the
        # better reading", so a key written twice is reported rather than
        # resolved. seed_rows() de-duplicates before it returns, so this is the
        # check and not a reading -- and it is the one shadowing case the
        # assertion can catch. The surviving row is the first, which is the
        # driver's own rule: seed_rows() sorts each program's seeds by evidence
        # strength and keeps the strongest, so a caller that kept the last would
        # be a second, disagreeing definition of which row wins.
        basis, dupes = sbp.seed_pairs([("bank0", 0x2BD5, "annotation"),
                                       ("bank0", 0x2BD5, "call-target")])
        self.assertEqual(basis, {("bank0", 0x2BD5): "annotation"})
        self.assertEqual(dupes, [("bank0", 0x2BD5)])
        self.assertTrue(sbp.seed_duplicate_problems(dupes))


class CommonAreaFold(unittest.TestCase):
    """`common` and `bank0` are the same row, so they resolve to one basis."""

    def test_the_fold_resolves_to_bank0_and_leaves_the_others_alone(self):
        # `join_index()` renames a folded bank0 row to `common` and deletes
        # bank1's, so a `common` row IS bank0's row under another name. A
        # resolution that disagreed here would fail every common-area row.
        self.assertEqual(sbp.index_program("common"), "bank0")
        for program in ("bank0", "bank1", "pd"):
            with self.subTest(program=program):
                self.assertEqual(sbp.index_program(program), program)

    def test_a_folded_row_answers_with_bank0s_seed(self):
        basis, dupes = sbp.seed_pairs([("bank0", 0x0012, "vector"),
                                       ("bank1", 0x0012, "vector"),
                                       ("pd", 0x0012, "annotation")])
        self.assertEqual(dupes, [])
        # The fold: a `common` row was bank0's, so it answers bank0's.
        self.assertEqual(sbp.expected_basis("common", 0x0012, basis), "vector")
        # And the PD image is a different program in the same address space, so
        # its 0x0012 is a different function and keeps its own answer. This is
        # the confusion docs/findings.md §19 records as one row wide.
        self.assertEqual(sbp.expected_basis("pd", 0x0012, basis), "annotation")


class CommittedIndexAgrees(unittest.TestCase):
    """The property `build_ec_decompile.py --check` also asserts, over the
    committed tree, so `bash tools/run-tests.sh` covers it without Ghidra."""

    @classmethod
    def setUpClass(cls):
        # Derived once for the class: the derivation reads the committed
        # firmware and two CSVs and re-derives on every call, and two cases here
        # want the same answer.
        cls.basis, cls.dupes, cls.problems = sbp.committed_basis()

    def test_every_committed_row_records_its_own_programs_basis(self):
        self.assertEqual(self.problems, [], "%d row(s) disagree:\n%s"
                         % (len(self.problems), "\n".join(self.problems)))

    def test_the_seed_set_holds_no_duplicate_pair(self):
        self.assertEqual(sbp.seed_duplicate_problems(self.dupes), [])

    def test_a_row_that_reads_another_programs_basis_is_reported(self):
        # Driven on a fixture, because the committed tree is not supposed to
        # have one and a check that only ever sees a clean tree cannot be shown
        # to go red. The address and the two bases come from the committed seed
        # set's own disagreement rather than from a literal, so a later
        # annotation tranche moves this case instead of breaking it.
        disagreeing = [(a, v) for a, v in sbp.shared_addresses(self.basis).items()
                       if len(set(v.values())) > 1]
        self.assertTrue(disagreeing,
                        "the committed seed set seeds no address into two "
                        "programs on different bases, so there is nothing for "
                        "this case to imitate")
        addr, programs = disagreeing[0]
        (mine, mine_basis), (theirs, their_basis) = sorted(
            programs.items(), key=lambda kv: kv[1])[:2]
        rows = [{"program": mine, "addr": "%04X" % addr, "name": "fixt",
                 "seed_basis": their_basis}]
        self.assertEqual(
            sbp.row_mismatches(rows, self.basis),
            [(mine, "%04X" % addr, "fixt", their_basis, mine_basis)])
        self.assertTrue(sbp.index_problems(rows, self.basis, "index.csv"))


if __name__ == "__main__":
    sys.exit(unittest.main())