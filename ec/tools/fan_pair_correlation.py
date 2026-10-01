#!/usr/bin/env python3
"""What the committed captures can and cannot say about 0x075B and 0x075C
(issue #247).

Issue #237 left the two published fan-duty bytes with the name unresolved:
`ECSpec` calls them L and R, `FanInfo.GetEcCpuFanDuty` / `GetEcGpuFanDuty` read
the same two as CPU and GPU, and nothing in the tree decided between the two.
#247 asks which physical fan each byte measures, or for a precise statement of
why the committed inputs cannot say -- and the second answer is the one the
committed inputs give. This tool is the measurement behind that statement, so
each figure in `../../docs/findings/fan-duty-channel-075b-075c.md` is its
output rather than a number typed into prose.

**What it measures, in three parts.**

1. *The paired difference.* `0x075B` and `0x075C` are published together, so
   the comparison is between the two values at one instant: the rows are read
   as a carry-forward step function per address and the two series are paired
   at the timestamps they **share**. Pairing at the union of their timestamps
   instead is the wrong method and is named as such in `deltas()`'s docstring
   -- a capture records changes only, so a timestamp carrying a row for one
   byte and not the other pairs that byte's fresh value against the other's
   carried forward from an earlier pass, inventing differences the hardware
   never published.
2. *Temperature correlation*, each duty byte against `CPU_TEMP` (0x043E) and
   `GPU_TEMP` (0x044F), on the same carry-forward reconstruction. A
   coefficient is printed only when the temperature register's own observed
   range is wide enough to carry one; see `MIN_TEMP_RANGE`.
3. *The tachometer pair*, correlated with each other. Each pair is assembled
   **high byte first**, which is the EC's own order rather than this tool's
   choice: `be16_046c_046d_minus_100` and `be16_0464_0465_minus_100` each
   subtract 100 from the second address and carry the borrow into the first,
   which is only a 16-bit subtract if the second is the low byte. Part 3
   reports the coefficient under **both** orders with their spans beside
   them, because the order moves the figure and a reader should see that
   rather than take it on trust.

**Why the third part is here when the issue asks about two duty bytes.** The
duty bytes cannot be attributed from the committed captures, and the
tachometer evidence is the other end of the same question: `GetEcGpuFanRpm`
reads 1132/1131 (`0x046C`/`0x046B`) as one 16-bit value, while the EC writes
`0x046C` and `0x046D` together in `store_r6_r7_to_046c_046d`. The two
readings of the second tachometer disagree, and that disagreement is about the
vendor's code rather than about which fan is where -- so it is reported as a
lead with its own caveats, and not as a naming.

**What none of this is.** No register was written, no register was read back,
and no laptop, EC or Windows machine was reached. Every figure is arithmetic
over CSV files already in this repository, and a carry-forward reconstruction
is a method with its own blind spot: a capture records only *changes*, so a
byte's value between two rows is inferred rather than observed, and a change
that happened and reverted between two rows leaves no row at all. That is
stated where a number is quoted rather than once here.

**Why it prints rather than asserts.** No threshold is applied to the paired
difference: `deltas()` returns every distinct value it saw with its count, and
a third value is a finding about the data rather than an error to be averaged
away. The refusal that *is* applied is the narrow-range one in part 2, and it
is applied because a Pearson coefficient against a register that moved three
counts across a whole sweep is a number with no reading behind it -- the
failure mode #247 was opened over is a coefficient printed over a signal that
was never there.

Usage:
    python3 fan_pair_correlation.py                    # all three parts
    python3 fan_pair_correlation.py --part duty        # parts 1 and 2 only
    python3 fan_pair_correlation.py --capture <path>   # one capture
    python3 fan_pair_correlation.py --self-test
"""

import argparse
import csv
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.join(HERE, os.pardir, os.pardir)
WATCH = os.path.join(REPO, "evidence", "ec-watch")

# The pair, and the two temperatures. The addresses are the register names in
# `../annotations/registers.yaml` (MAIN_FAN_L_DUTY, MAIN_FAN_R_DUTY, CPU_TEMP,
# GPU_TEMP); nothing here infers one address from the other's position.
DUTY_A, DUTY_B = 0x075B, 0x075C
CPU_TEMP, GPU_TEMP = 0x043E, 0x044F

# The tachometer pairs. The first is the vendor's, and the second is written
# out twice because there are two readings of it and they disagree:
#
#   * as the vendor assembles it -- `GetEcGpuFanRpm` reads 1132 then 1131,
#     each high byte first (`FanInfo.cs`). 1131 is 0x046B, so the pair is
#     neither adjacent nor a range.
#   * as the EC writes it -- `store_r6_r7_to_046c_046d` stores R6 to 0x046C
#     and R7 to 0x046D as one 16-bit value, and `be16_046c_046d_minus_100`
#     subtracts 100 across 0x046D into 0x046C through the borrow
#     (`../annotations/ghidra-functions.csv`).
#
# Which pair to compare is measured rather than assumed: `change_counts()`
# reads the per-address change counts out of the committed sweep summary, and
# a 16-bit tachometer whose high byte churns beside a low byte that moved once
# is not the shape of a tachometer pair. So the tool reports both the vendor's
# assembly (which cannot be built at all -- see below) and the EC's.
#
# **Every tuple is (high, low), and the order is not this tool's to pick.**
# For `TACH_FIRST` the vendor settles it: `GetEcCpuFanRpm` reads 1124
# (0x0464) then 1125 (0x0465) and returns `(num << 8) | b`. For the EC pair
# there is no vendor read at all -- `FanInfo` never reads 0x046D, which has no
# name in any of the three `ECSpec.cs` versions -- so the order there is the
# EC's, read off the borrow chain: `be16_046c_046d_minus_100` does
# `subb A,#0x64` on 0x046D and then `subb A,#0x0` on 0x046C, and a 16-bit
# subtract puts the constant on the low byte and carries into the high one, so
# 0x046D is low and 0x046C is high. That is the pair as written above.
# `be16_0464_0465_minus_100` has the same shape over the first pair.
TACH_FIRST = (0x0464, 0x0465)
TACH_VENDOR_SECOND = (0x046C, 0x046B)
TACH_EC_SECOND = (0x046C, 0x046D)

# The per-address change-count summary. A different shape from a capture --
# `addr,change_count,first_old,last_new` behind three `#` comment lines -- so
# it has its own reader rather than a flag on the other.
SWEEP_SUMMARY = os.path.join(
    "evidence", "ec-watch", "2026-09-18-ac-plugin-sweep-summary.csv")

# The captures, in the order the write-up reads them. The first two are the
# ones issue #247 names; the third is the one that carries a temperature
# register, which is the correction the write-up states beside the claim
# rather than making silently.
PROFILE_0700 = "2026-09-18-profile-switch-0700-07ff.csv"
POWER_0700 = "2026-09-23-power-mode-cycle-0700-07ff.csv"
PROFILE_0400 = "2026-09-18-profile-switch-0400-07ff.csv"
CAPTURES = (PROFILE_0700, POWER_0700, PROFILE_0400)

# A Pearson coefficient is printed only when the temperature register spanned
# at least this many counts across the capture.
#
# The floor is not a significance test and is not derived from one; it is the
# narrowest span at which this tool is willing to characterise a correlation
# as weak rather than as absent, and it is a named constant so a reader can
# see it and disagree with it. GPU_TEMP in `PROFILE_0400` moves 51-53 -- three
# counts across a whole profile sweep -- and a coefficient against it would
# describe the shape of a coincidental handful of samples rather than any
# relationship, which is the failure #247 was opened over. CPU_TEMP spans 33
# and clears it comfortably.
MIN_TEMP_RANGE = 8

# Below this many paired samples a correlation is reported as unsupported
# whatever the range, for the same reason: three points describe a shape
# rather than a relationship, and `pearson()` declines below three anyway.
MIN_SAMPLES = 10

# How far apart two change counts may be and still read as one 16-bit value.
# Calibrated from the settled pair and not from the disputed one -- see
# `_same_order`, which carries the figures.
ORDER_FACTOR = 8


class NotACapture(Exception):
    """A file this tool will not read as a capture, named rather than skipped.

    Raised for a missing header or an unparseable field. The alternative --
    treating it as a capture carrying no rows of that address -- is the
    failure this tool exists to prevent: a file that parses to nothing reads
    exactly like a capture in which the byte never moved, and those two say
    opposite things about the machine.
    """


def read_capture(path):
    """-> [(ts, addr, old, new)] for every data row, in file order.

    The `ts,addr,old,new` shape every reader in `ec/tools/` opens, read here
    with the codec the format declares rather than the interpreter's default
    (`docs/findings/0751-capture-encoding.md`). `old` is kept because it is
    the only record of a byte's value before the capture began: a series
    seeded at its first row's `new` would drop the state that row was a change
    *from*, which is a whole reading of each byte.
    """
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise NotACapture("%s is empty" % path)
        if [f.strip() for f in header[:4]] != ["ts", "addr", "old", "new"]:
            raise NotACapture(
                "%s opens %r, not the ts,addr,old,new capture header"
                % (path, header[:4]))
        for lineno, row in enumerate(reader, start=2):
            if not row or row[0].startswith("#"):
                continue
            if len(row) < 4:
                raise NotACapture(
                    "%s:%d has %d field(s), not 4" % (path, lineno, len(row)))
            try:
                addr = int(row[1], 16)
                old = int(row[2], 16)
                new = int(row[3], 16)
            except ValueError as exc:
                raise NotACapture("%s:%d: %s" % (path, lineno, exc))
            rows.append((row[0], addr, old, new))
    return rows


def preexisting(rows, addr):
    """The value `addr` held before the capture opened, or `None`.

    The `old` of the address's first row, and the only reading of the byte
    from before the first change. It is deliberately **not** a step in
    `series()`: it shares a timestamp with that first row's `new`, so seeding
    a series with it would put two values at one instant and the second would
    silently overwrite the first, leaving a step function that carried a value
    no caller could ever read. Exposed as its own function instead, so a
    caller that wants the pre-capture state has to ask for it.

    This is a weaker thing than a series: it is one value, at one moment the
    capture's author happened to record, and a byte that had not changed
    since boot would return whatever it was then.
    """
    for _, addr_at, old, _ in rows:
        if addr_at == addr:
            return old
    return None


def series(rows, addr):
    """One address as a carry-forward step function: -> [(ts, value)].

    One step per change, at the change's own timestamp, so `value_at` answers
    "what did this byte hold at instant T" for every T the file mentions.
    Two rows for one address at one timestamp collapse to the later `new`: a
    capture that recorded a change and a re-change inside one timestamp string
    has one settled value, and keeping both would make the step function
    non-monotonic in time.

    The value *before* the first change is `preexisting()`, not a step here --
    see its note.

    An address with no row yields `[]`, which every caller reads as "this
    capture does not record that byte" rather than as a value.
    """
    hits = [r for r in rows if r[1] == addr]
    if not hits:
        return []
    steps = {}
    for ts, _, _, new in hits:
        steps[ts] = new
    return sorted(steps.items())


def value_at(steps, ts):
    """The value `steps` holds at `ts`, carrying the last step forward.

    `None` when `ts` precedes every step, which is the one case the carry
    cannot answer: the byte's value then is whatever it held before the
    capture opened, and this reconstruction does not know it. Callers skip
    rather than substitute, because substituting the first observed value
    would invent a reading.
    """
    value = None
    for step_ts, step_value in steps:
        if step_ts > ts:
            break
        value = step_value
    return value


def deltas(rows, a=DUTY_A, b=DUTY_B):
    """-> {delta: count} over the timestamps the two series share.

    **The union of the two timestamps is not the pairing, and this is the one
    method choice that would have produced a different finding.** A capture
    records changes only, and the two bytes change independently, so a
    timestamp carrying a row for one byte and not the other describes a moment
    when that byte's value was fresh and the other was whatever an earlier
    pass last left. Pairing there yields spurious differences of one or two
    counts -- and, on the profile sweep, nine distinct values where the
    shared-timestamp pairing finds two. What is compared is the two bytes'
    values at instants the capture records *both* of, which is the only
    instant at which "these two bytes at once" is something the file
    actually says.

    The addresses are parameters so a caller can measure another pair, and are
    named rather than read from module globals, so a test measuring the
    third-value case runs the same function the committed run does.
    """
    left, right = dict(series(rows, a)), dict(series(rows, b))
    counts = {}
    for ts in sorted(set(left) & set(right)):
        counts[left[ts] - right[ts]] = counts.get(left[ts] - right[ts], 0) + 1
    return counts


def pearson(xs, ys):
    """The Pearson r of two equal-length sequences, or `None` if undefined.

    `None` rather than 0.0 for a constant input: a zero there would be a
    coefficient, and the two cases this tool must not collapse together --
    "these track each other not at all" and "this register never moved" --
    are exactly the ones a zero would confuse.
    """
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    sdx, sdy = statistics.pstdev(xs), statistics.pstdev(ys)
    if sdx == 0 or sdy == 0:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
    return cov / (sdx * sdy)


def temperature_correlation(rows, duty_addr, temp_addr, label):
    """The correlation of one duty byte's series against one temperature's.

    Each temperature step is the anchor: at every instant the capture records
    a new temperature value the duty series is read forward to that instant,
    so each pair is (duty, temperature) coexisting rather than duty at its own
    change against temperature at its own.

    Returns a dict rather than a formatted string so the caller decides how to
    print it and a test can assert on `supported` without matching prose.
    `temp_range` is the temperature register's own observed span and is
    reported even when `r` is `None`: that span is the reason for a refusal,
    and a refusal that does not say why is what this tool must not produce.
    """
    duty = series(rows, duty_addr)
    temp = series(rows, temp_addr)
    result = {
        "label": label,
        "duty": duty_addr,
        "temp": temp_addr,
        "samples": 0,
        "temp_min": None,
        "temp_max": None,
        "temp_range": 0,
        "r": None,
        "supported": False,
        "reason": "",
    }
    if not duty:
        result["reason"] = ("this capture records no row of 0x%04X, so there "
                            "is no series to carry forward" % duty_addr)
        return result
    if not temp:
        result["reason"] = ("this capture records no row of 0x%04X, so there "
                            "is nothing to correlate against"
                            % temp_addr)
        return result

    values = [v for _, v in temp]
    result["temp_min"], result["temp_max"] = min(values), max(values)
    result["temp_range"] = result["temp_max"] - result["temp_min"]

    pairs = [(value_at(duty, ts), tv) for ts, tv in temp]
    pairs = [(d, t) for d, t in pairs if d is not None]
    result["samples"] = len(pairs)

    if result["temp_range"] < MIN_TEMP_RANGE:
        result["reason"] = (
            "%s (0x%04X) moved %d counts across this capture (%d-%d), below "
            "the floor of %d, so a coefficient against it would describe the "
            "shape of a handful of coincidental samples rather than any "
            "relationship"
            % (label, temp_addr, result["temp_range"], result["temp_min"],
               result["temp_max"], MIN_TEMP_RANGE))
        return result
    if len(pairs) < MIN_SAMPLES:
        result["reason"] = ("%d paired sample(s), below the floor of %d"
                            % (len(pairs), MIN_SAMPLES))
        return result

    result["r"] = pearson([d for d, _ in pairs], [t for _, t in pairs])
    if result["r"] is None:
        result["reason"] = ("the duty byte is constant across the paired "
                            "samples, so its coefficient is undefined")
        return result
    result["supported"] = True
    return result


def sixteen_bit(rows, high_addr, low_addr, anchors=None):
    """A 16-bit big-endian value series: -> [(ts, value)], or `[]`.

    `high_addr` is the high byte and `low_addr` the low one, and the order is
    read off the code that uses the pair rather than chosen here. For
    `TACH_FIRST` it is the vendor's own: `FanInfo.GetEcCpuFanRpm` reads 1124
    (0x0464) then 1125 (0x0465) and returns `(num << 8) | b`. For
    `TACH_EC_SECOND` there is **no vendor read of this pair at all** --
    `GetEcGpuFanRpm` reads 1132/1131 = 0x046C/0x046B and never touches
    0x046D, so citing `FanInfo` for its order would be citing a read that
    does not exist. The order there is the EC's, from the borrow chain in
    `be16_046c_046d_minus_100`: `subb A,#0x64` on 0x046D, then `subb A,#0x0`
    on 0x046C. A 16-bit subtract subtracts the constant from the low byte and
    carries the borrow into the high one, so 0x046D is the low byte and
    0x046C the high. That routine is the evidence for this pair's order, and
    it happens to agree with the vendor's order on the first pair.

    Because the order moves the coefficient, `tachometer_comparison` is
    measured both ways round and both are reported -- see `swapped_order`.

    Either half missing yields `[]` rather than a partial value: a 16-bit
    reading assembled from one live byte and one dead one is not a smaller
    measurement, it is a different and wrong one.

    `anchors` is the set of instants to report at. It defaults to the union of
    this pair's own halves' steps, which is the right default for one series
    read on its own, and is **not** right when two series are compared: a
    value assembled at an instant only one of its own halves moved is not
    wrong, but comparing two such series on *their own* step sets measures how
    often each pair's halves happened to move together rather than how the two
    values relate. The caller passes all four bytes' timestamps so every
    sample is one at which all four are live and each is read forward to it.
    On the committed sweep that is the difference between 36 samples and 210,
    and the 36 figure is an artefact of the default rather than a property of
    the data.
    """
    high, low = series(rows, high_addr), series(rows, low_addr)
    if not high or not low:
        return []
    if anchors is None:
        stamps = {t for t, _ in high} | {t for t, _ in low}
    else:
        stamps = set(anchors)
    out = []
    for ts in sorted(stamps):
        hi, lo = value_at(high, ts), value_at(low, ts)
        if hi is None or lo is None:
            continue
        out.append((ts, (hi << 8) | lo))
    return out


def read_change_counts(path):
    """-> {addr: change_count} from a sweep summary.

    A third committed shape, `addr,change_count,first_old,last_new` behind a
    few `#` comment lines, and the only committed record of how often a byte
    moved across a whole `0x0000-0x07FF` sweep. The row log behind it is not
    committed, so this count is not re-derivable from anything else in the
    tree -- which is why it is read rather than recomputed, and why the
    write-up cites it as this file rather than as a figure.

    A header row is recognised by its own text rather than by position, so a
    summary that grows a column does not become a data row.
    """
    counts = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for lineno, row in enumerate(csv.reader(handle), start=1):
            if not row or row[0].startswith("#"):
                continue
            if row[0].strip() == "addr":
                continue
            if len(row) < 2:
                raise NotACapture("%s:%d has %d field(s), not 4"
                                  % (path, lineno, len(row)))
            try:
                counts[int(row[0], 16)] = int(row[1])
            except ValueError as exc:
                raise NotACapture("%s:%d: %s" % (path, lineno, exc))
    if not counts:
        raise NotACapture("%s carries no change count" % path)
    return counts


def swapped_order(rows, second=TACH_EC_SECOND):
    """The same comparison with each pair's two bytes the other way round.

    -> the same dict shape `tachometer_comparison` returns, or `None` when
    that function refused to build the pair at all.

    This is what the byte order is worth. Assembling high-byte-first is the
    EC's order (`sixteen_bit`'s note carries the derivation), but a
    correlation over a 16-bit value is a different number under the other
    order, so quoting the first without the second reports a property of the
    assembly rather than of the capture. Both are printed, with their spans
    beside them: the spans are what decide the matter, because only one of
    the two orders puts the readings in a range a fan could be turning at.
    """
    flipped_first = (TACH_FIRST[1], TACH_FIRST[0])
    flipped_second = (second[1], second[0])
    anchors = set()
    for addr in flipped_first + flipped_second:
        anchors.update(ts for ts, _ in series(rows, addr))
    first = sixteen_bit(rows, *flipped_first, anchors=anchors)
    other = sixteen_bit(rows, *flipped_second, anchors=anchors)
    if not first or not other:
        return None
    left, right = dict(first), dict(other)
    shared = sorted(set(left) & set(right))
    if not shared:
        return None
    return {
        "samples": len(shared),
        "r": pearson([left[ts] for ts in shared],
                     [right[ts] for ts in shared]),
        "first_min": min(left.values()),
        "first_max": max(left.values()),
        "second_min": min(right.values()),
        "second_max": max(right.values()),
    }


def tachometer_comparison(rows, second=TACH_EC_SECOND):
    """Two 16-bit tachometer readings against each other, and their shape.

    -> a dict with the shared sample count, the correlation, how many samples
    the two agreed on exactly, and each reading's own span. The agreement
    count is beside the correlation deliberately: a correlation near 1.0 is a
    statement about the *shape* of two series, and two series can have that
    shape while agreeing on a value rarely -- so neither figure alone says
    what is being read here, and the pair is printed rather than the verdict.

    `second` is the address pair under test and defaults to the EC's
    (`0x046C`/`0x046D`); a caller passes `TACH_VENDOR_SECOND` to ask what the
    service's own read produces, which on the committed captures is nothing,
    because `0x046B` never moves.

    Both series are assembled at the union of all four bytes' timestamps, so
    every sample is one at which all four are live. See `sixteen_bit`'s note
    on `anchors` for what the alternative would have measured.
    """
    anchors = set()
    for addr in TACH_FIRST + second:
        anchors.update(ts for ts, _ in series(rows, addr))
    first = sixteen_bit(rows, *TACH_FIRST, anchors=anchors)
    other = sixteen_bit(rows, *second, anchors=anchors)
    result = {
        "second": second,
        "samples": 0,
        "r": None,
        "identical": 0,
        "first_span": 0,
        "second_span": 0,
        "first_min": 0,
        "first_max": 0,
        "second_min": 0,
        "second_max": 0,
        "swapped": None,
        "reason": "",
    }
    if not first or not other:
        missing = second if not other else TACH_FIRST
        present = missing[0] if any(r[1] == missing[0] for r in rows) else None
        if present is None:
            result["reason"] = ("this capture records no row of 0x%04X, so "
                                "the 16-bit pair cannot be assembled"
                                % missing[0])
        else:
            result["reason"] = ("0x%04X is recorded but 0x%04X is not, so the "
                                "pair has one live byte and one dead one and "
                                "assembling it would be a measurement of "
                                "neither" % (present, missing[1]))
        return result

    left, right = dict(first), dict(other)
    shared = sorted(set(left) & set(right))
    result["samples"] = len(shared)
    if not shared:
        result["reason"] = "the two readings share no timestamp"
        return result
    result["first_span"] = max(left.values()) - min(left.values())
    result["second_span"] = max(right.values()) - min(right.values())
    result["first_min"], result["first_max"] = (min(left.values()),
                                                max(left.values()))
    result["second_min"], result["second_max"] = (min(right.values()),
                                                  max(right.values()))
    result["identical"] = sum(1 for ts in shared if left[ts] == right[ts])
    result["r"] = pearson([left[ts] for ts in shared],
                          [right[ts] for ts in shared])
    result["swapped"] = swapped_order(rows, second)
    if result["r"] is None:
        result["reason"] = ("one of the two readings is constant across the "
                            "shared samples, so the correlation is undefined")
    return result


def tachometer_pair_shape(counts):
    """Which of the two readings of the second tachometer looks like a pair.

    -> a dict naming the reading whose two bytes change at rates of the same
    order, and the counts each reading's two bytes took. A 16-bit value from a
    spinning fan has a high byte that moves on the low byte's carry, so the
    two change counts are the same order of magnitude; a reading whose high
    byte churns beside a low byte that moved once is a byte that is not the
    low half of what its partner is.

    This is a shape test, not a decoding: it says which pair of addresses
    behaves as a unit, and it cannot say what the unit measures. Both readings
    are reported either way, so a summary where neither matches leaves the
    reader with two counts rather than a conclusion.
    """
    out = {"shape": None, "counts": {}, "reason": ""}
    readings = (("vendor", TACH_VENDOR_SECOND), ("ec", TACH_EC_SECOND))
    for label, (high, low) in readings:
        if high not in counts or low not in counts:
            out["reason"] = ("the summary carries no count for 0x%04X or "
                             "0x%04X, so this reading cannot be assessed"
                             % (high, low))
            out["counts"][label] = None
            continue
        out["counts"][label] = (counts[high], counts[low])
    if out["counts"].get("vendor") and out["counts"].get("ec"):
        vendor_hi, vendor_lo = out["counts"]["vendor"]
        ec_hi, ec_lo = out["counts"]["ec"]
        out["shape"] = ("vendor" if _same_order(vendor_hi, vendor_lo)
                        else "ec" if _same_order(ec_hi, ec_lo) else None)
        if out["shape"] is None:
            out["reason"] = ("neither reading's two bytes change at rates of "
                             "the same order, so this test picks neither")
    return out


def _same_order(high, low):
    """True when two change counts are within `ORDER_FACTOR` of each other.

    A factor rather than an equality, because the ratio a real 16-bit counter
    produces depends on how fast the value moves: a fast-changing low byte
    carries its high byte often, a nearly-steady one rarely.

    `ORDER_FACTOR` is calibrated from the one pair the EC's own code settles,
    which is the only honest way to set it here. `0x0464`/`0x0465` is written
    as one 16-bit value by `gate_06e6_then_store_0464` and read back through
    the borrow chain in `be16_0464_0465_minus_100`, and across the committed
    sweep its two bytes changed **126 and 540** times -- a ratio of 4.3. A
    factor of 4 would therefore have excluded a pair that is not in dispute,
    which is the failure mode that makes a shape test worse than none: it
    would have reported the doubt this tool exists to raise against the
    reading the EC's code supports. 8 clears that case with room to spare and
    still excludes the shape it is here to catch, where a byte that moved
    **once** sits beside one that moved 154.
    """
    if high == 0 and low == 0:
        return False
    bigger, smaller = max(high, low), min(high, low)
    if smaller == 0:
        return False
    return bigger <= smaller * ORDER_FACTOR


def duty_span(rows, addr=DUTY_A):
    """(min, max) over a whole series, or `(None, None)` with no rows."""
    values = [v for _, v in series(rows, addr)]
    if not values:
        return (None, None)
    return (min(values), max(values))


def _fmt_span(span):
    return "0x%02X-0x%02X" % span if span[0] is not None else "not recorded"


def report_capture(path):
    """The three parts for one capture, as the dict the printers consume.

    Both readings of the second tachometer are measured, not just the one the
    tool believes: `vendor_tach` is what the service's own read assembles and
    `ec_tach` is what the EC writes. Printing only the survivable one would
    make this look like a measurement of the vendor's code when it is a
    measurement of the EC's.
    """
    rows = read_capture(path)
    name = os.path.basename(path)
    deltas_by_file = deltas(rows)
    temps = []
    for addr, label in ((CPU_TEMP, "CPU_TEMP"), (GPU_TEMP, "GPU_TEMP")):
        for duty_addr in (DUTY_A, DUTY_B):
            temps.append(temperature_correlation(rows, duty_addr, addr, label))
    return {
        "name": name,
        "path": path,
        "rows": len(rows),
        "timestamps": len({ts for ts, _, _, _ in rows}),
        "deltas": deltas_by_file,
        "delta_samples": sum(deltas_by_file.values()),
        "span_a": duty_span(rows, DUTY_A),
        "span_b": duty_span(rows, DUTY_B),
        "temperatures": temps,
        "vendor_tach": tachometer_comparison(rows, TACH_VENDOR_SECOND),
        "ec_tach": tachometer_comparison(rows, TACH_EC_SECOND),
    }


def print_report(reports, part="all", shape_report=None):
    out = sys.stdout.write
    out("fan_pair_correlation: 0x%04X and 0x%04X over the committed captures\n\n"
        % (DUTY_A, DUTY_B))
    out("Every figure below is arithmetic over a CSV in evidence/ec-watch/. No\n"
        "register was read back and no machine was reached.\n")

    if part in ("all", "duty"):
        out("\n1. The paired difference, at the timestamps both bytes share\n")
        for rep in reports:
            out("  %s  (%d rows over %d timestamps)\n"
                % (rep["name"], rep["rows"], rep["timestamps"]))
            if not rep["deltas"]:
                out("    neither byte recorded\n")
                continue
            for value in sorted(rep["deltas"]):
                out("    0x%04X - 0x%04X = 0x%02X  in %d of %d paired "
                    "samples\n"
                    % (DUTY_A, DUTY_B, value, rep["deltas"][value],
                       rep["delta_samples"]))
            out("    0x%04X spans %s, 0x%04X spans %s\n"
                % (DUTY_A, _fmt_span(rep["span_a"]), DUTY_B,
                   _fmt_span(rep["span_b"])))
        out("\n  No threshold is applied to this. A value here that is neither\n"
            "  0x00 nor 0x14 is a fact about the capture, and the tool prints it\n"
            "  as one.\n")

        out("\n2. Each duty byte against each temperature\n")
        for rep in reports:
            out("  %s\n" % rep["name"])
            for entry in rep["temperatures"]:
                head = ("    0x%04X vs %s" % (entry["duty"], entry["label"]))
                if not entry["supported"]:
                    out("  %s -- no coefficient: %s\n" % (head, entry["reason"]))
                    continue
                out("  %s  r = %+.3f over %d paired samples "
                    "(%s spans %d counts, %d-%d)\n"
                    % (head, entry["r"], entry["samples"], entry["label"],
                       entry["temp_range"], entry["temp_min"],
                       entry["temp_max"]))

    if part in ("all", "tach"):
        out("\n3. The tachometer pairs, both readings of the second one\n")
        for rep in reports:
            out("  %s\n" % rep["name"])
            for key, label in (("vendor_tach", "as the service reads it"),
                               ("ec_tach", "as the EC writes it")):
                tach = rep[key]
                pair = tach["second"]
                if not tach["samples"] and tach["reason"]:
                    out("    0x%04X/0x%04X, %s: %s\n"
                        % (pair[0], pair[1], label, tach["reason"]))
                    continue
                out("    0x%04X/0x%04X against 0x%04X/0x%04X, %s: "
                    "%d shared samples\n"
                    % (TACH_FIRST[0], TACH_FIRST[1], pair[0], pair[1], label,
                       tach["samples"]))
                if tach["r"] is not None:
                    out("      r = %+.3f, identical in %d of %d, spans %d and "
                        "%d counts\n"
                        % (tach["r"], tach["identical"], tach["samples"],
                           tach["first_span"], tach["second_span"]))
                    out("      high byte first: %d-%d and %d-%d\n"
                        % (tach["first_min"], tach["first_max"],
                           tach["second_min"], tach["second_max"]))
                    sw = tach["swapped"]
                    if sw is not None:
                        out("      the other byte order: r = %s over %d "
                            "samples, %d-%d and %d-%d\n"
                            % ("undefined" if sw["r"] is None
                               else "%+.3f" % sw["r"], sw["samples"],
                               sw["first_min"], sw["first_max"],
                               sw["second_min"], sw["second_max"]))
                else:
                    out("      no coefficient: %s\n" % tach["reason"])
        out("\n  Two series tracking each other is a fact about the capture,\n"
            "  not about two fans. A carry-forward reconstruction is a method\n"
            "  with a named blind spot -- a capture records changes only, so a\n"
            "  value between two rows is inferred -- and a high correlation is\n"
            "  a statement about the shape of two series rather than about\n"
            "  what is spinning.\n")
        out("\n  The byte order is named rather than assumed, and both orders\n"
            "  are printed above. High byte first is the EC's own: the\n"
            "  be16_* routines subtract 100 from the second address and carry\n"
            "  the borrow into the first, which is a 16-bit subtract only if\n"
            "  the second is the low byte. It is also the only one of the two\n"
            "  orders whose readings land in a range a fan could turn at, and\n"
            "  that range is the evidence for the order rather than a\n"
            "  consequence of it.\n")

        shape = shape_report
        if shape is not None:
            out("\n  Change counts across a whole 0x0000-0x07FF sweep, from\n"
                "  %s\n" % SWEEP_SUMMARY)
            for label in ("vendor", "ec"):
                pair = TACH_VENDOR_SECOND if label == "vendor" else TACH_EC_SECOND
                counts = shape["counts"].get(label)
                if counts is None:
                    out("    0x%04X/0x%04X: %s\n"
                        % (pair[0], pair[1], shape["reason"]))
                    continue
                out("    0x%04X/0x%04X changed %d and %d times\n"
                    % (pair[0], pair[1], counts[0], counts[1]))
            if shape["shape"] == "ec":
                out("    The two bytes whose change counts are the same order\n"
                    "    of magnitude are 0x%04X/0x%04X, which is the pair\n"
                    "    the EC writes together in store_r6_r7_to_046c_046d.\n"
                    % TACH_EC_SECOND)
            elif shape["shape"] == "vendor":
                out("    The pair whose change counts agree is the service's\n"
                    "    own: 0x%04X/0x%04X.\n" % TACH_VENDOR_SECOND)
            else:
                out("    %s\n" % (shape["reason"] or
                                  "neither reading's shape is conclusive"))


# --- self-test --------------------------------------------------------------

def _capture(tmp, name, rows):
    path = os.path.join(tmp, name)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ts", "addr", "old", "new"])
        for row in rows:
            writer.writerow([row[0], "0x%04X" % row[1], "0x%02X" % row[2],
                             "0x%02X" % row[3]])
    return path


def self_test():
    """The tool's own known answers, over captures written here.

    `--self-test` is what the ghidra tooling gate runs, so this is the half
    that keeps the tool's own refusals from being untested claims. It writes
    captures into a temp directory and never into `evidence/ec-watch/`:
    `check_capture_encoding` walks that directory as a committed corpus, so a
    fixture committed beside the real ones would turn its own case red.
    """
    import tempfile

    problems = []
    check = problems.append

    with tempfile.TemporaryDirectory() as tmp:
        # A capture whose only shared-timestamp difference is 0x14, and one
        # whose difference is 0x00: the two values the committed captures take.
        only_14 = _capture(tmp, "only14.csv", [
            ("t1", DUTY_A, 0x40, 0x50),
            ("t1", DUTY_B, 0x30, 0x3C),
        ])
        only_00 = _capture(tmp, "only00.csv", [
            ("t1", DUTY_A, 0x40, 0x50),
            ("t1", DUTY_B, 0x40, 0x50),
        ])
        # The third value: a difference no committed capture takes. It must
        # come back as itself, not be folded into the two above.
        third = _capture(tmp, "third.csv", [
            ("t1", DUTY_A, 0x40, 0x50),
            ("t1", DUTY_B, 0x40, 0x43),
        ])

        if deltas(read_capture(only_14)) != {0x14: 1}:
            check("a capture whose difference is 0x14 gave %r"
                  % deltas(read_capture(only_14)))
        if deltas(read_capture(only_00)) != {0: 1}:
            check("a capture whose difference is 0x00 gave %r"
                  % deltas(read_capture(only_00)))
        if deltas(read_capture(third)) != {0x0D: 1}:
            check("a capture taking a third difference did not report it: %r"
                  % deltas(read_capture(third)))

        # An address absent from a capture is `[]`, not a value, and a
        # temperature that never appears is a stated refusal.
        bare = _capture(tmp, "bare.csv", [
            ("t1", DUTY_A, 0x40, 0x50),
            ("t1", DUTY_B, 0x40, 0x3C),
        ])
        report = temperature_correlation(read_capture(bare), DUTY_A, CPU_TEMP,
                                         "CPU_TEMP")
        if report["supported"] or "no row of 0x043E" not in report["reason"]:
            check("a capture with no CPU_TEMP row did not refuse by name: %r"
                  % report)

        # A duty byte missing entirely: no series to carry forward.
        no_duty = _capture(tmp, "noduty.csv", [("t1", DUTY_B, 0x40, 0x50)])
        report = temperature_correlation(read_capture(no_duty), DUTY_A, CPU_TEMP,
                                         "CPU_TEMP")
        if report["supported"] or "no row of 0x075B" not in report["reason"]:
            check("a capture with no duty row did not refuse by name: %r"
                  % report)

        # The narrow-range refusal: a temperature that moves two counts cannot
        # yield a coefficient, however many samples carry it.
        narrow = [("t%d" % i, CPU_TEMP, 0x40 + (i % 2), 0x41 + (i % 2))
                  for i in range(40)]
        narrow += [("t%d" % i, DUTY_A, 0x10, 0x10 + (i % 5)) for i in range(40)]
        narrow_path = _capture(tmp, "narrow.csv", narrow)
        report = temperature_correlation(read_capture(narrow_path), DUTY_A,
                                         CPU_TEMP, "CPU_TEMP")
        if report["supported"] or report["r"] is not None:
            check("a temperature spanning 1 count produced a coefficient: %r"
                  % report)
        if "below the floor of %d" % MIN_TEMP_RANGE not in report["reason"]:
            check("the narrow-range refusal did not name the floor: %r"
                  % report["reason"])
        # That refusal is the one this fixture above produced, and it is
        # CPU_TEMP: a reason naming any other register would be a true
        # sentence about the wrong byte, which is worse than no reason.
        if "0x%04X" % CPU_TEMP not in report["reason"]:
            check("the narrow-range refusal named the wrong register: %r"
                  % report["reason"])

        # A wide, well-populated temperature does produce a coefficient, so
        # the refusal above is the floor and not a refusal of everything.
        wide = [("s%d" % i, CPU_TEMP, 0x30, 0x30 + i) for i in range(40)]
        wide += [("s%d" % i, DUTY_A, 0x10, 0x10 + i) for i in range(40)]
        wide_path = _capture(tmp, "wide.csv", wide)
        report = temperature_correlation(read_capture(wide_path), DUTY_A,
                                         CPU_TEMP, "CPU_TEMP")
        if not report["supported"] or report["r"] is None:
            check("a wide, well-populated temperature was refused: %r" % report)

        # A 16-bit pair with one half missing is refused rather than assembled
        # from a live byte and a dead one.
        half = _capture(tmp, "half.csv", [
            ("t1", TACH_EC_SECOND[0], 0x10, 0x20),
        ])
        result = tachometer_comparison(read_capture(half))
        if result["samples"]:
            check("a half-present tachometer pair assembled a value")
        if "one live byte and one dead one" not in result["reason"]:
            check("the half-present refusal did not say why: %r"
                  % result["reason"])

        # Both readings are measured, so a caller cannot ask for the survivable
        # one and get a measurement of the vendor's code instead.
        both = _capture(tmp, "bothtach.csv", [
            ("t1", TACH_FIRST[0], 0x10, 0x11),
            ("t1", TACH_FIRST[1], 0x20, 0x21),
            ("t1", TACH_EC_SECOND[0], 0x10, 0x11),
            ("t1", TACH_EC_SECOND[1], 0x20, 0x21),
        ])
        ec_result = tachometer_comparison(read_capture(both), TACH_EC_SECOND)
        vendor_result = tachometer_comparison(read_capture(both),
                                              TACH_VENDOR_SECOND)
        if not ec_result["samples"]:
            check("a complete EC tachometer pair produced no sample")
        if vendor_result["samples"]:
            check("the service's own pair assembled a value with no 0x046B")

        # The anchors argument: two series compared on their own step sets
        # lose every sample where the *other* pair moved, which is a
        # measurement of co-movement rather than of the two values.
        staggered = [("u%d" % i, TACH_FIRST[0], 0x10, 0x10) for i in range(3)]
        staggered += [("v%d" % i, TACH_FIRST[1], 0x20, 0x21)
                      for i in range(3)]
        staggered += [("w%d" % i, TACH_EC_SECOND[0], 0x30, 0x31)
                      for i in range(3)]
        staggered += [("x%d" % i, TACH_EC_SECOND[1], 0x40, 0x41)
                      for i in range(3)]
        staggered_path = _capture(tmp, "staggered.csv", staggered)
        own = tachometer_comparison(read_capture(staggered_path),
                                    TACH_EC_SECOND)
        if not own["samples"]:
            check("an interleaved tachometer comparison found no sample")

        # The pair-shape test: the counts decide which reading looks like one
        # 16-bit value, and both readings are reported either way.
        shape = tachometer_pair_shape({0x046C: 154, 0x046B: 1, 0x046D: 536})
        if shape["shape"] != "ec":
            check("154/1 against 154/536 did not pick the EC's pair: %r"
                  % shape)
        shape = tachometer_pair_shape({0x046C: 154, 0x046B: 140, 0x046D: 536})
        if shape["shape"] != "vendor":
            check("a summary agreeing on both readings picked neither: %r"
                  % shape)
        shape = tachometer_pair_shape({0x046C: 154, 0x046D: 536})
        if shape["shape"] is not None or "cannot be assessed" not in shape["reason"]:
            check("a summary missing a byte still produced a verdict: %r"
                  % shape)

        # The bound is calibrated from the pair the EC's own code settles, and
        # held from that side too. `0x0464`/`0x0465` is written as one 16-bit
        # value by `gate_06e6_then_store_0464` and its two bytes changed 126
        # and 540 times across the committed sweep; a factor of 4 would have
        # excluded a pair nobody disputes, which is how a shape test becomes
        # worse than none. This case is what stops the factor being tightened
        # back to 4.
        if not _same_order(126, 540):
            check("the settled 0x0464/0x0465 pair (126 against 540 changes) "
                  "does not satisfy the bound ORDER_FACTOR=%d, so the bound "
                  "would exclude a pair the EC's own code supports"
                  % ORDER_FACTOR)
        if _same_order(154, 1):
            check("a byte that moved once beside one that moved 154 "
                  "satisfies the bound, so the test cannot catch the shape")

        # A change-count file is read behind its `#` header lines, and a
        # header row is recognised by its text rather than by position.
        summary = os.path.join(tmp, "summary.csv")
        with open(summary, "w", newline="", encoding="utf-8") as handle:
            handle.write("# derived from a sweep\n# second comment\n")
            handle.write("addr,change_count,first_old,last_new\n")
            handle.write("0x046C,154,0x08,0x13\n")
            handle.write("0x046D,536,0x27,0x03\n")
        counts = read_change_counts(summary)
        if counts != {0x046C: 154, 0x046D: 536}:
            check("the change-count reader returned %r" % counts)

        # A file that is not a capture is refused by name.
        broken = os.path.join(tmp, "broken.csv")
        with open(broken, "w", encoding="utf-8") as handle:
            handle.write("a,b,c\n1,2,3\n")
        try:
            read_capture(broken)
            check("a file with the wrong header was read as a capture")
        except NotACapture as exc:
            if "capture header" not in str(exc):
                check("the wrong-header refusal did not say why: %s" % exc)

    if problems:
        for problem in problems:
            print("fan_pair_correlation.py: %s" % problem, file=sys.stderr)
        print("%d self-test failure(s)" % len(problems), file=sys.stderr)
        return 1
    print("self-test passed: the paired difference reports a third value "
          "rather than averaging it, a missing address is a stated refusal "
          "rather than a value, and a temperature too narrow to correlate "
          "against yields no coefficient.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture", action="append", metavar="PATH",
                        help="a capture to measure (default: the three "
                             "committed ones this tool is about)")
    parser.add_argument("--part", choices=("all", "duty", "tach"),
                        default="all", help="which parts to print")
    parser.add_argument("--self-test", action="store_true",
                        help="run the known answers over captures written to "
                             "a temp directory and check them")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    paths = args.capture or [os.path.join(WATCH, name) for name in CAPTURES]
    try:
        reports = [report_capture(path) for path in paths]
        shape = None
        if args.part in ("all", "tach"):
            summary = os.path.join(REPO, SWEEP_SUMMARY)
            try:
                shape = tachometer_pair_shape(read_change_counts(summary))
            except (NotACapture, OSError) as exc:
                # A missing summary costs the shape test and nothing else, so
                # it is reported on stderr and the rest of the run stands.
                print("fan_pair_correlation.py: %s not read (%s); the capture "
                      "figures below do not depend on it"
                      % (SWEEP_SUMMARY, exc), file=sys.stderr)
    except (NotACapture, OSError) as exc:
        print("fan_pair_correlation.py: %s" % exc, file=sys.stderr)
        return 1
    print_report(reports, part=args.part, shape_report=shape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
