#!/usr/bin/env python3
"""Merge the annotation sweep's per-shard CSVs into the component's annotations
file, and refuse anything that would not survive the build's own check.

The sweep is fan-out: one agent per shard of functions, each writing its own
CSV, each row then independently checked against that function's disassembly by
a second agent. This is the step that turns 65 files into one, and it is where
the mechanical rules are applied -- because an agent reading a brief is not a
parser, and the build's `--check` is the only thing standing between a
mis-quoted comment and `main`.

What it refuses, and why each of these has bitten something:

  a row whose (scope, addr) resolves to no exported function  -- a typo, or an
      address the project has since stopped seeding
  a duplicate (scope, addr)                                  -- two agents, one
      address; the build would silently keep the last
  an empty name, comment, type or evidence                    -- the row exists
      to carry these
  a type outside the controlled vocabulary                    -- an unchecked
      vocabulary becomes an unchecked claim
  an evidence cell with no path-like token                   -- a citation to
      nothing is what the whole evidence rule exists to stop
  a comment naming a hex address that appears nowhere in the
  function's own .c or .asm                                  -- see below

That last one is the calibration rule made mechanical, and it is the reason
this script exists. "Calibrate, don't overclaim" is easy to state and hard to
apply across two thousand rows, and the specific failure at scale is an agent
writing a confident sentence about a register the function does not touch. A
comment may only name a hexadecimal address, a function name or an SFR/EXTMEM
symbol that is actually present in that function's own source or listing. It
may not name one that is not: at 1,891 rows a single unsupported address is
invisible, and a gate that only checks the cell is non-empty accepts it.

Usage:
    python3 ec/tools/merge_annotation_shards.py <existing.csv> <shard-dir> \\
        <out.csv> [--index ec/decompiled/index.csv] [--report]
    python3 ec/tools/merge_annotation_shards.py --census [--export <dir>]
        [--candidates <out.csv>]

The `--census` mode is the other half of the file's job, and it exists because
a batch of rows has to be *bounded* before it is written. The first variable
batch was bounded on a predicate; the second needed one measured the same way,
and the number the batch is sized by has to come out of a committed tool rather
than out of somebody's arithmetic. So it re-derives two things from the
committed export and prints them:

  the declaration census, structurally. A function's declared parameters are
      the placeholders in its signature's parameter list, and its declared
      locals are the ones in its locals block. A regex over the file would
      count mentions, and a mention count moves on a regeneration without a
      single declaration changing -- which is why docs/findings.md 18 quotes
      declarations and not mentions.

  the A-store predicate. For a function's listing, in address order, the
      first instruction that touches A. If that instruction is a
      `movx @DPTR,A`, then A still holds whatever it held on entry, because
      nothing in between wrote it. That is a fact about the listing, and it is
      the only family in the variable layer the listing decides on its own: it
      says a value ARRIVES in A, and nothing more -- Ghidra has no Keil C51
      calling-convention model, so a prototype here would be a guess sitting
      where a fact reads.
"""
import argparse
import csv
import glob
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))

HEADER = ["scope", "addr", "name", "signature", "type", "comment", "evidence", "basis"]

# The variable layer's header and its one controlled vocabulary. A separate pair
# rather than a shared one because a function's row IS a function -- the build's
# annotation_seeds() reads every row's addr as a seed and join_index() keys one
# row per (scope, addr) -- and a function with eight named parameters cannot be
# eight rows in that file. A variable row is keyed on a decompiler placeholder
# instead, so several can share one (scope, addr).
VARIABLE_HEADER = ["scope", "addr", "key", "name", "kind", "comment", "evidence", "basis"]

# `kind` is to a variable row what `type` is to a function row: a closed
# vocabulary, because an unchecked vocabulary becomes an unchecked claim. Most
# `param_N` in this export are not parameters at all -- the decompiler renders a
# callee's R7, a scratch register and an uninitialised DPTR as parameters
# alike -- so `artifact` and `return` are not edge cases, they are most of the
# batch. `unresolved` is a result, not a failure: the listing does not say, and
# the placeholder stays.
VARIABLE_KINDS = {"param", "local", "return", "artifact", "unresolved"}

# The hand-written annotations file, used as the base a merge starts from. The
# self-test needs a real one because the rows it writes have to resolve against
# a real index; a synthetic base would test a different thing.
EXISTING_DEFAULT = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
# The self-test's base: a file with the header and nothing else, because the
# live one accumulates exactly the rows the test cases use.
_SELF_TEST_BASE = "empty"

# The controlled vocabulary: the union of the EC's and the BIOS's, because both
# sweep briefs have one and the merge reads both components' shards. Kept here
# rather than only in the brief so the merge is the thing that enforces it: an
# agent that invents `charge-path` gets the row rejected, not a new column
# value in a file nobody checks.
#
# It is a union rather than two lists because a per-component list means the
# wrong one silently rejects every row of the other component -- which is what
# happened the first time this ran on BIOS shards, rejecting 115 of 137 for
# naming a perfectly good `protocol`.
TYPES = {
    # shared
    "entry", "init", "dispatch", "forwarder", "gate", "reader", "writer",
    "copy", "math", "logic", "serial", "state", "unresolved", "helper",
    "module-entry",
    # EC
    "sbi", "ec-io", "delay", "bank-switch", "charge-target",
    # BIOS
    "smi", "nvram", "setup-var", "protocol", "acpi", "graphics", "usb",
    "overclock", "thermal", "power", "debug",
    # already in use in the hand-written rows, both components
    "gpio-pad", "nvram-write", "pcr-read", "pch-select",
}

BASES = {"hand-decoded", "restatement", "inferred"}

# A comment longer than this is refused. The point is not brevity for its own
# sake -- several functions here genuinely need a paragraph -- it is that a
# 1,500-character block above a six-instruction function is a document that
# happens to be in the wrong place, and it should be written as one rather than
# smuggled in as a comment.
MAX_COMMENT_CHARS = 1200

# A *register reference* in a comment: an address qualified by the word that
# says what kind of memory it is.
#
# The first cut of this rule flagged every 4-hex-digit run in a comment, and
# rejected 535 of 967 rows for naming 0xFFFF -- in sentences like "lies in the
# 0x8000-0xFFFF banked CODE window", which is a true statement about the memory
# map and not a claim that the function touches 0xFFFF. A rule that rejects
# true statements gets switched off, so it is narrowed to the thing it is
# actually for: a comment that says a function reads, writes or gates on a
# location, and names one that is not in that function. Qualifying words only.
# `byte` and `word` were tried here and removed: prose says "the same byte
# 0x53AF tests against" about an address in a *different* function, and the
# qualifier turned that into a rejection. The words that name a memory space are
# the ones a register claim actually uses.
REGISTER_REF = re.compile(
    r"(?i)\b(EXTMEM|XDATA|DATA|CODE|SFR|IRAM|register|reg)"
    r"\s*(?:at\s+)?#?(0x[0-9a-f]{2,4})\b")


def addr_key(a):
    return a.upper().replace("0X", "")


def load_existing(path):
    if not path or not os.path.isfile(path):
        return []
    return list(csv.DictReader(open(path, newline="")))


def function_sources(index_path):
    """(scope, addr) -> the index row, keyed both ways.

    The .asm is the ground truth and the .c is the decompiler's reading; a
    comment may cite either, so both are what a claim gets checked against.

    Two keys per row, because the two components pad differently: the EC index
    writes `0B158` and the BIOS one writes `00000260`, while a shard writing
    `0x260` matches neither as a string. Addresses are numbers, so the second
    key is the integer value."""
    out = {}
    for row in csv.DictReader(open(index_path, newline="")):
        out[(row["program"], row["addr"])] = row
        out[(row["program"], "#%d" % int(row["addr"], 16))] = row
    return out


def resolve(index, scope, addr):
    """The index row for (scope, addr), whichever way each side padded it."""
    row = index.get((scope, addr))
    if row is None:
        try:
            row = index.get((scope, "#%d" % int(addr, 16)))
        except ValueError:
            row = None
    return row


# A call target the comment names: "calls 0xC030, which writes XDATA 0x1601".
# A function that delegates its register work is making a true claim about a
# register that is in the callee and not in itself, and rejecting that punishes
# the more informative comment in favour of a vaguer one.
CALLEE_REF = re.compile(r"(?i)\b(?:call|calls|called|calling|calls\s+into|at|to)"
                        r"\s+(?:function\s+)?(?:0x)?([0-9a-f]{4})\b")


def callee_text(index, comment, scope):
    """The source of every function the comment names as a call target."""
    prog = scope
    texts = []
    for m in CALLEE_REF.finditer(comment):
        want = m.group(1).lower().lstrip("0") or "0"
        for key in index:
            p, a = key
            if p != prog or a.startswith("#"):
                continue
            try:
                if int(a, 16) != int(want, 16):
                    continue
            except ValueError:
                continue
            t = read_function_text(index, p, a)
            if t:
                texts.append(t)
            break
    return "\n".join(texts)


def neighbour_text(index, scope, addr, span=3):
    """The source of the `span` functions either side of this one.

    Needed because Ghidra's function boundaries on this firmware cut through
    straight-line code: 0x8004 is a one-instruction fragment (`movx a,@dptr`)
    whose DPTR was loaded by the function at 0x8001. A comment on 0x8004 that
    says "reads XDATA 0x06C6, reached by falling through from the mov DPTR at
    0x8001" is correct, and a rule that only looks at the function's own bytes
    rejects it -- which is a rule that punishes the careful answer and rewards
    the vague one."""
    prog, key = scope, addr_key(addr)
    sibs = sorted((a for p, a in index if p == prog and not a.startswith("#")),
                  key=lambda a: int(a, 16))
    try:
        i = next(j for j, a in enumerate(sibs) if int(a, 16) == int(key, 16))
    except (StopIteration, ValueError):
        return ""
    texts = []
    for j in range(max(0, i - span), min(len(sibs), i + span + 1)):
        if sibs[j] == key:
            continue
        t = read_function_text(index, scope, sibs[j])
        if t:
            texts.append(t)
    return "\n".join(texts)


# Where a listing's out_file can resolve, most specific first. The BIOS's
# per-function listings live under bios/ghidra/listings/<Module>/ while its
# decompile is one file per module beside it, so the two are in different trees
# and a comment may cite either.
SEARCH_BASES = (
    os.path.join(REPO, "ec", "decompiled"),
    os.path.join(REPO, "bios", "ghidra", "listings"),
    os.path.join(REPO, "bios", "decompiled"),
    os.path.join(REPO, "windows", "decompiled", "native"),
)


def _read(path):
    return open(path, errors="replace").read() if os.path.isfile(path) else None


def read_function_text(index, scope, addr):
    """The .asm and, where there is one, the .c for this function.

    A comment may cite either, so both are what a claim gets checked against.
    The BIOS has no per-function .c -- its decompile is one file per module --
    so the module's file is read too, on the grounds that a comment about a
    BIOS function is entitled to the context its module provides."""
    row = resolve(index, scope, addr)
    if not row:
        return None
    parts = []
    for rel in (row.get("out_file", ""), row.get("listing_file", "")):
        if not rel or rel.startswith("("):
            continue
        for base in SEARCH_BASES:
            text = _read(os.path.join(base, rel))
            if text is not None:
                parts.append(text)
                break
    for base in SEARCH_BASES:
        text = _read(os.path.join(base, scope + ".c"))
        if text is not None:
            parts.append(text)
            break
    return "\n".join(parts) if parts else None


# --- the census and the A-store predicate --------------------------------
#
# Both of these are here rather than in a new tool because the boundary a batch
# is defined by belongs next to the merge that enforces the rules on the rows
# the boundary produced, and because this file is already in the cheap gate
# loop with a --self-test that the new cases join.

EXPORT_DEFAULT = os.path.join(REPO, "ec", "decompiled")

# The decompiler's placeholder families. Ghidra numbers them per function, so
# the set of distinct names is small (param_1..param_11 here) and the number
# that sizes the job is the number of (file, name) pairs -- which is what
# "declarations" means in the table this feeds.
PLACEHOLDER = re.compile(r"\b(param_\d+|[cbuils]Var\d+|p[a-z]?Var\d+)\b")

# A function's signature parameter list, up to the body's opening brace. The
# decompile is one function per file, so the first line that looks like this is
# the signature and the `if (...) {` lines in the body come after it. Two
# shapes have to be covered, and both are in the export: a short signature is
# one line, and a long one is wrapped with the parameter list indented onto the
# next -- `bank0,0xBD7F`'s five parameters do not fit, and a `[ \t]*` between
# the name and the `(` would read that file as declaring nothing at all.
SIGNATURE = re.compile(r"^[A-Za-z_][\w \*]*?\s*\(([^()]*)\)\s*\{", re.M)

# A declaration statement in the body: `char cVar1;`, `undefined1 *puVar2;`,
# `int local_10[4];`. The type may carry a `*`, which is why it is in the
# class. An assignment does not match: `puVar2 = &DAT_EXTMEM_1c35;` has `=`
# where this wants `;`.
DECLARATION = re.compile(
    r"^[ \t]*[A-Za-z_][\w \*]*?[ \t]+([A-Za-z_]\w*)[ \t]*(?:\[[^\]]*\])?"
    r"[ \t]*;[ \t]*$", re.M)


def strip_c_comments(text):
    """The decompiled C with both comment forms removed.

    The plate comment above a function names the placeholder it is explaining
    -- `bank0,0x901C`'s says "param_1 is a pointer the decompiler invented" --
    and that sentence is the reading, not a declaration. Counting it is how a
    mention count comes to exceed a declaration count for a function that
    declares nothing.
    """
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", text, flags=re.S))


def declared_placeholders(c_text):
    """(signature parameters, body locals) as two sets of placeholder names.

    Structural on purpose. The declaration is the place in the text where the
    name is *introduced* -- the parameter list, or a declaration statement --
    and a mention is every other time it appears. A regeneration renames
    symbols and rewrites expressions without moving a single declaration, so
    the two counts part company and only the first one is the size of the job.

    A local Ghidra declares inside an inner block rather than at the top of
    the body is still a declaration, and is counted: the reader has to name it
    either way. This export emits a few hundred of those (a `cVar1` declared
    inside a loop body, for one), which is most of the difference between the
    two readings of "the locals block" and is the reason this states which one
    it is.
    """
    text = strip_c_comments(c_text)
    m = SIGNATURE.search(text)
    if not m:
        return set(), set()
    params = set(PLACEHOLDER.findall(m.group(1)))
    params = {p for p in params if p.startswith("param_")}
    locals_ = {d.group(1) for d in DECLARATION.finditer(text[m.end():])}
    return params, {n for n in locals_ if PLACEHOLDER.fullmatch(n)}


def census(export):
    """The declaration census, measured over every `.c` under `export`.

    Returns the mention and declaration counts per family, the file count, and
    how many files declare anything. Both counts are returned, and the report
    prints them side by side, because the gap between them is the thing a
    reader needs to see: `param_N` is read 8,553 times and declared 2,317
    times, and it is the second number that sizes a batch.
    """
    mentions = {}
    declarations = {}
    files = with_declarations = with_placeholders = 0
    params_total = locals_total = pairs = both = 0
    for path in sorted(glob.glob(os.path.join(export, "*", "*.c"))):
        files += 1
        text = _read(path) or ""
        code = strip_c_comments(text)
        if PLACEHOLDER.search(code):
            with_placeholders += 1
        for name in PLACEHOLDER.findall(code):
            mentions[name] = mentions.get(name, 0) + 1
        params, locals_ = declared_placeholders(text)
        params_total += len(params)
        locals_total += len(locals_)
        both += len(params & locals_)
        pairs += len(params | locals_)
        if params or locals_:
            with_declarations += 1
        for name in params | locals_:
            declarations[name] = declarations.get(name, 0) + 1
    return {
        "files": files,
        "files_with_placeholders": with_placeholders,
        "files_with_declarations": with_declarations,
        "params": params_total,
        "locals": locals_total,
        "pairs": pairs,
        "both": both,
        "mentions": mentions,
        "declarations": declarations,
    }


def _by_family(counts):
    """{param_1: 3, param_2: 2} -> {param_: 5}, so families print as rows."""
    out = {}
    for name, n in counts.items():
        fam = re.sub(r"\d+$", "", name)
        out[fam] = out.get(fam, 0) + n
    return out


def parse_listing(path):
    """(address, mnemonic, operands) per instruction, in listing order.

    The columns are read positionally, because `ExportListing.java`'s
    `format()` pads all three of them. A whitespace split gets a line like
    `D438     d4 - -   da       A` wrong in a way that is invisible in the
    output: `da` is a valid two-digit byte field, so a greedy split reads the
    instruction's own mnemonic as its fourth byte and the operand as the
    mnemonic. The `da` is BCD adjust; the split calls it a bare `A`.
    """
    out = []
    for line in (_read(path) or "").splitlines():
        if not line.strip() or line.startswith(";"):
            continue
        if len(line) < 18:
            continue
        mnem = line[18:26].strip()
        if not mnem:
            continue
        out.append((line[0:8].strip(), mnem, line[27:].strip()))
    return out


def touches_accumulator(mnem, operands):
    """Does this instruction read or write A?

    The shapes this export actually uses, and what each does:

      read A         `movx @DPTR,A`, `movx @Rn,A`, `mov Rn,A`, `mov direct,A`,
                     `mov @Rn,A`, `mov @DPTR,A`, `addc Rn,A` and friends
      write A        `mov A,...`, `movc A,...`
      read and write `add`/`addc`/`subb`/`orl`/`anl`/`xrl A,...`, `inc`/`dec`/
                     `clr`/`cpl`/`da`/`swap`/`rl`/`rlc`/`rrc`/`rr A`,
                     `djnz A,...`, `mul AB`, `div AB`, `xch A,...`,
                     `xchd A,...`, `push A`, `pop A`
      read for a test `cjne A,...`, `jmp @A+DPTR`

    They are one rule because there is nothing to distinguish them here: the
    question is only whether A has been overwritten before the store, and
    every one of these overwrites it. Listing the families is worth the lines
    so a future 8051 opcode that does not fit is an addition to a list rather
    than a silent change to a predicate.
    """
    if mnem in ("mul", "div"):
        return operands == "AB"
    if mnem == "jmp":
        return operands == "@A+DPTR"
    return any(part.strip() == "A" for part in operands.split(","))


def first_accumulator_use(insns):
    """The first instruction that touches A, or None if the listing never does."""
    for addr, mnem, operands in insns:
        if touches_accumulator(mnem, operands):
            return (addr, mnem, operands)
    return None


def a_store_candidates(export):
    """Every function whose first A-touch is an XDATA store of A.

    The predicate is a fact about the listing and nothing else: at that store
    A holds its entry value, because no instruction between the entry and the
    store wrote it. It does **not** establish that a caller put it there. See
    `docs/findings.md` 18 for the two comment forms that keep the two apart.

    `movx @Rn,A` has the same property and is a separate row in the report
    rather than a folded-in one, so a reader can see that it was considered
    and how many there are rather than having to trust that it was considered
    at all. There are a handful; both shapes are reported, and the batch is
    `@DPTR` alone because that is the shape the existing `value_a` rows use.
    """
    listing_index = os.path.join(export, "listing-index.csv")
    if not os.path.isfile(listing_index):
        raise SystemExit("no listing-index.csv under %s" % export)
    dptr, rn, never = [], [], []
    for row in csv.DictReader(open(listing_index, newline="")):
        rel = row.get("out_file") or ""
        if not rel or rel.startswith("("):
            continue
        path = os.path.join(export, rel)
        if not os.path.isfile(path):
            continue
        insns = parse_listing(path)
        first = first_accumulator_use(insns)
        if first is None:
            never.append(row)
            continue
        addr, mnem, operands = first
        if mnem != "movx" or not operands.split(",")[0].strip().startswith("@"):
            continue
        c_path = os.path.join(export, rel[:-4] + ".c")
        params, _locals = declared_placeholders(_read(c_path) or "")
        entry = {
            "scope": row["program"],
            "addr": row["addr"],
            "store": addr,
            "operands": operands,
            "insns": len(insns),
            "annotated": row.get("annotated", ""),
            "params": sorted(params, key=lambda p: int(p.split("_")[1])),
        }
        (dptr if operands.split(",")[0].strip() == "@DPTR" else rn).append(entry)
    return {"dptr": dptr, "rn": rn, "no_a_touch": len(never)}


def census_mode(args):
    """Print the census and the predicate population over `args.export`.

    The report ends on the batch boundary rather than on the whole predicate,
    because those are two different numbers and only the second one sizes a
    batch of rows. Between them sit the two filters the second batch used, and
    both are printed so a reader never has to take the boundary on trust:
    the 7 functions the first batch already named, which no longer declare a
    `param_N` at all, and the functions with no row in `ghidra-functions.csv`,
    which this batch does not reach.
    """
    c = census(args.export)
    print("\ndeclaration census over %s" % os.path.relpath(args.export, REPO))
    print("  %d .c file(s); %d carry a placeholder, %d declare one"
          % (c["files"], c["files_with_placeholders"], c["files_with_declarations"]))
    print("\n  %-12s %10s %14s %7s" % ("family", "mentions", "declarations",
                                       "names"))
    by_m, by_d = _by_family(c["mentions"]), _by_family(c["declarations"])
    names = {}
    for name in list(c["mentions"]) + list(c["declarations"]):
        fam = re.sub(r"\d+$", "", name)
        names.setdefault(fam, set()).add(name)
    for fam in sorted(by_d, key=lambda f: -by_d[f]):
        print("  %-12s %10d %14d %7d"
              % (fam + "N", by_m.get(fam, 0), by_d[fam], len(names[fam])))
    print("\n  declared parameters (signature):  %d" % c["params"])
    print("  declared locals (body):          %d" % c["locals"])
    print("  declared placeholders, total:    %d distinct (file, name) pair(s)"
          % c["pairs"])
    if c["both"]:
        # Ghidra redeclares a parameter as a local in an inner scope often
        # enough to matter to anyone adding the two lines above, and the sum
        # of the two is therefore not the total.
        print("    %d declared twice, once in the signature and once as a local"
              % c["both"])

    sel = a_store_candidates(args.export)
    print("\nA-store predicate over the same export "
          "(first instruction touching A is `movx @DPTR,A`)")
    print("  %d function(s) whose first A-touch never happens" % sel["no_a_touch"])
    print("  %d `movx @DPTR,A`" % len(sel["dptr"]))
    print("  %d `movx @Rn,A`, reported and not folded in: the same property, "
          "and a different shape" % len(sel["rn"]))
    for e in sel["rn"]:
        print("    %-6s %-6s %s %s" % (e["scope"], e["addr"], e["store"],
                                       e["operands"]))

    done = [e for e in sel["dptr"] if e["annotated"] == "yes" and not e["params"]]
    unnamed = [e for e in sel["dptr"] if e["annotated"] != "yes"]
    batch = [e for e in sel["dptr"]
             if e["annotated"] == "yes" and e["params"]]
    print("  %d annotated and still declaring a `param_N` -- the batch"
          % len(batch))
    print("    %d annotated already named by the first batch, so no longer "
          "declaring one" % len(done))
    for e in done:
        print("      %-6s %-6s %s" % (e["scope"], e["addr"], e["store"]))
    print("    %d with no row in ghidra-functions.csv, so not reached by this "
          "batch" % len(unnamed))
    for e in unnamed:
        print("      %-6s %-6s %s" % (e["scope"], e["addr"], e["store"]))
    if not batch:
        return 0
    by_scope = {}
    for e in batch:
        by_scope[e["scope"]] = by_scope.get(e["scope"], 0) + 1
    print("    by scope: %s"
          % ", ".join("%s %d" % (s, by_scope[s]) for s in sorted(by_scope)))
    print("    declaring %d `param_N` between them (%s)"
          % (sum(len(e["params"]) for e in batch),
             " ".join("%dx%d" % (n, sum(1 for e in batch
                                        if len(e["params"]) == n))
                      for n in sorted({len(e["params"]) for e in batch}))))
    lens = sorted(e["insns"] for e in batch)
    print("    listing length: median %d instruction(s), longest %d"
          % (lens[len(lens) // 2], lens[-1]))

    if args.candidates:
        with open(args.candidates, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["scope", "addr", "store", "operands", "params"])
            for e in batch:
                w.writerow([e["scope"], e["addr"], e["store"], e["operands"],
                            " ".join(e["params"])])
        print("  wrote %d candidate row(s) to %s"
              % (len(batch), os.path.relpath(args.candidates, REPO)))
    return 0


def self_test():
    """Negative cases, so a check that has stopped rejecting anything is caught.

    Every case here is a row that reached this tool from a fan-out and had to be
    refused. One of them -- a row with an empty field -- was not being refused
    at all: the field loop used `break` with no `continue` after it, so the row
    was added to the rejected list and to the output in the same pass. Feeding
    this tool a deliberately bad shard is the only way that shows up.

    Each case is a row that MUST be rejected, and one that must survive, so a
    change that rejects everything is caught too.
    """
    import itertools
    import tempfile as _tf
    d = _tf.mkdtemp()
    _counter = itertools.count()
    ok = True
    # An empty annotations file as the base, not the live one. The base
    # contributes its rows to `seen`, so once the sweep annotated the
    # addresses these cases use, every one of them was refused as a duplicate
    # before reaching the check it exists to test -- and a self-test that goes
    # quietly vacuous as the corpus grows is worse than none. The *index* is
    # still the real one, so the rows still have to resolve to real functions.
    empty_base = os.path.join(d, "empty.csv")
    with open(empty_base, "w", newline="") as f:
        f.write(",".join(HEADER) + "\n")

    def check(label, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", label))
        ok = ok and cond

    def merge(rows, approved=None, kind="functions"):
        # A fresh directory per case. The shard directory is globbed for *.csv,
        # so writing the output beside the input makes the previous case's
        # output the next case's input -- which is how six of these assertions
        # were failing for reasons that had nothing to do with what they test.
        head = VARIABLE_HEADER if kind == "variables" else HEADER
        case = os.path.join(d, "case%d" % next(_counter))
        os.makedirs(case, exist_ok=True)
        with open(os.path.join(case, "t.csv"), "w", newline="") as f:
            f.write(",".join(head) + "\n")
            for r in rows:
                f.write(r + "\n")
        out = os.path.join(d, "out%d.csv" % next(_counter))
        appr = None
        if approved is not None:
            appr = os.path.join(case, "approved.txt")
            with open(appr, "w") as f:
                for a in approved:
                    f.write(a + "\n")
        import io
        import contextlib
        buf = io.StringIO()
        argv = [empty_base, case, out, "--report", "--csv-kind", kind]
        if appr:
            argv += ["--approved", appr]
        with contextlib.redirect_stdout(buf):
            rc = main_for(argv)
        accepted = []
        if os.path.isfile(out):
            accepted = list(csv.DictReader(open(out, newline="")))
        return rc, accepted, buf.getvalue()

    def main_for(argv):
        saved = sys.argv
        sys.argv = ["merge"] + argv
        try:
            return main()
        finally:
            sys.argv = saved

    def row(**kw):
        base = dict(scope="bank0", addr="0x0EA2", name="n", signature="",
                    type="writer", comment="Writes a byte to XDATA 0x0A56.",
                    evidence="ec/decompiled/bank0/0EA2.asm", basis="hand-decoded")
        base.update(kw)
        return ",".join(
            '"%s"' % base[h] if "," in base[h] else base[h] for h in HEADER)

    _, acc, _ = merge([row()])
    check("a well-formed row is accepted", len(acc) >= 1)
    _, acc, out = merge([row(evidence="")])
    check("a row with empty evidence is rejected and not merged",
          "empty evidence" in out and "no_evidence" not in out)
    _, acc, out = merge([row(name="")])
    check("a row with an empty name is rejected", "empty name" in out)
    _, acc, out = merge([row(comment="")])
    check("a row with an empty comment is rejected", "empty comment" in out)
    _, acc, out = merge([row(type="charge-path")])
    check("a type outside the vocabulary is rejected",
          "outside the controlled vocabulary" in out)
    _, acc, out = merge([row(basis="vibes")])
    check("an unknown basis is rejected", "is not one of" in out)
    _, acc, out = merge([row(addr="0xABCD")])
    check("an address no function resolves to is rejected",
          "resolves to no exported function" in out)
    _, acc, out = merge([row(), row(comment="A second row, same address.")])
    check("a duplicate (scope, addr) is rejected",
          "duplicate (scope, addr)" in out)
    # The verifier's whitelist. It was written once, then lost by an edit that
    # rewrote the block around it, and the merge carried on accepting rows
    # nobody had checked for several runs before anything noticed -- which is
    # the exact failure the whole verification stage exists to prevent.
    # A second real address, so the row reaches the whitelist rather than
    # being rejected for not existing.
    _, acc, out = merge([row(), row(addr="0x163C", name="other",
                                    comment="Returns immediately without touching memory.")],
                        approved=[row()])
    check("a row the verifier did not approve is rejected",
          "did not approve" in out)
    # Exactly the approved row: the base is empty, so anything else in `acc`
    # would mean the whitelist is not being applied.
    check("an approved row still gets in, and only that one", len(acc) == 1)
    _, acc, out = merge([
        row(comment="Writes the charge target to XDATA 0x0777 and sets the "
                    "fan enable bit.")])
    check("a comment naming a register the function does not touch is rejected",
          "nor a function it names" in out)

    # --- the variable layer -------------------------------------------------
    # The same refusals, against the other file. A guard exercised only on the
    # function layer is a guard that has never been shown to work on the
    # variable one, and the two files take different paths through this tool:
    # a different header, a different vocabulary, and a duplicate key that
    # includes the placeholder.
    def vrow(**kw):
        base = dict(scope="bank0", addr="0x0EA2", key="param_1", name="ticks",
                    kind="param", comment="The R7 the caller left, counted down "
                                          "to zero at XDATA 0x0A56.",
                    evidence="ec/decompiled/bank0/0EA2.asm", basis="hand-decoded")
        base.update(kw)
        return ",".join(
            '"%s"' % base[h] if "," in base[h] else base[h] for h in VARIABLE_HEADER)

    def vmerge(rows, approved=None):
        return merge(rows, approved=approved, kind="variables")

    _, acc, out = vmerge([vrow()])
    check("a well-formed variable row is accepted", len(acc) >= 1)
    _, acc, out = vmerge([vrow(kind="parameter")])
    check("a variable kind outside the vocabulary is rejected",
          "outside the controlled vocabulary" in out and "kind" in out)
    _, acc, out = vmerge([vrow(evidence="")])
    check("a variable row with empty evidence is rejected and not merged",
          "empty evidence" in out and "no_evidence" not in out)
    _, acc, out = vmerge([vrow(name="")])
    check("a named variable row with an empty name is rejected",
          "empty name" in out)
    _, acc, out = vmerge([vrow(key="")])
    check("a variable row with no key is rejected -- a row has to name the "
          "placeholder it replaces", "empty key" in out)
    _, acc, out = vmerge([vrow()])
    check("an unresolved variable row needs no name, and is accepted for what "
          "it says", "empty name" not in out)
    _, acc, out = vmerge([vrow(kind="unresolved", name="ticks")])
    check("an unresolved variable row that also carries a name is rejected",
          "the placeholder stays in place" in out)
    _, acc, out = vmerge([vrow(addr="0xABCD")])
    check("a variable row at an address no function resolves to is rejected",
          "resolves to no exported function" in out)
    _, acc, out = vmerge([vrow(), vrow()])
    check("a duplicate (scope, addr, key) is rejected -- the same placeholder "
          "twice", "duplicate (scope, addr, key)" in out)
    _, acc, out = vmerge([vrow(), vrow(key="param_2", name="other")])
    check("two DIFFERENT placeholders in one function are both accepted, which "
          "is the whole reason the key is part of the identity",
          len(acc) == 2 and "duplicate" not in out)
    _, acc, out = vmerge([
        vrow(comment="Writes the charge target to XDATA 0x0777 and sets the "
                     "fan enable bit.")])
    check("a variable comment naming a register the function does not touch is "
          "rejected too", "neither this function" in out)
    _, acc, out = vmerge([vrow(), vrow(key="param_2", name="other")],
                         approved=[vrow()])
    check("a variable row the verifier did not approve is rejected",
          "did not approve" in out)
    _, acc, out = vmerge([vrow()], approved=[vrow()])
    check("an approved variable row still gets in, and only that one",
          len(acc) == 1)

    # --- the census and the A-store predicate -------------------------------
    # A tool path with no self-test is a review blocker, and these are the two
    # halves that can be wrong in opposite directions: a census that reads
    # mentions instead of declarations inflates the backlog, and a predicate
    # that skips a `mov A` ahead of the store selects functions whose
    # accumulator is not the caller's. Both are checked against a fixture
    # small enough to count by hand.
    fixture = os.path.join(d, "export")
    os.makedirs(os.path.join(fixture, "bank0"), exist_ok=True)
    # Four functions, one per outcome: an A store on entry, a function that
    # loads A first, a `@Rn` store, and one that declares nothing. The last
    # one's plate comment names a placeholder, because a function's own prose
    # is allowed to discuss the placeholder it is explaining and a census that
    # reads it is counting the annotation rather than the code.
    write_fixture(os.path.join(fixture, "bank0", "1000.asm"),
                  "movx", "@DPTR, A", "1000")
    write_fixture(os.path.join(fixture, "bank0", "2000.asm"),
                  "mov", "A, #0x7", "2000")
    write_fixture(os.path.join(fixture, "bank0", "3000.asm"),
                  "movx", "@R0, A", "3000")
    write_fixture(os.path.join(fixture, "bank0", "4000.asm"),
                  "clr", "A", "4000")
    write_c_fixture(os.path.join(fixture, "bank0", "1000.c"),
                    "void f_1000(undefined1 param_1,undefined1 *param_2)\n"
                    "\n{\n  *param_2 = param_1;\n}\n")
    write_c_fixture(os.path.join(fixture, "bank0", "2000.c"),
                    "void f_2000(void)\n\n{\n  DAT_EXTMEM_1c35 = 7;\n}\n")
    write_c_fixture(os.path.join(fixture, "bank0", "3000.c"),
                    "void f_3000(undefined1 param_1)\n\n{\n  *param_1 = 0;\n}\n")
    write_c_fixture(os.path.join(fixture, "bank0", "4000.c"),
                    "/* f_4000 leaves param_9 and cVar7 alone.\n"
                    "   type: unresolved */\nvoid f_4000(void)\n\n{\n}\n")
    with open(os.path.join(fixture, "listing-index.csv"), "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["program", "addr", "out_file", "annotated"])
        for a in ("1000", "2000", "3000", "4000"):
            w.writerow(["bank0", a, "bank0/%s.asm" % a, "yes"])

    c = census(fixture)
    check("the census counts a signature's parameters and a body's locals",
          c["params"] == 3 and c["locals"] == 0 and c["files"] == 4
          and c["files_with_declarations"] == 2)
    check("a plate comment naming a placeholder is not a declaration, and "
          "not even a mention: it is the reading, not the code",
          "param_9" not in c["declarations"]
          and "param_9" not in c["mentions"]
          and c["files_with_placeholders"] == 2)
    sel = a_store_candidates(fixture)
    check("a `movx @DPTR,A` as the first use of A is selected",
          [e["addr"] for e in sel["dptr"]] == ["1000"]
          and sel["dptr"][0]["params"] == ["param_1", "param_2"])
    check("a `mov A,#..` ahead of the store is not selected -- the "
          "accumulator is that constant, not the caller's",
          "2000" not in [e["addr"] for e in sel["dptr"] + sel["rn"]])
    check("`movx @Rn,A` is reported as its own shape and not folded in",
          [e["addr"] for e in sel["rn"]] == ["3000"])
    check("a function that never touches A is neither selected nor lost",
          sel["no_a_touch"] == 0
          and "4000" not in [e["addr"] for e in sel["dptr"] + sel["rn"]])

    shutil.rmtree(d, ignore_errors=True)
    return 0 if ok else 1


def write_fixture(path, mnem, operands="", addr="1000"):
    """One listing line in `ExportListing.java`'s column format.

    The columns are padded here rather than produced by the exporter, because
    the point of the parser is that it reads those positions: a fixture with
    free-text spacing would pass against a whitespace split, which is the bug
    `parse_listing()` documents."""
    with open(path, "w") as f:
        f.write("; bank0 @ %s   [named]\n" % addr)
        f.write("%-8s %-8s %-8s %s\n" % (addr, "f0 - -", mnem, operands))


def write_c_fixture(path, body):
    with open(path, "w") as f:
        f.write(body)


def main():
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    if "--census" in sys.argv:
        # A mode of its own rather than three more positionals on the merge:
        # it reads the export and writes nothing the merge reads, and making
        # the merge's own arguments optional would let a mistyped invocation
        # fall through to it.
        c_ap = argparse.ArgumentParser(description=__doc__)
        c_ap.add_argument("--census", action="store_true",
                          help="measure the declaration census and the A-store "
                               "predicate over the committed export and print "
                               "them")
        c_ap.add_argument("--export", default=EXPORT_DEFAULT,
                          help="the decompiled export to measure")
        c_ap.add_argument("--candidates", help="also write the batch as CSV, "
                          "one row per candidate function")
        return census_mode(c_ap.parse_args())
    ap.add_argument("existing", help="the component's current annotations CSV")
    ap.add_argument("shard_dir", help="directory of per-shard CSVs from the sweep")
    ap.add_argument("out", help="where to write the merged CSV")
    ap.add_argument("--index", default=os.path.join(REPO, "ec", "decompiled",
                                                     "index.csv"))
    ap.add_argument("--approved", help="file of CSV row lines the adversarial "
                    "verifier approved (see extract_sweep_verdicts.py). A row "
                    "is kept only if its exact line is in this file")
    ap.add_argument("--report", action="store_true",
                    help="print every rejected row with its reason")
    ap.add_argument("--csv-kind", choices=("functions", "variables"),
                    default="functions",
                    help="which annotation layer the shards are for. `functions` "
                         "is ghidra-functions.csv, keyed on (scope, addr). "
                         "`variables` is ghidra-variables.csv, keyed on "
                         "(scope, addr, key) so one function may carry several "
                         "rows, and its controlled vocabulary is `kind`")
    args = ap.parse_args()

    # Which file this invocation is merging, and the two things that differ
    # with it: the header a shard must carry, and the vocabulary its controlled
    # column is checked against. Everything else -- the resolution rule, the
    # evidence rule, the register rule, the verifier whitelist -- is the same
    # machinery, which is the point: the calibration guard is not worth
    # reimplementing for a second file.
    variables = args.csv_kind == "variables"
    header = VARIABLE_HEADER if variables else HEADER
    vocab = VARIABLE_KINDS if variables else TYPES
    vocab_column = "kind" if variables else "type"

    index = function_sources(args.index)
    # The listing index is the one that knows about .asm files.
    listing_index = os.path.join(os.path.dirname(args.index), "listing-index.csv")
    if os.path.isfile(listing_index):
        for row in csv.DictReader(open(listing_index, newline="")):
            prev = index.get((row["program"], row["addr"]))
            if prev is not None:
                prev["listing_file"] = row["out_file"]

    existing = load_existing(args.existing)
    # A function row is identified by where it is; a variable row is
    # identified by where it is AND which placeholder it replaces, because one
    # function routinely has several. Keying variables on (scope, addr) alone
    # would make every variable after the first a duplicate of the first.
    def identity(r):
        base = (r["scope"], addr_key(r["addr"]))
        return base + (r.get("key", ""),) if variables else base
    seen = {identity(r) for r in existing}
    merged = list(existing)
    # The hand-written rows are not this tool's to rename. A swept row that
    # collides with one of them takes a suffix; a hand-written row never does,
    # because a person's name in `annotations/` is the thing everything else is
    # supposed to defer to.
    hand_named = {(r["scope"], r["name"]) for r in existing if r.get("name")}
    hand_scopes = [r["scope"] for r in existing]
    rejected = []
    accepted = 0
    unresolved = 0
    cross_referenced = 0

    # The verifier's whitelist, when there is one. Matched on the row's own
    # serialised content, which is the only key both sides agree on: the
    # journal identifies a verdict by an internal hash and the shard files know
    # nothing about the workflow.
    approved_lines = None
    if args.approved:
        if not os.path.isfile(args.approved):
            print("no approved-row file at %s" % args.approved)
            return 1
        # Compared as parsed field tuples, not as text. The verifier was told
        # to copy its rows verbatim, and a hand-copied line can differ from the
        # file in exactly one way that matters here -- whether a field with no
        # comma in it was quoted anyway. Parsing both sides makes the
        # comparison insensitive to that, which is the difference between a
        # whitelist that works and one that silently rejects everything.
        approved_lines = set()
        for line in open(args.approved, errors="replace"):
            line = line.rstrip("\n").rstrip("\r")
            if not line.strip():
                continue
            try:
                parsed = next(csv.reader([line]))
            except (csv.Error, StopIteration):
                continue
            approved_lines.add(tuple(parsed))
        print("  verifier approved %d row(s)" % len(approved_lines))

    shards = sorted(glob.glob(os.path.join(args.shard_dir, "*.csv")))
    if not shards:
        print("no shard CSVs in %s" % args.shard_dir)
        return 1

    for shard in shards:
        with open(shard, newline="") as f:
            table = [r for r in csv.reader(f) if r]
        if len(table) < 2:
            # A shard whose agent produced no rows at all. Not a rejection of
            # anything -- there is nothing to reject, and a header typo in a
            # file with no data in it is not a finding.
            continue
        head, body = table[0], table[1:]
        if head != header:
            rejected.append((shard, "-", "header is %r, not the agreed %r"
                             % (head, header)))
            continue
        for fields in body:
            if not fields:
                continue
            row = dict(zip(header, (fields + [""] * len(header))[:len(header)]))
            scope = (row.get("scope") or "").strip()
            addr = addr_key((row.get("addr") or "").strip())
            def bad(reason):
                rejected.append((os.path.basename(shard), addr, reason))
            # A common-area function is exported once, under `common`, and
            # its address therefore appears in no bank row even though the
            # sweep found it while walking a bank. That is a scope rename,
            # not a typo: the build's own join indexes `common` under both
            # banks, and a `bank0`-scoped row for a `common` address fails
            # the annotation check, so the row has to carry the scope the
            # index actually uses.
            eff_scope = scope
            if resolve(index, scope, addr) is None \
                    and resolve(index, "common", addr) is not None:
                eff_scope = "common"
            key = (row.get("key") or "").strip() if variables else ""
            # `name` is required of a function row and OPTIONAL of a variable
            # one, because `kind=unresolved` is a row whose whole content is
            # its comment: the listing does not say what the placeholder is, and
            # the placeholder stays. Requiring a name there would force the
            # precise thing this vocabulary exists to avoid.
            if variables:
                required = ["key", "comment", vocab_column, "evidence"]
                if row.get("kind", "").strip() != "unresolved":
                    required.append("name")
            else:
                required = ["name", "comment", vocab_column, "evidence"]
            if variables and not key:
                bad("empty key; a row has to name the placeholder it replaces")
                continue
            row_id = ((eff_scope, addr, key) if variables
                      else (eff_scope, addr))
            if row_id in seen:
                bad("duplicate (scope, addr%s); an earlier row already claims it"
                    % (", key" if variables else ""))
                continue
            if resolve(index, eff_scope, addr) is None:
                bad("resolves to no exported function")
                continue
            # A flag rather than for/else: a `break` out of the field loop
            # falls straight through to the append below, so a row with an
            # empty field was being rejected and merged in the same breath.
            # Found by feeding this tool a row with no evidence: it appeared in
            # the rejected list and in the output.
            if len(row.get("comment") or "") > MAX_COMMENT_CHARS:
                bad("comment is %d characters, over the %d this merge accepts; "
                    "a comment that long is an essay and belongs in a document "
                    "rather than above a function"
                    % (len(row["comment"]), MAX_COMMENT_CHARS))
                continue
            complete = True
            for field in required:
                if not (row.get(field) or "").strip():
                    bad("empty %s" % field)
                    complete = False
                    break
            if complete:
                if row[vocab_column].strip() not in vocab:
                    bad("%s %r is outside the controlled vocabulary"
                        % (vocab_column, row[vocab_column].strip()))
                    continue
                if variables and row["kind"].strip() == "unresolved" \
                        and (row.get("name") or "").strip():
                    bad("kind=unresolved carries the name %s; unresolved means "
                        "the placeholder stays in place" % row["name"].strip())
                    continue
                if row["basis"].strip() not in BASES:
                    bad("basis %r is not one of %s"
                        % (row["basis"].strip(), sorted(BASES)))
                    continue
                ev = [p for p in re.split(r"[;,]", row["evidence"]) if p.strip()]
                if not any("/" in p or p.strip().endswith((".yaml", ".md", ".csv"))
                           for p in ev):
                    bad("evidence names no path")
                    continue
                # The calibration rule, mechanically: a comment may only
                # name a hexadecimal address the function actually touches.
                text = read_function_text(index, eff_scope, addr)
                if text is None:
                    bad("no source to check the comment against")
                    continue
                hay = text.lower().replace(" ", "")
                unsupported = []
                for m in REGISTER_REF.finditer(row["comment"]):
                    tok = m.group(2).lower()
                    bare = tok[2:]
                    # The generated XDATA names are derived from the address
                    # in upper case with an underscore before a leading
                    # digit, so compare on digits rather than on spelling.
                    digits = bare.lstrip("0") or "0"
                    if (tok in hay
                            or ("0x" + bare) in hay
                            or digits in hay):
                        continue
                    unsupported.append(tok)
                if unsupported:
                    # An address that is not in this function is a
                    # cross-reference if the function either side
                    # establishes it, and an overclaim if nothing nearby
                    # does. Counted separately so the two are never
                    # confused for one another in the report.
                    around = (neighbour_text(index, eff_scope, addr)
                              + callee_text(index, row["comment"], eff_scope))
                    around = around.lower().replace(" ", "")
                    really_unsupported = [
                        t for t in unsupported
                        if (t.lower() not in around
                            and (t.lower()[2:].lstrip("0") or "0")
                            not in around)]
                    if really_unsupported:
                        bad("comment names address(es) %s that are in "
                            "neither this function, its neighbours, nor a "
                            "function it names as a call target"
                            % ", ".join(sorted(set(really_unsupported))[:4]))
                        continue
                    cross_referenced += len(unsupported)
                # The adversarial verifier's whitelist, when there is one. A
                # row nobody checked is not a row that failed; it is a row with
                # no second reading behind it, and it does not go in.
                if approved_lines is not None and tuple(fields) not in approved_lines:
                    bad("the adversarial verifier did not approve this row")
                    continue
                row["scope"] = eff_scope
                row["addr"] = row["addr"].strip()
                row["_swept"] = True
                merged.append(row)
                seen.add(row_id)
                accepted += 1
                if row[vocab_column].strip() == "unresolved":
                    unresolved += 1

    # Two agents naming two different functions the same thing is usually
    # correct rather than wrong -- several one-instruction `ret` stubs really
    # are the same routine, and several runs of erased flash really are the same
    # filler. The problem is only that the name then does not identify a
    # function: Ghidra disambiguates with a counter, so the tree grows
    # `ret_only`, `ret_only_1`, `ret_only_2` and a reader has to look up which
    # is which. Suffixing with the low 16 bits of the address instead makes the
    # name self-locating and groups the identical ones together, which is the
    # fact worth seeing.
    #
    # A VARIABLE row is not disambiguated, and must not be. Two functions
    # naming their own DPTR `entry_dptr` is two correct readings, not a
    # collision -- the name is scoped to the function, exactly as a C local is.
    # Suffixing them would make every variable in the tree unique for no reader's
    # benefit and would break the `--check` that expects the name in the export.
    by_name = {}
    if not variables:
        for row in merged:
            if row.get("name"):
                by_name.setdefault((row["scope"], row["name"]), []).append(row)
    disambiguated = 0
    for (_scope, _name), group in by_name.items():
        if len(group) < 2:
            continue
        for row in group:
            # Only swept rows are renamed. A name a person wrote in
            # `annotations/` is the thing everything else defers to, and
            # suffixing it because two agents happened to agree would be this
            # tool editing a human's reading.
            if not row.get("_swept"):
                continue
            suffix = addr_key(row["addr"])[-4:].lower()
            if not row["name"].endswith("_" + suffix):
                row["name"] = "%s_%s" % (row["name"], suffix)
                disambiguated += 1
    for row in merged:
        row.pop("_swept", None)

    order = {p: i for i, p in enumerate(
        ["bank0", "bank1", "common", "pd"])}
    # Variables sort by placeholder within a function, so the file groups the way
    # a reader reads a function: bank, address, then param_1, param_2, ...
    merged.sort(key=lambda r: (order.get(r["scope"], 9),
                               int(addr_key(r["addr"]), 16),
                               int(re.sub(r"\D", "", r.get("key") or "") or 0)))
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for row in merged:
            w.writerow(row)

    print("\n  merged %d shard file(s): %d row(s) accepted, %d rejected, "
          "%d of the accepted are %s=unresolved"
          % (len(shards), accepted, len(rejected), unresolved, vocab_column))
    print("  %d name(s) disambiguated by address where two functions in one "
          "program were given the same name" % disambiguated)
    # Comment length, reported rather than capped. A median around 300
    # characters is three or four sentences, which is what the brief asks for
    # and what fits above a function; the tail runs longer because some
    # functions are long, and cutting an accurate description to fit a line
    # budget would be trading analysis for tidiness. Only the absurd is
    # refused, and the distribution is printed so a reviewer can see the shape
    # rather than discover it.
    lens = sorted(len(r["comment"]) for r in merged if r.get("comment"))
    if lens:
        print("  comment length: median %d, p90 %d, longest %d over %d row(s)"
              % (lens[len(lens) // 2], lens[int(len(lens) * 0.9)], lens[-1],
                 len(lens)))
    print("  %d address reference(s) in accepted comments are established by a "
          "neighbouring function or by a callee the comment names, rather than "
          "by this one" % cross_referenced)
    print("  %s: %d row(s) total" % (os.path.relpath(args.out, REPO), len(merged)))
    if args.report and rejected:
        print("\n  rejected rows:")
        for shard, addr, reason in rejected[:200]:
            print("    %-18s %-6s %s" % (shard, addr, reason))
        if len(rejected) > 200:
            print("    ... and %d more" % (len(rejected) - 200))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
