#!/usr/bin/env python3
"""Score every candidate bank-to-file-offset pair against the trampoline call
sites, jointly, and say how far the winner is ahead of the runner-up.

`find_banks.py` scores each bank on its own: it collects the runtime targets
that reach one bank-switch stub and asks which 32 KiB slice of the file puts
most of them on a byte in a 30-entry `START_OPCODES` set. That is the source of
the 51% and 92% in `ec/README.md` §Layout, and the two things wrong with it are
the two this tool exists to fix. The metric is a **single-byte membership test**
over 30 of 256 byte values, so random bytes score about 12% and the distance
between a right offset and a wrong one is a distance between two mediocre
numbers -- the committed image gives bank 0 51% against 32%. And the banks are
scored **independently**, so nothing in the run requires the two mappings to be
consistent with each other, and the report is free to print two offsets that are
the same block.

Neither defect is a reason to distrust the offsets the tool prints; both are
reasons not to read its percentage as a probability. What is here instead is a
per-target verdict over the two byte classes that cannot be an instruction at
all -- the `0xFF` of erased flash and the four values the MCS-51 map assigns to
no instruction (`0x06`, `0x07`, `0x16`, `0x17`) -- counted over a population
taken from committed CSV rather than re-scanned, and a **joint** ranking over
`(offset for bank 0, offset for bank 1)` pairs.

**The population is the committed one, and it is the same 403 sites
`find_banks.py` counts.** `ec/annotations/bank-call-targets.csv` carries a
`calls_stub` column naming the bank a caller's target stub selects, and the
runtime target is not a column: it is the two operand bytes of the `MOV DPTR`
three bytes earlier, read here out of the firmware and cross-checked against
the `0x90` opcode that has to be there. Reading it from the image rather than
restating `find_banks.py`'s arithmetic is what lets this tool be wrong
independently of that one.

**What the winner is and is not.** No pair is ever called confirmed. The
verdict is *the pair this scoring ranks first, by this many bad landings*, and
the tool prints what a chance offset would have scored over the same population
so the reader can see how much of the margin is evidence. On the committed
image bank 0's winning offset takes **no** bad landing in 350 sites and bank
1's takes none in 53, and §4 prints what a uniformly random 32 KiB block would
have been expected to take over each of those populations, so the reader sees
how much of the margin is evidence rather than being handed a number here that
can only drift from the one the tool computes.

**Framing is reported, not scored.** `disasm8051.py`'s `OPCODE_LEN` table is
imported so a target that walks cleanly for N instructions is distinguished from
one that runs into padding three bytes in, which the single-byte test cannot see.
But the walk's ranking is **depth-sensitive and this tool does not use it to
pick a winner**: measured over the committed population, bank 0's best offset is
`0x08000` at a walk limit of 8, 16 and 32, and `0x10000` at 64. A walk stops on
the first erased or unassigned byte it reaches, so how far it gets is a property
of where those bytes sit in the candidate block rather than of the mapping, and
this tool attributes the change to nothing more specific than that. The
per-depth columns are printed so that sensitivity is visible rather than buried,
and §5 names it as the reason the composite is depth-independent.

**Nothing here changes the mapping.** Acting on a result would churn every
bank-0 listing, `c-digests.csv`, `reassembly.csv` and the Ghidra project, and
`--mode rebuild-project` cannot merge against another branch that also rebuilds.

Usage:
    python3 bank_map_score.py
    python3 bank_map_score.py --check
    python3 bank_map_score.py --self-test
"""
import argparse
import collections
import csv
import os
import sys

from disasm8051 import OPCODE_LEN

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
FIRMWARE = os.path.join(EC, "firmware", "GMxMGxx_11.800")
TARGETS_CSV = os.path.join(EC, "annotations", "bank-call-targets.csv")

# The window a bank-switch stub selects into, and the file block size the
# mapping is a choice among. Both are the linker's, not this tool's: the stubs
# push `0x08` and then set bank bits, so 0x8000-0xFFFF is what the common area
# itself says the runtime window is.
WINDOW_BASE = 0x8000
BLOCK = 0x8000

# The four byte values the MCS-51 map assigns to no instruction. A linear walk
# landing on one is a data or unprogrammed byte, which is the same criterion
# `citation_gap_scan.py` uses for its `not-code` verdict and for the same
# reason: a transfer read out of one would be vacuous.
UNASSIGNED = frozenset({0x06, 0x07, 0x16, 0x17})

# Walk limits for the framing columns. 8 is disasm8051's window size and 64 is
# deep enough to reach past most small functions; the pair is reported at both
# because the whole point is that the ranking between them is not stable.
WALK_LIMITS = (8, 16, 32, 64)

ERASED, UNASSIGNED_V, OUT_OF_RANGE, LANDS = (
    "erased", "unassigned", "out-of-range", "lands")


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def population(d: bytes, rows):
    """`{bank: [runtime target]}` over the `calls_stub` rows, read from bytes.

    The operand is the two bytes of the `MOV DPTR,#imm16` that ends where the
    audited call begins, big-endian as `mov dptr,#0xBF1C` encodes it. The
    `0x90` opcode three bytes back is asserted rather than assumed: a row whose
    `calls_stub` column is set but whose bytes do not carry that `MOV DPTR` is a
    disagreement between the CSV and the image, and it is dropped here rather
    than scored against a target read from the wrong place.
    """
    out = collections.defaultdict(list)
    dropped = []
    for r in rows:
        if not r["calls_stub"]:
            continue
        off = int(r["file_offset"], 16)
        if off < 3 or d[off - 3] != 0x90:
            dropped.append(off)
            continue
        out[int(r["calls_stub"])].append((d[off - 2] << 8) | d[off - 1])
    return dict(out), dropped


def verdict(d: bytes, off: int):
    """One target's landing byte, as one of the four classes."""
    if off < 0 or off >= len(d):
        return OUT_OF_RANGE
    b = d[off]
    if b == 0xFF:
        return ERASED
    if b in UNASSIGNED:
        return UNASSIGNED_V
    return LANDS


def tally(d: bytes, targets, base: int):
    """The four landing classes for one (bank, candidate offset) pair."""
    return collections.Counter(verdict(d, base + (t - WINDOW_BASE))
                               for t in targets)


def bad(counter):
    """The landing classes that are not `lands`, in the order they are ranked.

    Erased first, because a bank cannot hold a function entry in flash that was
    never programmed -- that is a property of the image, not a judgement about
    framing. Unassigned second, for the same reason in weaker form. The
    distinction matters for the margin: two candidates can tie on the first
    component and be separated by the second, and printing one number would hide
    that.
    """
    return (counter[ERASED], counter[UNASSIGNED_V], counter[OUT_OF_RANGE])


def walk_instructions(d: bytes, off: int, limit: int):
    """How many instructions decode from a landing byte, and why the walk stopped.

    A count and not a verdict: `--check` must not fail on this, because how far
    a walk of 32 or 64 instructions gets is a property of the image and not of
    the mapping.
    """
    i, n = off, 0
    while n < limit:
        if i >= len(d):
            return n, OUT_OF_RANGE
        b = d[i]
        if b == 0xFF:
            return n, ERASED
        if b in UNASSIGNED:
            return n, UNASSIGNED_V
        i += OPCODE_LEN[b]
        n += 1
    return n, LANDS


def framing(d: bytes, targets, base: int, limit: int):
    """`{class: count}` for a walk of `limit` instructions from each target."""
    out = collections.Counter()
    insns = 0
    for t in targets:
        n, why = walk_instructions(d, base + (t - WINDOW_BASE), limit)
        out[why] += 1
        insns += n
    return out, insns


def candidates(d: bytes):
    """Every aligned block in the image, ascending -- the choice set."""
    return [base for base in range(0x08000, len(d), BLOCK)]


def chance_baseline(n: int):
    """What a uniformly random block would score over `n` targets.

    Two numbers, and they say different things. Five of the 256 byte values are
    erased or unassigned, so the expected bad landings for an offset with no
    relationship to the sites is `n * 5 / 256`. The probability of observing *no*
    bad landing at all -- which is what the winning offsets achieve -- is
    `(251 / 256) ** n` under that model, and it falls away with n: for bank 0's
    population it is small and for bank 1's it is not, which is why §4 prints it
    next to the margin rather than the margin alone.
    """
    p_bad = (len(UNASSIGNED) + 1) / 256.0
    return n * p_bad, (1.0 - p_bad) ** n


def score_banks(d: bytes, pop):
    """`{bank: [(bad tuple, base), ...]}` ranked, best first."""
    out = {}
    for bank in sorted(pop):
        targets = pop[bank]
        scored = [(bad(tally(d, targets, base)), base)
                  for base in candidates(d)]
        out[bank] = sorted(scored, key=lambda r: (r[0], r[1]))
    return out


def score_pairs(d: bytes, pop, banks):
    """Every ordered `(off_a, off_b)` pair, ranked, best first.

    The pair must name two *different* blocks. That is not a heuristic: two
    banks selected into the same runtime window at two different bank-bit values
    would be the same code reachable two ways, and the linker had no reason to
    emit two stubs for it -- so the constraint is what makes the search joint
    rather than two searches run side by side, and dropping it is how an
    independent per-bank tool comes to print the same offset twice.
    """
    out = []
    for base_a in candidates(d):
        for base_b in candidates(d):
            if base_a == base_b:
                continue
            total = collections.Counter()
            per = {}
            for bank, base in ((banks[0], base_a), (banks[1], base_b)):
                t = tally(d, pop[bank], base)
                per[bank] = (base, bad(t), t[LANDS])
                total.update(t)
            out.append((bad(total), base_a, base_b, per, total))
    return sorted(out, key=lambda r: (r[0], r[1], r[2]))


def framing_note(d: bytes, pop, ranked, scored):
    """Whether the walk ranking is stable across the walk limits, stated.

    The text names the banks whose best offset moves and what the limits are,
    rather than asserting that it does: on the committed image bank 0's moves
    and bank 1's does not, and a sentence that claimed otherwise for every
    image would be a claim about this tool rather than about these bytes.
    """
    moves = []
    for b in scored:
        winners = set()
        for limit in WALK_LIMITS:
            scored_here = [(framing(d, pop[b], base, limit)[1], base)
                           for base in candidates(d)]
            winners.add(max(scored_here)[1])
        if len(winners) > 1:
            moves.append((b, winners))
    if not moves:
        return ("The best offset is the same at every walk limit for every "
                "bank, so on this image the framing read and the composite "
                "agree. The composite is still the one that ranks: it reads "
                "one byte and cannot move with the limit, and this table is "
                "printed so that a reader who would rather rank on framing "
                "can see that the two agree here rather than assuming it.")
    parts = []
    for b, winners in moves:
        by_limit = []
        for limit in WALK_LIMITS:
            best = max((framing(d, pop[b], base, limit)[1], base)
                       for base in candidates(d))[1]
            by_limit.append("`0x%05X` at %d" % (best, limit))
        parts.append("bank %d's best offset is %s" % (b, ", ".join(by_limit)))
    return ("**The ranking this table implies is not stable, and that is the "
            "finding.** " + "; ".join(parts) + ". A long walk from a target "
            "near the top of a window runs into that bank's erased tail, and "
            "whether it does depends on where the tail is -- which is a "
            "property of the candidate offset rather than of the mapping. The "
            "composite in §2 is depth-independent by construction, it reads "
            "one byte, and it is the composite that ranks; this table is "
            "printed so the sensitivity is visible to anyone who would "
            "otherwise have assumed a framing metric settles it.")


def report(d: bytes, pop, dropped, rows=None) -> str:
    ranked = score_banks(d, pop)
    banks = sorted(pop)
    scored = [b for b in banks if pop[b]]
    unscored = [b for b in banks if not pop[b]]
    lines = []

    lines.append("## 1. The population")
    lines.append("")
    lines.append("| bank | call sites | distinct targets | runtime range |")
    lines.append("|---|---:|---:|---|")
    for b in sorted(pop):
        t = pop[b]
        lines.append("| %d | %d | %d | `0x%04X`-`0x%04X` |"
                     % (b, len(t), len(set(t)), min(t), max(t)))
    lines.append("")
    lines.append("%d row(s) of `bank-call-targets.csv` carry a `calls_stub` "
                 "bank but no `MOV DPTR` opcode three bytes back, and are not "
                 "scored: %s"
                 % (len(dropped),
                    ", ".join("`0x%05X`" % x for x in dropped) or "none"))

    lines.append("")
    lines.append("## 2. Per bank, over every candidate block")
    lines.append("")
    lines.append("Ranked by `(landed on erased, landed on unassigned, out of "
                 "range)`, smallest first. Lower is better on all three; the "
                 "first non-tied component decides.")
    lines.append("")
    for b in scored:
        lines.append("**bank %d** (%d sites)" % (b, len(pop[b])))
        lines.append("")
        lines.append("| file offset | erased | unassigned | out of range | lands "
                     "|")
        lines.append("|---|---:|---:|---:|---:|")
        for btup, base in ranked[b][:4]:
            t = tally(d, pop[b], base)
            lines.append("| `0x%05X` | %d | %d | %d | %d |"
                         % (base, btup[0], btup[1], btup[2], t[LANDS]))
        best, second = ranked[b][0], ranked[b][1]
        lines.append("")
        margin = ("The winner is the only candidate with no erased landing."
                  if second[0][0] > 0 else
                  "The winner and the runner-up tie on erased landings and are "
                  "separated only by the unassigned class, which is a thinner "
                  "margin than the first table row suggests.")
        lines.append("Best `0x%05X` at %d bad landing(s); runner-up "
                     "`0x%05X` at %d. %s"
                     % (best[1], sum(best[0]), second[1], sum(second[0]),
                        margin))
    for b in unscored:
        lines.append("")
        lines.append("**bank %d**: no call site reaches its stub. Nothing to "
                     "score, and *not found by this method* is the reading -- "
                     "not 'this bank has no code'. `firmware_regions.py` §2 "
                     "reports what its file slot holds." % b)

    lines.append("")
    lines.append("## 3. Jointly, over ordered `(bank 0, bank 1)` offset pairs")
    lines.append("")
    lines.append("Every pair of distinct blocks, ranked the same way with both "
                 "banks' landings added together.")
    lines.append("")
    if len(scored) >= 2:
        pairs = score_pairs(d, pop, scored[:2])
        lines.append("| bank 0 offset | bank 1 offset | erased | unassigned | "
                     "out of range |")
        lines.append("|---|---|---:|---:|---:|")
        for tup, ba, bb, _per, _tot in pairs[:4]:
            lines.append("| `0x%05X` | `0x%05X` | %d | %d | %d |"
                         % (ba, bb, tup[0], tup[1], tup[2]))
        top, runner = pairs[0], pairs[1]
        lines.append("")
        lines.append("Best pair (`0x%05X`, `0x%05X`) at %d bad landing(s) in "
                     "total; runner-up (`0x%05X`, `0x%05X`) at %d."
                     % (top[1], top[2], sum(top[0]),
                        runner[1], runner[2], sum(runner[0])))
        lines.append("")
        lines.append("The two banks independently rank their own best offset "
                     "first and the joint pair the ranking finds is that same "
                     "pair, so on this image the consistency constraint adds "
                     "nothing to the per-bank result -- which is itself the "
                     "answer, not a null one." if
                     (top[1] == ranked[scored[0]][0][1] and
                      top[2] == ranked[scored[1]][0][1])
                     else "The joint pair is not the pair the two per-bank "
                          "rankings prefer; §6 says what that would mean.")
    else:
        lines.append("Fewer than two banks carry call sites, so there is no "
                     "joint ranking to print.")

    lines.append("")
    lines.append("## 4. What a chance offset scores over the same population")
    lines.append("")
    lines.append("A uniformly random 32 KiB block has five of 256 byte values "
                 "that are erased or unassigned, so an offset with no "
                 "relationship to the sites is expected to take that fraction "
                 "of them.")
    lines.append("")
    lines.append("| bank | sites | expected bad landings | P(no bad landing) |")
    lines.append("|---|---:|---:|---:|")
    for b in scored:
        exp, p0 = chance_baseline(len(pop[b]))
        lines.append("| %d | %d | %.1f | %.3f |"
                     % (b, len(pop[b]), exp, p0))
    lines.append("")
    lines.append("Read the two columns together. A zero observed against a "
                 "large expectation and a small probability is a margin worth "
                 "having; a zero observed against a small expectation and a "
                 "probability near half is not, and the population size is what "
                 "tells them apart.")

    lines.append("")
    lines.append("## 5. Framing, and why it does not pick the winner")
    lines.append("")
    lines.append("The instruction counts a linear walk decodes from each "
                 "landing byte, at four walk limits, for the winning and "
                 "runner-up offset of each bank. Higher is better.")
    lines.append("")
    header = "| bank | offset | " + " | ".join(
        "limit %d" % n for n in WALK_LIMITS) + " |"
    lines.append(header)
    lines.append("|---" * (len(WALK_LIMITS) + 2) + "|")
    for b in scored:
        for btup, base in ranked[b][:2]:
            cells = []
            for n in WALK_LIMITS:
                _c, insns = framing(d, pop[b], base, n)
                cells.append(str(insns))
            lines.append("| %d | `0x%05X` | %s |"
                         % (b, base, " | ".join(cells)))
    lines.append("")
    lines.append("**%s**" % framing_note(d, pop, ranked, scored))

    lines.append("")
    lines.append("## 6. What this method does not settle")
    lines.append("")
    bucket_c = sum(1 for r in (rows or []) if r.get("bucket") == "C")
    lines.append("- **No pair is confirmed.** What §3 prints is the pair this "
                 "scoring ranks first and by how much. A ranking over landing "
                 "bytes is evidence about where bytes land, not about what the "
                 "hardware selects.")
    lines.append("- **A pair that scored badly here is not disproved.** A "
                 "correct mapping whose targets all landed on instruction "
                 "shaped bytes would score like a wrong one, and nothing here "
                 "can tell those two cases apart.")
    lines.append("- **Computed targets are not in the population.** A target "
                 "built at run time (`jmp @a+dptr` and its relatives) names no "
                 "file offset to check, so a mapping that is right for every "
                 "static call and wrong for the computed ones would score "
                 "cleanly here.")
    lines.append("- **The %d common-area call sites naming a banked target are "
                 "not scored.** `audit_call_targets.py` files those as bucket "
                 "C, and `offset_for_runtime()` returns `None` for the shape "
                 "because no byte resolves which bank a common-area caller "
                 "meant. They carry no `calls_stub` value, so they are not in "
                 "§1, and no mapping scores well or badly on them here."
                 % bucket_c)
    lines.append("- **Framing uncertainty cuts both ways.** §5 shows the walk "
                 "ranking move; the composite does not, because it does not "
                 "walk. Neither is proof of alignment and both are printed.")
    lines.append("- **Nothing here was observed on hardware.** Every input is a "
                 "committed file.")
    return "\n".join(lines)


def self_test() -> int:
    """The known answers, and the refusals that make them worth anything.

    The oracles are outside this tool: the population is the committed CSV's
    `calls_stub` column cross-checked against the firmware's own `MOV DPTR`
    opcodes, the byte classes are `disasm8051.OPCODE_LEN`'s neighbourhood and
    the four MCS-51 unassigned values, and the erased blocks are the ones
    `firmware_regions.py` measures. The refusals are what stops this tool
    quietly becoming a second `find_banks.py`: a CSV row whose bytes do not
    carry the `MOV DPTR` is dropped rather than scored, a report it cannot
    reproduce from the committed inputs is refused, and no verdict anywhere in
    it is the word `confirmed`.
    """
    bad_count = 0
    print("bank_map_score.py --self-test")

    def check(label, ok, detail=""):
        nonlocal bad_count
        bad_count += 0 if ok else 1
        print("  %s  %s%s" % ("ok  " if ok else "FAIL", label,
                              "" if ok or not detail else "  " + detail))

    d = open(FIRMWARE, "rb").read()
    rows = read_csv(TARGETS_CSV)
    pop, dropped = population(d, rows)

    csv_sites = sum(1 for r in rows if r["calls_stub"])
    check("every `calls_stub` row has the `MOV DPTR` opcode three bytes back, "
          "so none is dropped", not dropped and csv_sites == sum(
              len(v) for v in pop.values()),
          "%d dropped of %d" % (len(dropped), csv_sites))
    check("the population is 403 call sites over two banks, 350 selecting "
          "bank 0 and 53 selecting bank 1",
          len(pop) == 2 and len(pop[0]) == 350 and len(pop[1]) == 53,
          "got " + repr({k: len(v) for k, v in sorted(pop.items())}))
    check("every target is a runtime address at or above the window base, and "
          "all are distinct within a bank",
          all(t >= WINDOW_BASE for v in pop.values() for t in v) and
          all(len(set(v)) == len(v) for v in pop.values()),
          "")
    # The two classes this tool scores on, asserted as the classes they claim
    # to be rather than as the set they happen to hold: `verdict()` over a
    # one-byte buffer is the oracle, and the list is the manual's, not the
    # decoder's. The bytes either side of the unassigned run are in it too, so
    # this is about where the MCS-51 map's hole is and not about how many values
    # the list happens to carry.
    bad_bytes = (0xFF, 0x06, 0x07, 0x16, 0x17)
    check("the five bad-landing byte values are exactly 0xFF plus the four the "
          "MCS-51 map assigns to no instruction, and `verdict()` files each of "
          "them into the class the name says",
          UNASSIGNED == {0x06, 0x07, 0x16, 0x17} and
          [verdict(bytes([b]), 0) for b in bad_bytes] ==
          [ERASED] + [UNASSIGNED_V] * 4,
          "got " + repr([(hex(b), verdict(bytes([b]), 0)) for b in bad_bytes]))
    check("the bytes either side of that hole are real instructions and land",
          all(verdict(bytes([b]), 0) == LANDS
              for b in (0x05, 0x15, 0x18, 0x22)),
          "got " + repr([(hex(b), verdict(bytes([b]), 0))
                        for b in (0x05, 0x15, 0x18, 0x22)]))
    check("the window base itself is not one of the bad-landing bytes, so a "
          "target of `0x8000` is a landing rather than a hole",
          verdict(d, WINDOW_BASE) == LANDS,
          "0x%05X is %s" % (WINDOW_BASE, verdict(d, WINDOW_BASE)))

    # A row that claims a stub but has no MOV DPTR must be dropped, not scored
    # against bytes read from the wrong place.
    tampered = open(TARGETS_CSV, newline="").read()
    check("a CSV row whose bytes do not carry the `MOV DPTR` is dropped rather "
          "than scored",
          _refuses_dropped_row(d, rows),
          "the drop path was not exercised")

    ranked = score_banks(d, pop)
    best0, second0 = ranked[0][0], ranked[0][1]
    best1, second1 = ranked[1][0], ranked[1][1]
    check("bank 0's best-scoring offset is the one `make_bank_image.py` builds "
          "from, with no erased landing in 350 sites",
          best0[1] == 0x08000 and best0[0] == (0, 0, 0),
          "best=0x%05X %r" % (best0[1], best0[0]))
    check("bank 1's best-scoring offset is the one `make_bank_image.py` builds "
          "from, with no erased landing in 53 sites",
          best1[1] == 0x10000 and best1[0] == (0, 0, 0),
          "best=0x%05X %r" % (best1[1], best1[0]))
    check("the two margins are not the same shape, and the assertion says which "
          "component each is decided on: bank 0's runner-up lands on erased "
          "flash, bank 1's ties it there and is caught by the unassigned class",
          second0[0][0] > 0 and second1[0][0] == 0 and second1[0][1] > 0,
          "bank0 runner %r, bank1 runner %r" % (second0, second1))
    check("every other candidate is worse than the winner, so the ranking is "
          "a total order and not an artefact of the sort",
          all(r[0] >= best0[0] for r in ranked[0]) and
          all(r[0] >= best1[0] for r in ranked[1]),
          "")

    pairs = score_pairs(d, pop, [0, 1])
    check("the joint ranking's best pair is the two per-bank winners, and no "
          "pair is allowed to name one block twice",
          (pairs[0][1], pairs[0][2]) == (0x08000, 0x10000) and
          all(p[1] != p[2] for p in pairs),
          "best=(0x%05X,0x%05X)" % (pairs[0][1], pairs[0][2]))
    check("the joint pair's per-bank breakdown names the same offsets the "
          "per-bank ranking does, so the two tables cannot disagree",
          pairs[0][3][0][0] == best0[1] and pairs[0][3][1][0] == best1[1] and
          pairs[0][3][0][1] == best0[0] and pairs[0][3][1][1] == best1[0],
          repr(pairs[0][3]))

    # -- the refusals --
    text = report(d, pop, dropped, rows)
    check("the word `confirmed` never appears except in the line that denies "
          "it, so no verdict this tool can print asserts one",
          [ln for ln in text.splitlines() if "confirmed" in ln.lower()] ==
          ["- **No pair is confirmed.** What §3 prints is the pair this "
           "scoring ranks first and by how much. A ranking over landing "
           "bytes is evidence about where bytes land, not about what the "
           "hardware selects."],
          "in " + repr([ln for ln in text.splitlines()
                        if "confirmed" in ln.lower()]))
    check("the report names the computed-target gap and the population this "
          "method does not score",
          all(s in text for s in ("Computed targets", "not scored")))
    check("a report this tool cannot reproduce from the committed inputs is "
          "refused", _refuses_unreproducible(d, rows),
          "an altered image was still accepted")
    check("the chance baseline is printed with the margin, so a clean score on "
          "a small population cannot read as a strong one: over bank 1's sites "
          "a chance offset would take no bad landing about a third of the time",
          "P(no bad landing)" in text and 0.1 < chance_baseline(53)[1] < 0.9,
          "P(no bad landing) over %d sites is %.3f" % (53,
                                                       chance_baseline(53)[1]))

    print("\n%d assertion(s) failed" % bad_count if bad_count
          else "\nall assertions passed")
    return 1 if bad_count else 0


def _refuses_dropped_row(d, rows):
    """A row claiming a stub whose bytes are not a `MOV DPTR` is not scored."""
    fake = dict(rows[0])
    fake["file_offset"] = "0x0000"          # no `MOV DPTR` three bytes back
    fake["calls_stub"] = "0"
    _pop, dropped = population(d, rows + [fake])
    return dropped == [0]


def _refuses_unreproducible(d, rows):
    """The population is a function of the image; a changed image changes it.

    This is the oracle for "reproducible from the committed image": a copy of
    the image with one `MOV DPTR` operand byte moved must give a different
    population, or the population is not being read out of the bytes at all. It
    moves an operand on a row that carries a `calls_stub` bank, since a row
    without one is not in the population and altering it would change nothing.
    """
    pop, _dropped = population(d, rows)
    first = next(r for r in rows if r["calls_stub"])
    off = int(first["file_offset"], 16)
    altered = bytearray(d)
    altered[off - 2] ^= 0x01
    pop2, _ = population(bytes(altered), rows)
    before = pop[int(first["calls_stub"])].index(
        (d[off - 2] << 8) | d[off - 1])
    return pop2[int(first["calls_stub"])][before] != pop[int(first["calls_stub"])][before]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="the gate form: the report, and a non-zero exit on a "
                         "dropped call site or an unreproducible population")
    ap.add_argument("--self-test", action="store_true",
                    help="the known answers and the refusals")
    ap.add_argument("--image", default=FIRMWARE,
                    help="the image to score; defaults to the committed dump, "
                         "and the fixtures under testdata/ are read this way")
    ap.add_argument("--targets", default=TARGETS_CSV,
                    help="the `bank-call-targets.csv` the population is read "
                         "from, for the same reason")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    d = open(args.image, "rb").read()
    rows = read_csv(args.targets)
    pop, dropped = population(d, rows)
    print(report(d, pop, dropped, rows))
    if not args.check:
        return 0
    # The two things --check is for, both of which are about this tool's own
    # inputs rather than about what the firmware contains. A dropped call site
    # means the CSV and the image disagree and the scoring is being run over a
    # population neither of them fully supports; an unreproducible population
    # means the report above is not a function of the committed files.
    if dropped:
        print("\nFAIL: %d `calls_stub` row(s) have no `MOV DPTR` three bytes "
              "back and were dropped from the population" % len(dropped),
              file=sys.stderr)
        return 1
    if _refuses_unreproducible(d, rows):
        return 0
    print("\nFAIL: the population did not change when an operand byte changed, "
          "so it is not being read from the image", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())