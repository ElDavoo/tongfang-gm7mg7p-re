#!/usr/bin/env python3
"""Re-decode the sites a linear `walk()` gives up on, by following one path
past the control-flow instruction it stopped at, and say which of them resolve.

`trace_xdata_refs.walk()` is a linear best-effort decode of at most 8
instructions that stops at the first control-flow instruction, and
`classify()` reports "no movx found in the decoded window" when a window ends
without one. That is the weakest cell `register_ref_table.py` prints, and
`../annotations/static-refs-audit.md` 5.3 shows all three of its EC-side
occurrences are the walk giving up rather than a site that does nothing: the
access sits on the *other side* of a branch, or in a routine one `sjmp` away.
This walks the one path it can and re-decodes what is there.

**What it does, precisely.** A site is re-decoded only if `classify()` calls
it `NO_MOVX` below. Anything already classified as `read`, `write`, `r+w`,
`movc`, `jmp` or a DPTR handoff comes back byte-identical, which is what makes
"no `static_refs*` count moves" structural rather than a check bolted on beside
it: the other six buckets are computed by unchanged code over unchanged bytes.
The re-decode starts at the address the walk stopped short of and continues:

  * a **conditional** branch does not transfer control on the path taken here,
    so the walk continues at its fall-through. The branch-taken arm is *not*
    walked, and the row says so in `via` (`fall-through past ...`) rather than
    leaving the reader to assume both were looked at.
  * an **unconditional** `sjmp`/`ajmp`/`ljmp` does transfer control, and its
    target is followed and the walk resumed there. `ljmp` is here for the same
    reason `ajmp` is: in a *followed* segment it is the same unconditional
    transfer, and the alternative is stopping at it, which is the giving-up
    this tool exists to stop.
  * `ret`/`reti` end the walk, and so does `jmp @a+dptr`: there is no next
    instruction to continue at, and an indirect jump's target is not in the
    bytes.

A window that ends in an `lcall`/`acall`/`ljmp`/`ajmp` is not really this
tool's to continue, and in practice it never is: `classify()` already reports
a DPTR handoff for those, so such a site is bucketed `handoff` and
`register_ref_table.py --callee-depth 1` is what resolves it. `continuation()`
carries the branches anyway, so that a `classify()` that stopped reporting the
handoff would follow the jump rather than fall through to its last line --
which is the direction that stays right.

Everything else -- a window that ran out of instruction budget, ran off the
buffer, or hit a `mov dptr` reload -- ends the walk at the same place
`walk()` did, with `walk_why()`'s own token, because a bound is not a branch
and there is nothing to follow. Changing one of those bounds is
`walk_budget_census.py`'s question, and that file measured what a larger
budget does to the committed tables; this one does not reopen it.

**Every target comes from the decoded stream, never from the site address.**
`walk_branch_arms.py`'s docstring gives the reason with a worked example:
`0x9432` is `90 07 51 e0 54 80 70 05`, where an intervening `anl a,#0x80`
puts the `jnz` at `site + 6` and not `site + 7`, so the same arithmetic lands
one byte inside the `mov dptr` that follows and decodes as a plausible-looking
`mov dptr,#0x7F90`. Here the last instruction the walk actually decoded
carries the operand, and `relative_target()`/`paged_target()` are asked for
the target, so a mis-framed branch is a wrong *source address* rather than a
wrong displacement. A target that is not reachable from the site's own region
is reported unresolved rather than followed against another region's bytes.

**The bounds are named, printed in `--help`, and named on every row that hits
them** -- `max_depth (4) exhausted` and `walk_why()`'s own
`max_insns (8) exhausted`, the same `budget_end()` idiom `walk()`'s terminator
column uses, rather than a bare number a reader has to look up. The site's own
window is always `walk()`'s own budget of 8 whatever `--max-insns` says, so
the `linear` column is the cell the committed tables carry. `loop back to
0xNNNN` is in `ends` and is *not* one of the bounds: a path that cycles has
been walked as far as it goes, and calling that a cut would understate it.

**A followed `read` is a weaker claim than one resolved at the site, and the
two are a column apart rather than averaged together.** `linear` is what
`classify()` says today, `followed` is what the single path this method chose
reaches, and `via` names the instruction that carried the follow -- so a site
resolved by walking past a branch cannot be read as one resolved where it
sits. The branch-taken arm is the other half of that weakness;
`walk_branch_arms.py` walks both arms with DPTR tracked and is the stronger
claim. Nothing here is a statement about what the EC does at run time.

**What a `0` or an unresolved `none` here means.** "Not found by this method",
never "absent" and never "this site does not access the register". The
indirect-addressing blind spot `../../docs/findings.md` 4c records belongs to
this walk as much as to `scan_refs.py`: `0x07B9` is a byte Windows
demonstrably writes with zero direct `MOV DPTR` sites anywhere in the image.
Reading a negative cell here as absence is 4c's error in miniature, and
`../annotations/static-refs-audit.md` 5.3 already warns of it for the cells
this tool reduces.

**Nothing here is measured on hardware.** A flow-followed `read` is an
instruction that loads the byte, on a path this method chose out of a bounded
number of them. No register was read back, no capture opened, no EC, no
Windows. Every input is the committed 256 KiB image.

Usage:
    python3 walk_flow_follow.py ../firmware/GMxMGxx_11.800 0x0768 0x043E 0x07D0
    python3 walk_flow_follow.py ../firmware/GMxMGxx_11.800 0x0768 --csv
    python3 walk_flow_follow.py ../firmware/GMxMGxx_11.800 0x0768 --max-depth 0
    python3 walk_flow_follow.py ../firmware/GMxMGxx_11.800 0x0768 --check
    python3 walk_flow_follow.py --check
"""
import argparse
import collections
import csv
import difflib
import io
import os
import sys

from disasm8051 import REL_OPCODES, mnemonic, relative_target
from trace_xdata_refs import (FLOW_END, PD_MARKER, call_target, classify,
                              offset_for_runtime, region_of, runtime_addr,
                              sites_for, walk_why)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
ANNOT = os.path.join(HERE, os.pardir, "annotations")
DEFAULT_FIRMWARE = os.path.join(HERE, os.pardir, "firmware", "GMxMGxx_11.800")
FOLLOW_CSV = os.path.join(ANNOT, "flow-follow-none-sites.csv")

# How many control transfers past the branch the site's own window stopped at
# to follow, and how many instructions to decode in each followed segment.
#
# Four is not a tuned figure and not a minimal one. The three EC-side sites
# ../annotations/static-refs-audit.md 5.3 hand-checked against `r2 -a 8051`
# each resolve on the *first* follow, so `--max-depth 1` reproduces the same
# three verdicts and the same `via` cells; 4 is headroom over that, kept
# named rather than hard-coded so a reader can re-run at another value and see
# which cells are a bound talking rather than the bytes. Both bounds are named
# in every row that hits them -- see the bounds paragraph in the docstring.
MAX_DEPTH = 4
MAX_INSNS = 8

# walk()'s own budget, read off the function rather than written out, the way
# walk_budget_census.py reads it. This is what fixes the *site's* window: the
# `linear` column is the cell the nine committed tables carry, and it stays
# that whatever --max-insns is set to, because --max-insns bounds the follow
# and not the window this file is an extension of.
WINDOW = walk_why.__defaults__[0]

# classify()'s "the decoded window held no access" verdict, taken from
# classify() rather than written out, so the test here and the bucket test in
# register_ref_table.py compare against one string and a change to classify()'s
# wording fails loudly instead of silently re-decoding every site.
NO_MOVX = classify([], skip=0)

# What `via` says when the site's own window resolved it and no branch was
# followed. Its own token rather than an empty cell: an empty `via` beside an
# empty `followed` is a row that has lost its own answer.
VIA_SITE = "at site"

# The `via` wording for a control transfer, as the two shapes the docstring
# names them. A function so the address is rendered the same way in every
# cell rather than at each call site.
VIA_FALLTHROUGH = "fall-through past {text} at 0x{pc:04X}"
VIA_JUMP = "{mn} target 0x{target:04X}"

# Stop reasons this file names itself, for the branches where there is no next
# address to continue at. A token `walk_why()` already owns (a budget, the end
# of the buffer, a DPTR reload) is passed through as that function wrote it, so
# one event has one spelling across both tools.
END_RET = "ret"
END_RETI = "reti"
END_INDIRECT = "indirect jump -- target not resolvable from the bytes"
END_HANDOFF = ("DPTR handed to a call -- classify() reports that as a handoff, "
               "and register_ref_table.py --callee-depth 1 resolves those")
END_UNFOLLOWED = "flow opcode this method does not know how to continue past"
END_UNREACHABLE = "target 0x{target:04X} is not reachable from region {region}"
END_LOOP = "loop back to 0x{pc:04X}"

# The bounds, as opposed to the shapes above: a walk that stopped at one of
# these has not seen everything after the cut, and a negative has to carry
# that. `ret` and a loop are not here, for walk_branch_arms.py's reasons -- a
# return is the end of the routine and a cycle has been fully walked. The two
# budget tokens are prefixes rather than whole strings, because one of them is
# written by `walk_why()` and not here.
CUTS = ("max_depth", "max_insns", END_INDIRECT, END_UNFOLLOWED, "target 0x")

COLUMNS = ("addr", "file_offset", "region", "runtime", "linear", "followed",
           "via", "max_depth", "max_insns", "insns", "ends", "window")


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


def depth_end(max_depth: int) -> str:
    """The token for a follow that used every transfer it was given.

    A function for the reason `trace_xdata_refs.budget_end()` gives: the
    number is the loop's own argument, and a reader looking at a
    `max_depth (4) exhausted` cell has to be able to see which 4 produced it."""
    return f"max_depth ({max_depth}) exhausted"


def is_cut(token: str) -> bool:
    """Whether this `ends` token says the walk stopped short.

    The depth token and `walk_why()`'s budget token both open with a name this
    module's `CUTS` holds, which is what lets one predicate serve a token
    written here and one written by `walk_why()` without either being restated
    as a constant."""
    return token.startswith(CUTS)


def continuation(d: bytes, insns, pd_verified: bool):
    """(next runtime address, `via` text) to continue at, or (None, reason).

    `insns` is the segment `walk_why()` just decoded, and the decision is made
    from its **last** instruction -- the control-flow opcode `walk()` stopped
    on. Taking the address of the branch from the decoded stream rather than
    from the site is what keeps the `0x9432` framing trap out of this file;
    see the docstring.

    The 2-byte paged forms need the address of the *next* instruction to name
    a page at all, and `paged_target()` takes the branch's own address and
    adds the instruction length itself, so what goes in is the runtime address
    the branch sits at.
    """
    i, raw, _ = insns[-1]
    op = raw[0]
    pc = runtime_addr(i, pd_verified)
    n = len(raw)
    # walk_why() renders mnemonics with no address, so the operand is the raw
    # displacement -- the same spelling the committed `window` columns carry,
    # which is what lets a `via` cell be matched against a table row.
    text = " ".join(mnemonic(d, i).split())
    if op == 0x22:
        return None, END_RET
    if op == 0x32:
        return None, END_RETI
    if op == 0x73:
        return None, END_INDIRECT
    if op == 0x80:                                   # sjmp: PC-relative
        target = relative_target(op, raw[-1], pc)
        return target, VIA_JUMP.format(mn="sjmp", target=target)
    if op == 0x02 or op & 0x1F == 0x01:              # ljmp / ajmp
        mn = "ljmp" if op == 0x02 else "ajmp"
        target = call_target(raw, pc)
        if target is None:
            return None, END_INDIRECT
        return target, VIA_JUMP.format(mn=mn, target=target)
    if op == 0x12 or op & 0x1F == 0x11:              # lcall / acall
        return None, END_HANDOFF
    if op in REL_OPCODES:                            # the conditional branches
        return (pc + n) & 0xFFFF, VIA_FALLTHROUGH.format(text=text, pc=pc)
    return None, END_UNFOLLOWED


class Follow:
    """One site's re-decode: the linear verdict, the followed one, and how."""

    def __init__(self, addr, off, region, rt):
        self.addr = addr
        self.off = off
        self.region = region
        self.rt = rt
        self.linear = ""            # classify()'s cell, verbatim
        self.followed = ""          # the flow-followed verdict
        self.anchor = []            # the site's own triples, for a caller's
                                    # `window` cell in the committed spelling
        self.via = []               # one entry per transfer followed
        self.ends = []              # why the follow stopped short
        self.insns = 0              # across every segment
        self.blocks = []            # (segment start, [(runtime, text)])

    def end(self, why: str) -> None:
        if why not in self.ends:
            self.ends.append(why)

    @property
    def redecoded(self) -> bool:
        """Whether this is one of the sites the follow looked at.

        False means `followed` and `linear` are the same string, and that is
        the structural half of the issue's "no count moves" guard rail: every
        bucket the committed tables carry is produced by `classify()` over the
        bytes `walk()` decoded, and none of that code changed."""
        return bool(self.via) or self.linear == NO_MOVX

    @property
    def resolved(self) -> bool:
        return self.followed != NO_MOVX

    @property
    def via_cell(self) -> str:
        return " ; ".join(self.via) if self.via else VIA_SITE

    @property
    def cuts(self):
        return [e for e in self.ends if is_cut(e)]

    @property
    def window(self) -> str:
        """Every segment's instructions, `|` between segments. A single flat
        list would read as a straight line through code that is not straight,
        which is the whole point of recording where the follow resumed."""
        return " | ".join(" ; ".join(f"0x{pc:04X} {t}" for pc, t in insns)
                          for _, insns in self.blocks)


def follow_site(d: bytes, addr: int, off: int, pd_verified: bool,
                max_depth: int = MAX_DEPTH, max_insns: int = MAX_INSNS) -> Follow:
    """Re-decode one site, and return both verdicts.

    The first segment is `walk()`'s own window at `WINDOW`, classified with
    `classify()`'s own `skip=1`: that is the committed `access` cell, and
    reproducing it here is what makes the `linear` column comparable with a
    committed table rather than with a second opinion. A site whose first
    segment already resolves is never walked again.

    Every later segment starts at the fall-through of a conditional or at an
    unconditional jump's target, and is classified with `skip=0` -- the first
    instruction at a fresh entry point is already an access, not the `mov
    dptr` that introduced the site.
    """
    region = region_of(off, pd_verified)[0]
    res = Follow(addr, off, region, runtime_addr(off, pd_verified))
    # The anchor counts as seen: a jump back to it would re-decode the same
    # window for the same verdict, and `seen` is about addresses decoded
    # rather than about block starts.
    at, follows, seen = off, 0, {off}
    while True:
        budget = WINDOW if not follows else max_insns
        insns, why = walk_why(d, at, budget)
        res.insns += len(insns)
        res.blocks.append((runtime_addr(at, pd_verified) or 0,
                           [(runtime_addr(i, pd_verified) or 0,
                             " ".join(mn.split()))
                            for i, _, mn in insns]))
        verdict = classify(insns) if not follows else classify(insns, skip=0)
        if not follows:
            res.linear = verdict
            res.anchor = insns
        # Whatever the last segment decoded is the row's verdict, so it is set
        # once here and every exit below keeps it -- including the ones that
        # stop, where it is the same `NO_MOVX` the linear column already says.
        res.followed = verdict
        if verdict != NO_MOVX:
            return res
        # The window stopped for a reason that is not a branch -- a budget, the
        # end of the buffer, a DPTR reload, an instruction that does not fit.
        # There is nothing to continue past, and `walk_why()`'s own token says
        # which, so the row carries a reason rather than a guess.
        if why != FLOW_END:
            res.end(why)
            return res
        nxt, via = continuation(d, insns, pd_verified)
        if nxt is None:
            res.end(via)
            return res
        noff = offset_for_runtime(nxt, region)
        if noff is None:
            res.end(END_UNREACHABLE.format(target=nxt, region=region))
            return res
        if noff in seen:
            res.end(END_LOOP.format(pc=nxt))
            return res
        if follows >= max_depth:
            res.end(depth_end(max_depth))
            return res
        seen.add(noff)
        res.via.append(via)
        at, follows = noff, follows + 1


def follow_rows(d: bytes, addrs, pd_verified: bool, max_depth: int = MAX_DEPTH,
                max_insns: int = MAX_INSNS):
    """One Follow per site of every address, in file order.

    `addrs` is a list of ints, as `register_ref_table.addresses()` yields them
    and `sites_for()` takes them; `main()` does the hex parsing, the way
    `trace_xdata_refs.csv_table()`'s caller does.

    Every site is returned, not only the ones re-decoded, so a caller can
    assert the untouched buckets come back unchanged -- the suite does, and
    that assertion is the point of the whole exercise."""
    out = []
    for addr in addrs:
        for off in sites_for(d, addr):
            out.append(follow_site(d, addr, off, pd_verified, max_depth, max_insns))
    return out


def follow_table(rows, max_depth: int, max_insns: int, redecoded_only: bool):
    """The `--csv` table, as a string so `--check` diffs the same bytes it
    prints.

    `redecoded_only` is on for the committed file, and it is not a way of
    hiding rows: a site that stops being `NO_MOVX` and a site that becomes
    `NO_MOVX` both change this table's row count, and `--check` is red either
    way. What it does leave out is the population the follow is not about --
    254 rows of `0x07D0`, of which eight are the measurement."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for r in rows:
        if redecoded_only and not r.redecoded:
            continue
        w.writerow([f"0x{r.addr:04X}", f"0x{r.off:05X}", r.region,
                    f"0x{r.rt:04X}" if r.rt is not None else "", r.linear,
                    r.followed, r.via_cell, max_depth, max_insns, r.insns,
                    "; ".join(r.ends), r.window])
    return buf.getvalue()


def check_table(generated: str, path: str) -> int:
    """Exit code for `--check`: 0 when this run reproduces `path` exactly.

    Read with `newline=""` for the reason `trace_xdata_refs.check_table()`
    gives -- the committed CSVs carry the csv module's own CRLF terminator, and
    universal-newline translation would report a difference on every run."""
    try:
        with open(path, newline="") as f:
            on_disk = f.read()
    except OSError as e:
        print(f"note: {e}", file=sys.stderr)
        return 1
    if generated == on_disk:
        print(f"{repo_path(path)}: this run reproduces it byte for byte "
              f"({generated.count(chr(10))} lines)")
        return 0
    print(f"note: {repo_path(path)} differs from what this run produced; the "
          "file is the product of the command on the page that names it, so "
          "regenerate rather than edit", file=sys.stderr)
    for line in difflib.unified_diff(on_disk.splitlines(), generated.splitlines(),
                                     "committed", "generated", lineterm="", n=0):
        print(line, file=sys.stderr)
    return 1


def load_recorded(path: str):
    """What the committed table actually records: its bounds and its addresses.

    Read for one purpose, the one `walk_budget_census.load_recorded_budgets()`
    reads it for: a `--check` that re-decodes a different population than the
    file holds would diff a different measurement against it and report a
    difference that says nothing. Both halves are refused rather than
    defaulted, because a default here is a `--check` that goes green against
    rows it never looked at -- at a bound it never reached, or at an address
    set that is a subset of the file's."""
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or not {"addr", "max_depth", "max_insns"} <= set(rows[0]):
        raise ValueError(f"{repo_path(path)} has no addr/max_depth/max_insns "
                         "columns; it is not a walk_flow_follow table")
    bounds = {(int(r["max_depth"]), int(r["max_insns"])) for r in rows}
    addrs = {int(r["addr"], 16) for r in rows}
    return bounds, addrs


def describe_addrs(addrs) -> str:
    return ", ".join(f"0x{a:04X}" for a in sorted(addrs))


def print_rows(rows, max_depth: int, max_insns: int) -> None:
    """The human form: one block per site, with the two verdicts side by side.

    Every site of the requested addresses is printed, not only the re-decoded
    ones, so the `none` rows are the exception a reader can see rather than
    the only thing the tool ever shows."""
    tally = collections.Counter()
    by_addr = collections.defaultdict(list)
    for r in rows:
        by_addr[r.addr].append(r)
    for addr in sorted(by_addr):
        group = by_addr[addr]
        print(f"0x{addr:04X}: {len(group)} direct MOV DPTR site(s)")
        for r in group:
            if not r.redecoded:
                tally["untouched (already classified at the site)"] += 1
                continue
            tally["resolved" if r.resolved else "still none"] += 1
            rt = f"0x{r.rt:04X}" if r.rt is not None else "runtime n/a"
            print(f"\n  file 0x{r.off:05X}  {r.region:<9} {rt}")
            print(f"    linear:   {r.linear}")
            print(f"    followed: {r.followed}")
            print(f"    via:      {r.via_cell}")
            print(f"    insns:    {r.insns} over {len(r.blocks)} segment(s), "
                  f"max_depth {max_depth}, max_insns {max_insns} per followed "
                  "segment")
            for end in r.ends:
                print(f"    ended:    {end}"
                      + ("  <- a bound: this is not everything after the cut"
                         if is_cut(end) else ""))
            for pc, insns in r.blocks:
                print(f"    -- segment 0x{pc:04X}")
                for at, text in insns:
                    print(f"      0x{at:04X}  {text}")
        print()
    print(f"{len(rows)} site(s): "
          + ", ".join(f"{k} {v}" for k, v in sorted(tally.items()))
          + ".")
    print("Only the `none` sites are re-decoded, so a `read`/`write`/`r+w`/"
          "`movc`/`jmp`/handoff cell is\nwhatever classify() said at the site "
          "and none of the committed tables can move. A `none`\nhere means "
          "'not found by this method', never 'absent' and never 'this site "
          "does not\naccess the register'; 0x07B9 is the standing "
          "counter-example. Nothing is measured on\nhardware.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: %(default)s)")
    ap.add_argument("addrs", nargs="*", help="hex addresses, e.g. 0x0768 0x043E 0x07D0")
    ap.add_argument("--max-depth", type=int, default=MAX_DEPTH,
                    help="control transfers to follow past the branch the site's "
                         f"own window stopped at (default: {MAX_DEPTH}; 0 "
                         "follows nothing and names the bound on every row)")
    ap.add_argument("--max-insns", type=int, default=MAX_INSNS,
                    help="instruction budget for each *followed* segment "
                         f"(default: {MAX_INSNS}, walk()'s own; the site's own "
                         f"window stays at walk()'s {WINDOW} whatever this is, "
                         "so the `linear` column is the committed cell)")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per re-decoded site on stdout instead of "
                         "the per-site decode")
    ap.add_argument("--all-sites", action="store_true",
                    help="with --csv, one row per site rather than per "
                         "re-decoded site; --check is always the re-decoded set")
    ap.add_argument("--check", nargs="?", const=FOLLOW_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: {repo_path(FOLLOW_CSV)}). "
                         "Needs the table's whole address set, not a subset: "
                         "with no addresses it re-decodes the ones the table "
                         "records, and with a partial list it refuses rather "
                         "than diff a partial run against the full table")
    args = ap.parse_args()

    # `--check` needs the whole address set, not a subset, or it diffs a
    # partial re-decode against the full table and reports the missing rows as
    # drift. Given no addresses of its own it takes them from the table, so
    # the error below can honestly name --check as the way out of it.
    addrs = [int(text, 16) for text in args.addrs]
    if args.check is not None:
        try:
            recorded_bounds, recorded_addrs = load_recorded(args.check)
        except (OSError, ValueError) as e:
            print(f"note: {e}", file=sys.stderr)
            return 1
        if not addrs:
            addrs = sorted(recorded_addrs)
        elif set(addrs) != recorded_addrs:
            print(f"note: {repo_path(args.check)} records "
                  f"{describe_addrs(recorded_addrs)} and this run asked for "
                  f"{describe_addrs(set(addrs))}; --check over a subset of "
                  "the addresses would diff a partial re-decode against the "
                  "whole table and call the missing rows drift",
                  file=sys.stderr)
            return 1
    elif not addrs:
        ap.error("give a firmware image and at least one address, or --check "
                 "to re-decode the addresses the committed table records")
    if args.max_depth < 0 or args.max_insns < 1:
        print("note: --max-depth is a count of transfers and may be 0; "
              "--max-insns is a count of instructions and has to be at least 1",
              file=sys.stderr)
        return 1

    d = open(args.firmware, "rb").read()
    off, magic = PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the annotations were written against", file=sys.stderr)
        return 1

    rows = follow_rows(d, addrs, pd_verified, args.max_depth, args.max_insns)

    if args.check is not None:
        if (args.max_depth, args.max_insns) not in recorded_bounds:
            have = ", ".join(f"max_depth {d0} / max_insns {i0}"
                             for d0, i0 in sorted(recorded_bounds))
            print(f"note: {repo_path(args.check)} records {have} and this run "
                  f"used max_depth {args.max_depth} / max_insns {args.max_insns}; "
                  "--check at bounds the file does not record would diff a "
                  "different measurement against it", file=sys.stderr)
            return 1
        return check_table(follow_table(rows, args.max_depth, args.max_insns, True),
                           args.check)

    if args.csv:
        sys.stdout.write(follow_table(rows, args.max_depth, args.max_insns,
                                      not args.all_sites))
        return 0

    print_rows(rows, args.max_depth, args.max_insns)
    return 0


if __name__ == "__main__":
    sys.exit(main())
