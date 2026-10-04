#!/usr/bin/env python3
"""Join the `0x086x` opcode sweep and the C-level census, site by site.

`ec/annotations/xdata-086x-dispatch.md` quotes two direction vocabularies for
the same address and had no way to say whether they contradict each other: the
opcode sweep behind §8, which counts a `MOV DPTR,#addr` and the `movx` after
it, and the decompiled-C census behind §3, which counts occurrences of the
address in the decompiled text. Different denominators, so the totals are
never comparable -- but the *direction* at one site is comparable, and a
hand-typed table is exactly the kind of prose no tool can see (#272).

So the correspondence is committed as data, one file per address --
`ec/annotations/xdata-0860-census-sites.csv` and one for every other address
the page sweeps, each found by `mapping_csv()` rather than listed here -- and
this holds each to the other two. It reads the sweep's `access` cell out of
`xdata-086x-dispatch-sites.csv`, the bucket out of the mapping, and the
occurrences out of the census itself --
`xdata_register_map.py`'s `load_index`, `load_symbols`, `occurrence_re`,
`strip_comments` and `classify`, never a re-grep, so the line numbers it
checks are the reader's line numbers and the buckets are the census's own. It
fails loudly on a mapped site whose two directions disagree, on a bucket
claimed where the census is structurally blind, on a citation that no longer
resolves or no longer classifies the way the map says, on an occurrence no
site accounts for or two sites account for between them, on per-bucket totals
that miss the committed `xdata-registers.csv` row, on a site that is in one of
the two files and not the other, and on a `census` cell in the sites table
that no longer says what the mapping row it restates says.

**The vocabulary, which is the whole content of the check.** The two methods
are not in conflict on any address of this page; they are in two languages:

| sweep classification | census bucket | verdict |
|---|----------------|---------|
| `read xN` | `read xM` | agree, for any `M >= 1` |
| `write xN` | `write xM` | agree |
| `read xN`, window ending in a call | `passed-to-call xM` | agree -- one instruction, two vocabularies |
| `DPTR handed to <call>`, or a `read xN` whose window is one bare `movx a,@dptr` | `address-taken xM` | agree -- one instruction, two vocabularies, and `address-taken` names no direction, so this is not a direction claim |
| `DPTR handed to <call>` | any bucket other than `address-taken` | **error** -- a bucket the decompile does not name cannot exist there, and `address-taken` is the one bucket it does name at a handoff |
| `read xN` or `write xN` | `no-occurrence` | **error** -- the sweep decoded an access the decompile does not name. `census-blind` is the row that says so, and it is *not* an error |
| `no movx found in the decoded window`, or a handoff | `no-occurrence` | agree -- nothing for either method to see |
| a bucket the sweep did not name, **at a site whose window ends at a conditional branch and which also has a row the sweep does name** | any | `window-cut` -- the sweep's decode stopped at the branch, so its `access` cell could not have seen this access. Neither method is wrong |
| `<direction> x1, DPTR from <helper>` | `dptr-from-callee` | **reported on its own** -- see below |
| any | `census-blind` | out of scope -- reported as blind, never as agreeing |
| any | `other-program` | out of scope -- reported as unchecked, never as agreeing |

**`census-blind`, and why it is a third outcome rather than a fourth verdict.**
At a site where the sweep decoded a `movx` and the decompile names no address,
neither method is wrong and the two cannot be joined: the sweep read the byte,
the C-level reader does not have a line for it. `0x1F01` has four `write x1`
sites and one occurrence between them, which is the shape at its starkest.
Reporting that as `agree` would be a claim neither method supports and
reporting it as a failure would be a claim about the decompiler's competence,
so it gets its own count in the summary line and is neither. What it is *not*
is evidence the byte is unused -- the sweep's `movx` is the evidence it is
used, and `no census occurrence` at such a site is a statement about the
C-level reader's vocabulary.

**`dptr-from-callee` is the row that was `agree` and was not.** A `movx`
whose DPTR a callee left behind (`trace_xdata_refs.py`'s `DPTR from` cell,
sourced from `callee_dptr_sites.py`) is a site the sweep's own `MOV DPTR` scan
cannot find, and the census cannot see it either -- Ghidra bound DPTR to its
pre-call value, so the decompiled C names some other address or none. Both
methods missing the same byte is not corroboration, and this tool used to
report it as agreement at the `0x0D31C` cell. It now has its own outcome,
counted separately on the summary line and never added to `agree`; a site in
that state that the sweep does not agree is still an error. A
`dptr-from-callee` site contributes to no bucket total either: the census sees
no occurrence there, so adding its zero to a bucket would be the tool
asserting a measured zero it does not have.

**A site may carry more than one mapping row, and this is the third shape.**
Three of `0x086B`'s clamp sites are one: the sweep's window decodes
`movx a,@dptr ; setb c ; subb a,#0x23 ; jc +0x03` and stops at the `jc`, so its
`access` cell records the read and not the `0x23` store after the branch,
while the decompile names both. The site needs a `read` row and a `write` row,
the join is still per-occurrence so both are checked, and the site counts once.
`verdict()` admits the extra bucket **only** where the window ends at a
*conditional* branch *and* the site also has a row the sweep's direction does
name -- so this cannot become a general way for a map to assert a bucket the
sweep contradicted. Both halves are narrow: a window that ends at a `ret` or an
`ljmp` stopped because the straight-line run ended, with no arm left for an
access to hide in, so an extra row there is an error like any other.

The counts are deliberately not compared per site. The sweep records one row
per `MOV DPTR`, and the `0x48`/`0x4C` chains re-read A without reloading
DPTR, so six C-level comparisons land on one sweep row: `2 + 6 + 6 = 14` reads
behind three `read x1` rows. The totals are compared instead, per bucket,
against the generated `xdata-registers.csv` row.

**What this does not check, which is as much of the point:**

  * *Whether either method is right.* Every verdict here is a statement about
    two readings of the same bytes agreeing or failing to join. Nothing in
    this file is evidence that the EC acts on a byte, that a store is acted
    on, or that a read returns anything.
  * *The PD-image sites.* `other-program`: the two programs have separate
    XDATA maps and the census's `0x0860` row is `main-ec`, so a direction for
    those bytes is a category error, not a missing measurement. The census is
    still scanned for occurrences, so a PD occurrence appearing one day would
    be reported as unaccounted rather than quietly ignored.
  * *The prose.* This reads three CSVs and the decompile; it cannot see a
    sentence in `xdata-086x-dispatch.md`, and the page's own §9 says so. The
    same gap `check_cluster_citations.py` concedes. **Corrected 2026-09-25
    (issue #801): that is still true of this tool and no longer true of the
    tree.** `check_citation_lines.py` reads the page's site table, its
    `xdata-registers.csv:NNN` cells and the `HAND_CHECKED["0x0860"]` comment,
    and holds them to the two CSVs this tool already joins -- so the *line
    numbers the prose repeats* are now checked, for the two units named in its
    `ROW_SCOPE`. What remains true is the first half: this tool still cannot
    read a sentence, and a claim the prose makes about a direction is not
    checked by anything. `docs/findings/prose-line-citations-held.md` says which
    of the prose's cells are covered and which are held by nothing.
  * *The sweep's blind spot.* A byte reached through a computed DPTR, a
    register-indirect access or a table lookup has no site here, and a site
    the decompiler folded a `MOV DPTR` out of -- `0x0D31C` -- looks identical
    to one the firmware never touches. `no census occurrence` is not evidence
    that the site is unused, and neither is `census-blind`. **Corrected
    2026-10-03 (issue #799): the second half of that used to be the whole of
    it, and the first sentence described only one of the two ways a site goes
    missing here.** A DPTR loaded by a **callee** was the other way, and it is
    worse than the folded `MOV DPTR`, because there the sweep at least had a
    site and only the census was silent -- here neither method has one.
    `callee_dptr_sites.py` resolves it from the `.asm`, its table feeds the
    sweep's `DPTR from` cell under `--callee-column`, and the
    `dptr-from-callee` state above is how the correspondence records the
    result. What is still not established is anything behind that: an
    unresolved row in that table is "not found by this method" in exactly the
    way this bullet describes, and `callee_dptr_sites.py` reports how many
    `movx` it could not place rather than leaving the set to read as a census.
  * *How many `census-blind` sites there are across the tree.* This reads the
    addresses the `0x086x` page sweeps and the decompiled functions covering
    them, and `census-blind` says the C-level reader named no address
    at a site where the sweep decoded one. It does not say how many such sites
    exist where no sweep site exists at all, which is a different question and
    an open one (`xdata-086x-dispatch.md` §11's last numbered item). The same
    goes for `dptr-from-callee`: the correspondence tables for `0x0860`,
    `0x0867` and `0x0868` record it, and the page addresses with no sweep row
    and the tree-wide version are separate.

Usage:
    python3 check_site_census.py [--address ADDR | --all] [--verbose]
"""
import argparse
import collections
import csv
import os
import sys

from xdata_register_map import (BUCKETS, DECOMPILED, classify, load_index,
                                load_symbols, occurrence_re, strip_comments)

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
SITES_CSV = os.path.join(EC, "annotations", "xdata-086x-dispatch-sites.csv")
ANNOT = os.path.join(EC, "annotations")
REGISTERS_CSV = os.path.join(EC, "annotations", "xdata-registers.csv")

# The address checked when neither switch is given. It is the one the page's
# §3 per-site table is written from and the one whose nine rows §3's
# corrections are pinned against, so a bare run keeps saying what it said.
ADDRESS = "0x0860"

# The addresses the page's §1 sweeps, which is the run whose --csv output is
# the committed sites table. Read out of that table rather than
# listed here, so an address added to the sweep is checked by `--all` without
# this file being edited -- the same "scan, never list" shape
# `trace_xdata_refs.committed_terminator_tables()` uses for the other three
# committed tables.
def page_addresses(path: str = SITES_CSV) -> list:
    seen = []
    for row in read_csv(path):
        if row["addr"] not in seen:
            seen.append(row["addr"])
    return seen


def mapping_csv(addr: str = ADDRESS) -> str:
    """The correspondence file for one address.

    Spelled the way `csv_table()` spells the address in its own `addr` column,
    so a file is found by the same string that identifies it in the sweep. A
    missing file is an `OSError` from `open()` rather than a default path: a
    second copy of this tool per address is what the docstring above rules
    out, so "no file" has to be loud rather than become an empty join."""
    return os.path.join(ANNOT, f"xdata-{addr[2:]}-census-sites.csv")


MAPPING_CSV = mapping_csv(ADDRESS)

# What a non-mapped row carries, per state, so "the census cannot see this
# site" is one shape, "the sweep cannot find this site" is a second, "a
# different program's byte" is a third, and "the sweep saw an access the
# C-level reader does not name" is a fourth. `na` is not a measured zero: the
# register row for the address is `main-ec`, so no count is established for a
# PD site at all. `0` is, for `census-blind` and `dptr-from-callee`: the sweep
# decoded an access, so this is a claim about the C-level reader and the count
# it does not carry is a measured absence of occurrences, not of accesses --
# and for `dptr-from-callee` the census is not looking at another program's
# map, it looked and found no occurrence because the decompile bound DPTR
# elsewhere.
BLIND = {"no-occurrence": "0", "other-program": "na", "census-blind": "0",
         "dptr-from-callee": "0"}

# trace_xdata_refs.classify()'s own spellings, read back off the committed
# `access` cell rather than re-run: the sweep's half of the join is the
# committed table, because that is the thing a reader is being shown.
HANDOFF = "DPTR handed to "
# Held here rather than read off `trace_xdata_refs.DPTR_FROM`, which is
# imported lazily below so this module's own import cost stays where it was.
# The two spellings have to be the same string; `test_check_site_census.py`
# pins that, which is the check that a hand-kept duplicate needs.
DPTR_FROM = "DPTR from "
NO_MOVX = "no movx found in the decoded window"
CODE_POINTER = "CODE pointer"

# The call and tail-call forms a window can end in. `movx a,@dptr ; lcall
# 0x7151` is the single instruction the two vocabularies disagree about, and
# the row above is the only place they are allowed to.
CALL_TAIL = ("lcall", "acall", "ljmp", "ajmp")

# Every mnemonic `walk_why()` can stop on: the decode reached control flow and
# stopped there.
#
# **Listed by name and not derived from `disasm8051.FLOW_OPCODES`.** Deriving
# it renders each opcode through `mnemonic()`, and three members of that set
# (`0xB6`, `0xB7`, `0xC1`) render as `db`/`clr` because the mnemonic table has
# no entry for them -- an artefact of the renderer, not names any listing
# carries, and importing it would put two mnemonics in this tuple that no
# window can end in. `test_check_site_census.py` pins this tuple against
# `FLOW_OPCODES` minus those three, so it cannot quietly fall behind the table.
FLOW_TAIL = CALL_TAIL + ("cjne", "djnz", "jb", "jbc", "jc", "jnb", "jnc",
                         "jnz", "jz", "jmp", "ret", "reti", "sjmp")

# **The subset of those a window can end in with an access still hidden behind
# it -- the conditional branches, and nothing else.** This is not the same
# question `FLOW_TAIL` answers, and `ends_in_branch()` below asks this one.
#
# A window that stops at `ret`, `reti`, `sjmp`, `ljmp` or `jmp @a+dptr` stopped
# because the straight-line run *ended*: there is no fall-through arm, so the
# instruction after it cannot execute and no access can hide there. Committed
# windows do end at a `ret`, and admitting an extra bucket at one of those would
# let a map assert a `write` the sweep read as nothing but a read, with nothing
# in the window to explain it. The call forms are excluded for the same reason
# `CALL_TAIL` exists separately: after an `lcall` returns, the walk would have
# carried on, so the decode gave up there rather than being diverted.
#
# `test_check_site_census.py` pins this tuple as exactly the members of
# `FLOW_TAIL` the decoder stops on that are conditional, so it cannot drift
# wide again, and pins a `ret`-terminated extra row as an error.
BRANCH_TAIL = ("cjne", "djnz", "jb", "jbc", "jc", "jnb", "jnc", "jnz", "jz")


def repo_path(path: str) -> str:
    """`path` relative to the repository root, for the messages below."""
    return os.path.relpath(path, REPO)


def sweep_direction(access: str):
    """The direction one `access` cell claims, or None if it claims none of
    the ones the table above can compare. `read+write` is its own answer
    rather than two, so a site the sweep calls both is not silently read as
    a read and made to agree with a `read` bucket.

    `DPTR from` is tested before the `read xN`/`write xN` substrings because a
    callee-set cell carries one of them: `write x1, DPTR from 0xD319` is a
    write the census cannot corroborate, not a write it can. Reading it as a
    plain `write` is the failure the `dptr-from-callee` state exists to stop.
    """
    if access.startswith(HANDOFF):
        return "handoff"
    if access == NO_MOVX:
        return "no-movx"
    if DPTR_FROM in access:
        return "callee-dptr"
    if CODE_POINTER in access:
        return "code-pointer"
    reads, writes = "read x" in access, "write x" in access
    if reads and writes:
        return "read+write"
    if reads:
        return "read"
    if writes:
        return "write"
    return None


def ends_in_call(window: str) -> bool:
    """True when a window's last instruction is a call, i.e. the value the
    sweep read is on its way into a subroutine. The window is the `;`-joined
    mnemonic text of the committed `window` cell."""
    tail = window.rsplit(" ; ", 1)[-1].strip()
    return bool(tail) and tail.split(" ")[0] in CALL_TAIL


def ends_in_branch(window: str) -> bool:
    """True when a window's last instruction is a *conditional* branch.

    This is what makes an extra row at one site checkable rather than a
    promise. `0x086B`'s three clamps decode `movx a,@dptr ; setb c ; subb
    a,#0x23 ; jc +0x03` and stop at the `jc`, so the sweep's `access` cell
    records the read and the `0x23` store after the branch is not in it --
    while the decompile names both. A conditional branch is the only tail with
    an arm the walk cannot reach, so the window ending in one is the evidence
    that the sweep could not have seen the extra row.

    Deliberately not `FLOW_TAIL`, which is the wider question of what the
    decode stops on: a window ending at a `ret` or an `sjmp` also stopped on
    control flow, but with no fall-through arm, so nothing can be behind it and
    an extra row there is a disagreement the map is asserting."""
    tail = window.rsplit(" ; ", 1)[-1].strip()
    return bool(tail) and tail.split(" ")[0] in BRANCH_TAIL


def is_bare_read(window: str) -> bool:
    """True when the whole window is one `movx a,@dptr` and nothing else.

    This is the narrow half of the `address-taken` row in the table above.
    `movx a,@dptr` on its own is the encoding of "load the byte's address for
    someone else to use", which is what `&XDATA_0866` in the decompile is:
    Ghidra has turned the load into a pointer. A window with anything after
    it -- a compare, a subtract, a call -- is the sweep reporting what it did
    with the byte, and `address-taken` against that window would be a
    disagreement rather than a second reading of one instruction. Named
    rather than inlined into the comparison so the narrowness is one readable
    predicate."""
    return window.strip() == "movx a,@dptr"


def verdict(sweep: str, state: str, bucket: str, call_tail: bool,
            bare_read: bool = False, branch_tail: bool = False,
            second_row: bool = False) -> str:
    """"agree", "callee-dptr", "error", "unchecked", "blind" or "window-cut"
    for one row, per the table above.

    Order matters: the structural cases are decided before the bucket is
    looked at, because a bucket the census cannot support is an error whatever
    the sweep says.

    `bare_read` is what admits the `address-taken` row against a plain read and
    `branch_tail` is what admits an extra row at one site; without them those
    pairs are errors, and the caller's tests pin both.

    **`second_row` is the load-bearing half of `branch_tail`, and it means "this
    site has a row the sweep's direction *does* name", not "this row is not
    first".** The caller computes it from the site's rows rather than from the
    row's position, because a map can order its rows either way and a check
    keyed on position would admit a site whose *only* row contradicts the sweep
    as soon as that row was written second. Requiring a sibling row that agrees
    is what makes this a surplus-access allowance: at least one row has to
    match what the sweep decoded, and only what is left over can be behind the
    branch. A site with no agreeing row is an error, which is what keeps `read`
    against `write` a failure on the `0x0860` shape it was written for."""
    if state == "other-program":
        return "unchecked"
    if state == "census-blind":
        # The sweep decoded an access and the decompile names no address. Its
        # own outcome: not agreement, not a failure. Claiming a bucket here is
        # the caller's bucket check, which rejects it.
        return "blind" if sweep not in (None, "no-movx", "handoff",
                                        "code-pointer", "callee-dptr") else "error"
    if state == "dptr-from-callee":
        # Both methods missing the same byte is not one method's answer, and
        # `agree` was the word that made it read as one. This gets its own
        # outcome, in both directions: the map says the sweep found the site
        # through a callee and the sweep's own cell does not say so, and that
        # is a disagreement like any other.
        return "callee-dptr" if sweep == "callee-dptr" else "error"
    if state == "no-occurrence":
        # Nothing to compare and nothing claimed. A window the sweep found no
        # `movx` in and a handoff the decompile names no address for are the
        # same shape -- the 0x0D31C one and its counterpart -- and both agree.
        # The caller's bucket check is what rejects a bucket claimed here.
        return "agree" if sweep in ("no-movx", "handoff") else "error"
    if bucket == "address-taken":
        # `address-taken` names no direction, so it cannot disagree with one.
        # It is admitted only where the sweep's own cell says the byte went
        # somewhere rather than what was done with it: a handoff, or a window
        # that is one bare `movx a,@dptr` and so is the encoding of an address
        # being taken. Anywhere else it is an error, and `0x0866`'s three
        # `&XDATA_0866` lines are the rows that say so.
        if sweep == "handoff" or (sweep == "read" and bare_read):
            return "agree"
        return "error"
    if second_row and branch_tail and sweep != bucket:
        # The sweep's window stopped at a conditional branch before this
        # access, so its `access` cell could not have named it. Its own
        # outcome: neither agreement nor a failure, because neither method is
        # wrong.
        return "window-cut"
    if sweep == "handoff":
        # Mapped, so a bucket is claimed, and DPTR went to a call that named no
        # address in the decompile. An occurrence cannot exist there.
        return "error"
    if sweep == "callee-dptr":
        # The sweep found the site through a callee and the map does not say
        # so, which would leave the site out of the per-bucket totals as well.
        return "error"
    if sweep == "no-movx" or sweep in (None, "code-pointer"):
        return "error"
    if bucket == "passed-to-call":
        return "agree" if sweep == "read" and call_tail else "error"
    return "agree" if sweep == bucket else "error"


def read_csv(path: str):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def sweep_sites(path: str = SITES_CSV, addr: str = ADDRESS) -> dict:
    """file_offset -> row, for one address's sites in the committed sweep.

    Keyed on `file_offset` rather than `runtime`: a bank window maps the same
    file offset to a different runtime address per bank, and the mapping is
    about bytes."""
    return {r["file_offset"]: r for r in read_csv(path) if r["addr"] == addr}


def parse_refs(text: str) -> list:
    """[(out_file, line), ...] for a `bank0/D091.c:43,47` cell, or for a
    `bank0/D289.c:19;bank0/D28E.c:19` cell.

    Line numbers are the reader's, because strip_comments() keeps every
    newline. The `;` separator is not decoration: `clear_0860`'s decompiled
    body runs on into the `copy_0866_86b_to_1c04_1c3a` block at `0xD28E`, so
    one store is named in two `.c` files and the census counts both. A cell
    that can only name one file would have to drop one, and the per-bucket
    total would then miss `xdata-registers.csv` -- so the cell carries both and
    the citation check below visits each."""
    out = []
    for group in text.split(";"):
        where, _, lines = group.partition(":")
        out.extend((where, int(n)) for n in lines.split(","))
    return out


def census_occurrences(addr: str = ADDRESS) -> dict:
    """{(out_file, line): [bucket, ...]} for every C-level occurrence of
    `addr` in the decompiled tree, one entry per occurrence so a line holding
    three comparisons counts three. The census is reused rather than re-grepped
    so the buckets are the ones `xdata-registers.csv` was generated from."""
    funcs, by_file = load_index()
    symbols = load_symbols()
    pattern = occurrence_re(symbols)
    by_name = {name: value for value, name in symbols.items()}
    func_names = {row["name"] for row in funcs.values()}
    out = collections.defaultdict(list)
    for out_file in by_file:
        with open(os.path.join(DECOMPILED, out_file)) as f:
            text = strip_comments(f.read())
        for m in pattern.finditer(text):
            value = (int(m.group(1), 16) if m.group(1) is not None
                     else by_name[m.group(2)])
            if value == int(addr, 16):
                line = text.count("\n", 0, m.start()) + 1
                out[(out_file, line)].append(
                    classify(text, m.start(), m.end(), m.group(0), func_names))
    return dict(out)


def register_buckets(path: str = REGISTERS_CSV,
                     addr: str = ADDRESS) -> tuple:
    """({bucket: count}, refs) for one address, read out of the generated
    census rather than re-derived. This is the point of reading it: the
    mapping's per-bucket sums are hand-typed, and this is the number they have
    to equal, so a hand-typed number that drifts fails instead of reading as
    agreement."""
    for row in read_csv(path):
        if row["addr"] == addr:
            return ({b: int(row[b]) for b in BUCKETS}, int(row["refs"]))
    raise KeyError(f"{repo_path(path)} has no row for {addr}")


def check(sites: dict, rows: list, occurrences: dict, expected: tuple,
          verbose=False, addr: str = ADDRESS) -> tuple:
    """(problems, agreed, unchecked, blind, cut, callee_dptr, sites) over the
    three committed inputs.

    Every clause is a disagreement between a hand-typed correspondence and
    something derived -- the sweep's own `access` cell, the census's own
    classification of the cited lines, and the census's own totals. Passing
    means those three agree; it does not mean either method is right about the
    firmware.

    `sites` in the result is the number of sweep sites the run accounted for,
    not the number of mapping rows: a site the sweep's window truncated at a
    conditional branch carries two rows (the access it decoded and the one
    behind the branch), and the summary line counts it once. `cut` counts the
    second of those rows, so it is a count of rows where `sites` is a count of
    places. `callee_dptr` is counted apart from `agreed` precisely because
    neither method saw those bytes at all."""
    buckets, refs_total = expected
    mapping = mapping_csv(addr)
    problems = []
    agreed = unchecked = blind = cut = callee_dptr = 0

    # The join in both directions, before anything is compared: a site in one
    # file and not the other is a visible mismatch rather than a silent one.
    # Keyed on (offset, bucket), so two rows at one offset are the documented
    # shape rather than a duplicate -- but two rows at one offset *in one
    # bucket* are still a duplicate, and two rows for one occurrence are
    # caught below by `accounted`.
    mapped = {}
    for row in rows:
        offset = row["file_offset"]
        if offset not in sites:
            problems.append(f"{offset}: in {repo_path(mapping)} but the "
                            f"sweep has no {addr} site there")
            continue
        if row["region"] != sites[offset]["region"]:
            problems.append(f"{offset}: mapped as {row['region']!r}, the sweep "
                            f"says {sites[offset]['region']!r}")
        key = (offset, row["census_bucket"])
        if key in mapped:
            problems.append(f"{offset}: two rows for bucket "
                            f"{row['census_bucket']!r} in {repo_path(mapping)}")
            continue
        mapped[key] = row
    for offset in sites:
        if not any(k[0] == offset for k in mapped):
            problems.append(f"{offset}: a {addr} site in "
                            f"{repo_path(SITES_CSV)} with no row in "
                            f"{repo_path(mapping)}")
    if problems:
        # Nothing below can mean anything until both files describe the same
        # set of sites, and a report that mixes "disagrees" with "no row" is
        # harder to read than the first real failure.
        return problems, 0, 0, 0, 0, 0, 0

    accounted = collections.Counter()
    totals = collections.Counter()
    seen_sites = set()
    # Per site, whether any row carries the direction the sweep decoded. This
    # is `verdict()`'s `second_row`, computed here because it is a property of
    # the site's rows and not of the row being judged -- see its docstring.
    sweep_of = {offset: sweep_direction(sites[offset]["access"])
                for offset in sites}
    agrees = {offset: any(row["census_state"] == "mapped"
                          and row["census_bucket"] == sweep_of[offset]
                          for (off, _), row in mapped.items() if off == offset)
              for offset in sites}
    for (offset, _), row in mapped.items():
        state, bucket = row["census_state"], row["census_bucket"]
        site = sites[offset]
        seen_sites.add(offset)
        where = f"{offset} ({state}/{bucket})"
        sweep = sweep_of[offset]

        if state == "mapped":
            if bucket not in BUCKETS:
                problems.append(f"{where}: census_bucket {bucket!r} is not one "
                                f"of the census's {', '.join(BUCKETS)}")
                continue
            try:
                count = int(row["census_count"])
            except ValueError:
                problems.append(f"{where}: census_count {row['census_count']!r} "
                                "is not a number")
                continue
            if count < 1:
                problems.append(f"{where}: a mapped site carries "
                                f"census_count {count}; a site the census "
                                "cannot see is state 'no-occurrence', not a "
                                "mapped row with a zero")
                continue
            if row["census_refs"] == "none":
                problems.append(f"{where}: mapped, but census_refs names no "
                                "line -- a mapped site without a citation is "
                                "unverifiable, not corroborated")
                continue
            totals[bucket] += count
        else:
            if state not in BLIND:
                problems.append(f"{where}: census_state {state!r} is not one of "
                                f"'mapped', {', '.join(repr(s) for s in BLIND)}")
                continue
            if bucket != "none" or row["census_count"] != BLIND[state]:
                problems.append(f"{where}: the census is structurally blind "
                                "here, so census_bucket/census_count must be "
                                f"'none'/'{BLIND[state]}' and are "
                                f"{bucket!r}/{row['census_count']!r}")
                continue
            if row["census_refs"] != "none":
                problems.append(f"{where}: census_refs names "
                                f"{row['census_refs']!r} on a site the census "
                                "is blind to -- a claim with no occurrence "
                                "behind it")
                continue

        how = verdict(sweep, state, bucket, ends_in_call(site["window"]),
                      is_bare_read(site["window"]), ends_in_branch(site["window"]),
                      agrees[offset])
        if how == "unchecked":
            unchecked += 1
            if verbose:
                print(f"  unchecked {where}: sweep says "
                      f"{site['access']!r}, out of scope here", file=sys.stderr)
            continue
        if how == "callee-dptr":
            # Counted and named, and then left out of `agreed` and out of every
            # bucket total below -- the census has no occurrence here, so adding
            # its zero to a bucket would be this tool asserting a measured zero
            # it does not have.
            callee_dptr += 1
            if verbose:
                print(f"  callee-dptr {where}: the sweep's own cell says "
                      f"{site['access']!r}, so neither method saw the decompile "
                      "at this address", file=sys.stderr)
            continue
        if how == "blind":
            blind += 1
            if verbose:
                print(f"  blind {where}: sweep decoded "
                      f"{site['access']!r} and the decompile names no address "
                      "there", file=sys.stderr)
            continue
        if how == "window-cut":
            # Counted and named, and then checked like any other mapped row --
            # its citations still have to resolve and still have to classify
            # the way the map says, and its occurrences still have to be
            # accounted for exactly once. Not continuing here is deliberate: a
            # `window-cut` row that carried a stale line would otherwise be
            # invisible, which is the one thing a third outcome must not be.
            cut += 1
            if verbose:
                print(f"  window-cut {where}: the sweep's window stopped at "
                      f"{site['window'].rsplit(' ; ', 1)[-1]!r}, before this "
                      "access", file=sys.stderr)
        elif how == "error":
            problems.append(f"{where}: the sweep says {site['access']!r} and "
                            f"the map says bucket {bucket!r}; "
                            + ("a handoff names no direction, so any bucket "
                               "here but address-taken cannot exist"
                               if sweep == "handoff" and
                               bucket != "address-taken" else
                               "one of the methods found this site through a "
                               "callee's DPTR and the other does not know of "
                               "it, and the table in this tool's docstring is "
                               "the only set of pairs allowed to agree"
                               if sweep == "callee-dptr" else
                               "the two methods disagree, and the table in "
                               "this tool's docstring is the only set of pairs "
                               "allowed to agree"))
            continue
        else:
            agreed += 1

        if state != "mapped":
            continue
        # The citation itself: does it still resolve, and does the census's
        # own classify() still put it in the bucket the map claims?
        seen = 0
        try:
            refs = parse_refs(row["census_refs"])
        except ValueError as e:
            problems.append(f"{where}: census_refs {row['census_refs']!r} does "
                            "not parse as 'file.c:line[,line]' groups "
                            f"separated by ';' ({e})")
            continue
        for ref in refs:
            accounted[ref] += 1
            if ref not in occurrences:
                problems.append(f"{where}: census_refs cites {ref[0]}:{ref[1]}, "
                                f"where the census has no {addr} occurrence "
                                "-- the line moved, or the reference was dropped")
                continue
            seen += len(occurrences[ref])
            found = set(occurrences[ref])
            if found != {bucket}:
                problems.append(f"{where}: census_refs cites {ref[0]}:{ref[1]}, "
                                f"which the census classifies "
                                f"{', '.join(sorted(found))} and the map claims "
                                f"{bucket}")
        if seen != int(row["census_count"]):
            problems.append(f"{where}: census_count says {row['census_count']} "
                            f"and the cited lines hold {seen}")

    for ref, times in sorted(accounted.items()):
        if times > 1:
            problems.append(f"{ref[0]}:{ref[1]}: {times} mapped rows cite this "
                            "occurrence; the correspondence splits one "
                            "occurrence between sites")
    for ref in sorted(set(occurrences) - set(accounted)):
        problems.append(f"{ref[0]}:{ref[1]}: a {addr} occurrence no mapped "
                        "row accounts for")

    for bucket in BUCKETS:
        if totals.get(bucket, 0) != buckets[bucket]:
            problems.append(f"per-bucket totals: the map sums {bucket} to "
                            f"{totals.get(bucket, 0)} where "
                            f"{repo_path(REGISTERS_CSV)} says {buckets[bucket]}")
    if sum(totals.values()) != refs_total:
        problems.append(f"per-bucket totals: the map sums {sum(totals.values())} "
                        f"where {repo_path(REGISTERS_CSV)} says refs {refs_total}")
    return problems, agreed, unchecked, blind, cut, callee_dptr, len(seen_sites)


def check_cells(sites: dict, cells: dict) -> list:
    """The sweep's own `census` cell, held to what the mapping says.

    `trace_xdata_refs.load_census_map()` renders the column from the mapping
    files, so a `census` cell in `xdata-086x-dispatch-sites.csv` that no longer
    matches the row it restates is a column that has drifted from its source --
    and a cell that reads `not recorded` where the mapping has a row is a cell
    that reads as agreement about a join nobody recorded. Compared rather than
    regenerated, so this is a check and not a second writer of the table."""
    return [f"{offset}: the sites table says {site['census']!r} where the "
            f"mapping says {cells.get(offset, 'nothing')!r}"
            for offset, site in sorted(sites.items())
            if site.get("census") != cells.get(offset)]


def check_address(addr: str, verbose=False) -> tuple:
    """(problems, line, counts) for one address: the join, then the summary
    line and the numbers it was built from.

    The cell clause runs whether or not the join passed, because a drifted
    column is worth reporting even on an address whose mapping is also wrong --
    and it is the only clause that can see the column at all. `counts` is
    returned rather than parsed back out of `line`, so `--all`'s page total is
    arithmetic on the run's own numbers and not on a string."""
    import trace_xdata_refs

    mapping = mapping_csv(addr)
    sites = sweep_sites(addr=addr)
    rows = read_csv(mapping)
    occurrences = census_occurrences(addr)
    expected = register_buckets(addr=addr)
    problems, agreed, unchecked, blind, cut, callee_dptr, site_count = check(
        sites, rows, occurrences, expected, verbose, addr)
    problems = problems + check_cells(
        sites, trace_xdata_refs.load_census_map(mapping))
    if problems:
        return problems, "", {}
    total = sum(expected[0].values())
    counts = " ".join(f"{b} {expected[0][b]}" for b in BUCKETS)
    line = (f"{addr}: {agreed} of {site_count} site(s) agree across both "
            f"methods, {blind} blind to the decompile, {cut} behind a branch "
            f"the sweep's window stopped at, {callee_dptr} found only through "
            f"a callee's DPTR and counted in no bucket, {unchecked} unchecked "
            f"(other program), {total} occurrence(s) accounted for once each "
            f"-- {counts}, refs {expected[1]}")
    return [], line, {"sites": site_count, "occurrences": total}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--address", metavar="ADDR",
                       help=f"check one address's correspondence file "
                            f"(default: {ADDRESS})")
    group.add_argument("--all", action="store_true",
                       help="check every address the 0x086x page's sweep "
                            "covers, and print a page total")
    ap.add_argument("--verbose", action="store_true",
                    help="name the sites reported as unchecked, blind or "
                         "callee-set, not only the ones that fail")
    args = ap.parse_args()

    addresses = page_addresses() if args.all else [args.address or ADDRESS]

    failed, lines, page = 0, [], collections.Counter()
    for addr in addresses:
        try:
            problems, line, counts = check_address(addr, args.verbose)
        except (OSError, KeyError) as e:
            failed += 1
            print(f"check_site_census.py: {addr}: {e}", file=sys.stderr)
            continue
        for problem in problems:
            print(f"check_site_census.py: {problem}", file=sys.stderr)
        if problems:
            failed += 1
            print(f"check_site_census.py: {len(problems)} disagreement(s) for "
                  f"{addr} between {repo_path(SITES_CSV)}, "
                  f"{repo_path(mapping_csv(addr))} and the census",
                  file=sys.stderr)
            continue
        lines.append(line)
        page.update(counts)

    for line in lines:
        print(line)
    # The page total is a measurement over the committed firmware and the
    # committed decompile, not a count of this repository's own text, so it is
    # the kind of figure CLAUDE.md allows stated once, beside its command.
    if args.all and not failed:
        print(f"page: {page['sites']} site(s) over {len(lines)} address(es), "
              f"{page['occurrences']} occurrence(s) accounted for once each")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
