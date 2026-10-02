#!/usr/bin/env python3
"""Re-derive the whole reference table for registers.yaml in one pass: the
per-image count split *and* the access direction of every site behind it.

check_register_counts.py answers "are the three recorded counts still the
counts in the image". This answers the question one level down, which a
count cannot: *what do those sites do*. Two different things inflate a
`MOV DPTR,#imm16` total and neither is a register access --

  * the site builds a **CODE** pointer (`movc a,@a+dptr`, `jmp @a+dptr`)
    into a string or jump table, which says nothing about a register of
    that number (ec/annotations/ec-0x07d0-sites.md 5), and
  * the site hands DPTR to a subroutine, where the direction is not
    resolvable at the site at all.

Both are reported as themselves here rather than as "no movx", so that an
address whose population is dominated by them is visible instead of
looking like an ordinary referenced register.

The classification is trace_xdata_refs.classify() over trace_xdata_refs.walk(),
so it inherits every limit of that walk: a linear best-effort decode, not a
disassembler, over a window of 8 instructions that stops at the first
control-flow instruction. Indirect/pointer XDATA access is invisible to the
site scan underneath it, so a `0` anywhere in this table means "not found by
this method", never "absent" -- 0x07B9 is the standing counter-example.
Nothing here is measured on hardware: a `write` class is not evidence that
the EC acts on the value, only that an instruction stores to the address.

The table reconciles itself twice per address -- the class buckets have to
sum to the site count, and main + PD to the file-wide total -- and exits
non-zero if either fails, so a silently dropped site is a failure rather
than a quieter table.

`--callee-depth N` resolves the handoff bucket N levels down, by decoding
the called routine's own entry point the way ec-0x07d0-sites.md 3 and
pd-xdata-overlap.md 3 did by hand for 0x07D0 and 0x04A6. It inherits every
limit above once per level, N+1 walks in all: a callee that hands DPTR on
again is followed again while the budget lasts, and one that ends its window
at a branch, or is not reachable from the calling site's region, or loops
back onto a routine the chain already entered, stays `handoff->unresolved`,
which is a verdict of this method and not a statement that the callee does
nothing. N=1 is the level every committed transcript was taken at and is
unchanged; deeper levels add a `chain` and a `stop` column rather than a new
class, so the buckets still partition the sites the same way at every N.

`--follow-flow` splits the `none` bucket the other way, by what
walk_flow_follow.py finds when it continues one path past the control-flow
instruction the walk stopped at -- a conditional's fall-through, or an
unconditional jump's target. A site resolved that way is a **weaker** claim
than one resolved where it sits, so it lands in its own `->flow` column rather
than in `read`/`write`/`r+w`, and `--csv` carries the instruction that carried
the follow in a `flow_via` column. Only `none` sites are re-decoded, so every
other bucket here is still `classify()` over the bytes `walk()` decoded and
the reconciliation below is what says the columns still partition the sites.
A `none` cell that stays `none` after the follow means "not found by this
method", never "this site does not access the register" -- 0x07B9 is the
standing counter-example, and nothing here is measured on hardware.

Usage:
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --csv > sites.csv
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 1
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --callee-depth 2 --csv
    python3 ec/tools/register_ref_table.py ec/firmware/GMxMGxx_11.800 --follow-flow
"""
import argparse
import collections
import csv
import sys

import yaml

from check_register_counts import DEFAULT_YAML, counts_for
from trace_xdata_refs import (PD_MARKER, call_target, classify, mnemonic,
                              offset_for_runtime, region_of, runtime_addr,
                              sites_for, walk)
# One-directional: this imports walk_flow_follow, which imports only
# trace_xdata_refs and disasm8051, so there is no cycle back here.
from walk_flow_follow import NO_MOVX, follow_site

# Names the absolute forms because that is what it meant when the committed
# transcripts and ec-0x07d0-sites.csv were taken; the bucket now also holds
# the paged ajmp/acall handoffs classify() learned to see.
HANDOFF = "handed to lcall/ljmp (unresolved)"

NONE = "no movx in window"

# Bucket label -> markdown column header. Order is the table's column order,
# and the labels are what --csv writes, so the two stay the same vocabulary.
CLASSES = (
    ("read", "read"),
    ("write", "write"),
    ("read+write", "r+w"),
    ("movc (CODE pointer)", "movc"),
    ("jmp @a+dptr", "jmp"),
    (HANDOFF, "handoff"),
    (NONE, "none"),
)

# What the handoff column becomes at --callee-depth 1. The unresolved bucket
# keeps the depth-0 label: it is the same verdict, reached one level further
# in, so nothing has to special-case it.
HANDOFF_CLASSES = (
    ("handed to lcall/ljmp -> callee reads", "handoff->read"),
    ("handed to lcall/ljmp -> callee writes", "handoff->write"),
    ("handed to lcall/ljmp -> callee reads+writes", "handoff->r+w"),
    (HANDOFF, "handoff->unresolved"),
)

# Why a handoff chain stopped without a direction. Four reasons, each its
# own string, because the class is the same `handoff->unresolved` for all of
# them and the class alone cannot say which fired: a chain that runs out of
# budget is a question this tool was not asked far enough to answer, and one
# that ends on a routine that never dereferences DPTR is an answer.
STOP_NO_TARGET = "call target is not resolvable from the bytes"
STOP_UNREACHABLE = "callee not reachable from the calling region"
STOP_CYCLE = "cycle: a routine already on this chain"
# The depth goes in the string rather than beside it, and it is the depth the
# run was asked for: the reader of a `cap 8` row then knows that a deeper
# `--callee-depth` would have carried that chain further, which the budget
# remaining at the moment it fired would not tell them.
STOP_CAP = "callee-depth cap {depth} reached; the callee is itself a handoff"

# What the none column becomes at --follow-flow, in the same in-place
# replacement --callee-depth uses. The `->flow` names are the point: a site
# resolved by following a branch is a weaker claim than one resolved where it
# sits, and the two never share a column, so nothing downstream can compare
# them as equal or average them together. The `none` label survives as the
# last of the five because a site the follow does not settle is still `none`:
# the same verdict, reached further in, on the same terms as the depth-0 one.
FLOW_CLASSES = (
    ("read reached only by following a branch", "read->flow"),
    ("write reached only by following a branch", "write->flow"),
    ("read+write reached only by following a branch", "r+w->flow"),
    ("CODE pointer or DPTR handoff reached only by following a branch",
     "other->flow"),
    (NONE, "none"),
)


def classes_for(callee_depth: int, follow_flow: bool = False):
    """Column order for a mode. Each flag replaces one column in place by the
    set it resolves into, so the two modes never both describe the same site,
    and depth 0 without --follow-flow stays byte-identical to before."""
    replacements = {}
    if follow_flow:
        replacements[NONE] = FLOW_CLASSES
    if callee_depth:
        replacements[HANDOFF] = HANDOFF_CLASSES
    if not replacements:
        return CLASSES
    out = []
    for label, short in CLASSES:
        out.extend(replacements.get(label, ((label, short),)))
    return tuple(out)


def bucket(access: str) -> str:
    """Map one classify() string onto one of CLASSES."""
    if access.startswith("DPTR handed"):
        return HANDOFF
    if access.startswith("movc"):
        return "movc (CODE pointer)"
    if access.startswith("jmp"):
        return "jmp @a+dptr"
    read, write = "read" in access, "write" in access
    if read and write:
        return "read+write"
    if read:
        return "read"
    if write:
        return "write"
    return NONE


def flow_bucket(access: str) -> str:
    """The bucket for a verdict `walk_flow_follow` reached past a branch.

    Deliberately not `bucket()`, and the difference is the whole reason the
    `->flow` columns exist: a handoff or a `movc` found one level down is a
    weaker claim than the same verdict at the site, and putting the two in one
    column would let a reader treat them as equal. Anything that is not a
    read, a write or both lands in the catch-all rather than in `none` -- the
    follow *did* find something there, and a `none` cell would say it had not.
    """
    if access == NO_MOVX:
        return NONE
    read, write = "read" in access, "write" in access
    if read and write:
        return FLOW_CLASSES[2][0]
    if read:
        return FLOW_CLASSES[0][0]
    if write:
        return FLOW_CLASSES[1][0]
    return FLOW_CLASSES[3][0]


def resolve_handoff(d: bytes, off: int, insns, pd_verified: bool, depth: int = 1,
                    seen: tuple = ()):
    """(bucket, callee runtime, callee window, chain, stop) for one handoff site.

    The callee's entry point is decoded with the same walk, classified with
    skip=0 because the instruction at the entry point is itself the access.
    Anything that is not a plain movx direction -- a movc, a walk that ends at
    a branch -- stays in the unresolved bucket with the callee's own verdict as
    the window, so the reason is on the row.

    `depth` is how many more levels of this walk may be spent on the callee,
    and `seen` is the chain of targets already entered to get here. A callee
    whose own window is *itself* a handoff is a second level down, so it
    recurses with depth-1 while the budget lasts: at depth 1 that branch is
    not taken and the row is unresolved exactly as it was before this took a
    depth. Each way out is a named reason rather than a bare unresolved, so a
    row that stops at N names which of them fired and at which address.

    The cap names the depth that was *asked for*, not the budget left when it
    fired: a chain cut off by `--callee-depth 3` is `seen`'s length plus this
    call's `depth`, which is 3 at every level of that run. Naming the
    remainder instead would put `cap 1` on a run that never mentioned 1, and
    the row would not say which of the depths a reader could have asked for
    would have carried it further.

    The chain and the stop reason are returned beside the three the depth-1
    call already returned, and are what `--csv` writes as its `chain` and
    `stop` columns. They are the only way to re-check a deeper row: the
    bucket says the direction, and these say how many levels it took to get
    there and what ended the walk.
    """
    # walk() stops at the first control-flow instruction, so the call
    # classify() saw is the last one it decoded. Its runtime address is what
    # the paged forms need to name a page at all -- without it call_target()
    # would return None for every ajmp/acall and they would all land in the
    # unresolved bucket.
    hoff, raw, _ = insns[-1]
    target = call_target(raw, runtime_addr(hoff, pd_verified))
    if target is None:
        return HANDOFF, None, "handoff target is not resolvable from the bytes", \
            seen, STOP_NO_TARGET
    region = region_of(off, pd_verified)[0]
    # For an ajmp/acall this lands in the caller's own region by construction
    # -- the target is inside the page the handoff itself runs in -- so the
    # same-bank assumption offset_for_runtime() carries is not load-bearing
    # for those rows, only for the absolute forms.
    coff = offset_for_runtime(target, region)
    if coff is None:
        return HANDOFF, target, f"callee not reachable from region {region}", \
            seen, STOP_UNREACHABLE
    # A routine that hands DPTR back to a routine this chain already entered
    # is a loop, and recursing on it would run until the stack gave out. This
    # image has no such chain, so nothing else would have caught it: the guard
    # is what the fixtures in test_callee_depth.py are for.
    if target in seen:
        return HANDOFF, target, f"cycle: 0x{target:04X} is already on this chain", \
            seen, STOP_CYCLE
    chain = seen + (target,)
    cinsns = walk(d, coff)
    access = classify(cinsns, skip=0)
    window = " ; ".join(" ".join(mn.split()) for _, _, mn in cinsns)
    read, write = "read" in access, "write" in access
    if read and write:
        return ("handed to lcall/ljmp -> callee reads+writes", target, window,
                chain, "")
    if read:
        return "handed to lcall/ljmp -> callee reads", target, window, chain, ""
    if write:
        return "handed to lcall/ljmp -> callee writes", target, window, chain, ""
    if access.startswith("DPTR handed") and depth > 1:
        # The one case that recurses, and only while a level remains to
        # spend: a callee that forwards DPTR again is the same question one
        # level down, and answering it is what --callee-depth N is for.
        return resolve_handoff(d, coff, cinsns, pd_verified, depth - 1, chain)
    # Not a direction, and either not a handoff or out of budget. Which of
    # the two is the difference between "this routine never dereferences the
    # DPTR it was given" and "there was no level left to find out", so the
    # reason names which rather than leaving both reading `unresolved`.
    stop = (STOP_CAP.format(depth=len(seen) + depth)
            if access.startswith("DPTR handed")
            else f"no direction at 0x{target:04X}: {access}")
    return HANDOFF, target, f"{access} | {window}", chain, stop


def site_rows(d: bytes, addr: int, pd_verified: bool, callee_depth: int,
              follow_flow: bool = False):
    """One (offset, region, runtime, bucket, callee, callee_window, window,
    via, chain, stop) per site. The markdown table is a group-by over these, so
    both outputs classify the same sites the same way.

    The last two are the chain `resolve_handoff` walked and why it stopped.
    They are None at depth 0, where nothing was resolved; from depth 1 up they
    carry whatever the walk found, and it is write_csv() that leaves the two
    columns out of the table until the depth is above 1. That is what keeps
    the depth-0 and depth-1 tables byte-identical to the ones the tool emitted
    before `--callee-depth` took an N -- the columns, not the values.
    """
    for o in sites_for(d, addr):
        if follow_flow:
            # follow_site() re-derives the site's own window rather than
            # taking one in, and both labels come out of that single decode --
            # so `bucket(f.linear)` and `flow_bucket(f.followed)` cannot
            # disagree about what the site looks like before a branch.
            f = follow_site(d, addr, o, pd_verified)
            insns, label, via = f.anchor, bucket(f.linear), None
            if label == NONE:
                label, via = flow_bucket(f.followed), f.via_cell
        else:
            insns, label, via = walk(d, o), None, None
            label = bucket(classify(insns))
        callee = window = chain = stop = None
        if callee_depth and label == HANDOFF:
            label, callee, window, chain, stop = resolve_handoff(
                d, o, insns, pd_verified, callee_depth)
        yield (o, region_of(o, pd_verified)[0], runtime_addr(o, pd_verified),
               label, callee, window,
               " ; ".join(" ".join(mn.split()) for _, _, mn in insns[1:]), via,
               chain, stop)


def addresses(regs):
    """(name, addr) for every address in registers.yaml, file order."""
    for r in regs:
        name = r.get("name", "?")
        addrs = r["addr"] if isinstance(r["addr"], list) else [r["addr"]]
        for addr in addrs:
            yield name, addr


def row_for(d: bytes, addr: int, pd_verified: bool, rows):
    """(total, main, pd, {bucket: count}) for one address."""
    total, main, pd = counts_for(d, addr, pd_verified)
    hist = collections.Counter(r[3] for r in rows)
    return total, main, pd, hist


def reconcile(name: str, addr: int, total: int, main: int, pd: int, hist,
              classes) -> int:
    problems = 0
    classified = sum(hist.values())
    if classified != total:
        print(f"{name} 0x{addr:04X}: {classified} site(s) classified, "
              f"{total} found -- a site was dropped between sites_for() and "
              "classify()", file=sys.stderr)
        problems += 1
    if main + pd != total:
        # Same failure check_register_counts.py makes, for the same reason:
        # a site outside the mapped regions means the image map is wrong.
        print(f"{name} 0x{addr:04X}: {main} + {pd} sites do not add up to "
              f"{total} -- some site is outside the mapped regions, "
              "re-derive them with find_banks.py", file=sys.stderr)
        problems += 1
    unknown = set(hist) - {label for label, _ in classes}
    if unknown:
        print(f"{name} 0x{addr:04X}: unbucketed class(es) {sorted(unknown)} -- "
              "classify() gained a verdict bucket() does not know",
              file=sys.stderr)
        problems += 1
    return problems


def write_markdown(d: bytes, regs, pd_verified: bool, callee_depth: int,
                   follow_flow: bool = False) -> int:
    problems = 0
    classes = classes_for(callee_depth, follow_flow)
    header = ["addr", "register", "total", "main EC", "PD"]
    header += [short for _, short in classes]
    align = ["---", "---"] + ["---:"] * (len(header) - 2)
    print("| " + " | ".join(header) + " |")
    print("|" + "|".join(align) + "|")
    for name, addr in addresses(regs):
        rows = list(site_rows(d, addr, pd_verified, callee_depth, follow_flow))
        total, main, pd, hist = row_for(d, addr, pd_verified, rows)
        problems += reconcile(name, addr, total, main, pd, hist, classes)
        # The parenthetical half of a name is commentary ("(Windows-only
        # address, ...)"), and one of them is longer than the rest of the
        # row put together; --csv keeps the name verbatim for grepping.
        short_name = name.split(" (")[0]
        cells = [f"`0x{addr:04X}`", f"`{short_name}`", str(total), str(main), str(pd)]
        cells += [str(hist.get(label, 0)) for label, _ in classes]
        print("| " + " | ".join(cells) + " |")
    return problems


def write_csv(d: bytes, regs, pd_verified: bool, callee_depth: int,
              follow_flow: bool = False) -> int:
    """One row per site. The markdown table is a group-by over this, so a
    reader can re-derive it without re-running anything. At depth 1 the two
    extra columns carry the callee the class came from, and under
    --follow-flow a `flow_via` column carries the instruction that carried
    the follow, so a row's verdict can be checked against an independent
    disassembler.

    Above depth 1 two more columns carry the chain the class came from and
    the reason the chain stopped, which is what makes a deeper row checkable
    the same way a depth-1 one is: `s 0xB1F2; pd N` at each address in the
    chain reproduces the window, and the stop says which of the four reasons
    ended it. Gated on `callee_depth > 1` rather than `> 0` so the depth-0
    and depth-1 headers stay exactly the committed ones."""
    problems = 0
    classes = classes_for(callee_depth, follow_flow)
    w = csv.writer(sys.stdout)
    head = ["addr", "register", "file_offset", "region", "runtime", "class",
            "window"]
    if callee_depth:
        head += ["callee", "callee_window"]
    if callee_depth > 1:
        head += ["chain", "stop"]
    if follow_flow:
        head += ["flow_via"]
    w.writerow(head)
    for name, addr in addresses(regs):
        rows = list(site_rows(d, addr, pd_verified, callee_depth, follow_flow))
        total, main, pd, hist = row_for(d, addr, pd_verified, rows)
        problems += reconcile(name, addr, total, main, pd, hist, classes)
        for o, region, rt, label, callee, callee_window, window, via, chain, stop \
                in rows:
            cells = [f"0x{addr:04X}", name, f"0x{o:05X}", region,
                     f"0x{rt:04X}" if rt is not None else "", label, window]
            if callee_depth:
                cells += [f"0x{callee:04X}" if callee is not None else "",
                          callee_window or ""]
            if callee_depth > 1:
                cells += [" -> ".join(f"0x{t:04X}" for t in chain or ()),
                          stop or ""]
            if follow_flow:
                cells += [via or ""]
            w.writerow(cells)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--registers", default=DEFAULT_YAML,
                    help="registers.yaml to tabulate (default: the one beside this tool)")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per site on stdout instead of the markdown table")
    ap.add_argument("--markdown", action="store_true",
                    help="markdown table (the default; accepted so a pasted command can be explicit)")
    ap.add_argument("--callee-depth", type=int, default=0, metavar="N",
                    help="N: split the handoff bucket by what the called "
                         "routine's own entry point does with DPTR, following "
                         "a chain of handoffs up to N levels down (default 0, "
                         "site only). N=1 is what the committed transcripts "
                         "were taken at. At N>=2 --csv adds `chain` and `stop` "
                         "columns; a cycle and the cap each name themselves "
                         "in `stop` rather than reading as a bare unresolved")
    ap.add_argument("--follow-flow", action="store_true",
                    help="split the `none` bucket by what ec/tools/walk_flow_"
                         "follow.py finds on the one path past the branch the "
                         "walk stopped at, into read->flow / write->flow / "
                         "r+w->flow / other->flow and a `none` that survives "
                         "it. A site resolved that way is a weaker claim than "
                         "one resolved where it sits and never shares a column "
                         "with it; only `none` sites are re-decoded, so every "
                         "other bucket is unchanged code over unchanged bytes")
    args = ap.parse_args()
    # Refused by name rather than left to mean nothing: `choices` cannot
    # express "any non-negative N", and a negative depth is not a shallower
    # table, it is a request to walk a chain that does not exist.
    if args.callee_depth < 0:
        ap.error(f"--callee-depth {args.callee_depth} is not a depth: it is how "
                 "many levels of handoff chain to follow, so it counts from 0 "
                 "(the site alone) upwards")

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1

    with open(args.registers) as f:
        regs = yaml.safe_load(f)["registers"]

    problems = (write_csv if args.csv else write_markdown)(
        d, regs, pd_verified, args.callee_depth, args.follow_flow)
    addrs = sum(1 for _ in addresses(regs))
    if problems:
        print(f"{problems} reconciliation problem(s) across {len(regs)} entries "
              f"/ {addrs} addresses", file=sys.stderr)
        return 1
    # stderr, so --csv output stays a clean CSV when redirected; flushed
    # first so a console transcript keeps the summary under the table.
    sys.stdout.flush()
    print(f"{len(regs)} entries / {addrs} addresses: class buckets sum to the "
          "site count and main + PD to the file-wide total for every address",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
