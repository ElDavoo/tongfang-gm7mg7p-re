#!/usr/bin/env python3
"""Offline checks for the `0x07C5` bit identification: bit 5 is the whisper-mode
main switch and bit 4 the safety-protect skip, replayed from the committed `.cs`.

`docs/findings/07c5-whms-bit5-vs-bit4.md` is the write-up. Its subject is a
byte with four service setters on it, none of which used to be tied to a named
bit: the DSDT calls bit 5 `WHMS`, the EC's USER fan path branches on bit 4, and
until this nothing in the tree said whether those were one field or two. They
are two, and each has a name.

**The transcription is held against the file it came from, not derived from it
at test time.** Every setter here is the same read-modify-write, `(Data & mask)
+ addend`, and the mask and the addends are what identify the bit. Reading them
out of the `.cs` and asserting the result would be asserting that the parser
works. So the constants below are written down by hand, the tests replay them
over every prior byte value, and a separate class re-derives them from the
committed decompile and fails if the two disagree. A re-export that moved a
mask goes red on `TheDecompileStillSaysThis` instead of quietly re-basing the
identification on whatever the new file happens to say.

**The retraction is held as wording, and the wrong wording has to survive.**
`TheRetractionIsVisible` asserts that the `WHMS` note still spells the sentence
that was withdrawn, because `CLAUDE.md`'s calibration rule and
`docs/findings.md`'s §4a-4d pattern both require a retraction to leave the
wrong version readable with a correction beside it -- a note that quietly
dropped the claim would pass a test that only looked for its absence, and would
be the one thing the rule forbids. What is asserted beside that is that the
correction is there, that it says why, and that it names a replacement that is
not the oracle the old sentence leaned on.

`TheCensusCannotSeparateTheBits` holds the reason the answer came from the
`.cs` and not from the generated table: every write row `ec-callsites.csv`
carries for this byte records the masked result variable, so the table names no
bit of this byte at all. That is a property of the census and it moves if the
census changes, which is the point -- a red there means the write-up's sentence
about the census needs rewording, not that a test broke.

Nothing here opens an EC, calls the vendor service or reads hardware: the
subject is a reading of committed `.cs`, `registers.yaml` and a generated CSV,
and no register is read back anywhere in this file.
"""
import csv
import re
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SERVICE = REPO / "windows" / "decompiled" / "v3.1.39.0" / "GCUService"
CALLSITES = REPO / "windows" / "decompiled" / "v3.1.39.0" / "ec-callsites.csv"
REGISTERS = REPO / "ec" / "annotations" / "registers.yaml"
WRITEUP = REPO / "docs" / "findings" / "07c5-whms-bit5-vs-bit4.md"

# The byte, as the vendor spells it: `ADDR_AP_OEM_BYTE5 = 1989` in
# windows/decompiled/v3.1.39.0/GCUService/Define/ECSpec.cs. Decimal and hex,
# because the setters use the first and every annotation here the second, and a
# transcription that conflated them would not fail loudly.
ADDR = 1989

# (file under GCUService, method, mask, addend when the argument is 1, addend
# otherwise). Transcribed by hand from the four `.cs` files named; see the
# module docstring for why they are constants rather than parse results.
WHISPER_MAIN = ("GCUService.MyFan.Overclocking/GpuFeatures.cs",
                "SetGpuWhisperModeMainSwitch", 0x9F, 0x60, 0x40)
WHISPER_CML = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5_CML.cs",
               "SetGpuWhisperModeSwitch", 0x9F, 0x60, 0x40)
WHISPER_NV = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5_NV.cs",
              "SetGpuWhisperModeSwitch", 0x9F, 0x60, 0x40)
WHISPER_NORMAL = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5_Normal.cs",
                  "SetGpuWhisperModeSwitch", 0x9F, 0x60, 0x40)
PROTECT_OFFICE = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5.cs",
                  "SkipOfficeModeSafetyProtect", 0xEF, 0x10, 0x00)
PROTECT_CML = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5_CML.cs",
               "SkipFanSafetyAbnormalProtection", 0xEF, 0x10, 0x00)
PROTECT_NV = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5_NV.cs",
              "SkipFanSafetyAbnormalProtection", 0xEF, 0x10, 0x00)
PROTECT_NORMAL = ("MyControlCenter.MyFan/MyFanManager_RamFan1p5_Normal.cs",
                  "SkipFanSafetyAbnormalProtection", 0xEF, 0x10, 0x00)
FAN_SPLIT = ("MyControlCenter.MyFan.FanTable/FanTable_Manager1p5.cs",
             "SetEcFanControlRespective", 0x7F, 0x80, 0x00)

WHISPER_SETTERS = (WHISPER_MAIN, WHISPER_CML, WHISPER_NV, WHISPER_NORMAL)
PROTECT_SETTERS = (PROTECT_OFFICE, PROTECT_CML, PROTECT_NV, PROTECT_NORMAL)

# The bit positions the finding is about, named rather than written as literals
# at each use so that a reader who disagrees has one place to disagree with.
BIT_SAFETY_SKIP = 4
BIT_WHMS = 5
BIT_UNNAMED_HIGH = 6

# The wrong sentence the `WHMS` note carried, in the spelling YAML's folded
# scalar gives it back. Kept here so the retraction has something to be a
# retraction of: asserting only that the claim is gone would pass on a note that
# deleted it, which is the edit the calibration rule rules out.
RETRACTED_SENTENCE = (
    'That bit is independently pinned by windows/tools/gpu_block_watch.py, '
    'which watches this byte for exactly this field ("WHMS b5", citing '
    'dsdt.dsl:52243 and this row), and the two agree from opposite ends of '
    'the stack.')

RETRACTION_MARK = "RETRACTED 2026-10-05 (issue #1260)"

# `SingleZone` reaches this byte through `ReadECRAM`/`WriteECRAM` rather than
# `EcCtrl`, which is the receiver `ec_callsites.py`'s call-site pattern is built
# around, so the census cannot see it and it is named here instead. `mask` is
# its `Value &= 0xF8`; the addend is its `Value += BreathingColorIndex`, whose
# cases run 1 to 4 over an index argument the caller passes.
RGB_KEYBOARD = ("MyControlCenter.MyRgbKeyboard/SingleZone.cs",
                "StartBreathingMode", 0xF8)

MASK = re.compile(r"byte b = (\d+);")
# `byte b2 = 0;` is a declaration and must not be read as an assignment, hence
# the lookbehind: every method here declares `b2` and then assigns it, and the
# declaration's `0` is not an addend any branch ever takes.
B2_ASSIGN = re.compile(r"(?<!byte )b2\s*=\s*(?P<rhs>[^;]*);")
# The conditional's own operand, cut out before the addends are counted:
# `b2 = (byte)((status != 1) ? 64 : 96)` contributes 64 and 96, and not the
# `1` the predicate compares against. Without this the addend set would carry a
# spurious 1 and the transcription check below would go red on a file that had
# not changed.
PREDICATE = re.compile(r"[=!]=\s*(?:0x[0-9a-fA-F]+|\d+)")
SIGNATURE = re.compile(r"^[ \t]*(?:public|private|internal|protected|static)[^\n]*?"
                       r"\b(?P<name>\w+)\s*\(", re.M)

# One conditional, spelled several ways across the tree: an `if`/`else` in
# GpuFeatures, and a ternary in the RamFan1p5 siblings in both of its orders,
# plus the `bool` predicate `SetEcFanControlRespective` uses. Reading only one
# would let a suite test GpuFeatures' transcription and silently apply it to
# the siblings, which is the mistake the entries above exist to make
# impossible. A body in a spelling none of these matches raises rather than
# falling through to a default, so a new shape is a red and not a pass.
IF_ELSE = re.compile(r"if \(status == 1\) \{ b2 = (\d+); \} "
                     r"else \{ [^}]*b2 = (\d+);")
TERNARY_NE = re.compile(r"b2 = \(byte\)\(\(status != 1\) \? (\d+) : (\d+)\);")
TERNARY_EQ = re.compile(r"b2 = \(byte\)\(\(status == 1\) \? (\d+) : (\d+)\);")
# `FanTable_Manager1p5.SetEcFanControlRespective` takes a `bool` rather than an
# int, so its predicate is the argument and there is no `== 1` to match on.
# Falling back to this form is what lets it be transcribed and checked the same
# way as the rest instead of being the one setter the suite skips.
TERNARY_BOOL = re.compile(r"b2 = \(byte\)\((?P<pred>\w+) \? (\d+) : (\d+)\);")


def method_body(rel, name):
    """The `{ ... }` body of one method, by brace counting from its signature.

    The signature match is anchored on an access modifier so that the
    `LogCtrl.TraceMessage("...", "SkipFanSafetyAbnormalProtection", ...)` label
    every one of these methods carries cannot be mistaken for the definition --
    those setters' own bodies name themselves, and a name-only search would
    find the log line first.
    """
    src = (SERVICE / rel).read_text(encoding="utf-8")
    sig = None
    for m in SIGNATURE.finditer(src):
        if m.group("name") == name:
            sig = m
            break
    if sig is None:
        raise AssertionError("%s: no method %s" % (rel, name))
    start = src.index("{", sig.end())
    depth = 0
    for i in range(start, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise AssertionError("%s: %s never closes" % (rel, name))


def rmw_arith(body):
    """(mask, addends) -- the whole of what this read-modify-write does.

    `addends` is every integer a `b2 = ...` assignment mentions, flattened and
    in source order. Which arm each belongs to is `arm_addends`, and that is
    only read where the arm is the claim; the bit-6 sweep below wants the set,
    not the pairing.
    """
    mask = MASK.search(body)
    if mask is None:
        return None
    addends = []
    for m in B2_ASSIGN.finditer(body):
        rhs = PREDICATE.sub("", m.group("rhs"))
        addends.extend(int(n) for n in re.findall(r"\d+", rhs))
    return int(mask.group(1)), tuple(addends)


def arm_addends(body):
    """(addend when the argument is true, addend otherwise) for this shape."""
    flat = re.sub(r"\s+", " ", body)
    m = IF_ELSE.search(flat)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = TERNARY_NE.search(flat)
    if m:
        # `status != 1 ? a : b` puts the argument-is-1 arm second.
        return int(m.group(2)), int(m.group(1))
    m = TERNARY_EQ.search(flat)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = TERNARY_BOOL.search(flat)
    if m:
        return int(m.group(2)), int(m.group(3))
    raise AssertionError("no two-armed conditional in this body")


def replay(prior, mask, addend):
    """What the service writes: C# `(Data & mask) + addend` cast to `byte`.

    The cast truncates, which is why the sweeps below go over every prior byte
    rather than a sample: an addend big enough to carry into bit 7 would show
    up as a bit the mask was supposed to preserve having moved, and only on the
    priors where the sum overflows -- a sample is not sure to include one.
    """
    return ((prior & mask) + addend) & 0xFF


def bit(value, index):
    return (value >> index) & 1


def census_writes():
    """Every method `ec-callsites.csv` records as writing this byte.

    Read from the census rather than listed here, so a setter added to the
    decompile cannot slip past the bit sweep below without a red: the census is
    the tool that claims completeness for literal-addressed `EcCtrl` writes, so
    taking its population is what makes "nothing clears this bit" a statement
    about every writer the tree knows of.
    """
    with CALLSITES.open() as f:
        return [r for r in csv.DictReader(f)
                if r["addr"].lower() == "0x%04x" % ADDR and r["op"] == "write"]


def whms_note():
    """The `WHMS` row's `note:`, folded the way YAML folds it."""
    doc = yaml.safe_load(REGISTERS.read_text(encoding="utf-8"))
    for row in doc["registers"]:
        if row.get("name") == "WHMS":
            return row
    raise AssertionError("registers.yaml has no WHMS row")


class TheByte(unittest.TestCase):
    """The decimal the setters use and the hex the annotations use are one."""

    def test_the_vendor_decimal_is_the_annotated_hex(self):
        self.assertEqual(0x07C5, ADDR)


class WhisperMainSwitchIsBitFive(unittest.TestCase):
    """`0x9F` and the two addends put the whisper switch on bit 5.

    Each setter is swept over every prior value of the byte rather than a
    sample, because the claim is not "bit 5 is set on this input" but "bit 5
    follows the argument whatever was there" -- which is a statement about the
    mask clearing the position first, and a mask that failed to clear it would
    pass on any prior byte that happened to agree with the addend.
    """

    def test_bit_five_follows_the_argument_from_every_prior_value(self):
        for rel, name, mask, on, off in WHISPER_SETTERS:
            for prior in range(256):
                self.assertEqual(
                    1, bit(replay(prior, mask, on), BIT_WHMS),
                    "%s: 0x%02X with the argument 1" % (name, prior))
                self.assertEqual(
                    0, bit(replay(prior, mask, off), BIT_WHMS),
                    "%s: 0x%02X with the argument 0" % (name, prior))

    def test_both_arms_set_the_bit_the_firmware_clears(self):
        for rel, name, mask, on, off in WHISPER_SETTERS:
            for prior in range(256):
                self.assertEqual(
                    1, bit(replay(prior, mask, on), BIT_UNNAMED_HIGH),
                    "%s: 0x%02X with the argument 1" % (name, prior))
                self.assertEqual(
                    1, bit(replay(prior, mask, off), BIT_UNNAMED_HIGH),
                    "%s: 0x%02X with the argument 0" % (name, prior))

    def test_the_mask_preserves_every_field_the_setter_does_not_name(self):
        for rel, name, mask, on, off in WHISPER_SETTERS:
            for prior in range(256):
                after = replay(prior, mask, on)
                for index in (0, 1, 2, 3, BIT_SAFETY_SKIP, 7):
                    self.assertEqual(
                        bit(prior, index), bit(after, index),
                        "%s: bit %d moved under 0x%02X" % (name, index, prior))

    def test_the_mask_clears_both_positions_the_addend_then_sets(self):
        # What makes `+ addend` equivalent to `| addend` here, and what lets the
        # sweep above claim the new state is independent of the old: the mask
        # has to leave the addend's own bits at zero or a carry could reach
        # into bit 7.
        for rel, name, mask, on, off in WHISPER_SETTERS:
            self.assertEqual(0, mask & on & ~BIT_WHMS)
            self.assertEqual(0, mask & off & ~BIT_UNNAMED_HIGH)
            self.assertEqual(0, on & 0x80)
            self.assertEqual(0, off & 0x80)


class BitFourIsItsOwnField(unittest.TestCase):
    """`0xEF` and `0x10` put the safety-protect skip on bit 4, and only there."""

    def test_bit_four_follows_the_safety_protect_argument(self):
        for rel, name, mask, on, off in PROTECT_SETTERS:
            for prior in range(256):
                self.assertEqual(
                    1, bit(replay(prior, mask, on), BIT_SAFETY_SKIP),
                    "%s: 0x%02X with the argument 1" % (name, prior))
                self.assertEqual(
                    0, bit(replay(prior, mask, off), BIT_SAFETY_SKIP),
                    "%s: 0x%02X with the argument 0" % (name, prior))

    def test_the_whisper_bit_is_not_moved_by_either_safety_protect_setter(self):
        # The identification, stated as the thing that would falsify it: if one
        # setter moved both bits, "two fields on one byte" would be wrong and
        # the note's retraction would have replaced a false claim with another.
        for rel, name, mask, on, off in PROTECT_SETTERS:
            for prior in range(256):
                for addend in (on, off):
                    self.assertEqual(
                        bit(prior, BIT_WHMS),
                        bit(replay(prior, mask, addend), BIT_WHMS),
                        "%s: bit 5 moved under 0x%02X" % (name, prior))

    def test_nothing_else_on_the_byte_moves(self):
        for rel, name, mask, on, off in PROTECT_SETTERS:
            for prior in range(256):
                after = replay(prior, mask, on)
                for index in (0, 1, 2, 3, BIT_WHMS, BIT_UNNAMED_HIGH, 7):
                    self.assertEqual(
                        bit(prior, index), bit(after, index),
                        "%s: bit %d moved under 0x%02X" % (name, index, prior))


class TheFanTableSetterIsBitSeven(unittest.TestCase):
    """The byte's third named field, unchanged here and checked for the same
    reason: it is the one setter whose mask `0x7F` is checked against the file,
    so a re-export moving it cannot pass silently either."""

    def test_its_arm_split_puts_the_table_flag_on_bit_seven(self):
        rel, name, mask, on, off = FAN_SPLIT
        for prior in range(256):
            self.assertEqual(1, bit(replay(prior, mask, on), 7))
            self.assertEqual(0, bit(replay(prior, mask, off), 7))
            for index in (0, 1, 2, 3, BIT_SAFETY_SKIP, BIT_WHMS,
                          BIT_UNNAMED_HIGH):
                self.assertEqual(bit(prior, index),
                                 bit(replay(prior, mask, on), index))


class NoCommittedWriterClearsTheHighBit(unittest.TestCase):
    """Both whisper arms set bit 6 and the EC's `0x83FF` clears it; nothing in
    the service does. Held as a sweep over the census's whole population of
    writers rather than as a sentence, because "nothing does" is the claim most
    likely to be broken by the next setter that lands -- and it is the half of
    the bit-6 observation that this repository can know without the machine.
    """

    def test_no_write_of_this_byte_takes_bit_six_from_set_to_clear(self):
        for row in census_writes():
            arith = rmw_arith(method_body(row["file"], row["method"]))
            self.assertIsNotNone(
                arith, "%s.%s is not the read-modify-write shape" %
                (row["file"], row["method"]))
            mask, addends = arith
            self.assertTrue(addends, "%s.%s writes no addend" %
                            (row["file"], row["method"]))
            for addend in addends:
                for prior in range(256):
                    if not bit(prior, BIT_UNNAMED_HIGH):
                        continue
                    self.assertEqual(
                        1, bit(replay(prior, mask, addend), BIT_UNNAMED_HIGH),
                        "%s.%s cleared bit 6 from 0x%02X"
                        % (row["method"], addend, prior))

    def test_the_census_covers_every_setter_the_write_up_names(self):
        # The sweep above is only as wide as the census, so the census and the
        # write-up are held to the same population: a setter named in one and
        # missing from the other is a red here rather than a silent narrowing.
        methods = {r["method"] for r in census_writes()}
        for _rel, name, _m, _on, _off in (WHISPER_SETTERS + PROTECT_SETTERS
                                          + (FAN_SPLIT,)):
            self.assertIn(name, methods)


class TheRGBKeyboardWriter(unittest.TestCase):
    """The one writer the census cannot see, checked by hand because it is.

    `ec_callsites.py` matches on the `EcCtrl.Read`/`Write` receivers, and this
    method calls `ReadECRAM`/`WriteECRAM` on its own class, so the sweep over
    the census's population does not cover it. Naming it here is what keeps
    "nothing in the service clears bit 6" true of the tree rather than of the
    census.
    """

    def test_its_mask_clears_the_low_field_and_preserves_everything_above(self):
        rel, name, mask = RGB_KEYBOARD
        self.assertRegex(method_body(rel, name),
                         re.compile(r"Value &= 0x%x;" % mask, re.IGNORECASE))
        # Stated as the claim rather than the arithmetic: the mask clears the
        # three low bits the breathing index lives in and preserves every bit
        # above them, so this writer cannot reach bit 6 either.
        cleared = [i for i in range(8) if not bit(mask, i)]
        self.assertEqual([0, 1, 2], cleared)


class TheCensusCannotSeparateTheBits(unittest.TestCase):
    """Why the answer came from the `.cs` and not from the generated table.

    `ec-callsites.csv` records the address, the direction and the argument
    expressions as written. Every setter on this byte writes the variable
    holding `(Data & mask) + addend`, so the row names no bit of the byte --
    which is the reason the census could not have answered the question the
    issue asks, and a reason worth holding so it does not go quiet if the
    census changes shape.
    """

    def test_every_write_row_records_the_masked_variable(self):
        refs = {r["value_expr"] for r in census_writes()}
        self.assertEqual(
            {"b3"}, refs,
            "the census no longer records only the masked variable for %04X, "
            "so docs/findings/07c5-whms-bit5-vs-bit4.md's sentence about it "
            "needs rewording" % ADDR)


class TheDecompileStillSaysThis(unittest.TestCase):
    """The constants above still match the committed `.cs`, or they are stale.

    The tests in this file replay transcribed masks; this class is what stops a
    transcription from quietly becoming fiction. It reads each body and
    compares against the constants, so a re-export that moves a mask, swaps an
    addend or reorders a conditional is red here and the write-up's table is
    red with it.
    """

    ALL = WHISPER_SETTERS + PROTECT_SETTERS + (FAN_SPLIT,)

    def test_the_mask_is_still_the_one_transcribed(self):
        for rel, name, mask, _on, _off in self.ALL:
            found = rmw_arith(method_body(rel, name))
            self.assertIsNotNone(found, "%s: no `byte b = ...` in %s"
                                 % (rel, name))
            self.assertEqual(mask, found[0], "%s in %s" % (name, rel))

    def test_the_two_arms_are_still_the_ones_transcribed(self):
        for rel, name, _mask, on, off in self.ALL:
            self.assertEqual(
                (on, off), arm_addends(method_body(rel, name)),
                "%s in %s" % (name, rel))

    def test_the_addends_in_the_body_are_the_two_transcribed_ones(self):
        # Guards the pairing above against a third branch appearing: a body
        # with a mask and two addends but a conditional that is not the one
        # `arm_addends` reads would otherwise be paired by position alone.
        for rel, name, _mask, on, off in self.ALL:
            _mask, addends = rmw_arith(method_body(rel, name))
            self.assertEqual({on, off}, set(addends),
                             "%s in %s" % (name, rel))


class TheRetractionIsVisible(unittest.TestCase):
    """The wrong sentence survives, with a correction beside it.

    Held this way round on purpose. `CLAUDE.md` puts a retraction in place --
    the wrong version left readable with the correction next to it -- so a test
    that asserted only the absence of the old claim would be satisfied by the
    edit the rule forbids. These cases require both halves: the sentence is
    still there, and so is the correction, and the correction names why the
    claim could not have held and what stands in its place.
    """

    def note(self):
        return whms_note()["note"]

    def test_the_withdrawn_sentence_is_still_readable(self):
        self.assertIn(RETRACTED_SENTENCE, self.note())

    def test_it_is_marked_retracted_before_it_is_quoted(self):
        note = self.note()
        self.assertIn(RETRACTION_MARK, note)
        self.assertLess(note.index(RETRACTION_MARK),
                        note.index(RETRACTED_SENTENCE),
                        "the retraction marker must precede the sentence it "
                        "withdraws, or the note reads as claiming it")

    def test_the_correction_says_why_the_claim_could_not_hold(self):
        note = self.note()
        self.assertIn("test_every_registers_yaml_status_is_verbatim", note)
        self.assertIn("corroborate", note)

    def test_the_correction_names_a_replacement_that_is_not_the_old_oracle(self):
        note = self.note()
        self.assertIn("SetGpuWhisperModeMainSwitch", note)
        self.assertIn("0x9F", note)

    def test_it_points_at_a_write_up_that_exists(self):
        self.assertIn(WRITEUP.name, self.note())
        self.assertTrue(WRITEUP.exists(), "%s is missing" % WRITEUP)

    def test_the_status_did_not_move(self):
        # Held because a name plus a matching setter is agreement about a bit
        # position and not a behavioural confirmation; only a live test could
        # move this off `present-untested`, and no live test ran.
        self.assertEqual("present-untested", whms_note()["status"])


class TheOracleNoLongerRestsOnTheCopy(unittest.TestCase):
    """`dsdt_ec_fields.py`'s `ORACLES` row for this byte, re-anchored.

    The same circularity reached the tool's own comment, which named
    `gpu_block_watch.py` as the reading from the other end of the stack and
    quoted a tuple spelling `NO_ROW` that the watch table no longer holds. The
    row now names the service's mask arithmetic and the EC's own masks, which
    are in files this tool never reads.
    """

    def _why(self):
        import dsdt_ec_fields
        rows = [r for r in dsdt_ec_fields.ORACLES if r[0] == ADDR]
        self.assertEqual(1, len(rows), "one ORACLES row for this byte")
        return rows[0][4]

    def test_the_row_still_pins_bit_five(self):
        import dsdt_ec_fields
        rows = [r for r in dsdt_ec_fields.ORACLES if r[0] == ADDR]
        # (address, bit, width, name, why) -- bit is the second field, and
        # width the third, which is the order the table is written in.
        self.assertEqual(5, rows[0][1])
        self.assertEqual(1, rows[0][2])
        self.assertEqual("WHMS", rows[0][3])

    def test_the_replacement_is_not_the_watch_table(self):
        self.assertNotIn("gpu_block_watch", self._why())

    def test_the_replacement_names_the_setters_mask(self):
        why = self._why()
        self.assertIn("SetGpuWhisperModeMainSwitch", why)
        self.assertIn("0x9F", why)


if __name__ == "__main__":
    unittest.main()