#!/usr/bin/env python3
r"""Read UniWillVariable through efivarfs; write one field, with a backup.

SAFETY ENVELOPE. `show` and `get` are read-only. `set` and `restore` write, and
both refuse to run without a backup file they did not create, refuse a variable
that is not exactly 180 bytes, and refuse an array field. A write is one
`chattr -i`, one write of the whole 184-byte entry, one `chattr +i`, then a
readback of every byte. **A successful run means the bytes written are the
bytes read back; it does not mean the EC or the BIOS acted on them.** The only
thing that shows the menu appearing is a reboot and a human looking at it.

WHAT IT IS. The Linux half of `windows/tools/uefi_var.py` (decode) and
`windows/tools/uniwill_set.py` (one-field write, backup, readback). The
variable is `UniWillVariable` {9f33f85c-13ca-4fd1-9c4a-96217722c593}, the block
the vendor service rewrites whole on any field change; `docs/findings.md` §8 is
the analysis and `evidence/uefi/` the committed dumps.

The efivarfs entry is a 4-byte little-endian attribute word (NV|BS|RT here)
followed by the 180-byte NVRAM_STRUCT, and the entry is immutable until
`chattr -i`. Note the dentry name: efivarfs keeps the GUID's dashes, so the
file is `UniWillVariable-9f33f85c-13ca-4fd1-9c4a-96217722c593`, the spelling
§8 gives. This tool does not build that path from a hand-typed string anyway:
it globs `UniWillVariable-*` and verifies the trailing digits, so it finds the
entry whichever way a given directory spells the GUID and still refuses a
different variable's entry sitting under the same name.

`--body-only` decodes a bare 180-byte dump with no attribute prefix, which is
the shape of the committed `evidence/uefi/*.bin`. It is a **decode-only**
input: no write subcommand accepts it, because a body file is not the live
variable and a write built from one would replace a 184-byte entry with a file
whose first four bytes are somebody's memory clock.

`MemoryOverClockSupport` (0x60) is writable here like any other field and is
**not the way in**; see the README, and §8's reason (the service's
`SetUserProfile()` puts 0x33 back on the next power-mode change when 0x60 is 1).

Usage:
  sudo python3 linux/uniwill-var/uniwill-var.py show
  sudo python3 linux/uniwill-var/uniwill-var.py get MemoryOverClockSwitch
  sudo python3 linux/uniwill-var/uniwill-var.py set MemoryOverClockSwitch 1 \
      --backup /tmp/uniwill-before.bin
  sudo python3 linux/uniwill-var/uniwill-var.py restore /tmp/uniwill-before.bin
  python3 linux/uniwill-var/uniwill-var.py show --body-only \
      evidence/uefi/2026-09-19-UniWillVariable.bin
"""
import argparse
import errno
import fcntl
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nvram_layout as L  # noqa: E402

# FS_IOC_SETFLAGS / FS_IMMUTABLE_FL, the ioctl `chattr -i` and `chattr +i` are.
# Hand-rolled rather than shelled out to because the whole safety argument here
# is that the immutable flag goes back on even when the write failed, and that
# belongs in a `finally` this process controls.
FS_IOC_GETFLAGS = 0x80086601
FS_IOC_SETFLAGS = 0x40086602
FS_IMMUTABLE_FL = 0x00000010


def set_immutable(path, immutable):
    """Set or clear FS_IMMUTABLE_FL on an efivarfs entry.

    -> whether the kernel accepted it. efivarfs entries are immutable by
    default, but the flag has varied across kernel versions and the ioctl is
    not guaranteed on every filesystem a `--var` path might point at, so the
    caller is told rather than left to assume either way: a write that went in
    with the flag never coming back would otherwise be silent.

    An absent ioctl is tolerated, an *unwritable* entry is not. The first means
    there was nothing to clear; the second raises out of the write below, which
    is the honest outcome rather than a tool that reports success it did not
    get.

    Both ioctls take the flags as a 4-byte buffer they write through, so the
    buffer is a `bytearray` and the third argument is `True` to say so. Passing
    an integer instead hands the kernel a null pointer, and the call fails
    EFAULT -- which is why the errno test below names two errnos and not
    "any OSError".

    THE OPEN IS READ-ONLY, and that is load-bearing rather than tidy. The
    entry being opened is the one carrying `FS_IMMUTABLE_FL` -- that is the
    whole reason this function exists -- and the kernel refuses a write-intent
    open on an immutable file: `may_open()` returns `-EPERM` for `MAY_WRITE`
    on an immutable inode, which is exactly what `os.O_RDWR` asks for. So
    opening the entry `O_RDWR` here fails on precisely the state this is
    called to undo, before the first ioctl, and the caller has not yet entered
    the `try` whose `finally` puts the flag back.

    `chattr` is the reference and never opens the file for writing. Traced on
    a runnable filesystem, `strace -e trace=openat,ioctl chattr +i f` opens
    `f` `O_RDONLY|O_NONBLOCK|O_NOFOLLOW` twice and issues `FS_IOC_GETFLAGS`
    and then `FS_IOC_SETFLAGS` on that read-only descriptor. The flag ioctls
    want the *inode*, not write access to the file's contents, so a read-only
    descriptor is all they need; `O_NONBLOCK` is carried over with it because
    it is chattr's other flag and costs nothing here.

    Do not "simplify" this back to `O_RDWR`. The write is a separate open, in
    `write_entry`, issued only after this returns with the flag confirmed
    clear.
    """
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        buf = bytearray(4)
        fcntl.ioctl(fd, FS_IOC_GETFLAGS, buf, True)
        flags = int.from_bytes(buf, "little")
        flags = flags | FS_IMMUTABLE_FL if immutable else flags & ~FS_IMMUTABLE_FL
        fcntl.ioctl(fd, FS_IOC_SETFLAGS, flags.to_bytes(4, "little"))
    except OSError as exc:
        # ENOTTY/EOPNOTSUPP: the filesystem behind --var has no flag ioctl, so
        # there is nothing to clear. Every other errno is this function's own
        # fault -- EFAULT for the buffer above, EPERM for setting the flag
        # without CAP_LINUX_IMMUTABLE -- and reporting those as "no ioctl here"
        # would send the reader after a filesystem that is working fine.
        if exc.errno in (errno.ENOTTY, errno.EOPNOTSUPP):
            return False
        raise
    finally:
        os.close(fd)
    return True


def find_entry(vardir):
    """The efivarfs entry for this variable, located by glob and verified.

    efivarfs names each dentry `Name-<guid>`, keeping the GUID's dashes, which
    is the path §8 spells. Globbing the name and then checking the trailing
    digits anyway is what makes `--var` safe to point anywhere: the tool works
    on a directory that spells the GUID either way, and would still refuse a
    directory holding a different variable's entry under this name.
    """
    root = Path(vardir)
    if not root.is_dir():
        raise SystemExit(
            f"error: {vardir} is not a directory. /sys/firmware/efi/efivars exists "
            f"only on a UEFI boot -- check the machine booted UEFI and not CSM, "
            f"or pass --var if this is a different path.")
    found = [p for p in sorted(root.iterdir())
             if L.is_var_dent(p.name)]
    if not found:
        near = [p.name for p in sorted(root.glob(L.UNIWILL_NAME + "-*"))]
        raise SystemExit(
            f"error: no {L.UNIWILL_NAME}-<guid> entry under {vardir}"
            + (f"; found {near[0]} whose GUID does not match {L.UNIWILL_GUID}"
               if near else "; the variable may not exist on this board"))
    if len(found) > 1:
        raise SystemExit(f"error: {len(found)} entries match "
                         f"{L.UNIWILL_NAME}-<guid>; refusing to guess: "
                         + ", ".join(str(p) for p in found))
    return found[0]


def read_entry(path):
    """-> (body, attributes) for an efivarfs entry.

    The 4-byte prefix is the variable's attributes, which are part of the
    variable: efivarfs passes them back on the next read and stores them on the
    next write, so they are carried rather than reconstructed.
    """
    raw = Path(path).read_bytes()
    if len(raw) < 4:
        raise SystemExit(f"error: {path} is {len(raw)} bytes; too short to carry "
                         f"even the 4-byte attribute prefix")
    return raw[4:], struct.unpack_from("<I", raw, 0)[0]


def write_entry(path, body, attr):
    """Write body+attributes to an efivarfs entry, then read the whole thing back.

    One write of the whole entry. A short write here is not a partial update:
    the variable is replaced with however many bytes were written, so a 180-byte
    struct cannot be one truncated write away from being 179.
    """
    blob = struct.pack("<I", attr) + bytes(body)
    cleared = set_immutable(path, False)
    try:
        with open(path, "wb") as handle:
            handle.write(blob)
    finally:
        # Restored unconditionally. A failed write must not leave the entry
        # writable for whatever happens next in this session.
        restored = set_immutable(path, True)
    if not (cleared and restored):
        print("note: the immutable flag ioctl was not accepted here; the write "
              "went through, and whether the entry is immutable afterwards is "
              "the kernel's answer rather than this tool's")
    back, back_attr = read_entry(path)
    if back != bytes(body) or back_attr != attr:
        raise SystemExit("error: readback does not match what was written")


def decode_body(raw):
    """Print the hexdump and the §8 field table, as `uefi_var.py uniwill` does."""
    natural, nat_size = L.layout(packed=False)
    packed, pk_size = L.layout(packed=True)
    print(f"variable is {len(raw)} bytes; NVRAM_STRUCT is {nat_size} with C# "
          f"default alignment, {pk_size} packed")
    for (name, fmt, off, size), (_, _, poff, _) in zip(natural, packed):
        def val(o):
            if o + size > len(raw):
                return "(past end)"
            v = struct.unpack_from("<" + fmt, raw, o)[0]
            return v.hex(" ") if isinstance(v, bytes) else f"0x{v:0{size * 2}X} ({v})"
        note = "" if off == poff else f"   [packed @0x{poff:02X}: {val(poff)}]"
        print(f"  0x{off:02X} {name:36s} {val(off)}{note}")


def hexdump(raw):
    for i in range(0, len(raw), 16):
        row = raw[i:i + 16]
        print(f"  {i:04X}: {row.hex(' '):47s}  "
              + "".join(chr(b) if 32 <= b < 127 else "." for b in row))


def resolve_source(args):
    """-> (body, attr or None, path or None, label) for this invocation.

    `attr is None` and `path is None` together are the `--body-only` case, and
    they are what the write paths refuse on: there is no live 184-byte entry
    behind those bytes to write back to or read back from.
    """
    if args.body_only:
        raw = Path(args.body_only).read_bytes()
        return raw, None, None, f"{args.body_only} (body only, no attributes)"
    path = find_entry(args.var)
    body, attr = read_entry(path)
    return body, attr, path, str(path)


def add_common(parser, suppress):
    """The options every subcommand shares, added to one parser.

    `suppress` is what lets the same option be accepted on either side of the
    subcommand. argparse splits at the subcommand, so an option declared only on
    the main parser is unreachable once `show` has been typed; and a subparser
    that carries a real default overwrites whatever the main parser already
    parsed, so `--var X show` would quietly lose the `X`. SUPPRESS leaves the
    attribute alone when the option was not given after the subcommand, which is
    the only behaviour that makes both spellings mean the same thing.
    """
    default = argparse.SUPPRESS if suppress else L.EFIVARS_DIR
    parser.add_argument("--var", default=default,
                        help="efivarfs directory (default: %s)"
                             % L.EFIVARS_DIR)
    parser.add_argument("--save",
                        default=argparse.SUPPRESS if suppress else None,
                        help="also write the raw bytes read to this file")
    parser.add_argument("--body-only", metavar="FILE",
                        default=argparse.SUPPRESS if suppress else None,
                        help="decode a bare 180-byte dump with no 4-byte "
                             "attribute prefix; decode only, never a write target")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_common(ap, suppress=False)
    sub = ap.add_subparsers(dest="cmd")
    common = argparse.ArgumentParser(add_help=False)
    add_common(common, suppress=True)
    sub.add_parser("show", parents=[common],
                   help="hexdump + field table + attributes (read-only)")
    p = sub.add_parser("get", parents=[common],
                       help="one field, its offset and its value")
    p.add_argument("field")
    p = sub.add_parser("set", parents=[common],
                       help="set one scalar field, with a backup")
    p.add_argument("field")
    p.add_argument("value", type=lambda s: int(s, 0))
    p.add_argument("--backup", required=True)
    p = sub.add_parser("restore", parents=[common], help="write a backup back")
    p.add_argument("backup")
    args = ap.parse_args(argv)
    args.cmd = args.cmd or "show"

    # Every refusal below names the reason and writes nothing. The order is the
    # safety order: what is being written to, is it the right size, is there a
    # backup, is the field writable at all, and only then the value.
    if args.cmd in ("set", "restore") and args.body_only:
        raise SystemExit(
            f"error: --body-only is a decode input. {args.cmd} needs the live "
            f"184-byte efivarfs entry to write back and read back from; run "
            f"without --body-only.")

    body, attr, path, label = resolve_source(args)

    if args.cmd == "show":
        head = f"{L.UNIWILL_NAME} {L.UNIWILL_GUID}: {len(body)} bytes"
        if attr is not None:
            head += f", attributes {L.attr_flags(attr)}"
        print(f"{head}  [{label}]")
        hexdump(body)
        decode_body(body)
        if args.save:
            Path(args.save).write_bytes(body)
        return 0

    if args.cmd == "get":
        f = L.field(args.field)
        if f is None:
            raise SystemExit(
                f"error: no scalar field {args.field!r} in NVRAM_STRUCT"
                + (" (that one is a byte[] field)"
                   if L.is_array(args.field) else ""))
        fmt, off, size = f
        if off + size > len(body):
            raise SystemExit(f"error: 0x{off:02X} {args.field} is past the end "
                             f"of {len(body)} bytes")
        v = struct.unpack_from("<" + fmt, body, off)[0]
        print(f"0x{off:02X} {args.field}: 0x{v:0{size * 2}X} ({v})")
        if args.save:
            Path(args.save).write_bytes(body)
        return 0

    if len(body) != L.NVRAM_STRUCT_SIZE:
        raise SystemExit(
            f"error: variable is {len(body)} bytes, NVRAM_STRUCT is "
            f"{L.NVRAM_STRUCT_SIZE}; layout not trusted, not writing")

    if args.cmd == "restore":
        old = Path(args.backup).read_bytes()
        if len(old) != len(body):
            raise SystemExit(f"error: backup is {len(old)} bytes, variable is "
                             f"{len(body)}")
        write_entry(path, old, attr)
        print(f"restored {args.backup}; readback matches")
        return 0

    # set. The backup is mandatory (argparse), must not already exist, and is
    # written before anything else happens to the variable.
    f = L.field(args.field)
    if f is None:
        raise SystemExit(
            f"error: no scalar field {args.field!r} in NVRAM_STRUCT"
            + (" (that one is a byte[] field; this writes scalars)"
               if L.is_array(args.field) else ""))
    fmt, off, size = f
    if not 0 <= args.value < (1 << (size * 8)):
        raise SystemExit(f"error: {args.value} does not fit a {size}-byte "
                         f"{args.field}")
    if os.path.exists(args.backup):
        raise SystemExit(f"error: {args.backup} exists; not overwriting a backup")
    with open(args.backup, "wb") as handle:
        handle.write(body)
    old_value = struct.unpack_from("<" + fmt, body, off)[0]
    new = bytearray(body)
    struct.pack_into("<" + fmt, new, off, args.value)
    print(f"0x{off:02X} {args.field}: 0x{old_value:0{size * 2}X} -> "
          f"0x{args.value:0{size * 2}X} (backup: {args.backup})")
    if old_value == args.value:
        print("already set; nothing written")
        return 0
    write_entry(path, new, attr)
    print("written; readback matches -- which is a transport check, not evidence "
          "the EC or BIOS acted on it")
    if args.save:
        Path(args.save).write_bytes(bytes(new))
    return 0


if __name__ == "__main__":
    sys.exit(main())