#!/usr/bin/env python3
"""Work out which routine each decompiled `.c` actually decompiles.

`ec/decompiled/index.csv` records one row per *export*, and the exporter cut
`bank1:0x8001`-`0x8189` into 42 of them -- 16 a single instruction -- whose
`sizes` sum to 393, the length of the run. Every one of those 42 `.c` files
decompiles that same routine, not its own bytes: 16 to 47 statements each, every
member scoring 0.87 to 0.98 containment against the owner's 47
(annotations/xdata-06c2-06db-timers.md 2, and the `body_lines` and
`containment` columns of the committed map). So `xdata_register_map.py`'s
`scan()`, which walks the index one row at a time and adds
`entry["refs"] += 1` per token per file, counts that one routine 42 times:
0x0843 reads 168 references where the routine is read 4 times, and 0x0843 is
42 `funcs` entries deep.

The root cause is the function boundary, and fixing it needs
`--mode rebuild-project` and a database write that cannot share a branch
(annotations/xdata-06c2-06db-timers.md 8 item 7). This is the measurement the
boundary fix is argued from, and it is deliberately **not** a boundary fix.

**The rule.** Strip the plate comment, the signature and the braces; split what
is left on `;`; whitespace-collapse each statement; the result is the file's
body, a *set*. Two files in the same program are in one containment class when
the smaller body's statements are at least `THRESHOLD` of the way into the
larger one. Classes are the connected components of that relation, and each
class has exactly one **owner**: its largest body, ties broken by the lowest
`index.csv` address. On this tree the 42-file class's owner is
`bank1/8001.c`, which is what keeps every `bank1:0x8001` citation in the tree
true.

`--fold-equal` is the one other grouping the page measured: bodies that are
*exactly* equal, which strict containment cannot group because neither is
strictly larger. The committed map is the strict-subset derivation.

**`MIN_BODY_STMTS` is not a tuning knob, it is the false-positive guard.** At
0.90 a one-statement body is contained by any larger body that happens to
spell that one statement, and 1,272 of the tree's 2,710 bodies are two
statements or fewer -- 494 of them a single statement, 426 of those naming
`return` and 111 exactly `return`. Left unguarded those fragments chain a whole
program together: on this tree a floor of 1 produces a **562-member** class of
`bank1` files, 155 of them the fragments above, whose two largest members --
78 and 67 statements -- hold a containment score of **1.5%** of the smaller,
and folding it would silently drop 561 routines out of the census. At 3 the
largest such chain is 7 classes, all of them small, and the 42-class is
unchanged by the floor. Every figure here is `--self-test`'s oracle, re-derived
there rather than quoted here.

**A class is a connected component, and that is a real limitation rather than
a detail.** Containment does not compose: A inside B and B inside C does not
make A inside C, so a member may reach its owner only through a chain of
intermediates rather than being contained by it directly. The `containment`
column records each member's own score *against its owner*, so a member that
is 0.43 similar to the 14-statement body it belongs with is visible in the
committed CSV instead of hidden inside the grouping.

**`containment` cannot tell a copy from a fragment, so the size runs the other
way too.** It is `|A & B| / |A|` with `A` the *smaller* body, so a four-statement
stub scores `1.00` against any larger body that happens to spell those four
statements -- the score of a copy and the score of a fragment are the same
number, and `MIN_BODY_STMTS` does not separate them because it is a floor and
the cases are four to six statements. `member_share` divides the same two
bodies by the other side: `|A| / |B|`, how much of the *owner* the non-owner
accounts for, which is the ratio `containment`'s direction normalises away.
A re-export of one routine scores near `1.00` on both; the three timer stubs
score `1.00` and `0.18`. `owner_body_lines` is carried beside it so
the ratio is checkable against the two bodies it came from rather than taken
on trust.

**`--min-share` is that ratio as a switch, and it ships off.** A containment
edge is refused when the member accounts for less than the named share of its
owner, which is the check the committed strict-subset derivation declines to
make by itself. The default is no floor because `member_share` does not
separate the two shapes, which was measured rather than guessed: the
`fragment` verdicts run from `common/3239.c`'s `0.06` to `bank0/BB78.c`'s
`0.50`, and `common/3BBF.c` is a `re-export` at that same `0.50`, so a floor
high enough to refuse every fragment refuses re-exports with it and no value
on the column is a separator. Enabling one is its own change with its own
re-pinned oracles
(docs/findings/export-ownership-relative-containment.md), and writing a scratch
map with `--map --min-share` is how to look at what one costs first.

**The floor is a condition on the edge, so it inherits the same limit as the
relation it filters.** A member still reaches its owner through a chain of
edges that each clear the floor even when the member itself is a smaller share
of the owner than the floor demands; at `CANDIDATE_MIN_SHARE` `bank0/F078.c`
has members that do exactly that against it. That is not a
second mechanism to fix, it is the "containment does not compose" caveat above
showing up again, and `member_share` is what makes it visible: a row whose
share is under the floor while it is still folded says its owner is a
container rather than a re-export, which is the judgement the check cannot
make for itself.

**What this is not.** A containment score over decompiled C text is a text
heuristic about how two files compare, not a function boundary and not a
disassembly. Two genuinely distinct routines can share most of their statements
and fold; one routine split across exports can be missed where the decompiler
re-spelled a line. Because a non-owner is skipped rather than reconciled
against its owner, the pass **loses** an address wherever the owner is not a
superset of the non-owners it swallows -- a mechanism, and a real risk, but
not one this tree exercises: `bank1/8E91.c`, the only export spelling
`DAT_EXTMEM_05e0`, owns its own two-file class, so nothing is lost here and
the `lost` set pinned in `xdata_register_map.py`'s `OWNERSHIP` oracle is empty.
That set is a measurement, not an absence -- the plan stage's detector did
lose 0x05E0, by folding that same file into a larger body
(annotations/xdata-export-ownership.md 4). The default stays off for the
measured reason instead: the flip re-keys 35 of the 430 clusters and breaks 5
of the 10 hand names. Nothing here says a byte is absent, and a row this pass
leaves alone is "not found by this method".

**The `body_lines` column counts statements, not lines.** It is the cardinality
of the set the containment score divides by, which is the only figure the rule
actually compares; a decompiled body's line count is indentation-dependent and
would say nothing about containment.
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC_DIR = os.path.dirname(HERE)
DECOMPILED = os.path.join(EC_DIR, "decompiled")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
OWNERSHIP_CSV = os.path.join(EC_DIR, "annotations", "xdata-export-ownership.csv")

# The issue's ad-hoc containment scan was run at a ">=90% line threshold";
# this is the committed form of that number, and changing it changes the map,
# which is why --check and --self-test refuse it rather than answering about a
# derivation other than the committed one.
THRESHOLD = 0.90
# The smallest body allowed to form a containment edge, and to be grouped by
# --fold-equal. See the docstring: at 1, the single statement `return` bridges
# routines that have nothing to do with each other.
MIN_BODY_STMTS = 3

# The candidate relative floor, named rather than inlined, because it is the
# value the oracle below measures: one constant holding the shape, the counts
# derived from it. It is not the default and never becomes one without a
# decision of its own -- see the docstring.
CANDIDATE_MIN_SHARE = 0.30

COLUMNS = ["out_file", "program", "addr", "body_lines", "owner_out_file",
           "owner_addr", "owner_name", "shared", "containment",
           "owner_body_lines", "member_share"]


def body_of(text: str) -> frozenset:
    """The file's body as a set of whitespace-collapsed statements.

    The plate comment (`//` banner and the `/* ... */` annotation block) and
    the signature are this repository's own text rather than the decompiler's,
    and the signature differs between two exports of one body purely by
    parameter naming, so all of it goes: what is left between the outermost
    braces is split on `;` and collapsed. The first `{` and the last `}` are
    taken rather than matched, because a body can carry a brace inside a string
    or a character literal and a match would then truncate it.
    """
    text = re.sub(r"//[^\n]*", " ", text)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    inner = text[start + 1:end] if start >= 0 and end > start else text
    return frozenset(" ".join(s.split()) for s in inner.split(";") if s.strip())


def load_rows() -> list:
    """index.csv rows, each with its `key` and file order.

    File order is the ownership tie-break's second half -- a lowest address,
    and a lowest address at an equal size is the order the exports themselves
    are already in -- so the row index is kept rather than discarded.
    """
    with open(INDEX_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    for i, r in enumerate(rows):
        r["key"] = (r["program"], int(r["addr"], 16))
        r["order"] = i
    return rows


def load_bodies(rows) -> dict:
    """out_file -> body set, read once each."""
    bodies = {}
    for r in rows:
        with open(os.path.join(DECOMPILED, r["out_file"])) as f:
            bodies[r["out_file"]] = body_of(f.read())
    return bodies


def containment(small: frozenset, large: frozenset) -> float:
    """How much of `small` is in `large`, in [0, 1].

    Directed, and always called with the smaller body first. `|A & B| / |A|`
    and not Jaccard: the question is whether this file's statements are the
    larger body's, and a large body that is mostly *another* routine must not
    be penalised for it.
    """
    if not small:
        return 0.0
    return len(small & large) / len(small)


def member_share(small: frozenset, large: frozenset) -> float:
    """`|A| / |B|`, how much of the larger body the smaller one accounts for.

    The direction `containment` normalises away. Containment asks how much of
    the *member* the owner has, and a four-statement fragment scores 1.00
    against any owner that spells those four statements; this asks how much of
    the *owner* the member is, which is the same number for a re-export of one
    routine and a different one for a fragment inside a longer routine. An
    owner has no larger body to be measured against, so it scores 1.00 -- it is
    the whole of its own class.
    """
    if not large:
        return 0.0
    return len(small) / len(large)


def classes_of(rows, bodies, threshold=THRESHOLD, fold_equal=False,
               floor=MIN_BODY_STMTS, min_share=None):
    """out_file -> list of its class's index.csv rows.

    The unit is the connected component, not the nearest container, and that
    choice is what makes the pass work. Assigning each file to its single best
    container fragments the 42-file class into a chain of a dozen pairwise
    classes, every one of which still has to be read, and the `refs` inflation
    survives the fix untouched. The component is the class; the owner is its
    largest body.

    Comparison is within a program only. `index.csv` rows already carry the
    program, and two programs are two address spaces that must never be
    compared (the mistake `docs/findings.md` 3a had to correct).

    `min_share` is off (`None`) unless `--min-share` asks for it, and then an
    edge additionally needs `member_share(sa, sb) >= min_share`. It is a second
    condition on the edge rather than a post-filter on the class, so a class
    held together by a chain loses the links below the floor and re-forms as
    whatever the remaining links connect.
    """
    by_prog = collections.defaultdict(list)
    for r in rows:
        by_prog[r["program"]].append(r)

    parent = {r["out_file"]: r["out_file"] for r in rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for rows_here in by_prog.values():
        usable = [r for r in rows_here
                  if len(bodies[r["out_file"]]) >= floor]
        by_size = sorted(usable, key=lambda r: len(bodies[r["out_file"]]))
        for i, small in enumerate(by_size):
            sa = bodies[small["out_file"]]
            for large in by_size[i + 1:]:
                sb = bodies[large["out_file"]]
                if len(sb) <= len(sa):
                    continue
                if min_share is not None and member_share(sa, sb) < min_share:
                    continue
                if containment(sa, sb) >= threshold:
                    union(small["out_file"], large["out_file"])
        if fold_equal:
            by_body = collections.defaultdict(list)
            for r in usable:
                by_body[bodies[r["out_file"]]].append(r)
            for same in by_body.values():
                for other in same[1:]:
                    union(same[0]["out_file"], other["out_file"])

    comps = collections.defaultdict(list)
    for r in rows:
        comps[find(r["out_file"])].append(r)
    return comps


def ownership(rows, bodies, threshold=THRESHOLD, fold_equal=False,
              floor=MIN_BODY_STMTS, min_share=None):
    """out_file -> the record that becomes one row of the committed CSV.

    The owner is the largest body in the class, ties by the lowest `index.csv`
    address. A body below the floor forms no edge and so is always a class of
    one: it is its own owner, left alone rather than folded into whatever is
    nearby, because "too short to compare" is not evidence of overlap and
    folding it would drop a real export's references.
    """
    out = {}
    for members in classes_of(rows, bodies, threshold, fold_equal, floor,
                              min_share).values():
        owner = min(members, key=lambda m: (-len(bodies[m["out_file"]]),
                                            m["key"][1], m["out_file"]))
        for m in members:
            score = containment(bodies[m["out_file"]],
                                bodies[owner["out_file"]])
            out[m["out_file"]] = row_record(m, owner, bodies, score)
    return out


def row_record(member, owner, bodies, score) -> dict:
    """One committed CSV row. `shared` says whether the file is read at all:
    `no` means it owns itself, `yes` means its references are already counted
    through the owner and the file is skipped."""
    own_body = bodies[member["out_file"]]
    owner_body = bodies[owner["out_file"]]
    return {
        "out_file": member["out_file"],
        "program": member["program"],
        "addr": member["addr"],
        "body_lines": len(own_body),
        "owner_out_file": owner["out_file"],
        "owner_addr": owner["addr"],
        "owner_name": owner["name"],
        "shared": "no" if member["out_file"] == owner["out_file"] else "yes",
        "containment": f"{score:.2f}",
        "owner_body_lines": len(owner_body),
        "member_share": f"{member_share(own_body, owner_body):.2f}",
    }


def derive(threshold=THRESHOLD, fold_equal=False, floor=MIN_BODY_STMTS,
           min_share=None) -> list:
    """The whole map as a list of records in index.csv order."""
    rows = load_rows()
    bodies = load_bodies(rows)
    own = ownership(rows, bodies, threshold, fold_equal, floor, min_share)
    return [own[r["out_file"]] for r in rows]


def render(recs) -> str:
    """The committed CSV: header, then one row per index.csv row."""
    return "\n".join(
        [",".join(COLUMNS)]
        + [",".join(str(r[c]) for c in COLUMNS) for r in recs]) + "\n"


def read_committed():
    """The committed CSV as a list of dicts, or None when it is absent."""
    if not os.path.exists(OWNERSHIP_CSV):
        return None
    with open(OWNERSHIP_CSV, newline="") as f:
        return list(csv.DictReader(f))


def diff(on_disk, generated) -> int:
    """First differing line, or 0. The message is a worklist, not a summary.

    Both sides are read through the columns, so a derived `body_lines` of `12`
    and the `12` a CSV reader gives back are the same cell rather than a
    difference that is really a type.
    """
    if on_disk is None:
        print(f"{OWNERSHIP_CSV} is absent; run --map to write it", file=sys.stderr)
        return 1
    cells = lambda r: {c: str(r[c]) for c in COLUMNS}  # noqa: E731
    for i, (a, b) in enumerate(zip(on_disk, generated), start=2):
        if cells(a) != cells(b):
            print(f"{OWNERSHIP_CSV}:{i}: on disk {cells(a)} != derived "
                  f"{cells(b)}", file=sys.stderr)
            return 1
    if len(on_disk) != len(generated):
        print(f"{OWNERSHIP_CSV}: {len(on_disk) + 1} lines on disk vs "
              f"{len(generated) + 1} derived", file=sys.stderr)
        return 1
    return 0


def check(args) -> int:
    """The committed map is a fresh derivation from the committed tree."""
    return diff(read_committed(), derive())


# Tree-wide figures this tool measures, pinned the way xdata_register_map.py
# pins its own ORACLE: a re-export that moves the map's shape fails here rather
# than quietly changing what every downstream prose number means.
#
# 2026-09-25, issue #554. These are this tool's figures, not the issue's 159.
# The 159 was an ad-hoc containment scan of an uncommitted run; the plan
# stage's independent re-derivation of the same >=90% idea put it at 144
# non-owner rows in 64 classes (strict subsets) and 233 in 74 (grouping equal
# bodies), and reproduced neither reading exactly. That spread is itself the
# finding -- a threshold over statement text is a heuristic whose count depends
# on the choices -- so the numbers below are the committed tool's own and
# replace all three rather than reconciling them. Re-derive any of them with
# --map --threshold, or read the class shape with --self-test.
OWNERSHIP_ORACLE = {
    # No row total: it is index.csv's length, every seeded routine moved it,
    # and the self-test asserts one row per index.csv row instead.
    "classes": 56,
    "shared_rows": 146,
    "largest_class": 42,
    # The floor's cost, both measured as classes whose two largest members are
    # *not* contained in each other -- classes that hold together only through
    # a chain. Without the floor the count is 14 and the largest of them is 562
    # members; with it, 7, all of them small. See the docstring.
    #
    # 13 -> 14 on 2026-09-28, issue #489: naming the 37 unannotated `pd`
    # listings. Both floor-1 figures moved, and `classes_no_floor` with them,
    # because `body_of` builds a body from the statements between the braces, so
    # a rename changes the text containment is measured on. `pd` 0x10BC is the
    # worked case: four of this issue's rows -- 0x3497, 0x998B, 0x9C1B, 0x9C4D --
    # are one-instruction forwarders to it that had carried the *callee's* name
    # `add_full_product_to_dptr` and are now `call_10bc`. Everyone calling one
    # of them had that call statement renamed with them, whether directly or by
    # jumping into a body that makes it: 0x4402 (`lcall 0x3497`), 0xC901
    # (`lcall 0x9C1B`), 0xF22E (`lcall 0x998B`), and 0x4800 and 0xF79F, which
    # `ljmp` into 0x4402. Those five left the 193-member floor-1 class. The four
    # forwarders kept the body `add_full_product_to_dptr();` -- they still call
    # 0x10BC under its own name -- and with 0xB263, a fifth forwarder to 0x10BC
    # that #489 did not name, plus 0xCCB7 and 0xEDB5, which merely contain that
    # statement, they stopped folding into that class and form one of their own.
    # One class net, and one more of them held together only through a chain.
    # `bridged` (7) and `flood_no_floor` (562) did not move, so the floor is
    # doing the same work it was pinned for.
    "bridged": 7,
    "bridged_no_floor": 14,
    # The largest class a floor of 1 produces, and how many classes it produces
    # at all, both at this tool's own threshold rather than at 0.0. The floor-1
    # flood is the whole argument for the floor, so both are measured where the
    # table above measures them and pinned.
    "classes_no_floor": 29,
    "flood_no_floor": 562,
}

# What `--min-share` would cost, measured at CANDIDATE_MIN_SHARE and pinned the
# same way, so that enabling the floor later is a re-pin someone has to make
# deliberately rather than a number that quietly moves. Issue #589, and
# docs/findings/export-ownership-relative-containment.md is the write-up.
#
# The finding is that this candidate is not a separator rather than that it is
# a well-placed one: the `fragment` verdicts run from 0.06 (`common/3239.c`) to
# 0.50 (`bank0/BB78.c`), and `common/3BBF.c` is a `re-export` at that same
# 0.50, so no floor refuses every fragment and keeps every re-export.
# `largest_class` is unchanged because a class is a connected component and
# the 42-file class is still one; `newly_read` is what the census would open
# again.
#
# `classes` is expected to collide with a figure another document already
# pins -- the `pd` cluster count of the census checklist's 6b is the same
# number -- so check_doc_figure_pins.py resolves that section's figure to this
# constant rather than to the census case that asserts it. Nothing is weakened
# by either: they are different measurements that happen to be equal. Read a
# resolution from that section at this constant as a prompt to open the
# checklist row, not as a statement about the pd image.
SHARE_ORACLE = {
    "classes": 50,
    "shared_rows": 133,
    "largest_class": 42,
    "largest_class_owner": "bank1/8001.c",
    "newly_read": 13,
}


def floored_cost(rows, bodies, min_share=CANDIDATE_MIN_SHARE):
    """`(cost, floored)` for a floor at `min_share`.

    The cost is measured rather than quoted, because the point of pinning the
    floor's cost is that a reader can re-run it: `newly_read` counts the files
    the committed map skips and a floor at this value would hand back to
    `xdata_register_map.py --export-ownership`, which is the number that says
    whether the flip is a re-pin or a rebuild. The floored records come back
    with it so the caller can check the derivation rather than the summary.
    """
    floored = ownership(rows, bodies, min_share=min_share)
    committed = ownership(rows, bodies)
    comps = [m for m in classes_of(rows, bodies, min_share=min_share).values()
             if len(m) > 1]
    big = [m for m in comps if len(m) == SHARE_ORACLE["largest_class"]]
    owner = (min(big[0], key=lambda m: (-len(bodies[m["out_file"]]),
                                        m["key"][1], m["out_file"]))
             if big else None)
    cost = {
        "classes": len(comps),
        "shared_rows": sum(1 for r in floored.values() if r["shared"] == "yes"),
        "largest_class": max((len(m) for m in comps), default=0),
        "largest_class_owner": owner["out_file"] if owner else None,
        "newly_read": sum(1 for f, r in committed.items()
                          if r["shared"] == "yes"
                          and floored[f]["shared"] == "no"),
    }
    return cost, floored


def bridged_classes(rows, bodies, floor, threshold=THRESHOLD) -> int:
    """How many classes hold together only through a chain of intermediaries.

    For each class, the two largest members: if the smaller is not itself
    contained in the larger, the class reached its size by `a in b`, `b in c`,
    `a not in c` -- containment does not compose, so the class is a hypothesis
    about one routine exported several times that the text alone does not
    establish. This is the number the `containment` column exists to let a
    reader find without re-deriving.
    """
    n = 0
    for members in classes_of(rows, bodies, threshold, False, floor).values():
        if len(members) < 2:
            continue
        top = sorted(members, key=lambda m: -len(bodies[m["out_file"]]))[:2]
        a, b = bodies[top[0]["out_file"]], bodies[top[1]["out_file"]]
        small, large = (a, b) if len(a) <= len(b) else (b, a)
        if not small or containment(small, large) < threshold:
            n += 1
    return n


def self_test(args) -> int:
    """The rule against fixtures, then the tree against the oracle.

    The fixtures are the half that matters: a detector that has quietly stopped
    folding looks exactly like a detector that is working, and only a case that
    asserts the fold happens says otherwise.
    """
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        if not cond:
            ok = False

    print("export_ownership.py --self-test")

    def fixture(stmts, names, program="bank0", addrs=None):
        """Inline index.csv-shaped rows, so each case reads as the shape it is
        about rather than as a diff against a stored file."""
        addrs = addrs or [f"{0x8000 + 4 * i:04X}" for i in range(len(names))]
        rows = [{"out_file": f"{program}/{addrs[i]}.c", "program": program,
                 "addr": addrs[i], "name": name, "order": i,
                 "key": (program, int(addrs[i], 16))}
                for i, (name, st) in enumerate(zip(names, stmts))]
        return rows, {r["out_file"]: frozenset(s.split()) for r, s in zip(rows, stmts)}

    big = "a; b; c; d; e;"

    # These two run with the floor lowered, because what they are about is the
    # *direction* of containment and the floor is a separate property with its
    # own case below. At the default floor a two-statement body is not
    # comparable at all, so testing the direction here would silently be
    # testing the floor too.
    rows, bodies = fixture([big, "b; c;"], ["big", "small"])
    own = ownership(rows, bodies, floor=1)
    check("an overlapping pair folds into the larger body",
          own["bank0/8000.c"]["owner_out_file"] == "bank0/8000.c"
          and own["bank0/8004.c"]["owner_out_file"] == "bank0/8000.c"
          and own["bank0/8004.c"]["shared"] == "yes")

    rows, bodies = fixture(["a; b; c;", "x; y; z;"], ["p", "q"])
    own = ownership(rows, bodies)
    check("a genuinely distinct pair does not fold",
          all(own[k]["shared"] == "no" for k in own))

    # The asymmetry is the rule: strict containment has a direction, and a pass
    # that let a large body follow a one-statement fragment would drop the
    # whole routine out of the census.
    rows, bodies = fixture([big, "b;"], ["big", "frag"])
    own = ownership(rows, bodies, floor=1)
    check("a one-statement fragment folds into a big body, never the reverse",
          own["bank0/8000.c"]["owner_out_file"] == "bank0/8000.c"
          and own["bank0/8004.c"]["owner_out_file"] == "bank0/8000.c")

    # ...and the floor, which is why the case above is not run at the default.
    # It is a claim about how much text a containment score is worth, and it is
    # the difference between a detector and the 562-member floor-1 flood.
    rows, bodies = fixture([big, "b;"], ["big", "frag"])
    own = ownership(rows, bodies)
    check(f"and at the default floor of {MIN_BODY_STMTS} a one-statement body is "
          "not compared at all, so it stays its own owner",
          own["bank0/8004.c"]["owner_out_file"] == "bank0/8004.c"
          and own["bank0/8000.c"]["owner_out_file"] == "bank0/8000.c")

    # Equal bodies: strict containment groups neither, because neither is
    # strictly larger. --fold-equal is the only thing that collapses them, and
    # the surviving owner is the lowest address -- here the *second* file.
    rows, bodies = fixture(["a; b; c;", "a; b; c;"], ["one", "two"],
                           addrs=["8004", "8000"])
    own = ownership(rows, bodies)
    check("equal bodies are each their own owner under strict containment",
          own["bank0/8000.c"]["shared"] == "no"
          and own["bank0/8004.c"]["shared"] == "no")
    own_eq = ownership(rows, bodies, fold_equal=True)
    check("and --fold-equal collapses them to the lowest address",
          own_eq["bank0/8004.c"]["owner_out_file"] == "bank0/8000.c"
          and own_eq["bank0/8004.c"]["shared"] == "yes"
          and own_eq["bank0/8000.c"]["shared"] == "no")

    # Two programs are two address spaces; a shared statement between them is
    # not evidence of one routine exported twice.
    rows, bodies = fixture([big], ["big"], program="bank0")
    rows2, bodies2 = fixture(["b; c;"], ["small"], program="bank1", addrs=["8004"])
    own = ownership(rows + rows2, {**bodies, **bodies2})
    check("a cross-program pair never folds",
          own["bank1/8004.c"]["owner_out_file"] == "bank1/8004.c")

    rows, bodies = fixture([big, ""], ["big", "empty"])
    own = ownership(rows, bodies)
    check("an empty-after-normalization body folds into nothing",
          own["bank0/8004.c"]["owner_out_file"] == "bank0/8004.c")

    # The tree. Every figure below is a property of the committed `.c` files
    # and index.csv, and is re-derivable by re-running this tool.
    rows = load_rows()
    bodies = load_bodies(rows)
    recs = derive()
    comps = classes_of(rows, bodies)
    real = [m for m in comps.values() if len(m) > 1]
    shared = [r for r in recs if r["shared"] == "yes"]
    check(f"one row per index.csv row ({len(recs)}), at threshold {THRESHOLD} "
          f"and floor {MIN_BODY_STMTS}",
          len(recs) == len(rows) > 0)
    check(f"{len(real)} containment classes, {len(shared)} non-owner rows",
          len(real) == OWNERSHIP_ORACLE["classes"]
          and len(shared) == OWNERSHIP_ORACLE["shared_rows"])

    by_file = {r["out_file"]: r for r in recs}
    big_class = [m for m in real
                 if len(m) == OWNERSHIP_ORACLE["largest_class"]]
    owner = (min(big_class[0], key=lambda m: (-len(bodies[m["out_file"]]),
                                             m["key"][1], m["out_file"]))
             if big_class else None)
    check(f"the {OWNERSHIP_ORACLE['largest_class']}-file class is owned by "
          f"bank1/8001.c, the run's own start address",
          len(big_class) == 1 and owner is not None
          and owner["out_file"] == "bank1/8001.c"
          and by_file["bank1/8001.c"]["owner_out_file"] == "bank1/8001.c")

    # The floor, both ways. Without it the pass is not a detector at all; with
    # it, a handful of classes still rest on a chain and say so. Both floor-1
    # figures are measured at THRESHOLD, the same detector as everything else
    # here: an earlier version of this check passed 0.0 in the threshold's
    # place, which made the number it printed a measurement of a different
    # question and left the floor-1 row of xdata-export-ownership.md mixing the
    # two. The class count is here rather than left to the reader because the
    # prose says this check re-derives the row, and a count it never computed
    # is not re-derived by anything.
    with_floor = bridged_classes(rows, bodies, MIN_BODY_STMTS)
    without = bridged_classes(rows, bodies, 1)
    comps_floor1 = classes_of(rows, bodies, THRESHOLD, False, 1)
    classes_floor1 = sum(1 for m in comps_floor1.values() if len(m) > 1)
    flood = max((len(m) for m in comps_floor1.values()), default=0)
    check(f"the body floor is load-bearing: {with_floor} chained classes with "
          f"it, {without} without it, and at the committed threshold a floor of "
          f"1 giving {classes_floor1} classes with a {flood}-member flood",
          with_floor == OWNERSHIP_ORACLE["bridged"]
          and without == OWNERSHIP_ORACLE["bridged_no_floor"]
          and classes_floor1 == OWNERSHIP_ORACLE["classes_no_floor"]
          and flood == OWNERSHIP_ORACLE["flood_no_floor"])

    tiny = sum(1 for v in bodies.values() if len(v) < MIN_BODY_STMTS)
    check(f"{tiny} of the {len(rows)} bodies are too short to carry a "
          f"containment claim, so the floor is not a rounding boundary",
          0 < tiny < len(rows))

    weak = [r for r in shared if float(r["containment"]) < THRESHOLD]
    check("every non-owner records its own containment score against the owner, "
          "so a chained member is visible in the CSV rather than hidden by the "
          f"grouping ({len(weak)} are below the threshold)",
          all(0.0 <= float(r["containment"]) <= 1.0 for r in shared) and bool(weak))

    # The relative floor's cost, at the named candidate value, from the same
    # bodies -- never quoted, so a reader who disagrees with the candidate can
    # see what a different one costs by editing one constant.
    cost, floored = floored_cost(rows, bodies)
    check(f"a --min-share floor of {CANDIDATE_MIN_SHARE} leaves the "
          f"{SHARE_ORACLE['largest_class']}-file class whole and owned by "
          f"{SHARE_ORACLE['largest_class_owner']}, moves "
          f"{OWNERSHIP_ORACLE['shared_rows']} non-owner rows to "
          f"{cost['shared_rows']} across {cost['classes']} classes, and hands "
          f"{cost['newly_read']} files back to the census",
          cost["classes"] == SHARE_ORACLE["classes"]
          and cost["shared_rows"] == SHARE_ORACLE["shared_rows"]
          and cost["largest_class"] == SHARE_ORACLE["largest_class"]
          and cost["largest_class_owner"] == SHARE_ORACLE["largest_class_owner"]
          and cost["newly_read"] == SHARE_ORACLE["newly_read"])

    # A floor that high must cost *something*: a check whose refusals the tree
    # does not notice is indistinguishable from a check that stopped refusing.
    check(f"the floor refuses rather than passing the tree through "
          f"({cost['shared_rows']} non-owners with it, {len(shared)} without, "
          f"{cost['newly_read']} files handed back)",
          cost["shared_rows"] < len(shared) and cost["newly_read"] > 0)

    # `member_share` is evidence about the fold only if it is the ratio of the
    # two sizes beside it, on every row and not only the ones that make a
    # point. A column computed from something the reader cannot see is a
    # number beside the evidence rather than part of it.
    check("every row's member_share is its own two committed sizes' ratio",
          all(r["member_share"] == f"{int(r['body_lines']) / int(r['owner_body_lines']):.2f}"
              for r in recs))

    on_disk = read_committed()
    check("the committed CSV is a fresh derivation from the committed tree",
          on_disk is not None and not diff(on_disk, recs))

    print("FAILURES ABOVE" if not ok else "all checks passed")
    return 1 if not ok else 0


def map_mode(args) -> int:
    """Write the derived map, to the committed path or a scratch one."""
    generated = render(derive(args.threshold, args.fold_equal,
                              min_share=args.min_share))
    with open(args.out, "w") as f:
        f.write(generated)
    print(f"wrote {args.out} ({generated.count(chr(10)) - 1} rows)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true",
                       help="derive the map in memory and diff it against the "
                            "committed CSV; no Ghidra, no image, no network")
    modes.add_argument("--self-test", action="store_true",
                       help="fixture cases for the containment rule, then the "
                            "tree-wide figures against OWNERSHIP_ORACLE")
    modes.add_argument("--map", action="store_true",
                       help="write the derived map to --out (default: the "
                            "committed CSV)")
    ap.add_argument("--threshold", type=float, default=THRESHOLD,
                    help="fraction of a body's statements that must appear in a "
                         f"larger body for the smaller to fold (default: "
                         f"{THRESHOLD})")
    ap.add_argument("--fold-equal", action="store_true",
                    help="also group bodies that are exactly equal, which "
                         "strict containment cannot; the committed map is the "
                         "strict-subset derivation")
    ap.add_argument("--min-share", type=float, default=None,
                    help="refuse a containment edge whose smaller body "
                         "accounts for less than this share (|A|/|B|) of the "
                         "larger one; off by default, so the committed map "
                         "folds on containment alone")
    ap.add_argument("--out", default=OWNERSHIP_CSV,
                    help=f"where --map writes (default: {OWNERSHIP_CSV})")
    args = ap.parse_args(argv)

    # Every knob changes the map, and each is refused where a gate could
    # otherwise answer a question about a derivation other than the committed
    # one -- the same shape as xdata_register_map.py's --no-eq-guard refusals.
    # Refused before any mode runs, so --check and --self-test stay statements
    # about the committed artifact.
    if args.threshold != THRESHOLD and (args.check or args.self_test):
        ap.error(f"--threshold {args.threshold} is not the committed "
                 f"{THRESHOLD}, so --check and --self-test cannot answer for "
                 f"it: they describe {OWNERSHIP_CSV}, which was derived at the "
                 f"default. Write a scratch map with --map --threshold and diff "
                 f"it.")
    if args.fold_equal and (args.check or args.self_test):
        ap.error("--fold-equal is not the derivation the committed map records, "
                 f"so --check and --self-test cannot answer for it: they "
                 f"describe {OWNERSHIP_CSV}, which was derived without it. Write "
                 f"a scratch map with --map --fold-equal and diff it.")
    if args.min_share is not None and (args.check or args.self_test):
        ap.error(f"--min-share {args.min_share} is not the derivation the "
                 f"committed map records, so --check and --self-test cannot "
                 f"answer for it: they describe {OWNERSHIP_CSV}, which was "
                 f"derived with no floor at all. Write a scratch map with "
                 f"--map --min-share and diff it.")

    if args.self_test:
        return self_test(args)
    if args.check:
        return check(args)
    return map_mode(args)


if __name__ == "__main__":
    sys.exit(main())
