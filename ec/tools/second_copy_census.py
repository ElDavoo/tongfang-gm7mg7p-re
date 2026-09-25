#!/usr/bin/env python3
"""Census the exported functions that carry a name no `ghidra-functions.csv`
row wrote, and say where each of those names came from.

`build_ec_decompile.py --check` already counts the population: 25 index rows are
marked `annotated=yes` with no annotation row behind them, which is
`docs/findings.md` §18's figure. What it could not do was say *why* each one
holds a name, so the seven readable ones sat in prose with nothing to check the
count against. This tool answers that per address, from committed files only,
and fails on the ones it cannot answer.

**Three answers, and the split between them is measured rather than asserted.**

  target-of-a-transfer   the committed bytes at the address are exactly one
                         unconditional `ljmp`/`ajmp`/`lcall`/`acall`, and the
                         target is an exported function a CSV row backs under
                         *this same name*. 11 of the 25: 7 jump, 4 call. A body
                         that is nothing but a transfer of control decompiles to
                         what the transfer reaches, so the name at the stub is
                         the target's name and the target's row is committed
                         text.
  ghidra-switch-entry    the committed `.c` declares the function inside a
                         `switchD_*` namespace -- Ghidra's own switch-analysis
                         namespace, and the same `switchD_` prefix
                         `ExportDecompile.java:339` keys `isPlaceholderName()`
                         on. 14 of the 25, and this is the bucket the name
                         belongs to whatever the bytes are.
  unexplained            anything else. `--check` **fails** here, and
                         "unexplained" is a refusal: it says this method found
                         no mechanism, never that the name is automatic,
                         project-only, or absent.

**Why the two are separated by the target's name and not by the shape of the
instruction.** Measured over the 25: 23 of them begin with a single `ljmp` or
`lcall`, and 12 of those reach somewhere real -- `bank1 0x8A80`'s
`ljmp 0x8AA7` is `clear_06f9_bits_0_3_then_call_abee` -- while the name at the
site is still Ghidra's, not the target's. So "it is a jump" carries almost no
information here, and a classifier built on it would call 23 of 25 explained
while explaining none of the 12. The discriminator is the name *and* the row
behind it, and the two are tried in that order: name equality with a row-backed
target first, the switch namespace second, `unexplained` only after both have
failed.

**Where the bytes come from.** Runtime addresses are mapped to file offsets with
`trace_xdata_refs.offset_for_runtime()`, off that file's own `REGIONS` table,
rather than with a `0x08000 + addr` of the kind that reads bank 1 and the PD
image in the wrong window. It returns `None` for a target above `0x8000` seen
from the common area, which no byte resolves, and this tool reports those as
unexplained rather than reading bank 0 and calling it a result. Single
instructions are decoded with `disasm8051.decode()` -- the repository's decoder,
imported, so the opcode tables and the `ajmp` page rule have one implementation
-- and then checked against the committed `.asm` at the same address, so the
verdict and the listing a reader opens are two independent reads of one claim.

**The framing read, and its caveat.** For a transfer row the tool also reports
whether a linear walk from the bytes to the left lands *on* the address or steps
over it, via `disasm8051.converges_from()`. That function's own docstring warns
that a site nobody syncs onto is not thereby misframed -- it may be preceded by
data no linear walk can align to -- and the warning is carried into what this
prints: `covered` is "not found by this method", and
`docs/findings/named-without-a-row.md` has the per-address reading and the step
that would settle it.

**Where the frame is, relative to the committed functions.** That read is then
turned into an answer of its own -- `vector`, `mid-instruction`,
`after-a-function` or `inside-a-function` -- by looking the landing instruction
up in the committed listings. It is a partition of the eleven transfer rows
(4/1/5/1) and it is what says, per address, whether the frame begins a statement
or splits one. It says nothing about *which tool drew the frame*, and the
docstring's last paragraph is where that stays open.

**What this is not.** Nothing here was observed on hardware or in Windows; every
input is a committed file. Whether a `--mode rebuild-project` re-derives these
names is a question about Ghidra's behaviour, not something this repository can
answer from text, and the tool does not pretend to. It writes no committed file:
it reads `index.csv`, `ghidra-functions.csv`, the firmware and the committed
`.c`/`.asm`, and reports.

Usage:
    python3 second_copy_census.py
    python3 second_copy_census.py --check
    python3 second_copy_census.py --self-test
"""
import argparse
import collections
import csv
import os
import re
import sys
import tempfile

from citation_callers import iter_instructions, norm_addr
from disasm8051 import OPCODE_LEN, converges_from, decode, paged_target
from trace_xdata_refs import (PD_MARKER, offset_for_runtime, region_of,
                              runtime_addr)

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
DECOMPILED = os.path.join(EC, "decompiled")
FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
ANNOTATIONS = os.path.join(EC, "annotations", "ghidra-functions.csv")

# How far back the framing read looks. 24 is disasm8051's own default, and it
# is wide enough to hold the longest 8051 instruction several times over, so an
# address whose immediately-preceding bytes are the tail of a real instruction
# reads as that rather than as a gap.
BACK = 24

# The three verdicts, and no fourth: one outside this vocabulary is a bug in
# this file rather than a new kind of name, and `problems()` fails on it.
BUCKETS = ("target-of-a-transfer", "ghidra-switch-entry", "unexplained")

JUMP_PREFIX = ("ljmp", "ajmp")
CALL_PREFIX = ("lcall", "acall")

# The one block comment the exporter puts at the top of a `.c`, ahead of the
# definition: the annotation plate. Stripped before a declaration is read, and
# stripped again in `same_decompile()` because it is the only thing that makes a
# stub's `.c` differ from its target's.
PLATE = re.compile(r"^/\*.*?\*/", re.S)
# The declared function's name, as it stands immediately ahead of the parameter
# list. Ghidra wraps a definition at 80 columns, so the name, its namespace and
# its parameter list can be three separate lines and a line-anchored pattern
# misses every wrapped one; this reads the whitespace-collapsed text instead.
# The character class carries the colons because Ghidra writes a switch
# namespace as `switchD_CODE:8aa6::caseD_0` -- one colon before the address,
# two before the leaf -- and a pattern assuming `::` throughout silently
# truncated it to the address, which is not a name.
DECLARED = re.compile(r"([A-Za-z_][A-Za-z0-9_:]*)\s*\(")
# One slot of the `.asm` byte column: two hex digits, or the single `-`
# that pads an absent byte. `ghidra/README.md`, "The disassembly, and the
# 1:1 property", is where the layout is stated.
BYTE_SLOT = re.compile(r"[0-9A-Fa-f]{2}$")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def exporter_rules():
    """`build_ec_decompile`'s two ledger rules, imported on first use.

    Deferred rather than module-level because `build_ec_decompile.py --check`
    imports *this* module to print the verdicts, and an import in both
    directions is a cycle. Both functions are pure and read nothing but the rows
    handed to them, so the second module object a deferred import creates while
    the exporter is running as `__main__` answers identically -- which is what
    makes importing them cheaper than keeping a second copy of the ledger's own
    definition of "an index row is backed by a row".
    """
    from build_ec_decompile import annotation_ledger, index_scopes_for
    return annotation_ledger, index_scopes_for


def population(index_rows, ann_rows):
    """The index rows marked `annotated=yes` with no annotation row behind them.

    The exporter's own `annotation_ledger()`, so this is the same list
    `--check` prints rather than a second derivation of it that could differ
    from it by one row."""
    annotation_ledger, _ = exporter_rules()
    return annotation_ledger(index_rows, ann_rows)[0]


def pd_verified(fw):
    """Whether the byte at `PD_MARKER` is the marker `trace_xdata_refs` names.

    `region_of()` declines to call `0x20000`-and-later the PD image without
    being told, and the way to know is to read the marker. The offset and the
    string come from that module rather than being retyped here, so a different
    dump announcing something else at that offset is reported as `unknown`
    instead of inheriting this image's conclusion."""
    off, magic = PD_MARKER
    return fw[off:off + len(magic)] == magic


def offset_for(program, addr, fw):
    """File offset of runtime `addr` in `program`, or None if unreachable.

    `pd` is the one index `program` value that is not a `trace_xdata_refs`
    region name; the rest pass straight through. None means the bytes are not
    reachable from this program -- a target at or above `0x8000` seen from the
    common area, which no byte chooses a bank for -- and every caller below reads
    that as "this method cannot see it", never as an address with no code."""
    return offset_for_runtime(addr, "pd-image" if program == "pd" else program)


def bytes_of(fw, program, addr, count):
    """`count` firmware bytes at runtime `addr`, or None if unreachable."""
    off = offset_for(program, addr, fw)
    if off is None:
        return None
    chunk = fw[off:off + count]
    return chunk if len(chunk) == count else None


def transfer_of(fw, program, addr):
    """The single unconditional transfer at `addr`, as (raw, text, target).

    None when the bytes are unreachable or the instruction is not one of the
    four transfer forms. `decode()` is handed the runtime address so the `ajmp`
    page rule resolves to an absolute target rather than to eleven operand bits
    with no page, and the target is then computed from `raw` instead of parsed
    out of `text`: the same bytes read twice by different code is what would
    catch a wrong page rule rather than print one."""
    off = offset_for(program, addr, fw)
    if off is None:
        return None
    got = list(decode(fw, off, 1, addr))
    if not got:
        return None
    _i, raw, text = got[0]
    op = raw[0]
    if op in (0x02, 0x12):
        target = (raw[1] << 8) | raw[2]
    elif op & 0x1F in (0x01, 0x11):
        target = paged_target(op, raw[1], addr)
    else:
        return None
    return raw, text, target


def declared_name(path):
    """The name the `.c`'s definition declares, namespace and all, or None.

    Ghidra's `Function.getName()` -- the index's `name` column -- is the *leaf*
    of that, so `leaf_matches()` is the check that this read and the index are
    talking about the same function, and the namespace above the leaf is the only
    part of the name with a word in this repository's vocabulary for it."""
    if not os.path.isfile(path):
        return None
    text = "\n".join(line for line in
                     open(path, errors="replace").read().split("\n")
                     if not line.startswith("//"))
    got = DECLARED.search(re.sub(r"\s+", " ", PLATE.sub("", text, count=1)))
    return got.group(1) if got else None


def leaf_matches(declared, name):
    """Whether `declared`'s leaf is `name`, which is Ghidra's own shape: a
    namespaced function's `getName()` is the leaf and not the whole."""
    return declared is not None and declared.rsplit("::", 1)[-1] == name


def in_switch_namespace(declared):
    """The root namespace of a `switchD_*`-rooted declaration, else None.

    A prefix test on the *root* component, not a test for "carries a namespace".
    Four committed `.c` files declare a namespaced name without being in one --
    `R3(x03)` and three like it, which is Ghidra rendering a call it could not
    resolve -- and a test for `::` would file those as switch entries. `switchD_`
    is the prefix `ExportDecompile.java:339` already keys `isPlaceholderName()`
    on, so the rule is the exporter's rather than this file's."""
    if declared is None or ":" not in declared:
        return None
    root = declared.split(":")[0]
    return root if root.startswith("switchD") else None


def target_row(program, target, index):
    """The index row a transfer at `program` reaches, or None.

    The caller's own program first, then `common` for a target below `0x8000`: a
    bank caller reaching into the common area has its target exported under
    `common` where the two banks' copies are identical and under the bank name
    where they are not. A `common` caller reaching at or above `0x8000` gets
    neither, because nothing in the bytes says which bank is mapped -- which is
    `offset_for()`'s refusal reaching this function as a missing row."""
    key = norm_addr("%04X" % target)
    if (program, key) in index:
        return index[(program, key)]
    if target < 0x8000 and ("common", key) in index:
        return index[("common", key)]
    return None


def is_backed(row, ann_keys):
    """Whether a CSV row stands behind this index row.

    `index_scopes_for()`'s mapping, imported: a `common`-scoped row backs an
    address in either bank, and a `bank0`-scoped row backs a `common` row the
    de-dup renamed. Restating either here would make this a third opinion about
    which row is responsible for which function."""
    _, index_scopes_for = exporter_rules()
    addr = norm_addr(row["addr"])
    return any((scope, addr) in ann_keys
               for scope in index_scopes_for(row["program"]))


def listing_bytes(decompiled, program, addr, count=3):
    """The opening bytes of the committed listing at `addr`, or None.

    Read out of the `.asm`'s fixed three-slot byte column through
    `citation_callers.iter_instructions`, the way `census_ff_fill.py` reads it,
    so the cross-check below is two committed files produced by different Ghidra
    runs and cannot agree by construction. A short instruction yields its own
    length rather than nothing, so a one-byte `ret` listing is still checked."""
    path = os.path.join(decompiled, program, "%04X.asm" % addr)
    if not os.path.isfile(path):
        return None
    out = bytearray()
    for parts in iter_instructions(path):
        if int(parts[0], 16) != addr:
            return None                 # the listing opens somewhere else
        for slot in parts[1:4]:
            if slot == "-":
                break
            out.append(int(slot, 16))
        break
    return bytes(out) if out else None


def decode_at(fw, off):
    """The mnemonic at a file offset, decoded with that offset as its address."""
    return next(decode(fw, off, 1, off))[2]


_SPANS = {}


def row_span(decompiled, program, addr):
    """(first, last) byte addresses of the committed listing at `addr`.

    The span is a property of the listing, so it is read from the `.asm` and not
    from `index.csv`'s `size` column: `bank0 0x8054` records 21 and its listing
    runs 0x8054-0x806B, so the two disagree and only one of them is the byte
    range a reader can check an address against. Cached by full path, so the
    self-test's fixture tree and the committed tree cannot read each other's
    answers."""
    path = os.path.join(decompiled, program, "%04X.asm" % addr)
    if path in _SPANS:
        return _SPANS[path]
    first = last = None
    if os.path.isfile(path):
        for parts in iter_instructions(path):
            at = int(parts[0], 16)
            if first is None:
                first = at
            # Bounded by the three byte slots *and* by what a slot looks like: a
            # three-byte instruction has no `-` pad to stop at, so a loop that
            # only looked for one ran on into the mnemonic. `width - 1` is the
            # byte count -- the loop stops one past the last byte it accepted,
            # which is the count of what it accepted plus the one it did not.
            width = 1
            while width < 4 and parts[width] != "-" and BYTE_SLOT.match(parts[width]):
                width += 1
            last = at + width - 2
    _SPANS[path] = None if first is None else (first, last)
    return _SPANS[path]


def covering_row(decompiled, program, addr, rows_by_program):
    """The exported function whose committed listing covers runtime `addr`.

    Walks the program's rows downwards from the first one at or below `addr` and
    stops at the first whose span reaches it, so a probe costs one or two listing
    reads rather than a pass over the program. None means no committed listing
    covers the address, which is reported as such and is not the same as there
    being no code there."""
    for _first, row in reversed(rows_by_program.get(program, ())):
        if int(row["addr"], 16) > addr:
            continue
        span = row_span(decompiled, program, int(row["addr"], 16))
        if span and span[0] <= addr <= span[1]:
            return row, span
    return None


def boundary(record, decompiled, rows_by_program, fw):
    """What the frame at a transfer row is, relative to the committed functions.

    Four answers, all of them read off committed files:

      vector               the address is its own program's first byte, so
                           nothing precedes it to be a boundary inside.
      mid-instruction      no framing in the window lands on it, so under every
                           one it is interior to an instruction. This is
                           `converges_from()`'s "not found by this method" and
                           is why the tool does not claim the frame is wrong:
                           what it reports is that nothing to the left reads as
                           a complete instruction ending here.
      after-a-function     a committed function ends immediately before the
                           frame, so the frame starts the next statement rather
                           than splitting one.
      inside-a-function    the function covering the instruction that lands on
                           the frame also spans the frame, so the frame sits
                           inside a function the export already framed.

    `unframed` -- nothing committed covers the instruction that lands on the
    frame -- is the fifth answer, and the only one of the five with no instance
    among the rows whose boundary is in question. It has one among the switch
    entries the same walk runs over (`bank1 0x9AD2`), which is why it is
    reported rather than left out: a class with no case is still a class a
    reader can be handed, and naming it keeps the four above a partition rather
    than a list of the cases that have come up.

    The landing instruction arrives as a file offset, because that is what the
    framing walk counts in, and goes back to a runtime address through
    `runtime_addr()` before it is looked up in the listings -- the two are the
    same number in the common area and differ by a window everywhere else, which
    is the mistake `offset_for_runtime()` exists to stop."""
    if record["transfer"] is None:
        return None, None
    frame_verdict, start = record["framing"]["verdict"], record["framing"]["start"]
    if frame_verdict == "image-start":
        return "vector", None
    if frame_verdict == "covered":
        return "mid-instruction", None
    if frame_verdict != "entered":
        return frame_verdict, None
    at = runtime_addr(start, pd_verified(fw))
    if at is None:
        return "unframed", None
    hit = covering_row(decompiled, record["program"], at, rows_by_program)
    if hit is None:
        return "unframed", None
    row, span = hit
    where = "%s 0x%s `%s`, listed 0x%04X-0x%04X" % (
        row["program"], row["addr"], row["name"], span[0], span[1])
    frame = int(record["addr"], 16)
    if span[0] <= frame <= span[1]:
        return "inside-a-function", where
    return "after-a-function", where


def framing(fw, program, addr, back=BACK):
    """Whether a linear walk from the left lands on `addr` or steps over it.

    A dict, and three answers with no fourth:

      entered       at least one anchor in the window decodes onto the address;
                    `start` is the instruction that does it and `detail` says
                    how many anchors agree, with the number that disagree counted
                    rather than dropped, because a detail that silently reports
                    the majority is a detail that reads as unanimity.
      covered       no anchor lands on it and every one steps over it, so under
                    every framing this window offers the address is interior to
                    an instruction; `detail` is that instruction. This is
                    `converges_from()`'s "not found by this method" case and is
                    labelled as such -- a site preceded by data reads the same
                    way, and telling the two apart needs the wider read
                    docs/findings/named-without-a-row.md names.
      image-start   nothing precedes the address inside its own program: the PD
                    image's first byte, where the window to the left is erase
                    rather than code to converge from.

    The window is clipped to the region the address's own bytes fall in, because
    the bytes before a bank's `0x8000` are the common area and the bytes before
    the common area's `0x0000` are the previous image's tail."""
    off = offset_for(program, addr, fw)
    if off is None:
        return {"verdict": "unreadable", "start": None, "onto": 0, "over": 0,
                "detail": "the bytes are not reachable from this program"}
    _name, lo, _base, _how = region_of(off, pd_verified(fw))
    back = min(back, off - lo)
    if back <= 0:
        return {"verdict": "image-start", "start": None, "onto": 0, "over": 0,
                "detail": "nothing precedes the address inside its own program"}
    onto, over = converges_from(fw, off, back)
    landed = collections.Counter()
    covered = collections.Counter()
    for b in range(1, back + 1):
        i, last = off - b, None
        while i < off:
            last = i
            i += OPCODE_LEN[fw[i]]
        # The instruction's own bytes, not the window up to the address: the
        # instruction that covers the address runs *past* it, so slicing to
        # `off` would print the first byte of a two-byte `sjmp` as if the
        # opcode were the whole instruction.
        raw = fw[last:last + OPCODE_LEN[fw[last]]]
        key = (last, raw.hex(" "), decode_at(fw, last))
        (landed if i == off else covered)[key] += 1
    if landed:
        (start, raw, text), n = landed.most_common(1)[0]
        others = len(landed) - 1
        return {"verdict": "entered", "start": start, "onto": onto, "over": over,
                "detail": "%d of %d anchors land on it: `%s` (%s) at 0x%05X%s" % (
                    n, onto, text, raw, start,
                    "" if not others else
                    "; %d other instruction(s) reach it too" % others)}
    (start, raw, text), n = covered.most_common(1)[0]
    return {"verdict": "covered", "start": start, "onto": onto, "over": over,
            "detail": "%d of %d anchors step over it, so the address is inside "
            "`%s` (%s) at 0x%05X -- not found to be an instruction start by this "
            "read, which is not the same as not being one"
            % (n, over, text, raw, start)}


def verdict(fw, row, index, ann_keys, decompiled=DECOMPILED):
    """One index row as a census record.

    The two questions are asked in the order that keeps the answers apart:

    1. is the body a single transfer into a function a CSV row backs under this
       same name?
    2. failing that, does the committed `.c` put the function in a `switchD_*`
       namespace under this same leaf name?
    3. failing both, `unexplained`, with `why` naming which of the two the row
       failed. "The jump reaches 0x8AA7, which is a row, but under the name
       `clear_06f9_bits_0_3_then_call_abee`" is the fact that decides it, and a
       reader told only that *something* failed has to go and re-derive it.

    `listing` and `image` are the committed listing's opening bytes and the
    firmware's, for `problems()` to compare. Both are read for every row rather
    than only the transfers, so the staleness cross-check covers the whole
    population."""
    program, addr, name = row["program"], norm_addr(row["addr"]), row["name"]
    value = int(addr, 16)
    out = {
        "program": program,
        "addr": addr,
        "name": name,
        "seed_basis": row.get("seed_basis", "?"),
        "bucket": "unexplained",
        "why": "",
        "declared": None,
        "transfer": None,
        "target": None,
        "framing": None,
        "boundary": (None, None),
        "listing": listing_bytes(decompiled, program, value),
        "image": bytes_of(fw, program, value, 3),
    }
    got = transfer_of(fw, program, value)
    if got:
        raw, text, target = got
        out["transfer"] = {"raw": raw, "text": text, "target": target}
        out["framing"] = framing(fw, program, value)
        hit = target_row(program, target, index)
        out["target"] = hit          # printed for every transfer, matched or not
        if hit is None:
            out["why"] = ("the body is a single `%s` to 0x%04X, where no "
                          "exported function stands" % (text, target))
        elif hit["name"] != name:
            out["why"] = ("the body is a single `%s` to %s 0x%s `%s`, which is a "
                          "row but not under this name"
                          % (text, hit["program"], hit["addr"], hit["name"]))
        elif not is_backed(hit, ann_keys):
            out["why"] = ("the body is a single `%s` to %s 0x%s `%s`, which "
                          "carries that name with no CSV row behind it"
                          % (text, hit["program"], hit["addr"], hit["name"]))
        else:
            out["bucket"] = "target-of-a-transfer"
            out["why"] = ("a single `%s` into %s 0x%s, a CSV row's function of "
                          "the same name" % (text, hit["program"], hit["addr"]))
    if out["bucket"] == "unexplained":
        # `out_file` already carries the program directory, so it is joined onto
        # the tree root rather than onto `decompiled/program`.
        declared = declared_name(os.path.join(decompiled,
                                              row.get("out_file", "")))
        out["declared"] = declared
        if in_switch_namespace(declared) and leaf_matches(declared, name):
            out["bucket"] = "ghidra-switch-entry"
            out["why"] = "declared `%s`, Ghidra's own switch namespace" % declared
        elif not out["why"]:
            out["why"] = ("no CSV row behind the name, the committed .c "
                          "declares `%s` with no `switchD_` namespace, and the "
                          "body is not a single transfer" % declared)
        else:
            out["why"] += ("; the committed .c declares `%s`, with no "
                           "`switchD_` namespace" % declared)
    return out


def census(named_without_row, index_rows, ann_rows, fw=None,
           decompiled=DECOMPILED):
    """The verdicts, in the order the index carries them."""
    if fw is None:
        fw = open(FIRMWARE, "rb").read()
    index = {(r["program"], norm_addr(r["addr"])): r for r in index_rows}
    ann_keys = {(r["scope"], norm_addr(r["addr"])) for r in ann_rows}
    by_program = {}
    for row in index_rows:
        by_program.setdefault(row["program"], []).append(
            (int(norm_addr(row["addr"]), 16), row))
    # Sorted here rather than left in the index's order, because `covering_row()`
    # walks it backwards and takes the first span that reaches the address -- so
    # for a nested function, where two spans reach it, the innermost is the one
    # it has to meet. `index.csv` happens to be in this order today; a re-export
    # that is not would otherwise change the answer without changing a byte.
    for rows in by_program.values():
        rows.sort(key=lambda pair: pair[0])
    out = [verdict(fw, row, index, ann_keys, decompiled)
           for row in sorted(named_without_row,
                             key=lambda r: (r["program"], norm_addr(r["addr"])))]
    for record in out:
        record["boundary"] = boundary(record, decompiled, by_program, fw)
    return out


def problems(verdicts):
    """What `--check` refuses, in three kinds and no more.

    A row this method does not explain is a gap in the record, and a census that
    reported it as merely unusual would let the gap grow a row at a time. A
    committed listing whose opening bytes are not the firmware's is a stale
    export, which would leave every verdict above a reading of a tree that is no
    longer there. And a row with no listing to compare against is reported
    rather than skipped, because a cross-check that silently declines the rows it
    cannot check is half a check."""
    out = []
    for v in verdicts:
        if v["bucket"] == "unexplained":
            out.append("%s %s %s: no CSV row behind the name, and %s -- either the "
                       "bytes are not what this method reads, or the mechanism is "
                       "new and wants a verdict of its own"
                       % (v["program"], v["addr"], v["name"], v["why"]))
        if v["listing"] is None:
            out.append("%s %s %s: no committed listing at %s/%s.asm to confirm the "
                       "bytes against" % (v["program"], v["addr"], v["name"],
                                          v["program"], v["addr"]))
        elif v["image"] is not None and v["listing"] != v["image"][:len(v["listing"])]:
            out.append("%s %s %s: the committed listing opens with %s and the "
                       "firmware holds %s there; the export is stale, re-run it"
                       % (v["program"], v["addr"], v["name"],
                          v["listing"].hex(" "),
                          v["image"][:len(v["listing"])].hex(" ")))
    return out


def report(verdicts, found):
    """The lines `docs/findings/named-without-a-row.md` quotes."""
    out = []
    say = out.append
    say("second_copy_census.py -- index rows marked annotated=yes with no "
        "ghidra-functions.csv row behind them")
    say("")
    counts = collections.Counter(v["bucket"] for v in verdicts)
    say("  %d row(s): %s" % (len(verdicts), ", ".join(
        "%d %s" % (counts[b], b) for b in BUCKETS)))
    say("")

    say("## where each name comes from")
    say("")
    say("  program addr    name                           verdict              why")
    for v in verdicts:
        say("  %-6s %-6s %-30s %-21s %s" % (
            v["program"], v["addr"], v["name"], v["bucket"], v["why"]))
    say("")

    transfers = [v for v in verdicts if v["transfer"]]
    matched = [v for v in transfers if v["bucket"] == "target-of-a-transfer"]
    jumps = [v for v in matched if v["transfer"]["text"].startswith(JUMP_PREFIX)]
    calls = [v for v in matched if v["transfer"]["text"].startswith(CALL_PREFIX)]
    say("## the transfers, and what each one reaches")
    say("")
    say("  %d of the %d begin with a single unconditional transfer; %d reach a "
        "CSV row's function under this row's own name (%d jumps, %d calls) and "
        "%d reach somewhere real under a name that is not this row's. That "
        "second figure is why the test is the name and not the instruction."
        % (len(transfers), len(verdicts), len(matched), len(jumps), len(calls),
           len(transfers) - len(matched)))
    say("")
    say("  program addr    bytes       instruction     target   the target's row"
        "                    framing      boundary")
    for v in transfers:
        t = v["transfer"]
        hit = v["target"]
        say("  %-6s %-6s %-10s %-14s %-7s %-30s %-12s %s" % (
            v["program"], v["addr"], t["raw"].hex(" "), t["text"],
            "%04X" % t["target"],
            ("%s %s `%s`" % (hit["program"], hit["addr"], hit["name"])) if hit
            else "no exported function",
            v["framing"]["verdict"], v["boundary"][0]))
    say("")
    for v in transfers:
        say("    %-6s %-6s %-12s %s" % (v["program"], v["addr"],
                                        v["framing"]["verdict"],
                                        v["framing"]["detail"]))
    say("")

    matched = [v for v in transfers if v["bucket"] == "target-of-a-transfer"]
    say("## what the frame at each of the %d is, relative to the committed "
        "functions" % len(matched))
    say("")
    say("  program addr    boundary            the committed function it is "
        "measured against")
    for v in matched:
        say("  %-6s %-6s %-20s %s" % (v["program"], v["addr"], v["boundary"][0],
                                      v["boundary"][1] or "(nothing precedes it)"))
    say("")

    switches = [v for v in verdicts if v["bucket"] == "ghidra-switch-entry"]
    if switches:
        say("## Ghidra's switch entries")
        say("")
        say("  %d row(s), %d of them a single `ljmp` as well -- what says whose "
            "name it is is the namespace above the leaf, not the bytes."
            % (len(switches), sum(1 for v in switches if v["transfer"])))
        say("")
        for v in switches:
            say("    %-6s %-6s %-30s declared `%s`" % (
                v["program"], v["addr"], v["name"], v["declared"]))
        say("")

    say("## problems")
    say("")
    if found:
        for p in found:
            say("  FAIL  %s" % p)
    else:
        say("  none: every row is explained by a mechanism this tool reads, and "
            "every committed listing agrees with the firmware at its address")
    return "\n".join(out)


def same_decompile(stub_path, target_path):
    """Whether two `.c` files declare the same function, annotation plates aside.

    A transfer-only body decompiles to what the transfer reaches, so the stub's
    `.c` is the target's decompilation. The two *files* are not equal -- the
    target carries the plate that gives it a name, and each carries its own
    address in the header -- so comparing them whole would report a difference
    on every row and teach nothing. What is compared is what is left once each
    file's header and plate are off. None when either file is missing, which is
    "not checked" and not "they differ"."""
    def code(path):
        if not os.path.isfile(path):
            return None
        text = "\n".join(line for line in
                         open(path, errors="replace").read().split("\n")
                         if not line.startswith("//"))
        # Stripped before the plate, not after: the header is followed by a blank
        # line, `^` anchors at the start of the string, and a plate that is not
        # stripped is a difference on every row -- which would make this report
        # "they differ" for all 25 and teach nothing.
        return PLATE.sub("", text.strip(), count=1).strip()
    a, b = code(stub_path), code(target_path)
    return None if a is None or b is None else a == b


def _fixture_tree(scratch, fw):
    """A scratch decompiled tree and a patched image holding the refusal cases.

    Fixtures rather than committed rows, because every one of these is a shape
    the committed tree happens not to have, and a refusal tested against the
    tree stops being a refusal the day the tree grows a row that needs it. The
    addresses are real ones in the common area and the image is the firmware
    with a handful of bytes replaced, so the tool under test resolves them
    through `offset_for_runtime()` and `region_of()` exactly as it does the
    committed tree rather than through a path only the fixtures take."""
    decompiled = os.path.join(scratch, "decompiled")
    os.makedirs(os.path.join(decompiled, "common"))
    image = bytearray(fw[:0x8000])
    rows, named, anns = [], [], []

    def add(at, raw, listing, decl, name, backed=False, is_target=False):
        addr = "%04X" % at
        image[at:at + len(raw)] = raw
        with open(os.path.join(decompiled, "common", addr + ".asm"), "w") as f:
            f.write("; fixture\n%s\n" % listing)
        with open(os.path.join(decompiled, "common", addr + ".c"), "w") as f:
            f.write("// common @ %s   %s   [named]\n%s\n" % (addr, name, decl))
        rows.append({"program": "common", "addr": addr, "name": name,
                     "seed_basis": "call-target", "annotated": "yes",
                     "out_file": "common/%s.c" % addr})
        if not is_target:
            # The population this census classifies is the index rows with no row
            # behind them. A fixture target is in the index and annotated, so
            # putting it in the population too would ask this tool to explain a
            # function the real ledger would never hand it.
            named.append(rows[-1])
        if backed:
            anns.append({"scope": "common", "addr": addr, "name": name})

    # A stub and the row-backed function it transfers into, under one name: the
    # shape the seven readable ones have.
    add(0x0100, b"\x12\x00\x20", "0100     12 00 20 lcall    0x0020",
        "void twice(void)\n\n{\n  twice();\n}", "twice", backed=True)
    add(0x0020, b"\x22", "0020     22 - -   ret",
        "void twice(void)\n\n{\n  return;\n}", "twice", backed=True, is_target=True)
    # A transfer into a row-backed function under a *different* name, declared
    # in a switch namespace: the case the name-equality test exists to keep out
    # of the target bucket.
    add(0x0110, b"\x02\x00\x30", "0110     02 00 30 ljmp    0x0030",
        "void switchD_CODE:0030::caseD_0(void)\n\n{\n  return;\n}", "caseD_0")
    add(0x0030, b"\x22", "0030     22 - -   ret",
        "void other(void)\n\n{\n  return;\n}", "other", backed=True, is_target=True)
    # A transfer to an address no exported function stands at.
    add(0x0120, b"\x02\x00\x90", "0120     02 00 90 ljmp    0x0090",
        "void into_fill(void)\n\n{\n  return;\n}", "into_fill")
    # A transfer into a function that is exported and carries the same name but
    # has no CSV row behind it: the gap §18's other direction is about, reached
    # from this side.
    add(0x0130, b"\x02\x00\x40", "0130     02 00 40 ljmp    0x0040",
        "void project_only(void)\n\n{\n  return;\n}", "project_only")
    add(0x0040, b"\x22", "0040     22 - -   ret",
        "void project_only(void)\n\n{\n  return;\n}", "project_only", is_target=True)
    # A second copy that is not a transfer at all.
    add(0x0140, b"\x90\x34\x12", "0140     90 34 12 mov  dptr,#0x1234",
        "void not_a_stub(void)\n\n{\n  return;\n}", "not_a_stub")
    # A transfer whose target is at or above 0x8000 seen from the common area:
    # no byte says which bank, so the read declines rather than guessing one.
    add(0x0150, b"\x02\x00\x90", "0150     02 00 90 ljmp    0x9000",
        "void across_banks(void)\n\n{\n  return;\n}", "across_banks")
    return decompiled, bytes(image), rows, named, anns


def self_test() -> int:
    """Today's measured answers, and the refusals that make them worth anything.

    The known answers are the population, the three verdicts it falls into, the
    bytes and target of each of the seven readable transfers, and the framing
    read on those seven. The refusals are the half that matters: a classifier
    that had quietly degraded into "a row with a name is a target-of-a-transfer"
    would still print every known answer, so what is pinned beside them is a
    second copy that is not a transfer, a stub whose target has no row, a jump
    whose target is a row under another name, a target at or above `0x8000` seen
    from the common area, a listing that disagrees with the firmware, and a
    listing that is not there to disagree."""
    bad = 0
    print("second_copy_census.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                              "" if ok or not detail else "  " + detail))

    fw = open(FIRMWARE, "rb").read()
    index_rows = read_csv(INDEX_CSV)
    ann_rows = read_csv(ANNOTATIONS)
    named = population(index_rows, ann_rows)
    verdicts = census(named, index_rows, ann_rows, fw)
    found = problems(verdicts)
    by_key = {(v["program"], v["addr"]): v for v in verdicts}
    counts = collections.Counter(v["bucket"] for v in verdicts)

    check("the population is the 25 index rows the exporter prints", len(named) == 25,
          "got %d" % len(named))
    check("11 target a transfer, 14 are switch entries, 0 unexplained",
          (counts["target-of-a-transfer"], counts["ghidra-switch-entry"],
           counts["unexplained"]) == (11, 14, 0),
          "got %d, %d, %d" % (counts["target-of-a-transfer"],
                              counts["ghidra-switch-entry"], counts["unexplained"]))
    jumps = [v for v in verdicts if v["bucket"] == "target-of-a-transfer"
             and v["transfer"]["text"].startswith(JUMP_PREFIX)]
    calls = [v for v in verdicts if v["bucket"] == "target-of-a-transfer"
             and v["transfer"]["text"].startswith(CALL_PREFIX)]
    check("7 of the 11 matched transfers are jumps and 4 are calls",
          (len(jumps), len(calls)) == (7, 4),
          "got %d and %d" % (len(jumps), len(calls)))
    check("23 of the 25 are a single transfer, and 12 of those carry a name "
          "that is not the target's",
          sum(1 for v in verdicts if v["transfer"]) == 23
          and sum(1 for v in verdicts if v["transfer"]
                  and v["bucket"] != "target-of-a-transfer") == 12,
          "got %d and %d" % (sum(1 for v in verdicts if v["transfer"]),
                             sum(1 for v in verdicts if v["transfer"]
                                 and v["bucket"] != "target-of-a-transfer")))
    check("no row is unexplained and --check reports no problem", not found,
          "; ".join(found[:3]))

    # The seven readable ones, each read out of the committed listing: bytes,
    # instruction, target, the target's committed row, and the decompilation.
    want = {
        ("bank0", "031C"): ("02 d2 36", "ljmp 0xd236", "D236"),
        ("bank0", "805B"): ("02 82 74", "ljmp 0x8274", "8274"),
        ("bank1", "031C"): ("02 d2 36", "ljmp 0xd236", "D236"),
        ("bank1", "703A"): ("02 e7 22", "ljmp 0xe722", "E722"),
        ("common", "0512"): ("01 03", "ajmp 0x0003", "0003"),
        ("common", "1207"): ("02 11 00", "ljmp 0x1100", "1100"),
        ("pd", "0000"): ("02 05 00", "ljmp 0x0500", "0500"),
    }
    for key, (raw, text, target) in sorted(want.items()):
        v = by_key[key]
        got = v["transfer"]
        check("%s %s is `%s` into %s, a CSV row's function of the same name"
              % (key[0], key[1], raw, text),
              got is not None and got["raw"].hex() == raw.replace(" ", "")
              and got["text"] == text and "%04X" % got["target"] == target
              and v["bucket"] == "target-of-a-transfer"
              and v["target"]["name"] == v["name"],
              "got %r, %s" % (got, v["bucket"]))
        check("  ... and the committed listing opens with those bytes",
              v["listing"] is not None and v["listing"].hex(" ") == raw,
              "got " + (v["listing"].hex(" ") if v["listing"] else "no listing"))
        check("  ... and its .c is the target's decompilation, plate aside",
              same_decompile(os.path.join(DECOMPILED, key[0], key[1] + ".c"),
                             os.path.join(DECOMPILED, v["target"]["program"],
                                          v["target"]["addr"] + ".c")) is True)
    check("the four pd call sites all reach pd 0x10BC `add_full_product_to_dptr`",
          sorted(v["program"] + " " + v["addr"] for v in calls) == ["pd 3497",
                                                                   "pd 998B",
                                                                   "pd 9C1B",
                                                                   "pd 9C4D"]
          and {("%04X" % v["transfer"]["target"]) for v in calls} == {"10BC"},
          "got " + repr([(v["addr"], "%04X" % v["transfer"]["target"]) for v in calls]))

    # The framing read, which is what the write-up's per-address verdicts rest
    # on. `covered` is converges_from()'s not-found-by-this-method case and is
    # pinned as the count of anchors rather than as a framing verdict.
    for key, want_framing, needle in (
            (("common", "1207"), "entered", "`mov  dptr,#0xbf62`"),
            (("bank0", "805B"), "entered", "`jb   acc.7,0x805e`"),
            (("pd", "0000"), "image-start", ""),
            (("bank0", "031C"), "covered", "`sjmp 0x031f`"),
            (("bank1", "703A"), "covered", "`jnc  0x703d`"),
            (("common", "0512"), "covered", "`cjne a,#0x01,0x0517`")):
        v = by_key[key]
        check("%s %s frames as %s %s" % (key[0], key[1], want_framing,
                                         needle or "(nothing precedes it)"),
              v["framing"]["verdict"] == want_framing
              and needle in v["framing"]["detail"],
              "got " + repr(v["framing"]))

    # The boundary read, which is the per-address adjudication. It is a
    # partition of the eleven, so the whole split is pinned rather than one
    # member of each class: a fourth class appearing, or one of these moving,
    # is the kind of change a reader of the write-up needs told about.
    want_boundary = {
        ("bank0", "031C"): "mid-instruction",
        ("bank0", "805B"): "inside-a-function",
        ("bank1", "031C"): "mid-instruction",
        ("bank1", "703A"): "mid-instruction",
        ("common", "0512"): "mid-instruction",
        ("common", "1207"): "after-a-function",
        ("pd", "0000"): "vector",
        ("pd", "3497"): "after-a-function",
        ("pd", "998B"): "after-a-function",
        ("pd", "9C1B"): "after-a-function",
        ("pd", "9C4D"): "after-a-function",
    }
    got_boundary = {(v["program"], v["addr"]): v["boundary"][0] for v in verdicts
                    if v["bucket"] == "target-of-a-transfer"}
    check("the eleven partition 4 mid-instruction, 5 after-a-function, "
          "1 inside-a-function and 1 vector", got_boundary == want_boundary,
          "got " + repr(sorted(got_boundary.items())))
    check("common 0x1207 is measured against the committed function that ends "
          "immediately before it, and bank0 0x805B against the one it sits inside",
          by_key[("common", "1207")]["boundary"][1].startswith("common 0x1204")
          and "0x1204-0x1206" in by_key[("common", "1207")]["boundary"][1]
          and by_key[("bank0", "805B")]["boundary"][1].startswith("bank0 0x8054")
          and "0x8054-0x806B" in by_key[("bank0", "805B")]["boundary"][1],
          "got " + repr([by_key[("common", "1207")]["boundary"][1],
                         by_key[("bank0", "805B")]["boundary"][1]]))
    check("the three pd call sites at 0x3497/0x998B/0x9C1B follow a committed "
          "function that ends one byte earlier",
          all(by_key[("pd", a)]["boundary"][1].split()[1].endswith(
              "%04X" % (int(a, 16) - 3))
              for a in ("3497", "998B", "9C1B")),
          "got " + repr([by_key[("pd", a)]["boundary"][1]
                         for a in ("3497", "998B", "9C1B")]))

    # --- the refusals ---
    with tempfile.TemporaryDirectory() as scratch:
        decompiled, image, rows, named, anns = _fixture_tree(scratch, fw)
        got = {v["addr"]: v for v in census(named, rows, anns, image, decompiled)}

        def bucket(at):
            return got["%04X" % at]["bucket"]

        check("refusal: a transfer into a row's function of the same name is "
              "classified", bucket(0x0100) == "target-of-a-transfer",
              "got " + bucket(0x0100))
        check("refusal: a jump is not enough -- a target under another name is "
              "the switch verdict, not a second copy",
              bucket(0x0110) == "ghidra-switch-entry", "got " + bucket(0x0110))
        check("refusal: a stub whose target has no CSV row behind it is "
              "unexplained", bucket(0x0130) == "unexplained", "got " + bucket(0x0130))
        check("refusal: a transfer with no exported function at the target is "
              "unexplained", bucket(0x0120) == "unexplained", "got " + bucket(0x0120))
        check("refusal: a second copy that is not a transfer at all is "
              "unexplained", bucket(0x0140) == "unexplained", "got " + bucket(0x0140))
        check("refusal: a target at or above 0x8000 read from the common area is "
              "unexplained rather than read out of bank 0",
              bucket(0x0150) == "unexplained", "got " + bucket(0x0150))
        # The one boundary answer with no instance in the committed tree, and a
        # refusal is the only place it can be exercised: nothing committed
        # covers the instruction that lands on a fixture frame.
        check("refusal: a frame whose landing instruction is under no committed "
              "listing is reported `unframed` rather than interpreted",
              got["0100"]["boundary"] == ("unframed", None),
              "got " + repr(got["0100"]["boundary"]))
        unexplained = sorted(v["addr"] for v in got.values()
                             if v["bucket"] == "unexplained")
        check("refusal: unexplained is what --check fails on, and it fails on "
              "exactly those four and on nothing else",
              unexplained == ["0120", "0130", "0140", "0150"] and
              len(problems(got.values())) == 4,
              "got " + repr(unexplained) + " and %d problem(s)"
              % len(problems(got.values())))
        with open(os.path.join(decompiled, "common", "0100.asm"), "w") as f:
            f.write("; fixture\n0100     22 - -   ret\n")
        check("refusal: a listing that disagrees with the firmware is reported "
              "as a stale export",
              any("the export is stale" in p
                  for p in problems(census(named, rows, anns, image, decompiled))))
        check("refusal: a row with no listing is reported rather than skipped",
              any("no committed listing" in p
                  for p in problems(census(named, rows, anns, image,
                                           os.path.join(scratch, "absent")))))
    check("refusal: the committed tree has no unexplained row, so --check is "
          "green on it", not found, "; ".join(found[:3]))

    print()
    if bad:
        print("self-test FAILED: %d check(s) disagree with the readings above" % bad)
        return 1
    print("self-test passed: 25 rows in 11/14/0, the seven readable transfers "
          "with their bytes, targets and decompilations, the framing reads and "
          "the boundary partition, and the refusals")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="the gate form: the same report, and a non-zero exit on "
                         "an unexplained name, a stale listing or a missing one")
    ap.add_argument("--self-test", action="store_true",
                    help="the known answers and the refusals")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    index_rows = read_csv(INDEX_CSV)
    ann_rows = read_csv(ANNOTATIONS)
    verdicts = census(population(index_rows, ann_rows), index_rows, ann_rows)
    found = problems(verdicts)
    print(report(verdicts, found))
    # The exit code is the same either way. A census that has found a row it
    # cannot account for should not report success because nobody passed a flag,
    # and `build_ec_decompile.py --check` is the caller that turns this into a
    # gate -- the flag is here for a reader who wants to be explicit about it.
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
