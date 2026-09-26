#!/usr/bin/env python3
"""Offline checks for `pd_image_census.py`: committed files only.

No firmware upload, no hardware, no Windows, no network. Every input is a file
this repository already ships -- `ec/firmware/GMxMGxx_11.800`,
`vendor/bios-1.09/BIOS_1.09.zip`, `ec/annotations/ghidra-functions.csv` and the
535 `ec/decompiled/pd/*.asm` listings -- so the whole suite runs in a cloud
agent's turn.

**The measurement is not stubbed where it can be.** The vector table, the
string pool, the digests and the provenance are all asserted *by value*
against the real committed image, so a byte that moved takes this red rather
than making a report quietly wrong. The synthetic cases exist for the three
things the committed image cannot supply: a dump whose marker is *not* where
this one's is, a string pool that *does* have a `movc` referrer, and a
CODE-table call site that *does* open a string. A suite with only the
committed image would pin two nulls and prove nothing about the code that
produced them, which is the defect `docs/findings.md` §88 records for a suite
whose cases all read the report.

**The nulls are the calibration cases, so they are the ones with teeth.** The
tool's load-bearing contract is that a search which found nothing says "not
found by this method" and never "absent". Three cases below hold that: the
refusal a dump without the marker gets, the verdict cell an unreferenced
string gets, and the refusal a dump too short to hold the region gets. The
last one exists because a `Refusal` that raised `IndexError` instead would
still be a loud failure and would still be wrong about *what* it looked at.

**The mutation.** `test_a_broken_attribution_takes_the_suite_red` is the case
that says the referrer attribution is not decorative: it points
`owning_function()` at the wrong listing and asserts the pinned case changes
with it. Without it the attribution could return the nearest function start,
or None, or a constant, and every other case in this file would stay green --
which is the same vacuous-green shape §88 names.

`test_every_section_name_goes_red_on_a_figure_of_its_own` is the second such
case, and it exists because `--section` was a substring match on the figure key
that made three of its five names select nothing: `--section command` over a
page whose `host_block` was wrong exited 0 having checked no figures at all. A
check that cannot be wrong is not a check, so each name gets a figure of its
own here, and the "rejected at the door" cases -- a name that reaches nothing,
a key no name reaches -- hold the mapping rather than the report.

Run it directly, or through `python3 ec/tools/pd_image_census.py --self-test`.
**Not in any gate**: see `docs/findings/pd-image-census.md` for the reason, and
note that `.github/scripts/agent-gates.sh` is a pipeline file this branch's
token cannot change. It does run under `agent-gates.sh`'s `python3 syntax`
check, which only proves it compiles.
"""
import collections
import importlib.util
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
TOOL = os.path.join(HERE, "pd_image_census.py")

spec = importlib.util.spec_from_file_location("pd_image_census", TOOL)
pdic = importlib.util.module_from_spec(spec)
sys.path.insert(0, HERE)          # for the tool's own `from disasm8051 import`
spec.loader.exec_module(pdic)

# One read of the committed image, shared by every case below. Parsing the
# region is a slice and reading the zip is a few hundred KB, so paying for it
# per case would be the suite's whole cost for nothing.
REGION, HOW = pdic.read_region()
EXTENTS = pdic.function_extents()
OWNERS = pdic.address_owners(EXTENTS)
NAMES = pdic.function_names()
PROV = pdic.provenance()

# The figures `ec/annotations/pd-image.md` pins, re-derived here rather than
# read from the page: a case that read the page would pass whenever the page
# and the tool drifted *together*, which is the drift `--check` exists to find.
FIGURES = pdic.figures(REGION, OWNERS, NAMES, PROV, EXTENTS)

# The eight protocol strings issue #26 and `lightbar-bat-flow.md` §2 quote.
# The offsets are the point of the case, not the texts: these are the same
# eight that file names as evidence that the region is PD firmware, and a
# reader landing on this page checks that they are still there.
PROTOCOL = {
    "PR Swap": 0xA7AB,
    "Error Recovery": 0xA7D5,
    "Set VBUS 5V": 0xA818,
    "DR Swap": 0xA824,
    "FR Swap": 0xA82C,
    "SRC Negotiate done": 0xA863,
    "SINK Negotiate done": 0xA876,
    "VCONN On": 0xD663,
}
IDENTITY = {"ITE8850-PD": 0x0040, "ProtoVer:01.00": 0x0160,
            "DriverVer:01.00": 0x0170, "UsbPdVer:01.00": 0xE1C0}

# The per-issue write-up, which restates several of the page's figures. Unlike
# the pinned block it has no `--check` on it, so a number it states in prose is
# only held by a case that reads it -- see Provenance.
WRITEUP = os.path.join(HERE, "..", "..", "docs", "findings",
                       "pd-image-census.md")


def firmware_bytes():
    """The committed 256 KiB dump, read once and closed.

    A helper rather than `open(...).read()` at each call site because
    `verbosity=2` makes unittest print a `ResourceWarning` inline with the
    result line, and a warning sitting between `... ok` and the next case name
    is the sort of thing a reader learns to skip. The house tools read bare;
    the suite should not, because its output is the report.
    """
    with open(pdic.FIRMWARE, "rb") as f:
        return f.read()


def region_with_patch(patches):
    """A synthetic region: `patches` is {offset: bytes} over a 0xFF-filled one.

    0xFF rather than 0x00 because the real region's tail is 0xFF and a fixture
    that differed there would be testing a different image shape. Not used for
    the committed-image cases -- it is here for the two things the committed
    image cannot be: a pool with a referrer, and a marker that is not this
    one's marker.
    """
    buf = bytearray(b"\xFF" * pdic.REGION_LEN)
    for off, data in patches.items():
        buf[off:off + len(data)] = data
    return bytes(buf)


class VectorTable(unittest.TestCase):
    """Six entries, read at `0x03 + n * 8` -- and the wrong read, named."""

    def test_six_entries_at_the_discovered_offsets(self):
        self.assertEqual(
            pdic.vector_table(REGION),
            [(0x00, 0x0500), (0x03, 0x0056), (0x0B, 0x0094),
             (0x13, 0x00B2), (0x1B, 0x00F0), (0x23, 0x010E)])

    def test_the_table_ends_in_erased_bytes(self):
        off = pdic.vector_table(REGION)[-1][0] + 3
        self.assertTrue(all(b == 0xFF for b in REGION[off:0x40]),
                        "0x26-0x3F are not erased, so the six-entry walk is "
                        "stopping for the wrong reason")
        self.assertEqual(pdic.erased_after_table(REGION,
                                                pdic.vector_table(REGION)),
                         "0x26-0x3F erased (0xFF)")

    def test_eight_aligning_the_whole_table_reads_the_wrong_bytes(self):
        """The one detail that is easy to get wrong, pinned as a rejection.

        8-aligning from `0x00` reads `0x00`, `0x08`, `0x10`, ... -- the padding
        between entries -- and on these bytes that finds an `LJMP` at `0x00`
        and nothing at the other five offsets. The result is a one-entry table,
        which is a plausible-looking answer, and the failure reads as "this
        firmware has no handler there" rather than as a wrong tool. So the
        wrong answer is named here, and the case fails if a future edit makes
        it right.
        """
        wrong = []
        for n in range(6):
            off = 8 * n
            if off + 2 < len(REGION) and REGION[off] == pdic.LJMP:
                wrong.append((off, (REGION[off + 1] << 8) | REGION[off + 2]))
        self.assertEqual(wrong, [(0x00, 0x0500)],
                         "the 8-aligned read is expected to fail after the "
                         f"reset vector; it read {wrong}")

    def test_the_reset_target_is_the_annotated_c_startup_stub(self):
        target = pdic.vector_table(REGION)[0][1]
        self.assertEqual(NAMES.get(target), "c_startup_idata_clear")
        self.assertIsNone(pdic.interrupt_handover(REGION, target),
                          "the C startup stub is not a vector wrapper, so it "
                          "must not be reported as one")

    def test_each_interrupt_entry_loads_its_own_dptr_and_one_shared_body(self):
        got = {off: pdic.interrupt_handover(REGION, target)
               for off, target in pdic.vector_table(REGION) if off}
        self.assertEqual(
            {off: (h[0], h[1], h[2]) for off, h in got.items()},
            {0x03: (0x0151, 0x0050, 13), 0x0B: (0x0154, 0x0050, 5),
             0x13: (0x0157, 0x0050, 13), 0x1B: (0x015A, 0x0050, 5),
             0x23: (0x015D, 0x0050, 13)})
        self.assertEqual({h[0] for h in got.values()},
                         {0x0151, 0x0154, 0x0157, 0x015A, 0x015D})


class Digests(unittest.TestCase):
    """Both digests, spelled out. A truncated digest in a check cannot fail."""

    def test_the_two_digests(self):
        self.assertEqual(
            pdic.digest(REGION),
            "30fe7fb8174535d2846e77ca837239a91548748e616cc6f061cf151ee230f970")
        self.assertEqual(
            pdic.digest(firmware_bytes()),
            "158d1c6416426939a814146b766a44e2ff0e9286b0abd237e70e51a0c03399c4")

    def test_the_region_is_the_slice_the_digest_claims(self):
        with open(pdic.FIRMWARE, "rb") as f:
            f.seek(pdic.REGION_OFF)
            self.assertEqual(f.read(pdic.REGION_LEN), REGION)


class StringPool(unittest.TestCase):
    """Where the strings are, and what the reference census did with them."""

    ROWS = pdic.string_rows(REGION, OWNERS, NAMES)

    def by_offset(self):
        return {r["region_offset"]: r for r in self.ROWS}

    def test_the_eight_protocol_strings_are_where_the_issue_puts_them(self):
        got = self.by_offset()
        for text, off in PROTOCOL.items():
            self.assertIn(f"0x{off:04X}", got, f"{text!r} is not in the census")
            self.assertEqual(got[f"0x{off:04X}"]["string"], text)

    def test_the_four_identity_strings_are_where_lightbar_bat_flow_puts_them(self):
        got = self.by_offset()
        for text, off in IDENTITY.items():
            row = got[f"0x{off:04X}"]
            self.assertEqual(row["string"].strip(), text)
            self.assertEqual(row["file_offset"], f"0x{pdic.REGION_OFF + off:05X}")

    def test_the_pool_is_three_runs_plus_the_identity_block(self):
        heads = {r["run_head"] for r in self.ROWS}
        self.assertIn("0xA798", heads)   # the protocol vocabulary
        self.assertIn("0xD616", heads)   # the "Set Ver"/VCONN run
        self.assertIn("0xE19C", heads)   # the version/hotfix run
        self.assertEqual(len(self.ROWS), 43)

    def test_a_ret_opcode_is_kept_as_a_pool_candidate_and_flagged(self):
        """`after_nul` is what lets a reader tell a string from a swallowed
        opcode, and the reason the tool does not filter one out is that a
        filter making that call would be the tool making the finding.

        0xA798 holds `22` (`RET`) immediately before `Drop Retry Rx-Msg`, and
        0x22 is also printable `"`, so the run head lands one byte early. The
        row is in the census with `after_nul=no`; a real pool entry is `yes`.
        """
        row = self.by_offset()["0xA798"]
        self.assertEqual(row["string"], '"Drop Retry Rx-Msg')
        self.assertEqual(row["after_nul"], "no")
        self.assertEqual(self.by_offset()["0xA7AB"]["after_nul"], "yes")

    def test_no_candidate_is_referenced_and_the_cells_say_so_in_words(self):
        found = [r for r in self.ROWS
                 if r["verdict"] == "referenced by this method"]
        self.assertEqual(found, [], "a MOVC-mediated referrer appeared; the "
                                    "page's null needs re-measuring")
        for row in self.ROWS:
            self.assertEqual(row["verdict"], pdic.NOT_FOUND)
            self.assertEqual(row["movc_referrers"], pdic.NOT_FOUND)

    def test_the_token_is_not_the_word_the_calibration_rule_forbids(self):
        self.assertNotIn("absent", pdic.NOT_FOUND)
        self.assertIn("this method", pdic.NOT_FOUND)

    def test_the_census_finds_a_referrer_when_one_exists(self):
        """The synthetic counterpart, and the reason the null above is worth
        anything: the same code path, run over a pool that *does* have a
        `MOV DPTR`/`MOVC` pair, has to report it. A method that could only
        return the null would pass the previous case for the wrong reason."""
        string = b"SRC Negotiate done\x00"
        at = 0x5000
        region = region_with_patch({
            at: string,
            0x0100: bytes([pdic.MOV_DPTR, at >> 8, at & 0xFF]),
            0x0103: bytes([0xE4, pdic.MOVC_ABS]),       # clr a; movc a,@a+dptr
        })
        rows = {r["region_offset"]: r for r in
                pdic.string_rows(region, {}, {})}
        row = rows[f"0x{at:04X}"]
        self.assertEqual(row["verdict"], "referenced by this method")
        self.assertEqual(row["dptr_sites"], "1")
        # No listing owns 0x0100 in the synthetic map, and that is a third
        # answer rather than a crash or a guess.
        self.assertIn("outside the committed pd listings", row["movc_referrers"])

    def test_a_dptr_load_with_no_movc_is_counted_separately(self):
        """The #181 collision, kept in two columns on purpose.

        On an 8051 `MOV DPTR,#imm16` is byte-identical whether the pointer
        goes to `MOVX` or `MOVC`. `+INF` at 0x07D1 is float-formatting text
        whose bytes collide with an XDATA address this program uses 76 times,
        so the `dptr_sites` column is large and the `movc_referrers` column
        is empty. Reading the two as one is the mistake the split prevents.
        """
        row = self.by_offset()["0x07D1"]
        self.assertEqual(row["string"], "+INF")
        self.assertGreater(int(row["dptr_sites"]), 1)
        self.assertEqual(row["movc_referrers"], pdic.NOT_FOUND)


    def test_no_code_table_call_site_opens_a_string(self):
        """The most plausible remaining route from a literal to a string, and
        the reason it is measured rather than only listed.

        `0x119C` and `0x11C2` pop the return address into DPTR and read the
        caller's inline argument bytes with `movc`, so every table in the
        program is a literal in the image. If any of those 25 tables began with
        a NUL-terminated printable run, the pool would be referenced by a
        literal after all -- and the §3.1 null would be narrower than the page
        says. It is 0, and the count of sites is what makes the 0 mean
        something.
        """
        tables = pdic.code_table_inline_tables(REGION)
        self.assertEqual(sorted({t[0] for t in tables}),
                         sorted(pdic.CODE_TABLE_DISPATCHERS))
        by_target = collections.Counter(t[0] for t in tables)
        self.assertEqual(by_target[0x119C], 9)
        self.assertEqual(by_target[0x11C2], 16)
        self.assertEqual([t for t in tables if t[3]], [],
                         "a CODE-table call site opens a string, so the "
                         "string-pool null has to be re-measured")

    def test_a_planted_code_table_string_is_found(self):
        """The same non-vacuity the `movc` census gets, for this measurement.

        A synthetic region with a string placed immediately after an
        `lcall 0x11C2` has to be reported: without this case, a
        `code_table_inline_tables()` that always returned `False` would leave
        the 0/9 and 0/16 above green for the wrong reason.

        "Immediately after" is the whole of the fixture, because the dispatcher
        reads from `site + 3` — the return address it popped points at the
        byte after the `lcall`. A string planted anywhere else would not be a
        table at all.
        """
        call = 0x0200
        at = call + 3
        region = region_with_patch({
            at: b"SRC Negotiate done\x00",
            call: bytes([pdic.LCALL, 0x11C2 >> 8, 0x11C2 & 0xFF]),
        })
        rows = [r for r in pdic.code_table_inline_tables(region)
                if r[0] == 0x11C2]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][3],
                        "a table that opens a pool entry was not reported")
        self.assertEqual(rows[0][1] + 3, at)
        self.assertEqual(rows[0][2], b"SRC ")

    def test_a_wider_inline_window_is_a_different_measurement(self):
        """`INLINE_TABLE_BYTES` is a parameter, and the width is quoted.

        A table that opens a string four bytes *after* the call is a shape
        this width cannot see, so the case pins that widening the window does
        not change the answer on this image -- which is what lets the page say
        "these 25 sites and these 4 bytes" rather than "this route".
        """
        narrow = pdic.code_table_inline_tables(REGION, width=4)
        wide = pdic.code_table_inline_tables(REGION, width=8)
        self.assertEqual([t[3] for t in narrow if t[3]], [])
        self.assertEqual([t[3] for t in wide if t[3]], [])


class ReferrerAttribution(unittest.TestCase):
    """Which committed function a site belongs to."""

    def test_a_committed_site_is_attributed_to_its_own_listing(self):
        entry, name, why = pdic.owning_function(0x0F0E, OWNERS, NAMES)
        self.assertEqual(entry, 0x0F0E)
        self.assertEqual(name, "sub_or_cmp_r0_r7")
        self.assertIsNone(why)

    def test_an_address_no_listing_holds_is_a_third_answer(self):
        entry, name, why = pdic.owning_function(0xF7FF, OWNERS, NAMES)
        self.assertIsNone(entry)
        self.assertEqual(why, "outside the committed pd listings")
        self.assertNotIn("absent", why)

    def test_the_latest_starting_owner_wins_and_the_census_says_none_today(self):
        """The rule is stated, so it is measured -- and the measurement is 0.

        The export's bodies can overlap: `pd,0xC873` in
        `ghidra-functions.csv` records that its listing holds bytes belonging
        to the function before it. They do not overlap in the committed tree,
        so `overlaps()` is empty and the tie-break never fires today. Pinning
        the zero is what stops the tie-break from being quietly untested code.
        """
        self.assertEqual(pdic.overlaps(EXTENTS), {})
        owners = pdic.address_owners({0x100: frozenset({0x100, 0x101}),
                                      0x090: frozenset({0x090, 0x100})})
        self.assertEqual(owners[0x100], 0x100,
                         "with two listings holding 0x0100 the later entry "
                         "must win")

    def test_a_broken_attribution_takes_the_suite_red(self):
        """The mutation. `owning_function` is what the `movc_referrers` column
        is built from, and every other case in this file would stay green if it
        returned a constant. So it is pointed at the wrong listing here and the
        pinned answer is asserted to move with it."""
        entry, name, _ = pdic.owning_function(0x0F0E, OWNERS, NAMES)
        broken = dict(OWNERS)
        broken[0x0F0E] = 0x0180
        wrong_entry, wrong_name, _ = pdic.owning_function(0x0F0E, broken,
                                                          NAMES)
        self.assertNotEqual(entry, wrong_entry)
        self.assertNotEqual(name, wrong_name)
        self.assertEqual(wrong_name, "dispatch_r5_write_083b_0300")
        # And the row the synthetic fixture builds really does move, so the
        # break is observable through the public entry point and not only
        # through the private one.
        at = 0x5000
        region = region_with_patch({
            at: b"SRC Negotiate done\x00",
            0x0100: bytes([pdic.MOV_DPTR, at >> 8, at & 0xFF]),
            0x0103: bytes([0xE4, pdic.MOVC_ABS]),
        })
        good = pdic.string_rows(region, {0x0100: 0x0F0E}, NAMES)[0]
        bad = pdic.string_rows(region, {0x0100: 0x0180}, NAMES)[0]
        self.assertIn("sub_or_cmp_r0_r7", good["movc_referrers"])
        self.assertIn("dispatch_r5_write_083b_0300", bad["movc_referrers"])


class Refusals(unittest.TestCase):
    """The three ways this tool declines, which is the calibration half."""

    def test_a_dump_without_the_marker_is_refused_not_reported_empty(self):
        with open(pdic.FIRMWARE, "rb") as f:
            broken = bytearray(f.read())
        broken[pdic.PD_MARKER_OFF:pdic.PD_MARKER_OFF
               + len(pdic.PD_MARKER)] = b"ITE8850-XX"
        with tempfile.NamedTemporaryFile(suffix=".800", delete=False) as f:
            f.write(bytes(broken))
            path = f.name
        try:
            with self.assertRaises(pdic.Refusal) as caught:
                pdic.read_region(path)
        finally:
            os.unlink(path)
        message = str(caught.exception)
        self.assertIn("marker", message)
        self.assertIn("not this image", message)
        for word in ("absent", "empty region", "0 references"):
            self.assertNotIn(word, message,
                             f"a refusal must not read as {word!r}")

    def test_a_dump_too_short_to_hold_the_region_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".800", delete=False) as f:
            f.write(b"\xFF" * 0x1000)
            path = f.name
        try:
            with self.assertRaises(pdic.Refusal) as caught:
                pdic.read_region(path)
        finally:
            os.unlink(path)
        self.assertIn("too short", str(caught.exception))

    def test_an_unreadable_dump_raises_rather_than_reporting(self):
        """`read_region` does not wrap the `open`: a missing file is an
        `OSError` the caller sees, not a `Refusal` dressed up as a
        measurement. The case says which, because a reader has to be able to
        tell "the dump is not this image" from "there is no dump"."""
        with self.assertRaises(FileNotFoundError):
            pdic.read_region(os.path.join(HERE, "no-such-image.800"))

    def test_a_page_with_no_pinned_figures_block_is_refused(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# no block here\n")
            path = f.name
        try:
            with self.assertRaises(pdic.Refusal) as caught:
                pdic.pinned_figures(path)
        finally:
            os.unlink(path)
        self.assertIn("pinned", str(caught.exception))

    def test_a_zip_without_the_named_member_is_refused(self):
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"PK\x05\x06" + b"\x00" * 18)
            path = f.name
        try:
            with self.assertRaises(pdic.Refusal) as caught:
                pdic.provenance(path)
        finally:
            os.unlink(path)
        self.assertIn("member", str(caught.exception))


class Provenance(unittest.TestCase):
    """The vendor half, which is a positive result and is stated as one."""

    def test_the_grep_artefact_is_not_the_answer(self):
        """The marker is not in the container a reader greps, and the reason
        is compression rather than absence.

        The exact shape matters, because the first draft of this case
        asserted "every non-empty member is DEFLATE" and was wrong:
        `GM7MG7P/ecflash.nsh` is *stored*, 29 bytes of plaintext. It does not
        contain the marker either, so the finding survives -- but the sentence
        that carries it does not, and a check that pins the wrong sentence
        would have reddened on a correct page. So the case pins what is true:
        every member big enough to hold the marker is DEFLATE, and the only
        stored one is the `.nsh`.
        """
        import re as _re
        with open(pdic.VENDOR_ZIP, "rb") as f:
            raw = f.read()
        self.assertEqual(_re.search(b"ITE8850-PD", raw), None,
                         "the marker is somehow greppable in the container; "
                         "the DEFLATE-artefact explanation needs revisiting")
        with zipfile.ZipFile(pdic.VENDOR_ZIP) as z:
            members = [i for i in z.infolist() if i.file_size]
            big = [i for i in members if i.file_size >= 1000]
            stored = [i.filename for i in members
                      if i.compress_type != zipfile.ZIP_DEFLATED]
            self.assertTrue(big, "the kit has no member big enough to matter")
            self.assertTrue(all(i.compress_type == zipfile.ZIP_DEFLATED
                                for i in big),
                            "a large member is stored, so the artefact "
                            "argument would be wrong for it")
            self.assertEqual(stored, [pdic.NSH_MEMBER],
                             "the only stored member is the .nsh, and if "
                             f"that changed the sentence changes with it: "
                             f"{stored}")
            self.assertNotIn(b"ITE8850-PD", z.read(pdic.NSH_MEMBER))

    def test_the_ec_member_is_the_committed_file(self):
        self.assertTrue(PROV["ec_member_is_committed"])
        self.assertEqual(PROV["ec_member_sha256"], FIGURES["firmware_sha256"])
        self.assertEqual(PROV["committed_sha256"],
                         "158d1c6416426939a814146b766a44e2ff0e9286b0abd237"
                         "e70e51a0c03399c4")

    def test_the_member_carries_the_region_and_its_marker(self):
        self.assertTrue(PROV["region_in_ec_member"])
        self.assertEqual(PROV["region_sha256"],
                         "30fe7fb8174535d2846e77ca837239a91548748e616cc6f061"
                         "cf151ee230f970")

    def test_the_rom_carries_five_copies_and_one_whole_ec_image(self):
        self.assertEqual(PROV["rom_region_copy_count"], 5)
        self.assertEqual(PROV["rom_region_copies"],
                         ["0x020000", "0x45CA2C", "0x49CA4C", "0x4DCA6C",
                          "0x51CA8C"])
        self.assertEqual(PROV["rom_ec_image_at"], ["0x43CA2C"])
        self.assertTrue(PROV["rom_ec_image_is_committed"])
        self.assertEqual(PROV["rom_size"], 13631488)

    def test_ecflash_nsh_is_read_from_the_zip_and_not_hardcoded(self):
        self.assertEqual(PROV["nsh_text"], "IFUX64.efi GMxMGxx_11.800 0 1")
        with zipfile.ZipFile(pdic.VENDOR_ZIP) as z:
            raw = z.read("GM7MG7P/ecflash.nsh")
        self.assertEqual(PROV["nsh_text"], raw.decode("ascii").strip())
        # One write, the whole file: the sentence the page's answer rests on.
        self.assertEqual(raw.decode("ascii").strip().split()[2:], ["0", "1"])

    def test_the_rom_offsets_are_search_results_and_the_pin_is_a_check(self):
        """The five region copies are a search result and the EC image's offset
        is a checked constant, and the split is deliberate.

        A re-cut ROM that moved the region copies should be *reported*, not
        rejected — so they are not pinned in the tool, and the suite pins their
        offsets by value instead. The EC image's offset is different: the tool
        has to compare the bytes it found there against the committed file to
        say "byte-identical", so it holds the offset as a constant and the
        search is the thing that can disagree with it.
        """
        with zipfile.ZipFile(pdic.VENDOR_ZIP) as z:
            rom = z.read(pdic.ROM_MEMBER)
            ec = z.read(pdic.EC_MEMBER)
        self.assertEqual(pdic.find_all(rom, ec[pdic.REGION_OFF:
                                               pdic.REGION_OFF
                                               + pdic.REGION_LEN]),
                         [0x020000, 0x45CA2C, 0x49CA4C, 0x4DCA6C, 0x51CA8C])
        self.assertEqual(pdic.find_all(rom, ec), [pdic.EC_IN_ROM])
        self.assertNotIn("ROM_REGION_COPIES", vars(pdic),
                         "the region copies are a search result; a constant "
                         "for them would reject a re-cut ROM instead of "
                         "reporting it")
        # And the copy count is what the issue's "both" answer turns on.
        self.assertGreater(PROV["rom_region_copy_count"], 1)

    def test_the_prose_member_count_is_the_measured_one(self):
        """The page's "the other N members" row is prose, so the number has to
        be pinned to what the container holds or it drifts.

        This page said seven for a container with 8 non-empty members of which
        the table names two. Nothing measured the figure, so nothing caught it.
        The tool now derives both numbers from `infolist()`, and this case
        holds the *prose* to them — the count in the page and in the write-up
        is checked against the zip, not against another copy of itself.
        """
        words = {6: "six", 7: "seven", 8: "eight"}
        other = PROV["zip_other_members"]
        self.assertIn(other, words)
        self.assertEqual(other,
                         PROV["zip_member_count"] - 2,
                         "'the other N members' is the container less the two "
                         "the table names; if that ever stops being true, the "
                         "table is quoting a member this case does not know")
        with zipfile.ZipFile(pdic.VENDOR_ZIP) as z:
            named = {pdic.EC_MEMBER, pdic.ROM_MEMBER}
            derived = sum(1 for i in z.infolist()
                          if i.file_size and i.filename not in named)
        self.assertEqual(other, derived)
        for path in (pdic.PAGE, WRITEUP):
            with open(path, encoding="utf-8") as f:
                text = f.read()
            self.assertIn(f"other {words[other]} members", text,
                          f"{path} states the count in prose; it has drifted "
                          f"from the {other} the container holds")


class HostSurface(unittest.TestCase):
    """The dispatch census, and what it is and is not a count of."""

    def test_the_annotation_row_counts(self):
        total, by_type, dispatch = pdic.command_surface(NAMES)
        self.assertEqual(total, 498)
        self.assertEqual(len(dispatch), 18)
        self.assertEqual(by_type["dispatch"], 18)
        self.assertEqual(dispatch[3], (0x119C, "dispatch_code_table"))
        self.assertEqual(dispatch[4], (0x11C2, "dispatch_code_table_2byte_key"))

    def test_the_dispatch_rows_are_sorted_and_unique(self):
        _, _, dispatch = pdic.command_surface(NAMES)
        addrs = [a for a, _ in dispatch]
        self.assertEqual(addrs, sorted(set(addrs)))

    def test_the_host_block_counts_are_site_counts(self):
        host = pdic.host_block_sites(REGION)
        self.assertEqual(host[0xFFE0], 6)
        self.assertEqual(host[0xFF80], 5)
        for addr, n in host.items():
            self.assertEqual(n, len(pdic.dptr_sites(REGION, addr)),
                             f"0x{addr:04X} count is not a MOV DPTR count")

    def test_a_zero_in_the_host_block_is_the_token_not_a_zero(self):
        """`0xFFE3` has no `MOV DPTR` site. The count is a real 0 and the
        report prints the token, because a bare 0 in that table reads as a
        measurement of nothing existing."""
        host = pdic.host_block_sites(REGION)
        self.assertEqual(host[0xFFE3], 0)
        self.assertEqual(pdic.dptr_sites(REGION, 0xFFE3), [])


class FiguresAndCheck(unittest.TestCase):
    """The page's pinned figures, and the `--check` that holds them."""

    def test_the_figures_this_tool_produces(self):
        self.assertEqual(FIGURES["vector_entries"], "6")
        self.assertEqual(FIGURES["used_end"], "0xF7B7")
        self.assertEqual(FIGURES["erased_tail"], "0xF7B8-0xFFFF")
        self.assertEqual(FIGURES["pool_candidates"], "43")
        self.assertEqual(FIGURES["pool_referrers"], "0")
        self.assertEqual(FIGURES["pd_listings"], "535")
        self.assertEqual(FIGURES["pd_listing_overlaps"], "0")
        self.assertEqual(FIGURES["pd_annotation_rows"], "498")
        self.assertEqual(FIGURES["pd_dispatch_rows"], "18")

    def test_the_page_pins_exactly_the_figures_the_tool_derives(self):
        """Both directions, because a one-way check is the drift it exists to
        catch: a figure the page gained and the tool does not know about is
        the case `check_figures()`'s union walk is written for."""
        pinned = pdic.pinned_figures()
        self.assertEqual(set(pinned), set(FIGURES),
                         f"only the page: {sorted(set(pinned) - set(FIGURES))}"
                         f"; only the tool: "
                         f"{sorted(set(FIGURES) - set(pinned))}")
        self.assertEqual(pdic.check_figures(pinned, FIGURES), 0)

    def test_a_wrong_pinned_figure_is_a_failure(self):
        pinned = dict(pdic.pinned_figures())
        pinned["vector_entries"] = "5"
        self.assertEqual(pdic.check_figures(pinned, FIGURES), 1)
        pinned["vector_entries"] = "6"
        pinned["not_a_key_anywhere"] = "1"
        self.assertEqual(pdic.check_figures(pinned, FIGURES), 1)

    def test_the_committed_csv_is_what_this_run_produces(self):
        generated = pdic.csv_table(REGION, OWNERS, NAMES)
        with open(pdic.STRINGS_CSV, newline="") as f:
            self.assertEqual(generated, f.read())

    def test_check_table_fails_on_a_different_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                         newline="") as f:
            f.write("string,region_offset\r\n")
            path = f.name
        try:
            buf, err = io.StringIO(), io.StringIO()
            stdout, stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = buf, err
            try:
                rc = pdic.check_table("a,b\r\n", path)
            finally:
                sys.stdout, sys.stderr = stdout, stderr
            self.assertEqual(rc, 1)
            self.assertIn("regenerate rather than edit", err.getvalue())
        finally:
            os.unlink(path)


class CommandLine(unittest.TestCase):
    """The tool as a command, which is how the page tells a reader to run it.

    A subprocess rather than an in-process call to `main()`: `--check` has to
    be shown reaching the files on disk and setting a process exit code, and
    both of those are facts about the command rather than about the functions
    underneath it.
    """

    def run_tool(self, *args):
        return subprocess.run([sys.executable, TOOL, *args],
                              capture_output=True, text=True, cwd=REPO)

    def run_tool_bytes(self, *args):
        """As `run_tool`, undecoded.

        `--csv` emits the csv module's own CRLF terminator and the committed
        table carries it. A `text=True` subprocess applies universal-newline
        translation and turns the whole file into LF, so the comparison has to
        be on bytes -- and a case that compared the two as text would be
        comparing a different thing from the one `--check` compares.
        """
        return subprocess.run([sys.executable, TOOL, *args],
                              capture_output=True, cwd=REPO)

    def test_the_report_names_the_region_and_prints_every_section(self):
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        for token in ("ITE8850-PD", "0x20000", "6 entries", "43 candidate",
                      "18 row(s) typed 'dispatch'", "0x43CA2C", "not found by "
                      "this method"):
            self.assertIn(token, r.stdout)

    def test_check_is_green_on_this_tree(self):
        r = self.run_tool("--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("reproduces it byte for byte", r.stdout)
        self.assertIn("pinned figure(s) re-derive", r.stdout)

    def test_check_goes_red_on_a_page_whose_figure_is_wrong(self):
        """The end-to-end shape of the drift the pinned block exists for: a
        page that says five vectors while the bytes say six must fail, and it
        has to fail through the command's exit code rather than through a unit
        call, because the exit code is what a gate would read.

        The page is copied and mutated rather than edited in place -- this is
        the committed tree, and a case that edited it to make itself red
        would be a case that made itself permanently red.
        """
        with open(pdic.PAGE, encoding="utf-8") as f:
            text = f.read()
        mutated = text.replace("vector_entries = 6", "vector_entries = 5")
        self.assertNotEqual(text, mutated,
                            "the page no longer pins 'vector_entries = 6', so "
                            "this case has stopped testing the mutation")
        with tempfile.TemporaryDirectory() as d:
            page = os.path.join(d, "pd-image.md")
            with open(page, "w", encoding="utf-8") as f:
                f.write(mutated)
            r = self.run_tool("--check", "--section", "vector", "--page", page)
        self.assertEqual(r.returncode, 1)
        self.assertIn("vector_entries", r.stderr)
        self.assertIn("the bytes say '6'", r.stderr)

    # One figure per `--section` name, so a name that stopped selecting its
    # own section's figures shows here rather than as a green run.
    SECTION_FIGURE = {
        "layout": "used_end = 0xF7B7",
        "vector": "vector_entries = 6",
        "strings": "pool_candidates = 43",
        "command": "host_block = 0xFF80=5",
        "provenance": "prov_zip_members = 8",
    }

    def test_every_section_name_goes_red_on_a_figure_of_its_own(self):
        """`--section` used to match the name as a substring of the key, and
        three of the five names matched nothing: `--section command` over a
        page whose `host_block` was wrong printed "all 0 pinned figure(s)
        re-derive" and exited 0. `strings` was the quiet one -- it caught
        `identity_strings` and missed `pool_candidates` and `pool_referrers`,
        which are the figures §3.1's claim is made of.

        One corrupted figure per name is what keeps that from coming back, and
        a subTest keeps the five failures apart rather than reporting only the
        first.
        """
        with open(pdic.PAGE, encoding="utf-8") as f:
            text = f.read()
        for section, figure in self.SECTION_FIGURE.items():
            with self.subTest(section=section):
                wrong = figure.rsplit(" = ", 1)[0] + " = 999"
                mutated = text.replace(figure, wrong)
                self.assertNotEqual(
                    text, mutated,
                    f"the page no longer pins {figure!r}, so the {section} "
                    f"case has stopped testing the mutation")
                with tempfile.TemporaryDirectory() as d:
                    page = os.path.join(d, "pd-image.md")
                    with open(page, "w", encoding="utf-8") as f:
                        f.write(mutated)
                    r = self.run_tool("--check", "--section", section,
                                      "--page", page)
                self.assertEqual(
                    r.returncode, 1,
                    f"--section {section} exited {r.returncode} on a page "
                    f"whose {figure!r} is wrong")
                self.assertIn(figure.split(" = ")[0], r.stderr)

    def test_a_section_name_that_selects_no_figure_is_a_refusal(self):
        """The other half: a name that reaches nothing must say so.

        `select_section()` cannot be reached through the command line for any
        name argparse accepts, which is the point -- argparse's `choices` and
        the mapping are two guards, and this case is what holds the second one
        if a prefix is ever narrowed until it matches nothing.
        """
        self.assertEqual(pdic.select_section("all", FIGURES), FIGURES)
        with self.assertRaises(pdic.Refusal):
            pdic.select_section("strings", {"used_end": "0xF7B7"})

    def test_every_derived_figure_is_reachable_by_a_section_name(self):
        """A key no name selects is unreachable except by `all`, and no
        non-empty check can see it -- `select_section()` refuses an *empty*
        section, not one that is merely missing a figure.

        This is not hypothetical: the first cut of SECTIONS wrote the vector
        prefix as `vector_` and silently dropped `vectors`, whose key has no
        underscore, so `--section vector` checked three of the table's four
        figures and reported a pass.
        """
        orphans = sorted(k for k in FIGURES
                         if not any(pdic.in_section(k, s)
                                    for s in pdic.SECTIONS))
        self.assertEqual(orphans, [], f"no --section name reaches {orphans}")

    def test_a_page_that_gained_a_figure_is_also_red(self):
        """The other direction, and the one a one-way check cannot catch: a
        figure the page has and the tool does not derive is drift too."""
        with open(pdic.PAGE, encoding="utf-8") as f:
            text = f.read()
        mutated = text.replace("# pd-image-census pinned figures\n",
                               "# pd-image-census pinned figures\n"
                               "invented_figure = 7\n")
        self.assertNotEqual(text, mutated)
        with tempfile.TemporaryDirectory() as d:
            page = os.path.join(d, "pd-image.md")
            with open(page, "w", encoding="utf-8") as f:
                f.write(mutated)
            r = self.run_tool("--check", "--page", page)
        self.assertEqual(r.returncode, 1)
        self.assertIn("invented_figure", r.stderr)

    def test_csv_mode_is_the_committed_table(self):
        r = self.run_tool_bytes("--csv")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        with open(pdic.STRINGS_CSV, "rb") as f:
            self.assertEqual(r.stdout, f.read())

    def test_help_block(self):
        r = self.run_tool("--help")
        self.assertEqual(r.returncode, 0)
        for flag in ("--check", "--self-test", "--csv", "--section"):
            self.assertIn(flag, r.stdout)

    def test_a_dump_without_the_marker_exits_1_with_the_refusal_on_stderr(self):
        with open(pdic.FIRMWARE, "rb") as f:
            broken = bytearray(f.read())
        broken[pdic.PD_MARKER_OFF] = ord("X")
        with tempfile.NamedTemporaryFile(suffix=".800", delete=False) as f:
            f.write(bytes(broken))
            path = f.name
        try:
            r = self.run_tool("--firmware", path)
        finally:
            os.unlink(path)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout, "")
        self.assertIn("not this image", r.stderr)
        self.assertNotIn("absent", r.stderr)

    def test_self_test_runs_a_suite_and_hands_back_its_exit_code(self):
        """The subprocess path, on a throwaway suite rather than this one.

        Running it against this file would recurse -- suite -> tool -> suite --
        and the obvious way to stop that, an environment variable, fires on
        the *direct* child, which is exactly the run this case is trying to
        reach. So `self_test()` takes the suite path as a parameter and this
        case points it at a two-case file, and the two things worth checking
        are both reachable that way: that a passing suite yields 0, and that a
        failing one yields non-zero. The second is the half that matters -- a
        `--self-test` that always returned 0 would be a gate-shaped hole.
        """
        with tempfile.TemporaryDirectory() as d:
            passing = os.path.join(d, "green.py")
            with open(passing, "w") as f:
                f.write("import unittest\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_ok(self):\n"
                        "        self.assertTrue(True)\n"
                        "if __name__ == '__main__':\n"
                        "    unittest.main()\n")
            failing = os.path.join(d, "red.py")
            with open(failing, "w") as f:
                f.write("import unittest\n"
                        "class T(unittest.TestCase):\n"
                        "    def test_red(self):\n"
                        "        self.assertTrue(False)\n"
                        "if __name__ == '__main__':\n"
                        "    unittest.main()\n")
            self.assertEqual(pdic.self_test(passing), 0)
            self.assertNotEqual(pdic.self_test(failing), 0)

    def test_the_self_test_flag_reaches_self_test(self):
        """The flag wiring, without recursing into the real suite.

        `sys.argv` is patched and `self_test` is stood in for, so the case
        proves `main()` dispatches `--self-test` to that function and does not
        prove the suite's own name -- which is a constant two lines above, and
        checking a constant against itself is the kind of case that reads as
        coverage and is not.
        """
        calls = []
        saved_argv, saved = sys.argv, pdic.self_test
        pdic.self_test = lambda *a, **k: calls.append(a) or 0
        sys.argv = [TOOL, "--self-test"]
        try:
            self.assertEqual(pdic.main(), 0)
        finally:
            sys.argv, pdic.self_test = saved_argv, saved
        self.assertEqual(calls, [()])


if __name__ == "__main__":
    unittest.main(verbosity=2, argv=[sys.argv[0]])
