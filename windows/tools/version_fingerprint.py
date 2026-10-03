#!/usr/bin/env python3
r"""Say which vintage a Windows vendor artifact is, from bytes alone.

Issue #83 has to tell a 2021 Control Center apart from the committed 3.1.39.0,
and the obvious way to do it -- read the version -- works on some of these files
and not others, in a way that is worth knowing before the 2021 file turns up
rather than after. Measured over the committed vendor set by `--self-check`:

- the **installer** carries the Control Center release in its own version
  resource (`3.1.6.0`, `3.9.18.0`), so an installer is self-dating;
- the **installed service** does not: `GCUService.exe` out of release 3.1.39.0
  reports `FileVersion 1.0.2.70`, and so does the `Assembly` table, and its
  `ProductName` is the string `GCUService`. There is no field anywhere in that
  PE that says 3.1.39.0;
- `ACPIDriver.sys` has no version resource at all.

So "read the version" dates an *installer* and does not date the service it
installs: no field in a recovered `Program Files\OEM` tree carries the Control
Center release, so such a tree cannot be placed by release. That is not the
same as undatable. Its COFF link stamp and its SHA-256 are there, and both
place it relative to the committed set -- the driver's own stamp is 2020-09-14,
the service's 2021-09-28 -- so run this over a recovered tree before
concluding anything about it. The narrow claim is a fact about the vendor's
build scripts, it is why the recovery is worth doing in a particular order,
and it is a *negative* result: "no version found" here means the vendor did
not write one, never that the file is unlabelled or unimportant.

**What it reads, all of it inside the file:**
- SHA-256 of the whole image, which is the one field that is never ambiguous;
- the COFF `TimeDateStamp`, i.e. what the linker recorded;
- `VS_VERSION_INFO`: `VS_FIXEDFILEINFO`'s file and product version, and the
  `StringFileInfo` table (`CompanyName`, `FileDescription`, `FileVersion`,
  `ProductName`, `ProductVersion`, `OriginalFilename`, ...);
- for a .NET assembly, the `Assembly` table's name and version, which is a
  different number from the version resource and is the one a C# `#if` or a
  binding redirect cares about.

No disassembler, no Windows, no network. `dnfile` is optional and is what reads
the `Assembly` table; without it the .NET half is reported as not read rather
than absent.

**`TimeDateStamp` is a link stamp, not a release date**, and the committed set
shows why in one comparison: the 3.1.6.0 and the 3.9.18.0 installers carry the
*same* one, `0x5CC41133`. What is measured is that one stamp is shared across
two different releases. A shared setup stub is the obvious explanation and is
consistent with it, but that is an inference, not a measurement. The
consequence either way is the same: a tool that printed the stamp as a release
date would date the 3.9.18.0 installer into the 3.1.6.0 era. That limits what
the stamp is *for* -- it is not a release date and not an install date --
without making it useless: it still places a file relative to the committed
set, and the 3.9.18.0 package's own payloads post-date it (`ACPIDriver.sys`
2020-09-14, `ACPIDriverDll.dll` 2020-12-10). Every field here is labelled for
what it is, and a field that is not in the file is reported as not in the file
rather than inferred from a sibling.

`pe_triage.py` is the sibling tool for native binaries; it parses PE32+ only and
no resources, and two of the artifacts here are PE32, so the header and resource
parse below is written out rather than imported.

Usage:
    python3 version_fingerprint.py vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe
    python3 version_fingerprint.py --csv *.exe *.dll *.sys > fingerprints.csv
    python3 version_fingerprint.py --self-check        # the committed vendor set
"""
import argparse
import csv
import datetime
import hashlib
import os
import struct
import sys

MACHINE = {0x014C: "x86", 0x8664: "x86-64", 0x01C0: "ARM", 0xAA64: "ARM64"}
OPT_MAGIC = {0x010B: "PE32", 0x020B: "PE32+"}

RT_VERSION = 16

# What StringFileInfo holds that is worth a column, and the order to print it
# in. Not every file has every key: an absent key is left out of the output
# rather than printed empty, so a reader can tell "not in the file" from
# "in the file and blank".
STRING_KEYS = ("CompanyName", "FileDescription", "FileVersion", "InternalName",
               "LegalCopyright", "OriginalFilename", "ProductName",
               "ProductVersion")

FIXEDFILEINFO_SIG = 0xFEEF04BD

# Unix epoch 1970-01-01T00:00:00Z, which is what a COFF TimeDateStamp counts
# seconds from. Written out because the stamp is a *link* time and the reader
# is entitled to know that before converting it.
_EPOCH = (1970, 1, 1, 0, 0, 0)


class PE:
    """The PE header, the section table, and the resource directory.

    Both optional-header magics, because the committed vendor set contains
    PE32 installers as well as PE32+ binaries. Deliberately not an extension of
    `pe_triage.PE`: that class raises on anything but PE32+ and parses no
    resources, and this tool's `--self-check` reads two PE32 files.
    """

    def __init__(self, data: bytes):
        self.data = data
        if data[:2] != b"MZ":
            raise ValueError("not a PE: no MZ signature")
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off:pe_off + 4] != b"PE\0\0":
            raise ValueError("not a PE: no PE signature")
        coff = pe_off + 4
        (self.machine, self.nsections, self.timestamp, _symtab, _nsyms,
         opt_size, self.characteristics) = struct.unpack_from("<HHIIIHH", data, coff)

        opt = coff + 20
        self.magic = struct.unpack_from("<H", data, opt)[0]
        if self.magic not in OPT_MAGIC:
            raise ValueError(f"unknown optional header magic 0x{self.magic:04X}")
        # DataDirectory starts at 96 in PE32 and 112 in PE32+, and its count
        # sits in the four bytes before it in both.
        dd = opt + (96 if self.magic == 0x010B else 112)
        ndirs = struct.unpack_from("<I", data, dd - 4)[0]
        self.dirs = [struct.unpack_from("<II", data, dd + 8 * i) for i in range(ndirs)]

        sec = opt + opt_size
        self.sections = []
        for i in range(self.nsections):
            off = sec + 40 * i
            name = data[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
            self.sections.append((name, vaddr, vsize, rawptr, rawsize))

    def rva_to_off(self, rva: int):
        for _name, vaddr, vsize, rawptr, rawsize in self.sections:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                off = rva - vaddr + rawptr
                return off if off < len(self.data) else None
        return None

    def _dir(self, index: int):
        return self.dirs[index] if index < len(self.dirs) else (0, 0)

    def resource(self, want_type: int):
        """The bytes of the first `want_type` leaf, or None.

        The resource directory is a three-level tree -- type, name, language --
        and only the last level holds a data entry rather than another
        directory. Two encodings matter and both are easy to get wrong: an
        entry whose high bit is set points at a *subdirectory* by offset from
        the start of the resource section, and one whose bit is clear points at
        a data entry by *RVA*. Following the second as if it were the first
        lands the parse in whatever bytes follow, which is why every step here
        is bounds-checked and a failure is None rather than a wrong answer.
        """
        rva, _size = self._dir(2)
        if not rva:
            return None
        base = self.rva_to_off(rva)
        if base is None:
            return None
        try:
            node = self._descend(base, 0, want_type)
            node = self._descend(base, node, None)
            # The language level is a leaf, so its target is an offset into the
            # resource section rather than another subdirectory.
            leaf = self._entry_target(base, node, None)
            if leaf is None or leaf & 0x80000000:
                return None
            leaf_rva, leaf_size = struct.unpack_from("<II", self.data, base + leaf)
            start = self.rva_to_off(leaf_rva)
        except (struct.error, IndexError, ValueError):
            return None
        if start is None:
            return None
        return self.data[start:start + min(leaf_size, len(self.data) - start)]

    def _descend(self, base: int, node: int, want_id):
        """`node`'s wanted subdirectory, as an offset from `base`."""
        target = self._entry_target(base, node, want_id)
        return None if target is None or not target & 0x80000000 \
            else target & 0x7FFFFFFF

    def _entry_target(self, base: int, node: int, want_id):
        """The raw target of the wanted entry under `node`, or the first one.

        `want_id` None means "the first entry at this level", which is what the
        name and language levels want: a file with two version resources is a
        shape this does not model, and taking the first is better than guessing
        which is current -- the caller reports that it found one.
        """
        if node is None:
            return None
        named, ids = struct.unpack_from("<HH", self.data, base + node + 12)
        for i in range(named + ids):
            entry, target = struct.unpack_from("<II", self.data, base + node + 16 + 8 * i)
            if want_id is None or (not entry & 0x80000000 and entry == want_id):
                return target
        return None


def _utf16z(data: bytes, off: int):
    end = data.find(b"\0\0", off)
    while end != -1 and (end - off) % 2:
        end = data.find(b"\0\0", end + 1)
    if end == -1:
        return ""
    return data[off:end].decode("utf-16le", "replace")


def _pad4(off: int) -> int:
    return (off + 3) & ~3


def parse_version_info(blob: bytes):
    """-> (file version, product version, {key: value}), each "" when unread.

    `wValueLength` counts the VS_FIXEDFILEINFO in *bytes* while the same field
    in a child counts its string in bytes-plus-terminator, and the header is
    padded to a 4-byte boundary before each value. Getting that wrong lands the
    parse in the middle of a string, which is the kind of failure that yields a
    plausible wrong version rather than an error, so every step is bounds-checked
    against `blob` and an unreadable one reports "" rather than a guess.
    """
    strings = {}
    if len(blob) < 6:
        return "", "", strings
    w_length, w_value_len, _w_type = struct.unpack_from("<HHH", blob, 0)
    if w_length > len(blob) or w_length < 6:
        return "", "", strings
    if _utf16z(blob, 6) != "VS_VERSION_INFO":
        return "", "", strings

    pos = _pad4(6 + len("VS_VERSION_INFO") * 2 + 2)
    file_v = product_v = ""
    if w_value_len >= 52 and pos + 52 <= len(blob) and \
            struct.unpack_from("<I", blob, pos)[0] == FIXEDFILEINFO_SIG:
        file_ms, file_ls = struct.unpack_from("<II", blob, pos + 8)
        prod_ms, prod_ls = struct.unpack_from("<II", blob, pos + 16)
        file_v = _quad(file_ms, file_ls)
        product_v = _quad(prod_ms, prod_ls)
        pos = _pad4(pos + w_value_len)

    for key, value in _string_children(blob, pos, min(w_length, len(blob))):
        strings[key] = value
    return file_v, product_v, strings


def _quad(ms: int, ls: int) -> str:
    """A `dwVersionMS`/`dwVersionLS` pair as `a.b.c.d`: two 16-bit halves each."""
    return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"


def _string_children(blob: bytes, pos: int, end: int):
    """Every `key`/`value` pair under a StringFileInfo, at any table depth.

    A StringFileInfo holds StringTables which hold Strings, and all three are
    the same record shape -- length, value length, type, key, value, pad to
    four -- differing only in whether `wValueLength` is zero. A container's
    `wLength` spans its children as well as its own header, so the next
    sibling sits at the end of the whole subtree and the children sit just
    after the key. Reading only the top level finds `StringFileInfo` and no
    strings at all, which is the failure that looks like "this file has no
    version strings".
    """
    while pos + 6 <= end:
        w_length, w_value_len, _w_type = struct.unpack_from("<HHH", blob, pos)
        if w_length < 6 or pos + w_length > end:
            return
        key = _utf16z(blob, pos + 6)
        head = _pad4(pos + 6 + (len(key) + 1) * 2)
        if w_value_len:
            if key and head < len(blob):
                # Inno Setup right-pads its own fields to a fixed column, so a
                # raw read carries dozens of spaces that are not part of the
                # value and would make two identical versions look different.
                yield key, _utf16z(blob, head).strip()
        elif key in _CONTAINERS or _is_string_table(key):
            yield from _string_children(blob, head, pos + w_length)
        pos = _pad4(pos + w_length)


# The two record names that hold other records rather than a value. A
# StringTable's key is a language-and-codepage block ("000004b0") rather than a
# name, which is why it is recognised by shape.
_CONTAINERS = ("StringFileInfo",)


def _is_string_table(key: str) -> bool:
    return len(key) == 8 and all(c in "0123456789abcdefABCDEF" for c in key)


def timestamp_utc(stamp: int) -> str:
    """COFF `TimeDateStamp` as UTC, or the reason there is not one.

    A zero stamp means the linker was not told to record one, and is reported
    as that rather than as 1970. Any other stamp is converted and shown as it
    is: a field that says 2106 is a wrong field, which is a fact about the
    file, and a reader who is told "no date" would have no way to tell it from
    a file that genuinely carries none. The field is 32 bits, so no value in it
    can overflow the conversion.
    """
    if not stamp:
        return "not recorded (0)"
    return str(datetime.datetime(*_EPOCH, tzinfo=datetime.timezone.utc)
               + datetime.timedelta(seconds=stamp))


def dotnet_assembly(path: str):
    """(name, `a.b.c.d`) from the `Assembly` metadata table, or None.

    None covers all three ways it can fail to answer -- no dnfile, not a .NET
    assembly, or a metadata root the obfuscator damaged -- and they are the
    same answer for this tool's purpose: the `Assembly` table was not read.
    Which of the three it was is worth knowing, so `dotnet_status` says.
    """
    try:
        import dnfile
    except ImportError:
        return None, "dnfile not installed"
    try:
        pe = dnfile.dnPE(path)
    except Exception as exc:  # dnfile raises a wide range on damaged input
        return None, f"unreadable: {type(exc).__name__}"
    if getattr(pe, "net", None) is None:
        return None, "no CLI header: not a .NET assembly"
    try:
        rows = list(pe.net.mdtables.Assembly)
    except Exception as exc:
        return None, f"no Assembly table: {type(exc).__name__}"
    if not rows:
        return None, "no Assembly table: empty"
    a = rows[0]
    return (str(a.Name), "{}.{}.{}.{}".format(a.MajorVersion, a.MinorVersion,
                                             a.BuildNumber, a.RevisionNumber)), ""


def fingerprint(path: str) -> dict:
    """Every field this tool can read out of one artifact, plus how each went."""
    with open(path, "rb") as fh:
        data = fh.read()
    row = {
        "path": path,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    try:
        pe = PE(data)
    except (ValueError, struct.error) as exc:
        row["pe"] = f"not a PE ({exc})"
        row["machine"] = row["format"] = row["timestamp"] = ""
        row["timestamp_utc"] = ""
        row["fixed_file_version"] = row["fixed_product_version"] = ""
        row["assembly_name"] = row["assembly_version"] = ""
        row["dotnet"] = ""
        for key in STRING_KEYS:
            row[key] = ""
        return row

    row["machine"] = MACHINE.get(pe.machine, f"0x{pe.machine:04X}")
    row["format"] = OPT_MAGIC[pe.magic]
    row["timestamp"] = f"0x{pe.timestamp:08X}"
    row["timestamp_utc"] = timestamp_utc(pe.timestamp)

    # VS_FIXEDFILEINFO holds the file version and the product version in two
    # separate 8-byte fields. They agree on every committed artifact here, and
    # are still read separately: a file whose two disagree is the one case
    # where quoting either as "the version" gives a different answer.
    res = pe.resource(RT_VERSION)
    file_v = product_v = ""
    strings = {}
    if res is None:
        row["_version_resource"] = "absent from the file"
    else:
        file_v, product_v, strings = parse_version_info(res)
        row["_version_resource"] = "read" if file_v else "present but not parsed"
    # Named `fixed_` because StringFileInfo carries a `FileVersion` string too
    # and the two are separate fields: on these files they agree, and a caller
    # that cannot tell which one it read cannot tell whether they do.
    row["fixed_file_version"] = file_v
    row["fixed_product_version"] = product_v
    for key in STRING_KEYS:
        row[key] = strings.get(key, "")

    asm, status = dotnet_assembly(path)
    row["assembly_name"] = asm[0] if asm else ""
    row["assembly_version"] = asm[1] if asm else ""
    row["dotnet"] = status or "read"
    return row


CSV_FIELDS = (["path", "size", "sha256", "machine", "format", "timestamp",
               "timestamp_utc", "fixed_file_version", "fixed_product_version"]
              + list(STRING_KEYS)
              + ["assembly_name", "assembly_version"])


def print_one(row: dict) -> None:
    def field(label, value):
        print(f"  {label:<22}{value or '(not in the file)'}")

    print(row["path"])
    field("size", str(row["size"]))
    field("sha256", row["sha256"])
    if not row.get("machine"):
        field("", row.get("pe", "unreadable"))
        return
    field("pe", f"{row['format']} {row['machine']}")
    field("TimeDateStamp", f"{row['timestamp']} ({row['timestamp_utc']})")
    field("version resource", row.get("_version_resource", "read"))
    field("FileVersion (fixed)", row["fixed_file_version"])
    field("ProductVersion (fix)", row["fixed_product_version"])
    for key in STRING_KEYS:
        if row.get(key):
            field(f"{key} (string)", row[key])
    if row["assembly_name"]:
        field("Assembly", f"{row['assembly_name']}, Version={row['assembly_version']}")
    else:
        field("Assembly", f"not read ({row['dotnet']})")


# The committed vendor artifacts, and what each one is here to establish.
#
# The two installer rows are the ones the tool exists for: both carry the same
# COFF TimeDateStamp, and they wrap two different releases. A fingerprint tool
# that reported that stamp as a release date would date the 3.9.18.0 installer
# to the 3.1.6.0 era, so the self-check pins the equality -- the two stamps
# *do* match -- as a known answer about the wrapper rather than about the
# payload. Nothing here dates either release: the directory names encode a
# version number, not a time, and no committed file carries a date for them.
# What the committed binaries do carry is a chronology for the files
# themselves -- the 3.9.18.0 payloads post-date the installers' shared stamp,
# `ACPIDriver.sys` 2020-09-14 and `ACPIDriverDll.dll` 2020-12-10 against
# `0x5CC41133` 2019-04-27.
SELF_CHECK = [
    "vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe",
    "vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe",
    "vendor/control-center-3.9.18.0/setup.exe",
    "vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys",
    "vendor/control-center-3.9.18.0/ACPIDriverDll.dll",
]

# The oracle, transcribed from `windows/decompiled/v3.1.39.0/README.md`, not
# from a run of this tool: "the executable's own `FileVersion` is `1.0.2.70`".
# That README records it as prose about the shipped file, so the tool
# recovering it is two independent readings agreeing, and a tool that graded
# itself would pass whatever it produced.
ORACLE_ASSEMBLY_VERSION = "1.0.2.70"

# The same README's `DisplayVersion 3.1.39.0`, which is what the *release* is
# called and which the PE does not carry. Asserted as a difference so a reader
# learns from the self-check, not only from prose, that a version resource is
# not a Control Center version.
ORACLE_CONTROL_CENTER_VERSION = "3.1.39.0"


def self_check(repo: str) -> int:
    """The committed vendor set, against answers this file did not produce."""
    bad = 0
    print("version_fingerprint.py --self-check")

    def expect(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    rows = {}
    for rel in SELF_CHECK:
        try:
            rows[rel] = fingerprint(f"{repo}/{rel}" if repo else rel)
        except OSError as exc:
            expect(f"{rel} reads", False, str(exc))
            return 1

    for rel in SELF_CHECK:
        row = rows[rel]
        expect(f"{rel}: a PE header and a SHA-256",
               bool(row["machine"]) and len(row["sha256"]) == 64)

    gc = rows[SELF_CHECK[0]]
    expect("GCUService.exe FileVersion is the README's 1.0.2.70",
           gc["fixed_file_version"] == ORACLE_ASSEMBLY_VERSION,
           f"got {gc['fixed_file_version']!r}")
    expect("GCUService.exe's Assembly table version is 1.0.2.70 too",
           gc["assembly_version"] == ORACLE_ASSEMBLY_VERSION,
           f"got {gc['assembly_version']!r}")
    expect("GCUService.exe's FileVersion is not the Control Center release it "
           "belongs to, so the installed service cannot be dated by its "
           "version resource",
           gc["fixed_file_version"] != ORACLE_CONTROL_CENTER_VERSION,
           f"FileVersion {gc['fixed_file_version']} against a "
           f"{ORACLE_CONTROL_CENTER_VERSION} release")

    # The other side of the same fact, and the actionable one: the *installer*
    # does carry the release number in its own version resource. A recovered
    # 2021 installer is therefore dateable and a recovered `Program Files\\OEM`
    # tree is not -- which is what tells a human where to spend the recovery
    # effort.
    expect("both installers' own version resources carry the Control Center "
           "release they wrap, so an installer is dateable",
           rows[SELF_CHECK[1]]["fixed_file_version"] == "3.1.6.0"
           and rows[SELF_CHECK[2]]["fixed_file_version"] == "3.9.18.0",
           f"{rows[SELF_CHECK[1]]['fixed_file_version']} and "
           f"{rows[SELF_CHECK[2]]['fixed_file_version']}")

    old = rows[SELF_CHECK[1]]
    new = rows[SELF_CHECK[2]]
    expect("both installers carry the same COFF TimeDateStamp, and it is not "
           "the release date of what either wraps",
           old["timestamp"] == new["timestamp"] and old["timestamp"] != "",
           f"{old['timestamp']} vs {new['timestamp']}")
    expect("their payloads are not the same artifact, so the shared stamp is "
           "not evidence the two are the same version",
           old["sha256"] != new["sha256"])

    # The refusal: a stamp of zero means the linker recorded none. It must not
    # be rendered as 1970, which would read as a date.
    expect("a zero TimeDateStamp is reported as not recorded, not as 1970",
           timestamp_utc(0) == "not recorded (0)")
    expect("a real stamp converts to a UTC date",
           timestamp_utc(0x61528305).startswith("2021-09-28"),
           timestamp_utc(0x61528305))

    # The resource parse against a hand-built blob, because every real file
    # here is also a .NET image or an installer: these assertions are about the
    # parser, and no committed artifact isolates it from the file around it.
    file_v, product_v, strings = parse_version_info(_synthetic_version_blob())
    expect("a synthetic VS_VERSION_INFO yields the file version it encodes",
           file_v == "3.4.5.6", f"got {file_v!r}")
    expect("a synthetic VS_VERSION_INFO keeps the product version separate",
           product_v == "3.4.5.7", f"got {product_v!r}")
    expect("a synthetic VS_VERSION_INFO yields its ProductName",
           strings.get("ProductName") == "Synthetic", f"got {strings!r}")
    expect("a truncated VS_VERSION_INFO reads as nothing rather than as a "
           "version", parse_version_info(b"\x06\x00\x00\x00\x00\x00") == ("", "", {}))
    expect("a VS_VERSION_INFO with the wrong key reads as nothing rather than "
           "as a version", parse_version_info(b"\x06\x00\x00\x00\x00\x00"
                                              b"N\x00o\x00t\x00 \x00i\x00t\x00") ==
           ("", "", {}))

    print("data:" if not bad else f"{bad} failure(s); data:")
    w = csv.DictWriter(sys.stdout, CSV_FIELDS, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows.values())
    return 1 if bad else 0


def _synthetic_version_blob() -> bytes:
    """A minimal VS_VERSION_INFO: one fixed file info, one string table.

    Built here rather than shipped as a fixture, because `ec/tools/testdata/`
    carries its own hand-written index (`check_testdata_index.py`), and a
    286-byte blob does not need a row in it.

    Two things about it are chosen to catch a parser rather than to exercise
    one. The file version and the product version differ in a single component,
    so a parse that reads the wrong field is caught instead of agreeing by
    accident. And the strings sit two records deep -- `StringFileInfo` holds a
    `StringTable` holds a `String` -- because a walker that stops at the first
    level finds the table's own name and no strings at all, which is a failure
    that looks like a file with no version strings.
    """
    fixed = struct.pack("<IIIIII",
                        FIXEDFILEINFO_SIG,
                        0x00010000,                    # dwStrucVersion
                        0x00030004, 0x00050006,        # file    3.4.5.6
                        0x00030004, 0x00050007)        # product 3.4.5.7
    fixed += b"\0" * (52 - len(fixed))

    strings = b"".join(
        _version_record(k, v.encode("utf-16le") + b"\0\0", wtype=1)
        for k, v in (("ProductName", "Synthetic"), ("CompanyName", "Nobody")))
    strings = _version_record("StringFileInfo", children=strings)
    strings = _version_record("000004b0", children=strings)
    strings = _version_record("StringFileInfo", children=strings)
    return _version_record("VS_VERSION_INFO", fixed, children=strings, wtype=0)


def _version_record(key: str, value: bytes = b"", children: bytes = b"",
                    wtype: int = 1) -> bytes:
    """One VS_VERSION_INFO-shaped record: header, key, pad, value, children.

    `wLength` is the whole record *and* its subtree, which is why it cannot be
    written until `children` is known. `wValueLength` is the value's byte count
    including its terminator -- except at the root, where the value is the
    binary VS_FIXEDFILEINFO and the field is already the right length.
    """
    keyb = key.encode("utf-16le") + b"\0\0"
    pad = -(6 + len(keyb)) % 4
    total = 6 + len(keyb) + pad + len(value) + len(children)
    return (struct.pack("<HHH", total, len(value), wtype) + keyb
            + b"\0" * pad + value + children)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="PE files to fingerprint")
    ap.add_argument("--csv", action="store_true", help="one row per file")
    ap.add_argument("--self-check", action="store_true",
                    help="fingerprint the committed vendor set")
    args = ap.parse_args(argv)

    if args.self_check:
        here = os.path.dirname(os.path.abspath(__file__))
        return self_check(os.path.abspath(os.path.join(here, os.pardir, os.pardir)))

    if not args.paths:
        ap.error("give paths, or --self-check")

    rows = []
    for path in args.paths:
        try:
            rows.append(fingerprint(path))
        except OSError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return 1

    if args.csv:
        w = csv.DictWriter(sys.stdout, CSV_FIELDS, lineterminator="\n",
                           extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    else:
        for i, row in enumerate(rows):
            if i:
                print()
            print_one(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
