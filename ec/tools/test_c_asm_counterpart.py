#!/usr/bin/env python3
"""Cases for `c_asm_counterpart.py`.

The tool's own `--self-test` carries the readings, and this drives it. What is
here is the half a self-test cannot be: the tool's *shapes* held directly, so a
verdict that had quietly started answering a different question, or a column
that had stopped meaning what its name says, is caught by a named case rather
than by a figure moving.

**No count of the tree is asserted anywhere in this file.** The census is a
table of the committed corpus and every row of it moves on any merge that
touches a `.c` or an `.asm`, so a suite that pinned its size would have gone
red on a correct tool and told the implement stage to fix the wrong thing.
What is asserted is the claim and the relation: these named addresses are
reported with these verdicts against these listings, the four verdicts
partition, the walk column explains rows without witnessing them, and the
7B14 disagreement is still the one this census cannot see.

Everything here reads committed files. No Ghidra, no hardware, no Windows, no
network.
"""
import collections
import contextlib
import io
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import c_asm_counterpart as tool                                       # noqa: E402
import xdata_register_map as X                                         # noqa: E402

CENSUS = None


def census():
    """The census over the committed tree, built once for the whole module.

    It is a walk of every listing in the tree, so it is built at most once per
    suite process rather than once per class that needs a row from it.
    """
    global CENSUS
    if CENSUS is None:
        index, listings = tool.context()
        CENSUS = tool.rows_for(index, listings)
    return CENSUS


def row(program, addr, xdata_addr):
    """The one census row for a (function, address), or None."""
    for r in census():
        if (r["program"], r["addr"], r["xdata_addr"]) == (program, addr,
                                                           xdata_addr):
            return r
    return None


class TheSelfTest(unittest.TestCase):
    """The tool's own self-test, which is where the readings live."""

    def test_it_passes(self):
        # Its transcript goes to a buffer rather than to this suite's own
        # output: it is a couple of dozen lines, and a reader running the suite
        # would otherwise have to find this suite's own result underneath them.
        # The exit code is the whole of the assertion.
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            rc = tool.self_test()
        self.assertEqual(rc, 0, buf.getvalue()[-2000:])


class TheVocabulary(unittest.TestCase):
    """Closed, and the closure is what makes the split a partition."""

    def test_there_are_four_verdicts(self):
        self.assertEqual(tool.VERDICTS,
                         ("beyond-listing-extent", "reaches-via-callee",
                          "seeded-elsewhere", "no-witness"))

    def test_the_verdicts_partition_the_census(self):
        tally = collections.Counter(r["verdict"] for r in census())
        # Every row carries a verdict, and it is one of the four. Together
        # those are what `verdict_of()` returning a name from anywhere else
        # would break, and no single row would show it.
        self.assertEqual(set(tally) - set(tool.VERDICTS), set())
        self.assertEqual(sum(tally.values()), len(census()))

    def test_no_verdict_reads_as_an_absence(self):
        # `no-witness` is the one a reader is most likely to misread, and the
        # word is deliberate: it is a claim about the method, not about the
        # byte. A verdict named `absent`, `missing` or `unbacked` would be the
        # overclaim CLAUDE.md puts above every other rule, in a column.
        for name in tool.VERDICTS:
            for word in ("absent", "missing", "unbacked", "bogus", "wrong"):
                self.assertNotIn(word, name)


class TheE237Case(unittest.TestCase):
    """The committed instance, and the reason the tool exists.

    `bank1/E237.c`'s own annotation plate says the decompiled C "continues
    past 0xE27C with writes to 0x0680, 0x0681, 0x0683, 0x03A0 and 0x1C05 that
    this listing does not contain". The tool's job is to say WHICH listing
    holds those seeds, not to restate the plate.
    """

    def test_each_address_the_plate_names_is_reported_against_its_successor(self):
        for xdata in ("0x03A0", "0x0680", "0x0683", "0x1C05"):
            with self.subTest(xdata=xdata):
                r = row("bank1", "E237", xdata)
                self.assertIsNotNone(r)
                self.assertEqual(r["verdict"], "beyond-listing-extent")
                self.assertEqual(r["via"], "bank1:E27D/listing")
                self.assertEqual(r["listing_extent"], "[0xE237,0xE27D)")

    def test_the_successor_really_does_begin_where_the_listing_ends(self):
        # The verdict is "the holder's listing starts at this listing's end",
        # so the two ends have to be read off the bytes rather than asserted
        # twice in a row. 0xE27D is `E237 + 70`, and `bank1/E27D.asm` opens at
        # 0xE27D -- which is the whole claim.
        here = tool.listing_extent(os.path.join(tool.DECOMPILED, "bank1",
                                                "E237.asm"))
        there = tool.listing_extent(os.path.join(tool.DECOMPILED, "bank1",
                                                 "E27D.asm"))
        self.assertEqual(here, (0xE237, 0xE27D))
        self.assertEqual(there[0], here[1])

    def test_the_addresses_the_listing_does_seed_file_no_row(self):
        # Otherwise the table would be a copy of the listing rather than the
        # disagreement between the two files.
        for xdata in ("0x1C00", "0x1C03", "0x0391", "0x03C7", "0x0387"):
            with self.subTest(xdata=xdata):
                self.assertIsNone(row("bank1", "E237", xdata))

    def test_the_plate_names_one_address_the_decompile_does_not(self):
        # `bank1/E237.c`'s plate lists "0x0680, 0x0681, 0x0683, 0x03A0 and
        # 0x1C05". Four of the five are in the body; 0x0681 is not, and
        # `bank1/E237.asm` seeds no such address either -- the byte is seeded
        # elsewhere in the tree (`bank0` and `bank1` both have a
        # `mov DPTR,#0x681`), so the claim is about THIS listing's C against
        # THIS listing, not about the byte. The plate is prose and it
        # over-lists by one address relative to the decompile it describes --
        # a small correction recorded here rather than made in the annotation,
        # which this change does not edit. Pinning it means a later re-export
        # that puts 0x0681 in the body fails this case instead of passing.
        with open(os.path.join(tool.DECOMPILED, "bank1", "E237.c"),
                  errors="replace") as handle:
            body = X.body_of(X.strip_comments(handle.read()))
        self.assertNotIn("DAT_EXTMEM_0681", body)
        self.assertIsNone(row("bank1", "E237", "0x0681"))
        self.assertNotIn(
            0x0681,
            tool.immediates_of(os.path.join(tool.DECOMPILED, "bank1",
                                            "E237.asm")))

    def test_the_extent_is_the_bases_own_and_not_the_index_sizes(self):
        # `listing-index.csv` records 70 for E237 and the `.asm` runs 70 bytes,
        # so the two agree here and the verdict does not depend on choosing.
        # They do not agree everywhere -- the report counts the rows where they
        # do -- so the tool reads the bytes and carries the column, and this
        # case is what says which one decided.
        r = row("bank1", "E237", "0x0680")
        self.assertEqual(r["index_size"], "70")
        self.assertEqual(tool.extent_width(r), 70)


class The7B14Case(unittest.TestCase):
    """The disagreement this census does NOT catch, asserted as a non-row.

    `docs/findings/7b14-07c9-token.md` is built on `pd/7B14.c` passing
    `DAT_EXTMEM_07c9` to `make_dptr_r6_minus_3_9028` where `pd/7B14.asm`
    builds the column byte with `clr A` / `add A, #0x1c`. The census is per
    (function, address) and `7B14.asm` seeds 0x07C9 at a dozen other sites, so
    there is no row. Pinning the *absence* is what stops a later reader from
    concluding the tool covers this case, and stops a later change from
    "fixing" it by widening the census and quietly dropping the limit.
    """

    def test_the_census_files_no_row_for_it(self):
        self.assertIsNone(row("pd", "7B14", "0x07C9"))

    def test_and_the_listing_really_does_seed_that_address_elsewhere(self):
        seeds = tool.immediates_of(os.path.join(tool.DECOMPILED, "pd",
                                                "7B14.asm"))
        self.assertIn(0x07C9, seeds)
        # ... while never seeding 0x001C, the constant the C dropped.
        self.assertNotIn(0x001C, seeds)

    def test_the_listing_builds_the_constant_the_c_drops(self):
        at = tool.inspect_listing("pd", "7B14")
        self.assertEqual(at[0x7CC1], ("clr", "A"))
        self.assertEqual(at[0x7CC2], ("add", "A, #0x1c"))
        self.assertEqual(at[0x7CC4], ("lcall", "0x9028"))

    def test_and_the_c_passes_the_symbol_to_that_call(self):
        with open(os.path.join(tool.DECOMPILED, "pd", "7B14.c"),
                  errors="replace") as f:
            body = X.body_of(X.strip_comments(f.read()))
        self.assertIn("make_dptr_r6_minus_3_9028(DAT_EXTMEM_07c9);", body)
        self.assertNotIn("DAT_EXTMEM_001c", body)

    def test_every_call_site_sets_its_column_byte_from_an_immediate(self):
        # Why neither arm of the counterfactual repairs the file, and why this
        # change does not correct it. Every `lcall 0x9028` in the listing is
        # preceded by an `add A, #imm`, and `pd/9028.asm`'s first instruction is
        # `mov R7, A` -- so A is the column byte that becomes DPL. The committed
        # C passes ONE argument at all ten sites, so one of the two inputs
        # `pd/9028.asm` moves into DPTR is unrendered at every one of them.
        # Read off the committed listing rather than asserted twice, so this
        # cannot drift from the bytes it is about.
        at = tool.inspect_listing("pd", "7B14")
        # Every mnemonic that ends a straight-line run, conditional jumps
        # included: `jnb 0xe1, 0x7ccc` at 0x7CBC sits between 0x7CC2's `add`
        # and 0x7CC4's call only if it is *not* counted as a barrier, and then
        # the window picks up an earlier `add` and the case stops saying what
        # it says.
        transfers = ("lcall", "ljmp", "ajmp", "acall", "sjmp", "ret", "jmp",
                     "jb", "jnb", "jc", "jnc", "jz", "jnz",
                     "djnz")
        calls = sorted(a for a, (mnem, ops) in at.items()
                       if mnem == "lcall" and "0x9028" in ops)
        self.assertEqual(len(calls), 10)
        immediates = []
        for addr in calls:
            before = sorted(a for a in at if a < addr)
            barrier = [a for a in before if at[a][0] in transfers]
            window = [a for a in before if a > (barrier[-1] if barrier else -1)]
            setters = [at[a][1] for a in window
                       if at[a][0] == "add" and at[a][1].startswith("A, #")]
            self.assertEqual(len(setters), 1,
                             "exactly one `add A, #imm` between the previous "
                             "transfer and the call at 0x%04X" % addr)
            immediates.append(setters[0].split("#")[1])
        # The exporter prints an immediate unpadded (`add A, #0x3`), so the
        # expected set is written the way the listing writes it rather than
        # zero-padded to two digits.
        self.assertEqual(sorted(set(immediates)),
                         sorted(["0x3", "0xd", "0x11", "0x14", "0x19", "0x1c"]))
        # `0x1c` is the one the issue named, and it is built at two sites.
        self.assertEqual(immediates.count("0x1c"), 2)


class TheWalkColumn(unittest.TestCase):
    """`walked_from` explains a row; it does not witness it."""

    def test_it_names_the_seed_one_byte_below_and_nothing_else(self):
        self.assertEqual(tool.walked_from({0x08D0}, 0x08D1), "0x08D0")
        # An address the listing seeds itself is not a walk from anything.
        self.assertEqual(tool.walked_from({0x08D0}, 0x08D0), "")
        self.assertEqual(tool.walked_from(set(), 0x08D1), "")
        # And it is a walk only from exactly one below, not from two.
        self.assertEqual(tool.walked_from({0x08CF}, 0x08D1), "")

    def test_a_walked_row_is_still_no_witness(self):
        # The point of the column: it explains why the bucket is not empty
        # without promoting a walk to a `mov DPTR` counterpart. If this ever
        # changed, the bucket would mean two things at once.
        r = row("bank0", "8054", "0x08D1")
        self.assertIsNotNone(r)
        self.assertEqual(r["verdict"], "no-witness")
        self.assertEqual(r["walked_from"], "0x08D0")
        seeds = {int(t, 16) for t in r["listing_seeds"].split()}
        self.assertIn(0x08D0, seeds)
        self.assertNotIn(0x08D1, seeds)


class TheWitness(unittest.TestCase):
    """A `mov DPTR, #imm` and nothing else, which is the census's own rule."""

    def test_an_eight_bit_immediate_is_not_a_witness(self):
        # `anl A, #0x7c` and `mov DPTR, #0x7c9` are spelled the same way by
        # the exporter. Reading the operand column rather than the instruction
        # would have let the first witness the second.
        self.assertIsNone(X.seed_of("anl", "A, #0x7c9"))
        self.assertEqual(X.seed_of("mov", "DPTR, #0x7c9"), 0x07C9)

    def test_a_transfer_target_is_not_a_witness(self):
        # `pd/7B14.asm` carries `sjmp 0x7c9d` and `jnb 0xe4, 0x7c9b`; the
        # address there is CODE.
        self.assertIsNone(X.seed_of("ljmp", "0x7c9d"))
        self.assertIsNone(X.seed_of("lcall", "0x9028"))


class TheReport(unittest.TestCase):
    """The table, and the `--check` that holds it."""

    def test_every_row_carries_every_column(self):
        for r in census():
            for column in tool.COLUMNS:
                self.assertIn(column, r)

    def test_via_is_empty_exactly_when_no_witness_is_named(self):
        # `no-witness` is the only verdict that may leave `via` empty, and a
        # row that named a holder while claiming to name none would be the
        # ambiguity the column exists to remove.
        for r in census():
            if r["verdict"] == "no-witness":
                self.assertEqual(r["via"], "", r)
            else:
                self.assertTrue(r["via"], r)

    def test_a_seeded_address_never_files_a_row(self):
        # The negative half: the table is the disagreement, so a (function,
        # address) the listing does seed must be absent from it entirely.
        for r in census():
            seeds = {int(t, 16) for t in r["listing_seeds"].split()}
            self.assertNotIn(int(r["xdata_addr"], 16), seeds, r)

    def test_the_rendered_table_is_a_reader_fixed_point(self):
        import csv as _csv
        text = tool.render(census())
        self.assertEqual(tool.render(list(_csv.DictReader(text.splitlines()))),
                         text)

    def test_check_compares_bytes_and_says_which_row_moved(self):
        text = tool.render(census())
        self.assertEqual(tool.check_table(text, text), (0, []))
        first = census()[0]
        other = next(v for v in tool.VERDICTS if v != first["verdict"])
        drifted = text.replace(",%s," % first["verdict"], ",%s," % other, 1)
        rc, lines = tool.check_table(drifted, text)
        self.assertEqual(rc, 1)
        self.assertTrue(any("verdict" in ln for ln in lines), lines)

    def test_a_row_dropped_is_caught_by_the_row_count(self):
        text = tool.render(census())
        rc, lines = tool.check_table("\n".join(text.splitlines()[:-1]) + "\n",
                                     text)
        self.assertEqual(rc, 1)
        self.assertEqual(len(lines), 1)
        self.assertIn("row count", lines[0])

    def test_the_committed_csv_is_the_one_this_tool_writes(self):
        # `--check` reads the committed file; this says the same thing in the
        # suite so a stale CSV fails the tests job rather than waiting for
        # someone to run the tool by hand.
        self.assertTrue(os.path.isfile(tool.REPORT), tool.REPORT)
        with open(tool.REPORT, newline="") as f:
            have = f.read()
        rc, lines = tool.check_table(have, tool.render(census()))
        self.assertEqual(rc, 0, "\n".join(lines[:20]))


if __name__ == "__main__":
    unittest.main()
