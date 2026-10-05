#!/usr/bin/env python3
"""Per-address reachability for a span of the EC's XDATA, joining every
addressing form the committed tools can already see.

**Why this is a new file and not a mode on `xdata_span_survey.py`.** That tool
counts `MOV DPTR,#imm16` byte sites per image and says nothing about what they
do; this one asks a different question of the same span -- *is this address
reached at all, and by which site* -- and answers it from four more passes that
already exist. Its `--csv` output is reproduced byte-for-byte by committed
tables elsewhere in the tree, so a new mode on it would have had to answer for
those too. CLAUDE.md's "a new tool is a new file" is the same rule.

**The verdict vocabulary, and why there is no "absent".** Two tokens, and a
zero is always the second of them:

    reached                     a site in this table reaches THIS address
    not-reached-by-this-method  no pass run here reaches it

`not-reached-by-this-method` is `dsdt_ec_fields.py`'s `NO_SITE` under the name
this page's own methods warrant, and it is deliberately **not** a
`registers.yaml` `status:` value: a status grades what is known about a
register, and what is known here is only what five static passes found.
`check_status_vocabulary.py` reads that file's header comment for the declared
list, so a token that leaked in from here would be caught there -- and
`test_xdata_page_reach.py` asserts the two vocabularies stay disjoint from this
side too.

**Reaching a page is not reaching an address, and the table keeps them apart.**
A computed `mov DPH,a` whose high byte an immediate supplies reaches the *page*
it names and no address within it, because the low byte is a run-time value.
That is a real finding -- the page is not dead -- and it is the difference
between "nothing here" and "nothing here that names this byte", so it has its
own `page_site` column rather than being folded into the verdict. **Crediting
the page's every address instead would be the overclaim this repository has
retracted twice**: it would make `reached` true of all 256 addresses of a page
whose low byte no site in the image resolves, which is a statement about the
column and not about the firmware. So the verdict stays address-level, and a
row can read `not-reached-by-this-method` beside a `page_site` that says the
page is reached.

**The five passes, and what each one is blind to.** A reach is only ever
"reached" if one of these produced a site for *this* address; the summary
prints what each contributed, and a pass that contributed nothing to the span
says so rather than being dropped.

  1. `mov dptr,#imm16` direct sites, located by `trace_xdata_refs.sites_for()`
     and counted per image by `xdata_span_survey.survey()` -- the same `90 hi lo`
     byte pattern `scan_refs.py` uses, so the `direct_main_ec` /
     `direct_pd_image` columns are that tool's numbers and can be compared with
     it directly. Not instruction-aligned, so a hit can be an operand byte or
     table data; and it cannot see a pointer at all.
  2. The direction and the `inc dptr` walk of each of those sites, from
     `trace_xdata_refs.walk_why()`/`classify()`. **A walk is the reach the
     count alone can miss**: a site that writes its seed address and the one
     after it reaches the second address with no site of its own. It is
     reported separately (`walk`) because the two reach different addresses,
     and on a span whose walks all land on bytes that have sites of their own
     it contributes no address -- which is a measurement, not a defect.
  3. Computed DPTR, from `computed_dptr_sites.page_of_sites()`. Reaches the
     page (`page_site`); reaches an address only where the low byte is
     resolved, and **no site in this image resolves one**, so that arm is
     carried because the case exists, not because it fires.
  4. The `addc DPH` residual, `addc_dph_sites.residual()`. Its page set is
     always two elements, so a row on this page's high byte makes the page
     *possible*, never reached -- and it is reported as such.
  5. `movx @Ri` with a literal P2 and Rn, from `find_indirect_xdata.sites()`.

**What this cannot see, named rather than left to the reader.** An `inc dptr`
walk needs a two-byte seed to start from, so a walk entered from a subroutine
that received DPTR is not followed -- `classify()`'s own
`DPTR handed to ...` cell is that case. An `movx @Ri` needs both halves
literal, and `find_indirect_xdata`'s population leaves at least one unresolved
at every site in this image, so the `indirect` reach is empty wherever this runs;
`unresolved_by()` says which half, per site. A pointer held in a register and
dereferenced later reaches nothing here, which is the same blind spot the
*writer* has and is why a page can be fully written and fully unread at the same
time. None of these is evidence that the address is untouched, and the write-up
says so.

Read-only: it opens the firmware image for reading and writes nothing.

Usage:
    python3 xdata_page_reach.py ../firmware/GMxMGxx_11.800 0x0E00 0x0EFF
    python3 xdata_page_reach.py ../firmware/GMxMGxx_11.800 0x0E00 0x0EFF --csv
    python3 xdata_page_reach.py ../firmware/GMxMGxx_11.800 0x0E00 0x0EFF --csv \\
        --check ../annotations/xdata-0exx-page-reach.csv
"""
import argparse
import collections
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import addc_dph_sites                                          # noqa: E402
import computed_dptr_sites as C                                # noqa: E402
import find_indirect_xdata as I                                # noqa: E402
import trace_xdata_refs as T                                   # noqa: E402
import xdata_span_survey as S                                   # noqa: E402

# The two verdict tokens, and nothing else. `REACHED` is what a reader needs to
# act on; every other row is a statement about the method, never about the
# byte. Declared here rather than spelled inline so the suite asserts the
# closed vocabulary instead of a substring.
REACHED = "reached"
NOT_REACHED = "not-reached-by-this-method"
VERDICTS = (REACHED, NOT_REACHED)

# How each pass is named in the `reach` cell, so a reader can tell which of
# them produced the site. `walk` is separate from `direct` because the two
# reach different addresses: a walk reaches the bytes after its seed, which
# carry no site of their own.
DIRECT = "direct"
WALK = "walk"
COMPUTED = "computed"
INDIRECT = "indirect"


def site_label(d: bytes, offset: int, pd_verified: bool) -> str:
    """`region:0xADDR` for a file offset, the spelling the write-ups use.

    The runtime address rather than the file offset, because a site in bank0
    is cited as `bank0:0xF335` everywhere else in this repository and two
    spellings for one byte is one more thing to keep straight.
    """
    runtime = T.runtime_addr(offset, pd_verified)
    region = T.region_of(offset, pd_verified)[0]
    if runtime is None:
        return f"{region}:file-0x{offset:05X}"
    return f"{region}:0x{runtime:04X}"


def direct_reach(d: bytes, lo: int, hi: int, pd_verified: bool):
    """[(address, method, site label, direction)] over the direct sites.

    **A walk is credited from the seed's window, and only within it.** The
    addresses past the seed come from `walk_span()` over the same instruction
    list `classify()` reads, so the reach and the `reach_cell` prose a reader
    checks it against are two views of one decode. A site whose window
    `classify()` declined to describe -- a DPTR handed to an `lcall`, a window
    with no `movx` -- contributes its seed and no walk, which is the honest
    reading: the window did not say the walk went anywhere.
    """
    out = []
    for addr in range(lo, hi + 1):
        for off in T.sites_for(d, addr):
            insns, _why = T.walk_why(d, off)
            label = site_label(d, off, pd_verified)
            direction = T.classify(insns)
            out.append((addr, DIRECT, label, direction))
            out.extend((addr + step, WALK, label, direction)
                       for step in range(1, walk_span(insns)))
    return out


def walk_span(insns) -> int:
    """How many consecutive addresses this site's window rides DPTR over.

    The same count `classify()` makes -- one plus the `inc dptr` opcodes after
    the seed -- recovered as a number so a reach can be attributed to the
    addresses past the seed. Counted off the instruction list rather than
    parsed out of `classify()`'s prose, so a wording change cannot silently
    move a reach; and `skip=1` because the seed's own instruction is the
    `mov dptr,#imm16`, which carries no direction and moves nothing.

    The budget is `walk_why()`'s, so a window the walk cut short contributes
    the reach its decoded instructions show and no further. That is a limit
    on the look rather than a fact about the byte, and it is why the write-up
    names the window's terminator rather than reading this as the walk's real
    extent.
    """
    return 1 + sum(1 for _, raw, _text in insns[1:] if raw[0] == 0xA3)


def computed_reach(d: bytes, lo: int, hi: int, pd_verified: bool):
    """([(address, label, cell)], {page: [(label, cell)]}) from the computed
    DPTR sites.

    Two returns because the pass reaches two different things and the table
    must not merge them. An address goes in the first list only where the site
    resolved its **low** byte -- a concrete address, reached. Everything else
    goes in the second, keyed by page: the site reaches the page and no
    address in it, because the low byte is a run-time value.

    The split is not a precaution. **No site in this image resolves a low
    byte**, so a version that credited the page to its addresses would print
    `reached` for every address of a reached page and the column would say
    nothing at all -- and the write-up's whole point is the addresses it
    cannot separate. The `page_site` column carries the finding instead: the
    page is reached, the byte is not named.
    """
    reached, pages = [], collections.defaultdict(list)
    for page in sorted({addr >> 8 for addr in range(lo, hi + 1)}):
        hits, _undecided = C.page_of_sites(d, pd_verified, page)
        for _region, rows in hits.items():
            for row in rows:
                label = site_label(d, row["offset"], pd_verified)
                if row["low_value"] is not None:
                    addr = (row["page_value"] << 8) | row["low_value"]
                    if lo <= addr <= hi:
                        reached.append((addr, label, row["xaddr"]))
                    continue
                pages[page].append((label, row["xaddr"]))
    return reached, pages


def possible_pages(d: bytes, lo: int, hi: int, pd_verified: bool):
    """{page: [label, ...]} for the `addc DPH` residual's two-element sets.

    A *possible* page, kept out of the reach table on purpose. The set always
    has two members because `addc` reads a carry this scan never establishes,
    so a row here is a page the method could not rule out -- a reader who saw
    it in the `reach` column would read a reach that does not exist.
    """
    out = collections.defaultdict(list)
    pages = {addr >> 8 for addr in range(lo, hi + 1)}
    for row in addc_dph_sites.residual(d, pd_verified):
        if not pages & set(row["pages"]):
            continue
        for page in sorted(set(row["pages"]) & pages):
            out[page].append(site_label(d, row["offset"], pd_verified))
    return out


def indirect_reach(d: bytes, lo: int, hi: int, pd_verified: bool):
    """[(address, method, site label, cell)] for `movx @Ri` with both halves.

    `resolve()` returns a bare `0xNNNN` only when P2 and the register load are
    both literal; every other cell is prose, and this reads the structured
    `p2`/`rn` fields rather than parsing that prose back, for the reason
    `find_indirect_xdata.unresolved_by()` gives.
    """
    out = []
    for row in I.sites(d, pd_verified):
        p2, rn = row["p2"], row["rn"]
        if p2 is None or p2[1] is None or rn is None:
            continue
        addr = (p2[1] << 8) | rn
        if lo <= addr <= hi:
            out.append((addr, INDIRECT, site_label(d, row["offset"], pd_verified),
                        row["xaddr"]))
    return out


def reach_table(d: bytes, lo: int, hi: int, pd_verified: bool):
    """({address: [(method, label, cell), ...]}, {page: [(label, cell)]}).

    One function so the table, the summary and the possible-page list are
    three views of one walk and cannot disagree about the population or about
    which pass reached what.
    """
    reach = collections.defaultdict(list)
    for addr, method, label, cell in (direct_reach(d, lo, hi, pd_verified)
                                      + indirect_reach(d, lo, hi, pd_verified)):
        reach[addr].append((method, label, cell))
    computed, pages = computed_reach(d, lo, hi, pd_verified)
    for addr, label, cell in computed:
        reach[addr].append((COMPUTED, label, cell))
    return reach, pages


def csv_table(reach, pages, possible, counts, lo: int, hi: int) -> str:
    """(the `--csv` table, one row per address in the span) as a string.

    A string rather than a write to stdout, because `--check` diffs the same
    bytes this prints. The columns are the address, its verdict, the site that
    reached it and how, the per-image direct counts so the table can be
    compared with `xdata_span_survey.py` without re-running it, then the two
    findings that are **not** evidence of a reach -- the computed site that
    reaches this address's *page*, and the `addc DPH` residual that leaves it
    *possible*. Evidence first, non-evidence after, so a reader who stops at
    the verdict has read a claim and a reader who reads on finds what would
    have overstated it.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["addr", "verdict", "reach_method", "reach_site", "reach_cell",
                "direct_main_ec", "direct_pd_image", "page_site",
                "page_site_cell", "page_possible"])
    for addr in range(lo, hi + 1):
        sites = reach.get(addr, [])
        page = addr >> 8
        w.writerow([
            f"0x{addr:04X}",
            REACHED if sites else NOT_REACHED,
            ";".join(sorted({method for method, _l, _c in sites})),
            ";".join(sorted({label for _m, label, _c in sites})),
            ";".join(sorted({cell for _m, _l, cell in sites})),
            S.totals(counts[addr], S.MAIN_EC_IMAGES),
            counts[addr][S.PD_IMAGE],
            ";".join(sorted({label for label, _c in pages.get(page, [])})),
            ";".join(sorted({cell for _l, cell in pages.get(page, [])})),
            ";".join(possible.get(page, [])),
        ])
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("firmware",
                    help="raw EC firmware image (e.g. ec/firmware/GMxMGxx_11.800)")
    ap.add_argument("lo", help="first address of the span, e.g. 0x0E00")
    ap.add_argument("hi", help="last address of the span, inclusive, e.g. 0x0EFF")
    ap.add_argument("--csv", action="store_true",
                    help="write one row per address on stdout instead of the summary")
    ap.add_argument("--check", metavar="PATH",
                    help="with --csv, diff this run against a committed table and "
                         "exit non-zero on any difference")
    args = ap.parse_args()

    if args.check is not None and not args.csv:
        ap.error("--check is about the --csv table; without --csv this run "
                 "prints the summary")

    lo, hi = int(args.lo, 16), int(args.hi, 16)
    if lo > hi:
        ap.error("lo must not be above hi")

    d = open(args.firmware, "rb").read()
    off, magic = T.PD_MARKER
    pd_verified = d[off:off + len(magic)] == magic
    if not pd_verified:
        # stderr, so --csv output stays a clean CSV when redirected.
        print(f"note: no {magic.decode()!r} marker at file 0x{off:05X} -- "
              "sites in 0x20000-0x2FFFF will be reported as region 'unknown'\n",
              file=sys.stderr)

    counts = S.survey(d, lo, hi, pd_verified)
    reach, pages = reach_table(d, lo, hi, pd_verified)
    possible = possible_pages(d, lo, hi, pd_verified)

    if args.csv:
        table = csv_table(reach, pages, possible, counts, lo, hi)
        if args.check is not None:
            return T.check_table(table, args.check)
        sys.stdout.write(table)
        return 0

    by_method = collections.Counter(method for sites in reach.values()
                                    for method, _l, _c in sites)
    span = hi - lo + 1
    print(f"0x{lo:04X}-0x{hi:04X}: {span} addresses")
    for method in (DIRECT, WALK, COMPUTED, INDIRECT):
        print(f"  {method:<10} {by_method[method]:>6} address-reach(es)")
    print(f"  {'reached':<10} {len(reach):>6} of {span} address(es)")
    print(f"  {'not reached':<10} {span - len(reach):>6} by this method")

    print(f"\n  every address without a `reached` row below is "
          f"`{NOT_REACHED}`: not\n  found by the passes this tool runs, which is "
          "not the same statement as\n  absent. What each pass cannot see is "
          "named at the end of this run.")

    if reach:
        print("\n  reached addresses, by method:")
        for addr in sorted(reach):
            for method, label, cell in sorted(set(reach[addr])):
                print(f"    0x{addr:04X}  {method:<10} {label:<16} {cell}")

    print("\n  reached *pages*, where no address in the page is named:")
    if not any(pages.values()):
        print("    none")
    for page in sorted(pages):
        for label, cell in sorted(set(pages[page])):
            print(f"    page 0x{page:02X}  {label:<16} {cell}")
    print("    A page reached by a computed DPTR names no address inside it: "
          "the low byte\n    is a run-time value, so crediting the page to its "
          "addresses would claim\n    bytes no site resolved.")

    for page in sorted(possible):
        print(f"\n  page 0x{page:02X} is *possible* for the `addc DPH` residual "
              f"at {', '.join(possible[page])}.\n  A two-element page set is a "
              "page this scan could not rule out, not a reach; it is\n  kept "
              "out of the table above for that reason.")

    print("\n  not reachable by any pass here: an `inc dptr` walk needs a "
          "two-byte seed, so a\n  walk entered with DPTR handed over is not "
          "followed; an `lcall`-supplied\n  accumulator is the refusal "
          "addc_dph_sites.py already names; `movx @Ri` needs both\n  halves "
          "literal; and a pointer held in a register reaches nothing here, "
          "which is\n  the same blind spot on the reading side that a fully "
          "written, fully unread page\n  has on the writing one.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
