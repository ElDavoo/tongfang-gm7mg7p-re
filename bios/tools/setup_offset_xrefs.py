#!/usr/bin/env python3
r"""Which BIOS module reads a given byte of a setup variable, and what it feeds.

Input is committed text -- `bios/ghidra/load-map.csv` and the disassembly
listings under `bios/ghidra/listings/`. No ROM, no Ghidra project, no
UEFIExtract: `bios/tools/bios_extract.py` produces those listings and this
tool only reads them. `--listings` points it at a different tree, which is how
the same code reads an export taken in a scratch work directory.

    python3 bios/tools/setup_offset_xrefs.py --offset Setup:0x4F3
    python3 bios/tools/setup_offset_xrefs.py --offset Setup:0x7D7 --verbose
    python3 bios/tools/setup_offset_xrefs.py --list-offsets Setup
    python3 bios/tools/setup_offset_xrefs.py --module OemOcDxe
    python3 bios/tools/setup_offset_xrefs.py --check
    python3 bios/tools/setup_offset_xrefs.py --self-test

A setup offset does not reach code as a literal, which is why this tool exists.
A search for `0x4F3` over `bios/decompiled/*.c` turns up no `Setup[0x4F3]`
literal -- the only matches are substrings of longer constants, such as
`local_14 = 0x4f3c34b8` in `OemHddHeadParkSmm.c` -- and that is not evidence of
absence: `gRT->GetVariable` is called with a *stack buffer*,
and every later access to the byte is a displacement against that buffer's
base. In `bios/ghidra/listings/OemOcDxe/000007A8.asm` the `Setup` buffer base
is `[RBP + 0x2e0]` and the store `docs/findings.md` §8 publishes as
`Setup[0x7D7]` sits at `[RBP + 0xab7]`; `0x2e0 + 0x7d7 = 0xab7`, so the offset
is recoverable by subtraction. The listing is the layer to read, because the
listing header says where the two layers disagree this file is right.

**How a site is identified.** Three things make a `GetVariable` call site
recoverable, and all three are in the listing a few instructions above the
call:

* *Which variable* -- the GUID is built in the frame as four dword stores at
  `RDX`'s target, and `EFI_GUID` is mixed-endian, so `Setup`'s
  `EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9` reads as the immediates
  `0xec87d643, 0x4bb5eba4, 0x3e3fe5a1, 0xa90db236`.
* *How big* -- `R9` points at a frame slot holding the byte count. That bounds
  which offsets are in range, and doubles as a check on the base: an offset
  recovered against the wrong base usually falls outside the size.
* *Where* -- the data buffer is the fifth argument, `[RSP + 0x20]`, holding a
  pointer from a `lea` a few instructions earlier. Both forms occur: an
  `RBP`-relative base (`OemOcDxe/000007A8.asm`) and an `RSP`-relative one
  (`OemPowerModeDxe/00000494.asm`).

So the tool recovers `(GUID, size, base)` per site, then reads every memory
operand in that function and subtracts the base to get the offsets the
function touches. A `--offset` query prints the ones that match.

**The wide blind spot, and it is the first one to state.** The GUID recovery
above only works when the GUID is built in the frame. A plurality of sites in
this firmware instead do `lea RDX, [0x1520]` -- a static in the module's
`.data` section, named by address. A code listing carries instructions, not
the contents of `.data`, so this tool cannot read those bytes and skips the
site whole. That is the largest single limitation here and it is why every
query prints the count of sites skipped: **a negative from this tool means "no
reader among the sites whose GUID the listing carries", not "no reader in the
firmware".** Naming the static instead of its bytes would need the module
image, which is a different committed input than a listing.

That count is deliberately printed without a cause attached to it, because
the population is not one cause. Roughly half the skipped sites name a static
in `.data` and would need the module image; the rest are `RDX` values that
arrived through a register copy, an arithmetic step this tool does not model,
a frame slot holding a *pointer* to a GUID the caller passed down, or a
definition the listing never shows. `--list-skip-causes` prints the split,
and the distinction matters: only the first is a matter of committing a file.

Register-indirect bases are resolved rather than merely counted. If the
buffer pointer is copied into `RBX` and reached as `[RBX + off]`, plain base
subtraction misses it, so the tool tracks a small amount of value provenance:
a `mov` from a tracked address, an `lea` off one, and a constant `add`/`sub`
each carry a frame address through a register. What that cannot close, the
tool reports rather than hides:

* **A register the tool has lost track of.** Any access whose base register
  has no tracked frame address is counted per module, and `--verbose` prints
  the breakdown.
* **A base computed at runtime** -- an indexed operand like `[R8 + RCX*0x1]`,
  or an address assembled by arithmetic the tool does not model. These land in
  the same count as the line above.
* **Cross-function reach** -- a buffer handed to a helper, so the access is in
  a different listing. This tool reads one function at a time and cannot see
  it, and `Setup`'s own variable wrapper is exactly this shape:
  `docs/findings/setup-charge-offset-readers.md` records what is known about
  it on this board.

Both counts are printed on every query, because a negative is only as strong
as the number that bounds it.

**`Setup` is scoped separately and always will be.** It is the HII form
engine, and it calls `GetVariable` far more than any other module here. It
writes a question's value on Save by construction, through a generic path, so
a "reader" found inside it is the form engine's own store rather than a
charge-path consumer. The tool marks those rows so a reader of the table
cannot mistake one for the other. That is the single most likely way a table
like this misleads, and it is why the flag is in the output rather than in a
note nobody reads.

`--check` is a gate over committed text: it re-derives the answer
`docs/findings.md` §8 already publishes (`Setup[0x7D7]` is written from
`OemOcDxe`'s `SyncOcVariables`) from the arithmetic rather than from a
fixture written to match, and holds the known variable table to the GUIDs and
sizes the committed IFR dump and `docs/findings.md` §6 publish. Neither mode
opens the ROM or the project.
"""
import argparse
import csv
import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_LISTINGS = os.path.join(REPO, "bios", "ghidra", "listings")
DEFAULT_LOADMAP = os.path.join(REPO, "bios", "ghidra", "load-map.csv")

# --------------------------------------------------------------------------
# The variables this asks about, and where each fact comes from
# --------------------------------------------------------------------------

# `guid` is the mixed-endian EFI_GUID: Data1 and Data2 little-endian, Data3
# big-endian, Data4 raw. `size` is the store's byte count.
#
# The GUIDs and sizes are not this tool's to decide. `Setup` and `CpuSetup`
# are the `VarStore` lines at the top of the committed IFR dump, restated in
# docs/findings/ifr-charge-and-battery-options.md, which `--check` re-reads.
# `UniWillVariable` is docs/findings.md §6's, and its 180-byte struct is
# `docs/findings/uniwill-variable-0x60-writers.md`'s subject. A size alone
# does not name a store -- several share 0xB4 in this firmware -- so a site
# is only named when its GUID matches, and a size match is reported
# separately as the weaker evidence it is.
VARIABLES = {
    "Setup": {
        "guid": "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9",
        "size": 0x7D8,
    },
    "SetupVolatileData": {
        "guid": "EC87D643-EBA4-4BB5-A1E5-3F3E36B20DA9",
        "size": 0x97,
    },
    "CpuSetup": {
        "guid": "B08F97FF-E6E8-4193-A997-5E9E9B0ADB32",
        "size": 0x2BB,
    },
    "UniWillVariable": {
        "guid": "9F33F85C-13CA-4FD1-9C4A-96217722C593",
        "size": 0xB4,
    },
}

GUID_BY_SIZE = {}
for _name, _v in sorted(VARIABLES.items()):
    GUID_BY_SIZE.setdefault(_v["size"], set()).add(_name)

# The store sizes are also the IFR dump's own numbers, and `--check` holds
# this table against the committed file rather than against a constant of its
# own, so a regenerated dump that changed one is a red run here.
IFR_VARSTORES = ("Setup", "CpuSetup", "SetupVolatileData")

# The charge offsets the issue names, and the three `UniWillVariable` bytes no
# consumer has been located for. This is the tool's default query set so the
# bare run answers the question the tool exists for; `--offset` replaces it.
# The prompts are the IFR's own, from the committed dump.
CHARGE_OFFSETS = (
    ("Setup", 0x4F3),            # Charging Method, Normal/Fast
    ("Setup", 0x3D2),            # Charger participant
    ("Setup", 0x65D),            # Battery Participant
    ("CpuSetup", 0xC3),          # AC Brick Capacity
    ("UniWillVariable", 0x30),   # BatteryLimitation
    ("UniWillVariable", 0x31),   # ChargeMaximumLimit
    ("UniWillVariable", 0x32),   # ChargeMinimumLimit
)

CHARGE_NAMES = {
    ("Setup", 0x4F3): "Charging Method, Normal/Fast",
    ("Setup", 0x3D2): "Charger participant",
    ("Setup", 0x65D): "Battery Participant",
    ("CpuSetup", 0xC3): "AC Brick Capacity",
    ("UniWillVariable", 0x30): "BatteryLimitation",
    ("UniWillVariable", 0x31): "ChargeMaximumLimit",
    ("UniWillVariable", 0x32): "ChargeMinimumLimit",
}

# `Setup` is the HII form engine; see the module docstring.
FORM_ENGINE = "Setup"


def guid_to_dwords(text):
    """The four stack immediates a GUID is written as, or None.

    The inverse of `guid_from_dwords`, and used by the self-test to build a
    fixture's GUID stores from the GUID itself. A fixture that hand-writes
    four immediates is a fixture that can be wrong in the mixed-endian
    direction this code exists to get right, and would then agree with a
    broken decoder.
    """
    parts = text.split("-")
    if len(parts) != 5:
        return None
    raw = (int(parts[0], 16).to_bytes(4, "little") +
           int(parts[1], 16).to_bytes(2, "little") +
           int(parts[2], 16).to_bytes(2, "little") +
           bytes.fromhex(parts[3]) + bytes.fromhex(parts[4]))
    return [int.from_bytes(raw[i:i + 4], "little") for i in range(0, 16, 4)]


def guid_from_dwords(words):
    """The EFI_GUID four stack immediates spell, or None if they do not.

    `EFI_GUID` is mixed-endian, which is the whole reason this is not four
    hex digits concatenated: Data1 and Data2 are little-endian, Data3 is
    big-endian, and Data4 is eight raw bytes.
    """
    if len(words) != 4 or any(w is None for w in words):
        return None
    d0, d1, d2, d3 = words
    d1 &= 0xFFFFFFFF
    d2 &= 0xFFFFFFFF
    d3 &= 0xFFFFFFFF
    raw = (d0.to_bytes(4, "little") + d1.to_bytes(4, "little") +
           d2.to_bytes(4, "little") + d3.to_bytes(4, "little"))
    text = "%08X-%04X-%04X-%s-%s" % (
        int.from_bytes(raw[0:4], "little"),
        int.from_bytes(raw[4:6], "little"),
        int.from_bytes(raw[6:8], "little"),
        raw[8:10].hex().upper(),
        raw[10:16].hex().upper(),
    )
    return text


def name_for(guid, size):
    """`(name, how)` for a site, from its GUID, else from its size alone.

    A GUID plus a size is the answer. A GUID alone is nearly as good but not
    quite: `Setup` and `SetupVolatileData` share a GUID and are told apart by
    size, so a site with the right GUID and no recovered size is reported as
    both rather than silently assigned to whichever sorts first. A size match
    is the weakest of the three and says so, because several stores in this
    firmware share these sizes.
    """
    if guid:
        by_guid = sorted(n for n, v in VARIABLES.items() if v["guid"] == guid)
        if not by_guid:
            # A real GUID for a variable this tool has no entry for. Saying so
            # is the point: it is how a store missing from the table above
            # shows up rather than being read as a failed decode.
            return guid, ("a GUID this tool has no store for; the site is "
                          "recovered but not attributed")
        if size is None:
            if len(by_guid) == 1:
                return by_guid[0], "guid"
            return "/".join(by_guid), ("guid, but no size recovered and this "
                                       "GUID names more than one store")
        exact = [n for n in by_guid if VARIABLES[n]["size"] == size]
        if len(exact) == 1:
            return exact[0], "guid+size"
        if exact:
            return "/".join(exact), "guid+size, shared by %s" % ", ".join(exact)
        return "/".join(by_guid), ("guid matches %s but not the %s size"
                                   % (", ".join(by_guid), hex(size)))
    cands = GUID_BY_SIZE.get(size) if size is not None else None
    if cands and len(cands) == 1:
        return next(iter(cands)), "size only (GUID not recoverable here)"
    if cands:
        return None, "size %s is shared by %s, and the GUID is not recoverable" % (
            hex(size), ", ".join(sorted(cands)))
    return None, "unidentified"


# --------------------------------------------------------------------------
# The listing format
# --------------------------------------------------------------------------

# `000008B6 88 85 b7 0a 00 00 - - - - -      mov      byte ptr [RBP + 0xab7], AL`
# The byte column is padded with `-` where Ghidra emitted fewer than the full
# instruction, so it cannot be split on whitespace and taken by position.
# The exporter writes addresses uppercase and the byte column lowercase. Both
# cases are accepted here because this is a parser and the fixtures that pin
# it are easier to write in one case than the other.
INSN = re.compile(r"^([0-9A-Fa-f]{8})\s+((?:[0-9a-f]{2}|-)(?:\s+(?:[0-9a-f]{2}|-)){0,14})\s+"
                  r"([a-z][a-z0-9]*)\s*(.*?)\s*$")

# `[RBP + 0xab7]`, `[RSP + -0x6d]`, `[RSP + 0x20]`, `[0x000019a0]`, `[RAX]`,
# and the indexed forms this tool reports as unattributed rather than
# subtracting: `[R8 + RCX*0x1]`.
MEM = re.compile(r"^(?:(byte|word|dword|qword|xmmword|oword) ptr )?"
                 r"\[(\w+)"
                 r"(?:\s+([+-])\s+(0x[0-9a-f]+|-0x[0-9a-f]+))?"
                 r"((?:\s+[+-]\s+\w+\*0x[0-9a-f]+)*)"
                 r"\]$")

# `[0x000019a0]` names a fixed address rather than a frame slot, so it is not a
# candidate for base subtraction at all -- not an unattributed one either.
ABSOLUTE = re.compile(r"^0x[0-9a-f]+$")

GETVARIABLE_SLOT = 0x48
CALL_TABLE = re.compile(r"^qword ptr \[(\w+) \+ (0x[0-9a-f]+)\]$")

GPR = ("RAX", "RBX", "RCX", "RDX", "RSI", "RDI", "R8", "R9", "R10", "R11",
       "R12", "R13", "R14", "R15")

# Mnemonics that write their first operand and nothing else, and the ones
# that only compare. Anything not listed clobbers its destination, which is
# the conservative direction: an address this tool loses track of becomes an
# unattributed access, not a wrong offset.
NO_EFFECT = ("cmp", "test", "call", "ret", "jmp", "nop", "push", "pop",
             "int", "leave", "endbr64", "cdq", "cwde", "cdqe", "bswap")


def operand(text):
    """`(destination, source)` of one instruction's operand text."""
    if "," not in text:
        return text.strip(), ""
    dst, src = text.split(",", 1)
    return dst.strip(), src.strip()


def parse_int(tok):
    """An immediate as an int, or None when it is a register or symbol."""
    if tok is None:
        return None
    tok = tok.strip()
    neg = tok.startswith("-")
    if neg:
        tok = tok[1:]
    try:
        val = int(tok, 16) if tok.lower().startswith("0x") else None
    except ValueError:
        return None
    if val is None:
        return None
    return -val if neg else val


def parse_listing(path):
    """`(module, function name, [(addr, mnemonic, operands)])` for one file.

    The first comment line carries the module and the function's name, and the
    function name is what a reader cites, so it is worth carrying out of the
    header rather than re-deriving from the filename. The trailing `[named]`
    marker is the exporter's, not part of the name.
    """
    module = name = None
    insns = []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("; ") and module is None:
                parts = line[2:].split()
                if not parts:
                    continue
                module = parts[0]
                if len(parts) >= 4 and parts[1] == "@":
                    tail = [p for p in parts[3:] if not p.startswith("[")]
                    name = " ".join(tail) or None
                continue
            m = INSN.match(line)
            if m:
                insns.append((int(m.group(1), 16), m.group(3), m.group(4)))
    return module, name, insns


# --------------------------------------------------------------------------
# Frame tracking: enough value provenance to subtract a base, no more
# --------------------------------------------------------------------------

class Frame(object):
    """Where each tracked value lives, in one function's own frame.

    Addresses are offsets from the stack pointer as it stood at the function's
    first instruction, so `RBP` and `RSP` references are directly comparable
    and a base recovered in one form can be matched against an access in the
    other. A tracked value is an int address, or None for "known to be
    something this tool does not model".
    """

    def __init__(self):
        self.rsp = 0
        self.rbp = None
        self.reg = {}        # register -> frame address or None
        self.mem = {}        # frame address -> int, a constant written there
        self.ptr = {}        # frame address -> frame address, a pointer written there

    def addr(self, reg, disp):
        """The frame address of `[reg + disp]`, or None if untracked."""
        if reg == "RSP":
            return self.rsp + disp
        if reg == "RBP":
            return None if self.rbp is None else self.rbp + disp
        val = self.reg.get(reg, "?")
        return None if not isinstance(val, int) else val + disp

    def set_reg(self, reg, val):
        if val is None:
            self.reg[reg] = None
        else:
            self.reg[reg] = val


def step(frame, mnemonic, ops):
    """Advance the frame model over one instruction."""
    dst, src = operand(ops)
    dm = MEM.match(dst)
    sm = MEM.match(src)

    # The stack pointer moves, and a `push` also invalidates every register
    # this tool was tracking: the callee's prologue will have reused them.
    if mnemonic == "push":
        frame.rsp -= 8
        frame.reg.clear()
    elif mnemonic == "pop":
        frame.rsp += 8
        frame.reg.clear()
    elif mnemonic in ("sub", "add") and dst == "RSP":
        val = parse_int(src)
        if val is not None:
            frame.rsp += -val if mnemonic == "sub" else val
    elif mnemonic == "lea" and dst == "RSP" and sm and sm.group(2) == "RSP":
        val = parse_int(sm.group(4))
        if val is not None:
            frame.rsp += val
    if mnemonic == "lea" and dst == "RBP":
        if sm and sm.group(2) == "RSP":
            val = parse_int(sm.group(4))
            if val is not None:
                frame.rbp = frame.rsp + val
        elif src == "RSP":
            frame.rbp = frame.rsp
    elif mnemonic == "mov" and dst == "RBP" and src == "RSP":
        # The other common x64 frame idiom, and a common one in this firmware.
        # Without it `frame.rbp` stays None for the whole function, every
        # `[RBP + disp]` operand is untracked, and a GUID sitting four
        # instructions above the call is reported as unrecoverable -- which is
        # `OemGlobalNvsDxe`'s `FUN_0000057c`, whose `Setup` GUID is in the
        # listing at `0000059B`-`000005B0` and named by `00000751`.
        frame.rbp = frame.rsp

    # Register values. A `mov` from a tracked address, an `lea` off one, or a
    # constant `add`/`sub` carries a frame address; a `mov reg, reg` copies it.
    if dst in GPR:
        val = None
        if dm is not None and not dm.group(5):
            if dm.group(4) is None:
                # `[reg]` with no displacement: only tracked when the register
                # itself is tracked, which is the register-copy case.
                frame.set_reg(dst, frame.reg.get(dm.group(2)))
                val = frame.reg.get(dst)
            else:
                frame.set_reg(dst, frame.addr(dm.group(2), parse_int(dm.group(4)) or 0))
                val = frame.reg[dst]
        elif mnemonic == "lea" and sm is not None and not sm.group(5):
            if sm.group(4) is None:
                frame.set_reg(dst, frame.reg.get(sm.group(2)))
            else:
                frame.set_reg(dst, frame.addr(sm.group(2), parse_int(sm.group(4)) or 0))
        elif dm is None and src in frame.reg:
            val = frame.reg[src]
            frame.set_reg(dst, val)
        elif mnemonic in ("add", "sub"):
            base = frame.reg.get(dst)
            val = parse_int(src)
            if isinstance(base, int) and val is not None:
                frame.set_reg(dst, base + (val if mnemonic == "add" else -val))
            else:
                frame.set_reg(dst, None)
        elif mnemonic in NO_EFFECT or mnemonic == "lea":
            pass
        elif mnemonic in ("movzx", "movsx", "movsxd"):
            pass
        else:
            frame.set_reg(dst, None)

    # Frame slots. A constant written to a slot is remembered so a GUID and a
    # size can be read back out of it; a pointer written to one is remembered
    # so a base handed over as an argument can be recovered.
    if dm is not None and dm.group(4) is not None and \
            mnemonic in ("mov", "movzx", "movsx", "movsxd"):
        at = frame.addr(dm.group(2), parse_int(dm.group(4)) or 0)
        if at is not None:
            const = parse_int(src)
            if const is not None:
                frame.mem[at] = const
                frame.ptr.pop(at, None)
            elif sm is None and src in frame.reg:
                frame.ptr[at] = frame.reg[src]
                frame.mem.pop(at, None)
            else:
                frame.mem.pop(at, None)
                frame.ptr.pop(at, None)


# --------------------------------------------------------------------------
# The analysis
# --------------------------------------------------------------------------

class Site(object):
    """One `GetVariable` call site, and what the listing says about it."""

    def __init__(self, addr, table_reg, guid, size, base):
        self.module = None
        self.listing = None
        self.func = None
        self.addr = addr
        self.table_reg = table_reg
        self.guid = guid
        self.size = size
        self.base = base
        self.offsets = {}       # (offset, width) -> [(addr, is_destination)]
        self.skip_cause = None  # why the GUID is missing, if it is

    @property
    def where(self):
        return "bios/ghidra/listings/%s/%s.asm" % (self.module, self.listing)

    @property
    def cite(self):
        return "%s @ %s" % (self.func or self.listing, hex(self.addr))

    @property
    def named(self):
        return name_for(self.guid, self.size)

    def reason(self):
        """Why a site cannot be subtracted against, in the reader's terms."""
        missing = []
        if not self.guid:
            missing.append("no GUID recoverable at this site")
        if self.size is None:
            missing.append("no size argument recovered, so no bound on offsets")
        if self.base is None:
            missing.append("no data-buffer base recovered")
        return ", ".join(missing) if missing else None


def analyse(insns):
    """Every `GetVariable` site in one function, plus its buffer accesses.

    Two passes over the same instruction list. The first recovers the sites,
    because a site's GUID, size and base are only knowable at the call itself;
    the second re-walks the function with every base already known, so a
    memory operand can be attributed to the buffer whose range it lands in.
    Doing it in one pass would mean deciding at the call whether some later
    access belongs to this buffer, which is the same problem with fewer facts
    in hand.
    """
    frame = Frame()
    sites = []
    last_rdx = None
    for addr, mnemonic, ops in insns:
        if mnemonic == "call":
            m = CALL_TABLE.match(ops)
            if m and parse_int(m.group(2)) == GETVARIABLE_SLOT:
                sites.append(recover_site(addr, m.group(1), frame, last_rdx))
        dst, src = operand(ops)
        if dst == "RDX" and mnemonic not in NO_EFFECT:
            last_rdx = (mnemonic, src)
        step(frame, mnemonic, ops)

    # A site is usable for subtraction only with all three of GUID, size and
    # base. Without the size there is no bound, and an unbounded subtraction
    # places every frame access in the buffer -- which is how a tool like this
    # comes to claim readers it does not have.
    ranges = [(s.base, s.size, s) for s in sites
              if s.guid and isinstance(s.size, int) and s.base is not None
              and s.size > 0]
    unattributed = []
    if ranges:
        frame = Frame()
        for addr, mnemonic, ops in insns:
            _classify(frame, mnemonic, ops, ranges, unattributed, addr)
            step(frame, mnemonic, ops)
    return sites, unattributed


def skip_cause(frame, last_def):
    """Why this site has no GUID, in terms of what `RDX` points at.

    A skipped site is not one thing, and a count that names only the largest
    cause reads as if it named all of them. The four cases differ in what
    *else* would recover them, which is the whole question a reader of a
    negative has:

    * a **static address in `.data`** -- the GUID's bytes are in the module
      image and only the module image has them;
    * **a frame slot holding a pointer** -- the slot does not contain the GUID,
      it contains a pointer to one the caller passed down, so the GUID is in
      another function and no amount of reading *this* listing finds it;
    * **computed or copied through a register** -- the pointer went through
      arithmetic or a register copy this tool does not carry;
    * **no `RDX` definition at all** -- the value arrives set up by code the
      listing does not show.

    The second is the one most worth separating from the first: it looks like a
    frame case the method already handles, and it is not one.
    """
    at = frame.reg.get("RDX")
    if isinstance(at, int):
        return "frame slot holding a pointer"
    if last_def is None:
        return "no RDX definition in the function"
    _mnemonic, src = last_def
    m = MEM.match(src)
    if m is not None and ABSOLUTE.match(m.group(2)):
        return "static address in .data"
    return "computed or copied through a register"


def recover_site(addr, table_reg, frame, last_def=None):
    """The `(GUID, size, base)` triple for a `GetVariable` call, if recoverable.

    Each of the three is recovered separately and a site missing one is still
    returned with the others filled in. That is deliberate: a site with a GUID
    and a size but no base is still evidence that the variable is read here,
    and dropping it would lose a real observation.
    """
    guid_at = frame.reg.get("RDX")
    guid = None
    if isinstance(guid_at, int):
        guid = guid_from_dwords([frame.mem.get(guid_at + 4 * i) for i in range(4)])
    size_at = frame.reg.get("R9")
    size = frame.mem.get(size_at) if isinstance(size_at, int) else None
    # The data buffer is the fifth argument, `[RSP + 0x20]`. `frame.ptr` holds
    # what was written into that slot; the slot's own address is the stack
    # pointer *at the call*, which is what the ABI means, and `Frame.rsp` has
    # been following every push, pop and sub to get there.
    base = frame.ptr.get(frame.rsp + 0x20)
    site = Site(addr, table_reg, guid, size, base)
    if not guid:
        site.skip_cause = skip_cause(frame, last_def)
    return site


# Mnemonics whose memory operand is only ever read, and the ones that read it
# and write it back. `cmp`/`test` matter because their operand sits in the
# *destination* position -- `cmp byte ptr [RBP + 0xab7], 0x1` -- so position
# alone would record the commonest read of a setup byte as a write to it.
READ_ONLY = ("cmp", "test")
READ_MODIFY_WRITE = ("add", "sub", "adc", "sbb", "and", "or", "xor",
                     "inc", "dec", "not", "neg", "btc", "bts", "btr")


def _roles(mnemonic, dst, src):
    """`(operand text, (is_destination, ...))` for one instruction.

    A memory operand can be neither purely a source nor purely a destination:
    `or byte ptr [RBP + 0x93], 0x2` is how a firmware flips a bit in a
    variable it already holds, and calling that a read alone would lose the
    write. It is recorded as both.
    """
    if mnemonic in READ_ONLY:
        return ((dst, (False,)), (src, (False,)))
    if mnemonic in READ_MODIFY_WRITE:
        return ((dst, (False, True)), (src, (False,)))
    return ((dst, (True,)), (src, (False,)))


def _classify(frame, mnemonic, ops, ranges, unattributed, addr):
    """Attribute one instruction's memory operands to a buffer, or record why not.

    Two kinds of operand are not accesses at all, and counting them would put
    noise in the blind-spot figure and offsets in a table that should not have
    them:

    * **A `lea`.** It computes an address and reads no memory. Its operand is
      the same `[RBP + 0x2e0]` that a real access two instructions later uses,
      so treating it as a read of offset 0 puts a phantom row at the base.
    * **A `call`/`jmp` target.** `call qword ptr [RAX + 0x48]` names the
      dispatch slot in the runtime-services table, not a buffer.
    """
    if mnemonic in ("lea", "call", "jmp"):
        return
    dst, src = operand(ops)
    for text, roles in _roles(mnemonic, dst, src):
        m = MEM.match(text)
        if m is None or ABSOLUTE.match(m.group(2)):
            # A fixed address is not unattributed: a static is not a candidate
            # for base subtraction in the first place.
            continue
        if m.group(5):
            # An indexed or scaled operand, so the address is computed at
            # runtime: one of the blind spots the docstring names.
            unattributed.append((addr, text.strip()))
            continue
        at = frame.addr(m.group(2), parse_int(m.group(4)) or 0)
        if at is None:
            # A base register this tool has lost track of, which is the
            # register-indirect case the docstring names.
            unattributed.append((addr, text.strip()))
            continue
        for base, size, site in ranges:
            if base <= at < base + size:
                width = {"byte": 1, "word": 2, "dword": 4, "qword": 8}.get(
                    m.group(1), 1)
                for is_dst in roles:
                    site.offsets.setdefault((at - base, width), []).append(
                        (addr, is_dst))


def analyse_listing(path, module_hint=None):
    """`(module, func, sites, unattributed)` for one listing file."""
    module, func, insns = parse_listing(path)
    module = module or module_hint or "?"
    sites, unattributed = analyse(insns)
    for site in sites:
        site.module = module
        site.func = func
        site.listing = os.path.splitext(os.path.basename(path))[0]
    return module, func, sites, unattributed


def read_load_map(path):
    """The programs `load-map.csv` names, in file order.

    The file is iterated rather than counted: the listing tree is walked from
    it so a module with no listings is reported rather than skipped silently.
    """
    programs = []
    if not os.path.isfile(path):
        return programs
    with open(path, "r", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("program") or "").strip()
            if name:
                programs.append(name)
    return programs


def iter_listings(root, programs, module=None):
    """Yield `(module, listing path)` for each program, in load-map order."""
    for prog in programs:
        if module and prog != module:
            continue
        directory = os.path.join(root, prog)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name.endswith(".asm"):
                yield prog, os.path.join(directory, name)


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------

def collect(args):
    """Every site, and the two blind-spot counts, over the listing tree.

    Two counts and not one, because they bound a negative differently. A site
    the tool could not read a GUID for is a *narrower* search than one whose
    accesses it could not place, and conflating them would let a reader
    assume the offsets were checked inside a site that was skipped whole.
    """
    programs = read_load_map(args.loadmap)
    if args.module:
        programs = [p for p in programs if p == args.module] or [args.module]
    sites = []
    unplaced = {}
    unnamed = {}
    causes = {}
    covered = []
    for prog, path in iter_listings(args.listings, programs, args.module):
        module, _func, found, un = analyse_listing(path, prog)
        sites.extend(found)
        covered.append(module)
        if un:
            unplaced[module] = unplaced.get(module, 0) + len(un)
        skipped = sum(1 for s in found if not s.guid)
        if skipped:
            unnamed[module] = unnamed.get(module, 0) + skipped
        for site in found:
            if site.skip_cause:
                causes.setdefault(site.skip_cause, []).append(site)
    return sites, unplaced, unnamed, covered, causes


def parse_offset(text):
    """`Store:0xNNN` as `(store, offset)`."""
    if ":" not in text:
        raise ValueError("expected Store:0xNNN, got %r" % text)
    store, off = text.split(":", 1)
    store = store.strip()
    if store not in VARIABLES:
        raise ValueError("unknown store %r; this tool knows %s"
                         % (store, ", ".join(sorted(VARIABLES))))
    try:
        return store, int(off, 16)
    except ValueError:
        raise ValueError("offset must be hex, got %r" % off)


def describe_offset(store, offset):
    """The IFR's name for a charge offset, when this tool knows one."""
    return CHARGE_NAMES.get((store, offset), "")


def sites_for(sites, store):
    """The sites whose *GUID* names `store`, and only those.

    Two exclusions, both because a weaker match would put a row in the table
    that the table's own heading does not support:

    * **A size-only match.** Several stores in this firmware share a byte
      count, so a site identified by size alone is evidence that *a* variable
      of that size is read here, not which one. These are reported by
      `--module` with the weakness stated, which is where a reader can see
      them and overrule it.
    * **A site naming two stores.** `Setup` and `SetupVolatileData` share a
      GUID and differ only in size, so a site with the right GUID and no
      recovered size is left out of both rather than filed under one.
    """
    out = []
    for site in sites:
        name, how = site.named
        if name == store and not how.startswith("size only"):
            out.append(site)
    return out


def print_offset(args, store, offset, sites, unplaced, unnamed):
    """Readers of one offset, or the scoped negative if there are none."""
    label = describe_offset(store, offset)
    print("%s[0x%X]%s" % (store, offset, "  %s" % label if label else ""))
    hits = []
    for site in sites_for(sites, store):
        for (off, width), accesses in sorted(site.offsets.items()):
            if off != offset:
                continue
            for addr, is_dst in accesses:
                hits.append((site, addr, width, is_dst))
    for site, addr, width, is_dst in hits:
        kind = "writes" if is_dst else "reads"
        print("  %s %s -- %d byte(s) at %s, %s"
              % (site.where, site.cite, width, hex(addr), kind))
    if not hits:
        print("  no reader found by this method")
        if store == FORM_ENGINE:
            print("  note: %s is the HII form engine; a reader there is its own"
                  % FORM_ENGINE)
            print("  generic store path, not a charge-path consumer")
        # The reason a site was skipped belongs next to the claim that none was
        # found, not only in `--module`: a reader who stops here has to be able
        # to see what the search could not cover.
        reasons = sorted({s.reason() for s in sites if s.reason()})
        for reason in reasons:
            print("  some sites were not searched: %s" % reason)
    # The counts that bound the negative, printed on every query so a scoped
    # negative cannot be read as an unqualified one. The first is the wider
    # search: a site whose GUID the listing does not carry was skipped whole,
    # so its offsets were never checked.
    print("  method: gRT->GetVariable sites in %s, buffer base subtracted"
          % ("this module" if args.module else "every module in the load map"))
    print("  sites skipped, GUID not recoverable from this listing: %d"
          % sum(unnamed.values()))
    print("  accesses this method does not place: %d" % sum(unplaced.values()))
    if args.verbose:
        for label, counts in (("sites skipped", unnamed),
                              ("accesses not placed", unplaced)):
            for module in sorted(counts):
                print("    %s: %d (%s)" % (module, counts[module], label))
    return 0


def print_list_offsets(args, store, sites):
    """Every offset of one store this method can place, per site."""
    print("%s: offsets this method places, per GetVariable site" % store)
    for site in sites_for(sites, store):
        if not site.offsets:
            print("  %s %s -- site recovered, no access placed in the buffer"
                  % (site.where, site.cite))
            continue
        offs = []
        for (off, width), accesses in sorted(site.offsets.items()):
            tag = "w" if any(is_dst for _a, is_dst in accesses) else "r"
            offs.append("0x%X%s/%d" % (off, tag, width))
        print("  %s %s -- %s" % (site.where, site.cite, " ".join(offs)))
    return 0


def print_skip_causes(causes):
    """The skipped-site population, by what would recover each part of it.

    A skipped site is not one thing, so the total on every query is printed
    here with its breakdown rather than under one cause's name. The cases are
    ordered by what each needs next, because that is the question the count
    raises: the `.data` cases need the module image, the rest need either
    cross-function reach or arithmetic this method does not model, and only
    one of those is a matter of committing a file.
    """
    order = ("static address in .data",
             "frame slot holding a pointer",
             "computed or copied through a register",
             "no RDX definition in the function")
    ordered = list(order) + sorted(c for c in causes if c not in order)
    total = sum(len(v) for v in causes.values())
    print("sites skipped for want of a GUID, by what RDX points at: %d" % total)
    for cause in ordered:
        rows = causes.get(cause)
        if not rows:
            continue
        print("  %-40s %d" % (cause, len(rows)))
    # A module that dominates the largest bucket is where the follow-up work
    # is, so name it rather than leaving a reader to sum the listings.
    for cause in ordered:
        rows = causes.get(cause)
        if not rows:
            continue
        by_module = {}
        for site in rows:
            by_module[site.module] = by_module.get(site.module, 0) + 1
        top = sorted(by_module.items(), key=lambda kv: (-kv[1], kv[0]))
        print("  %s, by module:" % cause)
        for module, n in top:
            print("    %-32s %d" % (module, n))
    return 0


def print_module(args, sites, unplaced, unnamed, covered):
    """Every site in one module, with its named variable and its reason."""
    print("GetVariable sites in %s" % (args.module or "every module"))
    for site in sites:
        name, how = site.named
        print("  %s %s" % (site.where, site.cite))
        print("    variable: %s (%s)" % (name or "?", how))
        print("    guid: %s   size: %s   base: %s"
              % (site.guid or "not recoverable at this site",
                 hex(site.size) if site.size is not None else "not recovered",
                 hex(site.base) if site.base is not None else "not recovered"))
        bad = site.reason()
        if bad:
            print("    not usable for subtraction: %s" % bad)
        if site.offsets:
            print("    offsets placed: %s"
                  % " ".join(sorted(hex(o) for o, _w in site.offsets)))
    print("modules with listings read: %d" % len(set(covered)))
    print("sites skipped for want of a GUID in the listing: %d"
          % sum(unnamed.values()))
    print("  (the cause is mixed; --list-skip-causes breaks it down by what "
          "RDX points at)")
    print("accesses this method does not place: %d" % sum(unplaced.values()))
    return 0


def check(args, fail):
    """The gate: known answers re-derived from the committed tree.

    Two things, both properties rather than figures. `Setup[0x7D7]` resolves to
    `OemOcDxe`'s `SyncOcVariables` from the arithmetic, which is what makes
    the method trustworthy before it is turned on an offset with no published
    answer; and the size table above still matches the committed IFR dump, so
    a regenerated dump that moved one is caught here.
    """
    if not os.path.isdir(args.listings):
        fail("no listings at %s" % os.path.relpath(args.listings, REPO))
        return
    path = os.path.join(args.listings, "OemOcDxe", "000007A8.asm")
    if not os.path.isfile(path):
        fail("no %s; the Setup[0x7D7] check needs it"
             % os.path.relpath(path, REPO))
        return
    _m, func, sites, _un = analyse_listing(path, "OemOcDxe")
    hits = [s for s in sites if any(off == 0x7D7 for (off, _w) in s.offsets)]
    if not hits:
        fail("Setup[0x7D7] resolved to nothing; docs/findings.md section 8 "
             "publishes that write from OemOcDxe's SyncOcVariables")
        return
    if any(s.func != func for s in hits):
        fail("Setup[0x7D7] resolved outside %s, the listing's own function"
             % (func or "?"))

    for store in IFR_VARSTORES:
        want = VARIABLES[store]["size"]
        got = ifr_size(args, store)
        if got is None:
            continue
        if got != want:
            fail("%s is %d bytes in the committed IFR dump and %d in this "
                 "tool's table; one of the two is stale"
                 % (store, got, want))

    print("  setup-offset-xrefs: Setup[0x7D7] resolves to OemOcDxe %s; "
          "variable table matches the committed IFR dump" % (func or "?"))


def ifr_size(args, store):
    """The store's byte count from the committed IFR dump, or None."""
    path = os.path.join(REPO, "bios", "ifr", "Setup.en-US.ifr.txt")
    if not os.path.isfile(path):
        return None
    pat = re.compile(r'VarStore Guid: ([0-9A-Fa-f-]+), VarStoreId: \S+, '
                     r'Size: (0x[0-9A-Fa-f]+), Name: "%s"' % re.escape(store))
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            m = pat.search(line)
            if m:
                return int(m.group(2), 16)
    return None


def guid_stores(guid, at, start=0x110):
    """The four `mov dword` lines that build `guid` at `[RSP + at + 4*i]`.

    Generated rather than hand-written, because a fixture that spells four
    immediates out by hand can be wrong in exactly the mixed-endian direction
    `guid_from_dwords` exists to get right -- and would then agree with a
    broken decoder instead of catching one.
    """
    words = guid_to_dwords(guid)
    lines = []
    addr = start
    for i, word in enumerate(words):
        disp = at + 4 * i
        lines.append("%08x c7 44 24 %02x %02x %02x %02x %02x  mov      "
                     "dword ptr [RSP + %s], 0x%08x"
                     % (addr, disp & 0xFF,
                        word & 0xFF, (word >> 8) & 0xFF,
                        (word >> 16) & 0xFF, (word >> 24) & 0xFF,
                        ("-%#x" % -disp) if disp < 0 else ("%#x" % disp),
                        word & 0xFFFFFFFF))
        addr += 8
    return lines


def fixture_frame(prologue, tag):
    """A listing-shaped fixture on disk, and its path.

    Written to disk rather than parsed from a string so the fixtures go
    through `parse_listing` exactly as a committed listing does. A fixture
    that skipped the parser would not be testing the parser.
    """
    path = os.path.join(tempfile.gettempdir(),
                        "setup_offset_xrefs_%s.asm" % tag)
    with open(path, "w") as fh:
        fh.write("; Fixture @ 00000100   fixture_%s\n" % tag)
        fh.write("; Ghidra 12.1.3 disassembly, generated by a test -- do not edit.\n")
        fh.write("; Source: none\n")
        fh.write("; This is the machine code. The decompiled C for this address is\n")
        fh.write("; 00000100.c in the same tree; where the two disagree, this file is\n")
        fh.write("; right and the C is a reading of it.\n\n")
        for line in prologue:
            fh.write(line + "\n")
    return path


def self_test():
    """Known answers: fixtures for the shapes, the committed tree for the fact.

    The fixture half is where the parts that are easy to get subtly wrong are
    pinned, because the committed listings have no second answer to check
    against -- there is one `Setup[0x7D7]` write in this tree and no second
    reading of it. The committed half is the arithmetic `docs/findings.md` §8
    already publishes, re-derived from the base subtraction rather than
    restated, which is what makes the method worth pointing at an offset with
    no published answer.
    """
    failures = []

    def want(cond, why):
        if not cond:
            failures.append(why)

    # Every fixture below is built in the same frame, and the two constants
    # are what the expected answers are derived from rather than guessed at.
    #
    # `lea RBP, [RSP + -0x110]` with RSP still at the function's entry, then
    # `sub RSP, 0x100`, leaves RBP at -0x110 and RSP at -0x100 in this tool's
    # coordinates. A buffer based at `[RSP + 0x40]` is therefore at -0xC0, and
    # an access at `[RSP + 0x533]` is offset 0x4F3 of it -- `Setup`'s
    # `Charging Method`, so the fixture asserts on the same offset the tool is
    # pointed at by default. The displacements are derived from the two frame
    # constants rather than chosen to match a guess, which is what makes a
    # wrong answer here a wrong answer rather than a moved goalpost.
    RSP_AFTER_SUB = -0x100
    BUF_DISP = 0x40
    BASE = RSP_AFTER_SUB + BUF_DISP            # -0xC0
    READ_OFF = RSP_AFTER_SUB + 0x533 - BASE         # 0x4F3
    SECOND_OFF = RSP_AFTER_SUB + 0x534 - BASE       # 0x4F4
    WRITE_OFF = RSP_AFTER_SUB + 0x535 - BASE        # 0x4F5

    # The GUID and size slots sit at negative displacements, well below the
    # buffer, so that writing them is not itself an access into the buffer.
    GUID_AT = -0x20
    SIZE_AT = -0x10

    def prologue(guid, size, extra=(), tail=()):
        lines = [
            "00000100 48 8d ac 24 f0 ff ff - - -    lea      RBP, [RSP + -0x110]",
            "00000107 48 83 ec 00 01 00 00 - - -    sub      RSP, 0x100",
            "0000010d 48 8d 44 24 40 - - - - -    lea      RAX, [RSP + 0x40]",
            "00000112 48 89 44 24 20 - - - - -    mov      qword ptr [RSP + 0x20], RAX",
        ]
        lines.extend(extra)
        lines.append("00000150 4c 8d 4c 24 f0 - - - - -    lea      R9, [RSP + -0x10]")
        lines.append("00000155 48 c7 44 24 f0 %02x 07 00 00  mov      qword ptr "
                     "[RSP + -0x10], 0x%02x" % (SIZE_AT & 0xFF, size))
        lines.append("0000015d 48 8d 54 24 e0 - - - - -    lea      RDX, [RSP + -0x20]")
        lines.extend(guid_stores(guid, GUID_AT, start=0x160))
        lines.append("00000190 48 8b 05 b0 0f 00 00 - - -    mov      RAX, "
                     "qword ptr [0x1000]")
        lines.append("00000197 ff 50 48 - - - - - - - -      call     "
                     "qword ptr [RAX + 0x48]")
        lines.extend(tail)
        return lines

    # A GUID built in the frame, an RSP-relative base, a size argument, a read
    # and a write inside the buffer, and one indexed operand the method must
    # decline to place rather than guess at.
    lines = prologue(
        VARIABLES["Setup"]["guid"], 0x7D8,
        tail=[
            "00000199 80 bc 24 03 05 00 00 - - -    cmp      byte ptr [RSP + 0x533], 0x1",
            "000001a0 8a 84 24 04 05 00 00 - - -    mov      AL, byte ptr [RSP + 0x534]",
            "000001a7 88 84 24 05 05 00 00 - - -    mov      byte ptr [RSP + 0x535], AL",
            "000001ae 41 8a 04 08 - - - - - - -    mov      AL, byte ptr [R8 + RCX*0x1]",
        ])
    path = fixture_frame(lines, "shape")
    _m, _f, sites, un = analyse_listing(path, "Fixture")
    os.unlink(path)
    want(len(sites) == 1, "shape: one GetVariable site, got %d" % len(sites))
    if sites:
        site = sites[0]
        want(site.guid == VARIABLES["Setup"]["guid"],
             "shape: GUID %s is not Setup's" % site.guid)
        want(site.size == 0x7D8,
             "shape: size %s is not 0x7d8" % hex(site.size or 0))
        want(site.base == BASE,
             "shape: base %s, expected %s from the fixture's own frame"
             % (hex(site.base) if site.base is not None else None, hex(BASE)))
        placed = sorted((off, width) for (off, width) in site.offsets)
        want(placed == sorted([(READ_OFF, 1), (SECOND_OFF, 1), (WRITE_OFF, 1)]),
             "shape: placed %s, expected the three the fixture makes"
             % [hex(o) for o, _w in placed])
        want(any(not is_dst for _a, is_dst in site.offsets.get((READ_OFF, 1), [])),
             "shape: the compare at 0x%X was not recorded as a read" % READ_OFF)
        want(any(not is_dst for _a, is_dst in site.offsets.get((SECOND_OFF, 1), [])),
             "shape: the load at 0x%X was not recorded as a read" % SECOND_OFF)
        want(any(is_dst for _a, is_dst in site.offsets.get((WRITE_OFF, 1), [])),
             "shape: the store at 0x%X was not recorded as a write" % WRITE_OFF)
        want(site.named == ("Setup", "guid+size"),
             "shape: named %r" % (site.named,))
        want(site.reason() is None,
             "shape: a complete site reports %r as unusable" % site.reason())
    want(len(un) == 1,
         "shape: only the indexed operand should be left unplaced, got %d"
         % len(un))

    # An RBP-relative base, which is the form `OemOcDxe` uses rather than the
    # RSP-relative one above. Both occur in this firmware and a method that
    # handles only one of them is half a method.
    lines = [
        "00000200 55 - - - - - - - - -          push     RBP",
        "00000201 48 8d ac 24 40 fe ff ff - - -  lea      RBP, [RSP + -0x1c0]",
        "00000208 48 81 ec 00 02 00 00 - - - -  sub      RSP, 0x200",
    ]
    lines[1] = "00000201 48 8d ac 24 40 fe ff ff - - -  lea      RBP, [RSP + -0x1c0]"
    lines.extend(prologue.__wrapped__ if False else [])
    # The base is RBP + 0x2e0 and the access RBP + 0x2e0 + 0x4F3, which is the
    # geometry `OemOcDxe` actually uses and the one `docs/findings.md` section 8
    # publishes for 0x7D7.
    lines += [
        "00000208 48 8d 85 e0 02 00 00 - - - -  lea      RAX, [RBP + 0x2e0]",
        "0000020f 48 89 44 24 20 - - - - -    mov      qword ptr [RSP + 0x20], RAX",
        "00000214 4c 8d 8d f0 fd ff ff - - - -  lea      R9, [RBP + -0x10]",
        "0000021b 48 c7 85 f0 ff ff ff d8 07 00  mov      qword ptr [RBP + -0x10], 0x7d8",
        "00000225 48 8d 95 ec ff ff ff - - - -  lea      RDX, [RBP + -0x14]",
        "0000022c c7 85 ec ff ff ff 43 d6 87 ec  mov      dword ptr [RBP + -0x14], 0xec87d643",
        "00000236 c7 85 f0 ff ff ff a4 eb b5 4b  mov      dword ptr [RBP + -0x10], 0x4bb5eba4",
        "00000240 c7 85 f4 ff ff ff a1 e5 3f 3e  mov      dword ptr [RBP + -0x0c], 0x3e3fe5a1",
        "0000024a c7 85 f8 ff ff ff 36 b2 0d a9  mov      dword ptr [RBP + -0x08], 0xa90db236",
        "00000254 48 8b 05 b0 0f 00 00 - - -    mov      RAX, qword ptr [0x1000]",
        "0000025b ff 50 48 - - - - - - - -      call     qword ptr [RAX + 0x48]",
        "0000025e 80 bd d3 07 00 00 00 00 00 -  cmp      byte ptr [RBP + 0x7d3], 0x1",
    ]
    path = fixture_frame(lines, "rbpbase")
    _m_b, _f_b, sites_b, _un_b = analyse_listing(path, "Fixture")
    os.unlink(path)
    want(len(sites_b) == 1, "rbpbase: one site, got %d" % len(sites_b))
    if sites_b:
        placed_b = sorted(off for (off, _w) in sites_b[0].offsets)
        want(placed_b == [0x4F3],
             "rbpbase: placed %s, expected 0x4F3 from the RBP-relative base"
             % [hex(o) for o in placed_b])

    # A register-indirect base: the buffer pointer is copied into RBX and the
    # access is `[RBX + off]`. Plain base subtraction misses this shape
    # entirely; provenance carried through the register copy does not.
    lines = prologue(
        VARIABLES["UniWillVariable"]["guid"], 0xB4,
        extra=["00000149 48 89 c3 - - - - - - - -      mov      RBX, RAX"],
        tail=["00000199 80 3c 18 01 - - - - - - -    cmp      "
              "byte ptr [RBX + 0x1], 0x0"])
    path = fixture_frame(lines, "indirect")
    _m2, _f2, sites2, un2 = analyse_listing(path, "Fixture")
    os.unlink(path)
    want(len(sites2) == 1, "indirect: one site, got %d" % len(sites2))
    if sites2:
        want(sites2[0].named[0] == "UniWillVariable",
             "indirect: named %r" % (sites2[0].named[0],))
        offs = sorted(off for (off, _w) in sites2[0].offsets)
        want(offs == [1],
             "indirect: placed %s, expected the [RBX+1] access"
             % [hex(o) for o in offs])
    want(len(un2) == 0,
         "indirect: the register copy should resolve, %d left unplaced"
         % len(un2))

    # A site with no size argument must place nothing at all. Without a bound
    # the whole frame is inside "the buffer", which is how a tool like this
    # comes to claim readers it does not have.
    lines = prologue(
        VARIABLES["Setup"]["guid"], 0x7D8,
        tail=["00000199 80 bc 24 03 05 00 00 - - -    cmp      "
              "byte ptr [RSP + 0x533], 0x1"])
    lines = [ln for ln in lines if ", 0x7d8" not in ln]
    path = fixture_frame(lines, "nosize")
    _m3, _f3, sites3, _un3 = analyse_listing(path, "Fixture")
    os.unlink(path)
    want(len(sites3) == 1, "nosize: one site, got %d" % len(sites3))
    if sites3:
        want(sites3[0].size is None,
             "nosize: size should be unrecovered, got %s" % sites3[0].size)
        want(not sites3[0].offsets,
             "nosize: an offset was placed without a bound: %s"
             % [hex(o) for o, _w in sites3[0].offsets])
        want(sites3[0].reason() is not None,
             "nosize: a site with no size must say why it is unusable")

    # `Setup` and `SetupVolatileData` share a GUID and are told apart only by
    # size. A 0x97-byte read of that GUID is the volatile store, and filing it
    # under `Setup` would be a wrong answer rather than a missing one.
    lines = prologue(
        VARIABLES["SetupVolatileData"]["guid"], 0x97,
        tail=["00000199 80 bc 24 03 05 00 00 - - -    cmp      "
              "byte ptr [RSP + 0x533], 0x1"])
    path = fixture_frame(lines, "shared")
    _m4, _f4, sites4, _un4 = analyse_listing(path, "Fixture")
    os.unlink(path)
    want(bool(sites4) and sites4[0].named[0] == "SetupVolatileData",
         "shared GUID: a 0x97-byte read must name SetupVolatileData, got %r"
         % ((sites4[0].named,) if sites4 else None))
    want(bool(sites4) and not sites_for(sites4, "Setup"),
         "shared GUID: a 0x97-byte read must not also appear as Setup")
    want(name_for(VARIABLES["Setup"]["guid"], None)[0]
         == "Setup/SetupVolatileData",
         "a GUID with no size must name both stores it could be, got %r"
         % (name_for(VARIABLES["Setup"]["guid"], None),))
    want(name_for(None, 0xB4) == ("UniWillVariable",
                                 "size only (GUID not recoverable here)"),
         "a size-only site must say the evidence is size alone, got %r"
         % (name_for(None, 0xB4),))

    # GUID decoding itself, round-tripped through the encoder, against the
    # GUIDs the committed IFR dump publishes.
    want(guid_from_dwords(guid_to_dwords(VARIABLES["Setup"]["guid"]))
         == VARIABLES["Setup"]["guid"], "Setup's GUID does not round-trip")
    want(guid_from_dwords(guid_to_dwords(VARIABLES["CpuSetup"]["guid"]))
         == VARIABLES["CpuSetup"]["guid"], "CpuSetup's GUID does not round-trip")
    want(guid_from_dwords([0xec87d643, 0x4bb5eba4, 0x3e3fe5a1, 0xa90db236])
         == VARIABLES["Setup"]["guid"],
         "Setup's four immediates do not decode to its GUID")
    want(guid_from_dwords([0xb08f97ff, 0x4193e6e8, 0x9e5e97a9, 0x32db0a9b])
         == VARIABLES["CpuSetup"]["guid"],
         "CpuSetup's four immediates do not decode to its GUID")
    want(guid_from_dwords([0xec87d643, 0x4bb5eba4, None, 0xa90db236]) is None,
         "a partial GUID must decode to None, not a half-guid")

    # The committed answer: `docs/findings.md` section 8 publishes that
    # `OemOcDxe`'s `SyncOcVariables` writes `Setup[0x7D7]`, as a store at
    # `[RBP + 0xab7]` against a `[RBP + 0x2e0]` buffer. If the arithmetic is
    # right that falls out of the listing; if it is wrong, this is the case
    # that says so.
    committed = os.path.join(DEFAULT_LISTINGS, "OemOcDxe", "000007A8.asm")
    if os.path.isfile(committed):
        _m5, _f5, sites5, _un5 = analyse_listing(committed, "OemOcDxe")
        found = [s for s in sites5 if any(off == 0x7D7 for (off, _w) in s.offsets)]
        want(bool(found),
             "Setup[0x7D7] resolved to nothing in the committed listing")
        want(all(s.func == "SyncOcVariables" for s in found),
             "Setup[0x7D7] resolved outside SyncOcVariables (%s)"
             % ", ".join(sorted({s.func or "?" for s in found})))
        want(all(any(is_dst for _a, is_dst in acc)
                 for s in found for (off, _w), acc in s.offsets.items()
                 if off == 0x7D7),
             "Setup[0x7D7] was placed as a read only; the published access is "
             "a store")
    else:
        failures.append("no committed OemOcDxe/000007A8.asm to check against")

    for why in failures:
        print("  self-test: FAIL %s" % why, file=sys.stderr)
    if failures:
        return 1
    print("  self-test: fixtures hold for both base forms, the "
          "register-indirect copy, the missing size and the shared GUID; the "
          "committed Setup[0x7D7] store resolves in OemOcDxe's "
          "SyncOcVariables")
    return 0


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--listings", default=DEFAULT_LISTINGS,
                    help="the listing tree to read (default "
                         "bios/ghidra/listings)")
    ap.add_argument("--loadmap", default=DEFAULT_LOADMAP,
                    help="bios/ghidra/load-map.csv, the program list")
    ap.add_argument("--offset", metavar="STORE:0xNNN", action="append",
                    help="report readers of this offset; repeatable. Defaults "
                         "to the charge offsets")
    ap.add_argument("--list-offsets", metavar="STORE",
                    help="every offset of STORE this method places, per site")
    ap.add_argument("--module", metavar="NAME",
                    help="restrict to one module")
    ap.add_argument("--list-skip-causes", action="store_true",
                    help="break the skipped-site count down by what RDX "
                         "points at, since it is not one cause")
    ap.add_argument("--verbose", action="store_true",
                    help="print the unattributed-access breakdown per module")
    ap.add_argument("--check", action="store_true",
                    help="fail if a published answer no longer resolves; needs "
                         "neither the ROM nor Ghidra")
    ap.add_argument("--self-test", action="store_true",
                    help="known-answer assertions against fixtures and the "
                         "committed listings")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        problems = []

        def fail(msg):
            problems.append(msg)

        check(args, fail)
        if problems:
            for msg in problems:
                print("  setup-offset-xrefs: FAIL %s" % msg, file=sys.stderr)
            return 1
        return 0
    if not os.path.isdir(args.listings):
        raise SystemExit("error: no %s. Pass --listings, or regenerate with "
                         "bios/tools/bios_extract.py."
                         % os.path.relpath(args.listings, REPO))
    if args.list_offsets:
        if args.list_offsets not in VARIABLES:
            raise SystemExit("error: unknown store %r; this tool knows %s"
                             % (args.list_offsets, ", ".join(sorted(VARIABLES))))
        sites, _up, _un, _cov, _causes = collect(args)
        return print_list_offsets(args, args.list_offsets, sites)
    sites, unplaced, unnamed, covered, causes = collect(args)
    if args.list_skip_causes:
        return print_skip_causes(causes)
    if args.module:
        return print_module(args, sites, unplaced, unnamed, covered)
    queries = []
    if args.offset:
        for text in args.offset:
            try:
                queries.append(parse_offset(text))
            except ValueError as exc:
                raise SystemExit("error: %s" % exc)
    else:
        queries = list(CHARGE_OFFSETS)
    for store, offset in queries:
        print_offset(args, store, offset, sites, unplaced, unnamed)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(1)
