#!/usr/bin/env python3
"""Grade a capture of the bank1 0x8001-0x8189 counter sweep: the 0x06D6 period,
and which countdowns ticked at which rate.

Input is one or more CSVs in `ec_watch.py`'s `ts,addr,old,new` format --
`ec/tools/ec_timer_capture.py` writes them on Linux -- with `#` comment lines
skipped, except that `ec_timer_capture.py`'s `# interval ... addresses:` and
`# baseline ...:` lines are read when present, so a byte that never moved is
still graded against the value it held. Several captures are the documented
shape and `load()` merges their rows into one run, so what is refused is the
same file named twice rather than a second capture: a repeat doubles every
change row, which collapses each step interval to 0 and the median step with
it, and `period / step` then divides by that zero. See
docs/findings/grader-repeated-capture.md.

A merged run takes two of its figures from one file apiece, because a capture
states each of them once in its own header: one sample interval for the whole
run, and one starting level per watched address. A file that states neither
contributes nothing -- the run's interval is `not recorded`, and an address
takes the level from whichever file stated it. What is refused is a merge whose
files *disagree*: one interval and one level per address are numbers this
report has to print, and which file each came from is not something it can put
in the sentence. `merged_capture_refusal` builds that one refusal, naming every
disagreement in it at once, and `load()` raises it. A merged run that is graded
at all has its header say where it came from -- the span is the union of the
captures given, with the half about the files (`which none of them covers`)
printed only when no one file's own window is that union, and the interval
clause says how many of them state it. See
docs/findings/grader-merged-capture-sources.md.

What the grading is measured against is the code, and it is re-derivable from
the committed image (`python3 disasm8051.py ../firmware/GMxMGxx_11.800 --at
0x10001 --runtime 0x8001 -n 220`) as well as from
`ec/decompiled/bank1/8001.c`:

  * PRE: 13 countdowns decremented *before* the 0x06D6 test at 0x806C. They
    run on every pass of the routine.
  * 0x06D6: decremented and `ret` at 0x8074 while non-zero; loaded with 9 at
    0x8075 when zero, and the pass continues. Every pass therefore changes
    0x06D6 exactly once, so its step interval *is* the routine's period, and
    a clean capture shows only `-1` steps and `0 -> 9` reloads.
  * POST: 25 countdowns after the return, reached only on the pass that found
    0x06D6 zero -- one pass in ten, so they should step at 10x the routine's
    period. Three of them (0x06D8, 0x085B, 0x06DB) are further gated on
    0x0440 != 0, and 0x06D9 on two predicate calls.
  * 13 + 25 + 0x06D6 = 39, the countdown total in
    `ec/annotations/xdata-06c2-06db-timers.md` section 3; the test holds the
    lists to that.

What this reports and what it does not:

  * Every address in the watched list gets a line, moved or not. A byte that
    held still is reported as held at its value over the span -- "not reached
    on the paths watched, over this span" -- never as absent.
  * An upward step that is not 0x06D6's `0 -> 9` is a reload by some other
    writer. It is counted and printed, not interpreted.
  * A decrement interval is only measured between two consecutive `-1` steps
    of one byte; a byte that stepped once has no interval.
  * No register status comes out of this. A rate is a fact about the capture.
  * A `MARK` row whose label contains "resumed" (what `ec_timer_capture.py
    --auto-mark` writes after a suspend) splits the capture. The mark is
    stamped by a poller, so it can land after the first sample taken on
    resume; the gap is therefore the longest silence in the row stream in the
    second before the mark, not the interval the mark falls in. No step,
    period or decrement interval is measured across a gap. For each such gap the report
    instead says how many 0x06D6 passes the gap holds modulo 10 -- all a
    ten-step counter can say -- against what the awake step would give.

Usage:
  grade_timer_sweep.py capture.csv [capture2.csv ...]
"""
import argparse
import csv
import datetime
import re
import statistics
import sys

# `distinct_captures` is the one spelling of "the same file twice", and it is
# borrowed rather than copied so the three `nargs="+"` capture graders in this
# directory cannot disagree about which captures a run has. It is free here for
# the same reason `grade_gpu_door.py` imports the module: it is stdlib-only, so
# nothing it pulls in is unavailable offline, and it imports no grader, so the
# import cannot cycle. The comment is here so the second copy cannot appear by
# accident -- a copy would be a third rule, and a third rule is the defect this
# refusal exists to close.
import grade_0751_isolation as fan

PRE = [0x06C6, 0x06CD, 0x06D1, 0x06D2, 0x06F3, 0x0635, 0x0636, 0x0637,
       0x0638, 0x0639, 0x063A, 0x0890, 0x07F6]
RELOAD = 0x06D6
POST = [0x06C2, 0x06C3, 0x06D8, 0x06D9, 0x06DA, 0x08E4, 0x055F, 0x09CE,
        0x070B, 0x0706, 0x06C5, 0x085B, 0x0986, 0x070D, 0x07F3, 0x0981,
        0x0982, 0x0811, 0x0809, 0x0843, 0x0844, 0x06DB, 0x080D, 0x08A7,
        0x08A8]
SIDE = [0x0460, 0x0468, 0x0621, 0x0723, 0x080C, 0x0985]
GATE = [0x0440]
RELOAD_VALUE = 9

GROUP = {a: "pre" for a in PRE}
GROUP.update({RELOAD: "reload"})
GROUP.update({a: "post" for a in POST})
GROUP.update({a: "side" for a in SIDE})
GROUP.update({a: "gate" for a in GATE})


def _ts(s):
    return datetime.datetime.fromisoformat(s).timestamp()


RESUMES = []   # timestamps of "resumed" MARK rows, filled by load()
GAPS = []      # (last sample before, first sample after), one per resume
INTERVALS = []  # (path, sample interval) per `# interval` **line** read by
                # load(), so one entry per line: the header's count of files is
                # `len({p for p, _ in INTERVALS})`, never `len(INTERVALS)`.
                # Module state because `grade`'s header has to say how many.
WINDOWS = []   # (path, first, last) per file -- that file's own window, from
                # its own `# baseline`/`# ended` comments and its own first
                # and last row, filled by load() for the same reason. The
                # merged span is the min of the firsts and the max of the
                # lasts, and a file whose own pair *is* that pair covers the
                # whole thing; `span_clause` needs to tell that case from one
                # where no file does, and only the per-file pairs can.


def spans_resume(a, b):
    """True for an interval across a gap, or starting at the first sample after
    one: a change first seen there happened somewhere inside the gap, so its
    timestamp is a bound and not a time."""
    return any((a <= ga and b >= gb) or a == gb for ga, gb in GAPS)


def find_gaps(rows):
    GAPS.clear()
    ts = sorted({r[0] for r in rows})
    for r in RESUMES:
        pairs = [(a, b) for a, b in zip(ts, ts[1:]) if a < r and b <= r + 1.0]
        if pairs:
            GAPS.append(max(pairs, key=lambda ab: ab[1] - ab[0]))


def merged_capture_refusal(nfiles, intervals, levels):
    """The one sentence a merge of captures that disagree is refused with, or
    `None` when they do not.

    `intervals` is `(path, sample interval)` for every file that states one and
    `levels` is `(addr, path, value)` for every `# baseline` entry there is, so
    a file that states neither contributes nothing and two files that state
    different ones are visible to each other. `None` is the whole of an
    accepted merge: one interval for the run whether one file or all of them
    state it, and one level per address that every file stating it gives the
    same value.

    A function rather than a literal at the two places that need it, for
    `bom_refusal`'s reason: `load()` raises this sentence and `main()` prints
    it, and the warning an operator reads and the error the grading raises
    have to be one verdict rather than two that can drift apart.

    **Two shapes reach this sentence, and every clause is true of both.** A
    merge of files that disagree is the one the write-up is about; the other is
    a *single* file whose own `# interval` or `# baseline` line states a figure
    twice at two values. `load()` collects both the same way and refuses them
    the same way -- `intervals` and `levels` are built per entry rather than per
    file, and nothing in the loop below knows how many paths it was handed -- so
    the second shape is not hypothetical. It needs a hand-edited or foreign
    capture, since `ec_timer_capture.py:314` writes its levels from a dict keyed
    by address and states each `# interval` line once; the refusal is new with
    the merge it came in with, so the sentence explaining it is new too, and
    `nfiles` alone says which shape arrived. With one file there is no second
    file, no row merge between two and no other file's rows for a span to
    include, so the four clauses that would otherwise assert a merge that did
    not happen say what is true of a run instead -- `1 capture` rather than
    `1 captures`, a level conflict inside one header rather than across two,
    and a closer for one file rather than for several.

    **It does not say nothing was read, because everything was.** The repeat
    refusal in `main()` says that and it is true there: `fan.distinct_captures`
    runs before any file is opened, so a repeated path really does cost
    nothing. This sentence is reached only once every file has been opened and
    parsed, and reading them all is the only way to know they disagree -- the
    sentence then names what it read. Carried over, `so nothing was read` would
    send an operator looking for an unreadable file rather than for two
    captures taken at different `--interval` values, which is the problem the
    message is meant to name. So it says the run was not built, which is what
    did not happen.

    **The order is stated here and pinned by a test, not discovered by running
    the thing**, which is `docs/findings/0751-file-refusal-order.md`'s finding
    applied one level down: which refusal an operator reads first is part of
    the verdict, and a set or dict iteration order would be a second, silent
    one. Intervals first, then levels by ascending address, and within one
    disagreement the files in the order they were given -- so the values
    within a clause are unsorted on purpose, because an operator looking for
    which of the two files said what is reading them against a command line,
    not against each other. The two levels are independent, so the order costs
    nothing to fix and is the one a reader can predict from this paragraph
    alone.

    Not hoisted into `grade_0751_isolation.py` beside `bom_refusal`, though
    the shape is borrowed from there. No sibling grader reads either header --
    neither `grade_gpu_door.py` nor `grade_0751_isolation.py` parses
    `# interval` or `# baseline` -- so there is no second caller to keep in
    step, and the open question `grader-repeated-capture.md` records under
    "New questions this opens" -- that a third `nargs="+"` capture grader
    reaching into a fourth file for a seven-line helper is a sign the rule
    wants a small shared module of its own -- is about `distinct_captures`
    and its three callers, not about this one.
    """
    def where(paths):
        return " and ".join(repr(p) for p in paths)

    # The four clauses that have to be true of whichever shape arrived, rather
    # than of the merge alone. `nfiles` is the whole of the difference: it is
    # how many paths `load()` was given, so it says whether there is a second
    # file to disagree with at all. The merge halves are the sentences the
    # write-up's measured transcript reproduces, unchanged.
    if nfiles > 1:
        opening = (f"{nfiles} captures disagree about a figure a merged run "
                   f"can only take from one file")
        over_rows = f"over all {nfiles} files"
        over_level = "over a span that includes the other file"
        closing = ("Grade them one at a time, or re-take them so that they "
                   "agree.")
    else:
        # Not "1 captures disagree" and not "the other file": one file holding
        # an address at two values in its own `# baseline` line contradicts
        # itself, there is no second file, and `setdefault` drops the second
        # value just as silently as it drops a second file's -- so the level
        # clause names the capture that would have swallowed the other value
        # rather than a merge that did not happen.
        opening = ("1 capture contradicts itself about a figure a run can only "
                   "take from one file")
        over_rows = "over this run's rows"
        over_level = ("over the whole of that capture, the other value never "
                      "printed")
        closing = ("Grade it on its own, or re-take it so that it states one "
                   "value.")

    claims = []
    said = {}
    for path, value in intervals:
        said.setdefault(value, []).append(path)
    if len(said) > 1:
        claims.append(
            "the sample interval is "
            + " and ".join(f"{v}s in {where(ps)}" for v, ps in said.items())
            + f", and one of them would have been the interval the 'the step "
              f"is not resolved' check judged a median step taken "
              f"{over_rows} against")
    by_addr = {}
    for addr, path, value in levels:
        by_addr.setdefault(addr, {}).setdefault(value, []).append(path)
    for addr in sorted(by_addr):
        held = by_addr[addr]
        if len(held) > 1:
            claims.append(
                f"the `# baseline` level of 0x{addr:04X} is "
                + " and ".join(f"0x{v:02X} in {where(ps)}"
                               for v, ps in held.items())
                + ", and one of them would have been reported as the level it "
                  f"held at, {over_level}")
    if not claims:
        return None
    return (f"{opening}, so no run was built: {'; '.join(claims)}. "
            f"`load()` merges the rows of every file it is given, so there is "
            f"no report of this run that can print both. {closing}")


def span_clause(nfiles):
    """The header's clause about a merged run's span, or `''` for one capture.

    The span of a run built from several files is the min of their firsts and
    the max of their lasts, so it is a union of their windows however those
    windows sit relative to each other. The second half of the clause -- that
    no single file covers that union -- is a claim about the *captures*, not
    about the construction, and it is not true of every merge: two files can
    nest, one taken wholly inside the other's window, and then the outer file
    does cover the whole span on its own. So it is printed only when
    `WINDOWS` says no file's own `[first, last]` is the merged pair, and
    nothing checks it: printing it unconditionally made a merged run whose
    files nest assert something the run's own construction contradicts.

    `WINDOWS` is read rather than a window handed in, for the same reason
    `INTERVALS` is: `load()` is what knows each file's own endpoints, and its
    tuple is this tool's published shape.
    """
    if nfiles < 2:
        return ""
    have = [(lo, hi) for _, lo, hi in WINDOWS if lo is not None and hi is not None]
    if not have:
        return f" (the union of the {nfiles} captures given)"
    first, last = min(lo for lo, _ in have), max(hi for _, hi in have)
    if any((lo, hi) == (first, last) for lo, hi in have):
        return f" (the union of the {nfiles} captures given)"
    return (f" (the union of the {nfiles} captures given, which none of them "
            f"covers)")


def load(paths):
    """Return (watched addrs or None, baseline {addr: v}, rows, span, interval).

    `utf-8` is declared, the codec the writers of this shape put on disk, so
    a capture reads the same here as it does in the grader that shares it.

    Raises `ValueError` -- `merged_capture_refusal`'s sentence, and only that
    -- when the files given disagree about the sample interval or about a
    `# baseline` level, so the interval this returns is a value every file
    stating one agrees on rather than whichever was named last, and the
    baseline is a level no file contradicts.
    """
    watched, baseline, rows = None, {}, []
    RESUMES.clear()
    INTERVALS.clear()
    WINDOWS.clear()
    first = last = None
    levels = []
    for p in paths:
        # This file's own endpoints, kept apart from the run's below: the run's
        # are the min and the max across every file, and a file holding both of
        # those is a file that covers the whole merged window. Same
        # construction either way -- its own `# baseline` and `# ended`
        # comments and its own first and last row.
        own_first = own_last = None
        with open(p, newline="", encoding="utf-8") as f:
            body = []
            for line in f:
                if line.startswith("#"):
                    m = re.search(r"interval ([0-9.]+)s .* addresses: (.*)$", line)
                    if m:
                        INTERVALS.append((p, float(m.group(1))))
                        got = [int(x, 16) for x in m.group(2).split()]
                        watched = (watched or []) + [a for a in got
                                                     if a not in (watched or [])]
                    m = re.match(r"# baseline (\S+): (.*)$", line)
                    if m:
                        t = _ts(m.group(1))
                        first = t if first is None else min(first, t)
                        own_first = t if own_first is None else min(own_first, t)
                        for tok in m.group(2).split():
                            hx, vx = tok.split("=")
                            a, v = int(hx, 16), int(vx, 16)
                            levels.append((a, p, v))
                            baseline.setdefault(a, v)
                    m = re.match(r"# ended (\S+)", line)
                    if m:
                        t = _ts(m.group(1))
                        last = t if last is None else max(last, t)
                        own_last = t if own_last is None else max(own_last, t)
                    continue
                body.append(line)
        for r in csv.reader(body):
            if not r or r[0] == "ts":
                continue
            if r[1] == "MARK":
                if "resumed" in r[3]:
                    RESUMES.append(_ts(r[0]))
                continue
            t = _ts(r[0])
            own_first = t if own_first is None else min(own_first, t)
            own_last = t if own_last is None else max(own_last, t)
            rows.append((t, int(r[1], 16), int(r[2], 16), int(r[3], 16)))
        WINDOWS.append((p, own_first, own_last))
    # Read once, refused once: every file has to be read before the question
    # can be asked, and a run that cannot be graded is refused before any of
    # it is built rather than halfway through the report.
    refusal = merged_capture_refusal(len(paths), INTERVALS, levels)
    if refusal is not None:
        raise ValueError(refusal)
    interval = INTERVALS[0][1] if INTERVALS else None
    rows.sort()
    find_gaps(rows)
    if rows:
        first = rows[0][0] if first is None else min(first, rows[0][0])
        last = rows[-1][0] if last is None else max(last, rows[-1][0])
    span = (last - first) if first is not None and last is not None else 0.0
    return watched, baseline, rows, span, interval


def classify(a, old, new):
    if new == (old - 1) & 0xFF and old != 0:
        return "dec"
    if a == RELOAD and old == 0 and new == RELOAD_VALUE:
        return "reload"
    if new > old:
        return "up"
    return "other"


def fmt_s(x):
    return f"{x:.4f}s" if x < 10 else f"{x:.1f}s"


def grade(paths, out=None):
    out = out or sys.stdout
    watched, baseline, rows, span, interval = load(paths)
    addrs = watched or sorted({r[1] for r in rows})
    by = {a: [r for r in rows if r[1] == a] for a in addrs}
    p = lambda *x: print(*x, file=out)

    p(f"capture: {', '.join(paths)}")
    # Both clauses are about there being more than one file, so with one
    # capture there is nothing to point at and the report is byte for byte the
    # one this grader printed before either clause was written. The span is a
    # union and stays one -- the merged row set has no samples outside it, so
    # "held over the span" below is true as a claim about what was not
    # observed -- and `span_clause` says the half about the files only when no
    # one of them covers the union on its own, which is a question about the
    # captures and not a fixed phrase. The interval, by the time this runs, is
    # a value every file stating one agrees on, so its clause is about
    # provenance rather than about a number that could be wrong.
    union = span_clause(len(paths))
    # Files, not entries: `INTERVALS` holds one entry per `# interval` **line**,
    # and a file may state its interval more than once, so `len(INTERVALS)` is
    # not a count of files and can put the numerator above the denominator --
    # `stated by 3 of 2 files`, on a run built by `cat`ing two captures of one
    # sweep together, in the one sentence whose whole job is saying where a
    # figure came from. A repeat at the *same* value is not a disagreement
    # (`merged_capture_refusal` groups by value, so only a genuine conflict
    # trips its test), so such a run is graded and then the count has to be the
    # unit the denominator already uses.
    stated = (f" (stated by {len({p for p, _ in INTERVALS})} of "
              f"{len(paths)} files)") if len(paths) > 1 else ""
    p(f"span {span:.3f}s{union}, {len(rows)} change rows, sample interval "
      f"{interval if interval is not None else 'not recorded'}"
      f"{'s' if interval is not None else ''}{stated}, {len(addrs)} addresses "
      f"watched")
    p("")

    # 0x06D6, the routine's own clock.
    step = None
    p("0x06D6 (reload and rate control)")
    ev = by.get(RELOAD)
    if ev is None:
        p("  not in the watched list; no period can be read from this capture")
    elif not ev:
        v = baseline.get(RELOAD)
        held = f"0x{v:02X}" if v is not None else "an unrecorded value"
        p(f"  did not move over {span:.1f}s; held at {held}")
        p("  a constant is what a stopped routine gives, and also what a sample "
          "interval that is a multiple of the ten-pass cycle gives (aliasing); a "
          "faster sample tells them apart. Not a statement that it never runs")
    else:
        kinds = {}
        for _, _, o, n in ev:
            k = classify(RELOAD, o, n)
            kinds[k] = kinds.get(k, 0) + 1
        steps = [b[0] - a[0] for a, b in zip(ev, ev[1:])
                 if not spans_resume(a[0], b[0])]
        reloads = [e[0] for e in ev if classify(RELOAD, e[2], e[3]) == "reload"]
        per = [b - a for a, b in zip(reloads, reloads[1:])
               if not spans_resume(a, b)]
        p(f"  {len(ev)} changes: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
        clean = set(kinds) <= {"dec", "reload"}
        p("  every change is a -1 step or the 0 -> 9 reload: "
          + ("yes -- nothing else wrote it at a resolvable moment" if clean
             else "NO -- another writer, or a missed sample; see rows above"))
        if steps:
            step = statistics.median(steps)
            mean = statistics.mean(steps)
            p(f"  step interval (= one pass of 0x8001): median {step * 1000:.1f} ms, "
              f"mean {mean * 1000:.2f} ms, min {min(steps) * 1000:.1f}, "
              f"max {max(steps) * 1000:.1f}")
            if interval is not None and step < 3 * interval:
                p(f"  WARNING: median step is under 3 sample intervals "
                  f"({interval * 1000:.1f} ms); the step is not resolved")
        for ga, gb in GAPS:
            before = [e for e in ev if e[0] <= ga]
            after = [e for e in ev if e[0] >= gb]
            if not (before and after and step):
                continue
            a, b = before[-1], after[0]
            pos = lambda v: (RELOAD_VALUE - v) % 10
            seen = (pos(b[3]) - pos(a[3])) % 10
            gap = b[0] - a[0]
            awake = gap / (mean if steps else step)
            p(f"  across the suspend gap ending {datetime.datetime.fromtimestamp(gb).time()}: "
              f"{gap:.3f}s between samples, 0x{a[3]:02X} before and 0x{b[3]:02X} "
              f"after, so the gap held {seen} (mod 10) passes; the awake "
              f"step would give about {awake:.0f} ({round(awake) % 10} mod 10)"
              + (" -- the same residue, which cannot rule out an uninterrupted "
                 "sweep" if seen == round(awake) % 10 else
                 " -- a different residue: the sweep did not keep its awake "
                 "rate through the whole gap"))
            p("  intervals spanning that gap are excluded from the figures above")
        if per:
            p(f"  reload period over {len(per)} complete cycles: median "
              f"{fmt_s(statistics.median(per))}, mean {fmt_s(statistics.mean(per))}, "
              f"min {fmt_s(min(per))}, max {fmt_s(max(per))}")
            if steps:
                p(f"  period / step = {statistics.median(per) / step:.2f} "
                  f"(the code predicts 10: nine decrements and one reload)")
        elif reloads:
            p("  one reload only; the period is longer than this span allows "
              "measuring -- a bound, not a measurement")
    p("")

    # Every other address, in code order within its group.
    rates = {"pre": [], "post": []}
    for g, lst in (("pre", PRE), ("post", POST), ("side", SIDE), ("gate", GATE)):
        p({"pre": "PRE -- before the 0x06D6 return, predicted one step per pass",
           "post": "POST -- after the return, predicted one step per ten passes",
           "side": "SIDE -- the sweep writes these only as a zero-reach side effect",
           "gate": "GATE -- read by the sweep, never written by it"}[g])
        for a in lst:
            if a not in by:
                p(f"  0x{a:04X}  not sampled")
                continue
            ev = by[a]
            v0 = baseline.get(a)
            s0 = f"0x{v0:02X}" if v0 is not None else "?"
            if not ev:
                p(f"  0x{a:04X}  held at {s0} over {span:.1f}s -- not reached on "
                  f"the paths watched, over this span")
                continue
            kinds = {}
            for _, _, o, n in ev:
                k = classify(a, o, n)
                kinds[k] = kinds.get(k, 0) + 1
            dec_iv = [b[0] - x[0] for x, b in zip(ev, ev[1:])
                      if not spans_resume(x[0], b[0])
                      and classify(a, x[2], x[3]) == "dec"
                      and classify(a, b[2], b[3]) == "dec"]
            line = (f"  0x{a:04X}  {s0} -> 0x{ev[-1][3]:02X}  {len(ev)} changes ("
                    + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())) + ")")
            if dec_iv:
                med = statistics.median(dec_iv)
                line += f"; decrement interval median {med * 1000:.0f} ms over {len(dec_iv)}"
                if g in rates:
                    rates[g].append(med)
            p(line)
        p("")

    p("rate ratio")
    if rates["pre"] and rates["post"]:
        pre, post = statistics.median(rates["pre"]), statistics.median(rates["post"])
        p(f"  POST / PRE decrement interval = {post * 1000:.0f} / {pre * 1000:.0f} ms "
          f"= {post / pre:.2f} (the early return predicts 10)")
    else:
        missing = [g for g in ("pre", "post") if not rates[g]]
        p(f"  not measurable: no byte in {' or '.join(g.upper() for g in missing)} made two "
          f"consecutive -1 steps in this capture")
    if step is not None:
        for g, pred in (("pre", 1), ("post", 10)):
            if rates[g]:
                p(f"  {g.upper()} median / 0x06D6 step = "
                  f"{statistics.median(rates[g]) / step:.2f} (predicted {pred})")
    p("")
    p("Nothing above is a register status. A byte that held still was not "
      "reached on the paths watched over this span, which is not absence.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="+",
                    help="ec_timer_capture.py capture(s), and never the same "
                         "file twice -- every file's rows are merged into one "
                         "run, so a file listed twice doubles them and the "
                         "step interval collapses to zero. By resolved path, "
                         "so ./x.csv and x.csv are the same repeat")
    args = ap.parse_args(argv)

    # Before `grade`, so the refusal costs nothing: with the rows doubled every
    # interval between two of 0x06D6's own steps is 0, the median step prints
    # as 0.0 ms under the "not resolved" warning, and `period / step` then
    # divides by that zero. That is a crash on a command line a fat finger
    # produces, and a crash is not a refusal.
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
              "so one file listed twice would have doubled every change row, "
              "collapsed each interval between two 0x06D6 steps to 0, printed "
              "a median step of 0.0 ms under the 'the step is not resolved' "
              "warning, and then divided by that zero at `period / step` -- a "
              "traceback, not a number. Several captures are this tool's "
              "documented shape, so what is refused is one file named twice, "
              "not a second capture. Name it once.", file=sys.stderr)
        return 1

    # The same shape and the same reason as the refusal above: a merge whose
    # files disagree is refused before `grade()` prints anything, so the cost is
    # stderr and rc 1 rather than a report whose header states one file's
    # sample interval, whose resolution check judged it, and whose per-address
    # levels came from the first file that happened to state them. `ValueError`
    # rather than a class of its own, to match `bom_refusal`; the price is that
    # a capture with a row `int()` cannot read is reported here too, as its own
    # message and the same exit 1 rather than as a traceback. Its sibling
    # graders validate the row shape and name the field; this one does not, and
    # that is a separate change.
    try:
        return grade(paths)
    except ValueError as raised:
        print(f"\n{raised}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
