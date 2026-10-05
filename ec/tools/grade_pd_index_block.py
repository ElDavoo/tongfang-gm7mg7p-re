#!/usr/bin/env python3
"""Grade a capture of the PD image's `0x260` record block: a per-address table
of what each byte did, not a transcript of when it did it.

The two questions `docs/hardware-tests/pd-index-geometry-live.md` asks of a run
are separable and this reports them separately.

  * **Map separation.** `ec/annotations/pd-xdata-overlap.md` §7 asks whether
    the PD image's XDATA is the same memory the ECMG window reads: read
    `0x04A6`/`0x04A7` while the PD controller is active and see whether the
    reported cycle count is disturbed. The asymmetry is load-bearing and is
    printed here rather than left to the reader of a table: a quiet
    `0x04A6` is **consistent with** separate maps and does not prove them
    separate, because a separate map would leave it undisturbed too. A
    `0x04A6` that moves across a renegotiation **does** prove overlap. One
    direction is evidence and the other is not, and a table that printed both
    the same way would be claiming the second one.
  * **Record contents.** How many distinct values each address took, how many
    times it changed, and when it last changed relative to the mark before it
    -- the nearest thing to a record-contents answer a memory window can give
    (`pd-index-geometry.md` §5 names no record count, because bounding one
    needs the index registers' ranges and §4 resolved none).

Input is one or more CSVs in `ec_watch.py`'s `ts,addr,old,new` format, which
`ec/tools/ec_timer_capture.py` writes on Linux. `#` comment lines are skipped,
except that its `# interval ... addresses:` and `# baseline ...:` lines are read
when present, so an address that never moved is still graded against the value
it held rather than dropped. `MARK` rows are kept apart: they are the
operator's actions, and "when this address last changed relative to the mark
before it" is a claim about them.

**What this reports and what it does not.**

  * Every watched address gets a line, moved or not, with the record slot it
    belongs to and how much of that record this host can reach. That figure is
    what `ec_timer_capture.py` would actually sample -- inside the host window
    and not on the fan page `0x0460`-`0x046F`, which it refuses -- so a line
    saying `592/608 reachable` is a statement about a record no capture
    covered whole, whether or not this particular byte sat in the readable
    part. A byte that held still reads as *not reached on the paths watched,
    over this span* -- never as absent, never as unused.
  * A distinct-value count is what the capture saw at its sampling interval. A
    byte that steps between two values faster than the interval is one value
    here and two on the hardware, so the figure is a floor, and the header
    says so with the interval beside it.
  * Nothing here is a register status, and nothing here reads an index
    register: a memory read observes state, not a register at the moment a
    site runs. The procedure document enumerates what a capture cannot
    conclude rather than leaving this tool to infer it.
  * An address outside the host window reads `0xFF` for the whole run, which is
    indistinguishable from a value that never changes. Such a line is marked
    rather than graded, because a constant `0xFF` there means the host does
    not map the page -- not that the EC holds `0xFF` there.

Offline: it opens no EC and no `/dev/mem`. Every figure below is arithmetic
over capture rows.

Usage:
  grade_pd_index_block.py capture.csv [capture2.csv ...]
  grade_pd_index_block.py idle.csv --active active.csv    diff two states
  grade_pd_index_block.py capture.csv --mark-relative     time each change
                                    against its preceding mark
"""

import argparse
import csv
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# The one spelling of "the same file twice", borrowed from the sibling graders
# rather than copied, so the capture readers in this directory cannot disagree
# about which captures a run has. It is free here for the reason
# `grade_timer_sweep.py` gives: stdlib-only, and it imports no grader, so the
# import cannot cycle.
import grade_0751_isolation as fan

# `RECORD_STRIDE` and the family scope come from the readability tool rather
# than being restated, because the two grade a prediction and a host window
# against the same constant and `pd_index_block_readability.py` is where that
# constant is held to `pd-base-strides.csv`. Two copies of `0x260` in this
# directory would be a second thing for a re-run to move.
import pd_index_block_readability as reach

RECORD_STRIDE = reach.RECORD_STRIDE

# The two addresses `pd-xdata-overlap.md` §7's first runtime step names. They
# are called out by name rather than left in the table because for these the
# reading is one-sided, and the direction is decided by which way they moved:
# the probes below print what the capture supports, not a verdict.
SEPARATION_PROBES = (0x04A6, 0x04A7)

# `slots_of` walks the committed base list, which does not change within a run
# but is walked once per watched address otherwise. Built on first use so
# importing this module -- which the test suite does, and `main` does before it
# knows whether any capture was named -- reads no CSV.
_SLOTS = {}


def _ts(s):
    return datetime.datetime.fromisoformat(s).timestamp()


def load(paths):
    """`(watched, baseline, rows, marks, span, interval)` over every file.

    `utf-8` is declared, the codec the writers of this format put on disk, so
    a capture reads the same here as in the graders that share it. Rows from
    several files are merged into one run and sorted, so a run given an idle
    capture and an active one reports the later bytes as the run's end state.
    """
    watched, baseline, rows, marks = None, {}, [], []
    intervals = []
    first = last = None
    for path in paths:
        with open(path, newline="", encoding="utf-8") as f:
            body = []
            for line in f:
                if line.startswith("#"):
                    m = re.search(r"interval ([0-9.]+)s .* addresses: (.*)$", line)
                    if m:
                        intervals.append(float(m.group(1)))
                        got = [int(x, 16) for x in m.group(2).split()]
                        watched = (watched or []) + [a for a in got
                                                     if a not in (watched or [])]
                    m = re.match(r"# baseline (\S+): (.*)$", line)
                    if m:
                        t = _ts(m.group(1))
                        first = t if first is None else min(first, t)
                        for tok in m.group(2).split():
                            hx, vx = tok.split("=")
                            baseline.setdefault(int(hx, 16), int(vx, 16))
                    m = re.match(r"# ended (\S+)", line)
                    if m:
                        t = _ts(m.group(1))
                        last = t if last is None else max(last, t)
                    continue
                body.append(line)
        for r in csv.reader(body):
            if not r or r[0] == "ts":
                continue
            if r[1] == "MARK":
                marks.append((_ts(r[0]), r[3] if len(r) > 3 else ""))
                continue
            t = _ts(r[0])
            first = t if first is None else min(first, t)
            last = t if last is None else max(last, t)
            rows.append((t, int(r[1], 16), int(r[2], 16), int(r[3], 16)))
    rows.sort()
    marks.sort()
    interval = intervals[0] if intervals else None
    span = (last - first) if first is not None and last is not None else 0.0
    return watched, baseline, rows, marks, span, interval


def slot_index():
    """`{byte: (stride family, slot, base)}` for every byte of every record.

    Inverts `pd_index_block_readability.slot_start` over the committed base
    list, so an address's slot comes from the same base list and the same
    stride the prediction was written against rather than from a second
    reading of the CSV.

    **Only sampleable bytes are placed**, and they come from
    `reachable_addrs` rather than from a length: the list is the definition,
    and a length would place the wrong addresses twice over. A record's tail
    past the window is not in the index, and neither is the fan page
    `0x0460`-`0x046F` a slot-0 record can span -- `ec_timer_capture.py` refuses
    those before it reads anything, so no capture can hold one, and an index
    built by counting would place `0x0470` and onwards at the offset the hole
    displaced them from. An address this host cannot sample is reported as
    unplaced rather than as a byte of a record it cannot see: `unplaced` means
    "in no record this run could name", and the out-of-window line means "in
    one, but not observable here".
    """
    if not _SLOTS:
        for stride, bases in reach.load_strides():
            if stride not in reach.PAGED_STRIDES:
                continue
            for base in bases:
                for slot in range(reach.SLOTS):
                    # The reachable *addresses* per slot, not slot 0's reused
                    # across them. Slot 1 of a `0x60` base starts inside the
                    # window and runs out of it partway, so reusing slot 0's
                    # list would place the record's tail -- addresses this
                    # host does not map at all -- into a record and print them
                    # as sampled bytes of it.
                    for addr in reach.reachable_addrs(base, slot):
                        _SLOTS.setdefault(addr, (stride, slot, base))
    return _SLOTS


def slots_of(addr):
    """`(stride family, slot, base)`, or `(None, None, None)`.

    `None`s for a byte in no record at all. That is a fact about the block and
    it is printed as `unplaced` rather than forced into the nearest record: a
    byte that is not in one would acquire a record by proximity.
    """
    if not _SLOTS:
        slot_index()
    return _SLOTS.get(addr, (None, None, None))


def reachable_note(addr):
    """The parenthesised reach of the record this byte is in, or `''`.

    A record can start inside the window and run out of it -- the window ends
    at `0x07FF` and the next page is `0x0C00` -- so a byte in the first half of
    slot 1 is sampled and one past it is not addressable at all. A slot-0
    record can also span the fan page `0x0460`-`0x046F`, which a capture tool
    refuses rather than reads, so those sixteen bytes are unsampled however far
    into the record they sit. The figure is therefore how many bytes of this
    record a capture can read, and it is short of `RECORD_STRIDE` for either
    reason.

    Silent only when the record is whole. The note fires for every byte of a
    partly-readable record, not only for the ones past the edge, because the
    claim it corrects is made by the whole line: a reader of a `0x04A6` row in
    a slot-0 record needs to know the record was not covered even when that
    byte itself sits well inside what can be read.
    """
    stride, slot, base = slots_of(addr)
    if base is None:
        return ""
    got = reach.reachable_bytes(base, slot)
    return "" if got >= RECORD_STRIDE else f" ({got}/{RECORD_STRIDE} reachable)"


def unmapped(addr):
    """True when this host does not map the page holding `addr`.

    Read from the same `HOST_WINDOW` the capture tool's own guard refuses on,
    so a `0xFF` constant is reported as *not sampled* rather than as a byte
    that held a value. `ec_timer_capture.py --outside-window` can read there
    and get `0xFF` whatever the EC holds; that is what the flag means and it
    is why this line is not graded.
    """
    return not reach.in_window(addr)


def last_values(paths):
    """`{addr: (end value, change count)}` for one set of captures.

    The end value is the last change row's, or the `# baseline` level where an
    address never changed -- which is the value it *held* at the end of the
    span, and is the only one that makes the two captures comparable. Reading
    it as "no value, absent from the diff" would drop the one case the
    comparison exists for: a byte quiet in one state and moved in the other is
    exactly what a map-overlap reading turns on, and it is the byte with no
    change rows in the quiet capture.

    `(None, ...)` is kept for the case where neither a change row nor a
    `# baseline` line states the address, which is what a capture written by
    something other than `ec_timer_capture.py` looks like. That stays `None`
    rather than becoming zero.
    """
    watched, baseline, rows, _, _, _ = load(paths)
    addrs = watched or sorted({r[1] for r in rows})
    out = {}
    for a in addrs:
        ev = [r for r in rows if r[1] == a]
        out[a] = (ev[-1][3] if ev else baseline.get(a), len(ev))
    return out


def mark_relative_refusal(paths):
    """The sentence a `--mark-relative` request over a markless capture is
    refused with, or `None`.

    Asked for, the answer would have to be relative to a mark, and there is
    none: the report's own column is the only thing `--mark-relative` adds, so
    a markless capture would silently grade as though no action had happened.
    That is the reading the procedure exists to prevent -- "nothing moved
    around the plug" and "nothing was timed relative to the plug" are
    different results, and only the second is true here.
    """
    _, _, _, marks, _, _ = load(paths)
    if marks:
        return None
    return ("no MARK rows in " + ", ".join(paths) + ", so there is no mark to "
            "be relative to, and the timing column --mark-relative asks for "
            "would be absent while the rest of the report still graded. That "
            "reads as 'nothing moved around the action' rather than 'nothing "
            "was timed against it'. Re-take the capture with --mark or "
            "--auto-mark, or grade it without --mark-relative, which needs "
            "none.")


def fmt_time(t):
    """A timestamp to milliseconds, so two rows of one table line up.

    `ec_timer_capture.py` writes its rows at millisecond resolution and the
    capture's own `now()` never emits more, so a full `time()` would print six
    digits of zeros on some rows and three on the rest.
    """
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S.%f")[:-3]


def separation_verdict(addr, values, changes, sampled=True):
    """What this capture supports for one of §7's probe addresses, as a whole
    report line -- the address named, then the sentence.

    A function rather than a branch inside the report, because the two
    directions are the whole point of the section and the only way to hold
    them apart is to have each as a value a test can read on its own: a quiet
    byte and a moving byte must never produce interchangeable text. It names
    the address rather than leaving it to the caller so that a line and the
    address it is about cannot come apart.

    `sampled=False` is the address the host does not map. Both probes named in
    `SEPARATION_PROBES` are inside this machine's window, so the report never
    reaches that sentence here -- it is kept because this tool is meant to run
    on a host whose window is not this one, and there the quiet reading would
    otherwise be printed for a byte that was never observed. A `0xFF` constant
    from an unmapped page looks exactly like a byte that held still.
    """
    if not sampled:
        return (f"0x{addr:04X}  outside the host window -- not readable here "
                f"at all, so neither direction is available. A byte this host "
                f"does not map reads 0xFF whatever the EC holds, which is "
                f"indistinguishable from a value that never changes.")
    if not values:
        # Watched but never stated: the capture names the address in its
        # `# interval ... addresses:` header and gives it neither a change row
        # nor a `# baseline` level. `ec_timer_capture.py` always writes that
        # line, so this is a capture from somewhere else -- and saying nothing
        # about the byte is the only honest reading of it. Falling through to
        # the moved branch would print "took 0 distinct values" next to the
        # overlap wording, which is a positive claim built out of no evidence.
        return (f"0x{addr:04X}  watched but no value is stated for it "
                f"anywhere in this capture: no change row and no `# baseline` "
                f"level, so there is nothing to read a movement or a stillness "
                f"from. Neither direction is available from this file.")
    if len(values) == 1:
        return (f"0x{addr:04X}  held 0x{next(iter(values)):02X} over the whole "
                f"capture. This is CONSISTENT WITH the PD image's XDATA being "
                f"a separate map and does not establish it: a separate map "
                f"would leave this byte undisturbed just as a shared one might "
                f"over this span. It rules nothing in and nothing out.")
    return (f"0x{addr:04X}  took {len(values)} distinct value(s) and moved "
            f"{changes} time(s). If any of that movement lines up with a PD "
            f"renegotiation, the two maps OVERLAP and "
            f"pd-xdata-overlap.md's independent-map verdict is wrong. If the "
            f"movement lines up with nothing the capture marked, it is not "
            f"evidence of overlap -- this capture cannot say what wrote it.")


def grade(paths, active=None, mark_relative=False, out=None):
    out = out or sys.stdout
    watched, baseline, rows, marks, span, interval = load(paths)
    addrs = watched or sorted({r[1] for r in rows})
    by = {a: [r for r in rows if r[1] == a] for a in addrs}
    p = lambda *x: print(*x, file=out)

    p(f"capture: {', '.join(paths)}")
    p(f"span {span:.3f}s, {len(rows)} change rows, sample interval "
      f"{interval if interval is not None else 'not recorded'}"
      f"{'s' if interval is not None else ''}, {len(addrs)} addresses watched, "
      f"{len(marks)} mark(s)")
    if interval is not None:
        p(f"  a byte changing faster than {interval * 1000:.1f} ms can step "
          f"past a sample, so the distinct-value counts below are floors over "
          f"this interval rather than the number of values the byte took")
    p("")

    if mark_relative:
        p("last change relative to the preceding mark")
        for t, label in marks:
            after = [a for a in addrs if any(r[0] > t for r in by.get(a, []))]
            p(f"  {fmt_time(t)}  {label}: {len(after)} watched address(es) "
              f"changed after this mark")
            if after:
                shown = " ".join(f"0x{a:04X}" for a in sorted(after)[:16])
                p(f"    {shown}" + (" ..." if len(after) > 16 else ""))
            else:
                p("    nothing in the watched set changed after this mark, over "
                  "the span the capture covers -- which is not the same as "
                  "'nothing changed because of it'")
        p("")

    p("per-address")
    p(f"  {'addr':8}  {'record':10}  {'baseline -> last':17}  "
      f"{'changes':>7}  {'distinct':>8}  last change")
    for a in addrs:
        stride, slot, _ = slots_of(a)
        where = f"{stride}/{slot}" if stride is not None else "unplaced"
        if unmapped(a):
            p(f"  0x{a:04X}  {where:10}  {'-- not sampled --':17}  "
              f"{'--':>7}  {'--':>8}  outside the host window, so this "
              f"address reads 0xFF whatever the EC holds; it was not observed")
            continue
        ev = by.get(a, [])
        v0 = baseline.get(a)
        s0 = f"0x{v0:02X}" if v0 is not None else "?"
        if not ev:
            # The wording is the point, and it is the one
            # `grade_timer_sweep.py` uses: a zero is "not reached by this
            # method", so a quiet byte is not reached on the paths watched
            # over this span -- never absent, never unused, never zero. The
            # span goes before that clause rather than inside it so the clause
            # is the same sentence whichever kind of line it is on, and a
            # reader skimming the table is not reading two grammars.
            p(f"  0x{a:04X}  {where:10}  {f'{s0} (held)':17}  {0:>7}  "
              f"{1:>8}  never, over {span:.1f}s -- not reached on the paths "
              f"watched, over this span{reachable_note(a)}")
            continue
        values = {r[2] for r in ev} | {r[3] for r in ev}
        if v0 is not None:
            values.add(v0)
        last_t, last_v = ev[-1][0], ev[-1][3]
        delta = ""
        if marks:
            prior = [m for m in marks if m[0] < last_t]
            delta = (f"  +{last_t - prior[-1][0]:.3f}s after "
                     f"{fmt_time(prior[-1][0])}" if prior else "  before any mark")
        p(f"  0x{a:04X}  {where:10}  {s0 + ' -> 0x' + format(last_v, '02X'):17}"
          f"  {len(ev):>7}  {len(values):>8}  {fmt_time(last_t)}{delta}"
          f"{reachable_note(a)}")
    p("")

    p("map separation (pd-xdata-overlap.md section 7's first runtime step)")
    for a in SEPARATION_PROBES:
        if a not in addrs:
            p(f"  0x{a:04X}  not in the watched list, so this capture says "
              f"nothing about it")
            continue
        ev = by.get(a, [])
        base_v = baseline.get(a)
        values = {r[2] for r in ev} | {r[3] for r in ev}
        if base_v is not None:
            values.add(base_v)
        p("  " + separation_verdict(a, values, len(ev),
                                    sampled=not unmapped(a)))
    p("")

    if active:
        grade_diff(paths, active, out)

    p("Nothing above is a register status, and nothing above reads an index "
      "register. A memory read observes state; it does not observe a register "
      "at the moment a site runs. An address with no change rows was not "
      "reached on the paths watched over this span, which is not absence.")
    return 0


def grade_diff(idle_paths, active_path, out=None):
    """The idle-against-active comparison, per address.

    Two captures of the same addresses in two PD states, compared on the value
    each held at the end of its own span. That is the comparison
    `pd-xdata-overlap.md` §7 asks for, and it is separated from the per-address
    table because a byte that changed in *both* captures is not a PD finding
    at all -- it moved without the controller doing anything, and printing it
    as though the difference of the two states explained it would be exactly
    the overclaim this tool is shaped against.
    """
    out = out or sys.stdout
    p = lambda *x: print(*x, file=out)
    active_paths = [active_path] if isinstance(active_path, str) else active_path
    idle = last_values(idle_paths)
    active = last_values(active_paths)
    p("idle against active")
    p(f"  idle: {', '.join(idle_paths)}")
    p(f"  active: {', '.join(active_paths)}")
    common = sorted(set(idle) & set(active))
    only = sorted(set(idle) ^ set(active))
    if only:
        p(f"  {len(only)} address(es) appear in one capture and not the other "
          f"and are not compared: "
          + " ".join(f"0x{a:04X}" for a in only[:16])
          + (" ..." if len(only) > 16 else ""))
    sampled = [a for a in common if not unmapped(a)]
    unobserved = [a for a in common if unmapped(a)]
    changed = [a for a in sampled
               if idle[a][0] is not None and active[a][0] is not None
               and idle[a][0] != active[a][0]]
    p(f"  {'addr':8}  {'idle last':>9}  {'active last':>11}  {'idle chg':>8}  "
      f"{'active chg':>10}")
    for a in sampled:
        il, ic = idle[a]
        al, ac = active[a]
        mark = "  <- differs" if a in changed else ""
        p(f"  0x{a:04X}  {f'0x{il:02X}' if il is not None else '?':>9}  "
          f"{f'0x{al:02X}' if al is not None else '?':>11}  {ic:>8}  {ac:>10}"
          f"{mark}")
    if unobserved:
        p(f"  {len(unobserved)} watched address(es) are outside the host "
          f"window and are not compared: "
          + " ".join(f"0x{a:04X}" for a in unobserved[:16])
          + (" ..." if len(unobserved) > 16 else ""))
        p("    both captures would hold 0xFF there whatever the EC does, so a "
          "difference between them would be a fact about the host, not about "
          "the two states")
    p(f"  {len(changed)} of {len(sampled)} sampled address(es) hold a "
      f"different value in the two captures.")
    p("  A difference here is a difference between two states, not an "
      "attribution: this tool cannot say which state caused it, and a byte "
      "that changed in both captures changed for a reason neither state "
      "explains. Only a difference aligned with a mark in the *active* capture "
      "is a candidate for the PD controller, and even then a memory read "
      "cannot rule out that some other writer ran at the same moment.")
    p("")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="ec_timer_capture.py capture(s), and never the same "
                         "file twice -- every file's rows are merged into one "
                         "run, so a file listed twice would double its change "
                         "counts. By resolved path, so ./x.csv and x.csv are "
                         "the same repeat")
    ap.add_argument("--active", metavar="CSV",
                    help="a second capture taken with the PD controller "
                         "active; the idle-against-active diff is printed "
                         "beside the per-address table")
    ap.add_argument("--mark-relative", action="store_true",
                    help="print when each mark was followed by a change in the "
                         "watched set; refused over a capture with no MARK "
                         "rows, which has nothing to be relative to")
    args = ap.parse_args(argv)

    # Before `grade`, so the refusal costs nothing: a repeated path would be
    # merged into itself and every change count in the table doubled, with
    # nothing in the output saying so. `fan.distinct_captures` runs before any
    # file is opened, so this really does read nothing.
    paths, repeats = fan.distinct_captures(args.csv)
    if repeats:
        for given, first, resolved in repeats:
            if given == first:
                print(f"\n{given!r} is given twice, and both times it is "
                      f"{resolved}.", file=sys.stderr)
            else:
                print(f"\n{given!r} and {first!r} are both {resolved}.",
                      file=sys.stderr)
        print("A capture given twice is one capture and not two, so nothing "
              "was read: `load()` merges the rows of every file it is given, "
              "so one file listed twice would have doubled every change row "
              "and every distinct-value count with it, and nothing in the "
              "report would say the figures were of a doubled run. Several "
              "captures is this tool's documented shape, so what is refused is "
              "one file named twice, not a second capture. Name it once.",
              file=sys.stderr)
        return 1
    if args.active:
        # Compared against the captures already kept rather than by running
        # `distinct_captures` over the flag on its own: one path is not a
        # repeat of itself, and the diff that matters is `--active` against
        # the positional list. Keyed on `fan.capture_key` for the same reason
        # that helper exists -- `./x.csv`, `x.csv` and a symlink are one file.
        given = {fan.capture_key(p) for p in paths}
        if fan.capture_key(args.active) in given:
            print(f"\n--active {args.active!r} is one of the captures already "
                  f"given, so the diff would compare a capture with itself: "
                  f"every address would read as unchanged and the section "
                  f"would report no difference that was not a property of the "
                  f"comparison. The two states need two files. Grade the "
                  f"active capture on its own instead.", file=sys.stderr)
            return 1
        active = args.active
    else:
        active = None

    if args.mark_relative:
        # Its own refusal rather than a `ValueError` caught below, because it
        # is the only one of the three that has to read the files to know --
        # whether there are marks in them *is* the question. So it runs after
        # the two that cost nothing, and it pays for that with being the point
        # at which a row `int()` cannot read is reported as a traceback rather
        # than as its own message. The sibling graders validate the row shape
        # and name the field; this one does not, and that is a separate change.
        refusal = mark_relative_refusal(paths)
        if refusal is not None:
            print(f"\n{refusal}", file=sys.stderr)
            return 1

    return grade(paths, active, args.mark_relative)


if __name__ == "__main__":
    sys.exit(main())