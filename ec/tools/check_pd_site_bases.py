#!/usr/bin/env python3
"""What a PD-image `MOV DPTR,#imm16` site *names*: a byte, or the base of a
record array -- decided by the called routine's own body, not by the token.

`check_site_resolution.py` drops the PD image on purpose (its `region ==
"pd-image"` guard, and the reason in its docstring: the two programs have
separate XDATA maps, so a direction for the other program's byte is a category
error). That decision is right and this file does not undo it. What it left
open is the question the guard raises rather than answers: `static_refs_pd_image`
still counts those sites, a count with no direction, and an address with sites
in one program and none in the other reads as a lopsidedness in the firmware
when it may be a property of how the address is used.

The rule this asks is the one `ec/annotations/xdata-inc-dptr-only.md` §4 states
in general terms -- **the address space is a property of the callee's body, not
of the token** -- applied to the sites that tool cannot reach because they are
in the other program. `pd-xdata-overlap.md` §3 worked it by hand for `0x04A6`'s
four sites, reading the committed `pd/10BC.asm` and finding no `movx` in it;
this is that reading made re-runnable for any address, so a reader does not have
to take the hand argument on trust and a fifth site cannot be left out.

`stride-base` is the class that answer produces. It means: the site hands DPTR
to a routine that computes with the pointer and never dereferences it, so the
literal names **a base address of an indexed structure, not a byte**. The
address's own site count is real and stays in `static_refs_pd_image`; what it
counts is occurrences of the base, not reads or writes of that byte. Whether
the *rebased* pointer is dereferenced later, and where, is a question about the
caller's own body and is out of what this file can see (see below) -- a
`stride-base` row is a statement about the callee, never about the record.

**Two things this cannot do, both load-bearing.**

  * *It does not follow control flow.* A callee that dereferences DPTR on one
    path and not another is classified from its entry point's own decoded
    bytes, so a body whose access lies behind a branch reads as `stride-base`
    here. Every classification is therefore a statement about instructions at
    and just after the entry point, which is why `add_full_product_to_dptr`
    -- 7 instructions, all of them arithmetic on DPTR -- is a verdict its whole
    committed listing supports rather than an artefact of where a window ended.
  * *It is a static scan, and a class is not a behaviour.* `read` and `write`
    say an instruction dereferences or stores; they are not evidence that the
    PD acts on the value, and nothing here was measured on hardware. A site
    this file does not reach is `unresolved` or absent, and `unresolved` means
    "not found by this method", never "the PD does not touch this address" --
    the `movx @Ri` + P2 paging form (issue #34) is unscanned, so a zero is a
    lower bound.

The output is committed as `ec/annotations/pd-0436-0437-bases.csv` and
`--check` diffs it byte for byte, the arrangement `check_site_resolution.py`
uses, because the point of a census is that a reader can take it without
re-running anything.

Usage:
    python3 check_pd_site_bases.py ec/firmware/GMxMGxx_11.800
    python3 check_pd_site_bases.py ec/firmware/GMxMGxx_11.800 --csv
    python3 check_pd_site_bases.py ec/firmware/GMxMGxx_11.800 0x0437 0x0436
    python3 check_pd_site_bases.py --check
    python3 check_pd_site_bases.py --self-test
"""
import argparse
import csv
import io
import os
import sys

from check_site_resolution import (DEFAULT_IMAGE, INDEX_CSV, NOT_EXPORTED,
                                   containing, load_image, load_functions,
                                   runtime_of)
from disasm8051 import decode
from trace_xdata_refs import (call_target, classify, offset_for_runtime,
                              region_of, sites_for, walk, walk_why)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
COMMITTED_CSV = os.path.join(HERE, os.pardir, "annotations",
                             "pd-0436-0437-bases.csv")

# The addresses this census was asked about. `0x0434` is here beside the pair
# so the artifact shows the shape next to a second stride base rather than
# asserting the resemblance in prose, and `0x0436` is here because its
# absence from the PD is half of what the issue asked -- an address with sites
# on one program and none on the other is a fact about the two images, and it
# only reads as such against a row for the member that has none.
DEFAULT_ADDRS = ("0x0434", "0x0436", "0x0437")

# `trace_xdata_refs.REGIONS` names the PD program `pd-image`;
# `listing-index.csv` names it `pd`. One translation, at the join, so the
# region column keeps the spelling every other tool in this directory prints.
PROGRAM_FOR_REGION = {"pd-image": "pd"}

STRIDE_BASE = "stride-base"
READ = "read"
WRITE = "write"
READ_WRITE = "read+write"
UNRESOLVED = "unresolved"

CLASSES = (STRIDE_BASE, READ, WRITE, READ_WRITE, UNRESOLVED)


def movx_class(insns) -> str:
    """`read`/`write`/`read+write` from a decoded body, or "" for no `movx`.

    Deliberately not `trace_xdata_refs.classify()`, which is a *site*
    classifier: it takes `skip=1` to step over the `MOV DPTR` a site begins
    with, returns a handoff label on control flow, and describes how far an
    `inc DPTR` walked. A callee's body is not a site -- there is no leading
    `MOV DPTR` to step over, and the point here is what the body does to the
    pointer it was handed. So this counts the opcodes directly, and "" is the
    answer that carries the finding: a body with no `movx` in it never
    dereferences, whatever the caller went on to do with the result.

    The `db`-free opcodes are counted off `raw[0]` rather than off the
    mnemonic text, which is what keeps an `INLINE_ARG_CALLS` argument block or
    a `CASE_TABLE_CALLS` table out of the count: `disasm8051.decode()` yields
    those as items too, and a data byte can be `0xE0` without being a `movx`.
    A body that reached one is not a verdict this can make, so it is refused
    rather than counted -- see `decode_export()`'s `None`.
    """
    reads = writes = 0
    for _off, raw, text in insns:
        if text.startswith(("inline args:", "case table:")):
            return UNRESOLVED
        if raw[0] == 0xE0:
            reads += 1
        elif raw[0] == 0xF0:
            writes += 1
    if reads and writes:
        return READ_WRITE
    if reads:
        return READ
    if writes:
        return WRITE
    return ""


def decode_export(d: bytes, off: int, addr: int, size: int) -> list:
    """The instructions from `addr` onward, bounded by its export's end and by
    the first control-flow instruction.

    Both bounds are load-bearing, and neither alone is enough. `decode()` on
    its own answers "how many instructions do you want", and a count asked for
    is a count the caller guessed: decoding freely from `add_full_product_to_dptr`
    runs past its `ret` into the next export and finds a `movx` belonging to
    somebody else, which is how a 7-instruction pointer routine reads as an
    accessor. The export's `size` -- `check_site_resolution.load_functions`'s,
    reused rather than re-spelled, because it is what makes a half-open range
    out of an export -- closes that.

    The size bound alone is still not enough, and the case that shows it is
    `dptr_0428_plus_60a`: one of `0x0434`'s sites enters it at `0x35B0`, four
    bytes past its start, and its tail is `ljmp 0x10bc`, after which the bytes
    belong to the next routine even though the span reaches them. So
    `stop_at_flow` closes that too, and the two bounds answer different
    questions -- the export's end says how far the routine reaches, the flow
    stop says where its own instructions end.

    `size` is the distance from `addr` to the export's end, not the export's
    own length, because the two differ whenever a site enters mid-routine; the
    export's full length from `addr` would read past it.

    `size` is a ceiling, not a promise: `decode()` stops cleanly at the end of
    the buffer or of an inline argument block, and a body that decodes short of
    its span is one whose extent the index overstates. That is not checked
    here, and it is the way a `stride-base` could be an artefact of a truncated
    decode rather than of the bytes -- see the module docstring's "it does not
    follow control flow", which is the same limit on the other axis.
    """
    out = []
    for off_i, raw, text in decode(d, off, size, addr=addr, stop_at_flow=True):
        if off_i - off >= size:
            break
        out.append((off_i, raw, text))
    return out


def callee_body(d: bytes, target: int, region: str, functions: dict) -> tuple:
    """(decoded callee body, the export's `size`, its name) for `target`.

    A callee with no export is `(None, 0, NOT_EXPORTED)` rather than an error:
    an unexported routine is a real thing this image has -- two of `0x0434`'s
    PD sites hand DPTR to one -- and a row that says so says something the
    caller needs, where a decode at an assumed boundary would say something it
    cannot support.
    """
    program = PROGRAM_FOR_REGION.get(region, region)
    off = offset_for_runtime(target, region)
    if off is None:
        return None, 0, NOT_EXPORTED
    holder = containing(functions, program, target)
    if holder == NOT_EXPORTED:
        return None, 0, NOT_EXPORTED
    start = int(holder.split()[0], 16)
    for addr, (end, _name) in functions.get(program, ()):
        if addr == start:
            return (decode_export(d, off, target, end - target), end - addr,
                    holder)
    return None, 0, NOT_EXPORTED


def classify_site(d: bytes, off: int, region: str, functions: dict) -> dict:
    """One site's verdict: the class, the callee it was read through, why.

    The order is the argument. A `movx` at the site settles it and nothing else
    is consulted; failing that, a handoff is resolved against the callee's own
    body, and a callee with no `movx` is the `stride-base` case; anything the
    walk stopped short of is `unresolved` with the token that ended it, so a
    row is never silently a guess.
    """
    insns, why = walk_why(d, off)
    at_site = movx_class(insns[1:])
    if at_site:
        return {"class": at_site, "callee": "", "callee_name": "",
                "callee_size": "", "movx": "", "why": ""}

    hoff, raw, _text = insns[-1]
    if classify(insns).startswith("DPTR handed"):
        target = call_target(raw, runtime_of(hoff, region))
        if target is None:
            return {"class": UNRESOLVED, "callee": "", "callee_name": "",
                    "callee_size": "", "movx": "",
                    "why": "handoff target not resolvable from the bytes"}
        body, size, name = callee_body(d, target, region, functions)
        if body is None:
            return {"class": UNRESOLVED, "callee": f"0x{target:04X}",
                    "callee_name": name, "callee_size": "", "movx": "",
                    "why": "callee is not in the committed listing index"}
        cls = movx_class(body)
        if cls == UNRESOLVED:
            return {"class": UNRESOLVED, "callee": f"0x{target:04X}",
                    "callee_name": name, "callee_size": size, "movx": "",
                    "why": "callee's decode reached an inline argument block "
                           "or a case table, which is data rather than a "
                           "verdict about DPTR"}
        return {"class": cls or STRIDE_BASE,
                "callee": f"0x{target:04X}",
                "callee_name": name.split(None, 1)[1] if " " in name else name,
                "callee_size": size,
                "movx": cls or "none",
                "why": "" if cls else
                       f"{name} is {size} bytes of pointer arithmetic with no "
                       f"movx; the address is a base, not a byte"}

    return {"class": UNRESOLVED, "callee": "", "callee_name": "",
            "callee_size": "", "movx": "", "why": why}


COLUMNS = ("addr", "file_offset", "runtime", "class", "site_access", "callee",
           "callee_name", "callee_size", "callee_movx", "why")


def site_rows(d: bytes, addrs, pd_verified: bool, functions: dict):
    """One row per PD-image site of each address, file-offset order.

    Non-PD sites are skipped rather than counted, for the reason
    `check_site_resolution.py` gives for excluding them from its own census:
    the two programs have separate XDATA maps, so a class read off the main
    EC's bytes would say nothing about the PD's. An address with no PD site at
    all contributes no row, which is what makes its absence a measurement --
    `sites_for()` is the same byte scan the recorded `static_refs_pd_image`
    counts come from, so a missing row and a recorded zero are the same claim.
    """
    for text in addrs:
        addr = int(text, 16)
        for off in sites_for(d, addr):
            region = region_of(off, pd_verified)[0]
            if region not in PROGRAM_FOR_REGION:
                continue
            insns = walk(d, off)
            verdict = classify_site(d, off, region, functions)
            yield ([f"0x{addr:04X}", f"0x{off:05X}",
                    f"0x{runtime_of(off, region):04X}", verdict["class"],
                    classify(insns), verdict["callee"], verdict["callee_name"],
                    str(verdict["callee_size"]), verdict["movx"], verdict["why"]])


def csv_text(d: bytes, addrs, pd_verified: bool, functions: dict) -> str:
    """The whole census as CSV text, from the image.

    A string rather than a file write, so `--check` diffs the same bytes the
    default run prints -- the arrangement `check_site_resolution.py:csv_text()`
    documents and the reason `--csv` needs no separate code path.
    """
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    for row in site_rows(d, addrs, pd_verified, functions):
        w.writerow(row)
    return buf.getvalue()


CALIBRATION = (
    "A class here is a statement about instructions, not about behaviour, and\n"
    "nothing in this file was measured on hardware. `stride-base` says the\n"
    "called routine computes with DPTR and never dereferences it, so the\n"
    "literal names a base address rather than a byte -- it is not a claim that\n"
    "the record behind it is never read. A site this file does not reach is\n"
    "'not found by this method', never 'absent': the indirect `movx @Ri` and P2\n"
    "paging form (issue #34) is unscanned, so every count here is a lower bound."
)


def write_sites(d: bytes, addrs, pd_verified: bool, functions: dict) -> None:
    tally = {}
    for row in site_rows(d, addrs, pd_verified, functions):
        tally[row[3]] = tally.get(row[3], 0) + 1
        print(f"  {row[0]}  file {row[1]}  pd {row[2]}  {row[3]:<12} "
              f"{row[4]}")
        if row[5]:
            print(f"        handed to {row[5]} = {row[6]} "
                  f"({row[7]} bytes, movx: {row[8]})")
        if row[9]:
            print(f"        {row[9]}")
    print()
    for cls in CLASSES:
        if tally.get(cls):
            print(f"  {cls}: {tally[cls]}")
    print()
    print(CALIBRATION)


def self_test() -> int:
    """The classifier's discrimination, against constructed bodies.

    Fixtures rather than the committed rows, for the reason
    `check_site_resolution.py`'s own `self_test()` gives: a rule tested only
    against the data it was derived from is not tested. The negative
    controls are the
    point -- a classifier that answered `stride-base` for everything would pass
    every assertion about the real callee, so each of `movx a,@dptr` and
    `movx @dptr,a` is fed a body built from the committed listing's own bytes
    and has to come back `read` and `write` respectively.
    """
    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    # `add_full_product_to_dptr` byte for byte, from ec/decompiled/pd/10BC.asm.
    add_full = bytes.fromhex("a4 25 82 f5 82 e5 f0 35 83 f5 83 22")
    check("a body with no movx classifies as no access at all",
          movx_class(decode(add_full, 0, 32)) == "",
          "(this is the finding: the routine computes with DPTR and never "
          "dereferences it, so '' is a result and not a failure)")
    # `read_xdata_pair_to_r1r2`, from ec/decompiled/bank1/8886.asm.
    read2 = bytes.fromhex("e0 f9 a3 e0 fa 22")
    check("a body of movx a,@dptr classifies as read",
          movx_class(decode(read2, 0, 32)) == READ)
    check("a body of two reads is still read, not read+write",
          movx_class(decode(read2, 0, 32)) != READ_WRITE)
    # `write_r1r2_to_xdata_pair`, from ec/decompiled/bank1/888C.asm.
    write2 = bytes.fromhex("e9 f0 a3 ea f0 22")
    check("a body of movx @dptr,a classifies as write",
          movx_class(decode(write2, 0, 32)) == WRITE)
    both = bytes.fromhex("e0 f0 22")
    check("a body that both reads and stores is read+write",
          movx_class(decode(both, 0, 32)) == READ_WRITE)
    check("an empty body is no access, not read",
          movx_class(decode(b"", 0, 32)) == "")
    check("a bare ret is no access",
          movx_class(decode(bytes.fromhex("22"), 0, 32)) == "")

    check("every class name this file can emit is in CLASSES",
          {STRIDE_BASE, READ, WRITE, READ_WRITE, UNRESOLVED} == set(CLASSES),
          "(a class nothing in CLASSES names would print in a committed cell "
          "with no vocabulary behind it)")
    check("read+write is the only class naming two directions",
          CLASSES.count(READ_WRITE) == 1)

    # --- the containment join, against the committed listing index --------
    functions = load_functions()
    check("the committed index loads spans for the pd program",
          bool(functions.get("pd")),
          "(the size-span join is what makes a callee's body decidable, and "
          "without it every row would be `unresolved`)")
    check("a known pd export is found by its size span",
          containing(functions, "pd", 0x10C0) != NOT_EXPORTED,
          "(the join this file borrows from check_site_resolution.py)")

    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_IMAGE,
                    help="raw EC firmware image (default: the one beside "
                         "this tool)")
    ap.add_argument("addrs", nargs="*", default=list(DEFAULT_ADDRS),
                    help=f"XDATA addresses to census in the PD image "
                         f"(default: {' '.join(DEFAULT_ADDRS)})")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per site on stdout instead of the "
                         "human table")
    ap.add_argument("--check", action="store_true",
                    help="fail if the census differs byte for byte from the "
                         "committed CSV")
    ap.add_argument("--committed", default=COMMITTED_CSV,
                    help="CSV --check diffs against (default: the committed "
                         "one beside this tool); a path is taken so the "
                         "refusal can be shown against a doctored copy "
                         "without touching the committed file")
    ap.add_argument("--self-test", action="store_true",
                    help="pin the classifier against constructed bodies")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    d, pd_verified = load_image(args.firmware)
    if d is None:
        return 1
    functions = load_functions(INDEX_CSV)

    if args.check:
        with open(args.committed, newline="") as f:
            committed = f.read()
        fresh = csv_text(d, args.addrs, pd_verified, functions)
        if committed != fresh:
            import difflib
            for line in list(difflib.unified_diff(
                    committed.splitlines(True), fresh.splitlines(True),
                    os.path.relpath(args.committed, REPO), "fresh"))[:40]:
                sys.stdout.write(line)
            print("check_pd_site_bases.py: the census differs from the "
                  f"committed {os.path.relpath(args.committed, REPO)}",
                  file=sys.stderr)
            return 1
        rows = len(fresh.splitlines()) - 1
        print(f"{os.path.relpath(args.committed, REPO)}: {rows} PD site row(s) "
              "match a fresh census from the committed image")
        return 0

    if args.csv:
        sys.stdout.write(csv_text(d, args.addrs, pd_verified, functions))
        return 0

    write_sites(d, args.addrs, pd_verified, functions)
    return 0


if __name__ == "__main__":
    sys.exit(main())