#!/usr/bin/env python3
r"""Hold the byte claims of `docs/findings/uniwill-variable-0x60-writers.md`.

Issue #116 asked which writer of `UniWillVariable` put offset 0x60 at 0 with
the 76 reserved bytes zeroed, and to keep "established" apart from "possible".
The answer is a table of writers and a verdict per writer, and the verdict rests
on byte claims: a struct layout, the state of the committed dumps, the shape of
their pairwise differences, and a handful of instructions in one BIOS listing.
Those are what this holds. The per-writer reasoning is prose, and this does not
rule it true -- it refuses an artifact whose bytes have stopped saying what the
write-up says they say.

It reads only committed text: `windows/decompiled/v3.1.39.0`'s `NVRAM_STRUCT.cs`
and `NvramVariable.cs`, `bios/decompiled/OemUniWillVariableDxe.asm` and `.c`,
and `evidence/uefi/*.bin`. No Ghidra, no network, no vendor binary, so a
reviewer runs it offline from a clean checkout.

**Eight rules, and the reason each is here.**

  1. **The layout is derived, never asserted.** `NVRAM_STRUCT` carries no
     `[StructLayout]`, no `[FieldOffset]` and no `Pack`, so C# lays it out
     sequentially with each scalar naturally aligned and a `byte[]` aligned to
     one. The layout is recomputed from the committed `.cs` on every run and the
     packed figure is printed beside it, because the 180-versus-178 distinction
     is the one every offset here depends on, and computing it means a field
     reorder in a later service build becomes a red run instead of a write-up
     that quietly describes the old struct.
  2. **No committed dump is a whole-struct write from a zeroed baseline.**
     `OemBoardSsid` is non-zero in every committed dump. A `GetFwVars()` that
     returned `default(NVRAM_STRUCT)`, followed by a `SetFwVars` writing that
     whole cached struct back, would leave it zero. This is the negative control
     that carries the finding rather than supporting it: it is what stops "the
     service zeroed the block" being available as a conclusion before a warm
     cache has been established.
  3. **The dumps taken either side of one change differ by one byte.** The
     pair bracketing the memory-OC switch differs at a single offset, which is
     what a read-modify-write over a warm cache produces and what a write from a
     zeroed baseline does not. The rule names the offset when a future dump
     breaks it, so a red run says which byte moved rather than only that
     something did. It is scoped to that pair rather than to every pair because
     that is what the committed dumps actually show; a broader rule would be one
     that had to be weakened to go green.
  4. **The state under test.** Offset 0x60 reads 0 and `Reserved` reads all zero
     in every committed dump. That is the observation the issue is about, so a
     dump that moves either ends the run rather than silently changing the
     subject.
  5. **The BIOS create path is conditional.** The 0xFF fill and the
     `SetVariable` both sit below the `jns` that skips them on a non-negative
     `GetVariable` status, so the initialisation runs only when the variable is
     absent. Without this rule the write-up's central claim -- that nothing in
     the tree shows the create path ran on this machine -- could drift away from
     the listing while still reading true.
  6. **The create path assigns offset 0x60, and assigns 1.** Measured, not
     typed: the buffer base is the `Data` argument of the `GetVariable` and the
     store's frame displacement is resolved against it, so the offset is
     computed. The store is 16 bits wide and also writes `ApUseFlag`; that is
     printed as an observation rather than dropped, and deliberately not counted
     as a refusal, because it is a fact about the listing rather than a shape
     these inputs are forbidden to take. What this rule cannot do is rule the
     *rest* of the tree out: the sweep that found no other writer of the field
     is a static one, so its result is "not found by this method".
  7. **The 0xFF fill is not aligned to `Reserved`.** It starts one byte before
     `Reserved` and stops one byte short of its end, so it covers `FnKeyStatus`
     plus `Reserved[0..74]` and leaves the last reserved byte to whatever the
     frame held. "0xFF in the 76 reserved bytes" is wrong in a way a reader
     cannot see, which is the whole reason to compute the extent rather than
     repeat it.
  8. **The service never assigns the field.** `MemoryOverClockSupport` is
     declared in `NVRAM_STRUCT.cs` and appears in no `case` of any `SetFwVars`
     switch, while the marshalled write is the whole struct. So the service sits
     on offset 0x60 in every write it makes and puts a value there only ever by
     carrying the one it read.

`--self-test` is what decides whether the other seven mean anything: each rule
is driven against the mutation it is meant to catch, on fixtures rather than the
committed inputs, with a negative control beside every positive, so that a green
run is not the absence of testing. A check that has quietly stopped refusing
looks exactly like a check that is working.

**What this does not check, which is as much of the point.** Nothing here
establishes which writer ran on this machine, or when. There is no hardware and
no Windows machine on this pipeline, the committed dumps are reads taken at
moments, and nothing in this file observes the EC, the BIOS or the service
running. It holds the bytes the verdict rests on. It does not make the verdict.

Usage:
    python3 tools/check_uniwill_writers.py --check
    python3 tools/check_uniwill_writers.py --self-test
"""
import argparse
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WINDOWS = os.path.join("windows", "decompiled", "v3.1.39.0", "GCUService",
                       "MyControlCenter")
DEFAULT_STRUCT = os.path.join(REPO, WINDOWS, "NVRAM_STRUCT.cs")
DEFAULT_NVRAM = os.path.join(REPO, WINDOWS, "NvramVariable.cs")
DEFAULT_BIOS_ASM = os.path.join(REPO, "bios", "decompiled",
                                "OemUniWillVariableDxe.asm")
DEFAULT_BIOS_C = os.path.join(REPO, "bios", "decompiled", "OemUniWillVariableDxe.c")
DEFAULT_EVIDENCE = os.path.join(REPO, "evidence", "uefi")

# The field issue #116 is about, and the byte array the finding turns on. Named
# because the rules are about these two; the *offsets* are not named, because
# recomputing those is rule 1.
MEMORY_OC = "MemoryOverClockSupport"
RESERVED = "Reserved"
SSID = "OemBoardSsid"

# C# scalar sizes and the alignment each carries in a default-sequential layout.
# A `byte[]` is alignment one however long it is: it is a fixed blob inside the
# struct, not a scalar with a wider type, and handing it its own length as an
# alignment is what turns 180 into 188.
SCALAR = {"byte": (1, 1), "ushort": (2, 2), "uint": (4, 4)}

FIELD = re.compile(r"public\s+(uint|ushort|byte)\s+(\w+)\s*;")
ARRAY = re.compile(r"\[MarshalAs\(UnmanagedType\.ByValArray,\s*SizeConst\s*=\s*(\d+)\)\]"
                   r"\s*\[JsonConverter\(typeof\(ByteArrayHexConverter\)\)\]"
                   r"\s*public\s+byte\[\]\s+(\w+)\s*;")

# A listing line: the address, up to fifteen byte columns (each a hex pair or a
# `-`), then the mnemonic and operands. Matched by counting the byte columns
# rather than by a fixed slice, because the padding between the last column and
# the mnemonic is not the same width on every line and a fixed slice silently
# drops instructions -- which is how a rule ends up finding nothing and passing.
# The listings spell addresses `%08X`, so the letter digits are uppercase; a
# lowercase-only class matches every all-numeric address and silently skips
# every other one, which is the same failure wearing a green run.
LISTING = re.compile(r"^([0-9A-Fa-f]{8}) ((?:(?:[0-9A-Fa-f]{2} )|(?:- )){1,15})"
                     r"\s*(\S.*)$", re.IGNORECASE)

STORE = re.compile(r"^(?:mov|or) (byte|word|dword|qword) ptr \[rbp ([^\]]+)\],"
                   r" (0x[0-9a-f]+)$")
LEA_RAX = re.compile(r"^lea rax, \[rbp ([^\]]+)\]$")
LEA_RCX = re.compile(r"^lea rcx, \[rbp ([^\]]+)\]$")
LEA_COUNT = re.compile(r"^lea r8d, \[rdx \+ (0x[0-9a-f]+)\]$")
WIDTH = {"byte": 1, "word": 2, "dword": 4, "qword": 8}

# `EFI_RUNTIME_SERVICES_TABLE` slots, spelled as the listings spell them after
# `listing_instructions` has normalised them. Read off the committed listings
# rather than quoted from the UEFI specification, because the point of the sweep
# is that nothing here is taken on trust.
GET_VARIABLE = "[rax + 0x48]"
SET_VARIABLE = "[rax + 0x58]"


def _short(path):
    """Repository-relative where that is shorter and inside the tree.

    A fixture passes a path under a temporary directory, and a `relpath` out of
    the repository comes back as a tower of `../` that names nothing.
    """
    rel = os.path.relpath(path, REPO)
    return path if rel.startswith("..") else rel


def _disp(text):
    """A frame displacement, as the listings spell them.

    The disassembler writes the displacement's own sign where the arithmetic
    put it, so a negative frame offset comes out as `[RBP + -0x19]` -- a plus
    and then a minus -- and reading that as one signed token is what turns a
    rule that resolves the create path into one that finds no stores at all.
    """
    parts = text.split()
    if len(parts) != 2 or parts[0] not in ("+", "-"):
        return None
    try:
        return int(parts[1], 16)
    except ValueError:
        return None


def _hex(value):
    return ("-0x%x" % -value) if value < 0 else ("0x%x" % value)


# --- reading the committed inputs ------------------------------------------

def parse_fields(src):
    """`[(name, size, alignment)]` in declaration order, from the `.cs`.

    Both shapes are matched over the whole struct body and the earlier match
    wins at each step, because the two regexes interleave in source order and a
    field-by-field walk that lost that order would silently misalign the layout
    from the first `byte[]` onwards.
    """
    body = src[src.index("public struct NVRAM_STRUCT"):]
    out, pos = [], 0
    while True:
        a, b = ARRAY.search(body, pos), FIELD.search(body, pos)
        cands = [(m.start(), m) for m in (a, b) if m]
        if not cands:
            return out
        _pos, m = min(cands, key=lambda t: t[0])
        if m.re is ARRAY:
            out.append((m.group(2), int(m.group(1)), 1))
        else:
            size, align = SCALAR[m.group(1)]
            out.append((m.group(2), size, align))
        pos = m.end()


def struct_layout(fields, pack=0):
    """`({name: offset}, size)` for a default-sequential or packed layout.

    `pack` is the alignment to force; 0 means each field's own. It is a
    parameter rather than a second function so the packed figure comes out of
    the same walk as the real one -- a reimplementation of the packed case is a
    second thing to get wrong, and it is the second thing that decides whether
    offset 0x60 is 0x60 or 0x5F.
    """
    offsets, off = {}, 0
    for name, size, align in fields:
        a = pack or align
        if off % a:
            off += a - off % a
        offsets[name] = off
        off += size
    if not pack:
        widest = max(align for _n, _s, align in fields)
        if off % widest:
            off += widest - off % widest
    return offsets, off


def field_at(fields, offsets, offset):
    """The field covering `offset`, with the byte's index inside it."""
    for name, size, _a in fields:
        if offsets[name] <= offset < offsets[name] + size:
            return name if offset == offsets[name] else "%s+%d" % (name, offset - offsets[name])
    return None


def listing_instructions(path):
    """`[(address, operands)]` for one `.asm` listing, in file order.

    Operands come back whitespace-collapsed and lower-cased. The listings align
    the mnemonic in a column, so `call     qword ptr [RAX + 0x48]` reaches here
    as `call qword ptr [rax + 0x48]`, and every pattern below can then be
    written against single spaces -- which is the difference between a rule
    that finds the `SetVariable` and one that reports the listing has none.
    """
    out = []
    with open(path) as f:
        for line in f:
            m = LISTING.match(line.rstrip("\n"))
            if m:
                out.append((int(m.group(1), 16),
                            " ".join(m.group(3).split()).lower()))
    return out


def create_path(asm_path=DEFAULT_BIOS_ASM):
    """What the create-if-missing routine does, measured off the listing.

    Four things, none of them typed here:

      `data_base`  the frame displacement of the `Data` argument of the
                   `GetVariable`, which is where the 180-byte block starts and
                   therefore the origin every other displacement is measured
                   against;
      `guard`      where the conditional jump on the `GetVariable` status skips
                   to, and where that jump is;
      `set_var`    the address of the `SetVariable`;
      `stores` and `fill`, the immediate stores in the routine and the 0xFF
                   fill's destination and count.

    The decompiled C cannot supply these. Ghidra names its stack locals after
    the entry frame pointer, and this routine rebuilds RBP for itself, so a
    local's name does not line up with its displacement by eye. Measuring every
    displacement against the `Data` argument sidesteps that: it needs no frame
    arithmetic at all, and it is what lets the write-up say offset 0x60 without
    trusting either the C's names or its own arithmetic.
    """
    insns = listing_instructions(asm_path)
    get_at = next((a for a, i in insns if i.startswith("call") and GET_VARIABLE in i), None)
    set_at = next((a for a, i in insns if i.startswith("call") and SET_VARIABLE in i), None)

    # One pass, because the two things being looked for sit on opposite sides
    # of the GetVariable and a loop that stopped at it would never reach the
    # guard -- which is exactly how this rule came to fire on a listing whose
    # guard is plainly there.
    data_base, guard = None, None
    for a, i in insns:
        if get_at is not None and a < get_at and i == "mov qword ptr [rsp + 0x20], rax":
            for b, j in insns:
                if b >= a:
                    break
                m = LEA_RAX.match(j)
                if m and _disp(m.group(1)) is not None:
                    data_base = _disp(m.group(1))
        if get_at is not None and a > get_at and guard is None:
            m = re.match(r"jns (0x[0-9a-f]+)$", i)
            if m:
                guard = (a, int(m.group(1), 16))

    stores = []
    for a, i in insns:
        m = STORE.match(i)
        if m and _disp(m.group(2)) is not None:
            stores.append((a, _disp(m.group(2)), int(m.group(3), 16),
                           WIDTH[m.group(1)]))

    # The 0xFF fill is found as the last call before the SetVariable that has
    # both a first-argument destination and a third-argument count materialised
    # into it. Locating it by shape rather than by the callee's name is what
    # keeps a rename in the listing from turning this rule into a silent pass.
    # The window is wide because the two arguments are set sixteen instructions
    # apart, with the whole tail of the initialiser between them.
    fill = None
    limit = set_at if set_at is not None else 1 << 62
    for idx, (a, i) in enumerate(insns):
        if not re.match(r"call 0x[0-9a-f]+$", i) or a > limit:
            continue
        dest = count = None
        dest_at = None
        for b, j in insns[max(0, idx - 24):idx]:
            d = LEA_RCX.match(j)
            if d and _disp(d.group(1)) is not None:
                dest, dest_at = _disp(d.group(1)), b
            n = LEA_COUNT.match(j)
            if n:
                count = int(n.group(1), 16)
        if dest is not None and count is not None:
            fill = (a, dest_at, dest, count)
    return {"data_base": data_base, "guard": guard, "set_var": set_at,
            "stores": stores, "fill": fill}


def writes_to(stores, base, offset):
    """Every store in `stores` whose width covers struct `offset`."""
    return [(a, disp - base, val, width) for a, disp, val, width in stores
            if disp - base <= offset < disp - base + width]


def service_switches(path=DEFAULT_NVRAM):
    """Every `case` label in the file, and whether the whole struct is written.

    Read from the switch statements rather than from a list kept here: the claim
    is that the *service* never assigns the field, and a list in this file would
    be a second place to update when the vendor's next version adds a case.
    """
    with open(path) as f:
        src = f.read()
    cases = set(re.findall(r'case "([^"]+)":', src))
    start = src.index("private static async void SetFwBufferTesting")
    whole = "Marshal.SizeOf(typeof(NVRAM_STRUCT))" in src[start:]
    return cases, whole


def dumps(evidence_dir=DEFAULT_EVIDENCE):
    """`[(name, bytes)]` for every committed variable dump, in name order."""
    out = []
    for path in sorted(glob.glob(os.path.join(evidence_dir, "*.bin"))):
        with open(path, "rb") as f:
            out.append((os.path.basename(path), f.read()))
    return out


# --- the rules --------------------------------------------------------------

def layout_problems(struct_path=DEFAULT_STRUCT):
    """Rule 1, plus the layout every other rule is measured against."""
    with open(struct_path) as f:
        src = f.read()
    name = os.path.basename(struct_path)
    problems = []
    # The absence rule comes first because it is what licenses the default
    # layout: a `[StructLayout]` or a `[FieldOffset]` anywhere would move these
    # offsets without changing a single field declaration.
    for attr in ("StructLayout", "FieldOffset", "Pack"):
        if attr in src:
            problems.append(
                "%s carries a `%s` attribute, so the default-sequential layout "
                "this tool derives is not the layout the service marshals. "
                "Every offset below and every citation of it would be wrong; "
                "resolve the attribute before reading anything else here."
                % (name, attr))

    fields = parse_fields(src)
    offsets, size = struct_layout(fields)
    _packed_offsets, packed_size = struct_layout(fields, pack=1)
    sizes = dict((n, s) for n, s, _a in fields)
    layout = {"fields": fields, "offsets": offsets, "size": size,
              "packed_size": packed_size}

    for needed in (MEMORY_OC, RESERVED):
        if needed not in offsets:
            problems.append(
                "%s declares no %s field, so the offsets this tool reports and "
                "the write-up's whole subject are about a field that is not "
                "there. A rule about a field that was renamed is a rule about "
                "nothing." % (name, needed))

    # Recorded whenever both fields resolve, even alongside the refusals above,
    # so a run that has already found a problem reports that problem instead of
    # dying on a missing key two rules later.
    if MEMORY_OC in offsets and RESERVED in offsets:
        end = offsets[RESERVED] + sizes[RESERVED]
        layout["reserved_end"] = end
        # Held back while a layout attribute is present: that attribute is what
        # invalidates these offsets, and a second refusal derived from the same
        # invalidated numbers would read as a second finding rather than as the
        # first one again.
        if end != size and not any("attribute" in p for p in problems):
            problems.append(
                "%s ends at offset 0x%X but %s ends at 0x%X. The reserved "
                "array does not reach the end of the struct, so the bytes past "
                "it are not part of the block and rule 4 would be reading "
                "outside it." % (name, size, RESERVED, end))
    return problems, layout


def dump_problems(blobs, layout):
    """Rules 2, 3 and 4, over whatever dumps are handed in."""
    problems = []
    offsets, size = layout["offsets"], layout["size"]
    if MEMORY_OC not in offsets or "reserved_end" not in layout:
        return problems
    sizes = dict((n, s) for n, s, _a in layout["fields"])
    reserved = list(range(offsets[RESERVED], layout["reserved_end"]))
    mem_oc = offsets[MEMORY_OC]
    # `.get` rather than `[]`: a struct that has lost the board-SSID field is
    # still one this function can say something useful about, and dying on the
    # lookup would replace rules 3 and 4 with a traceback.
    ssid = offsets.get(SSID)

    for name, blob in blobs:
        if len(blob) != size:
            problems.append(
                "%s is %d bytes; the derived struct is %d. Every offset below "
                "is only meaningful for a block of the derived size, so this "
                "dump is not read rather than read wrongly."
                % (name, len(blob), size))
            continue
        # rule 4: the state the finding is about
        if blob[mem_oc] != 0:
            problems.append(
                "%s reads 0x%02X at offset 0x%02X (%s). The finding is about "
                "this byte reading 0; a dump that moves it ends the run rather "
                "than silently changing the subject."
                % (name, blob[mem_oc], mem_oc, MEMORY_OC))
        lit = [i for i in reserved if blob[i] != 0]
        if lit:
            problems.append(
                "%s has %d non-zero byte(s) in %s, the first at 0x%02X. The "
                "finding rests on that region reading all zero."
                % (name, len(lit), RESERVED, lit[0]))
        # rule 2: the negative control the finding turns on
        if ssid is not None:
            value = int.from_bytes(blob[ssid:ssid + sizes[SSID]], "little")
            if value == 0:
                problems.append(
                    "%s has %s == 0. A whole-struct write from a zeroed cache "
                    "produces exactly that, so this dump no longer excludes the "
                    "writer the finding excludes."
                    % (name, SSID))

    # rule 3: the before/after pair.
    #
    # Not "every pair differs by one byte" -- that is not what the committed
    # dumps show, and a rule asserting it would be a rule that had to be
    # weakened to pass. What they show is that the pair taken either side of
    # one deliberate change, the memory-OC switch, moved a single byte: a
    # read-modify-write over a warm cache. A whole-block write from a zeroed
    # cache would have moved every byte it did not happen to set to the same
    # value it happened to set.
    before = [n for n, _b in blobs if "before" in n]
    after = [n for n, _b in blobs if "after" in n]
    if not before or not after:
        problems.append(
            "no before/after pair of dumps in the evidence directory. The "
            "single-byte claim is read off that pair; without it there is "
            "nothing here to hold it to.")
    else:
        index = dict(blobs)
        for nb in before:
            for na in after:
                a, b = index[nb], index[na]
                if len(a) != size or len(b) != size:
                    continue
                moved = [k for k in range(size) if a[k] != b[k]]
                if len(moved) == 1:
                    continue
                problems.append(
                    "%s and %s differ at %d byte(s) (%s)%s. A single byte is "
                    "what a read-modify-write over a warm cache moves; more "
                    "than one, or none at all, means a dump moved and the "
                    "write-up's reading of these has to be redone."
                    % (nb, na, len(moved),
                       ", ".join("0x%02X" % k for k in moved[:8]) or "none",
                       "" if moved else " -- the change is not in these dumps at all"))
    return problems


def create_path_problems(asm_path=DEFAULT_BIOS_ASM, layout=None, c_path=DEFAULT_BIOS_C):
    """Rules 5, 6 and 7. Returns `(refusals, observations, facts)`."""
    problems, notes = [], []
    name = os.path.basename(asm_path)
    info = create_path(asm_path)
    if layout is None or MEMORY_OC not in layout.get("offsets", {}):
        return problems, notes, info
    offsets, target = layout["offsets"], layout["offsets"][MEMORY_OC]

    # --- rule 5: the guard -------------------------------------------------
    if info["guard"] is None:
        problems.append(
            "%s has no conditional jump between the GetVariable and the "
            "SetVariable, so the initialisation is not guarded by the variable "
            "being absent and 'it runs only when the variable is missing' has "
            "no code behind it." % name)
    elif info["set_var"] is None:
        problems.append("%s has no SetVariable call." % name)
    elif info["guard"][1] <= info["set_var"]:
        problems.append(
            "%s: the conditional jump at 0x%X targets 0x%X, which is not past "
            "the SetVariable at 0x%X. The initialisation block is then not the "
            "fall-through of a failed GetVariable, and the create path is not "
            "conditional on the variable's absence."
            % (name, info["guard"][0], info["guard"][1], info["set_var"]))

    # --- rule 6: the only assignment to 0x60 ------------------------------
    if info["data_base"] is None:
        problems.append(
            "%s: the Data argument of the GetVariable could not be located, so "
            "no store in the create path resolves to a struct offset and rule 6 "
            "has checked nothing." % name)
        return problems, notes, info
    base = info["data_base"]
    touching = writes_to(info["stores"], base, target)
    if not touching:
        problems.append(
            "%s: no store in the create path reaches offset 0x%02X (%s). The "
            "write-up says this path initialises it to 1; the listing does not. "
            "Note this is about the create path alone: the sweep that found no "
            "other writer of the field is a static one, and its result is "
            "'not found by this method' rather than an absence."
            % (name, target, MEMORY_OC))
    else:
        addr, off, val, width = touching[0]
        got = (val >> (8 * (target - off))) & 0xFF
        if got != 1:
            problems.append(
                "%s: the store at 0x%X writes 0x%02X to offset 0x%02X (%s), not "
                "1. The write-up says the create path initialises it to 1."
                % (name, addr, got, target, MEMORY_OC))
        # An observation, not a refusal: the store is wider than the field, and
        # the neighbouring byte is part of what this finding is about.
        others = [(off + i, field_at(layout["fields"], offsets, off + i))
                  for i in range(width) if off + i != target]
        notes.append("the create path's store at 0x%X is %d bytes wide, so "
                     "offset 0x%02X gets 0x%02X and %s"
                     % (addr, width, target, got,
                        ", ".join("0x%02X (%s) gets 0x%02X"
                                  % (o, f or "?", (val >> (8 * (o - off))) & 0xFF)
                                  for o, f in others)))

    # --- rule 7: the fill is not aligned to Reserved -----------------------
    if info["fill"] is None:
        problems.append(
            "%s: the 0xFF fill could not be located, so the write-up's claim "
            "about which bytes it covers is unchecked." % name)
    else:
        addr, dest_at, disp, count = info["fill"]
        start, end = disp - base, disp - base + count - 1
        res_start = offsets[RESERVED]
        res_end = layout["reserved_end"] - 1
        if (start, end) == (res_start, res_end):
            problems.append(
                "%s: the fill prepared at 0x%X and issued at 0x%X covers "
                "0x%02X..0x%02X, which is exactly %s. The finding says it starts "
                "one byte early and stops one byte short of the end, which is a "
                "different claim about different bytes."
                % (name, dest_at, addr, start, end, RESERVED))
        elif end >= res_end:
            problems.append(
                "%s: the fill at 0x%X reaches 0x%02X, at or past the last "
                "reserved byte 0x%02X. A dump's reserved region would then "
                "carry no 0xFF to be distinguished from a warm cache."
                % (name, addr, end, res_end))
        notes.append("the 0xFF fill prepared at 0x%X covers 0x%02X..0x%02X "
                     "(%d bytes); %s runs 0x%02X..0x%02X"
                     % (dest_at, start, end, count, RESERVED, res_start, res_end))

    # The C is read as well, because the write-up quotes its guard too, and the
    # listing cannot show the source-level shape a reader will look for.
    if c_path and os.path.exists(c_path):
        with open(c_path) as f:
            csrc = f.read()
        fn = csrc[csrc.index("FUN_00000454"):]
        fn = fn[:fn.index("// ==== FUN_00000620")]
        if "if (lVar1 < 0)" not in fn:
            problems.append(
                "%s: FUN_00000454 no longer carries the `if (lVar1 < 0)` guard "
                "the write-up cites. Rules 5 to 7 are measured off the listing "
                "because the C's local names do not resolve against it, but the "
                "C's guard is a claim of its own."
                % os.path.basename(c_path))
    return problems, notes, info


def service_problems(nvram_path=DEFAULT_NVRAM, layout=None):
    """Rule 8. Returns `(refusals, cases)`."""
    cases, whole = service_switches(nvram_path)
    problems = []
    name = os.path.basename(nvram_path)
    if MEMORY_OC in cases:
        problems.append(
            "%s has a `case \"%s\":` arm. The service now assigns the field, so "
            "'the service never writes offset 0x60' is no longer true of this "
            "build and the verdict column has to be redone."
            % (name, MEMORY_OC))
    if not whole:
        problems.append(
            "%s: the routine that writes the block no longer marshals "
            "Marshal.SizeOf(typeof(NVRAM_STRUCT)). The whole-block claim the "
            "finding rests on is no longer visible in the file." % name)
    if layout is not None and MEMORY_OC not in layout.get("offsets", {}):
        problems.append(
            "%s declares no %s field, so the absence of a case for it is an "
            "absence of the field rather than of the assignment."
            % (name, MEMORY_OC))
    return problems, cases


def check(struct_path=DEFAULT_STRUCT, nvram_path=DEFAULT_NVRAM,
          asm_path=DEFAULT_BIOS_ASM, c_path=DEFAULT_BIOS_C,
          evidence_dir=DEFAULT_EVIDENCE):
    # An input that cannot be read is a refusal naming the file, not a
    # traceback. A checker handed a path that is not there has checked nothing,
    # and a traceback says so far less clearly than a line that names the file
    # and says which rule went unchecked.
    missing = [p for p in (struct_path, nvram_path, asm_path)
               if not os.path.exists(p)]
    if missing:
        return (["%s is not there, so the rules that read it did not run. A "
                 "check handed a tree it cannot read has checked nothing."
                 % _short(p) for p in missing],
                {"layout": {}, "blobs": [], "cases": set(), "info": {},
                 "notes": []})
    layout_problems_, layout = layout_problems(struct_path)
    problems = list(layout_problems_)
    blobs = dumps(evidence_dir)
    if not blobs:
        problems.append(
            "%s holds no *.bin dump. A run that read nothing has checked "
            "nothing, and reporting that as clean is how a check stops gating."
            % evidence_dir)
    else:
        problems += dump_problems(blobs, layout)
    more, notes, info = create_path_problems(asm_path, layout, c_path)
    problems += more
    again, cases = service_problems(nvram_path, layout)
    problems += again
    return problems, {"layout": layout, "blobs": blobs, "cases": cases,
                      "info": info, "notes": notes}


# --- the self-test ----------------------------------------------------------

def self_test():
    """Each rule against the mutation it is meant to catch."""
    tmp = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", ".check_uniwill_writers_selftest"))
    os.makedirs(tmp, exist_ok=True)
    failures = []

    def want(label, cond, detail=""):
        if not cond:
            failures.append("%s %s" % (label, detail))

    def says(problems, needle):
        return any(needle in p for p in problems)

    def write(name, text):
        path = os.path.join(tmp, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def read(path):
        with open(path) as f:
            return f.read()

    def swap(path, pattern, replacement, count=1):
        """A fixture that is the committed file with one thing changed.

        `count=0` replaces every occurrence, which is what a fixture needs when
        the text it removes appears in more than one place and only the one
        inside the routine under test matters -- replacing the first would leave
        the case testing nothing.
        """
        text = read(path)
        new, n = re.subn(pattern, replacement, text, count=count, flags=re.M)
        if count and n != count:
            raise AssertionError("the fixture pattern %r matched %d time(s), not %d"
                                 % (pattern, n, count))
        if not n:
            raise AssertionError("the fixture pattern %r matched nothing" % pattern)
        return write(os.path.basename(path) + ".fixture", new)

    # --- the committed inputs, which is the point of running this ---------
    problems, state = check()
    layout, info = state["layout"], state["info"]
    want("the committed inputs raise no refusal", not problems,
         "(%s)" % "; ".join(problems[:3]))
    want("the derived layout is 180 bytes", layout.get("size") == 180,
         "(got %s)" % layout.get("size"))
    want("the packed layout is 178 bytes", layout.get("packed_size") == 178,
         "(got %s)" % layout.get("packed_size"))
    want("%s is at offset 0x60" % MEMORY_OC,
         layout["offsets"].get(MEMORY_OC) == 0x60,
         "(got %s)" % hex(layout["offsets"].get(MEMORY_OC, -1)))
    want("the committed dumps were read", len(state["blobs"]) > 1)
    want("the create path's Data argument resolved",
         info.get("data_base") == -0x79, "(got %s)" % info.get("data_base"))
    want("the create path's 0xFF fill resolved", info.get("fill") is not None)
    want("the service does not assign the field", MEMORY_OC not in state["cases"])

    # --- rule 1 -------------------------------------------------------------
    packed = swap(DEFAULT_STRUCT, r"(public struct NVRAM_STRUCT\n\{)",
                  r"\1\n\t[System.Runtime.InteropServices.StructLayout("
                  r"System.Runtime.InteropServices.LayoutKind.Sequential, Pack = 1)]")
    want("a struct carrying a Pack attribute is refused",
         says(layout_problems(packed)[0], "carries a `Pack` attribute"),
         "(got %s)" % layout_problems(packed)[0])
    renamed = swap(DEFAULT_STRUCT, r"public byte %s;" % MEMORY_OC,
                   "public byte RENAMED_%s;" % MEMORY_OC)
    want("renaming the field under test is refused",
         says(layout_problems(renamed)[0], "declares no %s field" % MEMORY_OC),
         "(got %s)" % layout_problems(renamed)[0])
    reordered = swap(DEFAULT_STRUCT, r"public byte\[\] %s;" % RESERVED,
                     "public byte[] Reserved;\n\tpublic byte Extra;")
    want("a struct whose reserved array no longer reaches its end is refused",
         says(layout_problems(reordered)[0], "does not reach the end"),
         "(got %s)" % layout_problems(reordered)[0])
    want("the negative control: the committed struct is clean",
         not layout_problems(DEFAULT_STRUCT)[0])

    # --- rules 2, 3, 4 ------------------------------------------------------
    baseline = state["blobs"][0][1]
    zeroed = dump_problems([("zeroed.bin", bytes(layout["size"]))], layout)
    want("an all-zero dump is reported as the zeroed baseline",
         says(zeroed, "no longer excludes the writer"),
         "(got %s)" % zeroed)
    want("the negative control: a dump with a real SSID is not rule 2's problem",
         not says(dump_problems([("copy.bin", baseline)], layout), "excludes"))

    hot = bytearray(baseline)
    hot[layout["offsets"][MEMORY_OC]] = 1
    want("a dump with 0x60 non-zero is refused",
         says(dump_problems([("hot.bin", bytes(hot))], layout), "ends the run"),
         "(got %s)" % dump_problems([("hot.bin", bytes(hot))], layout))

    lit = bytearray(baseline)
    lit[layout["offsets"][RESERVED] + 3] = 0xFF
    want("a dump with a non-zero reserved byte is refused",
         says(dump_problems([("lit.bin", bytes(lit))], layout),
              "reading all zero"))

    single = bytearray(baseline)
    single[layout["offsets"]["MemoryOverClockSwitch"]] ^= 0xFF
    moved_pair = [("x-before-memoc.bin", baseline),
                  ("x-after-memoc.bin", bytes(single))]
    want("the negative control: one byte of difference is not a refusal",
         not dump_problems(moved_pair, layout),
         "(got %s)" % dump_problems(moved_pair, layout))
    two_bytes = bytearray(single)
    two_bytes[layout["offsets"]["PowerMode"]] ^= 0x01
    want("a before/after pair differing at two offsets names them",
         says(dump_problems([("y-before.bin", baseline),
                             ("y-after.bin", bytes(two_bytes))], layout),
              "differ at 2 byte(s)"))
    want("no before/after pair in the evidence is refused",
         says(dump_problems([("solo.bin", baseline)], layout),
              "no before/after pair"))

    # --- rules 5, 6, 7 ------------------------------------------------------
    guard_target = info["guard"][1]
    unguarded = swap(DEFAULT_BIOS_ASM, r"jns +0x%08x\b" % guard_target,
                     "jns      0x%08x" % (guard_target - 0x200))
    want("a create path that is not behind the guard is refused",
         says(create_path_problems(unguarded, layout)[0], "is not conditional"),
         "(got %s)" % create_path_problems(unguarded, layout)[0])
    noguard_c = swap(DEFAULT_BIOS_C, r"if \(lVar1 < 0\)", "if (lVar1 > 0)")
    want("a C without the guard the write-up cites is refused",
         says(create_path_problems(DEFAULT_BIOS_ASM, layout, noguard_c)[0],
              "no longer carries the `if (lVar1 < 0)` guard"),
         "(got %s)" % create_path_problems(DEFAULT_BIOS_ASM, layout, noguard_c)[0])
    # The store: move it off 0x60 entirely, so the field is never assigned.
    store_at = [s for s in info["stores"]
                if s[1] - info["data_base"] <= layout["offsets"][MEMORY_OC]
                < s[1] - info["data_base"] + s[3]][0]
    off60 = swap(DEFAULT_BIOS_ASM, r"\[RBP ([^\]]+)\], 0xff01",
                 r"[RBP %s], 0xff01" % _hex(store_at[1] - 1))
    want("a create path that does not assign 0x60 is refused",
         says(create_path_problems(off60, layout)[0], "no store in the create path"),
         "(got %s)" % create_path_problems(off60, layout)[0])
    notone = swap(DEFAULT_BIOS_ASM, r"(\[RBP [^\]]+\]), 0xff01", r"\1, 0xff00")
    want("a create path that assigns 0x60 something other than 1 is refused",
         says(create_path_problems(notone, layout)[0], "not 1"),
         "(got %s)" % create_path_problems(notone, layout)[0])
    # The fill: align it to Reserved, which is the claim the finding denies.
    # Scoped to the instruction address rather than to the displacement text,
    # because a displacement appears in more than one function of the module and
    # moving the wrong one is a fixture that changes nothing while still
    # looking like it changed something.
    dest_at, disp = info["fill"][1], info["fill"][2]
    aligned = swap(DEFAULT_BIOS_ASM,
                   r"^(%08X [^\[]*\[RBP )[+-] %s\]" % (dest_at, re.escape(_hex(disp))),
                   r"\g<1>+ %s]" % _hex(disp + 1))
    want("a fill aligned to Reserved is refused as the wrong claim",
         says(create_path_problems(aligned, layout)[0], "which is exactly Reserved"),
         "(got %s)" % create_path_problems(aligned, layout)[0])
    want("the negative control: the committed create path is clean",
         not create_path_problems(DEFAULT_BIOS_ASM, layout, DEFAULT_BIOS_C)[0])

    # --- rule 8 -------------------------------------------------------------
    with_case = swap(DEFAULT_NVRAM, r'case "PowerMode":',
                     'case "%s":\n\t\t\t_fwvars.%s = value;\n\t\t\tbreak;\n'
                     '\t\tcase "PowerMode":' % (MEMORY_OC, MEMORY_OC))
    want("a service that assigns the field in a switch is refused",
         says(service_problems(with_case, layout)[0], "now assigns the field"),
         "(got %s)" % service_problems(with_case, layout)[0])
    partial = swap(DEFAULT_NVRAM, r"Marshal\.SizeOf\(typeof\(NVRAM_STRUCT\)\)",
                   "array.Length", count=0)
    want("a service that no longer marshals the whole struct is refused",
         says(service_problems(partial, layout)[0], "no longer marshals"),
         "(got %s)" % service_problems(partial, layout)[0])
    want("the negative control: the committed service is clean",
         not service_problems(DEFAULT_NVRAM, layout)[0])

    for name in os.listdir(tmp):
        os.remove(os.path.join(tmp, name))
    os.rmdir(tmp)

    if failures:
        for f in failures:
            print("  FAIL  %s" % f)
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def report(problems, notes):
    for p in problems:
        print("  REFUSED  %s" % p, file=sys.stderr)
    for n in notes:
        print("  note  %s" % n)
    if problems:
        print("%d refusal(s). A refusal is a shape these inputs are not allowed "
              "to take, not an argument that the vendor stack is wrong."
              % len(problems), file=sys.stderr)
    return problems


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on any refusal; the default run prints the same "
                         "sweep and exits 0")
    ap.add_argument("--struct", default=DEFAULT_STRUCT)
    ap.add_argument("--nvram", default=DEFAULT_NVRAM)
    ap.add_argument("--asm", default=DEFAULT_BIOS_ASM)
    ap.add_argument("--bios-c", default=DEFAULT_BIOS_C)
    ap.add_argument("--evidence", default=DEFAULT_EVIDENCE)
    ap.add_argument("--self-test", action="store_true",
                    help="pin each rule against the mutation it catches")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    problems, state = check(args.struct, args.nvram, args.asm, args.bios_c,
                            args.evidence)
    layout, info = state["layout"], state["info"]
    offsets = layout.get("offsets", {})
    if MEMORY_OC in offsets:
        print("NVRAM_STRUCT: %d bytes at C# default alignment, %d packed, both "
              "computed from the committed .cs; %s at 0x%02X, %s at 0x%02X..0x%02X."
              % (layout["size"], layout["packed_size"], MEMORY_OC,
                 offsets[MEMORY_OC], RESERVED, offsets[RESERVED],
                 layout["reserved_end"] - 1))
    if info.get("guard") and info.get("set_var") is not None:
        print("create path: block base [RBP%s], SetVariable at 0x%X under a "
              "guard that skips to 0x%X."
              % (_hex(info["data_base"]), info["set_var"], info["guard"][1]))
    print("read: %s, the SetFwVars switches in %s, and the committed dumps in "
          "evidence/uefi. Which writer ran on this machine is not established "
          "here and is not decidable from committed inputs."
          % (os.path.basename(args.asm), os.path.basename(args.nvram)))
    report(problems, state["notes"])
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())