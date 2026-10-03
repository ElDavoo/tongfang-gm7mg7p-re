#!/usr/bin/env python3
r"""The refusals of `tools/check_uniwill_writers.py`, not its happy path.

A rule that cannot fail is the failure mode worth a suite, and this checker's
whole job is refusing. Each case below mutates one committed input, runs
`--check` **as a subprocess** -- for a checker the exit code is the product, and
only a process shows what a consumer sees -- and asserts it goes red *and names
the problem*.

**The negative controls are what make the greens mean anything.** A rule that
fires on everything passes every positive in this file. Each absence rule
therefore carries a companion that must stay green: the committed inputs
themselves, a before/after pair that differs at one byte at an offset the
finding is not about, and a struct whose attributes are untouched. The
sweeps that matter most here are the ones a reader would be tempted to
"simplify" -- the struct layout, and the create path's frame arithmetic --
because both have a failure mode where the tool finds nothing and reports a
clean run, and only a fixture that removes the thing being looked for catches
it.

Every mutation is a `tempfile` copy, so nothing here writes a file the checker
reads from the repository. **Not in any gate:** `run-tests.sh` finds the suite by
itself, and the checker is deliberately not wired into `agent-gates.sh`, which
is copied from `agent-pipeline` and so is upstream's to change.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

import check_uniwill_writers as c  # noqa: E402

# The fixture inputs, named so the copies are readable in a failure message.
NAMES = {"struct": "NVRAM_STRUCT.cs", "nvram": "NvramVariable.cs",
         "asm": "OemUniWillVariableDxe.asm", "cs": "OemUniWillVariableDxe.c"}


def read(path):
    with open(path) as f:
        return f.read()


class CheckUniwillWriters(unittest.TestCase):
    """Every case runs the real checker over copies of the committed inputs."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="check-uniwill-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.ev = os.path.join(self.tmp, "uefi")
        os.makedirs(self.ev)
        shutil.copy(c.DEFAULT_STRUCT, self._p("struct"))
        shutil.copy(c.DEFAULT_NVRAM, self._p("nvram"))
        shutil.copy(c.DEFAULT_BIOS_ASM, self._p("asm"))
        shutil.copy(c.DEFAULT_BIOS_C, self._p("cs"))
        for name, blob in c.dumps():
            shutil.copy(os.path.join(c.DEFAULT_EVIDENCE, name),
                        os.path.join(self.ev, name))

    def _p(self, key):
        return os.path.join(self.tmp, NAMES[key])

    def run_check(self, *extra):
        """`--check` over the copies, as a subprocess. Returns (rc, out, err)."""
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "tools", "check_uniwill_writers.py"),
             "--check", "--struct", self._p("struct"), "--nvram", self._p("nvram"),
             "--asm", self._p("asm"), "--bios-c", self._p("cs"),
             "--evidence", self.ev, *extra],
            capture_output=True, text=True, cwd=self.tmp)
        return proc.returncode, proc.stdout, proc.stderr

    def assertRed(self, needle, *extra):
        rc, _out, err = self.run_check(*extra)
        self.assertEqual(rc, 1, f"expected a refusal, got a clean run:\n{err}")
        self.assertIn(needle, err,
                      f"the run went red but never named {needle!r}:\n{err}")

    def assertGreen(self, *extra):
        rc, _out, err = self.run_check(*extra)
        self.assertEqual(rc, 0, f"expected a clean run, got:\n{err}")

    def edit(self, key, pattern, replacement, count=1):
        """Mutate one committed input in place, as a fixture rather than a test."""
        path = self._p(key)
        text = read(path)
        new, n = re.subn(pattern, replacement, text, count=count, flags=re.M)
        if count:
            self.assertEqual(n, count,
                             f"the fixture pattern {pattern!r} matched {n} "
                             f"time(s) in {NAMES[key]}, not {count}; this case "
                             f"is not testing what it says it is")
        else:
            self.assertGreater(n, 0,
                               f"the fixture pattern {pattern!r} matched "
                               f"nothing in {NAMES[key]}; this case is not "
                               f"testing what it says it is")
        with open(path, "w") as f:
            f.write(new)

    # --- the committed inputs, which is the point of running this ---------

    def test_committed_inputs_are_clean(self):
        self.assertGreen()

    def test_self_test_passes(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, "tools", "check_uniwill_writers.py"),
             "--self-test"],
            capture_output=True, text=True, cwd=self.tmp)
        self.assertEqual(proc.returncode, 0,
                         f"--self-test refused:\n{proc.stdout}{proc.stderr}")

    def test_a_check_that_locates_nothing_is_not_a_clean_run(self):
        """A checker handed a tree it cannot read must fail, not pass quietly.

        The vacuous-check defect at the level of the exit code: a run that read
        no struct has checked nothing, and reporting that as green is how a gate
        stops gating. The refusal has to name the file as well, so this also
        holds the message and not only the exit code -- a bare traceback says
        nothing about which of the eight rules went unrun.
        """
        absent = os.path.join(self.tmp, "absent.cs")
        self.assertRed("absent.cs is not there", "--struct", absent)

    def test_no_evidence_is_not_a_clean_run(self):
        shutil.rmtree(self.ev)
        os.makedirs(self.ev)
        self.assertRed("no *.bin dump")

    # --- rule 1: the layout is derived, so it has to be re-derivable -------

    def test_a_struct_carrying_a_layout_attribute_is_refused(self):
        # On the type, where C# wants it, so the fixture is a thing the vendor
        # could plausibly have shipped rather than a marker this check hunts for.
        self.edit("struct", r"public struct NVRAM_STRUCT",
                  r"[System.Runtime.InteropServices.StructLayout("
                  r"System.Runtime.InteropServices.LayoutKind.Sequential, Pack = 1)]"
                  r"\npublic struct NVRAM_STRUCT")
        self.assertRed("carries a `Pack` attribute")

    def test_a_struct_that_no_longer_declares_the_field_is_refused(self):
        """What keeps rule 8 from being an absence about nothing.

        Rule 8 says the service has no `case` for the field. If the field were
        renamed out of the struct the absence would still hold, rule 8 would go
        on passing, and it would be saying that a service does not assign a
        field the struct no longer has.
        """
        self.edit("struct", r"public byte %s;" % c.MEMORY_OC,
                  "public byte RENAMED;")
        self.assertRed(f"declares no {c.MEMORY_OC} field")

    def test_a_struct_whose_reserved_array_overruns_is_refused(self):
        self.edit("struct", r"public byte\[\] %s;" % c.RESERVED,
                  r"public byte[] Reserved;\n\tpublic byte Extra;")
        self.assertRed("does not reach the end")

    def test_the_layout_the_committed_struct_derives_is_the_one_cited(self):
        """The write-up's offsets, recomputed rather than trusted."""
        _problems, layout = c.layout_problems(self._p("struct"))
        self.assertEqual(layout["size"], 180)
        self.assertEqual(layout["packed_size"], 178)
        self.assertEqual(layout["offsets"][c.MEMORY_OC], 0x60)
        self.assertEqual(layout["offsets"][c.RESERVED], 0x68)
        self.assertEqual(layout["reserved_end"], 0xB4)

    # --- rule 2: the zeroed baseline, which is the finding's control ------

    def test_an_all_zero_dump_is_refused_as_the_zeroed_baseline(self):
        """The case the finding turns on, not one that supports it.

        A dump with `OemBoardSsid` at zero is exactly what a `GetFwVars()`
        returning `default(NVRAM_STRUCT)` followed by a whole-struct write
        would leave. The committed dumps are not that, and this is what holds
        them apart.
        """
        with open(os.path.join(self.ev, "2026-09-25-UniWillVariable.bin"), "wb") as f:
            f.write(bytes(180))
        self.assertRed("no longer excludes the writer")

    # --- rule 3: one byte across one deliberate change -------------------

    def _rename_pair(self):
        """The committed pair, under names this run's rule recognises."""
        for old, new in (("2026-09-23-UniWillVariable-before-memoc.bin",
                          "2026-09-23-x-before.bin"),
                         ("2026-09-23-UniWillVariable-after-memoc.bin",
                          "2026-09-23-x-after.bin")):
            shutil.copy(os.path.join(c.DEFAULT_EVIDENCE, old),
                        os.path.join(self.ev, new))

    def test_a_pair_differing_at_two_bytes_is_refused_and_names_them(self):
        self._rename_pair()
        path = os.path.join(self.ev, "2026-09-23-x-after.bin")
        blob = bytearray(read_bytes(path))
        blob[0x33] ^= 0xFF
        blob[0x2F] ^= 0x01
        with open(path, "wb") as f:
            f.write(bytes(blob))
        self.assertRed("differ at 2 byte(s)")

    def test_a_pair_differing_at_one_byte_elsewhere_is_not_refused(self):
        """The negative control for the case above.

        The committed pair differs at `MemoryOverClockSwitch` and that is a
        clean run; a rule scoped to that offset rather than to any single
        changed byte would be a rule that had to be weakened to pass.
        """
        self._rename_pair()
        self.assertGreen()

    def test_no_before_after_pair_at_all_is_refused(self):
        for name in os.listdir(self.ev):
            os.remove(os.path.join(self.ev, name))
        shutil.copy(os.path.join(c.DEFAULT_EVIDENCE, "2026-09-19-UniWillVariable.bin"),
                    os.path.join(self.ev, "2026-09-19-UniWillVariable.bin"))
        self.assertRed("no before/after pair")

    # --- rule 4: the state under test -------------------------------------

    def test_a_dump_with_the_field_non_zero_is_refused(self):
        self._bump("2026-09-19-UniWillVariable.bin", 0x60, 1)
        self.assertRed("ends the run")

    def test_a_dump_with_a_non_zero_reserved_byte_is_refused(self):
        self._bump("2026-09-19-UniWillVariable.bin", 0x68, 0xFF)
        self.assertRed("reading all zero")

    def test_a_dump_of_the_wrong_length_is_refused(self):
        with open(os.path.join(self.ev, "2026-09-25-UniWillVariable.bin"), "wb") as f:
            f.write(bytes(178))
        self.assertRed("the derived struct is 180")

    def _bump(self, name, offset, value):
        path = os.path.join(self.ev, name)
        blob = bytearray(read_bytes(path))
        blob[offset] = value
        with open(path, "wb") as f:
            f.write(bytes(blob))

    # --- rules 5, 6, 7: the create path ----------------------------------

    def test_a_create_path_that_is_not_behind_the_guard_is_refused(self):
        info = c.create_path(self._p("asm"))
        self.edit("asm", r"jns +0x%08x\b" % info["guard"][1],
                  "jns      0x%08x" % (info["guard"][1] - 0x200))
        self.assertRed("is not conditional")

    def test_a_c_without_the_guard_the_write_up_cites_is_refused(self):
        self.edit("cs", r"if \(lVar1 < 0\)", "if (lVar1 > 0)")
        self.assertRed("no longer carries the `if (lVar1 < 0)` guard")

    def test_a_create_path_that_never_assigns_the_field_is_refused(self):
        """Rule 6's negative control, and the case that keeps it honest.

        Moving the store off offset 0x60 is what the listing would look like if
        a different field were initialised here. Without it the rule cannot tell
        "it assigns 1 to 0x60" from "it assigns nothing to 0x60", because both
        are a run that finds a store.
        """
        info = c.create_path(self._p("asm"))
        # `writes_to` reports the struct offset; the listing carries the frame
        # displacement, so the fixture needs the store's own displacement back.
        addr, off, _val, _w = c.writes_to(info["stores"], info["data_base"], 0x60)[0]
        disp = off + info["data_base"]
        self.edit("asm", r"^(%08X [^\[]*\[RBP )[+-] %s\], 0xff01$"
                  % (addr, re.escape(c._hex(disp))),
                  r"\g<1>+ %s], 0xff01" % c._hex(disp + 1))
        self.assertRed("no store in the create path reaches")

    def test_a_create_path_that_assigns_something_else_is_refused(self):
        self.edit("asm", r"(\[RBP [^\]]+\]), 0xff01", r"\1, 0xff00")
        self.assertRed("not 1")

    def test_a_fill_aligned_to_reserved_is_refused(self):
        """The claim rule 7 exists to hold, with the alignment it denies.

        Aligning the fill to `Reserved` is what "0xFF in the 76 reserved bytes"
        would look like in the listing. It is one byte of displacement away from
        what the listing actually says, and nothing else in the file would show
        the difference.
        """
        info = c.create_path(self._p("asm"))
        dest_at, disp = info["fill"][1], info["fill"][2]
        self.edit("asm", r"^(%08X [^\[]*\[RBP )[+-] %s\]" % (dest_at, re.escape(c._hex(disp))),
                  r"\g<1>+ %s]" % c._hex(disp + 1))
        self.assertRed("which is exactly Reserved")

    def test_the_committed_create_path_resolves_to_the_cited_offsets(self):
        """Rule 6's positive, recomputed from the listing rather than trusted."""
        info = c.create_path(self._p("asm"))
        self.assertEqual(info["data_base"], -0x79)
        self.assertGreater(info["guard"][1], info["set_var"])
        addr, off, val, width = c.writes_to(info["stores"], info["data_base"], 0x60)[0]
        self.assertEqual(off, 0x60)
        self.assertEqual((val >> (8 * (0x60 - off))) & 0xFF, 1)
        self.assertEqual(width, 2)
        _call, _dest_at, disp, count = info["fill"]
        self.assertEqual((disp - info["data_base"],
                          disp - info["data_base"] + count - 1), (0x67, 0xB2))

    # --- rule 8: the service never assigns the field ---------------------

    def test_a_service_that_assigns_the_field_is_refused(self):
        self.edit("nvram", r'case "PowerMode":',
                  'case "%s":\n\t\t\t_fwvars.%s = value;\n\t\t\tbreak;\n'
                  '\t\tcase "PowerMode":' % (c.MEMORY_OC, c.MEMORY_OC))
        self.assertRed("now assigns the field")

    def test_a_service_that_stops_writing_the_whole_struct_is_refused(self):
        """Count 0 rather than one: the expression appears more than once, and
        only the occurrence inside the writing routine is the claim."""
        self.edit("nvram", r"Marshal\.SizeOf\(typeof\(NVRAM_STRUCT\)\)",
                  "array.Length", count=0)
        self.assertRed("no longer marshals")

    def test_the_committed_service_has_no_case_for_the_field(self):
        cases, whole = c.service_switches(self._p("nvram"))
        self.assertNotIn(c.MEMORY_OC, cases)
        self.assertTrue(whole)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


if __name__ == "__main__":
    unittest.main()