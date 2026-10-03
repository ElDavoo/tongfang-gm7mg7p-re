#!/usr/bin/env python3
"""A C-level XDATA access whose own listing does not seed DPTR with it.

The standing order in this repository is `.asm` right, `.c` a reading of it, and
the XDATA census counts the reading: `xdata_register_map.py`'s `refs` column is
`DAT_EXTMEM_xxxx` tokens plus the names in the generated symbol table, matched
over the decompiled C. That makes every `refs` figure a **lower bound on the
machine code** -- the right way round for a count, and the wrong way round for
a *claim that a byte is touched*. Nothing asked the opposite question of the
same corpus: a `.c` that names an address, where the `.asm` beside it holds no
`mov DPTR, #imm` seeding that address.

`bank1/E237.c` is the committed instance, and it says so itself: its annotation
plate records that the decompiled C "continues past 0xE27C with writes to
0x0680, 0x0681, 0x0683, 0x03A0 and 0x1C05 that this listing does not contain."
A hand annotation already documenting a C-level access with no listing
counterpart -- which is the shape, unmeasured until now.

**The four verdicts are what the method could establish, in that order, and
none of them is an absence.** They partition; the reader has to know which one
put a row in its bucket.

  * `beyond-listing-extent` -- the listing that seeds this address **begins
    exactly where this listing ends**. That is `ExportListing.java`'s
    `getFunctionContaining` (an address-range test against Ghidra's function
    boundary, bucketing instructions per entry point) against a decompiler that
    follows the flow graph: the exporter cut the function, the decompiler ran
    past the cut, and the C attributed the next listing's bytes to this one.
    For `bank1,E237` the extent is `[0xE237,0xE27D)` and the holder of all
    four addresses its plate names is `bank1/E27D`, whose listing starts at
    0xE27D. The `via` column carries that holder, so the claim is checkable
    rather than a bucket name.

    **The obvious form of this test is vacuous and is not used.** "The address
    is outside `[entry, end)`" classifies *every* row in the corpus: an XDATA
    byte is never numerically inside a CODE function's range, because XDATA and
    CODE are different address spaces sharing sixteen bits. This tool's first
    draft used that form and it held for every row the census found. Naming
    the successor is what makes the verdict say something.
  * `reaches-via-callee` -- a function this listing *transfers to* seeds the
    address, or its annotation comment names it. DPTR can legitimately arrive
    at the call from there. `via` says which of the two it was: a callee's
    listing is a machine witness, a callee's comment is a hand reading, and
    they are not pooled.
  * `seeded-elsewhere` -- some other committed listing seeds the address. The
    access is real in the corpus and this function's `.c` is credited with it;
    which listing the exporter attributed the seed to is the disagreement.
  * `no-witness` -- nothing in the corpus seeds the address and no callee
    names it. **"Not found by this method", never "the access is not there."**
    The decompiler reaches an address legitimately by arithmetic
    (`CONCAT11(r6, r5)`), by a callee's returned pointer, or by an `inc DPTR`
    walk, and none of those seeds DPTR with a literal. The walk is the common
    case and it is *recorded*, not counted: `walked_from` carries the seed one
    byte below whenever the listing has one, so the bucket that reads as
    "nothing is here" turns out to be dominated by a route this tool
    deliberately declines to treat as a witness.
    `xdata_register_map.xdata_space()` measures the walk form properly for the
    census; folding one into the other here would make the bucket mean two
    things.

**The witness is a `mov DPTR, #0x…` and nothing else**, matched with
`xdata_register_map.seed_of()`. That is the census's own predicate. On this
machine `0x90` `MOV DPTR,#imm16` is the only operand carrying a full 16-bit
address -- `ec/annotations/xdata-register-map.md` §7.1 records that from the
opcode map -- and Ghidra spells an eight-bit immediate the same way
(`anl A, #0x7c`), so a looser `#0x…` scan would have let an 8-bit constant
witness an XDATA byte.

**What this cannot see, and it is the case the issue that asked for this
started from.** The census is per *(function, address)*, so it says nothing
about *which* access inside the C is the disagreeing one. `pd/7B14.c` is the
worked case: it passes `DAT_EXTMEM_07c9` to `make_dptr_r6_minus_3_9028`, while
`pd/7B14.asm` builds the column byte with `clr A` / `add A, #0x1c` before that
call -- but `7B14.asm` seeds DPTR with 0x07C9 at a dozen other sites, so the
function-level question is answered "yes, it is seeded" and this tool files no
row. Settling it needs statement-level alignment between the decompile and the
listing, which is `docs/findings/7b14-07c9-token.md`'s subject and not
something a text census over the `.c` can do.

**This is a census, not a gate.** It reports, and its CSV is a table of the
committed tree. What is asserted is in `--self-test` and in
`test_c_asm_counterpart.py`, and it is the claim -- the E237 rows, the fixture
shapes, the 7B14 non-row -- never a count of the tree.

Usage:
    python3 ec/tools/c_asm_counterpart.py              # census, write nothing
    python3 ec/tools/c_asm_counterpart.py --report     # write the CSV
    python3 ec/tools/c_asm_counterpart.py --check      # recompute and diff
    python3 ec/tools/c_asm_counterpart.py --self-test  # known answers
"""
import argparse
import collections
import csv
import os
import re
import tempfile
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import call_graph as cg                                             # noqa: E402
import verify_reassembly as V                                      # noqa: E402
import xdata_register_map as X                                      # noqa: E402

REPO = cg.REPO
DECOMPILED = cg.DECOMPILED
LISTING_INDEX = os.path.join(DECOMPILED, "listing-index.csv")
ANNOTATIONS = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
REPORT = os.path.join(REPO, "ec", "ghidra", "c-asm-counterpart.csv")

COLUMNS = ["program", "addr", "name", "xdata_addr", "symbol", "spellings",
           "c_tokens", "listing_extent", "index_size", "listing_seeds",
           "walked_from", "transfers", "verdict", "via"]

VERDICTS = ("beyond-listing-extent", "reaches-via-callee", "seeded-elsewhere",
            "no-witness")


def listing_extent(path):
    """`[entry, end)` for one `.asm`, from its own first and last instruction.

    Read from the address and byte columns rather than the mnemonic, and
    through `verify_reassembly.parse_listing` because that is the committed
    reader of the same columns -- a second parse here is a second place for the
    two to disagree about how long an instruction is. The end is one past the
    *last* instruction's last byte, so a listing whose last instruction is a
    one-byte `ret` is not credited with an extra.

    The two ends are read separately and on purpose. A listing is not
    necessarily contiguous -- 149 of this tree's listing lines are not, because
    a listing legitimately includes jump tables and string data -- so the end
    is the last instruction's address and not the entry plus a size.
    """
    entry, end = None, None
    for addr, hexbytes, _mnem, _ops in V.parse_listing(path):
        entry = addr if entry is None else entry
        end = addr + len(hexbytes) // 2
    return None if entry is None else (entry, end)


def inspect_listing(program, addr):
    """`{address: (mnemonic, operands)}` for one listing, handle closed.

    A named reader rather than a bare `parse_listing()` call at each site,
    because `parse_listing()` takes a *path* and the two callers here want the
    same listing keyed by address -- and because it is the one place the handle
    is provably closed. `verify_reassembly.parse_listing`'s own docstring
    records that leak: it was invisible until a unit test ran it under
    unittest's warning filters and printed one `ResourceWarning` per listing.
    """
    path = os.path.join(DECOMPILED, program, addr + ".asm")
    with open(path, errors="replace") as handle:
        text = handle.read()
    parsed = V.parse_listing_str(text)
    return {at: (mnem, ops) for at, _hexbytes, mnem, ops in parsed}


def immediates_of(path):
    """The addresses this listing loads into DPTR: `{mov DPTR, #0x…}` seeds.

    Matched with `xdata_register_map.seed_of()` and its `DPTR_IMM`, which is
    the census's own predicate, so the two tools cannot come to disagree about
    what counts as a direct XDATA address. The alternative -- scanning the
    operand column for any `#0x…` -- is what this started as and is wrong:
    Ghidra spells an **eight-bit** immediate the same way (`anl A, #0x7c` in
    `bank1/E237.asm`, `add A, #0x1c` in `pd/7B14.asm`), so `anl A, #0xc9` would
    have witnessed XDATA 0x00C9 and the bucket would have been quietly wrong.
    `mov DPTR,#imm16` is the only operand on this machine that carries a full
    16-bit address at all -- `ec/annotations/xdata-register-map.md` §7.1
    records that from the opcode map -- so it is the whole of the witness.

    The operand column is reached by position exactly as
    `xdata_register_map.read_asm` reaches it: the exporter pads the byte
    column with `-` to a fixed width, so a fixed column count drops every one-
    and two-byte instruction -- which is `movx` and `inc DPTR`, precisely the
    two this repository's XDATA argument is made of.
    """
    found = set()
    try:
        handle = open(path, errors="replace")
    except OSError:
        return found
    with handle:
        for line in handle:
            if line.startswith(";") or not line.strip():
                continue
            tok = line.split()
            i, width = 1, 0
            while i < len(tok) and width < 3 and X.ASM_OPCODE.match(tok[i]):
                i += 1
                width += 1
            if i >= len(tok):
                continue
            seed = X.seed_of(tok[i], " ".join(tok[i + 1:]).strip())
            if seed is not None:
                found.add(seed)
    return found


def witness_index(listing_rows, root=None):
    """`{address: {(program, addr), …}}`: which listings seed which address.

    One pass over the corpus rather than a re-read of each callee's listing on
    demand. The lookup is asked the same question for every row, and a
    function with forty transfers would otherwise re-read forty files per row.

    The tree it was built from is hung off the returned mapping, because
    `verdict_of()` needs to open the holder's listing to read its entry point
    and a `defaultdict` is the only object here that survives being carried
    through `rows_for()` unchanged.
    """
    root = root if root is not None else DECOMPILED
    out = _Witnesses()
    out.root = root
    for row in listing_rows:
        key = (row["program"], X.bare(row["addr"]))
        path = os.path.join(root, row["program"], row["addr"] + ".asm")
        for addr in immediates_of(path):
            out[addr].add(key)
    return out


class _Witnesses(collections.defaultdict):
    """A `defaultdict(set)` carrying the tree it was read from."""

    def __init__(self):
        super().__init__(set)
        self.root = DECOMPILED


def name_addr_table(symbols):
    """Symbol name -> address, for the second spelling the census matches."""
    return {name: addr for addr, name in symbols.items()}


def symbol_of(addr, symbols):
    """The generated symbol table's name for an address, or the empty string."""
    return symbols.get(addr, "")


def c_mentions(body, pattern, names):
    """`{address: (count, {spellings})}` for one decompiled C body.

    The body is what the census reads, and it is what this tool reads: the
    annotation plate at the top of every committed `.c` is this repository's
    own prose, and a plate that quotes `DAT_EXTMEM_0a56` is a human writing
    about the firmware rather than the firmware touching a byte. Reading the
    whole file would let `bank1/E237.c`'s own sentence about 0x0680 count as
    the access it describes.
    """
    out = collections.defaultdict(lambda: [0, set()])
    for m in pattern.finditer(body):
        token = m.group(1) or m.group(2)
        addr = int(token, 16) if m.group(1) else names.get(token)
        if addr is None:
            continue
        entry = out[addr]
        entry[0] += 1
        entry[1].add(token)
    return out


def comment_names(comment, addr, names):
    """True if a hand annotation comment names this address as a number.

    The weaker of the two `reaches-via-callee` witnesses, and reported
    separately from the listing one for that reason: a comment is a reading,
    and `.asm` right / `.c` a reading does not extend to treating a reading as
    a machine witness. The number is matched as `0x…` or bare four hex digits
    with a word boundary, so 0x07C9 does not match inside 0x07C90.
    """
    if not comment:
        return False
    digits = "%04X" % addr
    if re.search(r"0[xX]0*%s\b" % digits, comment):
        return True
    name = names.get(addr)
    return bool(name) and re.search(r"\b%s\b" % re.escape(name), comment)


def walked_from(held, addr):
    """`addr - 1` when this listing seeds it, else None: the `inc DPTR` form.

    **A column, never a fifth verdict.** The walk is a real route to the byte
    and `xdata_register_map.xdata_space()` measures it properly for the census,
    but it is not a listing counterpart: no `mov DPTR,#imm` in this listing
    names the address, which is the whole of what the census asks. Recording
    that the seed one byte below is present says why most `no-witness` rows are
    unremarkable without pretending the method found a witness -- and the
    bucket that reads as "nothing is here" turns out to be dominated by a
    route this tool deliberately declines to count.
    """
    return "0x%04X" % (addr - 1) if (addr - 1) in held else ""


def successor_holders(key, addr, extent, witnesses):
    """Holders of `addr` whose listing begins exactly where this one ends.

    Every holder is examined, not the first one: `bank1/E237`'s address 0x0680
    is seeded by fourteen listings in the committed tree, and the one the
    verdict is about is the one at 0xE27D, which is not the first in sort
    order. Taking the first holder and asking whether it happens to abut would
    have missed every instance of the case the verdict names.
    """
    if extent is None:
        return []
    out = []
    for holder in sorted(witnesses.get(addr, ())):
        if holder[0] != key[0]:
            # A `common` row and a bank row share an address space at runtime
            # but not on paper, and reading the pair as one would manufacture a
            # successor that is not there.
            continue
        path = os.path.join(witnesses.root, holder[0], holder[1] + ".asm")
        held = listing_extent(path)
        if held is not None and held[0] == extent[1]:
            out.append(holder)
    return out


def verdict_of(key, addr, extent, targets, witnesses, names, comments):
    """`(verdict, via)` for one (function, address) the listing cannot witness.

    Read in order, most specific first, because the four answer different
    questions and the reader has to know which one put the row in its bucket.

    `beyond-listing-extent` is the `ExportListing.java` case, and it is stated
    so that it is not vacuous: the holder's listing *begins exactly where this
    one ends*. A plain "the address is outside `[entry, end)`" would classify
    every row in the corpus -- an XDATA byte is never numerically inside a
    CODE function's range, because XDATA and CODE are different address spaces
    sharing sixteen bits -- and a verdict that holds for everything says
    nothing. Naming the successor makes the claim specific: the exporter cut
    the function at 0xE27D, the decompiler followed past the cut, and the C
    attributed the next listing's bytes to this one.

    `reaches-via-callee` comes next because a callee this listing *transfers
    to* is the case where DPTR legitimately arrives at the call, and it is the
    more specific reading of "some other listing seeds it". `via` says which
    of the two witnesses it was -- a callee's listing seeds it (a machine
    witness) or a callee's annotation comment names it (a hand reading). They
    are not pooled: `.asm` right and `.c` a reading does not extend to treating
    a reading as a witness.
    """
    abut = successor_holders(key, addr, extent, witnesses)
    if abut:
        return "beyond-listing-extent", " ".join(
            "%s:%s/listing" % k for k in abut)
    reached = callee_witnesses(targets, addr, witnesses, names, comments)
    if reached:
        return "reaches-via-callee", " ".join(
            "%s:%s/%s" % (k[0], k[1], how) for k, how in reached)
    holders = sorted(witnesses.get(addr, ()))
    if holders:
        return "seeded-elsewhere", " ".join("%s:%s/listing" % k for k in holders)
    return "no-witness", ""


def callee_witnesses(targets, addr, witnesses, names, comments):
    """`[(callee_key, how)]` for transfers whose target names this address.

    `how` is `listing` or `comment`; see `verdict_of` for why they are not
    pooled.
    """
    out = []
    for key in sorted(targets):
        if key in witnesses.get(addr, ()):
            out.append((key, "listing"))
        elif comment_names(comments.get(key), addr, names):
            out.append((key, "comment"))
    return out


def census(index_rows, listing_rows, ann_rows, symbols, listings, root=None):
    """One row per (function, address) the C names and the listing cannot witness.

    Every input is a committed file: `listing-index.csv`, the `.c`/`.asm` trees,
    `ghidra-functions.csv` and the generated symbol table. Nothing here observes
    hardware, and nothing re-runs the decompiler. `root` is the tree to read,
    which is the temp directory `--self-test` builds its fixture in and
    `DECOMPILED` everywhere else.
    """
    root = root if root is not None else DECOMPILED
    names = name_addr_table(symbols)
    pattern = X.occurrence_re(symbols)
    extent_by_key = {}
    index_size = {}
    for row in listing_rows:
        key = (row["program"], X.bare(row["addr"]))
        index_size[key] = row["size"]
        path = os.path.join(root, row["program"], row["addr"] + ".asm")
        if os.path.isfile(path):
            extent = listing_extent(path)
            if extent is not None:
                extent_by_key[key] = extent
    witnesses = witness_index(listing_rows, root)
    comments = {(r["scope"], X.bare(r["addr"])): r.get("comment", "")
                for r in ann_rows if r.get("comment")}

    out = []
    for row in index_rows:
        program, addr = row["program"], X.bare(row["addr"])
        key = (program, addr)
        c_path = os.path.join(root, program, addr + ".c")
        asm_path = os.path.join(root, program, addr + ".asm")
        if not (os.path.isfile(c_path) and os.path.isfile(asm_path)):
            continue
        with open(c_path, errors="replace") as f:
            body = X.body_of(X.strip_comments(f.read()))
        found = c_mentions(body, pattern, names)
        if not found:
            continue
        held = immediates_of(asm_path)
        listing = listings.get(key)
        targets = listing.targets if listing is not None else ()
        extent = extent_by_key.get(key)
        for addr_x, (count, spellings) in sorted(found.items()):
            if addr_x in held:
                continue
            verdict, via = verdict_of(key, addr_x, extent, targets, witnesses,
                                      names, comments)
            out.append({
                "program": program,
                "addr": addr,
                "name": row["name"],
                "xdata_addr": "0x%04X" % addr_x,
                "symbol": symbol_of(addr_x, symbols),
                "spellings": " ".join(sorted(spellings)),
                "c_tokens": str(count),
                "listing_extent": "" if extent is None else
                                  "[0x%04X,0x%04X)" % extent,
                "index_size": index_size.get(key, ""),
                "listing_seeds": " ".join("0x%04X" % a
                                        for a in sorted(held)),
                "walked_from": walked_from(held, addr_x),
                "transfers": " ".join("%s:%s" % k for k in sorted(targets)),
                "verdict": verdict,
                "via": via,
            })
    return out


def context():
    """The shared `call_graph` pass, so the transfer set is the graph's own.

    `listings()` resolves each listing's transfers through the same
    `Index.resolve` the rest of the repository uses, which is what carries a
    `bank0` call at a `common` address to the `common` row. Resolving transfer
    targets here instead would be a second implementation of a rule that
    already has one.
    """
    index = cg.load_index()
    _edges, _unresolved, _orphans, _total, listings = cg.scan(index)
    return index, listings


def rows_for(index, listings, symbols=None, listing_rows=None, ann_rows=None,
             root=None):
    """The census over the committed tree, or over a fixture the caller supplies.

    The parameters exist so `--self-test` can drive this same path over a
    hand-built tree: a check that rebuilt the population itself could not tell
    a regression in the walk from a regression in the code that feeds it.
    """
    symbols = symbols if symbols is not None else X.load_symbols()
    listing_rows = listing_rows if listing_rows is not None \
        else read_csv(LISTING_INDEX)
    ann_rows = ann_rows if ann_rows is not None else read_csv(ANNOTATIONS)
    return census(index.rows, listing_rows, ann_rows, symbols, listings,
                  root=root)


def render(rows):
    buf = []
    w = csv.DictWriter(_Sink(buf), fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return "".join(buf)


class _Sink:
    def __init__(self, sink):
        self._sink = sink

    def write(self, text):
        self._sink.append(text)


def diff_table(have, want):
    """The per-row, per-cell differences between two renderings.

    Never decides, for the reason `citation_gap_scan.diff_table` gives:
    asserting against a re-implementation of the diff would prove the
    re-implementation works.
    """
    have_rows = list(csv.DictReader(have.splitlines()))
    want_rows = list(csv.DictReader(want.splitlines()))
    lines, shown = [], 0
    for a, b in zip(have_rows, want_rows):
        if a != b:
            lines.append("  %s,%s %s:" % (a["program"], a["addr"],
                                          a["xdata_addr"]))
            for k in COLUMNS:
                if a.get(k) != b.get(k):
                    lines.append("    %-18s committed %r, recomputed %r"
                                 % (k, a.get(k), b.get(k)))
            shown += 1
            if shown >= 20:
                lines.append("  ... more")
                break
    if len(have_rows) != len(want_rows):
        lines.append("  row count: committed %d, recomputed %d"
                     % (len(have_rows), len(want_rows)))
    return lines


def check_table(have, want):
    """`(exit_code, lines)`: what `--check` returns, and the lines it prints.

    Byte equality is the pass condition, for `citation_gap_scan.check_table`'s
    reason -- a table whose rows read the same while its bytes do not is a
    table this tool did not write.
    """
    if have == want:
        return 0, []
    lines = diff_table(have, want)
    if not lines:
        lines = ["  bytes differ and every row parses equal: line endings, a "
                 "trailing blank line, column order or quoting differ from "
                 "what this tool writes"]
    return 1, lines


def extent_width(r):
    """The `.asm` extent's length, or None when the listing has no instruction.

    Read back out of the rendered `listing_extent` rather than kept alongside
    it, so the column a reader sees is the column the figure is taken from and
    the two cannot be formatted differently.
    """
    text = r["listing_extent"]
    if not text:
        return None
    lo, hi = text.strip("[)").split(",0x")
    return int(hi, 16) - int(lo[2:], 16)


def report(rows):
    """The census, the split, and the limits that make it readable."""
    tally = collections.Counter(r["verdict"] for r in rows)
    files = {(r["program"], r["addr"]) for r in rows}
    by_scope = collections.Counter(p for p, _a in files)
    wider = sum(1 for r in rows
                if extent_width(r) is not None
                and r["index_size"] != str(extent_width(r)))
    print("c_asm_counterpart.py -- a C-level XDATA access the listing beside it "
          "does not seed DPTR with")
    print()
    print("  %-52s %6d" % ("(function, address) rows", len(rows)))
    print("  %-52s %6d" % ("  over .c files carrying at least one", len(files)))
    print("  %-52s %6d" % ("  by program: " + ", ".join(
        "%s %d" % kv for kv in sorted(by_scope.items())), len(by_scope)))
    print()
    for verdict in VERDICTS:
        print("  %-52s %6d" % ("verdict %s" % verdict, tally.get(verdict, 0)))
    print("  %-52s %6d" % ("  the four verdicts add up to the row count",
                           sum(tally.values())))
    print()
    print("  %-52s %6d" % ("rows where listing-index.csv's `size` disagrees "
                           "with the .asm's own extent", wider))
    print()
    no_witness = [r for r in rows if r["verdict"] == "no-witness"]
    walked = [r for r in no_witness if r["walked_from"]]
    print()
    print("  %-52s %6d" % ("of the no-witness rows, the listing seeds the byte "
                           "BELOW the address", len(walked)))
    print("  %-52s %6d" % ("  ... and seeds nothing at or below it",
                           len(no_witness) - len(walked)))
    print("  no-witness rows, read one by one:")
    for r in no_witness:
        print("    %s/%s.c %s (%d token(s), %s): seeds %s%s"
              % (r["program"], r["addr"], r["xdata_addr"], int(r["c_tokens"]),
                 r["spellings"], r["listing_seeds"] or "nothing at all",
                 "" if not r["walked_from"]
                 else ", i.e. one below it -- the `inc DPTR` walk"))
    print()
    print("  limit: `no-witness` is NOT found by this method. The decompiler")
    print("  reaches an address legitimately by arithmetic, by a callee's")
    print("  returned pointer, or by an `inc DPTR` walk -- none of which seeds")
    print("  DPTR with a literal. This tool does not measure the walk form;")
    print("  `xdata_register_map.xdata_space()` does, and the two are not pooled.")
    print("  limit: `beyond-listing-extent` is a fact about ExportListing.java's")
    print("  `getFunctionContaining` bucketing against a decompiler that follows")
    print("  the flow graph, not a claim that the decompile is wrong. `via` names")
    print("  the holder whose listing begins where this one ends. The extent is")
    print("  read from the .asm's own last instruction; listing-index.csv's")
    print("  `size` is carried beside it and the two disagree on the rows counted")
    print("  above.")
    print("  limit: `reaches-via-callee` separates a callee whose LISTING seeds")
    print("  the address (a machine witness) from one whose COMMENT names it (a")
    print("  hand reading). The `via` column says which was which.")
    print("  limit: the census is per (FUNCTION, ADDRESS). It says nothing about")
    print("  which access inside the C is the disagreeing one -- `pd/7B14.c`'s")
    print("  0x07C9 is not in it, because `pd/7B14.asm` does seed that address")
    print("  elsewhere. See docs/findings/7b14-07c9-token.md.")
    print("  limit: this is a text measurement over committed files. No register")
    print("  status is changed, no listing is re-read, no live test is run, and")
    print("  nothing is observed on hardware.")


def check():
    index, listings = context()
    rows = rows_for(index, listings)
    text = render(rows)
    if not os.path.isfile(REPORT):
        print("  FAIL no report at %s; run c_asm_counterpart.py --report"
              % os.path.relpath(REPORT, REPO))
        return 1
    with open(REPORT, newline="") as f:
        have = f.read()
    rc, lines = check_table(have, text)
    if rc:
        for line in lines:
            print(line)
        print("c-asm-counterpart.csv differs from the committed listings; "
              "re-run with --report", file=sys.stderr)
        return 1
    tally = collections.Counter(r["verdict"] for r in rows)
    print("  c/asm counterpart scan: %d row(s); verdicts %s"
          % (len(rows), ", ".join("%d %s" % (v, k)
                                   for k, v in sorted(tally.items()))))
    print("  all checks passed")
    return 0


# --------------------------------------------------------------------------
# --self-test
# --------------------------------------------------------------------------

def read_csv(path):
    """Committed CSV rows, read strictly.

    `strict=True` is `build_ec_decompile.read_index`'s point rather than
    tidiness: csv's default reader ends a row early on a bad quote and hands
    back a short one, so a quoting mistake in a committed CSV would make every
    count taken from it quietly smaller than the file.
    """
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def fixture(program_addrs, root):
    """An `Index`, its listing map, and a listing index for a temp tree.

    `program_addrs` is `[(program, addr)]`. The listing index is derived from
    the `.asm` files actually written, so a fixture cannot hand-write a `size`
    that the bytes disagree with -- which is the mistake `listing-index.csv`
    itself makes on some rows, and the reason this tool reads the extent from
    the bytes instead.
    """
    index_rows, listing_rows = [], []
    for program, addr in program_addrs:
        path = os.path.join(root, program, addr + ".asm")
        entry = int(addr, 16)
        extent = listing_extent(path)
        size = 0 if extent is None else extent[1] - entry
        index_rows.append({"program": program, "addr": addr,
                           "name": "f_" + addr, "size": str(size),
                           "out_file": "%s/%s.c" % (program, addr)})
        listing_rows.append({"program": program, "addr": addr,
                             "name": "f_" + addr, "size": str(size),
                             "out_file": "%s/%s.asm" % (program, addr)})
    index = cg.Index(index_rows)
    # `root` has to reach `scan()` too, not just the census: it walks the
    # listing tree itself, and leaving it on the committed directory would give
    # the fixture the committed tree's transfer graph and silently answer a
    # different question.
    _edges, _unresolved, _orphans, _total, listings = cg.scan(index, root)
    return index, listings, listing_rows


def decompiled(addr, name, body):
    """A decompiled C in the exporter's shape, plate and body both.

    The plate mentions an address on purpose. A reader that scanned the whole
    file instead of `body_of(strip_comments(...))` would count this prose as a
    machine access, which is the mistake `xdata_register_map.strip_comments`
    exists to prevent and this tool inherits.
    """
    return ("// pd @ %s   %s\n\n/* plate mentioning DAT_EXTMEM_07c9 and 0x07c9 */\n"
            "void %s(void)\n\n{\n%s}\n" % (addr, name, name, body))


def self_test():
    """Known answers, oracles stated from committed inputs and the bytes.

    Never recorded from this tool. A self-test whose oracle came out of the
    code it is testing asserts nothing -- the note `citation_gap_scan.self_test`
    and `disasm8051.self_test` both make about their own digests.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    # ---- the witness form, and the 16-bit operand it turns on -------------
    # Transcribed from `bank1/E237.asm` and `pd/7B14.asm`. The 8-bit cases are
    # the load-bearing ones: `mov DPTR,#0x7c9` and `anl A,#0x7c` are spelled
    # the same way by the exporter, so only the mnemonic tells them apart.
    asm_path = os.path.join(DECOMPILED, "bank1", "E237.asm")
    with tempfile.TemporaryDirectory() as tmp:
        listing = os.path.join(tmp, "T.asm")
        with open(listing, "w") as f:
            f.write("; header\n"
                    "0000     90 07 c9 mov      DPTR, #0x7c9\n"
                    "0003     e0 - -   movx     A, @DPTR\n"
                    "0004     54 7c -  anl      A, #0x7c\n"
                    "0006     30 e1 13 jnb      0xe1, 0x001b\n"
                    "0009     80 08 -  sjmp     0x0013\n"
                    "000b     12 90 28 lcall    0x9028\n"
                    "000e     22 - -   ret      \n")
        assert_that(immediates_of(listing) == {0x07C9},
                    "the witness is a `mov DPTR, #0x…` seed and nothing else: "
                    "the same listing's `anl A, #0x7c`, `jnb 0xe1, 0x001b`, "
                    "`sjmp 0x0013` and `lcall 0x9028` seed nothing, so an "
                    "eight-bit constant and a transfer target cannot witness an "
                    "XDATA byte -- all four transcribed from bank1/E237.asm "
                    "and pd/7B14.asm")
        assert_that(X.DPTR_IMM.match("DPTR, #0x7c9") is not None
                    and X.DPTR_IMM.match("DPTR, #0x7c90") is not None,
                    "and `DPTR_IMM` is the census's own pattern rather than a "
                    "second one: it reads the unpadded `0x7c9` and the padded "
                    "`0x7c90` alike, as the exporter writes both")

        extent_listing = os.path.join(tmp, "E.asm")
        with open(extent_listing, "w") as f:
            f.write("; header\n"
                    "E000     90 07 c9 mov      DPTR, #0x7c9\n"
                    "E003     e0 - -   movx     A, @DPTR\n"
                    "E004     22 - -   ret      \n")
        assert_that(listing_extent(extent_listing) == (0xE000, 0xE005),
                    "the extent is one past the last instruction's last byte, "
                    "so a trailing 1-byte `ret` is not credited with an extra")
        assert_that(immediates_of(extent_listing) == {0x07C9},
                    "and a listing of `mov`/`movx`/`ret` witnesses 0x07C9")
        with open(extent_listing, "w") as f:
            f.write("; header only\n")
        assert_that(listing_extent(extent_listing) is None
                    and immediates_of(extent_listing) == set(),
                    "a listing with no instruction has no extent and witnesses "
                    "nothing -- reported as one, not as size zero")

    # ---- the fixture tree -----------------------------------------------
    # One shape per verdict, and each reached by a different structure rather
    # than by a threshold. `bank0/E237` and its successor `bank0/E23C` are the
    # committed pair's shape at fixture addresses; the rest are synthetic.
    symbols = {0x07C9: "DAT_EXTMEM_07c9", 0x0391: "DAT_EXTMEM_0391",
               0x0680: "DAT_EXTMEM_0680", 0x0683: "DAT_EXTMEM_0683",
               0x1ABC: "DAT_EXTMEM_1abc"}
    scratch = tempfile.TemporaryDirectory()
    try:
        root = scratch.name
        os.makedirs(os.path.join(root, "pd"))
        os.makedirs(os.path.join(root, "bank0"))

        def write(program, addr, body, asm_lines):
            with open(os.path.join(root, program, addr + ".c"), "w") as f:
                f.write(decompiled(addr, "f_" + addr, body))
            with open(os.path.join(root, program, addr + ".asm"), "w") as f:
                f.write("".join(asm_lines))

        # 1. beyond-listing-extent. E237's listing ends at 0xE23C and E23C's
        #    begins there, seeding the byte E237's C writes -- which is what
        #    committed `bank1/E237` / `bank1/E27D` do at 0xE27D.
        write("bank0", "E237", "  DAT_EXTMEM_0680 = 4;\n",
              ["E237     90 03 91 mov      DPTR, #0x391\n",
               "E23A     e0 - -   movx     A, @DPTR\n",
               "E23B     22 - -   ret      \n"])
        write("bank0", "E23C", "  return 0;\n",
              ["E23C     90 06 80 mov      DPTR, #0x680\n",
               "E23F     f0 - -   movx     @DPTR, A\n",
               "E240     22 - -   ret      \n"])
        # 2. reaches-via-callee, machine witness. The C names 0x07C9; this
        #    listing does not seed it, but the function it transfers to does.
        write("pd", "7C00", "  cVar2 = DAT_EXTMEM_07c9;\n",
              ["7C00     12 90 30 lcall    0x9030\n",
               "7C03     22 - -   ret      \n"])
        write("pd", "9030", "  DAT_EXTMEM_07c9 = 1;\n",
              ["9030     90 07 c9 mov      DPTR, #0x7c9\n",
               "9033     22 - -   ret      \n"])
        # 3. reaches-via-callee, hand reading. Same address, a callee that
        #    seeds nothing, and an annotation comment that names it.
        write("pd", "7D00", "  cVar2 = DAT_EXTMEM_07c9;\n",
              ["7D00     12 90 28 lcall    0x9028\n",
               "7D03     22 - -   ret      \n"])
        write("pd", "9028", "  return 0;\n",
              ["9028     ff - -   mov      R7, A\n",
               "9029     22 - -   ret      \n"])
        # 4. seeded-elsewhere. A listing three functions away holds the seed,
        #    so the access is real and only the attribution is in question.
        write("pd", "7E00", "  DAT_EXTMEM_0683 = 10;\n",
              ["7E00     90 06 82 mov      DPTR, #0x682\n",
               "7E03     22 - -   ret      \n"])
        write("pd", "7F00", "  return 0;\n",
              ["7F00     22 - -   ret      \n"])
        # 5. no-witness. No listing in the tree seeds it and no callee names
        #    it -- which is a statement about this method, not about the byte.
        write("pd", "7A00", "  DAT_EXTMEM_1abc = 1;\n",
              ["7A00     22 - -   ret      \n"])
        # 6. The negative case: the C names an address its own listing seeds,
        #    so no row is filed at all.
        write("pd", "7900", "  DAT_EXTMEM_0683 = 10;\n",
              ["7900     90 06 83 mov      DPTR, #0x683\n",
               "7903     22 - -   ret      \n"])

        keys = [("bank0", "E237"), ("bank0", "E23C"), ("pd", "7900"),
                ("pd", "7A00"), ("pd", "7C00"), ("pd", "7D00"),
                ("pd", "7E00"), ("pd", "7F00"), ("pd", "9028"), ("pd", "9030")]
        index, listings, listing_rows = fixture(keys, root)
        ann_rows = [
            {"scope": "pd", "addr": "9028",
             "comment": "Takes the column byte in A; 0x07C9 is the record "
                        "index its callers pass in R6."},
        ]
        rows = rows_for(index, listings, symbols, listing_rows, ann_rows,
                        root=root)
        by = {(r["program"], r["addr"], r["xdata_addr"]): r for r in rows}

        beyond = by[("bank0", "E237", "0x0680")]
        assert_that(beyond["verdict"] == "beyond-listing-extent"
                    and beyond["via"] == "bank0:E23C/listing"
                    and beyond["listing_extent"] == "[0xE237,0xE23C)"
                    and beyond["listing_seeds"] == "0x0391"
                    and beyond["transfers"] == "",
                    "the E237 shape: a C writing 0x0680, a listing running "
                    "[0xE237,0xE23C) that seeds 0x0391 and transfers to nothing, "
                    "and a holder that begins at 0xE23C -- so the verdict names "
                    "the listing the exporter cut the decompile short of")
        assert_that(by[("pd", "7C00", "0x07C9")]["verdict"]
                    == "reaches-via-callee"
                    and by[("pd", "7C00", "0x07C9")]["via"]
                    == "pd:9030/listing",
                    "an address seeded by a function this listing transfers to "
                    "is `reaches-via-callee/listing` -- a machine witness")
        assert_that(by[("pd", "7D00", "0x07C9")]["verdict"]
                    == "reaches-via-callee"
                    and by[("pd", "7D00", "0x07C9")]["via"]
                    == "pd:9028/comment",
                    "and one named only by a callee's annotation comment is "
                    "`reaches-via-callee/comment` -- a hand reading, reported "
                    "apart rather than pooled with the machine one")
        assert_that(by[("pd", "7E00", "0x0683")]["verdict"] == "seeded-elsewhere"
                    and by[("pd", "7E00", "0x0683")]["via"]
                    == "pd:7900/listing",
                    "an address seeded by a listing this one does not transfer "
                    "to is `seeded-elsewhere`, and `via` names the holder")
        assert_that(by[("pd", "7A00", "0x1ABC")]["verdict"] == "no-witness"
                    and by[("pd", "7A00", "0x1ABC")]["via"] == "",
                    "and an address nothing in the tree seeds is `no-witness` "
                    "with an empty `via` -- the bucket that means not found by "
                    "this method")
        assert_that(("pd", "7900", "0x0683") not in by,
                    "a C that names an address its own listing seeds produces "
                    "no row at all -- this is not a census of every XDATA token")
        assert_that({r["verdict"] for r in rows} == set(VERDICTS),
                    "all four verdicts are reached, each by a different "
                    "structure rather than by a threshold")
        assert_that(comment_names("writes 0x07C90 bytes", 0x07C9, {}) is False
                    and comment_names("writes 0x07C9 bytes", 0x07C9, {}) is True,
                    "a comment naming 0x07C90 does not witness 0x07C9 -- the "
                    "word boundary is what keeps one address from standing in "
                    "for the byte above it")
        assert_that(walked_from({0x08D0}, 0x08D1) == "0x08D0"
                    and walked_from({0x08D0}, 0x08D0) == ""
                    and walked_from(set(), 0x08D1) == ""
                    and by[("pd", "7A00", "0x1ABC")]["walked_from"] == "",
                    "`walked_from` names the seed one byte below and nothing "
                    "else: 0x08D0 walked to 0x08D1 is the `inc DPTR` form the "
                    "listing does record, while an address it seeds itself and "
                    "one with no seed at all both read empty -- so the column "
                    "explains rows rather than witnessing them")
        assert_that(verdict_of(("pd", "7A00"), 0x0391, None, set(), {}, {}, {},
                               ) == ("no-witness", ""),
                    "and `verdict_of` answers the same for a caller that passes "
                    "no extent and no transfers, rather than crashing on them")

        # A tree where every C symbol has a listing counterpart: zero rows, so
        # `clean` cannot be confused with `never ran`. The same guard
        # `build_ec_decompile.py --self-test` and `citation_gap_scan.py` carry.
        clean_scratch = tempfile.TemporaryDirectory()
        try:
            croot = clean_scratch.name
            os.makedirs(os.path.join(croot, "pd"))
            with open(os.path.join(croot, "pd", "0001.c"), "w") as f:
                f.write(decompiled("0001", "clean", "  DAT_EXTMEM_0391 = 1;\n"))
            with open(os.path.join(croot, "pd", "0001.asm"), "w") as f:
                f.write("0001     90 03 91 mov      DPTR, #0x391\n"
                        "0004     22 - -   ret      \n")
            c_index, c_listings, c_rows = fixture([("pd", "0001")], croot)
            assert_that(rows_for(c_index, c_listings, symbols, c_rows, [],
                                 root=croot) == [],
                        "a tree where every C symbol has a listing counterpart "
                        "produces zero rows, so a clean result cannot be "
                        "confused with a walk that never ran")
        finally:
            clean_scratch.cleanup()
    finally:
        scratch.cleanup()

    # ---- the committed claims -------------------------------------------
    index, listings = context()
    rows = rows_for(index, listings)
    by = {(r["program"], r["addr"], r["xdata_addr"]): r for r in rows}

    # E237 is the instance the committed annotation already described, and the
    # tool's job is to say *which* listing holds the seeds it does not -- not
    # to restate the annotation. Every address in that plate is checked, and
    # the one it names that this listing does seed is not in the table.
    for x in ("0x03A0", "0x0680", "0x0683", "0x1C05"):
        row = by.get(("bank1", "E237", x))
        assert_that(row is not None
                    and row["verdict"] == "beyond-listing-extent"
                    and row["via"] == "bank1:E27D/listing"
                    and row["listing_extent"] == "[0xE237,0xE27D)",
                    "bank1/E237.c's %s is `beyond-listing-extent` with "
                    "`bank1/E27D` as the holder -- its listing runs "
                    "[0xE237,0xE27D) and bank1/E27D.asm begins at 0xE27D, so "
                    "the decompile ran past the function boundary the listing "
                    "exporter cut at. The four addresses its own plate names "
                    "as past 0xE27C" % x)
    assert_that(("bank1", "E237", "0x1C00") not in by
                and ("bank1", "E237", "0x0391") not in by,
                "and the addresses E237's listing DOES seed -- 0x1C00, 0x0391 "
                "among them -- file no row, so the table is the disagreement "
                "and not a copy of the listing's seeds")
    assert_that(by[("bank1", "E237", "0x03A0")]["index_size"] == "70",
                "E237's listing-index `size` of 70 gives the same extent as the "
                ".asm's own last instruction, so the verdict does not rest on "
                "choosing between the two readings of the extent")

    # The `no-witness` bucket's worked case, so `walked_from` is anchored to a
    # real listing rather than only to the fixture. `bank0/8054.c` names
    # 0x08D1 and `bank0/8054.asm` seeds 0x08D0 -- the `inc DPTR` walk form
    # `xdata_register_map.xdata_space()` measures and this tool records rather
    # than counts. `ec/annotations/xdata-register-map.md` §7.1 already records
    # 0xFFC1, 0xFFD1 and 0xFFDB as reachable only this way.
    walk_row = by.get(("bank0", "8054", "0x08D1"))
    seeds = set() if walk_row is None else {
        int(t, 16) for t in walk_row["listing_seeds"].split()}
    assert_that(walk_row is not None
                and walk_row["verdict"] == "no-witness"
                and walk_row["walked_from"] == "0x08D0"
                and 0x08D1 not in seeds and 0x08D0 in seeds,
                "bank0/8054.c's 0x08D1 is `no-witness` with `walked_from` "
                "0x08D0: the listing seeds the byte below and no `mov DPTR` "
                "names 0x08D1, which is the walk `xdata_register_map."
                "xdata_space()` measures and this census records but does not "
                "count as a counterpart")

    # The 7B14 case this tool does NOT catch, asserted as a non-row rather than
    # left implicit -- `docs/findings/7b14-07c9-token.md` is built on it.
    assert_that(("pd", "7B14", "0x07C9") not in by,
                "pd/7B14.c's 0x07C9 is NOT in this census, and that is the "
                "limit rather than an omission: pd/7B14.asm seeds DPTR with "
                "0x07C9 at a dozen sites, so at (function, address) granularity "
                "the listing does witness it")
    at = inspect_listing("pd", "7B14")
    assert_that(0x7CC1 in at and 0x7CC2 in at and 0x7CC4 in at
                and at[0x7CC1] == ("clr", "A")
                and at[0x7CC2] == ("add", "A, #0x1c")
                and at[0x7CC4] == ("lcall", "0x9028")
                and 0x07C9 in immediates_of(
                    os.path.join(DECOMPILED, "pd", "7B14.asm")),
                "while pd/7B14.asm still reads `clr A` at 0x7CC1, "
                "`add A, #0x1c` at 0x7CC2 and `lcall 0x9028` at 0x7CC4: the "
                "column byte the committed C renders as "
                "`make_dptr_r6_minus_3_9028(DAT_EXTMEM_07c9)` is built by those "
                "three. `.asm` right means the C is the worse reading there, "
                "and settling it needs statement-level alignment this census "
                "does not attempt")
    with open(os.path.join(DECOMPILED, "pd", "7B14.c"),
              errors="replace") as handle:
        body = handle.read()
    assert_that("make_dptr_r6_minus_3_9028(DAT_EXTMEM_07c9);" in
                X.body_of(X.strip_comments(body))
                and "DAT_EXTMEM_001c" not in body,
                "and the committed C passes the symbol itself to that call and "
                "names no 0x001C -- the census's token pattern finds no "
                "`DAT_EXTMEM_001c` in this file, which is the other half of the "
                "same disagreement and is a statement about this one file, not "
                "about the byte")


    # ---- the report's own table ------------------------------------------
    text = render(rows)
    assert_that(render(list(csv.DictReader(text.splitlines()))) == text,
                "the rendered table is a csv.DictReader fixed point")
    assert_that(check_table(text, text) == (0, []),
                "and compares equal against itself, which is --check's "
                "passing case")
    # The first row's own verdict, replaced by a different one, so the case
    # does not depend on any particular verdict having rows on this tree.
    first = rows[0]
    other = next(v for v in VERDICTS if v != first["verdict"])
    drifted = text.replace(",%s," % first["verdict"], ",%s," % other, 1)
    rc, lines = check_table(drifted, text)
    assert_that(rc == 1 and lines
                and any("recomputed %r" % first["verdict"] in ln for ln in lines)
                and any("committed %r" % other in ln for ln in lines),
                "and a table with one row's verdict altered is rejected, "
                "naming that row and that column")
    dropped = "\n".join(text.splitlines()[:-1]) + "\n"
    rc, lines = check_table(dropped, text)
    assert_that(rc == 1
                and lines == ["  row count: committed %d, recomputed %d"
                              % (len(rows) - 1, len(rows))],
                "and a table with its last row dropped is rejected on the row "
                "count, which no cell-by-cell comparison can see")

    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--report", action="store_true",
                      help="write ec/ghidra/c-asm-counterpart.csv")
    mode.add_argument("--check", action="store_true",
                      help="recompute the table and fail on any diff")
    mode.add_argument("--self-test", action="store_true",
                      help="known answers from committed inputs and the bytes")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if args.check:
        return check()

    index, listings = context()
    rows = rows_for(index, listings)
    report(rows)
    if args.report:
        with open(REPORT, "w", newline="") as f:
            f.write(render(rows))
        print()
        print("wrote %s (%d rows)" % (os.path.relpath(REPORT, REPO), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
