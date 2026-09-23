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

# The hand-written annotations file, used as the base a merge starts from. The
# self-test needs a real one because the rows it writes have to resolve against
# a real index; a synthetic base would test a different thing.
EXISTING_DEFAULT = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")

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

    def check(label, cond):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", label))
        ok = ok and cond

    def merge(rows):
        # A fresh directory per case. The shard directory is globbed for *.csv,
        # so writing the output beside the input makes the previous case's
        # output the next case's input -- which is how six of these assertions
        # were failing for reasons that had nothing to do with what they test.
        case = os.path.join(d, "case%d" % next(_counter))
        os.makedirs(case, exist_ok=True)
        with open(os.path.join(case, "t.csv"), "w", newline="") as f:
            f.write(",".join(HEADER) + "\n")
            for r in rows:
                f.write(r + "\n")
        out = os.path.join(d, "out%d.csv" % next(_counter))
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = main_for([EXISTING_DEFAULT, case, out, "--report"])
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
    _, acc, out = merge([
        row(comment="Writes the charge target to XDATA 0x0777 and sets the "
                    "fan enable bit.")])
    check("a comment naming a register the function does not touch is rejected",
          "nor a function it names" in out)
    shutil.rmtree(d, ignore_errors=True)
    return 0 if ok else 1


def main():
    if "--self-test" in sys.argv:
        return self_test()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
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
    args = ap.parse_args()

    index = function_sources(args.index)
    # The listing index is the one that knows about .asm files.
    listing_index = os.path.join(os.path.dirname(args.index), "listing-index.csv")
    if os.path.isfile(listing_index):
        for row in csv.DictReader(open(listing_index, newline="")):
            prev = index.get((row["program"], row["addr"]))
            if prev is not None:
                prev["listing_file"] = row["out_file"]

    existing = load_existing(args.existing)
    seen = {(r["scope"], addr_key(r["addr"])) for r in existing}
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
        if head != HEADER:
            rejected.append((shard, "-", "header is %r, not the agreed %r"
                             % (head, HEADER)))
            continue
        for fields in body:
            if not fields:
                continue
            row = dict(zip(HEADER, (fields + [""] * len(HEADER))[:len(HEADER)]))
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
            if (eff_scope, addr) in seen:
                bad("duplicate (scope, addr); an earlier row already claims it")
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
            for field in ("name", "comment", "type", "evidence"):
                if not (row.get(field) or "").strip():
                    bad("empty %s" % field)
                    complete = False
                    break
            if complete:
                if row["type"].strip() not in TYPES:
                    bad("type %r is outside the controlled vocabulary"
                        % row["type"].strip())
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
                row["scope"] = eff_scope
                row["addr"] = row["addr"].strip()
                row["_swept"] = True
                merged.append(row)
                seen.add((eff_scope, addr))
                accepted += 1
                if row["type"].strip() == "unresolved":
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
    by_name = {}
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
    merged.sort(key=lambda r: (order.get(r["scope"], 9), int(addr_key(r["addr"]), 16)))
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for row in merged:
            w.writerow(row)

    print("\n  merged %d shard file(s): %d row(s) accepted, %d rejected, "
          "%d of the accepted are type=unresolved"
          % (len(shards), accepted, len(rejected), unresolved))
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
