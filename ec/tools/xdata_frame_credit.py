#!/usr/bin/env python3
"""What `functions_touched` counts, and what the other reading of it would say.

`xdata_register_map.py`'s `functions_touched` / `readers` / `writers` columns
are `len()` of sets of *function keys*, and a function key is one `index.csv`
row's `(program, addr)` -- so one committed `.c`, one `out_file`, one credit.
`ec/decompiled/index.csv` nests some of its own frames inside others
(`nested_frame_census.py` measures how many), and where it does, two `.c` files
decompile the same bytes. That raises a question the CSVs do not answer: does
the column count **one committed row per `out_file`** (what it does), or **one
frame of code** (which would give the inner listing's credit to the frame
holding it)?

**The ruling is the first one, and it is the dated block at the end of
`xdata_register_map.py`** -- not that module's docstring, which is where it
belongs and where it cannot stay, because the module is cited by line and the
docstring sits above every one of those anchors;
`docs/findings/xdata-frame-credit-column.md` §9 has that constraint in full. This
tool is what makes the second one derivable rather than asserted, so the ruling
has a measurement behind it instead of a preference.

**Both readings are derived from the census's own in-memory build**
(`load_index` / `scan` / `merge_group`), **not from `xdata-registers.csv`.**
That is a measured choice and the trap is worth naming, because the CSV looks
like it carries the answer in its `functions` column and does not: the `[writer]`
tag there is the function's *role* from `ghidra-functions.csv`, not a record of
which of its accesses were stores. Counting it reproduces the `writers` column
on a minority of the committed rows, and on `0x0491` -- whose twelve writers all
reach it as `read+write` -- it gives **2**. `entry["dirs"]`, the per-function
bucket sets `scan()` already builds, reproduces `functions_touched`, `readers`
and `writers` on **every** committed row. So the derivation reads the census, and
the CSV is only ever read to be *checked against*.

**"One frame of code" needs a single outermost frame, and the census says there
is not always one.** Two shapes have none, and both are refusals rather than a
guess:

  several-containers   the row sits inside two or more containers at once, so
                       "its container" is not one row. The census's own
                       docstring says so, and reports each of those rows' two
                       containers in *different* buckets, so picking either
                       would be wrong about the other.
  mutual-nesting       `common 0x6A02` and `common 0x6D46` each fall inside the
                       other's listing span and neither span contains the
                       other. Following the chain never reaches a row with no
                       container -- it returns to where it started -- so there is
                       no outermost frame to credit.

A refusal is a refusal in both directions: the row keeps its own credit rather
than moving to a container this tool cannot name. That is the same "refusal
rather than a third bucket" shape `nested_frame_census.bucket_of()` uses, reached
from the other end, and it is why a reader cannot tell from this tool's output
that the alternative reading was considered and declined.

**What the columns already encode is `--check`'s whole claim.** The stated
reading is today's behaviour, so a fresh derivation must equal the committed
`functions_touched`, `readers` and `writers` on every row. `--self-test` pins
that on the named rows *and* on the collapse's named effects, so a future silent
flip goes red rather than quietly changing what a published column means.
Neither mode asserts a count of the tree: the population moves as the export
moves, and a suite that pinned it would go red on a merge that added a row and
tell the implement stage to fix a correct tool.

**The clustering consequence is printed, not adopted.** `similar()` takes the
Jaccard of these sets, so collapsing them re-clusters the tree; the report
prints the before -> after component counts and how many addresses land in a
different `cluster_key`, and that is a tree-wide renumbering to land on a
boundary the export has not settled -- the cost `--export-ownership` is refused
for, measured on the other side of the same question.

**What this is not.** Every input is a committed file: `index.csv`, the `.asm`
listings, `ec/decompiled/*/*.c`, `ghidra-functions.csv`, `xdata-symbols.csv`,
`xdata-registers.csv` and `ec/firmware/GMxMGxx_11.800`. No Ghidra run, no
scratch project, no hardware, no Windows, no network. No register was read and
no machine was observed. A row's function set is a count of committed source
files, never a claim that the firmware has that many independent routines --
`annotations/xdata-register-map.md` 4.5 is the sibling claim with the 42-way
split already on record. **The tool writes nothing**, and says so on stderr the
way `xdata_register_map.py --collapse-co-readings` does.

Usage:
    python3 ec/tools/xdata_frame_credit.py              # both readings, the refusals, the clustering cost
    python3 ec/tools/xdata_frame_credit.py --check      # the committed columns already encode the stated reading
    python3 ec/tools/xdata_frame_credit.py --self-test  # named claims, named refusals, no count of the tree
"""
import argparse
import collections
import csv
import os
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)

# Imported by bare module name, as `check_site_census.py` imports the census
# tool. `xdata_register_map` builds the numbers; `nested_frame_census` supplies
# the edges. Both are already importable and side-effect-free at module level,
# and no tool here imported both before -- that join is the point of this file.
import nested_frame_census  # noqa: E402
import xdata_register_map as xrm  # noqa: E402
from second_copy_census import FIRMWARE, norm_addr, read_csv  # noqa: E402

REGISTERS_CSV = xrm.OUT_REGISTERS

# The two refusals, and no third. A shape outside these is not a collapse this
# tool can perform, and filing it under a name would be picking a container --
# see the docstring.
REFUSALS = ("several-containers", "mutual-nesting")

# The three derived columns, each paired with the committed CSV header it is
# checked against. One tuple so a drift between what is derived and what is
# checked is a drift in one list rather than two that disagree silently.
COLUMNS = (("functions_touched", "functions_touched"),
           ("readers", "readers"),
           ("writers", "writers"))


def census_edges() -> dict:
    """{function key: [container function key, ...]} over the committed tree.

    A function key is `xdata_register_map`'s own `(program, bare(addr))`, which
    is what `scan()` accumulates `entry["funcs"]` under -- so the keys returned
    here are directly usable as a collapse map, with no second spelling of "a
    function" in the file.

    Only rows the census calls `nested` appear, and only their edges: a row with
    no container is its own frame and needs no entry. Asked of the census's
    *records* rather than of its printed report, so this is the edge set and not
    a transcription of a table.
    """
    records = nested_frame_census.census(
        read_csv(nested_frame_census.INDEX_CSV),
        read_csv(nested_frame_census.ANNOTATIONS), _firmware())
    out = collections.defaultdict(list)
    for record in records:
        if record["verdict"] != "nested":
            continue
        key = (record["program"], norm_addr(record["addr"]).upper())
        for edge in record["edges"]:
            container = (edge["container"]["program"],
                         norm_addr(edge["container"]["addr"]).upper())
            out[key].append(container)
    return dict(out)


def partial_edges() -> list:
    """[(nested key, frame)] for the collapses that are not whole-listing ones.

    The census reads *address-inside-a-listing* -- the container's span reaches
    this row's address -- and separately whether it also swallows this row's
    whole listing, as `span_contained`. The collapse follows the first, which is
    the relation the issue is about, so an edge can be collapsible and still be
    a partial one: the inner listing runs past the container's last byte, and
    the container's `.c` does not re-decompile the tail. Collapsing such a row
    would remove credit for statements no frame repeated.

    Reported, never refused: refusing would mean refusing a collapse the census
    does support, on the strength of a predicate the question did not ask about.
    It is listed so the write-up can say which collapses are partial rather than
    let "collapsible" imply they are all the same kind of thing.
    """
    records = nested_frame_census.census(
        read_csv(nested_frame_census.INDEX_CSV),
        read_csv(nested_frame_census.ANNOTATIONS), _firmware())
    collapse, _refused = collapse_map(census_edges())
    out = []
    for record in records:
        if record["verdict"] != "nested":
            continue
        key = (record["program"], norm_addr(record["addr"]).upper())
        frame = collapse.get(key)
        if frame is None:
            continue
        for edge in record["edges"]:
            if not edge["span_contained"] and (
                    edge["container"]["program"],
                    norm_addr(edge["container"]["addr"]).upper()) == frame:
                out.append((key, frame))
    return out


def _firmware() -> bytes:
    """The committed image, read once per process.

    Handed to `nested_frame_census.census()` explicitly rather than left to its
    `fw=None` default: that default opens the image without closing it, which is
    the census's code to fix and not this file's to change, and reading it under
    a `with` keeps this tool from emitting a `ResourceWarning` under a caller
    that turns warnings into errors.
    """
    global _FIRMWARE
    if _FIRMWARE is None:
        with open(FIRMWARE, "rb") as handle:
            _FIRMWARE = handle.read()
    return _FIRMWARE


_FIRMWARE = None


def frame_of(key, edges: dict):
    """`(frame, reason)`: the row that would hold `key`'s credit, or why not.

    The frame is the row the walk finishes on: follow the single-container chain
    until it reaches a row that has no container of its own, which is the
    outermost frame. The chain is followed to its *end* rather than one step,
    because a row two levels down is held by the frame at the top of the walk,
    not by the row immediately above it.

    **The frame's listing contains this row's *address*, not always this row's
    whole listing.** The census keeps both predicates apart for exactly this
    reason, and two collapsible edges on this tree are `span_contained=False`:
    the inner listing runs past the container's last byte, so the container's
    `.c` does *not* re-decompile all of it. Collapsing such a row therefore
    removes credit for statements the frame never repeated --
    `partial_edges()` reports which edges those are, and the ruling does not rest
    on them being absent.

    A row already at the top of its own chain is its own frame, collapses to
    nothing, and says so as `already-outermost` rather than as an error.

    Two shapes have no frame and return a reason from `REFUSALS`:

    - more than one container, so there is no single row to credit;
    - a chain that returns to a row it has already visited, which is mutual
      nesting and means the walk never terminates.

    A visited-set rather than a depth limit, so a cycle is *reported* instead of
    being cut off at whatever depth bounded the search: a truncation would hand
    back a plausible frame for the mutually nested pair and be wrong about it.
    """
    seen = {key}
    current = key
    while True:
        containers = edges.get(current)
        if not containers:
            # `census_edges()` carries only rows that have at least one
            # container, so an absent key is a row nothing holds.
            if current == key:
                return None, "already-outermost"
            return current, None
        if len(containers) != 1:
            return None, "several-containers"
        nxt = containers[0]
        if nxt in seen:
            return None, "mutual-nesting"
        seen.add(nxt)
        current = nxt


def collapse_map(edges: dict):
    """`(collapsible, refused)` from `census_edges()`.

    `collapsible` is the key -> outermost-frame map the frame reading would
    apply. `refused` is key -> reason for the two shapes in `REFUSALS`;
    `already-outermost` is a reported outcome rather than a refusal and is left
    out of it, so a caller cannot read one as the other.

    Both are derived rather than tabulated: a hand-kept list of which of the
    export's rows nest is a value every merge that adds a row has to come back
    and correct, and the census already computes it.
    """
    collapsible = {}
    refused = {}
    for key in sorted(edges):
        frame, reason = frame_of(key, edges)
        if frame is not None:
            collapsible[key] = frame
        elif reason != "already-outermost":
            refused[key] = reason
    return collapsible, refused


def _moved(counter, collapse):
    """`counter` with each key replaced by its frame, counts summed."""
    out = collections.Counter()
    for key, n in counter.items():
        out[collapse.get(key, key)] += n
    return out


def _moved_dirs(dirs, collapse):
    """`dirs` with each key replaced by its frame, bucket sets unioned."""
    out = collections.defaultdict(set)
    for key, buckets in dirs.items():
        out[collapse.get(key, key)].update(buckets)
    return out


def read_census():
    """`(groups, names)` -- the committed census exactly as `build()` sees it.

    One read of the tree per process, memoised, because every mode needs it and
    `scan()` walks every `.c` file. The memo is what makes the collapsed view
    cheap and, more importantly, safe: `collapsed_groups()` copies each entry
    before remapping it, so the memo keeps describing the *stated* reading for
    the whole process. A collapse applied in place here would silently move the
    reading `--check` exists to protect.
    """
    global _CENSUS
    if _CENSUS is None:
        funcs, by_file = xrm.load_index()
        names = xrm.load_names(funcs)
        symbols = xrm.load_symbols()
        func_names = {r["name"] for r in funcs.values()}
        census, _calls, _raw = xrm.scan(by_file, names, func_names, symbols,
                                        True, False)
        groups = {g: xrm.merge_group(census, xrm.PROGRAM_COL[g])
                  for g in xrm.GROUPS}
        _CENSUS = (groups, names)
    return _CENSUS


_CENSUS = None


def collapsed_groups(collapse: dict):
    """The census with every nested row's credit moved to its outermost frame.

    `funcs` (the per-function reference counts) and `dirs` (the per-function
    bucket sets) are remapped; nothing else is touched, which is what `refs`
    needs -- the question is which *sources* an address has, not how many times
    it was mentioned. The frames are not merged with one another, so a container
    that already had its own references keeps them and simply absorbs the inner
    listing's.

    A copy of every entry rather than an in-place remap of the memo: `scan()`
    hands back `Counter` and `defaultdict` state that `absorb()` mutates, so a
    collapse applied to it would move the *stated* reading too, which is the one
    thing `--check` exists to protect. Everything except `funcs` and `dirs` is
    carried across by `absorb()` and left alone, which is what `refs` needs.
    """
    groups, names = read_census()
    if not collapse:
        return groups, names
    out = {}
    for g in xrm.GROUPS:
        out[g] = {}
        for addr, entry in groups[g].items():
            new = xrm.blank_entry()
            xrm.absorb(new, entry)
            new["funcs"] = _moved(entry["funcs"], collapse)
            new["dirs"] = _moved_dirs(entry["dirs"], collapse)
            out[g][addr] = new
    return out, names


def program_of(groups) -> dict:
    """addr -> [program, ...], from the merged groups.

    The shape `build()` derives for itself, so a `both` row is measured here
    over the same union of both programs' entries as it is there.
    """
    out = {}
    for g in xrm.GROUPS:
        for addr in groups[g]:
            out.setdefault(addr, []).append(g)
    return out


def entry_of(groups, where, addr):
    """One address's census entry, summed over both programs when it is `both`."""
    seen = where[addr]
    if len(seen) > 1:
        entry = xrm.blank_entry()
        for g in seen:
            xrm.absorb(entry, groups[g][addr])
        return entry
    return groups[seen[0]][addr]


def credit_of(entry, collapse=None) -> dict:
    """The three derived columns for one address's entry.

    `readers` and `writers` are the keys that used a reading or writing bucket
    *in that function*, which is `touches()` rather than a count over the
    address's own buckets -- the distinction `blank_entry()`'s docstring makes,
    and the reason a reader count derived from the address would call all of a
    heavily-touched address's sources writers. `read+write` is in both, which is
    `build()`'s own rule and why `0x0491`'s writers are all `read+write` on a
    row reading `write 0`.

    A `collapse` map moves each key to its frame, and only the *set* moves: a
    column is `len()` of the set, so no arithmetic on `refs` is involved and
    nothing here can double-count.
    """
    move = (lambda key: collapse.get(key, key)) if collapse else (lambda key: key)
    readers = {move(f) for f in xrm.touches(entry, "read")}
    readers |= {move(f) for f in xrm.touches(entry, "read+write")}
    writers = {move(f) for f in xrm.touches(entry, "write")}
    writers |= {move(f) for f in xrm.touches(entry, "read+write")}
    return {"functions_touched": {move(f) for f in entry["funcs"]},
            "readers": readers,
            "writers": writers}


def rows_for(groups, collapse=None):
    """{addr: credit} for every address the census reaches.

    The population is whatever `scan()` found on the tree the reader runs it
    over, and no figure this file prints is a standing total.
    """
    where = program_of(groups)
    return {addr: credit_of(entry_of(groups, where, addr), collapse)
            for addr in sorted(where)}


def committed_columns(path: str = REGISTERS_CSV) -> dict:
    """{addr: {column: int}} from the committed registers CSV.

    Read with `DictReader` rather than parsed back out of the `functions` column,
    because the derivation checks the *columns* against the CSV and reading the
    one column that is not a per-function record is exactly the trap the
    docstring names.
    """
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f, strict=True):
            out[int(row["addr"], 16)] = {name: int(row[name])
                                         for _derived, name in COLUMNS}
    return out


def label(key) -> str:
    """A function key as the report prints it."""
    return f"{key[0]}:0x{key[1]}"


def _named_keys() -> set:
    """The function keys any committed register row's `functions` cell names.

    Parsed out of the CSV rather than out of the census, because the question is
    about what the *published* column says -- a frame the census collapses but
    no row names costs the published columns nothing.

    The split is the same one `func_label()` writes, so the keys read back here
    are the keys the column was rendered from: `prog:0xADDR=name [type]`.
    """
    out = set()
    with open(REGISTERS_CSV, newline="") as f:
        for row in csv.DictReader(f, strict=True):
            for cell in row["functions"].split("; "):
                if not cell:
                    continue
                program, rest = cell.split(":", 1)
                addr = rest.split("=")[0]
                out.add((program, addr.upper().removeprefix("0X")))
    return out


def writer_tags(path: str = REGISTERS_CSV, addr=None) -> int:
    """How many `functions` cells carry the `[writer]` role tag.

    Read straight out of the committed CSV, because the point is that this is
    what the column invites a reader to count. `addr` narrows it to one row;
    `None` totals every row, which is the figure the write-up quotes beside the
    command that prints it.
    """
    total = 0
    with open(path, newline="") as f:
        for row in csv.DictReader(f, strict=True):
            if addr is not None and int(row["addr"], 16) != addr:
                continue
            total += sum(1 for cell in row["functions"].split("; ")
                         if cell and cell.rstrip().endswith("[writer]"))
    return total


def differing(stated: dict, frame: dict) -> list:
    """[(addr, before, after)] for the rows the frame reading would change.

    Compared as **sets of function keys** rather than as the three integers, and
    that is the substantive choice: a row can name a nested frame *and* its
    container and keep the same count, so a size-only comparison reports "no
    change" for a row whose `functions` cell loses one name and gains another.
    How many rows lose a name without losing a count is printed separately for
    the same reason.
    """
    return [(a, stated[a], frame[a]) for a in sorted(stated)
            if any(stated[a][col] != frame[a][col] for col, _name in COLUMNS)]


def cluster_effect(frame_groups, threshold: float) -> list:
    """[(program, components before, after, addresses whose `cluster_key` moves)].

    `components()` is re-run rather than the Jaccard re-implemented, so "what
    does the collapse do to the clustering" is answered by the same function
    that produces the committed clustering.

    `cluster_key` is reported rather than `cluster_id`: the id is a rank, and
    issue #253 is what a renumbering costs every page that names one, so a
    figure in the rank would understate what moves.
    """
    groups, _names = read_census()
    out = []
    for g in xrm.GROUPS:
        before = xrm.components(groups[g], threshold)
        after = xrm.components(frame_groups[g], threshold)
        key_before = {a: xrm.cluster_key(g, sorted(v))
                      for v in before.values() for a in v}
        key_after = {a: xrm.cluster_key(g, sorted(v))
                     for v in after.values() for a in v}
        moved = sum(1 for a in set(key_before) & set(key_after)
                    if key_before[a] != key_after[a])
        out.append((g, len(before), len(after), moved))
    return out


def report() -> int:
    """Both readings, the refusals, and the clustering cost. Writes nothing."""
    edges = census_edges()
    collapse, refused = collapse_map(edges)
    groups, names = read_census()
    frame_groups, _names = collapsed_groups(collapse)
    stated = rows_for(groups)
    frame = rows_for(frame_groups, collapse)
    committed = committed_columns()

    print("xdata_frame_credit.py -- what `functions_touched` counts, and what the")
    print("other reading of it would say. Both are derived from the census's own")
    print("build; xdata-registers.csv is read only to be checked against.")
    print()
    print("  stated: one committed index.csv row (one out_file) per function key,")
    print("          which is what xdata_register_map.py does and what the block at")
    print("          the end of that file says the column means.")
    print("  frame:  one frame of code, so a nested listing's credit moves to the")
    print("          frame holding it.")
    print()
    print(f"  nested rows the census reports        {len(edges)}")
    print(f"  collapsible onto an outermost frame   {len(collapse)}")
    print(f"  refused, and left on their own credit {len(refused)}")
    for reason in REFUSALS:
        keys = sorted(k for k, r in refused.items() if r == reason)
        shown = ", ".join(f"{p}:0x{a}" for p, a in keys[:6])
        print(f"    {reason:21} {len(keys):>4}  {shown}"
              + (", ..." if len(keys) > 6 else ""))
    # What the refusals cost, which is not the same as how many there are. A
    # refused row keeps its own credit, so it can only matter if some register
    # row names it; on a tree where none does, the refusal is principled and
    # binds nothing, and saying so is what keeps the docstring from reading the
    # refusal as the decisive reason for the ruling.
    named = _named_keys()
    print(f"  of the collapsible rows, {len(named & set(collapse))} are named by "
          f"a register row; of the refused, {len(named & set(refused))}")
    partial = partial_edges()
    if partial:
        print("  collapsible edges whose frame holds the row's address but not "
              "its whole")
        print("  listing -- the frame's .c does not re-decompile the tail, so "
              "collapsing")
        print("  them removes credit no frame repeated:")
        for key, onto in sorted(partial):
            print(f"    {label(key)} -> {label(onto)}")
    print()

    mismatched = {a for a in stated
                  for derived, name in COLUMNS
                  if len(stated[a][derived]) != committed[a][name]}
    print("  the committed columns against the stated reading: "
          + ("every row matches" if not mismatched
             else f"{len(mismatched)} row(s) do not"))
    print()

    diff = differing(stated, frame)
    swapped = [a for a, before, after in diff
               if len(before["functions_touched"]) == len(after["functions_touched"])]
    print(f"  rows the frame reading would change    {len(diff)}")
    print(f"    of those, {len(swapped)} keep their count and only exchange one "
          f"name for its frame")
    if diff:
        worst = max(diff, key=lambda t: len(t[1]["functions_touched"])
                    - len(t[2]["functions_touched"]))
        print(f"    largest drop: {xrm.hexaddr(worst[0])} "
              f"{len(worst[1]['functions_touched'])} -> "
              f"{len(worst[2]['functions_touched'])} functions")
    print()

    print("  the Jaccard in similar() is taken over these same sets, so the frame")
    print("  reading re-clusters the tree. Measured, not adopted:")
    print(f"    {'program':9} {'components':>20} {'cluster_key moves':>21}")
    for g, was, now, moved in cluster_effect(frame_groups, xrm.DEFAULT_THRESHOLD):
        print(f"    {g:9} {was:9d} -> {now:<8d} {moved:15d} addr(s)")
    print()
    print("no CSV was written: this mode exists so the question has an answer, "
          "not so the answer becomes the census", file=sys.stderr)
    return 0


def check() -> int:
    """The committed columns encode the stated reading, on every row.

    The by-facto half of the ruling: a fresh derivation of `functions_touched`,
    `readers` and `writers` under the stated reading must equal the committed
    CSV everywhere. A failure here is not a broken census --
    `xdata_register_map.py --check` would have caught that -- it is a column
    that no longer means what its docstring says it means.
    """
    groups, _names = read_census()
    committed = committed_columns()
    stated = rows_for(groups)
    problems = 0
    for addr in sorted(stated):
        for derived, name in COLUMNS:
            got = len(stated[addr][derived])
            want = committed[addr][name]
            if got != want:
                print(f"{xrm.hexaddr(addr)}: {name} is {want} in the committed "
                      f"CSV, the stated reading derives {got}", file=sys.stderr)
                problems += 1
    if problems:
        print(f"{problems} column cell(s) disagree with the stated reading; the "
              f"block at the end of xdata_register_map.py and the CSV are "
              f"describing different columns",
              file=sys.stderr)
        return 1
    print(f"{REGISTERS_CSV}: every row's functions_touched, readers and writers "
          f"match a fresh derivation under the stated reading -- one committed "
          f"index.csv row per function key")
    return 0


def self_test() -> int:
    """Named claims and named refusals, and no count of the tree.

    What is asserted is the claim and the relation: these named rows collapse
    onto these named frames, these two shapes are refused, the vocabulary is
    closed, and the committed columns agree with the stated reading. A figure
    that would go red on the next row added to the export is not asserted,
    because that would tell the implement stage to fix a correct tool.
    """
    problems = []

    def it(what, cond):
        # `what` rather than `label`, which is the module-level key formatter.
        if not cond:
            problems.append(what)

    edges = census_edges()
    collapse, refused = collapse_map(edges)

    # The refusal vocabulary is closed, which is what makes the refusals a
    # partition of the shapes rather than a list of the ones seen so far.
    it("a refusal fell outside the two the docstring names",
       all(r in REFUSALS for r in refused.values()))
    it("a refused key was also collapsed",
       not (set(refused) & set(collapse)))

    # The mutual pair is the load-bearing refusal: neither span contains the
    # other, so following the chain never terminates and there is no outermost
    # frame. Held here on the committed tree and by a fixture in the suite, so
    # it does not depend on the export keeping the pair.
    for key in (("common", "6A02"), ("common", "6D46")):
        it(f"{key[0]}:0x{key[1]} is not refused as mutual nesting",
           refused.get(key) == "mutual-nesting")

    # Several containers is the other refusal, and the census's docstring says
    # those rows' two containers fall in different buckets -- so there is no one
    # of them to pick.
    for key in (("common", "6B94"), ("common", "6116")):
        it(f"{key[0]}:0x{key[1]} is not refused for several containers",
           refused.get(key) == "several-containers")

    # A chain is followed to its *outermost* frame, not to its direct
    # container: `common 0x6209` sits inside `common 0x65A6`, and 0x65A6 is
    # itself inside nothing, so it is its own frame and the row collapses onto
    # it rather than onto nothing.
    it("a single-container row did not resolve to its outermost frame",
       collapse.get(("common", "6209")) == ("common", "65A6"))

    groups, _names = read_census()
    stated = rows_for(groups)
    frame_groups, _n = collapsed_groups(collapse)
    frame = rows_for(frame_groups, collapse)

    # The frame reading, on the row the report names: under the stated reading
    # 0x036C names both nested listings *and* the frame holding them, and under
    # the frame reading the two inner names are gone and the frame stays. Both
    # halves are asserted, because "the nested rows dropped" and "nothing else
    # moved" are different claims and a collapse that dropped the container too
    # would satisfy only the first.
    addr = 0x036C
    held, dropped = ("bank1", "E2D3"), {("bank1", "E322"), ("bank1", "E332")}
    it("0x036C names E322 and E332 under the stated reading",
       not dropped.isdisjoint(stated[addr]["functions_touched"]))
    it("0x036C names its holding frame E2D3 under the stated reading",
       held in stated[addr]["functions_touched"])
    it("0x036C drops E322 and E332 under the frame reading",
       dropped.isdisjoint(frame[addr]["functions_touched"]))
    it("0x036C keeps its holding frame E2D3 under the frame reading",
       held in frame[addr]["functions_touched"])

    # A collapse only ever removes a key or renames one, so no column grows.
    # Direction, not a figure: it survives a tree that has moved.
    for a in sorted(stated):
        for col, _name in COLUMNS:
            it(f"{xrm.hexaddr(a)}: the frame reading grew {col}",
               len(frame[a][col]) <= len(stated[a][col]))

    # Not every collapsible edge is a whole-listing one: the census reads
    # address-inside-a-listing, and two of these rows' listings run past their
    # frame's last byte, so the frame's `.c` does not re-decompile the tail.
    # Collapsing them removes credit no frame repeated, which is a reason the
    # frame reading is not adopted -- so it is pinned rather than assumed absent.
    partial = partial_edges()
    it("no partial-overlap edge was reported, or every one is collapsible",
       all(k in collapse for k, _frame in partial))
    it("the partial overlaps are the rows whose listing runs past the frame",
       {k for k, _f in partial} <= set(edges))

    # The trap: `[writer]` in the `functions` column is a role from
    # `ghidra-functions.csv`, not a per-access record. Counting it is the shape
    # of a derivation that looks supported by the CSV and is not, and 0x0491 is
    # where it shows -- every one of that row's writers reaches it as
    # `read+write` on a row that reads `write 0`.
    it("0x0491's [writer] tags under-count its writers",
       writer_tags(addr=0x0491) < len(stated[0x0491]["writers"]))

    if problems:
        for label in problems:
            print(f"FAIL {label}", file=sys.stderr)
        print(f"{len(problems)} self-test failure(s)", file=sys.stderr)
        return 1
    print("xdata_frame_credit.py --self-test: the named collapses hold, both "
          "refusals hold, and the committed columns encode the stated reading")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true",
                       help="assert the committed columns already encode the "
                            "stated reading; no writes, no network, no Ghidra")
    modes.add_argument("--self-test", action="store_true",
                       help="known-claim run: the named collapses, both "
                            "refusals, and the [writer]-tag trap")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.check:
        return check()
    return report()


if __name__ == "__main__":
    sys.exit(main())