#!/usr/bin/env python3
"""Census every XDATA address the decompiled EC firmware touches, attribute it
to the functions that touch it, and group the addresses into clusters -- the
regenerable register map issue #132 asks for.

The inputs are the committed text files the default mode reads, and nothing
else:

    ec/decompiled/*/*.c             the decompiled C
    ec/decompiled/index.csv         the exporter's own census of what exists
    ec/annotations/ghidra-functions.csv   hand names and types
    ec/ghidra/xdata-symbols.csv     the generated symbol table (read for `name`)

`--self-test` additionally reads `ec/decompiled/*/*.asm`. No firmware image,
no Ghidra, no network, which is what lets this live in
`.github/scripts/agent-gates.sh` next to the other decompiler self-tests. The
`--reconcile` mode is the one exception and says so: it deliberately reaches
for the image so it can be compared against `register_ref_table.py`, which is a
different method over different bytes.

**The function list comes from `index.csv`, not from the header comment.** The
`// bank0 @ 0EA2  name  [named]` banner is a comment format this tool would
then have to keep up with; the exporter already writes down what it exported.
The self-test asserts the census and the file set still agree, so a `.c` the
index lost is a failure rather than a silently unread function.

**Two programs, never one address space.** `ec/decompiled/pd/` is the
self-contained `ITE8850-PD` image at file `0x20000` with its own XDATA map
(ec/README.md's Layout section, `annotations/pd-xdata-overlap.md` §5, and
`../../docs/findings.md` §3a). Mixing the two is the mistake §3a already had to
correct, so the split is this tool's first act and clustering never crosses it.
The `program` column on every row says which image a count came from, and a
shared address number is not a shared byte.

**Each reference lands in exactly one of five direction buckets**, decided from
the C text around the occurrence:

    read             the value is used, which includes every `==` comparison
    write            an `=` target, including the compound forms Ghidra
                     spells `DAT_EXTMEM_1300 = DAT_EXTMEM_1300 & 0x0f`
    read+write       an `=` target whose right-hand side names the same address
    passed-to-call   an argument of a call to a routine `index.csv` records
    address-taken    `&DAT_EXTMEM_xxxx`

`passed-to-call` is its own bucket on purpose, mirroring the `handoff` bucket
`register_ref_table.py` already reports: an 8051 has no Keil
calling-convention model, so `FUN_CODE_2990(DAT_EXTMEM_0a54)` may be passing a
value or a pointer the callee writes through, and the decompiled C cannot say
which. Folding it into "read" is exactly the confident-sounding phrasing
`CLAUDE.md` rules out. The test is membership in `index.csv`'s name set rather
than a `FUN_CODE_` prefix, because `dptr_add_4x_a(DAT_EXTMEM_0a4c)` has the
same unresolved direction and does not carry the prefix; it also keeps Ghidra's
`CONCAT11`/`CARRY1` pseudomacros out, which are value expressions and not
handoffs.

`*DAT_EXTMEM_048a = DAT_EXTMEM_048d;` is the one shape the store rule has to
special-case: the `=` lands on a dereference, so the byte at `0x048A` is read
as a pointer and the write goes wherever it points, not to `0x048A`. The
address is a `read`, and there are two such sites in the whole tree. A `*`
followed by a *space* is Ghidra's multiplication, not a dereference
(`(param_2 + (ushort)param_1) * DAT_EXTMEM_0826;`), and is a `read` for the
ordinary reason -- the value is used -- not because of the `*`.

**`==` is a comparison, not a store, and 838 of them are in this tree.**
`ASSIGN` begins with `=`, so `if (DAT_EXTMEM_0440 == '\\0')` used to satisfy
the store test and land in `write` -- or in `read+write` when the right-hand
side named the address too. That is not a rounding error in a description of
the firmware: it invented writers, and the invented writers then fed the
writer axis the clustering runs on, so whole clusters moved. The rule is now
that the operator after the address must be an assignment and must not be
`==`, and the self-test pins both halves -- a table of literal Ghidra-shaped
lines through `classify()`, and a per-address direction oracle derived by grep
rather than by this tool (issue #178). The `!=`/`<`/`>`/`>=`/`<=` operators were
never in `ASSIGN` and already fell through, which is a claim the same
assertion now measures instead of assuming.

**What this does not say.** A cluster is a co-occurrence pattern in static code
-- "these forty-three addresses are touched by the same four functions" -- and
that is evidence about *shape*, not about meaning. Nothing here names a
register or gives a cluster a purpose; `annotations/xdata-register-map.md` says
so in its own §"What this does not establish", and the reading is one issue per
cluster. A `write` count is not evidence the EC acts on the value, and a zero
is "not found by this method", never "absent" (`../../docs/findings.md` §4c,
and the `0x0733`/`0x0735` reconciliation in that same report is the worked
counter-example). Two further limits ride on the input: a function that did not
decompile is not in the tree at all, so this is a lower bound on the image, and
pointer/indirect XDATA access never names an address at all, exactly as
`scan_refs.py`'s blind spot does.

**The decompiled C spells an XDATA address two ways, and a census that reads
only one of them is wrong by 41 addresses.** `build_ec_decompile.py` applies the
generated symbol table before exporting, so the 101 addresses
`gen_xdata_symbols.py` can name come out as `CPU_TEMP` and
`MODE_TCC_OFFSET_DEFAULTS_GAMING_0`, not as `DAT_EXTMEM_043e`. Scanning for
`DAT_EXTMEM_` alone -- which is what issue #132's headline number did -- reports
**zero** named main-EC addresses, and that looks like a finding about the
register corpus when it is a finding about the grep. The two spellings are
disjoint address for address within a program (the self-test asserts it), so a
zero from the old method stays recoverable from the same committed files.

**`spelled_as` and `name` are two different facts and must not be read as one.**
`spelled_as` is how the decompiled text refers to the address;
`name` is what `xdata-symbols.csv` calls it. They differ for the six named
addresses the PD image touches -- `0x07D0` is `BATTERY_CHARGE_LIMIT_DOWN` in
`name` and `DAT_EXTMEM_07d0` in the PD image's own source, because
`gen_xdata_symbols.py` refuses to name that program at all. Reading the PD row
as the PD firmware calling it `BATTERY_CHARGE_LIMIT_DOWN` is the
`pd-xdata-overlap.md` mistake in a new place.

**What settles an address's space is the encoding, not the token.** Ten of
`pd-001`'s 34 addresses sit in `0xFF00`-`0xFFFF`, inside the width of an SFR
byte, and the census counts them because Ghidra wrote `DAT_EXTMEM_ff80`. That
spelling is a decompiler decision; the opcode is not. Each is loaded by
`mov DPTR,#imm16` (opcode `0x90`) and dereferenced by `movx` (0xE0/0xF0), and
`movx` is the instruction that names the external space -- there is no `movx`
form for the direct or SFR space. The other half is structural and needs no
decompile at all: **no 8051 direct-addressing opcode takes a 16-bit operand**,
so a `0xFFxx` value cannot be a direct address whatever anything spelled it as.
`--self-test` reads the committed `.asm` and pins both, and pins the three
addresses a `90 hi lo` byte scan cannot find, because it reads the tree
precisely for those.

Usage:
    python3 ec/tools/xdata_register_map.py               # write the two CSVs
    python3 ec/tools/xdata_register_map.py --check       # diff vs committed
    python3 ec/tools/xdata_register_map.py --self-test
    python3 ec/tools/xdata_register_map.py --threshold-sweep
    python3 ec/tools/xdata_register_map.py --threshold-sweep --no-writer-axis
    python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800
"""
import argparse
import collections
import csv
import io
import os
import re
import sys

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
EC_DIR = os.path.dirname(TOOL_DIR)
DECOMPILED = os.path.join(EC_DIR, "decompiled")
INDEX_CSV = os.path.join(DECOMPILED, "index.csv")
ANNOT_CSV = os.path.join(EC_DIR, "annotations", "ghidra-functions.csv")
SYMBOLS_CSV = os.path.join(EC_DIR, "ghidra", "xdata-symbols.csv")
OUT_REGISTERS = os.path.join(EC_DIR, "annotations", "xdata-registers.csv")
OUT_CLUSTERS = os.path.join(EC_DIR, "annotations", "xdata-clusters.csv")

# The EC firmware proper: common area plus the two CODE banks that have
# callers in this build (ec/README.md's bank table). Never "pd" -- the two
# programs have separate XDATA maps and a cluster must not span them.
MAIN_PROGRAMS = ("common", "bank0", "bank1")
PD_PROGRAM = "pd"
GROUPS = ("main-ec", "pd")

# `program` column values. A row is `both` when the address number is touched
# by each program, which is a collision in the numbering and not a shared byte.
PROGRAM_COL = {"main-ec": MAIN_PROGRAMS, "pd": (PD_PROGRAM,)}

# Order is the CSV's column order and the order a reader meets the vocabulary
# in the report; a bucket that never fires would be a classifier that stopped
# looking, which is why the self-test asserts two of them are non-empty.
BUCKETS = ("read", "write", "read+write", "passed-to-call", "address-taken")
# The two spellings, spelled as they appear in the decompiled C.
SPELLINGS = ("DAT_EXTMEM", "symbol")
ASSIGN = ("=", "|=", "&=", "+=", "-=", "*=", "/=", "^=", "%=", "<<=", ">>=")

REGISTER_COLUMNS = [
    "addr", "program", "spelled_as", "span_group", "cluster_id", "refs",
    "read", "write", "read+write", "passed-to-call", "address-taken",
    "readers", "writers", "functions_touched", "single_function", "name",
    "functions",
]
CLUSTER_COLUMNS = [
    "cluster_id", "program", "size", "refs", "addrs", "addr_range",
    "functions_touched", "shared_functions", "callees", "named_addrs",
]

# Jaccard >= 0.5 sits at the top of the plateau the sweep shows: from 0.35 to
# 0.50 the largest main-EC cluster holds at 108-112 addresses while the cluster
# count only moves 337 -> 376, and 0.55 drops that to 43 and adds 149 clusters.
# `--threshold-sweep` prints the whole curve and the report quotes it, so the
# default is a recorded choice rather than a tuned one.
DEFAULT_THRESHOLD = 0.50
SWEEP_THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)

# The `callees` column lists this many routines per cluster, so a wide cluster
# does not print a page of names. The cap is reported in the column itself
# (a trailing "(+N more)") -- a silent cap reads as "covered" when it is not.
TOP_CALLEES = 3

# Issue #132's numbers, with the two corrections this tool had to make, both
# of which the report states in place.
#
# First: the issue's 14,399 references include nine occurrences that are this
# repository's own annotation text quoting the decompile back at itself
# (bank0/B9DF.c's comment writes `DAT_EXTMEM_0a56 = DAT_EXTMEM_1919` to make a
# point about it). A hand-written comment is not the firmware touching an
# address, so `strip_comments()` drops them and the `DAT_EXTMEM_` count is
# 14,390.
#
# Second, and much the larger: the issue counted `DAT_EXTMEM_` tokens only, and
# the addresses Ghidra was given a name for are not written that way. Reading
# both spellings adds the main-EC addresses the exporter named, which were
# always in the committed tree. Every number is pinned below -- the
# `DAT_EXTMEM_` totals and the full ones -- so a drift in either says which
# moved.
#
# The split moved 41 -> 82 named addresses (411 -> 915 references) when
# ec/decompiled/ was re-exported in issue #194, and the totals with it: 41
# addresses that had been committed as `DAT_EXTMEM_xxxx` are now written by the
# name ec/ghidra/xdata-symbols.csv gives them. Nothing was added or lost -- the
# full census below (1172 distinct / 14801 references, main EC 1063/13937) is
# unchanged, and no .asm moved -- so this is the exporter catching up with a
# symbol table that had already grown, which is the same re-derivation the
# `named_in_tree` comment below records for 44 -> 79 -> 86.
#
# 82 -> 84 (915 -> 932) for the same reason when #237's MAIN_FAN_L_DUTY and
# MAIN_FAN_R_DUTY entries were exported (0x075B/0x075C, 17 references that had
# been `DAT_EXTMEM_075b`/`_075c`); the full census does not move. 84 -> 127
# (932 -> 5897) with issue #179's 43 entries, the same way, and 127 -> 142
# (5897 -> 6016) with issue #180's 15, and 142 -> 146 (6016 -> 6060) with
# issue #183's four.
# *** 2026-09-24, merging issue #133 (PR #238): the FULL census moved for the first
# time, 1172/14801 -> 1171/14792 (main EC 1063/13937 -> 1062/13931, PD refs 864 ->
# 861). Not a new address and not an edit to any .asm: applying
# ghidra-variables.csv commits some functions' signatures, and at bank1 0x9EA1
# that dropped an argument at its call sites -- bank1/E100.c no longer passes
# DAT_EXTMEM_0390, which was the census's only reference to 0x0390. Nine C-level
# references moved in all (0x0390 -1, 0x0391 -1, 0x04AB -3, 0x07D8 -3, 0x08AD -1;
# PD 0x07D0 -1, 0x07C9 +1). The census was always a lower bound on the machine
# code; this is the annotation layer lowering it, recorded in
# xdata-register-map.md and docs/findings.md 18 as an open question.
ORACLE = {
    # DAT_EXTMEM_ only, i.e. what issue #132 counted, comments excluded.
    "extmem_distinct": 1036, "extmem_refs": 8732,
    "extmem_raw": 8741, "extmem_commented": 9,
    "extmem_main_distinct": 916, "extmem_main_refs": 7871,
    "extmem_pd_distinct": 157, "extmem_pd_refs": 861,
    # What the decompiler named, which the issue's grep could not see.
    "symbol_main_distinct": 146, "symbol_main_refs": 6060,
    "symbol_pd_distinct": 0, "symbol_pd_refs": 0,
    # The full census this tool publishes.
    "distinct": 1171, "refs": 14792,
    "main_distinct": 1062, "main_refs": 13931,
    "pd_only": 109, "both": 48,
    # Addresses the symbol table names AND the census reaches. It is not
    # `len(symbols)`: naming an address in registers.yaml does not put it in
    # a decompiled function, so the two counts part company whenever a
    # register is named that no surviving function touches. It moved 44 -> 79
    # when the 0x0400-0x045F page entries landed in registers.yaml without
    # this constant being re-derived, and the self-test was failing on `main`
    # because of it; 86 is the re-derived count, of which 7 are
    # 0x08A0/0x08A2/0x08EB/0x089E/0x089F/0x09E6/0x09E7
    # (ec/annotations/manual-fan-ctrl-0751.md 8a). 86 -> 88 when #237's
    # MAIN_FAN_L_DUTY/MAIN_FAN_R_DUTY (0x075B/0x075C) were exported by name.
    # 88 -> 131 with issue #179's 43 XDATA_* timer/counter entries, merged
    # after the ones above; the full census below does not move.
    # 131 -> 146 with issue #180's 15 0x086x/0x1Cxx/0x1Fxx entries.
    # 146 -> 150 with issue #183's 0x07C4/0x07D3/0x07D4/0x07D5.
    "named_in_tree": 150,
}
ORACLE_TOP_MAIN = (("0x0440", 181), ("0x08A8", 170))
# The two symbol-table addresses register_ref_table.py finds main-EC sites for
# that the census does not. Both are inside
# bank0:0x94D0=copy_code_table_into_0730_07a7: 0x0733 is spelled
# `puVar3 = &DAT_CODE_0733;`, as a code pointer, and 0x0735 is not spelled at
# all -- `sVar5 = 0x735; ... *(char *)(sVar5 + bVar2)` is an indexed access off
# a raw base literal. Only the first is findable, so only it is checked; see
# the self-test and the report's blind-spot section.
BLIND_SPOT = (0x0733, 0x0735)

# Issue #181: the ten pd-001 addresses in 0xFF00-0xFFFF, and the instruction
# form that carries each, read off the committed `ec/decompiled/pd/*.asm`. The
# census counts them because Ghidra wrote `DAT_EXTMEM_ff80`; what settles the
# address space is the encoding, and the form is written down here so a future
# export cannot quietly change one without a failing check. `INC` is the
# `mov DPTR,#seed` + `inc DPTR` continuation: 0xFFC1 and 0xFFD1 are reached
# that way and are never the operand of a `mov DPTR` of their own.
#
# 0xFFE0, 0xFFE1 and 0xFFE2 also appear as literal targets, and 0xFFD0 and
# 0xFFC0 as seeds. That overlap is the point -- the same address has both
# forms in the image, and the census never needed to know which.
XSPACE_FORM = {
    0xFF80: "mov DPTR,#0xFF80",
    0xFF84: "mov DPTR,#0xFF84",
    0xFFC0: "mov DPTR,#0xFFC0",
    0xFFC1: "INC",
    0xFFC2: "mov DPTR,#0xFFC2",
    0xFFD0: "mov DPTR,#0xFFD0",
    0xFFD1: "INC",
    0xFFE0: "mov DPTR,#0xFFE0",
    0xFFE1: "mov DPTR,#0xFFE1",
    0xFFE2: "mov DPTR,#0xFFE2",
}
# And the three of the twenty-three that only the continuation reaches. 0xFFDB
# is not one of the ten -- it is in another cluster -- but a `90 hi lo` scan
# misses it exactly as it misses 0xFFC1 and 0xFFD1, so the count the
# discrimination prints would be wrong without it.
XSPACE_INC_ONLY = (0xFFC1, 0xFFD1, 0xFFDB)
# Every PD census address at or above 0xF000, pinned address for address so a
# re-export that adds or drops one fails here instead of quietly reclassifying
# the region. Twenty are literal `mov DPTR,#imm16` targets, three are the
# continuation above.
XSPACE_PD_HIGH = (
    0xFF40, 0xFF42, 0xFF4A, 0xFF62, 0xFF80, 0xFF84, 0xFF88, 0xFFC0,
    0xFFC1, 0xFFC2, 0xFFC6, 0xFFD0, 0xFFD1, 0xFFD3, 0xFFD4, 0xFFD5,
    0xFFD8, 0xFFDA, 0xFFDB, 0xFFDF, 0xFFE0, 0xFFE1, 0xFFE2,
)
# The main EC's highest census address, and the ceiling the PD image's 0xFFxx
# run sits above. Pinned because "the 0xF000-0xFFFF run is the PD image's own"
# is a claim about the main EC's *census*, and a census is a lower bound.
MAIN_EC_CEILING = 0x9000
# How far past a `mov DPTR,#seed` the continuation walk looks for the `inc DPTR`
# and the `movx` that close it. Long enough for the windows in this tree
# (`pd/EFB9.asm` needs 4 instructions), short enough that a seed far from any
# dereference reports "not found by this method" instead of pairing across the
# rest of a function.
XSPACE_WINDOW = 32

# The five bucket totals `xdata-register-map.md` §4.1 publishes.
#
# This pin is INTERNAL, and deliberately kept apart from the two below: these
# are this tool's own buckets summed back to itself, so they catch a classifier
# that changes but not one that was wrong -- every entry satisfies
# `sum(buckets) == refs` either way. Presenting them as evidence that the
# direction split is right is the mistake issue #178 exists to correct. What
# makes the direction external is HAND_CHECKED.
BUCKET_TOTALS = {"read": 8317, "write": 3186, "read+write": 2476,
                 "passed-to-call": 543, "address-taken": 270}

# Direction, per address, derived by reading the decompiled C and re-derivable
# with the greps cited in each entry -- not by running this tool. That is the
# whole point: an internal consistency check passes on a misclassified
# comparison, because the misclassification is itself internally consistent, and
# 838 `==` comparisons were classified as stores for exactly that long (issue
# #178). Each value is the per-bucket reference counts plus `writers`, the
# number of distinct functions holding a write or read+write reference of their
# own. An entry here that the census disagrees with is a disagreement between a
# reading and a tool, and both are printed.
HAND_CHECKED = {
    # No `DAT_EXTMEM_0440 =` anywhere in ec/decompiled/. Of 181 references: 15
    # `==` (bank0/8749.c:91, 8B14.c:136, 8C46.c:53, 8F20.c:97, 9334.c:30,
    # 9CA6.c:58, B38E.c:28; bank1/8300.c:23, 8F6B.c:37, 9004.c:37, 9007.c:36,
    # 9008.c:39, A12D.c:27, A916.c:27; common/3DA8.c:12), 164 `!=`, 1 `<`, and
    # one bare right-hand-side read at bank0/8F20.c:98. All 181 are reads, and
    # no function writes it. This is the entry that would have caught the
    # original bug, and it is the machine-readable form of the "**No writer**"
    # prose registers.yaml already carried.
    "0x0440": {"read": 181, "write": 0, "read+write": 0, "passed-to-call": 0,
               "address-taken": 0, "writers": 0},
    # 17 references: 14 `==` inside bank0/D091.c's dispatch test (lines 30, 34,
    # 56, 57, 60, 61 and 62 -- the later ones are multi-line boolean chains,
    # three occurrences to a line), the dispatch argument itself at
    # bank0/D091.c:69, a `= 0xff` at bank0/D281.c:18 and a `= 0` at
    # bank0/D289.c:17. Two stores in two functions, and the dispatch argument
    # is `passed-to-call` rather than a read. The worst-looking row the phantom
    # writers produced: it read as 0 read / 13 write / 3 read+write, a pure
    # write-side dispatch byte.
    "0x0860": {"read": 14, "write": 2, "read+write": 0, "passed-to-call": 1,
               "address-taken": 0, "writers": 2},
    # 12 references and zero `==` adjacent to the address. Four are genuine
    # read-modify-writes at bank1/F11C.c:21, F11F.c:23, F2CA.c:23, F2F3.c:25
    # (`DAT_EXTMEM_0443 = (DAT_EXTMEM_0443 & 7) ± 1`). The other eight are
    # reads: four in the `((DAT_EXTMEM_0443 & 7) == 7)` / `!= 0` guard shape,
    # and four as the right-hand side of those same read-modify-writes, where
    # the operator is not adjacent to the address and was already a read.
    # Unchanged by the `==` fix, and it fails if that fix ever over-reaches: a
    # self-referencing store is a real `read+write`, not a comparison.
    "0x0443": {"read": 8, "write": 0, "read+write": 4, "passed-to-call": 0,
               "address-taken": 0, "writers": 4},
    # One shared writer, bank1/94FA.c:48 and :49, which is what holds a 16-bit
    # store's halves together when the touching-function relation scores them
    # 0.07 (xdata-register-map.md §4.2's worked example). 0x04FE's other ten
    # references are the `>> n & 1` bit-test and `-1 <` shapes.
    "0x04FE": {"read": 10, "write": 1, "read+write": 0, "passed-to-call": 0,
               "address-taken": 0, "writers": 1},
    "0x04FF": {"read": 6, "write": 1, "read+write": 0, "passed-to-call": 0,
               "address-taken": 0, "writers": 1},
}

# Literal Ghidra-shaped lines through classify(), and the bucket each must
# come back as. The rejection of `==` is pinned here rather than left to the
# docstring, and it survives the tree changing: these are strings, not a count
# of the committed files. The relational cases are here because they were
# already outside ASSIGN -- an assertion that measures that is worth more than
# a comment asserting it, and the last entry is a real name out of
# xdata-symbols.csv so the fix is pinned for the symbol spelling too, which the
# committed tree happens never to exercise.
CLASSIFIER_SHAPE = (
    ("DAT_EXTMEM_0440 = 0;", "write"),
    ("DAT_EXTMEM_0440 = DAT_EXTMEM_0440 & 0x0f;", "read+write"),
    # These two are `write` and should read as `read+write`: `read+write` is
    # decided syntactically -- "the right-hand side of the `=` names this
    # address" -- and `&=` compresses the self-reference out of the right-hand
    # side, so the test cannot see it. Pinned as measured rather than as
    # intended, because the shape does not occur: no compound assignment
    # operator follows a `DAT_EXTMEM_` token anywhere in the committed tree,
    # which is why the module docstring cites the spelled-out form Ghidra
    # actually emits. So this costs no bucket and is a follow-up, not a fix
    # folded silently into issue #178.
    ("DAT_EXTMEM_0440 &= 0x0f;", "write"),
    ("DAT_EXTMEM_0440 |= 0x0f;", "write"),
    ("if (DAT_EXTMEM_0440 == 0) {", "read"),
    ("if (DAT_EXTMEM_0440 == 0) {\n}", "read"),
    ("if (DAT_EXTMEM_0440 != 0) {", "read"),
    ("if (DAT_EXTMEM_0440 <= 7) {", "read"),
    ("if (DAT_EXTMEM_0440 >= 7) {", "read"),
    ("if (DAT_EXTMEM_0440 < 7) {", "read"),
    ("if (DAT_EXTMEM_0440 > 7) {", "read"),
    # No `case DAT_EXTMEM_xxxx:` occurs in the tree either, but the issue
    # asks for the switch shape to be measured rather than assumed, so it is.
    ("switch (DAT_EXTMEM_0440) {\ncase 1:\n}", "read"),
    ("*DAT_EXTMEM_0440 = 5;", "read"),
    ("param_1 = DAT_EXTMEM_0440;", "read"),
    ("&DAT_EXTMEM_0440", "address-taken"),
    ("switch_case_dispatch(DAT_EXTMEM_0440);", "passed-to-call"),
    # The symbol spelling, which the tree never spells a comparison in today.
    ("if (CPU_TEMP == 0) {", "read"),
    ("CPU_TEMP = 0;", "write"),
)

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"//[^\n]*")
IDENT_CALL = re.compile(r"\b([A-Za-z_][A-Za-z_0-9]*)\s*\(")
IDENT_TAIL = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)$")
# The `scope:0xADDR=name [type]` label func_label() writes, recovered so the
# self-test can check a cluster's function names against index.csv.
FUNC_KEY = re.compile(r"\b(bank0|bank1|common|pd):0x([0-9A-F]{4})=")
# Ghidra's third spelling, read only to name the blind spot in the self-test.
CODE_TOKEN = re.compile(r"DAT_CODE_([0-9a-fA-F]{4})")
BOUNDARY = ";{}"
# An `.asm` opcode column is up to three bytes wide with `-` standing in for the
# absent ones, so it is matched as a token rather than by column.
ASM_OPCODE = re.compile(r"^[0-9a-f]{2}$|^-+$")
# `DPTR,#0xff80` in the low window and `DPTR,#0xb8` in the low blocks: the
# exporter prints the minimum digits, so the width is 1-4 and not fixed.
DPTR_IMM = re.compile(r"^DPTR, #(0x[0-9a-f]{1,4})$")
# Control transfers, which end a straight-line window: past one of these the
# next instruction is not necessarily the one that runs.
XSPACE_FLOW = {"lcall", "ljmp", "acall", "ajmp", "sjmp", "jmp", "ret", "reti",
               "jb", "jbc", "jnb", "jc", "jnc", "jz", "jnz", "djnz"}


def hexaddr(addr: int) -> str:
    return f"0x{addr:04X}"


def bare(addr: str) -> str:
    """`0x1978` or `1978` -> `1978`, upper. index.csv and
    ghidra-functions.csv disagree about the prefix and the case."""
    a = addr.strip()
    if a[:2].lower() == "0x":
        a = a[2:]
    return a.upper()


def strip_comments(text: str) -> str:
    """Blank out comments, keeping every newline.

    The decompiled C carries this repository's own annotations in block
    comments, and an annotation that quotes `DAT_EXTMEM_0a56 = DAT_EXTMEM_1919`
    or `CPU_TEMP` would otherwise be counted as the firmware touching it.
    Blanking rather than deleting keeps the offsets -- and the line numbers a
    reader is given -- honest."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = BLOCK_COMMENT.sub(blank, text)
    return LINE_COMMENT.sub(lambda m: " " * len(m.group(0)), text)


def body_of(text: str) -> str:
    """The function body: everything after the lone `{` that opens it.

    Ghidra writes the signature, a blank line, then `{` at column 0. Scanning
    the body rather than the file is what keeps the signature's own `name(`
    from reading as a call, and keeps a decompiled local's address from
    borrowing the enclosing function's name."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "{" and not line.startswith(" "):
            return "\n".join(lines[i + 1:])
    return text


def rhs_of(text: str, pos: int) -> str:
    """The right-hand side of an assignment starting at `pos` (the `=`).

    Ends at the statement's own separator -- `;`, a brace, a top-level `,` from
    a comma expression, or the `)` that closes the enclosing paren -- so the
    self-reference test below cannot see the *next* statement's operand."""
    depth = 0
    for i in range(pos, len(text)):
        c = text[i]
        if c in "([":
            depth += 1
        elif c in ")]":
            if depth == 0:
                return text[pos:i]
            depth -= 1
        elif depth == 0 and (c in BOUNDARY or c == ","):
            return text[pos:i]
    return text[pos:]


def store_target(text: str, start: int, end: int) -> bool:
    """True if this occurrence is the assignment target itself.

    Every `=`-taking occurrence in the committed tree has `;`, `{`, `}`, `(`,
    `:`, `,` or `*` immediately before it -- Ghidra never emits a store
    through a larger lvalue -- so "the `=` follows" is the whole test.

    Two things are then excluded, both about what the `=` belongs to rather
    than to the lvalue. `*` before the address: a store through a dereference
    is a store to wherever the pointer points, not to this address.
    `==` after it: that is a comparison, and a comparison uses the value
    without storing one."""
    nxt = text[end:]
    stripped = nxt.lstrip()
    if not any(stripped.startswith(a) for a in ASSIGN):
        return False
    # A separate test rather than a reordering of ASSIGN, because the two
    # exclusions are unrelated and `==` is by far the commoner of them:
    # 838 occurrences in the committed tree against two dereference stores.
    if stripped.startswith("=="):
        return False
    left = text[:start].rstrip()
    return not (left and left[-1] == "*")


def read_asm(program: str) -> dict:
    """{function: [(at, mnemonic, operands)]} for one program's `.asm` files.

    Kept per function rather than flattened, because a window that ran from the
    end of one file to the start of the next would pair a pointer seed with a
    dereference that is not reachable from it.

    The opcode column is consumed as tokens, not by column: the exporter pads
    with `-` to a fixed width, so a fixed three-column parse drops every one-
    and two-byte instruction -- which is `movx` and `inc DPTR`, precisely the
    two the address-space discrimination below is made of.

    **The framing is not checked here, and is checked where it can be.** One
    listing row is one decoded instruction, but whether the decoder started on
    an instruction boundary is `disasm8051.py`'s question and its `--self-test`
    is the oracle; 149 of the 45,537 listing lines in this tree are not
    contiguous, because a listing legitimately includes jump tables and string
    data, so a blanket contiguity assertion would be false. `xdata_register_map
    --self-test` and `disasm8051.py --self-test` are both cheap and both run
    without Ghidra, the image or the network."""
    out = {}
    d = os.path.join(DECOMPILED, program)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".asm"):
            continue
        seq = []
        with open(os.path.join(d, name)) as f:
            for line in f:
                if line.startswith(";") or not line.strip():
                    continue
                tok = line.split()
                i, width = 1, 0
                while i < len(tok) and width < 3 and ASM_OPCODE.match(tok[i]):
                    i += 1
                    width += 1
                seq.append((tok[0], tok[i], " ".join(tok[i + 1:]).strip()))
        out[name[:-4]] = seq
    return out


def seed_of(mnem: str, oper: str):
    """The XDATA address a `mov DPTR,#imm16` loads, or None."""
    m = DPTR_IMM.match(oper) if mnem == "mov" else None
    return int(m.group(1), 16) if m else None


def dptr_operand_only(pd_asm, addrs) -> list:
    """Instructions in the PD tree that name one of `addrs` *without* being a
    `mov DPTR` of it, as `(function, at, mnemonic, operands)`.

    This is the negative half of the discrimination, and it is the half that
    tests the issue's premise rather than restating it. A direct address is one
    byte and a bit address is one byte, so naming a `0xFFxx` value in either
    is not possible -- but "not possible" is a claim about the opcode map, and
    the way to hold the committed listing to it is to require that the *only*
    instructions naming these ten are `mov DPTR` of them.

    It would also catch a `lcall 0xFF80`, and that is intended rather than
    incidental: a site where the same number is a CODE target is a fact about
    the image that the census would otherwise silently absorb, and
    `annotations/pd-xdata-overlap.md` 5.5 is the existing record of a `MOV
    DPTR,#imm16` that turned out to be exactly that."""
    want = {a for a in addrs}
    out = []
    for stem, seq in pd_asm.items():
        for at, mnem, oper in seq:
            for tok in re.findall(r"0x[0-9a-f]{1,4}", oper.lower()):
                if int(tok, 16) not in want:
                    continue
                if mnem == "mov" and seed_of(mnem, oper) in want:
                    continue
                out.append((stem, at, mnem, oper))
    return out


def clobbers_dptr(mnem: str, oper: str) -> bool:
    """True if this instruction can move DPTR without being one of the two the
    continuation walk allows.

    On an 8051 the full set is `MOV DPH/DPL,...` (`0x75` with `0x83`/`0x82`, and
    the register-to-register forms), `INC`/`DEC DPH/DPL` (`0xA5`-`0xA7`,
    `0x85`-`0x87`), `POP DPH/DPL` and `MOV DPTR,#imm16` -- the last because a
    callee's `push dph / push dpl ... pop dpl / pop dph` idiom restores a
    saved pointer. `PUSH` cannot move DPTR on its own, but the `POP` that
    eventually does is caught."""
    if mnem in ("inc", "dec", "pop"):
        return oper in ("DPH", "DPL")
    if mnem == "mov":
        return oper.split(",")[0].strip() in ("DPH", "DPL", "DPTR")
    return False


def xdata_space(asm, addr: int):
    """How `addr` is reached in one program's `.asm` tree, or None.

    Two forms, and the second is the reason this reads the disassembly rather
    than scanning the image for `90 hi lo`:

        ("literal", function, at)   a `mov DPTR,#imm16` naming `addr`, whose
                                    pointer a `movx` then dereferences
        ("inc", function, at)       an `inc DPTR` walking a seed one byte below
                                    `addr` to a `movx` that dereferences the
                                    walked pointer

    0xFFC1, 0xFFD1 and 0xFFDB are only ever the second, so a byte scan finds
    their seeds and cannot find them at all. The window the walk accepts is the
    straight-line run from the seed to that `movx`, with no control transfer in
    it, no second `inc DPTR`, and nothing in it that can move DPTR otherwise.

    **The limit, stated rather than hidden.** That is a bounded window check and
    not a DPTR dataflow: the `.asm` is linear and not control-flow aware, so a
    seed on one arm of a branch could in principle be paired with a `movx` on
    another. `pd-xdata-overlap.md` §6 records the same limit for every window
    in this repository's disassembly. None of the three continuations here is
    near a branch -- `pd/EFB9.asm` is four straight-line instructions, the
    other two three -- and `--self-test` prints the windows it matched, so a
    future match that is not straight-line is visible rather than trusted.

    None is "not found by this method", never "absent"."""
    for stem, seq in asm.items():
        for i, (at, mnem, oper) in enumerate(seq):
            seed = seed_of(mnem, oper)
            if seed is None or not (0 <= addr - seed <= 1):
                continue
            # Both forms require the `movx`. `mov DPTR,#imm16` on its own only
            # loads a pointer, and `ec/annotations/pd-xdata-overlap.md` 5.4 is
            # the case in this repository where a seed hands DPTR to an index
            # helper and the byte written lands somewhere else entirely -- so a
            # seed with no dereferencing `movx` behind it has not been shown to
            # address anything, and saying it has would be the overclaim this
            # check exists to avoid.
            walked = 0
            for j in range(i + 1, min(i + 1 + XSPACE_WINDOW, len(seq))):
                _at, m2, o2 = seq[j]
                if m2 in XSPACE_FLOW:
                    break
                if m2 == "inc" and o2 == "DPTR":
                    walked += 1
                    if walked > 1:
                        break
                    continue
                if clobbers_dptr(m2, o2):
                    break
                if m2 == "movx" and "@DPTR" in o2:
                    if walked == 1 and seed == addr - 1:
                        return ("inc", stem, at)
                    if walked == 0 and seed == addr:
                        return ("literal", stem, at)
                    # A dereference of the seed itself says nothing about the
                    # address one byte up, and an address's own seed says
                    # nothing about a walk past it. Keep looking.
    return None


def enclosing_call(text: str, start: int, func_names):
    """The call whose argument list contains `start`, or None.

    Walks left to the innermost enclosing `(` and out from there, stopping at
    the statement's last `;`/`{`/`}`. A cast's paren is not a call, so the
    walk continues past it: `FUN_CODE_x((char *)DAT_EXTMEM_y)` is a handoff."""
    depth = 0
    for i in range(start - 1, -1, -1):
        c = text[i]
        if c == ")":
            depth += 1
        elif c == "(":
            if depth:
                depth -= 1
                continue
            ident = IDENT_TAIL.search(text[:i])
            if ident and ident.group(1) in func_names:
                return ident.group(1)
        elif depth == 0 and c in BOUNDARY:
            return None
    return None


def classify(text: str, start: int, end: int, addr: str, func_names) -> str:
    """One occurrence -> one of BUCKETS. See the module docstring for why
    `passed-to-call` and `address-taken` are buckets of their own."""
    left = text[:start].rstrip()
    if left.endswith("&"):
        return "address-taken"
    if store_target(text, start, end):
        eq = text.index("=", end)
        return "read+write" if addr in rhs_of(text, eq) else "write"
    if enclosing_call(text, start, func_names):
        return "passed-to-call"
    return "read"


def callees_of(body: str, func_names) -> list:
    """Routines this function's body names in a call position.

    Membership in `index.csv`'s name set is the filter, so Ghidra's
    `CONCAT11`/`CARRY1`/`halt_baddata` pseudomacros are not callees. A nested
    call counts for the enclosing function as well as for the one it sits
    inside, which over-counts depth and is the usual reading of a call graph
    built out of a decompile rather than a linker map."""
    return sorted({m.group(1) for m in IDENT_CALL.finditer(body)
                   if m.group(1) in func_names})


def load_index():
    """(funcs, by_file) from index.csv.

    `funcs` is the (program, addr) -> row map the census and the cluster table
    both name from; `by_file` is out_file -> the same row, so a `.c` is read
    once and its scope comes from the exporter's own record."""
    funcs = {}
    by_file = {}
    with open(INDEX_CSV, newline="") as f:
        for row in csv.DictReader(f):
            row["key"] = (row["program"], bare(row["addr"]))
            funcs[row["key"]] = row
            by_file[row["out_file"]] = row
    return funcs, by_file


def load_names(funcs) -> dict:
    """Merge ec/annotations/ghidra-functions.csv over index.csv.

    The annotation is the hand name and type; where a function was never
    annotated the exporter's own name stands and the type is left empty rather
    than invented. The two agree on every address they share (the self-test
    says so), so this is belt and braces, not a merge rule."""
    out = {k: (r["name"], r["type"]) for k, r in funcs.items()}
    with open(ANNOT_CSV, newline="") as f:
        for row in csv.DictReader(f):
            key = (row["scope"], bare(row["addr"]))
            if key in out:
                out[key] = (row["name"], row["type"])
    return out


def load_symbols() -> dict:
    """addr -> name from the generated symbol table. Read for display only:
    the table is generated and a name here implies no `status:` anywhere
    (ec/tools/gen_xdata_symbols.py's own preamble). It is also the list of
    names the decompile was built with, so it is the second spelling the
    census has to recognise."""
    out = {}
    with open(SYMBOLS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["addr"], 0)] = row["name"]
    return out


def occurrence_re(symbols: dict):
    """One regex over both spellings the decompiled C uses.

    Group 1 is the four hex digits of a `DAT_EXTMEM_xxxx` token, group 2 the
    symbol name when the exporter had one. The alternation is longest-first
    and `\b`-terminated, so `AP_OEM` cannot match inside `AP_OEM_6`; the
    length sort is belt and braces on top of that.

    A symbol name is matched as a bare identifier, which is only safe because
    none of the 101 collides with a decompiled local, a parameter or a
    function -- the self-test re-checks that rather than assuming it."""
    names = sorted(symbols.values(), key=len, reverse=True)
    alt = "|".join(re.escape(n) for n in names)
    return re.compile(r"DAT_EXTMEM_([0-9a-fA-F]{4})|\b(" + alt + r")\b")


def check_file_set(by_file) -> int:
    """The census and the committed .c files still describe each other.

    A `.c` the index does not know would be a function the census never reads,
    and an index row with no `.c` a reference count attributed to a function
    that cannot be found. Either is a failure, not a note."""
    on_disk = set()
    for program in MAIN_PROGRAMS + (PD_PROGRAM,):
        d = os.path.join(DECOMPILED, program)
        if not os.path.isdir(d):
            print(f"{d} is missing", file=sys.stderr)
            return 1
        for name in os.listdir(d):
            if name.endswith(".c"):
                on_disk.add(f"{program}/{name}")
    listed = set(by_file)
    problems = 0
    for orphan in sorted(on_disk - listed):
        print(f"decompiled/{orphan}: on disk but not in {INDEX_CSV}", file=sys.stderr)
        problems += 1
    for missing in sorted(listed - on_disk):
        print(f"decompiled/{missing}: in {INDEX_CSV} but not on disk", file=sys.stderr)
        problems += 1
    return problems


def blank_entry():
    """One address's running tally.

    `funcs` is the ref count per function (the incidence matrix the clustering
    runs on) and `dirs` is which buckets *that function* used, because a
    reader count derived from the address's own buckets would call every one of
    0x06E6's 50 touchers a writer when 3 of its 72 references write it."""
    return {"refs": 0, "buckets": collections.Counter(),
            "funcs": collections.Counter(), "dirs": collections.defaultdict(set),
            "spellings": set()}


def absorb(entry, src):
    """Fold one file's (or one scope's) contribution into an address."""
    entry["refs"] += src["refs"]
    entry["buckets"].update(src["buckets"])
    entry["funcs"].update(src["funcs"])
    entry["spellings"].update(src["spellings"])
    for f, buckets in src["dirs"].items():
        entry["dirs"][f].update(buckets)
    return entry


def touches(entry, bucket: str):
    """The functions of `entry` that used `bucket` themselves."""
    return {f for f, buckets in entry["dirs"].items() if bucket in buckets}


def scan(by_file, names, func_names, symbols):
    """(per-program census, call graph, raw occurrence count) over the tree.

    An address is reached from many files in one program, so the per-file
    counts accumulate into the program's entry rather than replacing it.

    The raw count is what the files say before comments are blanked, kept so
    the self-test can pin the difference the ORACLE block records rather than
    leave it as a claim in prose."""
    pattern = occurrence_re(symbols)
    by_name = {name: addr for addr, name in symbols.items()}
    census = {p: {} for p in MAIN_PROGRAMS + (PD_PROGRAM,)}
    calls = {}
    raw = collections.Counter({s: 0 for s in SPELLINGS})
    for out_file, row in by_file.items():
        path = os.path.join(DECOMPILED, out_file)
        with open(path) as f:
            source = f.read()
        for m in pattern.finditer(source):
            raw["DAT_EXTMEM" if m.group(1) is not None else "symbol"] += 1
        text = strip_comments(source)
        key = row["key"]
        calls[key] = set(callees_of(body_of(text), func_names))
        per_addr = collections.defaultdict(blank_entry)
        for m in pattern.finditer(text):
            if m.group(1) is not None:
                addr, spelling = int(m.group(1), 16), "DAT_EXTMEM"
            else:
                addr, spelling = by_name[m.group(2)], "symbol"
            bucket = classify(text, m.start(), m.end(), m.group(0), func_names)
            entry = per_addr[addr]
            entry["refs"] += 1
            entry["buckets"][bucket] += 1
            entry["funcs"][key] += 1
            entry["dirs"][key].add(bucket)
            entry["spellings"].add(spelling)
        for addr, entry in per_addr.items():
            absorb(census[row["program"]].setdefault(addr, blank_entry()), entry)
    return census, calls, raw


def merge_group(census, programs):
    """One group's address -> entry, summing the scopes it is made of.

    A `common` function also exists in each bank's window (`also_in` in
    index.csv), so a common-area file is read once and its references belong
    to the main EC once; summing here is over *different* functions, never over
    a repeat of one."""
    out = {}
    for program in programs:
        for addr, entry in census[program].items():
            absorb(out.setdefault(addr, blank_entry()), entry)
    return out


def jaccard(a, b) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def similar(a: int, b: int, group: dict, writers: dict, threshold: float) -> bool:
    """Two addresses are neighbours if they share their touching-function set
    *or* their writer set at `threshold`.

    The second relation is what keeps a block written by one routine and read
    by disjoint callers together: those two addresses share no reader, so the
    first relation alone scores them 0 and splits a multi-byte store's halves
    apart. `writers` is empty when the caller dropped the axis, which is how
    `--no-writer-axis` measures what it is worth."""
    ta, tb = set(group[a]["funcs"]), set(group[b]["funcs"])
    if ta and tb and jaccard(ta, tb) >= threshold:
        return True
    wa, wb = writers.get(a, set()), writers.get(b, set())
    return bool(wa and wb and jaccard(wa, wb) >= threshold)


def components(group, threshold, writers_on: bool = True):
    """Connected components of the address similarity graph.

    Components, not a greedy cover: the relation is not transitive and a
    greedy pass would make the output depend on address order. Every address
    lands in exactly one component, and one with no neighbour is a component
    of size 1 rather than a drop -- the caller has to be able to account for
    all of them."""
    addrs = sorted(group)
    # Narrower than the touching-function set, which is the point: the writer
    # axis is what keeps a block written by one routine and read by disjoint
    # callers together.
    writers = ({a: touches(group[a], "write") | touches(group[a], "read+write")
                for a in addrs} if writers_on else {})
    parent = {a: a for a in addrs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_func = collections.defaultdict(list)
    by_writer = collections.defaultdict(list)
    for a in addrs:
        for f in group[a]["funcs"]:
            by_func[f].append(a)
        for f in writers.get(a, ()):
            by_writer[f].append(a)
    for buckets in (by_func, by_writer):
        for members in buckets.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    if find(members[i]) == find(members[j]):
                        continue
                    if similar(members[i], members[j], group, writers, threshold):
                        parent[find(members[i])] = find(members[j])
    out = collections.defaultdict(list)
    for a in addrs:
        out[find(a)].append(a)
    return out


def span_groups(addrs) -> dict:
    """Maximal runs of consecutive touched addresses -> a range label.

    Reported, never merged into a cluster. Adjacent addresses are often one
    multi-byte store, and `gen_xdata_symbols.py` names those `_0`/`_1` by
    address order precisely because it refuses to bake a byte order into a
    symbol -- merging on contiguity would make that same claim invisibly."""
    out = {}
    ordered = sorted(addrs)
    start = prev = ordered[0]
    for a in ordered[1:]:
        if a != prev + 1:
            for x in range(start, prev + 1):
                out[x] = f"{hexaddr(start)}-{hexaddr(prev)}"
            start = a
        prev = a
    for x in range(start, prev + 1):
        out[x] = f"{hexaddr(start)}-{hexaddr(prev)}"
    return out


def func_label(key, names):
    name, ftype = names.get(key, (key[0] + "_" + key[1], ""))
    return f"{key[0]}:0x{key[1]}={name}" + (f" [{ftype}]" if ftype else "")


def resolve_callee(name, caller_program, funcs):
    """A callee name -> `scope:0xaddr`, preferring the caller's own program.

    Fifteen names in index.csv are carried by more than one scope
    (`FUN_CODE_d946` is both a bank0 and a bank1 routine, `ret_stub` appears in
    both). A bank caller is unambiguous; a `common` caller is not, and there
    the first scope listed is shown rather than a guess, with the others named
    so the reader sees the ambiguity instead of inheriting it."""
    hits = [k for k in funcs if k[1] and funcs[k]["name"] == name]
    same = [k for k in hits if k[0] == caller_program]
    chosen = (same or hits)
    if not chosen:
        return f"{name}@unresolved"
    if len(chosen) == 1:
        return f"{chosen[0][0]}:0x{chosen[0][1]}"
    return f"{chosen[0][0]}:0x{chosen[0][1]} (also {' '.join(k[0] + ':0x' + k[1] for k in chosen[1:])})"


def build(funcs, names, symbols, census, calls, threshold):
    """The two row sets the CSVs render, plus the summary the modes print."""
    groups = {g: merge_group(census, PROGRAM_COL[g]) for g in GROUPS}
    program_of = {}
    for g in GROUPS:
        for a in groups[g]:
            program_of.setdefault(a, []).append(g)

    clusters = {g: components(groups[g], threshold) for g in GROUPS}
    # Numbering is by size, then references, then lowest address, so the ids
    # are stable across regenerations and `main-01` is the same cluster today
    # and after a re-run.
    cluster_id = {}
    cluster_rows = []
    for g in GROUPS:
        ordered = sorted(clusters[g].values(),
                         key=lambda v: (-len(v), -sum(groups[g][a]["refs"] for a in v), v[0]))
        for n, members in enumerate(ordered, 1):
            cid = f"{g}-{n:03d}"
            for a in members:
                cluster_id[(g, a)] = cid
            cluster_rows.append(cluster_rows_build(g, cid, members, groups[g], names,
                                                   funcs, calls, symbols))

    spans = {g: span_groups(groups[g]) for g in GROUPS}
    register_rows = []
    all_addrs = sorted({a for g in GROUPS for a in groups[g]})
    for addr in all_addrs:
        seen = program_of[addr]
        if len(seen) > 1:
            combined = blank_entry()
            for g in seen:
                absorb(combined, groups[g][addr])
            entry, primary = combined, "main-ec" if "main-ec" in seen else "pd"
        else:
            g = seen[0]
            entry, primary = groups[g][addr], g
        funcs_touched = set(entry["funcs"])
        readers = touches(entry, "read") | touches(entry, "read+write")
        writers = touches(entry, "write") | touches(entry, "read+write")
        cid = cluster_id.get((primary, addr))
        register_rows.append({
            "addr": hexaddr(addr),
            "program": seen[0] if len(seen) == 1 else "both",
            # A named address is one the decompiler was given a symbol for, so
            # its EC references read `CPU_TEMP` and the issue's `DAT_EXTMEM_`
            # grep never saw them. 0x07D8 and its two siblings are named in the
            # EC and written as `DAT_EXTMEM_` in the PD image, so both show.
            "spelled_as": "+".join(s for s in ("symbol", "DAT_EXTMEM")
                                   if s in entry["spellings"]),
            "span_group": spans[primary][addr],
            "cluster_id": cid or "",
            "refs": entry["refs"],
            "read": entry["buckets"].get("read", 0),
            "write": entry["buckets"].get("write", 0),
            "read+write": entry["buckets"].get("read+write", 0),
            "passed-to-call": entry["buckets"].get("passed-to-call", 0),
            "address-taken": entry["buckets"].get("address-taken", 0),
            "readers": len(readers),
            "writers": len(writers),
            "functions_touched": len(funcs_touched),
            "single_function": "yes" if len(funcs_touched) == 1 else "no",
            "name": symbols.get(addr, ""),
            "functions": "; ".join(func_label(f, names) for f in sorted(funcs_touched)),
        })
    return register_rows, cluster_rows, groups


def cluster_rows_build(g, cid, members, group, names, funcs, calls, symbols):
    """One row of xdata-clusters.csv.

    `shared_functions` is the subset touching two or more of the cluster's
    addresses -- the co-occurrence that put them together. `callees` is the
    call-graph axis: the routines the most of those functions call, capped at
    TOP_CALLEES with the overflow counted in the cell."""
    touching = collections.Counter()
    for a in members:
        for f in group[a]["funcs"]:
            touching[f] += 1
    shared = [f for f, n in touching.items() if n > 1]
    shared.sort(key=lambda f: (-touching[f], f))
    # Sorted, not set-iteration order: `calls` holds sets, and Python randomises
    # string hashing per process, so an unsorted walk here would make
    # most_common()'s tie-breaking -- and so the committed CSV -- differ
    # between two runs of the same tree.
    callee_hits = collections.Counter()
    for f in sorted(touching):
        for callee in sorted(calls.get(f, ())):
            callee_hits[callee] += 1
    top = callee_hits.most_common(TOP_CALLEES)
    callees = "; ".join(
        f"{resolve_callee(name, g, funcs)} [{n}/{len(touching)}]"
        for name, n in top)
    rest = len(callee_hits) - len(top)
    if rest > 0:
        callees += f" (+{rest} more called by the cluster's functions)"
    refs = sum(group[a]["refs"] for a in members)
    named = [a for a in members if a in symbols]
    return {
        "cluster_id": cid,
        "program": g,
        "size": len(members),
        "refs": refs,
        "addrs": " ".join(hexaddr(a) for a in members),
        "addr_range": (f"{hexaddr(members[0])}-{hexaddr(members[-1])}"
                       if len(members) > 1 else hexaddr(members[0])),
        "functions_touched": len(touching),
        "shared_functions": "; ".join(func_label(f, names) for f in shared),
        "callees": callees,
        "named_addrs": " ".join(hexaddr(a) for a in named),
    }


def render(rows, columns) -> str:
    """CSV text with \\n endings and no trailing blank lines, and nothing in
    it that is not a column -- the tool that wrote the file is the tool that
    reads it back, with csv.DictReader (ec/README.md's house rule)."""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n",
                       extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def diff(name, on_disk, generated) -> int:
    """First differing line named, the way gen_xdata_symbols.py does."""
    print(f"{name} differs from a fresh generation "
          f"({len(on_disk.splitlines())} on disk vs "
          f"{len(generated.splitlines())} generated) -- run without --check "
          "to rewrite", file=sys.stderr)
    for i, (a, b) in enumerate(zip(on_disk.splitlines(), generated.splitlines())):
        if a != b:
            print(f"  line {i + 1}: on disk {a!r} != generated {b!r}",
                  file=sys.stderr)
            break
    return 1


def generate(args):
    """(register_rows, cluster_rows, groups), or None after printing why."""
    funcs, by_file = load_index()
    problems = check_file_set(by_file)
    if problems:
        return None
    names = load_names(funcs)
    symbols = load_symbols()
    func_names = {r["name"] for r in funcs.values()}
    census, calls, _raw = scan(by_file, names, func_names, symbols)
    register_rows, cluster_rows, groups = build(funcs, names, symbols, census,
                                               calls, args.threshold)
    return register_rows, cluster_rows, groups


def outputs(args, built):
    """[(rows, columns, path, text)] for the two CSVs, in write order.

    Both modes go through this one list so `--check` and the writing default
    can never disagree about what a fresh generation is -- which is the whole
    reproducibility claim the two CSVs rest on."""
    register_rows, cluster_rows, _ = built
    out = []
    for rows, columns, path in ((register_rows, REGISTER_COLUMNS, args.out_registers),
                                (cluster_rows, CLUSTER_COLUMNS, args.out_clusters)):
        out.append((rows, columns, path, render(rows, columns)))
    return out


def check(args) -> int:
    built = generate(args)
    if built is None:
        return 1
    rc = 0
    for rows, _columns, path, text in outputs(args, built):
        try:
            with open(path, newline="") as f:
                on_disk = f.read()
        except FileNotFoundError:
            print(f"{path} does not exist -- run without --check to write it",
                  file=sys.stderr)
            rc = 1
            continue
        if on_disk != text:
            rc = diff(path, on_disk, text)
        else:
            print(f"{path}: {len(rows)} rows match a fresh generation from the "
                  f"committed tree at threshold {args.threshold}")
    return rc


def write(args) -> int:
    built = generate(args)
    if built is None:
        return 1
    register_rows, cluster_rows, groups = built
    for _rows, _columns, path, text in outputs(args, built):
        with open(path, "w", newline="") as f:
            f.write(text)
        print(f"wrote {path}: {text.count(chr(10)) - 1} rows")
    for g in GROUPS:
        addrs = groups[g]
        print(f"  {g}: {len(addrs)} distinct addresses, "
              f"{sum(e['refs'] for e in addrs.values())} references, "
              f"{sum(1 for r in cluster_rows if r['program'] == g)} clusters at "
              f"threshold {args.threshold}")
    return 0


def self_test(args) -> int:
    """Known-answer run over the committed tree. No image, no Ghidra, no
    network -- every assertion is re-derivable from the files this tool reads.

    The oracle is issue #132's published numbers *and* this tool's correction
    to them, so a change to what counts as a reference fails here rather than
    quietly making the report wrong."""
    funcs, by_file = load_index()
    names = load_names(funcs)
    symbols = load_symbols()
    func_names = {r["name"] for r in funcs.values()}
    census, calls, raw = scan(by_file, names, func_names, symbols)
    groups = {g: merge_group(census, PROGRAM_COL[g]) for g in GROUPS}
    ok = True

    def check(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
        if not cond:
            ok = False

    def of(g, spelling):
        return {a: e for a, e in groups[g].items() if e["spellings"] == {spelling}}

    print("xdata_register_map.py --self-test")
    check("index.csv and the committed .c files still describe each other",
          not check_file_set(by_file))
    check("the annotation CSV and index.csv agree on every address they share",
          all(names[k][0] == r["name"] for k, r in funcs.items()))
    # The occurrence regex matches a symbol name as a bare identifier, which is
    # only a register access if nothing else in the decompiled C claims the
    # name. None of the 101 does, and a new local called TRIGGER would quietly
    # inflate the census if one ever did.
    check("no generated symbol name is also a function, parameter or local in "
          "the decompiled tree",
          not (set(symbols.values()) & func_names))

    bad_buckets = [a for g in GROUPS for a, e in groups[g].items()
                   if set(e["buckets"]) - set(BUCKETS)]
    check(f"every reference is in one of the five buckets {list(BUCKETS)}",
          not bad_buckets)
    check("bucket counts sum to the reference count for every address",
          all(sum(e["buckets"].values()) == e["refs"]
              for g in GROUPS for e in groups[g].values()))
    fired = collections.Counter()
    for g in GROUPS:
        for e in groups[g].values():
            fired.update(e["buckets"])
    check("passed-to-call and address-taken both fire, so the two unresolved-"
          "direction buckets are not dead vocabulary",
          fired["passed-to-call"] > 0 and fired["address-taken"] > 0)

    # The narrow direction oracle: literal lines, so it pins the `==` rejection
    # itself and cannot be satisfied by a tree that happens to contain no
    # comparisons. The wide one is HAND_CHECKED below, the only direction check
    # in this file that compares against something outside the tool.
    pattern = occurrence_re(symbols)
    for snippet, expected in CLASSIFIER_SHAPE:
        m = pattern.search(snippet)
        check(f"classify({snippet!r}) is {expected!r}",
              m is not None and classify(snippet, m.start(), m.end(),
                                         m.group(0), func_names) == expected)

    def tally(g, spelling=None):
        sub = groups[g] if spelling is None else of(g, spelling)
        return len(sub), sum(e["refs"] for e in sub.values())

    distinct = {g: tally(g) for g in GROUPS}
    refs = {g: distinct[g][1] for g in GROUPS}
    both = {a for a in groups["main-ec"] if a in groups["pd"]}
    pd_only = set(groups["pd"]) - both
    total_distinct = len(set(groups["main-ec"]) | set(groups["pd"]))
    total_refs = refs["main-ec"] + refs["pd"]
    extmem = {g: tally(g, "DAT_EXTMEM") for g in GROUPS}
    syms = {g: tally(g, "symbol") for g in GROUPS}
    # The two spellings overlap between programs on a different set of
    # addresses than the full census's `both`, so it gets its own figure
    # rather than reusing that one.
    extmem_both = (ORACLE["extmem_main_distinct"] + ORACLE["extmem_pd_distinct"]
                   - ORACLE["extmem_distinct"])

    check(f"the issue's {ORACLE['extmem_raw']} file-wide DAT_EXTMEM_ occurrences "
          f"and the {ORACLE['extmem_commented']} of them that are this "
          "repository's own annotation text quoting the decompile are still "
          f"where they were (raw: {dict(raw)})",
          raw["DAT_EXTMEM"] == ORACLE["extmem_raw"] and
          raw["DAT_EXTMEM"] - (extmem["main-ec"][1] + extmem["pd"][1])
          == ORACLE["extmem_commented"])
    check(f"oracle: DAT_EXTMEM_ only, what issue #132 counted -- main EC "
          f"{ORACLE['extmem_main_distinct']} distinct / "
          f"{ORACLE['extmem_main_refs']} refs, PD "
          f"{ORACLE['extmem_pd_distinct']}/{ORACLE['extmem_pd_refs']}, which is "
          f"{ORACLE['extmem_distinct']} distinct addresses in all after the "
          f"{extmem_both} both spell there (got {extmem['main-ec']} and "
          f"{extmem['pd']}, "
          f"{len(set(of('main-ec', 'DAT_EXTMEM')) | set(of('pd', 'DAT_EXTMEM')))} distinct / "
          f"{extmem['main-ec'][1] + extmem['pd'][1]} refs in all)",
          (extmem["main-ec"][0], extmem["main-ec"][1]) ==
          (ORACLE["extmem_main_distinct"], ORACLE["extmem_main_refs"]) and
          # Asserted since 2026-09-24: these two were display-only, and went
          # stale through several re-pins of the per-program figures above.
          len(set(of("main-ec", "DAT_EXTMEM")) | set(of("pd", "DAT_EXTMEM")))
          == ORACLE["extmem_distinct"] and
          extmem["main-ec"][1] + extmem["pd"][1] == ORACLE["extmem_refs"] and
          (extmem["pd"][0], extmem["pd"][1]) ==
          (ORACLE["extmem_pd_distinct"], ORACLE["extmem_pd_refs"]))
    check(f"oracle: the {ORACLE['symbol_main_distinct']} main-EC addresses the "
          f"decompiler named, {ORACLE['symbol_main_refs']} references, and "
          f"{ORACLE['symbol_pd_distinct']}/{ORACLE['symbol_pd_refs']} of them in "
          f"the PD image (got {syms['main-ec']} and {syms['pd']})",
          syms["main-ec"] == (ORACLE["symbol_main_distinct"],
                              ORACLE["symbol_main_refs"]) and
          syms["pd"] == (ORACLE["symbol_pd_distinct"], ORACLE["symbol_pd_refs"]))
    # Within a program the two spellings are disjoint: the exporter applied its
    # symbol table to the EC programs and not to the PD image (gen_xdata_symbols
    # refuses to name PD), so no address there is both. Across programs they
    # differ -- 0x07D8 is `MODE_TCC_OFFSET_DEFAULTS_GAMING_0` in the EC and
    # `DAT_EXTMEM_07d8` in the PD image -- which is why `spelled_as` can carry
    # both.
    check("within each program the two spellings are disjoint address for "
          "address, so a named address is never also a DAT_EXTMEM_ token",
          all(len(e["spellings"]) == 1 for g in GROUPS for e in groups[g].values()))
    check("the PD image is spelled entirely in DAT_EXTMEM_ tokens, which is "
          "gen_xdata_symbols.py's own refusal to name it",
          all(e["spellings"] == {"DAT_EXTMEM"} for e in groups["pd"].values()))
    check(f"oracle: the full census, both spellings -- {ORACLE['distinct']} "
          f"distinct / {ORACLE['refs']} references, main EC "
          f"{ORACLE['main_distinct']}/{ORACLE['main_refs']} (got {total_distinct}"
          f"/{total_refs}, {distinct['main-ec']})",
          (total_distinct, total_refs) == (ORACLE["distinct"], ORACLE["refs"]) and
          distinct["main-ec"] == (ORACLE["main_distinct"], ORACLE["main_refs"]))
    check(f"oracle: {ORACLE['pd_only']} PD-only, {ORACLE['both']} touched by both "
          f"(got {len(pd_only)} / {len(both)})",
          (len(pd_only), len(both)) == (ORACLE["pd_only"], ORACLE["both"]))
    check("main + PD equals the file-wide total on both axes",
          distinct["main-ec"][0] + len(pd_only) == total_distinct and
          refs["main-ec"] + refs["pd"] == total_refs)

    top = sorted(((e["refs"], a) for a, e in groups["main-ec"].items()), reverse=True)
    check(f"oracle: the top two main-EC addresses by reference count are "
          f"{', '.join(f'{a}={n}' for a, n in ORACLE_TOP_MAIN)} (got "
          f"{', '.join(hexaddr(a) + '=' + str(n) for n, a in top[:2])})",
          tuple((hexaddr(a), n) for n, a in top[:2]) == ORACLE_TOP_MAIN)

    # 0x07D8 is the address the `DAT_EXTMEM_`-only reading called a blind spot.
    # It is not one: registers.yaml gives it static_refs_main_ec 1, the
    # decompiler was given the symbol MODE_TCC_OFFSET_DEFAULTS_GAMING_0, and
    # the reference is there under that name.
    check("the 0x07D8 correction: its main-EC reference is spelled "
          "MODE_TCC_OFFSET_DEFAULTS_GAMING_0, and the PD image spells the same "
          "address DAT_EXTMEM_07d8 because it is not named there",
          0x07D8 in of("main-ec", "symbol") and
          0x07D8 in of("pd", "DAT_EXTMEM"))
    everywhere = set(groups["main-ec"]) | set(groups["pd"])
    named = sorted(a for a in everywhere if a in symbols)
    check(f"of the {len(symbols)} named addresses, {ORACLE['named_in_tree']} "
          f"appear in the decompiled tree at all (got {len(named)}: "
          f"{', '.join(hexaddr(a) for a in named)})",
          len(named) == ORACLE["named_in_tree"])
    check("every address the tree spells by symbol is in the generated symbol "
          "table, so the name column can never be empty for one",
          all(a in symbols for g in GROUPS for a, e in groups[g].items()
              if "symbol" in e["spellings"]))

    # The residual blind spot, and it is a real one. Both addresses in
    # BLIND_SPOT are inside bank0:0x94D0=copy_code_table_into_0730_07a7, and
    # neither names itself: Ghidra typed 0x0733 as a code pointer, and 0x0735
    # is reached as a base literal plus a runtime index. Only the first is
    # findable, by looking for the `DAT_CODE_` spelling, so only the first is
    # checked -- the second is named rather than verified, and saying so is the
    # honest form. The census does not read `DAT_CODE_` as an occurrence, and
    # should not: 0x0460 and 0x049F in the same spelling are just as likely to
    # be common-area code, and importing them would repeat the PD/main
    # confusion in a new place.
    code_only = {int(a, 16) for out_file in by_file
                 for a in CODE_TOKEN.findall(open(os.path.join(DECOMPILED, out_file)).read())
                 if int(a, 16) in symbols and int(a, 16) not in everywhere}
    spelled, unspelled = 0x0733, 0x0735
    check(f"the two blind-spot addresses are "
          f"{', '.join(hexaddr(a) for a in BLIND_SPOT)}; "
          f"of them the one that is spelled at all is {hexaddr(spelled)}, behind "
          f"a CODE pointer (got {', '.join(hexaddr(a) for a in sorted(code_only)) or 'none'}), "
          f"and {hexaddr(unspelled)} is not findable by any spelling",
          code_only == {spelled})

    # Issue #181. Ten of pd-001's 34 addresses sit in 0xFF00-0xFFFF, and the
    # census counted them because Ghidra wrote `DAT_EXTMEM_ff80`. The address
    # space is settled from the encoding instead, out of the committed `.asm`.
    pd_asm = read_asm(PD_PROGRAM)
    forms = {a: xdata_space(pd_asm, a) for a in XSPACE_FORM}
    unbacked = [hexaddr(a) for a in sorted(XSPACE_FORM) if forms[a] is None]
    check(f"issue #181: all {len(XSPACE_FORM)} of pd-001's 0xFFxx addresses are "
          f"carried by a `mov DPTR,#imm16` in the committed .asm, each to a "
          f"`movx` -- and no 8051 direct-addressing opcode takes a 16-bit "
          f"operand, so none of them can be a direct address whatever the "
          f"decompiler spelled it (not found by this method: "
          f"{', '.join(unbacked) or 'none'})",
          not unbacked)
    wrong_form = [f"{hexaddr(a)}={forms[a][0]}"
                  for a in sorted(XSPACE_FORM)
                  if (forms[a] is not None and
                      (forms[a][0] == "inc") != (XSPACE_FORM[a] == "INC"))]
    literal_n = sum(1 for v in XSPACE_FORM.values() if v != "INC")
    check(f"and each is reached by the form the annotation records -- a "
          f"`mov DPTR,#imm16` for {literal_n} of them, a `mov DPTR` one byte "
          f"below plus `inc DPTR` for "
          f"{', '.join(hexaddr(a) for a in XSPACE_FORM if XSPACE_FORM[a] == 'INC')} "
          f"(got a different form for: {', '.join(wrong_form) or 'none'})",
          not wrong_form)
    # The negative half, and the one that tests the issue's premise instead of
    # restating it. `mov DPTR` of one of the ten is the *only* instruction in
    # the PD tree allowed to name one, so a direct-address or bit-address form
    # appearing here fails instead of being argued about.
    intruders = dptr_operand_only(pd_asm, XSPACE_FORM)
    check(f"and no other instruction in the PD tree names one of the ten -- a "
          f"direct address and a bit address are both one byte wide, so there "
          f"is no form in which a 0xFFxx value could be either (found: "
          f"{', '.join(f'{f}!{at} {m} {o}' for f, at, m, o in intruders) or 'none'})",
          not intruders)

    pd_high = sorted(a for a in groups[PD_PROGRAM] if a >= 0xF000)
    check(f"oracle: the PD census holds {len(XSPACE_PD_HIGH)} addresses at or "
          f"above 0xF000, the same address for address (got {len(pd_high)}: "
          f"{', '.join(hexaddr(a) for a in pd_high) or 'none'})",
          pd_high == list(XSPACE_PD_HIGH))
    unbacked_high = [hexaddr(a) for a in pd_high
                     if xdata_space(pd_asm, a) is None]
    check(f"every one of those {len(XSPACE_PD_HIGH)} is backed by an encoding "
          f"in the .asm, so the region is XDATA by opcode and not only by the "
          f"decompiler's spelling (not found by this method: "
          f"{', '.join(unbacked_high) or 'none'})",
          not unbacked_high)
    # The reason the discrimination reads the tree and not the image. Three of
    # the twenty-three are reached only by walking DPTR up one, so a `90 hi lo`
    # byte scan over the PD image finds the other twenty and cannot find these
    # at all -- and 0xFFDB is not one of pd-001's ten, so reading the issue's
    # list alone would have made the count twenty-one.
    inc_only = sorted(a for a in pd_high
                      if (xdata_space(pd_asm, a) or ("literal",))[0] == "inc")
    check(f"exactly {len(XSPACE_INC_ONLY)} of them -- "
          f"{', '.join(hexaddr(a) for a in XSPACE_INC_ONLY)} -- are reached by "
          f"`inc DPTR` from the address below and never by a `mov DPTR` of "
          f"their own, which is why a `90 hi lo` byte scan finds "
          f"{len(pd_high) - len(inc_only)} of the {len(pd_high)} and misses "
          f"these {len(inc_only)} (got "
          f"{', '.join(hexaddr(a) for a in inc_only) or 'none'})",
          inc_only == sorted(XSPACE_INC_ONLY))
    main_high = [a for a in groups["main-ec"] if a >= 0xF000]
    main_ceiling = max(groups["main-ec"], default=0)
    check(f"and no main-EC census address reaches 0xF000 either, the main EC's "
          f"highest being {hexaddr(MAIN_EC_CEILING)} (got {len(main_high)} at "
          f"or above 0xF000 and a ceiling of {hexaddr(main_ceiling)}), so the "
          f"0xF000-0xFFFF run is the PD image's own in the census -- which is "
          f"a claim about a census, and a census is a lower bound",
          not main_high and main_ceiling == MAIN_EC_CEILING)

    register_rows, cluster_rows, _ = build(funcs, names, symbols, census, calls,
                                           args.threshold)
    by_addr = {r["addr"]: r for r in register_rows}
    # The wide direction oracle, and the only one here that is not internal.
    # Each entry is read off the decompiled C by hand (the greps are in the
    # comment beside it), so this is where a `==` classified as a store fails
    # loudly instead of summing correctly.
    wrong = {}
    for addr, expected in HAND_CHECKED.items():
        row = by_addr.get(addr)
        got = ({k: int(row[k]) for k in expected} if row
               else {k: "absent" for k in expected})
        if got != expected:
            wrong[addr] = (expected, got)
    check(f"the hand-checked direction oracle: "
          f"{len(HAND_CHECKED)} addresses, "
          f"{', '.join(sorted(HAND_CHECKED))}, each read off the decompiled C by "
          f"hand rather than by this tool"
          + (f" -- disagreed on {', '.join(f'{a} (expected {e}, got {g})' for a, (e, g) in sorted(wrong.items()))}"
             if wrong else ""),
          not wrong)
    # Internal by construction, and labelled so: the report's §4.1 table read
    # off these, so a drift in any of them means the table and the CSVs have
    # parted. It cannot vouch for the direction -- only HAND_CHECKED can.
    check(f"the §4.1 bucket totals, "
          f"{' '.join(f'{k} {v}' for k, v in BUCKET_TOTALS.items())} "
          f"(got {' '.join(f'{k} {fired.get(k, 0)}' for k in BUCKET_TOTALS)})",
          all(fired.get(k, 0) == v for k, v in BUCKET_TOTALS.items()))
    # `name` is what the symbol table calls the address, which is not the same
    # fact as `spelled_as`: the six named addresses the PD image touches are
    # named for the EC and written as DAT_EXTMEM_ there, so a PD row carries
    # the EC's name in `name` while `spelled_as` says DAT_EXTMEM. Conflating
    # the two would be the PD image being credited with the EC's vocabulary.
    check("the `name` column is populated exactly for the addresses the symbol "
          "table names, independently of how the tree spells them",
          all((r["name"] != "") == (int(r["addr"], 0) in symbols)
              for r in register_rows))
    check("every address is in exactly one cluster",
          all(r["cluster_id"] for r in register_rows) and
          len({r["cluster_id"] for r in register_rows}) <= len(cluster_rows))
    check("cluster sizes sum to the address count of each program",
          sum(int(r["size"]) for r in cluster_rows if r["program"] == "main-ec")
          == distinct["main-ec"][0] and
          sum(int(r["size"]) for r in cluster_rows if r["program"] == "pd")
          == distinct["pd"][0])
    # A cluster of one address has no function touching two of its addresses,
    # so `shared_functions` is legitimately empty there.
    unknown = {m.group(0) for r in cluster_rows
               for m in FUNC_KEY.finditer(r["shared_functions"])
               if (m.group(1), m.group(2)) not in funcs}
    check("every shared function a cluster names resolves to a row in index.csv",
          not unknown)
    check("the two unresolved-direction buckets survive into the CSV as "
          "their own columns",
          all(int(r["passed-to-call"]) + int(r["address-taken"]) <= int(r["refs"])
              for r in register_rows))
    # The reader/writer columns count *functions*, so each one needs a
    # reference of its own direction to be there. 0x06E6 is the case that
    # matters: 50 functions touch it and 3 of its 72 references write it, so
    # anything that derives "writer" from the address's own buckets calls all
    # 50 of them writers.
    check("each reader function has a read or read+write reference of its own, "
          "and each writer a write or read+write one",
          all(int(r["readers"]) <= int(r["read"]) + int(r["read+write"]) and
              int(r["writers"]) <= int(r["write"]) + int(r["read+write"])
              for r in register_rows))
    check("readers and writers are subsets of the functions that touch the "
          "address, and neither exceeds it",
          all(int(r["readers"]) <= int(r["functions_touched"]) and
              int(r["writers"]) <= int(r["functions_touched"])
              for r in register_rows))
    check("the rank the report's worklist uses is total: no two clusters tie "
          "on size, references and lowest address",
          len({(r["size"], r["refs"], r["addr_range"]) for r in cluster_rows})
          == len(cluster_rows))
    check("the clusters CSV is a projection of the registers CSV, not a "
          "separate count",
          sum(int(r["refs"]) for r in cluster_rows) == total_refs)

    on_disk_ok = True
    for _rows, _columns, path, text in outputs(
            args, (register_rows, cluster_rows, groups)):
        try:
            with open(path, newline="") as f:
                if f.read() != text:
                    on_disk_ok = False
        except FileNotFoundError:
            on_disk_ok = False
    check("the committed CSVs match a fresh generation (run without --check "
          "after changing anything the census reads)", on_disk_ok)

    print(f"  {len(cluster_rows)} clusters at threshold {args.threshold}; "
          f"{distinct['main-ec'][0]} main-EC and {distinct['pd'][0]} PD addresses")
    print("  all assertions passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def threshold_sweep(args) -> int:
    """Cluster count against threshold, for the report's stability table.

    Reads the same census and re-clusters it; nothing is written."""
    funcs, by_file = load_index()
    names = load_names(funcs)
    symbols = load_symbols()
    census, _calls, _raw = scan(by_file, names,
                                {r["name"] for r in funcs.values()}, symbols)
    groups = {g: merge_group(census, PROGRAM_COL[g]) for g in GROUPS}
    # The `relations` column is what the run measured, so the two modes cannot
    # be mistaken for each other when a reader compares their output.
    relations = "touching" if args.no_writer_axis else "touching+writers"
    print(f"threshold,relations,main-ec clusters,main-ec largest,"
          f"main-ec singletons,pd clusters,pd largest")
    for t in list(args.thresholds) + ([args.threshold]
                                      if args.threshold not in args.thresholds else []):
        row = []
        for g in GROUPS:
            comps = sorted((len(v) for v in components(
                groups[g], t, not args.no_writer_axis).values()), reverse=True)
            row += [str(len(comps)), str(comps[0]), str(sum(1 for c in comps if c == 1))]
        print(",".join([f"{t:.2f}", relations] + row))
    return 0


def reconcile(args) -> int:
    """This tool's main-EC count against register_ref_table.py's, per address.

    The two methods are independent -- this one reads Ghidra's decompiled C,
    register_ref_table.py scans the committed image for unaligned `90 hi lo`
    byte patterns and decodes a window of opcodes at each -- but they do not
    count the same thing, so most rows differ and the differences are not
    errors. A `MOV DPTR,#0x043E` is one site and can be several C-level
    references (a helper call taking the address, a dereference of it, the same
    register named twice in one expression), and a function that did not
    decompile carries its sites nowhere at all. So `CPU_TEMP` reads 43 against
    15 and `CHARGE_TARGET_MV` reads 4 against 10, in opposite directions.

    What the two columns *are* good for is the cases where one is zero and the
    other is not, which is the only direction that can be read as a gap in the
    decompiled tree. Two addresses are in that state and the report names them.

    Neither number is right and the other wrong. Both inherit the
    indirect-addressing blind spot, and this one additionally misses every
    function that did not decompile -- so it is the lower bound of the two."""
    # Imported here, not at the top: the other four modes read committed text
    # only, and this is the one that needs PyYAML and a sibling tool from the
    # same directory.
    import yaml

    import register_ref_table

    image = open(args.firmware, "rb").read()
    off, magic = register_ref_table.PD_MARKER
    if image[off:off + len(magic)] != magic:
        print(f"no {magic.decode()!r} marker at file 0x{off:05X} -- this is not "
              "the image the recorded counts were taken from", file=sys.stderr)
        return 1
    with open(args.registers) as f:
        regs = yaml.safe_load(f)["registers"]

    funcs, by_file = load_index()
    names = load_names(funcs)
    symbols = load_symbols()
    census, _calls, _raw = scan(by_file, names,
                                {r["name"] for r in funcs.values()}, symbols)
    main = merge_group(census, MAIN_PROGRAMS)
    pd = merge_group(census, (PD_PROGRAM,))

    print("| addr | registers.yaml name | this tool, main EC | this tool, PD | "
          "register_ref_table.py, main EC | register_ref_table.py, PD | "
          "in decompiled tree |")
    print("|---|---|---:|---:|---:|---:|---|")
    agree = disagree = absent = 0
    for name, addr in register_ref_table.addresses(regs):
        rows = list(register_ref_table.site_rows(image, addr, True, 0))
        _, other_main, other_pd, _ = register_ref_table.row_for(image, addr, True, rows)
        mine_main = main.get(addr, {}).get("refs", 0)
        mine_pd = pd.get(addr, {}).get("refs", 0)
        if mine_main == other_main:
            agree += 1
            verdict = "agrees"
        elif mine_main == 0 and other_main:
            absent += 1
            verdict = "**not in the decompiled tree**"
        else:
            disagree += 1
            verdict = "**differs**"
        print(f"| `{hexaddr(addr)}` | `{name.split(' (')[0]}` | {mine_main} | "
              f"{mine_pd} | {other_main} | {other_pd} | {verdict} |")
    sys.stdout.flush()
    print(f"{agree + disagree + absent} addresses: {agree} agree on the main-EC "
          f"count, {absent} have main-EC sites the decompiled tree does not "
          f"contain, {disagree} differ another way. A zero in the 'this tool' "
          "column is 'not found by this method' -- a function that did not "
          "decompile carries its references nowhere -- never 'absent'.",
          file=sys.stderr)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true",
                       help="regenerate in memory and diff against the committed "
                            "CSVs; no network, no Ghidra, no image")
    modes.add_argument("--self-test", action="store_true",
                       help="known-answer run over the committed tree, including "
                            "issue #132's published census numbers")
    modes.add_argument("--threshold-sweep", action="store_true",
                       help="print the cluster count against each threshold in "
                            "--thresholds (the stability table in the report)")
    modes.add_argument("--reconcile", metavar="FIRMWARE",
                       help="cross-check every registers.yaml address against "
                            "register_ref_table.py on the given image; needs the "
                            "image and registers.yaml, unlike every other mode")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"Jaccard similarity for the clustering (default: "
                         f"{DEFAULT_THRESHOLD})")
    ap.add_argument("--thresholds", type=float, nargs="+", default=list(SWEEP_THRESHOLDS),
                    metavar="T", help="thresholds for --threshold-sweep")
    ap.add_argument("--no-writer-axis", action="store_true",
                    help="for --threshold-sweep: cluster on the touching-function "
                         "relation alone, which is how the second relation's "
                         "contribution is measured")
    ap.add_argument("--out-registers", default=OUT_REGISTERS,
                    help=f"per-address CSV (default: {OUT_REGISTERS})")
    ap.add_argument("--out-clusters", default=OUT_CLUSTERS,
                    help=f"per-cluster CSV (default: {OUT_CLUSTERS})")
    ap.add_argument("--registers", default=os.path.join(EC_DIR, "annotations",
                                                         "registers.yaml"),
                    help="registers.yaml for --reconcile")
    args = ap.parse_args()

    if args.self_test:
        return self_test(args)
    if args.threshold_sweep:
        return threshold_sweep(args)
    if args.reconcile:
        args.firmware = args.reconcile
        return reconcile(args)
    if args.check:
        return check(args)
    return write(args)


if __name__ == "__main__":
    sys.exit(main())
