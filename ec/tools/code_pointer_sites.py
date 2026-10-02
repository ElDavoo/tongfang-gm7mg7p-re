#!/usr/bin/env python3
"""Every image-wide `MOV DPTR,#imm16` whose DPTR turns out to be a *CODE*
pointer -- a `movc a,@a+dptr` table read or a `jmp @a+dptr` jump-table dispatch
-- committed as one regenerable row per site.

`scan_refs.py` counts `90 xx xx` bytes, and `register_ref_table.py` buckets
what each of them does. Neither writes the CODE-pointer population down, and
`annotations/static-refs-audit.md` §5.1 only carries the aggregate: "image-wide
there are 54 such sites across 48 addresses, none of them an address in
`registers.yaml`". The aggregate is the useful part and the list is the
unreproducible part -- the next person who needs the 48 re-derives them, and
gets a different answer if the walk has changed since. This tool is the list,
regenerated from the committed image by a command, and `--check` is what holds
it to that image.

**The two classes are picked out of `register_ref_table.CLASSES`, not
re-spelled.** `CODE_CLASSES` looks the two buckets up by their column header
(`movc`, `jmp`) rather than writing their labels out, so a rename in that file
moves this tool with it instead of silently emptying it -- a scan that quietly
starts finding nothing looks exactly like a scan that is working.

**A site on this list is a flag, not a verdict.** It means *this address has at
least one CODE-pointer site*, and nothing more. The converse is the
consequence people get wrong: an address that carries both a table site and
ordinary `movx` access is entirely ordinary, which is why the CSV is one row
per **site** and the tool reports 54 sites across 48 addresses rather than
collapsing them -- four addresses (`0x63BE`, `0x63D7`, `0xF13F`, `0xF45B`)
carry more than one, and the summary names them so the two figures cannot be
read as a contradiction. Being absent from the list means *this method found no
CODE pointer*, never that the address has no table behind it.

**The list is a floor, and the floor is the method's, not the image's.** It is
a linear best-effort decode -- `trace_xdata_refs.walk()`, over 8 instructions,
stopping at the first control-flow instruction -- and it inherits both of that
walk's limits: a CODE pointer reached past a branch is invisible, and the
`90 xx xx` scan is a byte scan and not an instruction-aligned one, so a hit can
in principle be an operand. `0x1051` is a site the walk resolves; nothing here
claims the walk resolves every one. A `movc` is a statement about the opcode
stream and about nothing else: no `status:` in `registers.yaml` moves because
one is on this list, and nothing here was measured on hardware.

**Data regions are labelled, never filtered.** `data_regions.region_at()` says
whether a site falls inside a span `annotations/data-regions.yaml` records as a
table, and the summary prints how many do -- zero at the time of writing, which
is a statement that this reading of the image found no known phantom here and
not that these sites are therefore real instructions. `refuse_filtering()` is
the rule as a refusal rather than a comment, so a future
`--only-outside-data-regions` has to delete it to be added; the reason is
`data_regions.py`'s, that a scan which dropped the phantoms would report a
smaller number indistinguishable from absence.

`--check` is not in `.github/scripts/agent-gates.sh` and cannot be from an
agent branch: the pipeline's push token has no `workflow` scope. The house
route for wiring it in is a prepared patch under `docs/ci/`, which this change
does not carry.

Usage:
    python3 code_pointer_sites.py ../firmware/GMxMGxx_11.800
    python3 code_pointer_sites.py --csv > ../annotations/code-pointer-sites.csv
    python3 code_pointer_sites.py --check
    python3 code_pointer_sites.py --self-test
    python3 code_pointer_sites.py --against-registers 0x07E6 0x07E7
"""
import argparse
import collections
import csv
import io
import os
import sys
import tempfile

import yaml

from data_regions import load as load_regions, region_at
from register_ref_table import CLASSES, bucket
from trace_xdata_refs import (MOV_DPTR, PD_MARKER, check_table, classify,
                              region_of, repo_path, runtime_addr, walk)

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REGISTERS_YAML = os.path.join(EC, "annotations", "registers.yaml")
SITES_CSV = os.path.join(EC, "annotations", "code-pointer-sites.csv")
DEFAULT_FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")


def column_label(column: str) -> str:
    """`register_ref_table.CLASSES`'s label for one column header.

    The lookup rather than a written-out label is the point: the two
    CODE-pointer classes are named by the columns that file prints them under,
    so a rename there moves this tool with it instead of leaving it filtering
    on a name nothing produces any more -- which is a scan that has quietly
    started finding nothing and looks exactly like a scan that is working.

    Refused rather than defaulted, because a missing column means the two files
    disagree about the vocabulary this tool's whole premise is borrowed, and
    the fix belongs in the file that owns the name.
    """
    for label, short in CLASSES:
        if short == column:
            return label
    raise SystemExit(
        f"error: register_ref_table.CLASSES has no `{column}` column, so this "
        "tool cannot name its CODE-pointer classes from it. Add the column\n"
        "       there rather than spelling the label out here.")


# The two buckets of CLASSES that are CODE-pointer reads, in the order §5.1's
# table prints them.
CODE_POINTER_COLUMNS = ("movc", "jmp")
CODE_CLASSES = tuple(column_label(c) for c in CODE_POINTER_COLUMNS)
JMP_CLASS = column_label("jmp")

# The CSV's columns, in order. `ec-0x07d0-sites.csv` and
# `register_ref_table.py --csv` are the two tables this one sits beside, and
# the order is theirs: address and where it is, then what the site does. The
# per-site `window` is the decoded opcodes after the site's own `MOV DPTR`,
# which is where a reader checks the class by hand. A committed table's header
# is a promise about its rows, so it is a list here rather than a format
# string, and `--check` diffs the bytes this writes.
CSV_COLUMNS = ["addr", "file_offset", "region", "runtime", "class", "window"]

# The regions a site is expected to land in, and what "no runtime address" would
# mean. `region_of()` answers "unknown" for an offset outside the mapped regions
# and `runtime_addr()` answers None there, and both have to be reported rather
# than dropped: a site whose runtime address is unknown cannot be cross-read in
# r2 at all, so a reader checking the list by hand would never reach it.
UNMAPPED = "unknown"


def refuse_filtering() -> None:
    """Why no mode of this tool drops a site.

    Reached only from `--self-test`, and deliberately so: the rule is worth
    something if it survives someone adding a `--only-outside-data-regions`
    flag, and a rule that lives in a comment has to be re-argued to survive.
    Same shape as `data_regions.refuse_filtering()`, which is the rule this one
    is the other half of.
    """
    raise SystemExit(
        "error: no mode filters rows out of this scan. A site inside a span\n"
        "       data-regions.yaml lists is labelled, not dropped: dropping it\n"
        "       makes a smaller list nobody can audit, and a smaller list is\n"
        "       indistinguishable from one that found nothing.")


def require_pd(d: bytes) -> bool:
    """The PD image's own marker, as the refusal it is.

    A SystemExit rather than a note on stdout because the failure it prevents
    is silent: without the marker `region_of()` calls 0x20000-0x2FFFF
    `unknown`, the per-region split silently loses its `pd-image` row, and a
    reader comparing a 5-site difference against §5.1's numbers has no way to
    tell a changed image from an unidentified one. `trace_xdata_refs.py` notes
    the same fact and carries on; here the region split is a headline number,
    so it is worth refusing over.
    """
    off, magic = PD_MARKER
    if d[off:off + len(magic)] == magic:
        return True
    raise SystemExit(
        f"error: no {magic.decode()!r} marker at file 0x{off:05X} -- the 0x20000\n"
        "       region is not the ITE8850-PD image this tool's region map\n"
        "       describes, so its sites would be reported as region 'unknown'\n"
        "       and the per-region split would under-report without saying so.\n"
        "       Re-derive the map with find_banks.py before running this on a\n"
        "       different dump.")


def immediate(d: bytes, o: int) -> int:
    """The 16-bit literal a `MOV DPTR,#imm16` at file offset `o` carries.

    `d[o]` is the `0x90`, which the caller has already matched, so the two
    bytes after it are the whole of the address and there is no bounds question
    left to answer.
    """
    return (d[o + 1] << 8) | d[o + 2]


def code_pointer_sites(d: bytes, pd_verified: bool) -> list:
    """(offset, addr, class, region, runtime, window) for every CODE-pointer
    site, in file-offset order.

    The scan is every `0x90` in the image rather than
    `trace_xdata_refs.sites_for()` per address, because the address is what is
    being discovered: asking the question address by address would need the
    list of addresses first, which is the thing this tool produces. It is the
    same byte scan `sites_for()` performs, in the same order, with the same
    `walk()`/`classify()`/`bucket()` applied to what each one decodes -- so the
    classification vocabulary cannot drift from
    `annotations/static-refs-audit.md` §5's, which is the table whose numbers
    this one has to agree with.

    Offsets inside a region the map does not cover are kept, with region
    `unknown` and runtime None, rather than skipped. The count on a different
    dump is then a count over the same question, and the two places that would
    otherwise have to notice the difference -- the summary and the CSV -- are
    the same walk.
    """
    out = []
    for o in range(len(d) - 2):
        if d[o] != MOV_DPTR:
            continue
        insns = walk(d, o)
        label = bucket(classify(insns))
        if label not in CODE_CLASSES:
            continue
        out.append((o, immediate(d, o), label, region_of(o, pd_verified)[0],
                    runtime_addr(o, pd_verified),
                    " ; ".join(" ".join(m.split()) for _, _, m in insns[1:])))
    return out


def csv_table(sites: list) -> str:
    """The `--csv` table, as a string rather than a write.

    A string because `--check` diffs the same bytes this prints, and a tool
    whose output only exists once written is a tool whose output cannot be
    compared without a temporary file. Rows keep the scan's file-offset order,
    so a site that moves in the image moves here too and the diff says where.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for o, addr, label, region, rt, window in sites:
        w.writerow([f"0x{addr:04X}", f"0x{o:05X}", region,
                    f"0x{rt:04X}" if rt is not None else "", label, window])
    return buf.getvalue()


def region_split(sites: list) -> collections.Counter:
    """How many sites fall in each region, for the summary line.

    A Counter rather than a fixed list of regions so a region this scan has
    never seen still gets a row instead of being dropped by a table that did not
    list it. `region_of()`'s spelling is the vocabulary, unchanged.
    """
    return collections.Counter(region for _, _, _, region, _, _ in sites)


def repeated(sites: list) -> dict:
    """{addr: its site count} for addresses carrying more than one site.

    Reported in the summary because the two headline figures are different
    numbers and a reader who has only been told one of them will assume the
    other is a mistake. `0x63BE` at three sites is the case §5.1 already worked
    by hand; the other three were not known to it.
    """
    counts = collections.Counter(addr for _, addr, _, _, _, _ in sites)
    return {a: n for a, n in counts.items() if n > 1}


def registers_addrs(path: str = REGISTERS_YAML) -> set:
    """Every address `registers.yaml` names, read-only.

    `addr` is a list for a pair and a scalar otherwise, and both are counted --
    a `0x0740`/`0x0741` entry contributes two numbers, and the pre-flight
    question is per number. `status:` is deliberately not read: the question
    here is which numbers the file carries, not what it concludes about them,
    and reading the status would invite the answer to be read as a verdict on
    the register.

    This file is opened for reading and nothing in this tool writes to it.
    `../tools/test_code_pointer_sites.py` pins that with a tripwire over
    `open` in any write mode, the way `test_inc_dptr_sites.py` does for the
    same file.
    """
    with open(path) as f:
        doc = yaml.safe_load(f)
    out = set()
    for entry in doc["registers"]:
        addr = entry["addr"]
        out.update(addr if isinstance(addr, list) else [addr])
    return out


def jmp_shapes(sites: list) -> collections.Counter:
    """The decoded window of each `jmp @a+dptr` site, counted.

    A shape census and not a decode: fifteen of the eighteen share one window
    and three carry a bare `jmp @a+dptr`, and that is what the opcode stream
    says. What the tables those jumps dispatch into is a different question,
    and nothing here answers it -- `docs/findings/code-pointer-site-census.md`
    is explicit that this is a record of an instruction shape.
    """
    return collections.Counter(window for _, _, label, _, _, window in sites
                               if label == JMP_CLASS)


def self_test(d: bytes, pd_verified: bool) -> int:
    """Known answers, and the refusals.

    Two halves, for the reason this repository keeps restating: a check that
    has quietly stopped refusing looks exactly like a check that is working.
    The known answers are transcribed from oracles outside this file --
    `annotations/static-refs-audit.md` §5.1 and the r2 transcripts below it for
    the worked examples, and `../annotations/code-pointer-sites.csv` for the
    splits -- so a tool graded against its own output is not what is being
    tested. The CSV half is not independent of the tool and is not claimed to
    be: it holds the committed table to today's run, which is the same
    narrower claim `--check` makes, and `--check` is the mode that decides
    whether the table should be regenerated.
    """
    bad = 0
    print("code_pointer_sites.py --self-test")

    def expect(label, ok, detail=""):
        nonlocal bad
        bad += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'}  {label}"
              + (f"  {detail}" if detail and not ok else ""))

    def refuses(fn, *a):
        try:
            fn(*a)
        except SystemExit:
            return True
        return False

    sites = code_pointer_sites(d, pd_verified)
    addrs = {addr for _, addr, _, _, _, _ in sites}

    # --- the two classes, and the vocabulary they are found through ---------
    expect("CLASSES still has exactly the two CODE-pointer buckets",
           CODE_CLASSES == ("movc (CODE pointer)", "jmp @a+dptr"),
           f"got {CODE_CLASSES}")
    expect("a column name CLASSES does not have is refused, not defaulted",
           refuses(column_label, "table"))

    # --- the aggregate, from §5.1 -------------------------------------------
    expect("54 sites", len(sites) == 54, f"got {len(sites)}")
    expect("48 distinct addresses", len(addrs) == 48, f"got {len(addrs)}")
    tally = collections.Counter(label for _, _, label, _, _, _ in sites)
    expect("36 movc / 18 jmp",
           (tally[CODE_CLASSES[0]], tally[JMP_CLASS]) == (36, 18),
           f"got {dict(tally)}")
    expect("§5.1's four repeated addresses are the four this scan finds",
           repeated(sites) == {0x63BE: 3, 0x63D7: 3, 0xF13F: 2, 0xF45B: 2},
           f"got {repeated(sites)}")

    # --- the per-region split, from the committed CSV ------------------------
    split = region_split(sites)
    expect("bank1=31 bank0=10 common=8 pd-image=5",
           dict(split) == {"bank1": 31, "bank0": 10, "common": 8, "pd-image": 5},
           f"got {dict(split)}")
    expect("no site in either erased region",
           not any(r == "erased" for r in split), f"got {sorted(split)}")
    expect("no site outside the mapped regions",
           UNMAPPED not in split, f"got {sorted(split)}")
    expect("no site whose runtime address is unresolved",
           not [s for s in sites if s[4] is None])

    # --- the worked examples §5.1 decodes in r2, by address and by file -----
    by_addr = collections.defaultdict(list)
    for o, addr, _, _, _, _ in sites:
        by_addr[addr].append(o)
    windows = {o: (label, window) for o, _, label, _, _, window in sites}
    expect("0x63BE is at 0xA6A4 with the two siblings the audit did not name",
           by_addr[0x63BE] == [0x0A6A4, 0x0A6B7, 0x0A6CC],
           f"got {[f'0x{o:05X}' for o in by_addr[0x63BE]]}")
    expect("0x63D7 carries three sites",
           len(by_addr[0x63D7]) == 3,
           f"got {[f'0x{o:05X}' for o in by_addr[0x63D7]]}")
    # §5.1's r2 transcript: `s 0x1051` in a bank image is `mov dptr,#0x1100`
    # then `jmp @a+dptr`, and the common area sits at its file offset, so the
    # file offset and the runtime address §5.1 seeks to are the same number.
    expect("0x1100 is the jmp @a+dptr §5.1 names at 0x1051",
           by_addr[0x1100] == [0x01051] and windows[0x01051] == (JMP_CLASS,
                                                                 "jmp @a+dptr"),
           f"got {by_addr[0x1100]} / {windows.get(0x01051)}")

    # --- the shape census, recorded as a shape and not a decode -------------
    shapes = jmp_shapes(sites)
    expect("15 jmp sites share one scaled shape and 3 are a bare jmp",
           sorted(shapes.values()) == [3, 15] and len(shapes) == 2,
           f"got {dict(shapes)}")

    # --- the data-region label, and the fact that it is not a filter --------
    expect("no site falls inside a listed data region",
           data_region_overlap(sites) == 0, f"got {data_region_overlap(sites)}")

    # --- the refusals -------------------------------------------------------
    expect("the annotate-never-suppress refusal is a refusal",
           refuses(refuse_filtering))
    expect("an image without the PD marker is refused, not reported as unknown",
           refuses(require_pd, bytes(len(d))))
    with tempfile.TemporaryDirectory() as scratch:
        # The mutations are applied to the table this run produced, not to the
        # committed one, because the claim under test is that `--check`
        # rejects a report it cannot reproduce. Mutating the committed file
        # would test the same diff and say nothing about which side moved.
        generated = csv_table(sites)
        for label, mutate in MUTATIONS:
            expect(f"--check rejects a report that is {label}",
                   check_table(generated, mutant(scratch, mutate(generated))) == 1)
        expect("--check accepts the committed table this run reproduces",
               check_table(generated, SITES_CSV) == 0)

    print(f"{'all checks passed' if not bad else f'{bad} FAILED'}")
    return 1 if bad else 0


# The three ways a committed table stops describing the image. Each mutates the
# bytes `csv_table()` produced rather than calling the tool again, so what is
# under test is the diff and not the mutation.
def _drop_a_row(table: str) -> str:
    """A table short its last row -- the shape a truncated commit leaves."""
    return "".join(table.splitlines(keepends=True)[:-1])


def _respell_a_class(table: str) -> str:
    """A class cell rewritten by hand into something more explanatory.

    The mutation a future reader is most likely to make, and the one that reads
    as an improvement: a diff is the only thing standing between that and a
    committed table that no longer describes the image.
    """
    return table.replace(JMP_CLASS, "jmp @a+dptr (jump table)", 1)


def _rename_a_column(table: str) -> str:
    """The header cell renamed, which would leave every row one field short."""
    head, _, rest = table.partition("\n")
    return head.replace("region", "where", 1) + "\n" + rest


MUTATIONS = (("short one row", _drop_a_row),
             ("a class cell respelled", _respell_a_class),
             ("a column renamed", _rename_a_column))


def committed_table() -> str:
    """`../annotations/code-pointer-sites.csv` as it is on disk.

    Read with `newline=""` for the reason `check_table()` gives: the committed
    table carries the csv module's own CRLF terminator, and universal-newline
    translation would rewrite every one of those terminators and make the
    self-test's accept case red on a table that is in fact reproduced.
    """
    with open(SITES_CSV, newline="") as f:
        return f.read()


def mutant(scratch: str, text: str) -> str:
    """A throwaway file holding `text`, for the self-test's `--check` cases.

    The committed table must not be the thing under mutation: these cases are
    about what `--check` does with a table it did not produce, and a self-test
    that edited the real file to find out would leave a red `--check` behind if
    it died halfway. Written into `scratch` rather than `tempfile`'s directory
    so the whole set is removed by the one context manager.
    """
    handle, path = tempfile.mkstemp(suffix=".csv", dir=scratch, text=True)
    with os.fdopen(handle, "w", newline="") as f:
        f.write(text)
    return path


def report(sites: list) -> None:
    """The default console output: the aggregate, then every site.

    The list is printed in the same file-offset order `--csv` writes, so the
    two cannot describe different scans, and the addresses that carry more than
    one site are named in the summary above it -- the only place where the
    "54 sites" and "48 addresses" figures would otherwise read as a
    contradiction.
    """
    tally = collections.Counter(label for _, _, label, _, _, _ in sites)
    split = region_split(sites)
    addrs = {addr for _, addr, _, _, _, _ in sites}

    print(f"{len(sites)} CODE-pointer site(s) across {len(addrs)} address(es): "
          + "  ".join(f"{label}={n}" for label, n in sorted(tally.items())))
    print("  by region: "
          + "  ".join(f"{region}={split[region]}"
                      for region in sorted(split) if region != UNMAPPED))
    if UNMAPPED in split:
        print(f"  {split[UNMAPPED]} site(s) fall outside the mapped regions, "
              "so they have no runtime address and cannot be cross-read in r2; "
              "this is a fact about the image map, not about the sites")
    dupes = repeated(sites)
    if dupes:
        print("  more than one site: "
              + "  ".join(f"0x{a:04X} x{n}" for a, n in sorted(dupes.items()))
              + "  (this is why sites and addresses are different numbers)")
    shapes = jmp_shapes(sites)
    if len(shapes) > 1:
        print("  jmp window shapes: "
              + "  ".join(f"x{n} `{w}`" for w, n in shapes.most_common()))
    print(f"  data-regions.yaml overlap: {data_region_overlap(sites)} of "
          f"{len(sites)} site(s) fall inside a listed span")
    print()
    for o, addr, label, region, rt, window in sites:
        rt_text = f"0x{rt:04X}" if rt is not None else "runtime n/a"
        print(f"  0x{addr:04X}  file 0x{o:05X}  {region:<9} {rt_text}  {label}")
        print(f"      {window}")


def data_region_overlap(sites: list) -> int:
    """How many sites fall inside a span `data-regions.yaml` records.

    A label, and the report prints it as one. Zero means no site of this scan
    coincides with a span a human has already read as a table; it does not mean
    these sites are therefore instructions, and it is not a filter -- every site
    is listed either way, which is what `refuse_filtering()` is there to keep
    it that way.
    """
    regions = load_regions()
    return sum(1 for o, _, _, _, _, _ in sites if region_at(regions, o))


def against_registers(sites: list, asked=None) -> int:
    """The pre-flight answer: is any address in `registers.yaml` on this list.

    With no `asked`, the question is §5.1's own null -- every address the file
    currently carries -- and the run names the population it read alongside the
    answer, so a reader can see the null was taken over the whole file rather
    than over whatever number was written down when this mode was added. The
    figure is this run's output over the file it opened, not a value committed
    anywhere, which is the point: `registers.yaml` grows at almost every
    landing change here, and a null pinned to a population would go stale
    without anything turning red.

    Exit code is 0 whether or not the intersection is empty. A non-empty one is
    a fact about an address, not a failure of the tool, and the addresses that
    would be affected by it are exactly the ones a reader needs to see; making
    it non-zero would make the mode usable in a gate in a way nothing authorises.
    """
    on_list = {addr for _, addr, _, _, _, _ in sites}
    in_file = registers_addrs()
    hits = sorted(on_list & (asked if asked is not None else in_file))
    if asked is None:
        print(f"{len(in_file)} address(es) in {repo_path(REGISTERS_YAML)}, "
              f"{len(hits)} of them on the CODE-pointer list")
    else:
        for addr in sorted(asked):
            mark = "ON THE LIST" if addr in on_list else "no CODE-pointer site"
            print(f"  0x{addr:04X}  {mark} (found by this method)")
    if not hits:
        print("none. This is a statement about this method over this image: a\n"
              "       site reached past a branch, or a `90 xx xx` that is an\n"
              "       operand rather than an instruction, is not on the list and\n"
              "       is not excluded by it.")
        return 0
    print("these addresses carry a CODE-pointer site, so a `static_refs` count "
          "for one of them\nincludes a table read and is not by itself evidence "
          "of a live register:")
    for o, addr, label, region, rt, _ in sites:
        if addr in hits:
            rt_text = f"0x{rt:04X}" if rt is not None else "runtime n/a"
            print(f"  0x{addr:04X}  file 0x{o:05X}  {region:<9} {rt_text}  {label}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware", nargs="?", default=DEFAULT_FIRMWARE,
                    help="raw EC firmware image (default: the committed one, "
                         "ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per site on stdout instead of the report")
    ap.add_argument("--check", nargs="?", const=SITES_CSV, metavar="PATH",
                    help="diff this run against the committed table and exit "
                         f"non-zero on any difference (default: {repo_path(SITES_CSV)})")
    ap.add_argument("--self-test", action="store_true",
                    help="the known answers and the refusals, including that "
                         "--check rejects a table this run cannot reproduce")
    ap.add_argument("--against-registers", nargs="*", metavar="ADDR", default=None,
                    help="report which of the given hex addresses is on this "
                         "list -- the pre-flight check for one about to be "
                         "added to registers.yaml. With no address, the whole "
                         "file, which is §5.1's null re-run over whatever the "
                         "file carries today. The addresses are values on the "
                         "flag rather than a second positional so that the "
                         "image, which has a default, stays the only one")
    args = ap.parse_args()

    if args.csv and args.check is not None:
        ap.error("--check diffs the --csv table; give one or the other")
    if args.against_registers is not None and (args.csv or args.check is not None):
        ap.error("--against-registers is a report about addresses, not a "
                 "table; it does not go with --csv or --check")
    if args.self_test and (args.csv or args.check is not None
                           or args.against_registers is not None):
        ap.error("--self-test runs on the committed image and takes no other "
                 "mode's arguments")

    d = open(args.firmware, "rb").read()
    pd_verified = require_pd(d)

    if args.self_test:
        return self_test(d, pd_verified)

    sites = code_pointer_sites(d, pd_verified)

    if args.check is not None:
        return check_table(csv_table(sites), args.check)
    if args.csv:
        sys.stdout.write(csv_table(sites))
        return 0
    if args.against_registers is not None:
        asked = ({int(text, 16) for text in args.against_registers}
                 if args.against_registers else None)
        return against_registers(sites, asked)

    report(sites)
    return 0


if __name__ == "__main__":
    sys.exit(main())
