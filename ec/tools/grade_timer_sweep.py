#!/usr/bin/env python3
"""Grade a capture of the bank1 0x8001-0x8189 counter sweep: the 0x06D6 period,
and which countdowns ticked at which rate.

Input is one or more CSVs in `ec_watch.py`'s `ts,addr,old,new` format --
`ec/tools/ec_timer_capture.py` writes them on Linux -- with `#` comment lines
skipped, except that `ec_timer_capture.py`'s `# interval ... addresses:` and
`# baseline ...:` lines are read when present, so a byte that never moved is
still graded against the value it held.

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


def load(paths):
    """Return (watched addrs or None, baseline {addr: v}, rows, span, interval).

    `utf-8` is declared, the codec the writers of this shape put on disk, so
    a capture reads the same here as it does in the grader that shares it.
    """
    watched, baseline, rows = None, {}, []
    RESUMES.clear()
    first = last = None
    interval = None
    for p in paths:
        with open(p, newline="", encoding="utf-8") as f:
            body = []
            for line in f:
                if line.startswith("#"):
                    m = re.search(r"interval ([0-9.]+)s .* addresses: (.*)$", line)
                    if m:
                        interval = float(m.group(1))
                        got = [int(x, 16) for x in m.group(2).split()]
                        watched = (watched or []) + [a for a in got
                                                     if a not in (watched or [])]
                    m = re.match(r"# baseline (\S+): (.*)$", line)
                    if m:
                        t = _ts(m.group(1))
                        first = t if first is None else min(first, t)
                        for tok in m.group(2).split():
                            a, v = tok.split("=")
                            baseline.setdefault(int(a, 16), int(v, 16))
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
                if "resumed" in r[3]:
                    RESUMES.append(_ts(r[0]))
                continue
            rows.append((_ts(r[0]), int(r[1], 16), int(r[2], 16), int(r[3], 16)))
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
    p(f"span {span:.3f}s, {len(rows)} change rows, sample interval "
      f"{interval if interval is not None else 'not recorded'}"
      f"{'s' if interval is not None else ''}, {len(addrs)} addresses watched")
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
    ap.add_argument("csv", nargs="+")
    args = ap.parse_args(argv)
    return grade(args.csv)


if __name__ == "__main__":
    sys.exit(main())
