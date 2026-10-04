#!/usr/bin/env python3
"""Tabulate the ACPI argument-header slots `ACPIDriver.sys` builds.

**What it reads.** The committed `windows/decompiled/native/ACPIDriver.asm`, one
line per instruction, and nothing else. No driver is loaded, no IOCTL is issued
and no EC register is touched; this is a read of the listing the write-up
`docs/findings/acpi-eval-argument-datalength.md` reasons from, made repeatable.

**Why a tool for this.** `ACPIDriver.sys.analysis.md` and
`ACPIDriver.sys`'s own generated C disagree about how many bytes `MMRD`'s
`mov qword ptr [RSP + 0x60], 0x40000` occupies, and that disagreement is
settled by the `.asm`. Which handlers carry the constant, at which slot, and
whether anything rewrites the four bytes under it is then a question about
every handler rather than about one, and `grep -c 40000` answers none of the
three. So this parses the listing once and prints the table the write-up
embeds, which is what makes the table a reading rather than a transcription.

**The two constants it is about, and why they are the whole question.**
`ACPI_EVAL_INPUT_BUFFER_COMPLEX` puts its header at `0x50` on the stack
(Signature `0x50`, MethodName `0x54`, Length `0x58`, ArgumentCount `0x5c`) and
its first `ACPI_METHOD_ARGUMENT` at `0x60`. The handler writes the argument
header as one dword at `+0`, of which `SMRW` and `T3WR` store `0x00800002` --
`Type = 2` and, at `+2`, a length of `0x80`, which is the count each of them
passes to `memcpy_s`, and which each reads back out of the slot as
`movzx R9D, word ptr [RSP + 0x62]` (`0x140001CB0`, `0x140002A40`) after
storing it. The scalar handlers store `0x00040000` there instead, which under
that same 16-bit-at-`+2` reading is a length of `4` over the four payload
bytes stored immediately after. This tool reports the stores; it does not
decide what any operating system makes of the field, which is a question about
`ACPI.sys` and not about this binary.

**Calibration.** Every conclusion here is a statement about the committed
listing and the method this way of reading it. The listing is a
disassembly, so an instruction the exporter did not emit is invisible to it;
that is the same blind spot `ec/tools/scan_refs.py` documents for its own scan
and it is why nothing here is worded as an absence. `MMWB` is the worked case
for what the tool cannot see by looking at literals alone: it has two
arguments and one constant, because its second header comes from a register.
Resolving a register source is a one-step-backward lookup for a zeroing `xor`
and nothing more -- it is not dataflow, it is the narrowest rule that reads
this listing correctly, and where it does not apply the source is reported
unresolved rather than guessed.

**What this is not.** `windows/tools/ecrw.py` is unchanged by anything here:
under both readings of the slot arithmetic the four byte stores copy
`SystemBuffer[0..3]` to `0x64`-`0x67` in order, so `Ec.read_dword`'s
little-endian `EC_BASE + addr` is intact either way.

**What this is checked by.** `windows/tools/test_acpi_eval_arg_slots.py`
holds the properties against the committed listing, and `--self-test` below
holds the parse and the slot arithmetic against fixtures -- including the
clobbered-slot case the committed tree does not contain, which is the one a
parse that always answered "intact" would pass.

Usage:
    python3 windows/tools/acpi_eval_arg_slots.py            # the table
    python3 windows/tools/acpi_eval_arg_slots.py --csv      # one row per slot
    python3 windows/tools/acpi_eval_arg_slots.py --handler FUN_1400015ec
    python3 windows/tools/acpi_eval_arg_slots.py --self-test
"""
import argparse
import csv
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DEFAULT_ASM = os.path.join(REPO, "windows", "decompiled", "native", "ACPIDriver.asm")

# `; ==== FUN_1400015ec @ 1400015EC`
MARKER = re.compile(r"^;\s+====\s+(\S+)\s+@\s+([0-9A-Fa-f]+)\s*$")
# `mov qword ptr [RSP + 0x60], 0x40000`. The offset is deliberately not
# constrained to the argument array, so this also matches the buffer's own
# fields at 0x50-0x5c; callers decide what an offset means. Filtering here
# would hide a handler that moved an argument somewhere this tool had not
# thought to look.
STORE = re.compile(r"^mov\s+(byte|word|dword|qword)\s+ptr\s+\[RSP \+ (0x[0-9a-f]+)\],"
                   r"\s*(0x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*)\s*$")
# `mov dword ptr [RSP + 0x5c], 0x3` -- ArgumentCount, an immediate in every handler
COUNT = re.compile(r"^mov\s+dword\s+ptr\s+\[RSP \+ 0x5c\],\s*(0x[0-9a-fA-F]+)\s*$")
# `mov dword ptr [RSP + 0x54], 0x44524d4d` -- the MethodName, stored as four chars
METHOD = re.compile(r"^mov\s+dword\s+ptr\s+\[RSP \+ 0x54\],\s*(0x[0-9a-fA-F]+)\s*$")

WIDTH = {"byte": 1, "word": 2, "dword": 4, "qword": 8}

# The buffer's own fields, from `FUN_1400015ec`'s stores: each is written
# separately rather than as one object, which is what puts the argument array
# at 0x60 instead of leaving its position a reading of Ghidra's stack layout.
# `ARG_BASE` is the buffer base plus the four dwords above it (Signature,
# MethodName, Length, ArgumentCount).
ARG_BASE = 0x60
ARG_STRIDE = 8
HEADER_BYTES = 4  # two 16-bit fields; the payload starts at +4

# The length a handler states in its argument headers. Little-endian in a dword
# at the slot's +0, so `0x00040000` is `Type = 0` at +0 and `4` at +2.
LITERAL_4 = 0x00040000
# `SMRW` and `T3WR`: `Type = 2` (buffer) at +0 and `0x80` at +2. The listing
# spells it `0x800002`; the dword is bytes `02 00 80 00`, so the length is in
# the *upper* half here where `LITERAL_4`'s is in the lower one. That `0x80` is
# the same value each passes to `memcpy_s`, computed there separately as
# `R15 + 0x7e` -- a coincidence of values, not a dataflow, and the write-up
# says so rather than claiming the field feeds the copy.
LITERAL_BUFFER = 0x00800002

# Register families, for the register-source rule described in the docstring.
# The rule needs to know that `xor EDI, EDI` clears `RDI` too, because the
# handlers zero the 32-bit form and store the 64-bit one. Written out rather
# than derived, because the eight legacy registers have eight spellings each
# (`SI`, `ESI`, `RSI`, `SIL`) and no rule that covers them stays readable.
# Anything not here -- a width keyword from `mov qword ptr [RSP + ...]`, say --
# is None, which is what keeps a memory operand out of the lookup.
FAMILY = {
    "rax": "rax", "eax": "rax", "ax": "rax", "al": "rax", "ah": "rax",
    "rbx": "rbx", "ebx": "rbx", "bx": "rbx", "bl": "rbx", "bh": "rbx",
    "rcx": "rcx", "ecx": "rcx", "cx": "rcx", "cl": "rcx", "ch": "rcx",
    "rdx": "rdx", "edx": "rdx", "dx": "rdx", "dl": "rdx", "dh": "rdx",
    "rsi": "rsi", "esi": "rsi", "si": "rsi", "sil": "rsi",
    "rdi": "rdi", "edi": "rdi", "di": "rdi", "dil": "rdi",
    "rbp": "rbp", "ebp": "rbp", "bp": "rbp", "bpl": "rbp",
    "rsp": "rsp", "esp": "rsp", "sp": "rsp", "spl": "rsp",
}
for _n in range(8, 16):
    for _suffix, _size in (("", 8), ("d", 4), ("w", 2), ("b", 1)):
        FAMILY["r%d%s" % (_n, _suffix)] = "r%d" % _n
del _n, _suffix, _size

# Mnemonics whose first operand names the register they write. `cmp` and `test`
# are deliberately absent: they read both operands and write neither, and
# including them would make every handler's nearest "definition" one of them.
WRITES_FIRST_OPERAND = frozenset((
    "mov", "lea", "add", "sub", "and", "or", "xor", "shl", "shr", "sar",
    "imul", "inc", "dec", "not", "neg", "movzx", "movsx", "movsxd", "pop",
))


def decode_name(immediate):
    """The four characters a dword MethodName immediate spells, or None."""
    raw = int(immediate, 16).to_bytes(4, "little")
    if not all(0x20 <= b < 0x7F for b in raw):
        return None
    return raw.decode("ascii")


class Store:
    """One `mov <width> ptr [RSP + off], src`, at `va`."""

    def __init__(self, va, width, off, src):
        self.va = va
        self.width = width
        self.off = off
        self.src = src

    def covers(self, lo, hi):
        """Does this store write any byte in the half-open range [lo, hi)?"""
        return self.off < hi and lo < self.off + self.width

    def __repr__(self):
        return "Store(%#x, %s, %#x, %s)" % (self.va, self.width, self.off, self.src)


class Handler:
    """One ACPI-evaluating function, as far as the argument buffer is concerned."""

    def __init__(self, name, va):
        self.name = name
        self.va = va
        self.method = None
        self.count = None
        self.stores = []
        self.insns = []  # (va, text) in address order, for the register rule

    def slot_base(self, index):
        return ARG_BASE + ARG_STRIDE * index

    def slot_index(self, off):
        """The argument slot an offset falls in, or None if it falls outside.

        A store's offset need not be the slot's base: the handlers write their
        payloads a byte at a time at `+4`, `+5`, `+6`, `+7`, and those four
        offsets all belong to the same slot. Rounding down by the stride is
        what puts them together.
        """
        delta = off - ARG_BASE
        if delta < 0:
            return None
        return delta // ARG_STRIDE

    def later_stores(self, after_va):
        """Every store in this handler at a VA above `after_va`."""
        return [s for s in self.stores if s.va > after_va]

    def header_stores(self, index):
        """The stores at a slot's own base offset -- where its header lives."""
        base = self.slot_base(index)
        return [s for s in self.stores if s.off == base]

    def header_stores_for_all_slots(self):
        """Every store sitting exactly at some slot's base offset."""
        bases = {self.slot_base(i) for i in range(0, self.slots() + 1)}
        return [s for s in self.stores if s.off in bases]

    def slots(self):
        """The highest slot index any store lands in, or -1 if none do."""
        indices = [self.slot_index(s.off) for s in self.stores]
        indices = [i for i in indices if i is not None]
        return max(indices) if indices else -1

    def payload_stores(self, index):
        base = self.slot_base(index)
        return [s for s in self.stores if base + HEADER_BYTES <= s.off
                < base + ARG_STRIDE]

    def rewrites_header(self, index, after_va):
        """Does any store after `after_va` write the slot's four header bytes?

        This is the question the whole settlement turns on. If nothing does,
        the four bytes the constant wrote are still there when the handler
        hands the buffer to `ACPI.sys`, and the byte stores that follow land in
        the payload half of the same eight-byte slot rather than over the top
        of them.
        """
        base = self.slot_base(index)
        return any(s.covers(base, base + HEADER_BYTES)
                   for s in self.later_stores(after_va))

    def slot_value(self, index, handler_cache):
        """The dword a slot's header store writes, or None if it is not a literal.

        `handler_cache` is this handler's resolved register values, keyed by
        store VA; it is threaded in rather than recomputed per slot because the
        backward lookup is the only walk over the instruction list.
        """
        stores = self.header_stores(index)
        if not stores:
            return None
        store = stores[0]
        if store.src.startswith("0x") or store.src.startswith("-0x"):
            return int(store.src, 16) & 0xFFFFFFFF
        return handler_cache.get(store.va)

    def register_value(self, store):
        """A register-sourced store's value, when a zeroing `xor` defines it.

        The rule is one step back, not dataflow: find the nearest preceding
        instruction that writes the same register family, and accept it only if
        it is that register xored with itself. `MMWB`'s second header and the
        `ECRR`/`ECRW` pair are the cases it exists for. Anything else is None,
        which the callers render as unresolved rather than as a value.
        """
        family = FAMILY.get(store.src.lower())
        if family is None:
            return None
        for va, text in reversed(self.insns):
            if va >= store.va:
                continue
            parts = text.split()
            if not parts or parts[0] not in WRITES_FIRST_OPERAND:
                continue
            dest = FAMILY.get(parts[1].rstrip(",").lower())
            if dest != family:
                continue
            if parts[0] != "xor" or len(parts) < 3:
                return None
            if FAMILY.get(parts[2].rstrip(",").lower()) != family:
                return None
            return 0
        return None


def parse_listing(path):
    """-> [(name, va, Handler)] in listing order.

    The listing's byte column is variable width -- one two-digit group per
    instruction byte, padded with `-` to a fixed nine -- so the parse is
    "consume two-digit groups and `-`, then the rest is the instruction". That
    is only unambiguous because no mnemonic in this listing is itself two hex
    digits, which `ambiguous_mnemonics()` checks rather than assumes.
    """
    handlers = []
    current = None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            marker = MARKER.match(line)
            if marker:
                current = Handler(marker.group(1), int(marker.group(2), 16))
                handlers.append(current)
                continue
            if not line or line.startswith(";") or current is None:
                continue
            fields = line.split()
            if len(fields) < 2:
                continue
            try:
                va = int(fields[0], 16)
            except ValueError:
                continue
            index = 1
            while index < len(fields) and (fields[index] == "-"
                                           or re.fullmatch(r"[0-9a-f]{2}", fields[index])):
                index += 1
            text = " ".join(fields[index:])
            if not text:
                continue
            current.insns.append((va, text))
            # STORE deliberately does not `continue`: a `mov dword ptr
            # [RSP + 0x54], 0x44524d4d` is a store like any other, and it is
            # also the handler's MethodName. Both readings are needed, so the
            # three patterns are tried against the same line rather than
            # against each other.
            store = STORE.match(text)
            if store:
                current.stores.append(Store(va, WIDTH[store.group(1)],
                                            int(store.group(2), 16), store.group(3)))
            count = COUNT.match(text)
            if count:
                current.count = int(count.group(1), 0)
            method = METHOD.match(text)
            if method:
                name = decode_name(method.group(1))
                if name:
                    current.method = name
    return handlers


def ambiguous_mnemonics(path):
    """Mnemonics this listing's byte column could be mistaken for a byte of.

    The parse above reads the instruction by consuming byte-shaped tokens and
    stopping. If a mnemonic were two hex digits (`AD`, `DB`) the two readings
    would be indistinguishable and the stop would be in the wrong place. No
    such mnemonic is in this listing; naming the set is how a regeneration that
    introduces one fails instead of quietly misparsing.
    """
    found = set()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            fields = line.split()
            if len(fields) < 2 or not re.fullmatch(r"[0-9A-Fa-f]+", fields[0]):
                continue
            index = 1
            while index < len(fields) and (fields[index] == "-"
                                           or re.fullmatch(r"[0-9a-f]{2}", fields[index])):
                index += 1
            if index < len(fields) and re.fullmatch(r"[0-9a-f]{2}", fields[index]):
                found.add(fields[index])
    return sorted(found)


def evaluate(handler):
    """-> [(slot, header_dword_or_None, header_rewritten_after_its_own_store)].

    Only slots with a store at their own base appear: a slot the handler never
    wrote a header into is not one this tool can say anything about, and
    inventing a row for it would turn an absence into a claim.
    """
    resolved = {}
    for store in handler.stores:
        if not store.src.startswith("0x"):
            value = handler.register_value(store)
            if value is not None:
                resolved[store.va] = value
    slots = sorted({h.off for h in handler.header_stores_for_all_slots()})
    rows = []
    for off in slots:
        index = handler.slot_index(off)
        headers = handler.header_stores(index)
        rows.append((index, handler.slot_value(index, resolved),
                     handler.rewrites_header(index, headers[0].va)))
    return rows


def rows_for(path):
    """-> [{'handler', 'va', 'method', 'count', 'slot', 'header', 'stores'}]."""
    out = []
    for handler in parse_listing(path):
        if handler.method is None or handler.count is None:
            continue  # not an ACPI-evaluating handler
        for index, header, rewritten in evaluate(handler):
            out.append({
                "handler": handler.name,
                "va": handler.va,
                "method": handler.method,
                "count": handler.count,
                "slot": index,
                "header": header,
                "rewritten": rewritten,
                "stores": handler.stores,
                "handler_obj": handler,
            })
    return out


def classify(value):
    """What a resolved header dword is, as a word the table can print."""
    if value is None:
        return "unresolved"
    if value == LITERAL_4:
        return "DataLength=4"
    if value == LITERAL_BUFFER:
        return "Type=2,DataLength=0x%x" % (value >> 16)
    if value == 0:
        return "zeroed"
    return "0x%08x" % value


def reach(store, base):
    """Where in a slot a store lands, in the words the settlement turns on.

    "header + payload" is the eight-byte store at a slot's base: it writes the
    four header bytes *and* zeroes the four payload bytes above them, and the
    payload is then filled a byte at a time. That is the difference between one
    dword here and two, and it is worth naming in the output rather than
    leaving a reader to subtract `width` from `offset`.
    """
    if store.off < base:
        return "below slot"
    if store.off == base:
        if store.width == HEADER_BYTES:
            return "header only"
        if store.width < HEADER_BYTES:
            return "header partial"
        return "header + payload"
    if store.off + store.width <= base + HEADER_BYTES:
        return "header upper"
    return "payload"


def payload_span(handler, index):
    """The byte offsets a slot's payload occupies, as `0x64-0x67` or `0x64`."""
    offsets = set()
    for store in handler.payload_stores(index):
        offsets.update(range(store.off, store.off + store.width))
    if not offsets:
        return "-"
    ordered = sorted(offsets)
    runs = [[ordered[0], ordered[0]]]
    for off in ordered[1:]:
        if off == runs[-1][1] + 1:
            runs[-1][1] = off
        else:
            runs.append([off, off])
    return ",".join("0x%x" % lo if lo == hi else "0x%x-0x%x" % (lo, hi)
                    for lo, hi in runs)


def print_table(path, stream):
    rows = rows_for(path)
    print("ACPIDriver.sys ACPI argument headers, from %s"
          % os.path.relpath(path, REPO), file=stream)
    print("  each handler writes ArgumentCount at RSP+0x5c and then one dword per"
          " argument at RSP+0x%X," % ARG_BASE, file=stream)
    print("  payload from +%d, an 8-byte stride; a header dword of 0x%08X is a"
          " length of 4 at +2" % (HEADER_BYTES, LITERAL_4), file=stream)
    print("", file=stream)
    columns = ("handler", "method", "argc", "slot", "at", "header dword",
               "read back", "payload")
    print("%-16s %-6s %4s %4s %5s %-24s %-10s %s" % columns, file=stream)
    print("-" * 88, file=stream)
    seen = set()
    for row in rows:
        first = row["handler"] not in seen
        seen.add(row["handler"])
        print("%-16s %-6s %4s %4d %5s %-24s %-10s %s" % (
            row["handler"] if first else "",
            row["method"] if first else "",
            row["count"] if first else "",
            row["slot"],
            "0x%x" % (ARG_BASE + ARG_STRIDE * row["slot"]),
            classify(row["header"]),
            "REWRITTEN" if row["rewritten"] else "intact",
            payload_span(row["handler_obj"], row["slot"])), file=stream)
    return rows


def print_csv(path, stream):
    writer = csv.writer(stream)
    writer.writerow(["handler", "va", "method", "argument_count", "slot",
                     "slot_offset", "header_dword", "header_reads",
                     "payload_store_count"])
    for row in rows_for(path):
        writer.writerow([
            row["handler"], "%#x" % row["va"], row["method"], row["count"],
            row["slot"], "%#x" % (ARG_BASE + ARG_STRIDE * row["slot"]),
            "" if row["header"] is None else "%#x" % row["header"],
            "rewritten" if row["rewritten"] else "intact",
            len(row["handler_obj"].payload_stores(row["slot"])),
        ])


def self_test(path):
    """The parse and the slot arithmetic, against hand-built listings.

    The committed listing is the oracle for the conclusions, but it cannot
    exercise the branches that are *not* taken there: a slot whose header is
    rewritten after the constant is the one thing this whole tool exists to
    rule out, so nothing in the committed tree would ever produce it and a
    parse that silently returned `intact` regardless would look identical from
    the outside. These fixtures are that branch, plus the boundary cases of
    `reach()`.
    """
    failures = []

    def check(label, got, want):
        if got != want:
            failures.append("%s: got %r, want %r" % (label, got, want))

    check("MM08 is one byte", WIDTH["byte"], 1)
    check("MM16 is two", WIDTH["word"], 2)
    check("MM32 is four", WIDTH["dword"], 4)
    check("qword is eight", WIDTH["qword"], 8)
    check("MMRD's constant as a dword", LITERAL_4, 0x00040000)
    check("Type=2 buffer as a dword", LITERAL_BUFFER, 0x00800002)
    check("a method name decodes little-endian",
          decode_name("0x44524d4d"), "MMRD")
    check("a non-printable dword is not a name",
          decode_name("0x00000000"), None)

    at_slot_base = Store(0x1000, 4, ARG_BASE, "0x40000")
    check("a dword at the base is header only", reach(at_slot_base, ARG_BASE),
          "header only")
    check("an eight-byte store at the base reaches the payload",
          reach(Store(0x1000, 8, ARG_BASE, "0x40000"), ARG_BASE),
          "header + payload")
    check("a byte at base+4 is payload",
          reach(Store(0x1000, 1, ARG_BASE + 4, "AL"), ARG_BASE), "payload")
    check("a byte at base+3 is in the header",
          reach(Store(0x1000, 1, ARG_BASE + 3, "AL"), ARG_BASE), "header upper")

    # One synthetic handler with the shape every ACPI handler has: a method
    # name, an ArgumentCount, and one argument whose header store does and
    # then does not survive.
    def fixture(body):
        lines = ["; ==== FUN_test @ 1000", "1000 90                  nop"]
        lines += body
        return "\n".join(lines) + "\n"

    alive = fixture([
        "1010 c7 44 24 54 4d 52 44 00      mov      dword ptr [RSP + 0x54], 0x44524d4d",
        "1016 c7 44 24 5c 01 00 00 00      mov      dword ptr [RSP + 0x5c], 0x1",
        "101c 48 c7 44 24 60 00 00 04 00  mov      qword ptr [RSP + 0x60], 0x40000",
        "1025 88 44 24 64                  mov      byte ptr [RSP + 0x64], AL",
    ])
    overwritten = fixture([
        "1010 c7 44 24 54 4d 52 44 00      mov      dword ptr [RSP + 0x54], 0x44524d4d",
        "1016 c7 44 24 5c 01 00 00 00      mov      dword ptr [RSP + 0x5c], 0x1",
        "101c 48 c7 44 24 60 00 00 04 00  mov      qword ptr [RSP + 0x60], 0x40000",
        "1025 88 44 24 64                  mov      byte ptr [RSP + 0x64], AL",
        "1029 c7 44 24 60 00 00 00 00      mov      dword ptr [RSP + 0x60], 0x0",
    ])
    with tempfile.TemporaryDirectory() as scratch:
        keep = os.path.join(scratch, "keep.asm")
        clobber = os.path.join(scratch, "clobber.asm")
        with open(keep, "w", encoding="utf-8") as handle:
            handle.write(alive)
        with open(clobber, "w", encoding="utf-8") as handle:
            handle.write(overwritten)

        rows = rows_for(keep)
        check("the fixture yields one slot", len(rows), 1)
        if rows:
            check("the fixture's header is the constant", rows[0]["header"], LITERAL_4)
            check("an untouched header reads back intact", rows[0]["rewritten"], False)
        clobbered = rows_for(clobber)
        check("a slot clobbered afterwards is reported rewritten",
              [r["rewritten"] for r in clobbered], [True])

    if failures:
        for line in failures:
            print("FAIL " + line)
        print("self-test: %d failure(s)" % len(failures))
        return 1
    print("self-test: all assertions passed")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("asm", nargs="?", default=DEFAULT_ASM,
                        help="the committed ACPIDriver.asm listing")
    parser.add_argument("--csv", action="store_true",
                        help="one row per argument slot instead of the table")
    parser.add_argument("--handler", help="print one handler's stores in full")
    parser.add_argument("--self-test", action="store_true",
                        help="the parse and slot arithmetic, against fixtures")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test(args.asm if os.path.exists(args.asm) else DEFAULT_ASM)

    if not os.path.exists(args.asm):
        print("no such listing: %s" % args.asm, file=sys.stderr)
        return 1

    if args.handler:
        for handler in parse_listing(args.asm):
            if handler.name != args.handler:
                continue
            print("%s @ %#x  method=%s  ArgumentCount=%s"
                  % (handler.name, handler.va, handler.method, handler.count))
            for store in handler.stores:
                slot = handler.slot_index(store.off)
                if store.off < ARG_BASE or slot is None:
                    continue
                base = handler.slot_base(slot)
                print("  %#010x  %d byte(s) at RSP+%#06x  slot %d %-16s from %s"
                      % (store.va, store.width, store.off, slot,
                         reach(store, base), store.src))
            return 0
        print("no function named %s in %s" % (args.handler, args.asm), file=sys.stderr)
        return 1

    ambiguous = ambiguous_mnemonics(args.asm)
    if ambiguous:
        print("listing has mnemonics the byte column could be read as: %s"
              % ", ".join(ambiguous), file=sys.stderr)
        return 1

    if args.csv:
        print_csv(args.asm, sys.stdout)
    else:
        print_table(args.asm, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())