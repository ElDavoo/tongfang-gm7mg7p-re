#!/usr/bin/env python3
"""Offline checks; no efivarfs, no UEFI variable, no machine is touched.

Hardware is not mocked, because there is nothing to mock. The tool's only I/O
is a filesystem path, so the suite stands a `tempfile.TemporaryDirectory()` in
for `/sys/firmware/efi/efivars` and the tool's real read/write/glob code runs
against it. That is why this suite can say something about the refusals and the
readback rather than only about the decoder.

**What a green run here is not.** It is not evidence that the efivarfs route
works. Nothing in this file has touched `/sys/firmware/efi/efivars`, no UEFI
variable has been written, and `docs/findings.md` §8's "that route has not been
exercised" is still true. The suite holds the tool's logic, its framing and its
refusals; the write on a real machine is
`docs/hardware-tests/uniwill-var-memoc-efivarfs.md`, which has not been run.

The load-bearing cases are in three groups:

- **The committed evidence.** The three 180-byte dumps in `evidence/uefi/` are
  the exact input the tool operates on, so decoding them is the decoder's real
  job done on real input, and applying the tool's own field-set to the
  before-dump reproducing the after-dump byte for byte reproduces the operator's
  2026-09-23 Windows transformation from committed inputs. It also pins that
  the tool touches exactly one byte.
- **The field table, pinned to its source.** `nvram_layout.NVRAM_FIELDS` is a
  copy of a table that exists in two other places, and a copy with nothing
  holding it in place is a copy that drifts. All three are compared against the
  decompiled `NVRAM_STRUCT.cs` field for field, in declaration order, width and
  array size. This is what makes the duplication safe rather than free-floating
  -- and it is a stronger guarantee than a shared import would be, because it is
  enforced on every run rather than trusted once.
- **The refusals.** Each asserts nothing was written. A safety argument that is
  only prose is one refactor away from being wrong, and this is the half that
  says the tool cannot truncate a 180-byte struct to 179.
- **The open mode of the immutable-flag ioctls.** An efivarfs entry is immutable
  on arrival, and the kernel refuses a write-intent open on a file that is, so
  the function that clears the flag must not ask for write access to the very
  file it is clearing it from. `ImmutableEntryModel` supplies that refusal --
  a model of the kernel rule, not the rule, since setting the flag for real
  needs `CAP_LINUX_IMMUTABLE` that CI does not have -- and two cases hold the
  mode and the resulting write down. This group is here because a suite can be
  green over a write path that cannot open its target: `FakeEfivarfs` replaces
  `set_immutable` wholesale, so the ordering cases prove the sequence and none
  of them prove the open.
"""
import ast
import builtins
import errno
import fcntl
import importlib.util
import io
import os
import re
import struct
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
EVIDENCE = REPO / "evidence" / "uefi"
BEFORE = EVIDENCE / "2026-09-23-UniWillVariable-before-memoc.bin"
AFTER = EVIDENCE / "2026-09-23-UniWillVariable-after-memoc.bin"
DUMP = EVIDENCE / "2026-09-19-UniWillVariable.bin"
# The decompiled struct the field table is a transcription of.
NVRAM_STRUCT_CS = (REPO / "windows" / "decompiled" / "v3.1.39.0" / "GCUService"
                   / "MyControlCenter" / "NVRAM_STRUCT.cs")
UEFI_VAR_PY = REPO / "windows" / "tools" / "uefi_var.py"

# NV|BS|RT, what `evidence/uefi/2026-09-19-UniWillVariable.txt` records for the
# live variable. Any write here must carry it through unchanged.
LIVE_ATTRS = 0x7


def _load(name, path):
    """Import a module from a path; the tool's filename is not a module name."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _open_that_fails_on(target):
    """An `open` that refuses to open `target` for writing, and works otherwise.

    Bound onto the tool module for one test so a write that reaches the efivarfs
    entry fails the way a real I/O error would, rather than succeeding against
    a tmpfs that has no opinions. Scoped to one path deliberately: the tool also
    writes the backup file, and a blanket failure would stop the run before it
    ever reached the entry, leaving the case green for the wrong reason.
    """
    real_open = open

    def patched(path, mode="r", *args, **kwargs):
        if str(path) == str(target) and ("w" in mode or "a" in mode
                                         or "+" in mode):
            raise OSError(f"simulated write failure on {target}")
        return real_open(path, mode, *args, **kwargs)

    return patched


layout = _load("nvram_layout", HERE / "nvram_layout.py")
tool = _load("uniwill_var", HERE / "uniwill-var.py")


class FakeEfivarfs:
    """A directory standing in for `/sys/firmware/efi/efivars`.

    Not a mock of the kernel: the tool's own `find_entry`/`read_entry`/
    `write_entry` run against real files, which is what lets the refusal cases
    assert what a refusal left behind. What this has to supply is the one thing
    a tmpfs cannot -- the immutable flag. `set_immutable` is replaced by a
    recorder for the life of the context, so the suite can assert the flag was
    taken off before the write and put back after, including when the write
    raises. The real ioctl on a tmpfs file fails with ENOTTY; that is a
    property of tmpfs, not of the tool, so the recorder stands in for a kernel
    that accepts it. What is asserted is the order and the count of the calls,
    never the flag on disk.
    """

    def __init__(self, root, body, attrs=LIVE_ATTRS, name=None):
        self.root = Path(root) / "efivars"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / (name or layout.guid_dent_name())
        self.attrs = attrs
        self.body = bytes(body)
        self.flag_calls = []
        self.put(self.body, attrs)

    def put(self, body, attrs):
        """Replace the entry's bytes directly, without going through the tool."""
        self.path.write_bytes(struct.pack("<I", attrs) + bytes(body))

    def __enter__(self):
        self._real_set_immutable = tool.set_immutable
        tool.set_immutable = self._record_flags
        return self

    def __exit__(self, *_exc):
        tool.set_immutable = self._real_set_immutable
        return False

    def _record_flags(self, path, immutable):
        self.flag_calls.append(bool(immutable))
        return True

    def run(self, *argv):
        """Call the tool's main, capturing its output; SystemExit is the caller's."""
        out = io.StringIO()
        with redirect_stdout(out):
            code = tool.main(["--var", str(self.root), *argv])
        return code, out.getvalue()

    def read(self):
        return tool.read_entry(self.path)

    def backup_path(self, name="backup.bin"):
        return self.root / name


class ImmutableEntryModel:
    """A file that refuses a write-intent open while its flag is set.

    **A model of the kernel rule, not the rule itself.** The real one: an inode
    carrying `FS_IMMUTABLE_FL` refuses an open with write intent -- `may_open()`
    returns `-EPERM` for `MAY_WRITE` on an immutable inode. That is why
    `chattr -i` has to come before the write, and why the flag ioctls themselves
    have to run on a descriptor that is not write-capable.

    Genuinely setting the flag needs `CAP_LINUX_IMMUTABLE`, which this runner
    does not have (`chattr +i` returns `EPERM` here, and `CapEff` is 0), so a
    test cannot manufacture the precondition the way `chattr` does. This stands
    in for the two things the kernel contributes: the refusal at open time, and
    the two flag ioctls. Everything else is real -- a real file, the tool's own
    `find_entry`/`read_entry`/`write_entry`, a real readback.

    So what a case using this proves is the tool's own open mode and its
    ordering. What it cannot prove is that the kernel behaves this way, and
    nothing here claims it does: that is what
    `docs/hardware-tests/uniwill-var-memoc-efivarfs.md` is for, and it has not
    been run.
    """

    def __init__(self, root, body, attrs=LIVE_ATTRS):
        self.root = Path(root) / "efivars"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / layout.guid_dent_name()
        self.path.write_bytes(struct.pack("<I", attrs) + bytes(body))
        # An efivarfs entry is immutable on arrival; that is the state the
        # write path is built around.
        self.immutable = True
        self.flag_calls = []
        self.refused = 0

    def __enter__(self):
        # `open` is not a global in the tool -- it resolves to the builtin --
        # so "was it there?" is a real question, and restoring has to answer it
        # or the next case inherits a patched `open` from this one. The real
        # `open` is taken from `builtins` rather than off the tool, which has
        # none to take.
        self._had_open = hasattr(tool, "open")
        self._saved_open = getattr(tool, "open", None)
        self._builtin_open = builtins.open
        self._open, self._ioctl = os.open, fcntl.ioctl

        def guarded_open(path, flags, *args, **kwargs):
            if (flags & os.O_ACCMODE) != os.O_RDONLY:
                self._refuse_if_immutable(path)
            return self._open(path, flags, *args, **kwargs)

        def guarded_builtin_open(path, mode="r", *args, **kwargs):
            # Scoped to the entry alone. The tool also writes the backup file,
            # which is an ordinary new file that no kernel rule applies to, and
            # a blanket refusal would stop the run before it reached the entry.
            if str(path) == str(self.path) and any(
                    m in mode for m in "wxa+"):
                self._refuse_if_immutable(path)
            return self._builtin_open(path, mode, *args, **kwargs)

        def flag_ioctl(fd, request, *args):
            if request == tool.FS_IOC_GETFLAGS:
                buf = args[0]
                buf[:] = (tool.FS_IMMUTABLE_FL if self.immutable else 0).to_bytes(4, "little")
                return 0
            if request == tool.FS_IOC_SETFLAGS:
                raw = args[0]
                value = int.from_bytes(raw, "little")
                self.flag_calls.append(bool(value & tool.FS_IMMUTABLE_FL))
                self.immutable = bool(value & tool.FS_IMMUTABLE_FL)
                return 0
            raise OSError(errno.ENOTTY, "Inappropriate ioctl for device")

        os.open, tool.open, fcntl.ioctl = guarded_open, guarded_builtin_open, flag_ioctl
        return self

    def __exit__(self, *_exc):
        os.open, fcntl.ioctl = self._open, self._ioctl
        if self._had_open:
            tool.open = self._saved_open
        elif hasattr(tool, "open"):
            delattr(tool, "open")
        return False

    def _refuse_if_immutable(self, path):
        if self.immutable:
            self.refused += 1
            raise PermissionError(errno.EPERM, "Operation not permitted", str(path))


class EfivarfsCase(unittest.TestCase):
    """A scratch directory and a `refuse()` that checks nothing was written.

    `refuse` is on the case rather than on the fake because it needs
    `assertRaises` and `assertEqual`, and because "a refusal must not have
    written" is the property every refusal case is actually asserting -- it
    belongs where the assertion is visible.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def efivars(self, body, attrs=LIVE_ATTRS, name=None):
        """A live fake, unregistered for cleanup on the way out."""
        var = FakeEfivarfs(self._tmp.name, body, attrs=attrs, name=name)
        self.addCleanup(lambda: var.__exit__(None, None, None))
        return var.__enter__()

    def refuse(self, var, *argv):
        """Run expecting a refusal; returns the message, nothing written."""
        before_bytes = var.path.read_bytes()
        with self.assertRaises(SystemExit) as caught:
            var.run(*argv)
        self.assertEqual(var.path.read_bytes(), before_bytes,
                         "a refusal must not have written to the variable")
        return str(caught.exception)


class DecodeAgainstEvidenceTests(unittest.TestCase):
    """The decoder run on the committed dumps, which is real input."""

    def setUp(self):
        self.raw = DUMP.read_bytes()

    def decode(self, raw):
        out = io.StringIO()
        with redirect_stdout(out):
            tool.decode_body(raw)
        return out.getvalue()

    def field_value(self, raw, name):
        fmt, off, size = layout.field(name)
        self.assertIsNotNone(fmt, name)
        return struct.unpack_from("<" + fmt, raw, off)[0]

    def test_the_committed_dumps_are_a_whole_struct(self):
        # The size the tool refuses to write against, checked against the files
        # rather than against the constant it also defines.
        for path in (DUMP, BEFORE, AFTER):
            self.assertEqual(len(path.read_bytes()), layout.NVRAM_STRUCT_SIZE,
                             f"{path.name}")

    def test_the_fields_the_evidence_records(self):
        # Every value `docs/findings.md` §8 and
        # `evidence/uefi/2026-09-19-UniWillVariable.txt` already state, asserted
        # from the bytes rather than from the prose.
        for name, offset, expected in (
                ("MemoryOverClockSwitch", 0x33, 0x00),
                ("OverClockRecoveryFlag", 0x5C, 0x00),
                ("ApExistFlag", 0x5D, 0x01),
                ("MemoryOverClockSupport", 0x60, 0x00),
                ("ApUseFlag", 0x61, 0x01),
                ("OemDisplayMode", 0x62, 0x04)):
            fmt, off, _size = layout.field(name)
            self.assertEqual(off, offset, f"{name} offset")
            self.assertEqual(self.field_value(self.raw, name), expected,
                             f"{name} value in {DUMP.name}")

    def test_the_decode_output_carries_the_offset_and_the_value(self):
        text = self.decode(self.raw)
        self.assertIn("0x33 MemoryOverClockSwitch", text)
        self.assertIn("0x11171D05", text)          # OemBoardSsid, the dump's own
        self.assertIn("180 with C# default alignment", text)
        self.assertIn("178 packed", text)

    def test_a_short_body_reads_as_past_end_rather_than_raising(self):
        # The `Reserved` array runs to 0xB4, so truncating loses it entirely.
        text = self.decode(self.raw[:0x70])
        self.assertIn("(past end)", text)


class RoundTripTests(unittest.TestCase):
    """The tool's own field-set reproduces the operator's committed write.

    This is the strongest assertion available without a machine: the two dumps
    are the before and after of the 2026-09-23 Windows run, they differ at one
    byte, and reproducing the transformation from them proves the layout, the
    offset and the write arithmetic together.
    """

    def setUp(self):
        self.before = BEFORE.read_bytes()
        self.after = AFTER.read_bytes()

    def test_the_two_committed_dumps_differ_at_one_byte(self):
        differing = [i for i in range(len(self.before))
                     if self.before[i] != self.after[i]]
        self.assertEqual(differing, [0x33],
                         "the dumps are the record of a one-byte write; if they "
                         "differ elsewhere the round-trip below proves less")

    def test_the_dumps_already_have_the_switch_set_and_unset(self):
        fmt, off, _ = layout.field("MemoryOverClockSwitch")
        self.assertEqual(struct.unpack_from("<" + fmt, self.before, off)[0], 0)
        self.assertEqual(struct.unpack_from("<" + fmt, self.after, off)[0], 1)

    def test_the_field_set_reproduces_the_after_dump_byte_for_byte(self):
        fmt, off, _size = layout.field("MemoryOverClockSwitch")
        out = bytearray(self.before)
        struct.pack_into("<" + fmt, out, off, 1)
        self.assertEqual(bytes(out), self.after)

    def test_the_round_trip_through_the_tool_is_the_same_bytes(self):
        # The same transformation run through `set`, against a standing-in
        # efivarfs, so what is asserted is the tool's code path and not a
        # re-derivation of it.
        with tempfile.TemporaryDirectory() as tmp:
            with FakeEfivarfs(tmp, self.before) as var:
                _code, text = var.run("set", "MemoryOverClockSwitch", "1",
                                      "--backup", str(var.backup_path()))
                self.assertIn("0x33 MemoryOverClockSwitch: 0x00 -> 0x01", text)
                self.assertIn("readback matches", text)
                body, attrs = var.read()
                self.assertEqual(body, self.after)
                self.assertEqual(attrs, LIVE_ATTRS)


class LayoutClaimTests(unittest.TestCase):
    """The layout claims the README makes, asserted rather than stated."""

    def test_the_struct_is_180_bytes_aligned_and_178_packed(self):
        _natural, natural = layout.layout(packed=False)
        _packed, packed = layout.layout(packed=True)
        self.assertEqual(natural, 180)
        self.assertEqual(packed, 178)
        self.assertEqual(layout.NVRAM_STRUCT_SIZE, 180)

    def test_the_switch_offset_does_not_depend_on_the_pack_question(self):
        # The one §8 field whose offset is the same under both readings, which
        # is why the tool can write it without resolving the question.
        natural = {n: o for n, _f, o, _s in layout.layout(packed=False)[0]}
        packed = {n: o for n, _f, o, _s in layout.layout(packed=True)[0]}
        self.assertEqual(natural["MemoryOverClockSwitch"], 0x33)
        self.assertEqual(packed["MemoryOverClockSwitch"], 0x33)

    def test_the_first_offset_sensitive_field_is_the_cpu_frequency(self):
        # So is the claim that everything past it is not safe to write blind.
        natural = {n: o for n, _f, o, _s in layout.layout(packed=False)[0]}
        packed = {n: o for n, _f, o, _s in layout.layout(packed=True)[0]}
        self.assertEqual(natural["ACpuFreqValue"], 0x44)
        self.assertEqual(packed["ACpuFreqValue"], 0x43)
        self.assertNotEqual(natural["ACpuFreqValue"], packed["ACpuFreqValue"])

    def test_the_fields_past_the_pad_are_the_ones_that_shift(self):
        # "17 fields past 0x42 shift", said as a check. Not the count of the
        # table -- it moves whenever a field is added -- but the claim the
        # README's alignment paragraph rests on, and it can only hold while the
        # table above it holds, which the ast cases below pin.
        natural = {n: o for n, _f, o, _s in layout.layout(packed=False)[0]}
        packed = {n: o for n, _f, o, _s in layout.layout(packed=True)[0]}
        shifted = {n for n in natural if natural[n] != packed[n]}
        self.assertTrue(all(natural[n] > 0x42 for n in shifted), shifted)
        self.assertIn("ACpuFreqValue", shifted)
        self.assertNotIn("MemoryOverClockSwitch", shifted)

    def test_the_layout_reads_the_committed_dump_the_way_the_txt_says(self):
        # `evidence/uefi/2026-09-19-UniWillVariable.txt` is the committed record
        # of the layout agreeing with these offsets; the one line worth holding
        # here is the switch, which the tool writes.
        raw = DUMP.read_bytes()
        fmt, off, _ = layout.field("MemoryOverClockSwitch")
        self.assertEqual(struct.unpack_from("<" + fmt, raw, off)[0], 0)
        self.assertIn("0x33 MemoryOverClockSwitch                0x00 (0)",
                      (EVIDENCE / "2026-09-19-UniWillVariable.txt").read_text())


class FieldTablePinningTests(unittest.TestCase):
    """All three copies of the field table, held to the decompiled struct.

    The duplication is deliberate (`windows/tools/uefi_var.py` runs
    `ctypes.WinDLL` at import, so nothing on Linux can import it) and this is
    what makes it safe. The two Python copies are read with `ast` rather than by
    importing them, and the C# by its declaration shape, so the check reads the
    committed source rather than a re-import that would agree with a broken one.
    """

    # The C# scalar types and the struct format each maps to.
    CS_TYPES = {"uint": "I", "ushort": "H", "byte": "B"}

    # A field declaration, and the ByValArray size that gives an array field its
    # width. The struct's members are all of one shape -- `public <type>
    # <name>;` -- so this is a whole-file parse rather than a real C# one. That
    # is a deliberate limit: `ast` is Python's parser and cannot read this file
    # at all, and no C# parser is committed here to reach for. A declaration
    # shape this regex misses shows up as a *missing field* in `cs_fields`,
    # which the comparison below reports as a mismatch -- so the failure mode is
    # red, not a silently shorter list that agrees with everything.
    CS_DECL = re.compile(r"^\s*public\s+(uint|ushort|byte(?:\[\])?)\s+"
                         r"(\w+)\s*;\s*$")
    CS_SIZE = re.compile(r"SizeConst\s*=\s*(\d+)")

    def cs_fields(self):
        """(name, fmt) per field of NVRAM_STRUCT.cs, in declaration order.

        The array fields carry `MarshalAs(UnmanagedType.ByValArray, SizeConst=N)`
        on the attribute above the declaration, so the size is read from there
        the same way the struct format's `Ns` is read off `uefi_var.py`. Getting
        that wrong would make every array field compare as a scalar and the
        check would be green on a table that does not match.
        """
        out, pending = [], None
        for line in NVRAM_STRUCT_CS.read_text(encoding="utf-8").splitlines():
            size = self.CS_SIZE.search(line)
            if size is not None:
                pending = int(size.group(1))
                continue
            match = self.CS_DECL.match(line)
            if match is None:
                continue
            csharp, name = match.groups()
            if csharp.endswith("[]"):
                self.assertIsNotNone(pending,
                                     f"{name}: array field with no SizeConst above it")
                out.append((name, f"{pending}s"))
                pending = None
            else:
                self.assertIn(csharp, self.CS_TYPES,
                              f"{name}: unexpected C# type {csharp}")
                out.append((name, self.CS_TYPES[csharp]))
        return out

    def py_table(self, path):
        """A module's NVRAM_FIELDS literal, read by ast rather than by import.

        The Python side *can* be read by `ast`, and is: a literal assignment
        evaluates the same whether it came from the module or from the source,
        but reading it here means a `uefi_var.py` that cannot be imported at all
        on this platform is still checked.
        """
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "NVRAM_FIELDS":
                        return [(n, f) for n, f in ast.literal_eval(node.value)]
        self.fail(f"no NVRAM_FIELDS assignment in {path}")

    def test_the_struct_declares_the_fields_the_tool_uses(self):
        # Guard the parser itself. A parse that returned nothing would make the
        # comparisons below vacuously true, which is the one outcome worse than
        # a table that does not match.
        fields = self.cs_fields()
        self.assertTrue(fields)
        self.assertEqual(len(fields), len(layout.NVRAM_FIELDS),
                         "the C# parse found a different number of fields; a "
                         "short parse would make the comparisons vacuous")
        self.assertIn("MemoryOverClockSwitch", dict(fields))
        self.assertIn("Reserved", dict(fields))

    def test_the_layout_table_matches_the_decompiled_struct(self):
        self.assertEqual(self.cs_fields(), layout.NVRAM_FIELDS)

    def test_the_windows_tool_table_matches_the_decompiled_struct(self):
        # The other copy, in the file that cannot be imported here. Held to the
        # same source, so the two cannot drift apart either.
        self.assertEqual(self.cs_fields(), self.py_table(UEFI_VAR_PY))

    def test_all_three_tables_agree(self):
        # The claim the module docstring makes, asserted once: same fields, same
        # order, same widths, same array sizes.
        self.assertEqual(layout.NVRAM_FIELDS, self.py_table(UEFI_VAR_PY))

    def test_a_field_edited_on_one_side_only_is_caught(self):
        # The check's own worth, in both directions: it has to fail when the C#
        # moves and it has to fail when a copy moves, or it is a green run that
        # says nothing. A renamed field and a resized array are the two edits a
        # vendor update would actually make.
        good = self.cs_fields()
        self.assertNotEqual(good, [("SupportByte", "I")] + good[1:])
        self.assertNotEqual(good, [(n, "16s" if f.endswith("s") else f)
                                   for n, f in good])
        self.assertEqual(self.cs_fields(), self.py_table(UEFI_VAR_PY),
                         "the unedited tree must still agree")


class GuidNamingTests(unittest.TestCase):
    """The efivarfs dentry name, and the two spellings the matcher accepts.

    `docs/findings.md` §8's "For Linux" paragraph and issue #118 both give
    `UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593`, and that is right:
    efivarfs keeps the GUID's dashes in the dentry and drops only the braces,
    and every entry on a real efivarfs mount is spelled that way. So these hold
    §8's spelling as the one the kernel produces, and the matcher's tolerance
    of the separator-free form as a property of `--var` rather than a claim
    about what any kernel writes.
    """

    def test_the_dent_name_is_the_dashed_spelling_the_findings_give(self):
        name = layout.guid_dent_name()
        self.assertEqual(name, "UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593")
        self.assertNotIn("{", name, "braces are the one thing a filename drops")
        self.assertEqual(name, layout.UNIWILL_NAME + "-" + layout.UNIWILL_GUID[1:-1])

    def test_both_spellings_are_accepted_by_the_matcher(self):
        # The dashed dentry is what the kernel writes, and the 32-bare-digit
        # form is what a `--var` directory might hold instead. `is_var_dent`
        # strips separators from both sides, so the tool finds the entry either
        # way. This is asserted against `is_var_dent` rather than against
        # `guid_dent_name`, which is the half that decides.
        for name in (layout.guid_dent_name(), layout.guid_dent_name_hex()):
            self.assertTrue(layout.is_var_dent(name), name)
        self.assertNotEqual(layout.guid_dent_name(), layout.guid_dent_name_hex(),
                            "two distinct spellings, both matched")

    def test_the_guid_is_the_one_the_findings_and_issue_spell(self):
        # Named rather than incidental: the string in §8 is this, and it is the
        # string an implementer would paste into a path.
        self.assertEqual(layout.UNIWILL_GUID, "{9f33f85c-13ca-4fd1-9c4a-96217722c593}")
        self.assertEqual(len(layout.UNIWILL_GUID_HEX), 32)
        self.assertRegex(layout.UNIWILL_GUID_HEX, r"^[0-9a-f]{32}$")
        # §8's path and the dentry the kernel writes are the same file, which
        # is the claim the old inverted "correction" denied.
        self.assertIn(layout.guid_dent_name(),
                      (REPO / "docs" / "findings.md").read_text(encoding="utf-8"))

    def test_a_dent_name_is_matched_on_name_and_digits(self):
        good = layout.guid_dent_name()
        self.assertTrue(layout.is_var_dent(good))
        self.assertFalse(layout.is_var_dent("Other-" + layout.UNIWILL_GUID_HEX))
        self.assertFalse(layout.is_var_dent("UniWillVariable-deadbeef" * 2))
        self.assertFalse(layout.is_var_dent(good + "x"))


class RefusalTests(EfivarfsCase):
    """Every refusal, each asserting the variable was not written."""

    def setUp(self):
        super().setUp()
        self.body = BEFORE.read_bytes()
        self.var = self.efivars(self.body)

    def test_a_set_without_a_backup_is_refused(self):
        # argparse's own requirement, checked through the same entry point so
        # the refusal cannot be lost by a later edit to the parser. stderr is
        # captured too: argparse writes its usage there, and an unredirected
        # run of this suite would put a usage block in the middle of the
        # runner's per-suite output.
        before = self.var.path.read_bytes()
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit):
            self.var.run("set", "MemoryOverClockSwitch", "1")
        self.assertIn("--backup", err.getvalue())
        self.assertEqual(self.var.path.read_bytes(), before)

    def test_an_existing_backup_is_not_overwritten(self):
        target = self.var.backup_path()
        target.write_bytes(b"a backup somebody cares about")
        message = self.refuse(self.var, "set", "MemoryOverClockSwitch", "1",
                              "--backup", str(target))
        self.assertIn("not overwriting a backup", message)
        self.assertEqual(target.read_bytes(), b"a backup somebody cares about")

    def test_a_body_that_is_not_the_struct_size_is_refused(self):
        # The one that matters most: efivarfs does not truncate-patch, it
        # replaces the variable with what was written, so a tool that wrote 179
        # bytes would leave a 179-byte NVRAM_STRUCT behind.
        self.var.put(self.body[:179], LIVE_ATTRS)
        message = self.refuse(self.var, "set", "MemoryOverClockSwitch", "1",
                              "--backup", str(self.var.backup_path()))
        self.assertIn("layout not trusted", message)
        self.assertFalse(self.var.backup_path().exists(),
                         "a refused write must not leave a backup behind either")

    def test_an_array_field_is_refused(self):
        for name in ("Reserved", "RGBKeyboard1A"):
            with self.subTest(field=name):
                message = self.refuse(self.var, "set", name, "1", "--backup",
                                      str(self.var.backup_path()))
                self.assertIn("byte[] field", message)

    def test_an_unknown_field_is_refused(self):
        message = self.refuse(self.var, "set", "MemoryOverClockSwitchk", "1",
                              "--backup", str(self.var.backup_path()))
        self.assertIn("no scalar field", message)
        self.assertNotIn("byte[] field", message,
                         "a typo must not be reported as an array field")

    def test_a_value_that_does_not_fit_the_field_is_refused(self):
        message = self.refuse(self.var, "set", "MemoryOverClockSwitch", "0x100",
                              "--backup", str(self.var.backup_path()))
        self.assertIn("does not fit", message)

    def test_a_body_only_file_is_never_a_write_target(self):
        for cmd, argv in (("set", ("set", "MemoryOverClockSwitch", "1",
                                   "--backup", str(self.var.backup_path()))),
                          ("restore", ("restore",
                                       str(self.var.backup_path())))):
            with self.subTest(cmd=cmd):
                message = self.refuse(self.var, *argv, "--body-only", str(BEFORE))
                self.assertIn("--body-only is a decode input", message)

    def test_an_unknown_var_path_says_so_and_names_the_path(self):
        # `/sys/firmware/efi/efivars` is absent on a CSM boot, and "no such
        # file or directory" on its own sends people looking for the tool.
        missing = str(Path(self._tmp.name) / "not-here")
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            tool.main(["--var", missing, "show"])
        message = str(caught.exception)
        self.assertIn(missing, message)
        self.assertIn("UEFI", message)
        self.assertIn("CSM", message)

    def test_an_entry_with_the_wrong_guid_is_not_mistaken_for_this_one(self):
        self.var.path.unlink()
        wrong = self.var.root / ("UniWillVariable-" + "0" * 32)
        wrong.write_bytes(struct.pack("<I", LIVE_ATTRS) + self.body)
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            tool.main(["--var", str(self.var.root), "show"])
        self.assertIn("does not match", str(caught.exception))

    def test_two_matching_entries_are_refused_rather_than_guessed(self):
        # Two *different* files that both name this variable: the fake's entry
        # carries the dashed spelling efivarfs actually writes, and this second
        # one carries the same GUID as 32 bare digits. The matcher strips
        # separators, so it accepts both -- and that is exactly why the tool
        # must still refuse here rather than pick one. Two files claiming one
        # variable, and writing the wrong one would be worse than refusing.
        self.assertNotEqual(layout.guid_dent_name(), layout.guid_dent_name_hex(),
                            "the two entries have to be distinct files")
        second = self.var.root / layout.guid_dent_name_hex()
        second.write_bytes(struct.pack("<I", LIVE_ATTRS) + self.body)
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            tool.main(["--var", str(self.var.root), "show"])
        self.assertIn("refusing to guess", str(caught.exception))


class NoOpAndReadbackTests(EfivarfsCase):
    """The two write outcomes that are not "a byte changed"."""

    def setUp(self):
        super().setUp()
        self.body = BEFORE.read_bytes()
        self.var = self.efivars(self.body)

    def test_an_equal_value_writes_nothing(self):
        # 0x33 is already 0 in the before-dump, so this is the no-op arm.
        snapshot = self.var.path.read_bytes()
        _code, text = self.var.run("set", "MemoryOverClockSwitch", "0",
                                   "--backup", str(self.var.backup_path()))
        self.assertIn("already set; nothing written", text)
        self.assertEqual(self.var.path.read_bytes(), snapshot)
        # The backup is still written: it is the record of what was there, and
        # the no-op is about the variable, not about the file.
        self.assertTrue(self.var.backup_path().exists())

    def test_a_readback_that_does_not_match_is_a_failure(self):
        # The readback is the tool's whole success criterion, so the failing
        # direction needs a case or the check is one refactor from being a
        # report rather than a gate. The second read is what the tool compares
        # against, so that is the one made to disagree.
        real_read = tool.read_entry
        calls = []

        def flaky(path):
            body, attr = real_read(path)
            calls.append(path)
            return (body + b"\0", attr) if len(calls) > 1 else (body, attr)

        tool.read_entry = flaky
        self.addCleanup(lambda: setattr(tool, "read_entry", real_read))
        with self.assertRaises(SystemExit) as caught:
            self.var.run("set", "MemoryOverClockSwitch", "1", "--backup",
                         str(self.var.backup_path()))
        self.assertIn("readback does not match", str(caught.exception))


class FramingTests(EfivarfsCase):
    """The 4-byte attribute prefix, in both directions and through a restore."""

    def setUp(self):
        super().setUp()
        self.body = BEFORE.read_bytes()

    def test_the_attribute_word_is_read_from_the_first_four_bytes(self):
        var = self.efivars(self.body)
        body, attrs = var.read()
        self.assertEqual(attrs, LIVE_ATTRS)
        self.assertEqual(layout.attr_flags(attrs), "NV|BS|RT")
        self.assertEqual(body, self.body)

    def test_a_set_preserves_the_attributes_and_every_other_byte(self):
        var = self.efivars(self.body)
        var.run("set", "MemoryOverClockSwitch", "1", "--backup",
                str(var.backup_path()))
        body, attrs = var.read()
        self.assertEqual(attrs, LIVE_ATTRS)
        self.assertEqual([i for i in range(len(body))
                          if body[i] != self.body[i] and i != 0x33], [],
                         "only 0x33 may change")

    def test_an_append_attribute_is_not_silently_dropped(self):
        # A variable carrying APPEND is a different variable, and efivarfs
        # stores the attributes it is given. Carrying them through is what the
        # Windows tool does (uniwill_set.py passes `attr` back untouched), so
        # a set here must not quietly rewrite the word to NV|BS|RT.
        var = self.efivars(self.body, attrs=LIVE_ATTRS | 0x40)
        var.run("set", "MemoryOverClockSwitch", "1", "--backup",
                str(var.backup_path()))
        _body, attrs = var.read()
        self.assertEqual(attrs, LIVE_ATTRS | 0x40)

    def test_a_backup_round_trips_through_a_restore(self):
        var = self.efivars(self.body)
        backup = var.backup_path("before.bin")
        var.run("set", "MemoryOverClockSwitch", "1", "--backup", str(backup))
        self.assertEqual(backup.read_bytes(), self.body)
        _code, text = var.run("restore", str(backup))
        self.assertIn("restored", text)
        body, attrs = var.read()
        self.assertEqual(body, self.body)
        self.assertEqual(attrs, LIVE_ATTRS)

    def test_a_restore_of_the_wrong_length_is_refused(self):
        var = self.efivars(self.body)
        short = var.backup_path("short.bin")
        short.write_bytes(self.body[:100])
        message = self.refuse(var, "restore", str(short))
        self.assertIn("backup is 100 bytes", message)

    def test_an_entry_shorter_than_the_prefix_is_refused(self):
        var = self.efivars(self.body)
        # Two bytes: too short to even carry the attribute word. Written
        # directly rather than through `put`, which would re-add the prefix.
        var.path.write_bytes(b"\x07\x00")
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            tool.read_entry(var.path)
        self.assertIn("too short", str(caught.exception))


class ImmutableFlagTests(EfivarfsCase):
    """The flag comes back, including when the write raises.

    An efivarfs entry left writable is a variable any later process can replace,
    so this is the one piece of cleanup that must not be conditional on the
    write having succeeded.
    """

    def setUp(self):
        super().setUp()
        self.body = BEFORE.read_bytes()

    def test_the_flag_is_taken_off_before_the_write_and_back_on_after(self):
        var = self.efivars(self.body)
        var.run("set", "MemoryOverClockSwitch", "1", "--backup",
                str(var.backup_path()))
        self.assertEqual(var.flag_calls, [False, True],
                         "immutable off, then on, in that order")

    def test_the_entry_is_never_opened_for_writing_while_it_is_immutable(self):
        """The open mode, which is the whole of the fix and the easiest to undo.

        `set_immutable` exists to clear `FS_IMMUTABLE_FL` from a file that has
        it, and the kernel refuses a write-intent open on exactly that state, so
        opening the entry `O_RDWR` to issue the flag ioctl fails on the very
        condition the function is called to undo -- before the first ioctl, and
        before the caller has entered the `try` that would put the flag back.
        `set` and `restore` then abort at the first write on a healthy machine,
        at the step the procedure hands a human as its centre.

        The recorder in `FakeEfivarfs` cannot see this, because it replaces
        `set_immutable` wholesale, and the case that does call the real
        function opens a file that was never made immutable, where `O_RDWR`
        succeeds happily. So the assertion is on the *mode*, which needs no
        privilege and no immutable file: hold the real `set_immutable` against a
        real file and check the descriptor it hands the ioctls is not
        write-capable. `chattr` is the reference, and it is read-only too --
        `strace -e trace=openat,ioctl chattr +i f` opens `f`
        `O_RDONLY|O_NONBLOCK|O_NOFOLLOW` and runs both ioctls on that
        descriptor.
        """
        real_open = os.open
        opened = []

        def recording_open(path, flags, *args, **kwargs):
            opened.append(flags)
            return real_open(path, flags, *args, **kwargs)

        os.open = recording_open
        self.addCleanup(lambda: setattr(os, "open", real_open))
        target = Path(self._tmp.name) / "entry"
        target.write_bytes(b"payload")
        try:
            tool.set_immutable(target, False)
        except OSError as exc:
            # The open-mode claim does not depend on the ioctl being supported,
            # so this case does not skip the way the one below it has to; the
            # filesystem property is not what is under test.
            if exc.errno not in (errno.ENOTTY, errno.EOPNOTSUPP):
                raise
        self.assertTrue(opened, "set_immutable must open the entry at all")
        for flags in opened:
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY,
                             "the flag ioctl needs the inode, not write access "
                             "to the file; a write-intent open is refused by "
                             "the kernel on an immutable entry")

    def test_a_write_succeeds_against_an_entry_that_is_immutable_on_arrival(self):
        """The write path, run against a file that refuses writes when set.

        The case above pins the open mode; this one is the consequence, and it
        is the shape the real machine presents: an efivarfs entry is immutable
        on arrival, and the tool has to clear the flag before it can write at
        all. Under `ImmutableEntryModel` a write-intent open of the entry
        raises `EPERM` whenever the flag is set, which is what the kernel does.

        An earlier version of this tool opened the entry `O_RDWR` inside
        `set_immutable`, so `set` died with `PermissionError` before its first
        write -- a green suite over a write path that cannot run on the target,
        because every other case in this class swaps the function out for a
        recorder that never opens anything. That version is refused here at the
        very first open, so it never reaches the `refused` assertion at all;
        the fixed one never asks for write access while the flag is set, the
        count is unchanged and the write goes in. Both halves matter, because a
        run that cannot tell "the guard fired" from "the guard was never
        installed" is not a test: the precondition is proved by trying the
        refused open directly, and the tool's own run is then asserted not to
        need one.
        """
        var = ImmutableEntryModel(self._tmp.name, self.body)
        with var:
            # The precondition, checked rather than assumed: this entry really
            # does refuse a write-intent open while it is immutable, which is
            # the state an efivarfs entry is in on arrival.
            with self.assertRaises(PermissionError):
                os.open(var.path, os.O_RDWR)
            armed = var.refused
            out = io.StringIO()
            with redirect_stdout(out):
                tool.main(["--var", str(var.root), "set",
                           "MemoryOverClockSwitch", "1",
                           "--backup", str(var.root / "backup.bin")])
            body, attr = tool.read_entry(var.path)
            self.assertEqual(var.refused, armed,
                             "the tool asked for write access to an entry that "
                             "was still immutable; the flag has to come off "
                             "first")
        self.assertEqual(var.flag_calls, [False, True],
                         "immutable off, then on, in that order")
        fmt, off, _size = layout.field("MemoryOverClockSwitch")
        self.assertEqual(struct.unpack_from("<" + fmt, body, off)[0], 1,
                         "the byte that was asked for is the byte that is there")
        self.assertTrue(var.immutable,
                        "the entry is left immutable, as it was found")

    def test_the_flag_is_restored_when_the_write_raises(self):
        var = self.efivars(self.body)
        # The tool opens the entry with the builtin `open`, resolved through the
        # module's globals, so the failure has to be injected there. A patch on
        # `Path.write_bytes` would leave this case green without the write ever
        # having failed, which is the failure mode this case exists to prevent.
        tool.open = _open_that_fails_on(var.path)
        self.addCleanup(lambda: delattr(tool, "open"))
        with self.assertRaises(OSError):
            var.run("set", "MemoryOverClockSwitch", "1", "--backup",
                    str(var.backup_path()))
        self.assertEqual(var.flag_calls, [False, True],
                         "a failed write must still put the flag back")

    def test_a_filesystem_with_no_flag_ioctl_is_reported_not_silently_assumed(self):
        # tmpfs and a few others have no FS_IOC_SETFLAGS, and the flag's
        # behaviour has varied across kernel versions. The write still happens;
        # what must not happen is the tool reporting a restored immutability it
        # never got.
        var = self.efivars(self.body)
        real_set = tool.set_immutable

        def unsupported(path, immutable):
            var.flag_calls.append(bool(immutable))
            return False

        tool.set_immutable = unsupported
        self.addCleanup(lambda: setattr(tool, "set_immutable", real_set))
        _code, text = var.run("set", "MemoryOverClockSwitch", "1", "--backup",
                              str(var.backup_path()))
        self.assertIn("immutable flag ioctl was not accepted", text)
        self.assertIn("readback matches", text,
                      "the write still goes through; only the flag is unknown")
        self.assertEqual(var.flag_calls, [False, True])

    def test_the_real_ioctl_is_called_the_way_the_kernel_expects(self):
        """`set_immutable` against a real file, not the recorder.

        Every other case in this class swaps `set_immutable` out, so nothing
        else here runs the ioctl at all -- and the function is where a wrong
        call is invisible: `FS_IOC_GETFLAGS` *writes* the flags through the
        pointer it is handed, so passing an integer hands the kernel a null
        pointer, the call fails EFAULT, and the `except OSError` that is there
        for a filesystem without the ioctl swallows it. The tool then reports
        "this filesystem has no flag ioctl" about a perfectly capable one, and
        never clears the flag, so the write that follows fails EACCES against a
        still-immutable entry. `chattr`'s idiom is the reference: a mutable
        buffer, and `True` to say the call mutates it.

        Clearing the flag needs no privilege -- setting it wants
        CAP_LINUX_IMMUTABLE -- so this clears, which is the direction the bug
        broke and the one a test can run unprivileged. On a filesystem with no
        flag ioctl at all there is nothing here to test, and that is the
        documented property of the filesystem rather than of the tool, so the
        case skips instead of asserting a shape the kernel does not have.

        The skip is on those two errnos and nothing else, which is the point:
        an earlier version of this case caught every `OSError`, and so skipped
        on the very `EFAULT` it exists to catch -- a test that reports "not
        applicable here" about the bug it was written for is worse than no
        test, because it is green.
        """
        target = Path(self._tmp.name) / "entry"
        target.write_bytes(b"payload")
        try:
            cleared = tool.set_immutable(target, False)
        except OSError as exc:
            if exc.errno in (errno.ENOTTY, errno.EOPNOTSUPP):
                self.skipTest(f"no FS_IOC_SETFLAGS on this filesystem: "
                              f"{exc.errno} {exc.strerror}")
            raise
        self.assertTrue(cleared,
                        "a real ext4 file accepted the ioctl, so returning "
                        "False here means the call itself was malformed")

    def test_a_malformed_ioctl_is_not_reported_as_an_unsupported_filesystem(self):
        """The errno narrowing, which is the half of the fix that is testable.

        `EFAULT` and `EPERM` are this function's own failures, not a property
        of the filesystem, and folding them into the ENOTTY case is what let the
        bad call pass for a missing ioctl. A stubbed return value could not
        catch that: it answers the question the caller asks rather than the one
        the function has to get right.
        """
        real_ioctl = tool.fcntl.ioctl

        def broken_ioctl(fd, request, *args):
            # What the kernel does with a null pointer: nothing is written back.
            raise OSError(errno.EFAULT, "Bad address")

        tool.fcntl.ioctl = broken_ioctl
        self.addCleanup(lambda: setattr(tool.fcntl, "ioctl", real_ioctl))
        target = Path(self._tmp.name) / "entry"
        target.write_bytes(b"payload")
        with self.assertRaises(OSError) as caught:
            tool.set_immutable(target, False)
        self.assertEqual(caught.exception.errno, errno.EFAULT,
                         "EFAULT is this tool's bug and must not be swallowed "
                         "into a 'this filesystem has no ioctl' note")

    def test_a_filesystem_with_no_flag_ioctl_returns_false_rather_than_raising(self):
        """The ENOTTY/EOPNOTSUPP branch the narrowing has to keep."""
        real_ioctl = tool.fcntl.ioctl

        def no_such_ioctl(fd, request, *args):
            raise OSError(errno.ENOTTY, "Inappropriate ioctl for device")

        tool.fcntl.ioctl = no_such_ioctl
        self.addCleanup(lambda: setattr(tool.fcntl, "ioctl", real_ioctl))
        target = Path(self._tmp.name) / "entry"
        target.write_bytes(b"payload")
        self.assertFalse(tool.set_immutable(target, False))


class ReadOnlyCommandsTests(EfivarfsCase):
    """`show` and `get` touch nothing, and `show` can save what it read."""

    def setUp(self):
        super().setUp()
        self.body = BEFORE.read_bytes()
        self.var = self.efivars(self.body)
        self.snapshot = self.var.path.read_bytes()

    def test_show_reads_and_writes_nothing(self):
        _code, text = self.var.run("show")
        self.assertIn("attributes NV|BS|RT", text)
        self.assertIn("0x33 MemoryOverClockSwitch", text)
        self.assertEqual(self.var.path.read_bytes(), self.snapshot)

    def test_get_reports_the_offset_and_the_value(self):
        _code, text = self.var.run("get", "MemoryOverClockSwitch")
        self.assertEqual(text.strip(), "0x33 MemoryOverClockSwitch: 0x00 (0)")
        self.assertEqual(self.var.path.read_bytes(), self.snapshot)

    def test_get_past_the_end_of_a_short_body_is_refused(self):
        self.var.put(self.body[:0x34], LIVE_ATTRS)
        message = self.refuse(self.var, "get", "OverClockRecoveryFlag")
        self.assertIn("past the end", message)

    def test_save_writes_the_body_without_the_attribute_prefix(self):
        # The shape of the committed `evidence/uefi/*.bin`, so a `--save` here
        # produces a file `show --body-only` can read back.
        out = Path(self._tmp.name) / "saved.bin"
        self.var.run("show", "--save", str(out))
        self.assertEqual(out.read_bytes(), self.body)
        _code, text = self.var.run("show", "--body-only", str(out))
        self.assertIn("body only", text)


class NoHardwareClaimTests(unittest.TestCase):
    """The suite must not become a claim that the efivarfs route was exercised.

    `docs/findings.md` §8's "That route has not been exercised" is still true,
    and the thing that would quietly make it false is a test that reads like a
    live result. So the two documents that say the run has not happened are
    held to it from here.
    """

    def test_the_procedure_still_says_it_has_not_been_run(self):
        doc = (REPO / "docs" / "hardware-tests" / "uniwill-var-memoc-efivarfs.md")
        self.assertTrue(doc.is_file(), doc)
        head = doc.read_text(encoding="utf-8")[:2000]
        self.assertIn("not run", head)

    def test_the_readme_calls_the_readback_a_transport_check(self):
        readme = (HERE / "README.md").read_text(encoding="utf-8")
        self.assertIn("readback", readme)
        self.assertRegex(readme, r"readback[^.]*is (a )?transport",
                         "a matching readback is transport, not behaviour")

    def test_no_document_under_this_directory_claims_the_menu_appeared(self):
        # The one sentence only hardware could produce. Narrow on purpose: a
        # general "does this document claim a live result" scan goes red on the
        # sentences that *explain* the distinction -- this directory's whole
        # subject is that a matching readback is not the menu -- and a check
        # that fires on its own subject gets deleted rather than satisfied.
        #
        # So it names the specific overclaim and allows the negated form, which
        # is the form these documents use to rule it out. Scoped to the files
        # this directory carries, so an unrelated edit elsewhere cannot turn it
        # red.
        negated = re.compile(r"\b(not|never|no|nothing|cannot|has not|had not|"
                             r"unless|if|would|must not)\b", re.I)
        claim = re.compile(r"\b(?:the\s+)?(?:memory\s+)?menu\b[^.\n]*\b"
                           r"(appeared|appears|is visible|was unlocked|"
                           r"is unlocked)\b", re.I)
        for path in sorted(HERE.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for paragraph in re.split(r"\n\s*\n", text):
                if not claim.search(paragraph):
                    continue
                # The unit is the paragraph, not the sentence: these documents
                # rule the claim out in a neighbouring clause ("...what a green
                # run does not prove: that ... the BIOS menu appears"), and
                # reading the sentence alone would call its own denial a claim.
                self.assertRegex(
                    paragraph, negated,
                    f"{path.name}: reads as a live result: "
                    f"{' '.join(paragraph.split())[:160]!r}")


if __name__ == "__main__":
    unittest.main()