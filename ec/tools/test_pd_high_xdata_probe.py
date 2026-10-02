#!/usr/bin/env python3
"""Cases for `pd_high_xdata_probe.py`'s per-address verdicts.

The tool's whole claim is a classification, and a classification whose failure
mode is silence is the one thing a suite of positives cannot catch: every
address would come back with *a* verdict and nothing would say it was the wrong
one. So the cases split three ways, and the third is the largest.

**The claim, as the issue stated it.** Every address either population names
carries a verdict from the declared vocabulary; the 23 the census pins stay
pinned, address for address; the residue is the twenty-five the issue listed and
not the twenty-two its prose said; and the eleven a dereferencing `movx` is
found behind are exactly those eleven, each with a direction.

**The instrument, held to the oracle and to itself.** The probe reads the
committed `.asm` where a listing covers a site and the image where none does,
which is only one method if the two produce the same row -- asserted by running
`listing_shape()` over the disassembly of bytes a listing also spells. And the
window the probe applies to decoded bytes is `xdata_space()`'s, so on the 23
addresses where the oracle has an answer the two must agree; a probe that
agreed with itself and not with `xdata_space()` would be circular.

**The refusals, and they are the point.** Each boundary of the window rule is
made to fire on hand-built rows, because a rule never seen to fail is not a
rule: a control transfer, a `mov` of DPH, a second `inc DPTR`, a run that ends
without a dereference, and -- the one that costs a real address if it is
missed -- a `movx` that does *not* end the window. A seed no linear walk lands
on is refused as a verdict, and a well-framed one is not, so the rule is not
just "demote everything". `not-found-by-this-method` has to be a reachable
answer and not a formality, and the tool's own words are held against the
calibration this repository writes down.

Nothing here asserts a count of the tree. The population is held as a
relationship between the two sets the issue named, so an address added to the
census or a seed added to the image moves the arithmetic and not a literal.
"""

import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = HERE
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import disasm8051 as D                                       # noqa: E402
import pd_high_xdata_probe as P                             # noqa: E402
import xdata_register_map as X                              # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
# The twenty-five `annotations/pd-xdata-overlap.md` 5.3's residue is, and the
# issue's own list. The issue's prose said twenty-two and its list held
# twenty-five, and the list is the one that reproduces from the image -- so this
# is transcribed from the issue rather than from the tool, which is the only way
# the tool can be caught transcribing itself.
ISSUE_LIST = (
    0xFF00, 0xFF02, 0xFF04, 0xFF08, 0xFF0A, 0xFF0C, 0xFF0E, 0xFFA3, 0xFFC4,
    0xFFCF, 0xFFD9, 0xFFDC, 0xFFDD, 0xFFDE, 0xFFF4, 0xFFF5, 0xFFF6, 0xFFF7,
    0xFFF8, 0xFFFA, 0xFFFB, 0xFFFC, 0xFFFD, 0xFFFE, 0xFFFF,
)
# The eleven a `movx` is found immediately behind the seed, with the direction
# the encoding gives each. `0xFF04` and `0xFF08` are read at one site and
# written at another, which is the case a single `read`/`write` cell would lose.
ELEVEN = {
    0xFF00: "read", 0xFF02: "write", 0xFF04: "read+write", 0xFF08: "read+write",
    0xFF0A: "write", 0xFF0E: "write", 0xFFC4: "write", 0xFFCF: "write",
    0xFFD9: "read", 0xFFDC: "write", 0xFFDD: "write",
}


def operands(oper: str) -> list:
    """One operand string as a comparable list, with immediates and branch
    targets read as the numbers they are.

    The exporter prints an immediate at its minimum width and `disasm8051`
    prints four, so `#0x200` and `#0x0200` are the same value written two ways
    and comparing the strings would fail on a spelling and not on an
    instruction."""
    out = []
    for part in oper.split(","):
        part = part.strip()
        if part.startswith("#"):
            out.append(f"#{int(part[1:], 16):x}")
        elif part.startswith("0x"):
            out.append(f"{int(part, 16):x}")
        else:
            out.append(part)
    return out


def one_shot():
    """The probe's rows over the committed tree, read once per module.

    A fresh call per case would re-read 541 listings and re-decode the region
    for every assertion, and the rows are the same object each time."""
    if not hasattr(one_shot, "rows"):
        one_shot.asm = X.read_asm(P.PD_PROGRAM)
        one_shot.image = P.load_image()
        one_shot.rows = P.classify(one_shot.image, one_shot.asm)
    return one_shot


class ThePopulation(unittest.TestCase):
    def test_the_residue_is_the_issues_list_and_not_its_arithmetic(self):
        # 45 scanned minus 20 in both populations, not 45 minus 23. The three
        # the census pins that a byte scan cannot see are exactly the three
        # `inc` continuations, and comparing the scan's 45 against the census's
        # 23 is what produced the issue's "22".
        scan = P.dptr_sites(one_shot().image)
        self.assertEqual(sorted(set(scan) - set(X.XSPACE_PD_HIGH)),
                         list(ISSUE_LIST))
        self.assertEqual(sorted(set(X.XSPACE_PD_HIGH) - set(scan)),
                         sorted(X.XSPACE_INC_ONLY))
        self.assertEqual(len(scan) - len(set(scan) & set(X.XSPACE_PD_HIGH)),
                         len(ISSUE_LIST))

    def test_every_address_either_side_names_is_classified(self):
        rows = one_shot().rows
        self.assertEqual(set(rows),
                         set(P.dptr_sites(one_shot().image)) | set(X.XSPACE_PD_HIGH))

    def test_every_address_carries_a_declared_verdict(self):
        # A classification that can return a word outside its own vocabulary is
        # not a closed classification, and the tally under the table is built
        # from the same set.
        for addr, row in sorted(one_shot().rows.items()):
            self.assertIn(row["verdict"], P.VERDICTS, hex(addr))
            self.assertIn(row["reach"], set(P.KINDS.values()), hex(addr))
            for site in row["sites"]:
                self.assertIn(site["verdict"], P.VERDICTS,
                              f"{hex(addr)} at {hex(site['site'])}")

    def test_the_census_addresses_keep_the_ors_reach_and_a_direction(self):
        # `census` is a fact about `XSPACE_PD_HIGH`; the reach beside it is
        # this tool's own reading, and the two agreeing on all 23 is what makes
        # the uncovered path's reading of the other 25 worth anything.
        for addr in sorted(X.XSPACE_PD_HIGH):
            oracle = X.xdata_space(one_shot().asm, addr)
            self.assertIsNotNone(oracle, hex(addr))
            self.assertEqual(one_shot().rows[addr]["reach"], oracle[0], hex(addr))
            self.assertNotEqual(one_shot().rows[addr]["direction"], "none",
                                hex(addr))
            self.assertEqual(one_shot().rows[addr]["verdict"], "census",
                             hex(addr))

    def test_the_census_pins_are_read_and_not_written(self):
        # The tool's subject is what the census does not carry, and extending it
        # would need new Ghidra seeds and a project rebuild. That it does not is
        # a property of this file, so it is checked here rather than trusted.
        with open(os.path.join(HERE, "pd_high_xdata_probe.py"),
                  encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn("XSPACE_PD_HIGH =", source)
        self.assertNotIn("XSPACE_PD_HIGH +=", source)
        self.assertNotIn("XSPACE_PD_HIGH.append", source)


class TheEleven(unittest.TestCase):
    def test_they_are_exactly_the_eleven(self):
        backed = {a: r["direction"] for a, r in one_shot().rows.items()
                  if not r["census"] and r["reach"] == "literal"}
        self.assertEqual(backed, ELEVEN)

    def test_each_is_backed_by_a_dereferencing_movx_at_that_site(self):
        # The direction is read off the operand of the `movx`, so it is held
        # against the bytes: `movx a,@dptr` reads and `movx @dptr,a` writes, and
        # a classifier that had the two the wrong way round would still produce
        # a direction, just the other one.
        for addr, want in ELEVEN.items():
            for site in one_shot().rows[addr]["sites"]:
                if P.KINDS[site["verdict"]] != "literal":
                    continue
                want_mnem = "movx"
                for _at, mnem, oper in P.image_run(one_shot().image, site["site"]):
                    if mnem == want_mnem and "@DPTR" in oper:
                        got = "write" if oper.split(",")[0].strip() == "@DPTR" \
                            else "read"
                        self.assertEqual(got, site["direction"],
                                         f"{hex(addr)} at {hex(site['site'])}")
                        break
                else:
                    self.fail(f"{hex(addr)} at {hex(site['site'])} has no movx")

    def test_none_of_them_rests_on_a_site_nothing_lands_on(self):
        for addr in ELEVEN:
            for site in one_shot().rows[addr]["sites"]:
                if P.KINDS[site["verdict"]] == "literal":
                    self.assertNotEqual(site["framed"], 0,
                                        f"{hex(addr)} at {hex(site['site'])}")


class TheSeedNobodyLandsOn(unittest.TestCase):
    """`0xFFA3` is the issue's tenth address and it has no instruction."""

    def test_its_only_site_is_the_tail_of_a_call(self):
        image = one_shot().image
        sites = one_shot().rows[0xFFA3]["sites"]
        self.assertEqual([s["site"] for s in sites], [0xCC53])
        # Read from one byte earlier the three bytes are not an instruction:
        # 0xCC52 is `12 90 ff`, an `lcall 0x90FF`, and the seed's `90` is that
        # call's opcode tail.
        self.assertEqual([f"{image[0xCC52 + i]:02x}" for i in range(4)],
                         ["12", "90", "ff", "a3"])
        self.assertEqual(D.mnemonic(image, 0xCC52, 0xCC52), "lcall 0x90ff")

    def test_and_it_is_reported_unresolved_with_the_window_kept_beside_it(self):
        site = one_shot().rows[0xFFA3]["sites"][0]
        self.assertEqual(site["framed"], 0)
        self.assertEqual(site["verdict"], "not-found-by-this-method")
        self.assertEqual(one_shot().rows[0xFFA3]["verdict"],
                         "not-found-by-this-method")
        # The window's own reading is kept rather than dropped, so a reader can
        # check it against the bytes instead of taking the refusal on trust.
        self.assertEqual(site["unframed"], "callee-derefs")

    def test_a_well_framed_seed_is_not_demoted(self):
        # The other half of the rule. If every site were demoted the eleven
        # above would be empty and this suite's other cases would say nothing
        # about which of the two halves is wrong.
        framed = [s for a, r in one_shot().rows.items() for s in r["sites"]
                  if s["framed"]]
        self.assertTrue(any(s["framed"] == 24 for s in framed))
        self.assertTrue(any(s["verdict"] != "not-found-by-this-method"
                            for s in framed if s["framed"] == 24))


class TheWindowRuleRefuses(unittest.TestCase):
    """Each boundary, on rows built to trip it and nothing else.

    A refusal that has only ever been read in prose is a comment, and this
    tool's failure mode is a window that reaches too far and reports a `movx`
    that is not behind the seed.
    """

    SEED = (0, "mov", "DPTR, #0xff00")

    def test_a_control_transfer_ends_the_window(self):
        self.assertEqual(
            P.window([self.SEED, (3, "jz", "0x0100")], 0xFF00, 0xFF00),
            ("stop", "jz ends the window", None))
        self.assertEqual(
            P.window([self.SEED, (3, "jz", "0x0100"),
                      (6, "movx", "A, @DPTR")], 0xFF00, 0xFF00),
            ("stop", "jz ends the window", None))

    def test_a_ret_ends_the_window_and_is_not_chased(self):
        self.assertEqual(
            P.window([self.SEED, (3, "ret", "")], 0xFF00, 0xFF00),
            ("stop", "ret ends the window", None))

    def test_a_mov_of_dph_or_dpl_ends_the_window(self):
        for mnem, oper in (("mov", "DPH, A"), ("mov", "DPL, A"),
                           ("inc", "DPH"), ("dec", "DPL"), ("pop", "DPL")):
            self.assertEqual(
                P.window([self.SEED, (3, mnem, oper), (4, "movx", "A, @DPTR")],
                         0xFF00, 0xFF00),
                ("stop", f"{mnem} {oper} moves DPTR".replace("  ", " "), None),
                f"{mnem} {oper}")

    def test_a_second_inc_dptr_ends_the_window(self):
        self.assertEqual(
            P.window([self.SEED, (3, "inc", "DPTR"), (4, "inc", "DPTR"),
                      (5, "movx", "A, @DPTR")], 0xFF00, 0xFF00),
            ("stop", "second inc DPTR", None))

    def test_a_window_that_runs_out_is_not_a_dereference(self):
        rows = [self.SEED] + [(3 + 2 * n, "nop", "") for n in range(40)]
        self.assertEqual(P.window(rows, 0xFF00, 0xFF00),
                         ("stop", "window end", None))

    def test_a_movx_that_does_not_dereference_the_address_does_not_end_it(self):
        # The one that costs a real address if it is got wrong. `pd/F2FB.asm`
        # writes the seed, walks DPTR up one and writes the address above it, so
        # `0xFFDB` is an `inc` continuation found *behind* a `movx` that
        # dereferences `0xFFDA`. Stopping at the first `movx` loses all three of
        # the census's inc-only addresses, silently.
        rows = [self.SEED, (3, "movx", "A, @DPTR"), (4, "inc", "DPTR"),
                (5, "movx", "A, @DPTR")]
        self.assertEqual(P.window(rows, 0xFF00, 0xFF00),
                         ("literal", "read", None))
        self.assertEqual(P.window(rows, 0xFF01, 0xFF00), ("inc", "read", None))

    def test_the_direction_is_the_operand_the_movx_writes_through(self):
        for oper, want in (("A, @DPTR", "read"), ("@DPTR, A", "write")):
            self.assertEqual(P.window([self.SEED, (3, "movx", oper)],
                                      0xFF00, 0xFF00), ("literal", want, None))

    def test_a_read_modify_write_site_is_reported_as_the_read(self):
        # The window stops at the first `movx`, so a site that reads and then
        # writes back is recorded as the read. `0xA692` in the PD image is that
        # shape -- it loads `0xFF04`, reads it, ORs `0x01` into A and stores it
        # back -- and the address-level direction survives only because
        # `0xFF04` is also written outright at two other sites. Held here so a
        # later change to the window does not change the answer silently.
        rows = [self.SEED, (3, "movx", "A, @DPTR"), (4, "orl", "A, #0x01"),
                (6, "movx", "@DPTR, A")]
        self.assertEqual(P.window(rows, 0xFF00, 0xFF00),
                         ("literal", "read", None))
        site = [s for r in one_shot().rows.values() for s in r["sites"]
                if s["site"] == 0xA692][0]
        self.assertEqual((site["verdict"], site["direction"]),
                         ("literal-read", "read"))


class TheTwoPathsAreOneMethod(unittest.TestCase):
    """A site read from a listing and the same bytes read from the image have to
    come out as the same instruction, or the probe is two methods and its
    agreement with `xdata_space()` on the 23 says nothing about the 25."""

    def test_listing_shape_is_idempotent_on_a_listing_row(self):
        for at, mnem, oper in one_shot().asm["A8AE"]:
            self.assertEqual(P.listing_shape(mnem, oper), P.listing_shape(
                *P.listing_shape(mnem, oper)))

    def test_a_decoded_row_and_the_listing_that_spells_it_agree(self):
        # `pd/A8AE.asm` is a listing this tool reads, so its bytes are both in
        # the image and in the exporter's own record. Read one way they are a
        # row from `read_asm`, read the other they are `disasm8051`'s, and the
        # window rule has to see the same instruction either way.
        #
        # **Scoped to the rows the window rule reads, and both exclusions are
        # the decoder's own stated limits rather than this test being lenient.**
        # The exporter prints an immediate at its minimum width and
        # `disasm8051` prints four (`#0x200` and `#0x0200`, which is why
        # `DPTR_IMM`'s width is 1-4 and not fixed), and `30 e7 6e` is
        # `jnb 0xe7, 0xa925` to Ghidra and `jnb acc.7, 0xa925` to `disasm8051`,
        # which carries its own `BIT_SFR` table; the window never reads a bit
        # address. And 0xF4 is one of the 36 opcodes `disasm8051` assigns to no
        # instruction, so `pd/A8AE.asm`'s `f4 cpl A` at 0xA984 comes back `db` --
        # the case is below. The window reads the mnemonic for the flow set and
        # the operand only for the DPTR family, `@DPTR` and immediates, so the
        # mnemonic is held for every row it can spell and the operands for those.
        full = 0
        for at, mnem, oper in one_shot().asm["A8AE"]:
            off = int(at, 16)
            text = D.mnemonic(one_shot().image, off, off)
            if text.startswith("db "):
                continue
            decoded = P.listing_shape(*text.partition(" ")[::2])
            self.assertEqual(decoded[0], mnem.lower(), hex(off))
            if decoded[0] in P.CALLS or decoded[0] == "movx" \
                    or any(t in decoded[1] for t in ("DPTR", "DPL", "DPH")):
                self.assertEqual(operands(decoded[1]), operands(oper), hex(off))
                full += 1
        self.assertTrue(full)

    def test_an_opcode_the_decoder_does_not_have_is_passed_over(self):
        # 0xF4 is `cpl A` in `pd/A8AE.asm` and `db 0xf4` to `disasm8051`, one
        # of 36 it assigns to no instruction. A decoded window steps over such a
        # row rather than reading it, so a window containing one is a window
        # this tool cannot fully see -- the same lower bound the listed path has
        # where a listing stops short, and the reason the probe's decoded
        # verdicts are not stronger than they are written.
        rows = [(0, "mov", "DPTR, #0xff00"), (3, "db", "0xf4"),
                (4, "movx", "A, @DPTR")]
        self.assertEqual(P.window(rows, 0xFF00, 0xFF00),
                         ("literal", "read", None))
        self.assertIn(0xF4,
                      [op for op in range(256)
                       if D.mnemonic(bytes([op, 0, 0]), 0).startswith("db ")])

    def test_a_register_is_recased_and_an_immediate_is_not(self):
        # `DPTR_IMM` reads a lower-case immediate and `XSPACE_FLOW` compares a
        # lower-case mnemonic, so a recase that touched either would quietly
        # stop every window from matching.
        self.assertEqual(P.listing_shape("mov", "dptr,#0xff80"),
                         ("mov", "DPTR, #0xff80"))
        self.assertEqual(P.listing_shape("lcall", "0x122f"),
                         ("lcall", "0x122f"))
        self.assertEqual(P.listing_shape("movx", "a,@dptr"),
                         ("movx", "A, @DPTR"))
        self.assertEqual(P.listing_shape("clr", "0xaf"), ("clr", "0xaf"))


class TheCalleeChase(unittest.TestCase):
    def test_a_routine_with_no_movx_is_callee_non_xdata(self):
        # A claim about a named routine, checked against that routine's own
        # listing rather than against a class.
        verdict, direction, _note = P.callee(
            one_shot().image, P.listed_index(one_shot().asm),
            one_shot().asm, 0x122F)
        self.assertEqual((verdict, direction), ("callee-non-xdata", "none"))
        self.assertEqual(
            [m for _at, m, _o in one_shot().asm["122F"] if m == "movx"], [])

    def test_a_one_line_forwarder_is_followed_to_what_it_reaches(self):
        # `pd/7059.asm` is `lcall 0x122f` and nothing else. Reporting "no movx"
        # about the wrapper rather than about the routine it reaches would name
        # the wrong function.
        listed = P.listed_index(one_shot().asm)
        verdict, _direction, note = P.callee(
            one_shot().image, listed, one_shot().asm, 0x7059)
        self.assertEqual(verdict, "callee-non-xdata")
        self.assertIn("0x122F", note)
        self.assertEqual([(m, o) for _at, m, o in one_shot().asm["7059"]],
                         [("lcall", "0x122f")])

    def test_a_routine_that_moves_dptr_before_its_first_movx_rebases(self):
        # `pd/0D38.asm` adds R1:R2 into DPTR and then dereferences it, so a
        # seed in front of a call to it is a base and the address is not the
        # one read. Calling that a dereference is the overclaim in the other
        # direction.
        listed = P.listed_index(one_shot().asm)
        verdict, direction, _note = P.callee(
            one_shot().image, listed, one_shot().asm, 0x0D38)
        self.assertEqual((verdict, direction), ("callee-rebases", "none"))

    def test_a_routine_that_dereferences_dptr_as_it_stands_derefs(self):
        listed = P.listed_index(one_shot().asm)
        verdict, direction, _note = P.callee(
            one_shot().image, listed, one_shot().asm, 0x10C8)
        self.assertEqual((verdict, direction), ("callee-derefs", "read"))

    def test_the_chase_is_bounded_and_says_which_level_it_reached(self):
        # A chase with no bound would follow a cycle until it ran out of stack
        # and would report a depth it never reached; a chase bounded by "we
        # found something" would report a depth it chose.
        listed = P.listed_index(one_shot().asm)
        verdict, _direction, note = P.callee(
            one_shot().image, listed, one_shot().asm, 0x122F,
            depth=P.MAX_CALLEE_DEPTH + 1)
        self.assertEqual(verdict, "not-found-by-this-method")
        self.assertIn(f"depth {P.MAX_CALLEE_DEPTH}", note)

    def test_every_callee_non_xdata_site_names_one_of_two_routines(self):
        # The category the issue did not name, held as a claim about 0x122F and
        # its forwarder rather than as a class this tool invented.
        targets = set()
        for row in one_shot().rows.values():
            for site in row["sites"]:
                if site["verdict"] == "callee-non-xdata":
                    targets.add(site["target"])
        self.assertEqual(sorted(targets), [0x122F, 0x7059])


class TheAggregate(unittest.TestCase):
    """`verdict_of` picks one word out of several sites, and the rule for which
    one is a choice that has to be tested rather than observed."""

    def sites(self, *verdicts):
        return [{"verdict": v, "direction": "none", "listing": None}
                for v in verdicts]

    def test_the_strongest_claim_wins_and_the_order_is_the_declared_one(self):
        # `census` is applied by `classify()` to the whole address and is never
        # a site's verdict, so it is not a candidate here; the rest are, and
        # each has to lose to every word declared above it.
        site_words = tuple(w for w in P.VERDICTS if w != "census")
        for weaker in site_words:
            self.assertEqual(P.verdict_of(self.sites(weaker)), weaker, weaker)
            for stronger in site_words:
                if P.VERDICTS.index(stronger) < P.VERDICTS.index(weaker):
                    self.assertEqual(
                        P.verdict_of(self.sites(weaker, stronger)), stronger,
                        f"{weaker} must lose to {stronger}")

    def test_no_sites_is_not_found_rather_than_a_crash(self):
        self.assertEqual(P.verdict_of([]), "not-found-by-this-method")

    def test_a_read_and_a_write_of_one_address_are_one_reach(self):
        # An address that is both read and written is reached one way, and a
        # `dir` cell that could only say `read` would understate it.
        sites = [{"verdict": "literal-read", "direction": "read", "listing": None},
                 {"verdict": "literal-write", "direction": "write",
                  "listing": None}]
        self.assertEqual(P.reach_of(sites), "literal")
        self.assertEqual(P.directions_of(sites, "literal"), "read+write")

    def test_a_read_and_a_write_of_different_addresses_are_not_mixed(self):
        # The counter-case: 0xFFFC hands DPTR to a routine that dereferences it
        # at one site and to one that never dereferences it at fourteen, and
        # the tally has to keep those apart.
        sites = [{"verdict": "callee-derefs", "direction": "read", "listing": None},
                 {"verdict": "callee-non-xdata", "direction": "none",
                  "listing": None}]
        self.assertEqual(P.reach_of(sites), "callee-derefs")
        self.assertEqual(P.directions_of(sites, "callee-non-xdata"), "none")


class TheWordsItUses(unittest.TestCase):
    """Calibration, held the way `test_scan_mark_collisions.py` holds it: the
    refusal words must be the ones this repository writes down, and the tool's
    own output must not read as an absence claim."""

    REFUSAL = ("absent", "inert", "unreferenced", "does not exist", "unused")

    def test_the_report_never_reads_as_an_absence_claim(self):
        report = P.report(one_shot().rows, P.coverage(one_shot().asm))
        low = report.lower()
        for word in self.REFUSAL:
            self.assertNotIn(word, low, word)
        self.assertIn("not-found-by-this-method", low)

    def test_not_found_is_reachable_rather_than_a_formality(self):
        # A classification in which every address gets a positive answer has
        # not been shown to have a refusal, and the eleven above are the
        # positive half that would hide it.
        verdicts = {r["verdict"] for r in one_shot().rows.values()}
        self.assertIn("not-found-by-this-method", verdicts)
        self.assertIn("callee-non-xdata", verdicts)

    def test_the_verdict_vocabulary_is_closed_and_carries_no_absence_word(self):
        for verdict in P.VERDICTS:
            for word in self.REFUSAL:
                self.assertNotIn(word, verdict, verdict)

    def test_the_docstring_states_the_hardware_limit(self):
        # The sentence a reader skims for, and the one that is false if this
        # tool ever grew a live path: every figure here is off committed files
        # and nothing was read back from an EC.
        with open(os.path.join(HERE, "pd_high_xdata_probe.py"),
                  encoding="utf-8") as f:
            source = f.read()
        self.assertIn("no register was read back", source)
        self.assertIn("is a floor rather than a\nclaim about the firmware",
                      source)


class TheOracles(unittest.TestCase):
    """The two checkers the probe now leans on, run as CI runs them."""

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(TOOLS, "pd_high_xdata_probe.py"),
             *args], cwd=REPO, capture_output=True, text=True)

    def test_the_tools_own_self_test_passes(self):
        out = self.run_tool("--self-test")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("self-test passed", out.stdout)
        self.assertNotIn("FAIL", out.stdout)

    def test_the_decoder_the_probe_depends_on_still_passes_its_own(self):
        out = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "disasm8051.py"),
             "--self-test"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_the_census_is_untouched_by_this_change(self):
        # The whole point of taking the second branch of the issue's fork. If
        # this ever goes red the census moved, and the write-up's claim that it
        # did not is false.
        out = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "xdata_register_map.py"),
             "--check"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_the_census_still_pins_its_own_three_continuations(self):
        out = subprocess.run(
            [sys.executable, os.path.join(TOOLS, "xdata_register_map.py"),
             "--self-test"], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertEqual(len(X.XSPACE_PD_HIGH), 23)
        self.assertEqual(len(X.XSPACE_INC_ONLY), 3)


if __name__ == "__main__":
    unittest.main()
