#!/usr/bin/env python3
r"""That `t1wr_sites.py`'s answer is a measurement, and that its zero is not vacuous.

The subject is `windows/tools/t1wr_sites.py` and what it reports is mostly a
**negative**: that no committed Windows input carries a call site for the
`0x9C40A4DC` IOCTL, and therefore that no arm of `T1WR` is reachable from one.
A negative is only worth as much as the method that produced it, so this suite
is built in the order `CLAUDE.md` asks for -- **the positive control first**, and
the tree's own zero only after it. `PositiveControlTests` builds a scratch tree
holding `WriteACPI(2621482204u, …)` in all three spellings a real call site
could take and holds that the tool finds every one; a control planted and missed
would make every other case here a green run over a broken search, and would
make the committed tree's zero unreadable rather than merely absent.

**The collision case, both directions**, is the second thing this suite is for.
`t1wr_callers.py` rejected thirteen of `T1WR`'s nineteen `Arg0` values because
`0x81`-`0x85` collide with `ECSpec.User_Fan_Level1`..`Level5` and `0x83`-`0x85`
with ILSpy's `Invalid MethodBodyBlock` markers. `CollisionTests` holds that a
site writing `0x84` into a `T1WR` buffer reaches arm `0x84` *even though the
same literal is a fan level elsewhere in the same tree* -- the assertion that
the new method reaches what the old one could not. It also holds the mirror: a
fan-level constant that is not a `T1WR` call site reaches nothing, so the
collision test cannot be passed by a tool that matches `0x84` anywhere.

`LayoutTests` re-derives the buffer slices from the committed
`windows/decompiled/native/ACPIDriver.c` and asserts them against the tool's own
reading, because "a caller's `Arg0` is the first four bytes of its buffer" is a
claim about a decompile that a re-export can change. If it changes, `Arg0` means
something else and every other case here would still pass while answering a
different question.

`RedundantArmTests` holds the one place a naive reading of `T1WR_ARMS` is
wrong: `0x71` is two arms, the first shadows the second, and a caller passing
`0x71` reaches `:50657` and *cannot* reach `:50667`.

**No figure of the tree is asserted.** What is held is the claim: which
`ACPIDriver` codes the decrypted service can send (a named set, not a count),
that none of the six Temp* codes is among them, that the CPU power-limit writes
route through `ECRW`, and that the readability probes came back non-zero. The
counts move when a legitimate re-export lands, and a suite holding one would go
red on exactly the change that is supposed to be reviewable --
`tools/test_readme_suite_table.py` carries the same lesson at its own scale.

Nothing here opens an EC, calls the vendor driver, or reads hardware: the
subject is a text and disassembly scan of committed files plus fixtures written
to a temp directory.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "ec" / "tools"))

import dsdt_ec_fields as D           # noqa: E402  (needs the sys.path entry)
import t1wr_sites as S               # noqa: E402

REPO = HERE.parent.parent

DRIVER_DECOMPILE = "windows/decompiled/native/ACPIDriver.c"
SERVICE = "windows/decompiled/v3.1.39.0/GCUService/MyECIO/AcpiCtrl.cs"

# A `WriteACPI`-shaped wrapper and one caller, in the ILSpy spelling. The
# buffer's first word is what makes this fixture worth having: the tool has to
# read `new int[2] { addr, data }` out of the wrapper's body to learn that
# argument 1 is the `Arg0` the `0x9C40A4DC` handler will see. A fixture that
# passed the Arg0 directly would not test that, and that is the whole of the
# reading key.
WRAPPER = """\tprivate void WriteACPI(uint ioctrl, int addr, int data)
\t{
\t\tint[] source = new int[2] { addr, data };
\t\tIntPtr intPtr2 = Marshal.AllocHGlobal(8);
\t\tMarshal.Copy(source, 0, intPtr2, 2);
\t\tint outBuffer = 0;
\t\tDeviceIoControl(intPtr, ioctrl, intPtr2, 8, ref outBuffer, 4, out var _, IntPtr.Zero);
\t}
"""


def fixture(call_line, extra=""):
    """One class holding the wrapper and a single caller at `call_line`."""
    return ("\tpublic const uint IOCTL_GPD_ACPI_TMPWRITE1 = 2621482204u;\n"
            + extra
            + WRAPPER
            + "\tpublic void Write(string ReadName, ushort Addr, byte Data)\n"
            + "\t{\n\t\t" + call_line + "\n\t}\n")


def sites_of(source, label="fixture.cs"):
    """The tool's sites over one source, with its const table."""
    return S.call_sites([(label, source)], S.const_table([source]))


class PositiveControlTests(unittest.TestCase):
    """The method finds a site that is definitely there.

    Everything else in this suite is a negative, and a negative whose method
    cannot be shown to find a planted site is worthless. These come first for
    that reason.
    """

    def assertFinds(self, source, want_ioctl, want_arg0):
        sites = [s for s in sites_of(source) if s["ioctl"] == want_ioctl]
        self.assertTrue(sites, f"no site carrying 0x{want_ioctl:08X} was found "
                               f"in:\n{source}")
        self.assertIn(want_arg0, [s["arg0"] for s in sites],
                      f"no site carried Arg0 0x{want_arg0:04X}; got "
                      f"{[(s['file_line'], s['arg0']) for s in sites]}")

    def test_a_decimal_literal_call_site_is_found(self):
        self.assertFinds(fixture("WriteACPI(2621482204u, 0x84, Data);"),
                         0x9C40A4DC, 0x84)

    def test_the_const_name_spelling_is_the_same_site(self):
        # The whole reason there is a const table: ILSpy emitted this constant
        # as a declaration and a caller could use either spelling.
        self.assertFinds(
            fixture("WriteACPI(IOCTL_GPD_ACPI_TMPWRITE1, 0x84, Data);"),
            0x9C40A4DC, 0x84)

    def test_a_hex_literal_spelling_is_the_same_site(self):
        self.assertFinds(fixture("WriteACPI(0x9C40A4DC, 0x84, Data);"),
                         0x9C40A4DC, 0x84)

    def test_all_three_spellings_reach_the_same_single_site(self):
        # One site, not three: three would mean the const table and the literal
        # path disagree about what a call is, and the reachability table would
        # then be counting a spelling rather than a caller.
        for call in ("WriteACPI(2621482204u, 0x84, Data);",
                     "WriteACPI(IOCTL_GPD_ACPI_TMPWRITE1, 0x84, Data);",
                     "WriteACPI(0x9C40A4DC, 0x84, Data);"):
            with self.subTest(call=call):
                rows = [s for s in sites_of(fixture(call))
                        if s["ioctl"] == S.T1WR_IOCTL]
                self.assertEqual(len(rows), 1)

    def test_the_arg0_is_read_out_of_the_wrapper_buffer_not_the_code(self):
        # The code is argument 0 and the Arg0 is argument 1. A tool that read
        # the wrong one would report Arg0 == 0x9C40A4DC here.
        sites = [s for s in sites_of(fixture("WriteACPI(2621482204u, 0x84, Data);"))
                 if s["ioctl"] == S.T1WR_IOCTL]
        self.assertEqual(sites[0]["arg0"], 0x84)

    def test_each_of_T1WRs_own_arms_is_reachable_when_a_site_passes_it(self):
        # Every Arg0 the DSDT dispatches on, planted one at a time. This is the
        # claim the whole tool rests on, and it is checked against
        # `dsdt_ec_fields`'s own table rather than a list written here.
        #
        # `0x71` is checked against the arm that a caller can actually reach.
        # It appears twice in the table and the second is unreachable -- which
        # is the subject of `RedundantArmTests`, not of a blanket "every row is
        # reachable", so it is excluded here rather than special-cased by line.
        shadowed = D.T1WR_REDUNDANT[1]
        for arg0, line, _fields in D.T1WR_ARMS:
            if line == shadowed:
                continue
            with self.subTest(arg0=hex(arg0)):
                rows = S.reachability(
                    [{"arg0": arg0}],
                    arms=[(arg0, line, (("FIELD", "FIELD", "present-untested"),))],
                    redundant=D.T1WR_REDUNDANT)
                self.assertTrue(rows[0]["reachable"])

    def test_a_non_constant_code_lands_in_the_unresolved_bucket(self):
        # Never guessed at. A wrapper call whose code comes from somewhere this
        # pass does not follow carries **no code** -- it is not resolved against
        # whatever the other spelling would have given, and it is not guessed
        # from the wrapper's own body. The `Arg0` beside it still resolves,
        # because the literal `0x84` really is at the call site; a site is only
        # a caller of `T1WR` when *both* are known, and `reachability()` takes
        # the sites the census has already filtered on the code.
        source = fixture("WriteACPI(someCode, 0x84, Data);")
        rows = [s for s in sites_of(source) if s["via"]]
        self.assertTrue(rows, "the wrapper call was not recognised as a site")
        for row in rows:
            self.assertIsNone(row["ioctl"],
                              "a non-constant code was resolved to a value")
        self.assertEqual([r["arg0"] for r in rows], [0x84],
                         "the literal at the call site is still the Arg0")

    def test_a_site_with_no_code_reaches_no_arm(self):
        # The consequence of the above, and the thing a caller of the reachability
        # table actually depends on: an unresolved site contributes nothing.
        source = fixture("WriteACPI(someCode, 0x84, Data);")
        rows = S.reachability(
            [s for s in sites_of(source) if s["ioctl"] == S.T1WR_IOCTL],
            arms=D.T1WR_ARMS)
        self.assertFalse(any(r["reachable"] for r in rows))


class CollisionTests(unittest.TestCase):
    """The `0x84` that `t1wr_callers.py` could not use, used here.

    The by-value search rejected `0x81`-`0x85` because the same literal names a
    fan level elsewhere in the tree. These hold both halves of the difference:
    a `T1WR` call site reaches the arm, and a fan-level constant reaches
    nothing.
    """

    FAN_TABLE = """\tpublic const byte User_Fan_Level4 = 0x84;

\tpublic void SetFanLevel()
\t{
\t\tif (level == User_Fan_Level4)
\t\t{
\t\t\tWriteACPI(2621482124u, 0x0751, level);
\t\t}
\t}
"""

    def test_the_same_literal_reaches_the_arm_and_names_a_fan_level(self):
        source = fixture("WriteACPI(2621482204u, 0x84, Data);",
                         extra=self.FAN_TABLE)
        text = source
        # Both readings are present in one file, which is exactly the situation
        # that stopped the by-value search.
        self.assertIn("User_Fan_Level4 = 0x84", text)
        self.assertIn("WriteACPI(2621482204u, 0x84, Data);", text)
        rows = S.reachability(
            [{"arg0": 0x84}],
            arms=[(0x84, 50646, (("APL4", "APL4", "present-untested"),))],
            redundant=D.T1WR_REDUNDANT)
        self.assertTrue(rows[0]["reachable"],
                        "a T1WR call site passing 0x84 must reach APL4")

    def test_a_fan_level_write_reaches_no_T1WR_arm(self):
        # The mirror, and the one that stops the previous case being passed by a
        # tool that matches `0x84` anywhere in the tree. `0x0751` is the fan-mode
        # register and `0x9C40A48C` is ECRW; neither is a T1WR site.
        source = fixture("WriteACPI(2621482124u, 0x0751, 0x84);",
                         extra=self.FAN_TABLE)
        t1wr = [s for s in sites_of(source) if s["ioctl"] == S.T1WR_IOCTL]
        self.assertEqual(t1wr, [],
                         "an ECRW write is not a T1WR call site")
        rows = S.reachability(
            [s for s in sites_of(source)], arms=D.T1WR_ARMS)
        self.assertFalse(any(r["reachable"] for r in rows))

    def test_the_committed_tree_does_not_carry_the_collision(self):
        # The real tree, as it stands: `0x84` is a fan level there and nothing
        # sends T1WR, so nothing reaches APL4. If a future dump added a T1WR
        # site this goes red rather than the write-up quietly going stale.
        census = S.census(native=False)
        t1wr = [s for s in census["sites"] if s.get("ioctl") == S.T1WR_IOCTL]
        self.assertEqual(t1wr, [],
                         "a committed managed site now sends 0x9C40A4DC")


class LayoutTests(unittest.TestCase):
    """The reading key, re-derived from the committed decompile."""

    @classmethod
    def setUpClass(cls):
        with open(REPO / DRIVER_DECOMPILE, encoding="utf-8") as fh:
            cls.text = fh.read()

    def test_the_handler_is_the_one_the_dispatch_selects(self):
        self.assertEqual(S.dispatch_table(self.text).get(S.T1WR_IOCTL),
                         S.HANDLER_FUNC)

    def test_that_handler_evaluates_T1WR(self):
        self.assertEqual(S.handler_method(self.text, S.HANDLER_FUNC),
                         "T1WR")

    def test_the_buffer_slices_are_the_three_arguments(self):
        layout = S.parse_handler_layout(self.text)
        self.assertIsNotNone(layout, "the handler layout did not re-derive")
        self.assertEqual(layout["slices"], [(0, 3), (4, 7), (8, 11)])
        self.assertEqual(layout["argument_count"], 3)
        self.assertEqual(layout["buffer_length"], 0x28)
        self.assertEqual(layout["arg_length"], 0x40000)

    def test_the_slices_agree_with_what_the_tool_asserts(self):
        # Two answers to "which bytes is Arg0" is the failure this tool exists
        # to avoid, so the tool's own EXPECTED_LAYOUT is checked against the
        # decompile rather than trusted.
        self.assertEqual(S.parse_handler_layout(self.text)["slices"],
                         [tuple(s) for s in S.EXPECTED_LAYOUT["slices"]])

    def test_the_two_writable_TempWrite_handlers_lay_the_buffer_out_alike(self):
        # `T1WR`'s and `T2WR`'s handlers build the evaluation buffer the same
        # way, which is what makes one parse able to answer for both. Checked
        # per handler including the method name, because a parser that returned
        # the same three slices for *any* function body would pass the slice
        # comparison and mean nothing.
        for func, want in (("FUN_140002614", "T1WR"),
                           ("FUN_140002748", "T2WR")):
            with self.subTest(handler=func):
                layout = S.parse_handler_layout(self.text, func=func)
                self.assertIsNotNone(layout,
                                     f"{func}'s layout did not re-derive")
                self.assertEqual(layout["method"], want)
                self.assertEqual(layout["slices"],
                                 S.parse_handler_layout(self.text)["slices"])

    def test_the_T3WR_handler_is_not_the_same_shape(self):
        # `T3WR`'s handler is a different function and this holds that the
        # parser knows it. It `memcpy`s 0x80 bytes into the buffer and passes
        # `ArgumentCount = 1`, where the other two pass three arguments built
        # from `SystemBuffer` word by word -- which is consistent with the DSDT,
        # where `T3WR` writes one field (`\_SB.INOU.T3PC`) and `T1WR` dispatches
        # on three. The parser returns an empty slice list for it rather than
        # borrowing `T1WR`'s, and the empty list is the honest answer: there are
        # no `SystemBuffer[0..3]` argument slices to read.
        body = S._function_text(self.text, "FUN_14000287c")
        self.assertIn("memcpy_s", body)
        layout = S.parse_handler_layout(self.text, func="FUN_14000287c")
        self.assertIsNotNone(layout, "the T3WR handler should still parse")
        self.assertEqual(layout["method"], "T3WR")
        self.assertEqual(layout["slices"], [])


class RedundantArmTests(unittest.TestCase):
    """The two `0x71` arms, and which of them a caller can reach.

    `T1WR_ARMS` carries `0x71` twice and that is not a duplicate: the arm at
    `:50657` is matched by any caller passing `0x71` and leaves the chain, so a
    `T1WR(0x71)` caller reaches the first and **cannot** reach the second. A
    reachability table that reported both as reachable would be wrong in the
    direction that looks like a positive.
    """

    ARMS = [(0x71, 50657, ()),
            (0x1171, 50658, (("CTWA", "CTWA", "present-untested"),)),
            (0x71, 50667, (("CTWA", "CTWA", "present-untested"),))]

    def test_a_0x71_caller_reaches_the_first_arm_and_not_the_second(self):
        rows = S.reachability([{"arg0": 0x71}], arms=self.ARMS,
                              redundant=D.T1WR_REDUNDANT)
        by_line = {r["line"]: r for r in rows}
        self.assertTrue(by_line[50657]["reachable"])
        self.assertFalse(by_line[50667]["reachable"])

    def test_the_shadowed_arm_says_why(self):
        rows = S.reachability([{"arg0": 0x71}], arms=self.ARMS,
                              redundant=D.T1WR_REDUNDANT)
        note = {r["line"]: r["note"] for r in rows}[50667]
        self.assertIn("50657", note)
        self.assertIn("unreachable", note)

    def test_the_real_table_has_the_pair_the_check_assumes(self):
        # `dsdt_ec_fields` owns the table; this holds that the two halves the
        # redundancy claim rests on are the ones it actually holds, so a .dsl
        # change cannot leave this suite checking a pair that moved.
        self.assertEqual(D.T1WR_REDUNDANT, (50657, 50667))
        lines = [line for arg0, line, _f in D.T1WR_ARMS if arg0 == 0x71]
        self.assertEqual(lines, list(D.T1WR_REDUNDANT))


class CommittedTreeTests(unittest.TestCase):
    """The claims the write-up makes about the tree as it is."""

    @classmethod
    def setUpClass(cls):
        cls.census = S.census(native=False)

    def test_the_self_check_passes(self):
        self.assertEqual(S.self_check(self.census), 0)

    def test_the_readability_probes_came_back_non_zero(self):
        # A probe at zero means this run read nothing, and every negative below
        # would be a statement about a tree that was never opened.
        for term, why, hits in self.census["probes"]:
            with self.subTest(term=term):
                self.assertTrue(hits, f"probe {term!r} is zero: {why}")

    def test_the_service_sends_the_named_codes_and_none_of_the_Temp_ones(self):
        implemented = set(self.census["dispatch"])
        sent = {s["ioctl"] for s in self.census["sites"] if s.get("ioctl")}
        acpi = {code for code in sent if code in implemented}
        self.assertEqual(acpi, set(S.EXPECTED_SERVICE_IOCTLS))
        self.assertFalse({code for code in acpi if code in S.ACPI_TMP_IOCTLS},
                         "the service sends a Temp* code, which is the drift "
                         "t1wr_callers.py also asserts against")

    def test_the_T1WR_code_is_declared_but_never_passed(self):
        # The by-value reading of the same fact, re-derived: the constant is in
        # the committed service and no site carries it.
        with open(REPO / SERVICE, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("IOCTL_GPD_ACPI_TMPWRITE1", text)
        carriers = [s for s in self.census["sites"]
                    if s["ioctl"] == S.T1WR_IOCTL]
        self.assertEqual(carriers, [])

    def test_a_reported_line_is_the_line_the_call_is_on(self):
        # The write-up quotes `file:line` for each site, so a line number that
        # is one out is a citation a reviewer cannot check. Held by opening the
        # file and reading the line back -- which is exactly what a reviewer
        # does -- rather than by comparing against a constant here, which would
        # only prove the tool agrees with itself.
        for site in self.census["sites"]:
            if not site.get("ioctl") or ":GCUService" not in site["input"]:
                continue
            rel, _, line = site["file_line"].rpartition(":")
            path = REPO / ("windows/decompiled/v3.1.39.0/GCUService/"
                           + rel.rsplit("/", 1)[-1])
            if not path.exists():
                continue
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
            with self.subTest(site=site["file_line"]):
                self.assertTrue(
                    any(call in lines[int(line) - 1]
                        for call in ("ReadACPI(", "WriteACPI(",
                                     "DeviceIoControl(", "Win32.")),
                    f"{site['file_line']} does not name a call line: "
                    f"{lines[int(line) - 1]!r}")

    def test_no_arm_of_T1WR_is_reachable(self):
        rows = S.reachability(
            [s for s in self.census["sites"] if s.get("ioctl") == S.T1WR_IOCTL])
        reachable = [r for r in rows if r["reachable"]]
        self.assertEqual(reachable, [], "a committed site now reaches a T1WR arm")

    def test_every_arm_is_accounted_for_against_the_dsdt(self):
        # The table is `dsdt_ec_fields`' own, so a dropped arm shows up here as
        # a row that is not in it rather than as a silently shorter table.
        self.assertEqual(len(self.census["rows"]), len(D.T1WR_ARMS))
        self.assertEqual([r["arg0"] for r in self.census["rows"]],
                         [a[0] for a in D.T1WR_ARMS])

    def test_the_power_limit_writes_route_through_ECRW_not_T1WR(self):
        # The question the issue asks about APL1/APL2/APL4 and APTC/APTN. Every
        # one of those addresses has a committed writer, and every one of those
        # writers resolves to the same IOCTL -- ECRW, a plain byte write.
        power = self.census["power"]
        self.assertEqual(set(power), set(S.POWER_LIMIT_ADDRS))
        for addr, info in sorted(power.items()):
            with self.subTest(addr=hex(addr)):
                self.assertTrue(info["writers"],
                                f"0x{addr:04X} has no committed writer")
                self.assertTrue(info["resolved"],
                                f"0x{addr:04X}'s route did not resolve")
                self.assertEqual(info["ioctl"], S.EXPECTED_POWER_IOCTL)
        self.assertNotEqual(S.EXPECTED_POWER_IOCTL, S.T1WR_IOCTL)


class NativeLayerTests(unittest.TestCase):
    """The disassembly layer, over a listing this suite writes itself.

    Driven from a fixture listing rather than from objdump, so the parse and
    the site logic are tested without a disassembler and without a 4 MB binary
    in the suite's runtime. `CommittedNativeTests` then runs the real thing.
    """

    # A `TempWrite1`-shaped body: the argument stores into a scratch buffer, a
    # `lea` naming it as `lpInBuffer` (r8), the IOCTL into edx, and the import
    # thunk call. The `int3` run in front is MSVC's inter-function padding and
    # is what bounds the backward scan for the buffer setup -- without it the
    # tool correctly reports "no setup found" rather than reaching into the
    # previous function, and this fixture would be measuring the fallback.
    LISTING = """\
   180003f70:\tcc                    \tint3
   180003f71:\tcc                    \tint3
   180003f72:\tcc                    \tint3
   180003f73:\tcc                    \tint3
   180003f80:\t40 53                \trex push %rbx
   180003f95:\t45 33 c9             \txor    %r9d,%r9d
   180003f98:\t89 0d 02 8d 27 00    \tmov    %ecx,0x278d02(%rip)        # 0x18027cca0
   180003fa4:\t48 8d 0d 15 ea 22 00 \tlea    0x22ea15(%rip),%rcx        # 0x1802329c0
   18000401d:\t4c 8d 05 7c 8c 27 00 \tlea    0x278c7c(%rip),%r8         # 0x18027cca0
   18000402c:\tba dc a4 40 9c       \tmov    $0x9c40a4dc,%edx
   180004037:\t4c 89 44 24 20       \tmov    %r8,0x20(%rsp)
   18000403f:\tff 15 f3 77 1c 00    \tcall   *0x1c77f3(%rip)        # 0x1801cb838
   180004048:\tff 15 e2 77 1c 00    \tcall   *0x1c77e2(%rip)        # 0x1801cb830
"""

    # The same body with the word-0 store carrying a literal instead of `%ecx`,
    # which is the shape a site with a *known* Arg0 has.
    IMMEDIATE = LISTING.replace(
        "mov    %ecx,0x278d02(%rip)        # 0x18027cca0",
        "movl   $0x84,0x278d02(%rip)       # 0x18027cca0")

    def test_the_listing_parses_to_instructions(self):
        instructions = S.parse_listing(self.LISTING)
        self.assertTrue(instructions)
        # The listing opens on `int3` padding and the function body follows it.
        # That padding is what the backward scan stops at, so a parser that
        # dropped it would leave the scan with no boundary to stop at.
        self.assertEqual([m for _v, m, _o in instructions[:4]],
                         ["int3"] * 4)
        self.assertEqual(instructions[4][0], 0x180003F80)

    def test_the_resolved_target_comment_survives_the_parse(self):
        # objdump's `# 0x18027cca0` is the only place the store's destination
        # address appears; a parse that stripped it would leave every `Arg0`
        # unresolved.
        by_va = {va: (m, o) for va, m, o in S.parse_listing(self.LISTING)}
        self.assertEqual(S._comment_target(by_va[0x180003F98][1]),
                         0x18027CCA0)

    def test_the_ioctl_site_is_found(self):
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(self.LISTING), 0x180000000,
                               {"TempWrite1": 0x3F80})
        issuing = [s for s in sites if s[2] == S.T1WR_IOCTL]
        self.assertEqual(len(issuing), 1)
        self.assertEqual(issuing[0][0], 0x18000402C)

    def test_a_register_store_into_the_buffer_is_not_an_arg0(self):
        # `mov %ecx, …` puts whatever the caller passed in `ecx` there. Naming
        # that a constant would be the tool inventing an answer.
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(self.LISTING), 0x180000000,
                               {"TempWrite1": 0x3F80})
        self.assertIsNone([s for s in sites if s[2] == S.T1WR_IOCTL][0][3])

    def test_an_immediate_store_into_the_buffer_is_the_arg0(self):
        # Same shape, but the site puts a literal in the buffer. That is the
        # case the managed layer reads, and the native layer has to read it too
        # or a native-only caller would be invisible.
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(self.IMMEDIATE), 0x180000000,
                               {"TempWrite1": 0x3F80})
        found = [s for s in sites if s[2] == S.T1WR_IOCTL][0]
        self.assertEqual(found[3], 0x84)

    def test_that_native_arg0_reaches_the_arm(self):
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(self.IMMEDIATE), 0x180000000,
                               {"TempWrite1": 0x3F80})
        rows = S.reachability(
            [{"arg0": sites[0][3]}],
            arms=[(0x84, 50646, (("APL4", "APL4", "present-untested"),))],
            redundant=D.T1WR_REDUNDANT)
        self.assertTrue(rows[0]["reachable"])

    def test_a_buffer_filled_before_any_padding_is_not_read_across_functions(self):
        # The fallback, and the reason the scan is bounded: with no `int3` run
        # in front, the tool stops at its window and reports no `Arg0` rather
        # than reaching back into the previous function for a store that has
        # nothing to do with this site.
        listing = "\n".join(line for line in self.IMMEDIATE.splitlines()
                            if "int3" not in line)
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(listing), 0x180000000,
                               {"TempWrite1": 0x3F80},)
        found = [s for s in sites if s[2] == S.T1WR_IOCTL]
        self.assertEqual([s[3] for s in found], [0x84],
                         "the window fallback still covers a short function")

    def test_a_call_to_a_TempWrite_export_is_a_different_claim(self):
        # Something calling the wrapper is not something issuing the IOCTL, and
        # the tool says which it found rather than counting both as one.
        listing = self.LISTING + (
            "   180005000:\t48 8b cb             \tmov    %rbx,%rcx\n"
            "   180005003:\te8 78 ef ff ff       \tcall   0x180003f80\n")
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(listing), 0x180000000,
                               {"TempWrite1": 0x3F80})
        self.assertTrue(any(s[1].startswith("calls TempWrite1") for s in sites))

    def test_an_unrelated_code_is_not_a_T1WR_site(self):
        listing = self.LISTING.replace("0x9c40a4dc", "0x9c40a48c")
        sites = S.native_sites("fixture", "fixture.dll",
                               S.parse_listing(listing), 0x180000000,
                               {"TempWrite1": 0x3F80})
        self.assertEqual([s for s in sites if s[2] == S.T1WR_IOCTL], [])


class CommittedNativeTests(unittest.TestCase):
    """The native layer against the committed PEs, when a disassembler exists.

    Skipped rather than failed when there is no binutils and no radare2: the
    suite's job is to check the committed tree, and a machine with no
    disassembler has not falsified anything. The tool itself reports an
    unreadable native layer rather than a clean one, which is what
    distinguishes this skip from a pass that found nothing.
    """

    @classmethod
    def setUpClass(cls):
        probe = subprocess.run(
            ["bash", "-c", "command -v objdump || command -v r2 || true"],
            capture_output=True, text=True)
        if not probe.stdout.strip():
            raise unittest.SkipTest("no objdump and no r2 on this machine")
        cls.census = S.census(native=True)

    def test_every_native_input_was_actually_read(self):
        # The inverse of the probe: an input reported unreadable makes its zero
        # meaningless, so the state is asserted rather than assumed.
        for label, _rel, _sites, state in self.census["native"]:
            with self.subTest(label=label):
                self.assertEqual(state, "read")

    def test_the_dll_that_defines_TempWrite1_is_the_one_that_issues_the_code(self):
        # `ACPIDriverDll.dll`'s `TempWrite1` is the wrapper: it stores its three
        # arguments and calls `DeviceIoControl` with 0x9C40A4DC. Finding it here
        # is the positive control for the whole native layer -- a scan that found
        # nothing anywhere would look exactly like a clean tree.
        found = {label: sites for label, _rel, sites, _s
                 in self.census["native"]}
        dll = [label for label in found if "ACPIDriverDll" in label][0]
        self.assertTrue([s for s in found[dll] if s[2] == S.T1WR_IOCTL],
                        "TempWrite1's own IOCTL setup was not found in the DLL")

    def test_no_native_program_calls_a_TempWrite_export(self):
        callers = [(label, s) for label, _rel, sites, _state
                   in self.census["native"] for s in sites
                   if s[1].startswith("calls ")]
        self.assertEqual(callers, [],
                         "a committed PE calls a TempWrite* export")

    def test_the_sys_dispatch_comparison_is_not_a_caller(self):
        # `ACPIDriver.sys` compares against 0x9C40A4DC in its dispatch. That is
        # the kernel side comparing a code it received, which is not a site
        # issuing it, and the `mov $…, %edx` rule is what keeps them apart.
        sys_input = [sites for label, _rel, sites, _state
                     in self.census["native"] if "ACPIDriver.sys" in label][0]
        self.assertEqual([s for s in sys_input if s[2] == S.T1WR_IOCTL], [])


class TempWriteOnlyTests(unittest.TestCase):
    r"""`T2WR`/`T3WR` are out of scope, measured rather than assumed.

    `T2WR` has an empty body and `T3WR` writes only `\_SB.INOU.T3PC`, so `T1WR`
    is the only one of the three that reaches an EC field. Held here so the
    scoping statement in the write-up is a check rather than a claim.
    """

    @classmethod
    def setUpClass(cls):
        with open(REPO / "evidence/acpi/dsdt.dsl", encoding="utf-8") as fh:
            cls.lines = fh.read().splitlines()

    def body(self, name, start):
        """The ASL body of a `Method (NAME, …)`, by brace count."""
        depth, out = 0, []
        for line in self.lines[start - 1:]:
            depth += line.count("{") - line.count("}")
            out.append(line)
            if depth == 0 and len(out) > 1:
                break
        return "\n".join(out)

    def test_T2WR_is_empty(self):
        text = self.body("T2WR", 50748)
        self.assertIn("Method (T2WR", text)
        self.assertEqual(text.count("{"), text.count("}"))
        self.assertNotIn("EC0", text, "T2WR writes no EC field")

    def test_T3WR_writes_only_T3PC(self):
        text = self.body("T3WR", 50752)
        self.assertIn("Method (T3WR", text)
        self.assertNotIn("EC0", text, "T3WR writes no EC field")
        self.assertIn("T3PC", text)


class TempDirectoryTests(unittest.TestCase):
    """The tool reads committed inputs; this holds that it writes none.

    `vendor/` is committed input and never build output, and the archive-heavy
    inputs are the reason a naive implementation would want a scratch
    directory under the tree.
    """

    def test_the_run_leaves_the_tree_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = sorted(os.listdir(REPO / "vendor"))
            env = dict(os.environ)
            env["TMPDIR"] = tmp
            subprocess.run([sys.executable, str(HERE / "t1wr_sites.py"),
                            "--self-check", "--no-native"],
                           capture_output=True, text=True, cwd=str(tmp),
                           env=env, timeout=600)
            self.assertEqual(sorted(os.listdir(REPO / "vendor")), before)
            self.assertEqual(os.listdir(tmp), [],
                             "the tool wrote into the directory it was given")


if __name__ == "__main__":
    unittest.main()
