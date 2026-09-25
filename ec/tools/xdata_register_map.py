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

**The direction split is now checked corpus-wide, and that is a wider net than
it looks and a shallower one than `HAND_CHECKED`.** Every occurrence the census
buckets `write` or `read+write` is asserted to have an assignment -- not `==`
-- after the address, measured over the whole tree rather than over five
hand-picked rows. Today that is **5,662 occurrences across 1,008 distinct
addresses** of the census's 1,171, and it holds with no exemptions: the second
pass accepts 5,664, and the two it accepts and the census does not are 0x048A's
`*`-dereference stores, which `store_target()` excludes for cause and a
necessary condition does not need to exclude.

**It is a second code path over the same text, not a second pair of eyes.**
Same files, same regex, same `strip_comments()`, and the buckets it is measured
against are the ones this tool just produced. What it is *not* is a
re-implementation, and that is what makes it worth asserting: the `==`
rejection lives in `store_target()`, and the second pass's predicate is only
"an `=` that is not `==` follows", so it never consults the thing under test.
Re-introduce the pre-fix classifier and the two disagree on 837 occurrences,
across 210 distinct addresses -- the 837, not the 838 above, because the one
`==` site that was already `address-taken` rather than `write` (`&&` at
bank0/A747.c:24) is not an offender either way.
What it cannot reach is everything a shape test over C text cannot reach -- a
store the decompiler mis-spelled, a write through a pointer, and a per-address
*count* that is wrong while every occurrence is assignment-shaped. Only
`HAND_CHECKED` measures per-address counts, and it is five addresses wide
because those five are a shape catalogue rather than a sample.

**A source count is a count of files, and 42 files can be one routine.** The
counter sweep at `bank1:0x8001`-`0x8189` is 393 bytes the exporter split into 42
listings whose sizes sum to exactly 393 (`annotations/xdata-06c2-06db-timers.md`
§2), and every one of the 42 decompiled the routine rather than its own bytes,
so the 19 addresses **all 42 of them name** are each counted 42 times over --
93% of `main-ec-002`'s references, and every one of `0x0843`'s 168. The count
falls off away from those 19, because a listing near the end of the run covers
less of it: `8001.c` names 46 addresses and the 19-address tail `80EF.c` names
19. The relation here makes that visible without deciding it:

> **Two `.c` files in the same program are co-readings when they name the same
> `COREADING_MIN_CORE` or more XDATA addresses. A co-reading group is a
> connected component of that relation, computed per program, exactly as
> `components()` already does for addresses.**

Connected components rather than a cover, and transitive by construction: the
relation is not transitive, so a greedy pass would make the output depend on
file order, and the same objection `components()` documents applies verbatim.
The component is what makes a group bigger than a pair -- and it is also why a
group's members need not resemble each other pairwise. The six-file `bank0`
group around `0x8749.c` has a **one-address** common core, `0x1804`, which all
six read; only three of the six also read `0x0440`. They are six real readers
that a neighbour connects, and the tool reports the core size in
`--co-reading-group-table` precisely so that shape is visible rather than
implied. **A co-reading group is a count of files, never a
claim that the files are one routine.** Deciding that is the boundary
hypothesis `--mode rebuild-project` owns, which is why
`--collapse-co-readings` prints what assuming it would imply and writes
nothing.

What the columns add is therefore bounded on purpose. `refs` does not move and
no reference is de-duplicated, the five direction buckets do not move, the
clustering does not move and `cluster_id` keeps its exact values: the worklist
ranks on `(size, refs, lowest address)` and two of those three are untouched,
so **nothing can reorder**. `co_reading` counts an address's source functions
that are in a group, `sources_beyond` is the difference -- the sources that are
not copies of one another by this relation -- and the cluster columns say the
same for a cluster. `0x0440` is the control that keeps this a count and not a
verdict: it loses 46 of 91 to a group and keeps 45 sources. `0x0843` keeps
none.

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

**One routine is exported 42 ways, and every per-address `refs` count in the
committed CSVs is an upper bound on *distinct* references because of it.**
`index.csv` splits `bank1:0x8001`-`0x8189` into 42 rows -- 16 of them a single
instruction -- and every one of their `.c` files decompiles that same routine
rather than its own bytes: 16 to 47 statements each, every member scoring 0.87
to 0.98 containment against the owner's 47 (`xdata-export-ownership.csv`). The
walk above adds a reference per token per *file*, so 0x0843 reads 168 times
where the routine reads it 4, and 42 entries in the incidence matrix stand for
one function. Clusters rank by size, then references, then address, so all of
that is a large part of why one 393-byte routine holds those addresses near the
top of the worklist at all. `ec/tools/export_ownership.py` derives which export
owns which body and `--export-ownership` reads each routine once, from that one
export, taking the census to 9,401 references with 0x0843 at 4 and one function
behind it.

**The default stays off, and that is the calibrated answer rather than a
cowardly one.** The pass is a containment heuristic over decompiled text, not a
function boundary: a non-owner is skipped rather than reconciled against its
owner, so an owner that is not a superset takes the references with it. On
this tree that costs `cluster_key` on 35 of the 430 clusters, breaks 5 of the
10 hand names in `xdata-cluster-names.csv`, and adds 2 clusters -- a
tree-wide renumbering to land on top of a detector known to be approximate.
The root cause is the export boundary, and fixing it needs
`--mode rebuild-project`, which cannot share a branch
(annotations/xdata-06c2-06db-timers.md 8 item 7). So the pass ships measured,
pinned by `OWNERSHIP` and reachable through the flag, and the flip is its own
PR once the boundary lands.

**A cluster has two identities and the prose needs the one that is not a rank.**
`cluster_id` is a rank -- `build()` orders by size, then references, then
lowest address, and `main-ec-001` is whatever sorts into first place. Issue
#253 is what that costs: a single change anywhere in the ranking reshuffles every
id below the one that moved, and the citations that named those ids drifted
# with it.
So the two census CSVs also carry `cluster_key`, a content hash over the
cluster's program and its sorted `addrs`, and `cluster_name`, a hand name keyed
by that hash in `annotations/xdata-cluster-names.csv`. A key is exact and says
nothing about a near miss; a name is a claim a human made and can be carried
across a regeneration *in changed form*, which is the case the key cannot cover
-- `--map` reports both, and says which of the two happened and with what score.
Both are additive: `cluster_id` keeps the exact values it has today, because
`xdata-registers.csv` and every page in the tree name it, and switching over is
a prose sweep rather than a decision this tool makes.

**What a carried name does and does not claim.** `seeded` (the names file names
this exact key) and `exact` (a named cluster of the committed census has this
exact key) are the same claim. `overlap` is a weaker one -- the name came from
the named cluster whose membership scores at least `CARRY_MIN_JACCARD` against
this one -- and the score is reported with it, because a name carried at 0.98
and one carried at 0.51 are not the same statement. `tie` is a named cluster
being claimed by two old names at the same score: that is a fact about the
clustering, so it is reported and no winner is picked. And `none` is **not
carried by this method** -- never *gone*, never *lost*, never *disappeared*: a
function that stopped decompiling, a threshold that moved, a guard that was
removed and a cluster that stopped existing are four different things, and this
column can only report that its own rule did not fire.

**`--no-eq-guard` re-runs the census with the `==` rejection turned off**, and
is refused with `--check` and `--self-test` because both are gates: a flag that
can change a bucket without changing anything on disk must not be reachable
inside a mode whose whole claim is that nothing changed. It is also refused
unless it is given `--out-registers` and `--out-clusters`, for the same reason
one step removed: run bare it would write the pre-#178 census over the
committed CSVs, and `--check` would then be green because the files agree with
each other. It exists because
`annotations/xdata-06c2-06db-timers.md` §6a measures what the guard bought, and
that measurement has to stay re-derivable from the committed tree forever. It
could not be, from a commit pointer: `git log --oneline -S 'startswith("==")' --
ec/tools/xdata_register_map.py` reaches **two commits on `origin/main`** -- #206,
which is itself the commit that added the guard, and #302, whose tree-wide
invariant added two more occurrences of the same string. Neither is the
pre-#178 classifier, which appears only at #206's parent, a revision the search
does not name, so the recipe was "copy the tool and patch it", which is how §6a
came to compare the tool against itself. The numbers that recipe produced are
real and the recipe is the problem; this flag is the recipe, kept.

Usage:
    python3 ec/tools/xdata_register_map.py               # write the two CSVs
    python3 ec/tools/xdata_register_map.py --check       # diff vs committed
    python3 ec/tools/xdata_register_map.py --self-test
    python3 ec/tools/xdata_register_map.py --map ec/annotations/xdata-clusters.csv
    python3 ec/tools/xdata_register_map.py --threshold-sweep
    python3 ec/tools/xdata_register_map.py --threshold-sweep --no-writer-axis
    python3 ec/tools/xdata_register_map.py --co-reading-sweep
    python3 ec/tools/xdata_register_map.py --co-reading-group-table
    python3 ec/tools/xdata_register_map.py --collapse-co-readings
    python3 ec/tools/xdata_register_map.py --no-eq-guard --out-registers /tmp/before-registers.csv --out-clusters /tmp/before-clusters.csv
    python3 ec/tools/xdata_register_map.py --reconcile ec/firmware/GMxMGxx_11.800
"""
import argparse
import collections
import csv
import hashlib
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
NAMES_CSV = os.path.join(EC_DIR, "annotations", "xdata-cluster-names.csv")
OWNERSHIP_CSV = os.path.join(EC_DIR, "annotations", "xdata-export-ownership.csv")
OUT_REGISTERS = os.path.join(EC_DIR, "annotations", "xdata-registers.csv")
OUT_CLUSTERS = os.path.join(EC_DIR, "annotations", "xdata-clusters.csv")

# export_ownership is a sibling tool in this directory, imported by bare module
# name the way check_site_census.py imports this one. The path is put on
# sys.path here rather than at the call site so a test loading this file by
# path -- which does not set sys.path[0] the way running it as a script does --
# resolves it too.
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import export_ownership  # noqa: E402

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
    "functions", "cluster_key", "co_reading", "sources_beyond",
]
CLUSTER_COLUMNS = [
    "cluster_id", "program", "size", "refs", "addrs", "addr_range",
    "functions_touched", "shared_functions", "callees", "named_addrs",
    "cluster_key", "cluster_name", "co_reading", "co_reading_refs",
    "co_reading_dominant",
]

# The two columns `--map` prints, one row per old cluster. A row is a *report*,
# not a file, so it is not in the column lists above and is never committed.
MAP_COLUMNS = [
    "old_cluster", "new_cluster", "key", "old_key", "new_key", "cluster_name",
    "carried", "match", "jaccard", "added", "removed",
]

# Jaccard >= 0.5 sits at the top of the plateau the sweep shows: from 0.35 to
# 0.50 the largest main-EC cluster holds at 108-112 addresses while the cluster
# count only moves 337 -> 376, and 0.55 drops that to 43 and adds 149 clusters.
# `--threshold-sweep` prints the whole curve and the report quotes it, so the
# default is a recorded choice rather than a tuned one.
DEFAULT_THRESHOLD = 0.50
SWEEP_THRESHOLDS = (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)

# How many XDATA addresses two `.c` files in one program have to name in common
# before they count as co-readings of each other. See the module docstring for
# what the relation measures and what it deliberately does not decide.
#
# **8 is recorded, not tuned, and `--co-reading-sweep` is what records it.**
# Largest group / files in groups, over the committed tree:
#
#     floor   2    4    6    8    10   12   16   20
#     largest 282  61   42   42   42   42   42   41
#     files   723  335  213  120  89   79   62   50
#
# Floors 2 and 4 are the trivially-equal-address-set artefact: two files that
# each name a single address score a Jaccard of 1.00, so a one-line helper and a
# 45-line routine join for no reason a reader would accept. From 6 to 16 the
# counter sweep's 42 files hold together as one group and the file count keeps
# falling; at 20 the sweep itself starts to break. 8 is where files-in-groups
# halves against 6 with the largest group unchanged, and it is the last floor
# before the curve's shape starts depending on the sweep alone. The same
# "recorded, not tuned" argument DEFAULT_THRESHOLD makes.
COREADING_MIN_CORE = 8
SWEEP_COREADING_FLOORS = (2, 4, 6, 8, 10, 12, 16, 20, 24)

# `cluster_key` is the content half of a cluster's identity: sha256 over the
# program's name and the cluster's space-joined sorted `addrs`, truncated to 12
# hex digits and spelled `k<hex>`. Twelve is 48 bits, and the self-test asserts
# the keys are distinct in a fresh generation and, read back out of the file,
# in the committed census as well, rather than taking a truncated hash's word
# for it. It is computed in `build()` where the cluster is formed, never
# written and read back to decide a key, so the key cannot drift with the file
# that records it.
CLUSTER_KEY_HEX = 12

# How much membership a named cluster must keep for its name to follow it into
# a new one. 0.50 is the clustering's own default and the top of the plateau
# `--threshold-sweep` prints, so a name and a cluster are carried by the same
# number: a rule that read the census two different ways would be one more thing
# to re-derive. The measured carries are in `annotations/xdata-register-map.md`
# §4.4, and the margin is not close -- across the guard-off regeneration the ten
# named clusters' best match scores 0.64 to 1.00 and the *next* named cluster
# scores 0.00 in every one of the ten -- so the exact value is a recorded choice
# rather than a tuned one.
#
# Below it, the outcome is `none`: **not carried by this method**. Never *gone*,
# never *lost* -- a cluster the decompiler stopped producing is not a cluster
# that stopped existing, and only the firmware can answer that.
CARRY_MIN_JACCARD = 0.50


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
# xdata-register-map.md and docs/findings.md 18.
# *** 2026-09-24, issue #259: the pins below do NOT move, and that is the
# measurement rather than an absence of one. Defining the byte -- registers.yaml
# gained XDATA_0390 and the regenerated xdata-symbols.csv named it, so
# ApplyAnnotations.java's createData now makes a definition where there was only
# an undeclared byte -- and re-running the export in default export-only mode
# moved no .c and no manifest.csv row: the export is byte-identical to the
# committed tree. The decompiler still renders the pair at bank1 0x9EA1 as
# CONCAT11(r4_value,r3_value), so naming the byte does not put it back in the
# token pattern's reach, and 0x0390 still has no row in the census.
# The other outcome the issue allowed for -- the census RISING, because the
# decompiler started spelling XDATA_0390 at 0x9EA1's two movxes -- did not
# happen. distinct/refs/main_distinct/main_refs and BUCKET_TOTALS therefore stand
# as 1171/14792 and 543/270 as committed, and the .asm witness in --self-test
# is what now keeps 0x0390 from reading as absent.
#
# The policy this measurement is the first test of, written where an annotation
# author will meet it: a variable row may change a caller's arity, and that is a
# correction rather than a loss; the census counts C-level references and is
# therefore a lower bound on the machine code; and a pin moves only with a
# measured reason recorded in the same change. ghidra/scripts/ApplyAnnotations.java,
# ec/annotations/README.md and docs/findings.md 18 carry the same rule.
#
# *** 2026-09-25, issue #263: the pins below move, and **almost all of the
# movement was already on `main`**. Measured against a pristine checkout of the
# parent commit as well as against this branch:
#
#   what the pin said | pristine `main` | this branch | this change moved it
#   refs              | 14818            | 14819       | +1
#   main_refs         | 13957            | 13961       | +4
#   pd_refs           | 861              | 858         | -3
#   symbol_main       | 147 / 6070       | 147 / 6070  | 0
#   named_in_tree     | 153              | 153         | 0
#   extmem_raw        | 8757             | 8758        | +1
#
# So the committed pins were **26 references and 3 named addresses behind the
# tree they were supposed to describe** before this branch touched anything, and
# `--self-test` was already red on `main` for that reason. Both halves are
# recorded rather than merged: the drift is not this issue's to claim, and the
# +1 is not large enough to explain it. `ec/decompiled/bank1/19A8.c` was stale
# against its own `ghidra-functions.csv` row (issue #255's correction landed
# without a re-export) and this build caught it up -- measured on its own, that
# file moves **no** census figure at all, so the whole +1 is the 88 rows.
#
# The +1 is still the mechanism the two blocks above describe, running in a
# direction #238 did not see. Committing 88 signatures moved **28 functions this
# batch never annotated**: 11 now pass more arguments than before (+25 declared
# parameters) and 17 pass fewer (-17). Net -78 against the -86 the 88 renames
# account for, which is arithmetically the census's own delta and is why the
# per-address list in xdata-register-map.md 7.2 is 6 addresses and not 88.
# Nothing here settles whether that is allowed; docs/findings.md 18 still calls
# it open, and this is the second batch's data point rather than its answer.
ORACLE = {
    # DAT_EXTMEM_ only, i.e. what issue #132 counted, comments excluded.
    #
    # 8758/8749 -> 8707/8698 and 915/7891 -> 906/7840, with the symbol tally
    # below moving 147 -> 156 distinct and 6070 -> 6121 refs. One cause, and it
    # is issue #250's: `a1d79a89` (PR #504) added nine `XDATA_*` symbols to
    # xdata-symbols.csv without re-exporting, so the committed `.c`/`.asm` text
    # kept spelling those nine addresses `DAT_EXTMEM_*` and both halves of this
    # oracle were pinned against that stale export. Issue #558's re-export is
    # the first one since, so the renames reach the text and the nine addresses
    # move from the DAT_EXTMEM_ tally to the symbol tally. `extmem_commented`
    # (9), the PD half (157/858) and `extmem_both` (37) are unmoved, which is
    # what fixes the diagnosis: the PD image is never given a symbol table, and
    # the nine renames are all main-EC.
    #
    # 1026/8698 -> 1024/8683 and 906/7840 -> 904/7825, with the symbol tally
    # below moving 156 -> 158 distinct and 6121 -> 6136 refs: issue #264's two
    # `XDATA_09EA`/`XDATA_09EB` rows, and the same mechanism as the nine above
    # rather than a new one. The plan for #264 expected only `named_in_tree` to
    # move, on the reasoning that export-only mode would leave the `.c` text
    # spelling `DAT_EXTMEM_*`; it does not, because `ApplyAnnotations.java`
    # applies xdata-symbols.csv to the project *copy* the export makes, so a
    # new name reaches the text without `--mode rebuild-project`. The deltas
    # cross-check exactly, which is what says this is explained: -2/+2
    # distinct and -15/+15 refs, and 15 is the census's own 7+8 references to
    # 0x09EA and 0x09EB. `extmem_commented` (9), the PD half (157/858) and
    # the full census below (1171/14819, main 1062/13961, 109/48) are all
    # unmoved -- the addresses and references did not change, only which token
    # spells them.
    "extmem_distinct": 1024, "extmem_refs": 8683,
    "extmem_raw": 8692, "extmem_commented": 9,
    "extmem_main_distinct": 904, "extmem_main_refs": 7825,
    "extmem_pd_distinct": 157, "extmem_pd_refs": 858,
    # What the decompiler named, which the issue's grep could not see.
    "symbol_main_distinct": 158, "symbol_main_refs": 6136,
    "symbol_pd_distinct": 0, "symbol_pd_refs": 0,
    # The full census this tool publishes.
    "distinct": 1171, "refs": 14819,
    "main_distinct": 1062, "main_refs": 13961,
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
    # 150 -> 153 on `main` without this block being re-derived. Found by
    # running --self-test on a pristine checkout of the parent commit, not by
    # this change. Which three is the one thing here that is **not** re-derivable
    # -- the pin is a bare integer and the prose above names only some of the
    # 150 -- so the 153 are not asserted individually. The --self-test failure
    # message enumerates every one of them, which is the place a reader is sent
    # rather than a list maintained here.
    #
    # 153 -> 162, issue #256: the drift went on, and by the time this change
    # re-derived it the symbol table had grown from 164 to 187 names and the
    # census from 1,171 to 1,171 distinct addresses with two of the new ones
    # (`0x07C7`, `0x07C8`) *not* among the named-in-tree set. The failure
    # message named exactly those two and no others, which is the arrangement
    # the paragraph above asks for -- the count is not asserted individually, the
    # *set* is, and the count is arithmetic over it. So both are recorded as
    # NOT_IN_TREE entries with their registers.yaml evidence, and this pin is
    # 187 - 25. Measured on `main` before this change touched anything: the two
    # rows and the two missing reasons were already there.
    # 162 -> 164, issue #264: XDATA_09EA and XDATA_09EB are both reached by a
    # decompiled function, so both are named-in-tree. Same cause as the
    # extmem/symbol movement above, and the same cross-check applies.
    "named_in_tree": 164,
}
ORACLE_TOP_MAIN = (("0x0440", 181), ("0x08A8", 170))
# `0x08A8`'s 170 above is 42-fold: all 44 of its source functions are members of
# a co-reading group -- 42 of them the counter sweep, the other two a four-file
# `bank0` group -- so its `sources_beyond` is **0** and the count of sources
# this relation can distinguish is 0 too. The pin stands as written: the census
# counts references and does not de-duplicate them, and the second entry here
# is the *second*-busiest address in the firmware by that count (`0x0440`, at
# 181, is the first). This comment is where the inflation is written down next
# to the number it inflates.
# `xdata-registers.csv`'s `co_reading` and `sources_beyond` columns carry it per
# address; COREADING_CHECKED below is the hand-read half.

# The co-reading relation's own figures, in the style of the ORACLE block and
# derived the same way: the largest group, the file total and the group count
# are arithmetic over `co_reading_groups()` at COREADING_MIN_CORE, and the
# oracle says so rather than leaving a reader to take them on trust.
#
# 24 groups over 120 files, largest 42. Re-derive with
# `python3 ec/tools/xdata_register_map.py --co-reading-sweep`, which prints the
# floor this is read at next to the curve it was chosen from.
#
# The 42 is the counter sweep of `annotations/xdata-06c2-06db-timers.md` §2 --
# the group's common core is 19 addresses, the 42 `index.csv` sizes sum to
# exactly 393, and 16 of them are one-instruction listings. All three are that
# page's §2 facts, now reproduced by the tool rather than by a hand count.
COREADING_GROUPS = 24
COREADING_FILES = 120
COREADING_LARGEST = 42
# The 42 sweep files are the first and last `out_file` of the largest group, and
# the group's size is the whole of it: a sweep split across two groups would be
# a different claim from one group of 42, and this asserts the difference.
# `out_file` is what `index.csv` records and what a reader greps. The last is
# `0x80EF`, not `0x8189`: the 42 listings are the *seeds* inside the run, and
# `0x8189` is where the run ends.
COREADING_SWEEP = ("bank1/8001.c", "bank1/80EF.c")
# How many addresses all 42 name. **Not 46, and the difference is the point:**
# `8001.c` opens at the start of the run and names 46, `80EF.c` opens 238 bytes
# in and names 19, and the core is the smaller of the two because it is the
# intersection over all 42. The group is 42 overlapping views of one routine,
# not 42 identical ones -- which is why `refs` is a 42-fold count for these 19
# addresses and a smaller multiple for the rest, and why the report presents the
# core rather than the largest file's count.
COREADING_SWEEP_CORE = 19

# Per address, `(co_reading, sources_beyond)` read off the decompiled tree by
# hand rather than by this tool, for the same reason HAND_CHECKED exists: an
# internal check passes on a wrong number when the wrong number is internally
# consistent, and a whole-tree invariant cannot tell a *count of files* from a
# count of routines. Every entry is the arithmetic of
# `co_reading + sources_beyond == functions_touched` over the committed
# register rows, with the derivation in the comment beside it.
COREADING_CHECKED = {
    # 168 references from 42 functions, and all 42 are the sweep's exports of
    # one 393-byte routine. `grep -c 0843 ec/decompiled/bank1/8*.c` reaches all
    # 42 and nothing outside the sweep names it. 42 + 0 = 42 touched.
    "0x0843": (42, 0),
    "0x0844": (42, 0),
    # 170 from 44 functions, and **all 44 are in groups**: the 42 sweep exports
    # plus `bank0/A139.c` and `bank0/A1A8.c`, the two members of a four-file
    # `bank0` group that also name this address (the group's other two,
    # `A00E.c` and `A1C8.c`, do not). So the distinct-source count this
    # relation can support is 0, and `0x08A8` is the second entry of
    # ORACLE_TOP_MAIN. 44 + 0 = 44 touched.
    "0x08A8": (44, 0),
    # 148 from 37 functions, all 37 of them members of the 42-file sweep group.
    # The address has ONE direct `MOV DPTR,#0x6D6` site in the image (timers
    # §2a) and the other 36 sources are that same body spelled 36 more times.
    # 37 + 0 = 37.
    "0x06D6": (37, 0),
    # 126 from 52 functions: 39 in groups -- the 42-file sweep's members that
    # spell this address, plus the six-file `bank0/8749.c` group and the
    # two-file `bank1/B98D.c` group, with overlaps -- and 13 that are not, each
    # of them a single reference in a file no group reaches. 39 + 13 = 52. The
    # control against a blanket "it is all the sweep": a co-reading group does
    # not have to contain every address the sweep touches, and this address is
    # read in thirteen places that have nothing to do with the sweep.
    "0x06C2": (39, 13),
    # **The control that keeps this a count and not a verdict.** 181 references
    # from 91 functions, and the grouped 46 are exactly three disjoint sets: the
    # 42 sweep exports, **three** of the six `bank0/8749.c` files
    # (`8749.c`, `8B14.c`, `8C46.c` -- the other three name `0x1804` instead),
    # and one of the two `bank1/976E.c`/`9817.c` files. 42 + 3 + 1 = 46, and
    # **45 are not in any group at all** -- `common/3DA8.c` and the `0x06C2`
    # thirteen above are among them. `0x0440` is read in 45 places this
    # relation cannot explain, it is all-read with no writer (HAND_CHECKED), and
    # it is the most-referenced address in the firmware. A co-reading flag that
    # retired this row would be reporting a shape as a verdict. 46 + 45 = 91.
    "0x0440": (46, 45),
    # 137 from 48 functions, 42 grouped and 6 not. `program=both`, and that is
    # the point of the entry: the main EC's 45 sources are the 42-file sweep
    # plus three singletons, and the PD image contributes three more that no
    # group reaches -- the relation never crosses the two programs, which is
    # what makes 42 and not 45 the grouped half. 42 + 6 = 48.
    "0x080D": (42, 6),
    # A PD-only address: one function, not in a group. This row is here to pin
    # the program split rather than the number -- a relation that grouped across
    # `main-ec` and `pd` would put the sweep's 42 exports and this together and
    # fail. 0 + 1 = 1.
    "0x00B6": (0, 1),
}
# The two symbol-table addresses register_ref_table.py finds main-EC sites for
# that the census does not. Both are inside
# bank0:0x94D0=copy_code_table_into_0730_07a7: 0x0733 is spelled
# `puVar3 = &DAT_CODE_0733;`, as a code pointer, and 0x0735 is not spelled at
# all -- `sVar5 = 0x735; ... *(char *)(sVar5 + bVar2)` is an indexed access off
# a raw base literal. Only the first is findable, so only it is checked; see
# the self-test and the report's blind-spot section.
BLIND_SPOT = (0x0733, 0x0735)

# The addresses the generated symbol table names and the census does not reach:
# `set(symbols) - everywhere`. Issue #280 pins this as a *set* rather than as
# the `named_in_tree` count alone, so "which addresses" is re-derivable here
# instead of only from a failure message, and so the count at
# ORACLE["named_in_tree"] becomes arithmetic over this dict rather than a
# number to be taken on trust.
#
# **The vocabulary has three entries and no word for absence.** A scan that
# finds no reference has found no reference; it cannot say the address is not
# there, which is `../../docs/findings.md` §4c and the whole content of 0x07B9's
# retraction below. The self-test asserts every reason begins with one of the
# three, and that no reason contains a word that would claim the byte is gone.
#
# The first reason is the only one that is re-derivable from the committed tree
# on its own, and it is the only one this file claims that for: it says the
# address is *there* in a form the token pattern cannot match, and that is
# checkable with a grep. Where the evidence lives in the image instead -- the
# 0x07E3-0x07E5 lightbar bytes, whose sites only `trace_xdata_refs.py` finds --
# the reason says so and uses the third entry. A line claiming the first reason
# with nothing behind it in the tree would be the overclaim this block exists
# to prevent, and the one that is easiest to make by accident.
NOT_IN_TREE_REASONS = ("reached through a form the scan cannot see",
                       "in a routine no export covers",
                       "not found by this method")
# The words that would turn a reason into an absence claim, which is the
# overclaim this block exists to make impossible. Asserted, not just intended.
NOT_IN_TREE_FORBIDDEN = ("absent", "does not exist", "no such", "unused",
                         "never touched", "dead")
# Every line cites the grep or the site that re-derives it, because a reason
# that cannot be re-derived is the thing this block is for.
NOT_IN_TREE = {
    # bank1/E100.asm:E176 carries `mov DPTR,#0x390` to a `movx`, and the
    # committed export writes neither the token nor the name: the callee at
    # bank1 0x9EA1 renders the address as CONCAT11(r4_value,r3_value) over
    # register names. The .asm is never rewritten by an annotation, so the byte
    # has a site in the machine code whatever the C spells.
    0x0390: "reached through a form the scan cannot see: the export spells it "
            "over register names (CONCAT11) where the .asm has a literal "
            "`mov DPTR,#0x390` at bank1/E100.asm:E176",
    # The decompiler read `mov DPTR,#0x402; lcall 0x889e` as a call to a
    # routine at 0x402, named the made-up routine `FUN_CODE_0402`, and exported
    # two files for it (ec/decompiled/common/0402.c, common/0408.c). Ten
    # bank1 sites call that name where the seed is. So the address is in the
    # tree, spelled as a function -- which is neither `DAT_EXTMEM_` nor a
    # generated symbol name, and so matches neither half of the occurrence
    # regex. Re-derive with `grep -rn FUN_CODE_0402 ec/decompiled/`.
    0x0402: "reached through a form the scan cannot see: the export spells the "
            "address as a function name, `FUN_CODE_0402`, and the census's "
            "regex matches no function name",
    # 16 occurrences, all the same shape: the 16-bit-pair helpers take the
    # address as a bare hex literal. `read_xdata_pair_to_r1r2(0x404)` at
    # bank1/B214.c:19 is the first; the `mov DPTR,#0x404; lcall 0x8892` pair
    # behind it is in bank1/B214.asm:B214.
    0x0404: "reached through a form the scan cannot see: passed to a 16-bit "
            "pair helper as a bare hex literal, `read_xdata_pair_to_r3r4"
            "(0x404)` at bank1/B214.c:19",
    # The second half of the same decompiler mistake as 0x0402, at its second
    # site: `FUN_CODE_0408`, from `common/0408.c`.
    0x0408: "reached through a form the scan cannot see: the export spells the "
            "address as a function name, `FUN_CODE_0408`, and the census's "
            "regex matches no function name",
    0x040A: "reached through a form the scan cannot see: passed to a 16-bit "
            "pair helper as a bare hex literal, `read_xdata_pair_to_r1r2"
            "(0x40a)` at bank1/AE2B.c:20",
    0x040C: "reached through a form the scan cannot see: passed to a 16-bit "
            "pair helper as a bare hex literal, `read_xdata_pair_to_r1r2"
            "(0x40c)` at bank1/AE92.c:18",
    0x040E: "reached through a form the scan cannot see: passed to a 16-bit "
            "pair helper as a bare hex literal, `write_r1r2_to_xdata_pair"
            "(0x40e)` at bank1/B50E.c:29",
    0x0410: "reached through a form the scan cannot see: passed to a 16-bit "
            "pair helper as a bare hex literal, `write_r3r4_to_xdata_pair"
            "(0x410)` at bank1/B50E.c:36",
    0x0420: "reached through a form the scan cannot see: passed to a record "
            "helper as a bare hex literal, `add_full_product_to_dptr"
            "(0x420,0x60,...)` at pd/34A5.c:18",
    0x043A: "reached through a form the scan cannot see: passed to a 16-bit "
            "pair helper as a bare hex literal, `read_xdata_pair_to_r3r4"
            "(0x43a)` at bank1/AD77.c:22",
    # registers.yaml records four EC-side sites, all read-modify-writes, at
    # bank1 0x8190, 0x81D1, 0x8246 and 0x826A -- in the gaps between the
    # exported functions 0x80EF, 0x8202, 0x820F and 0x8300. Seeding that
    # routine needs `--mode rebuild-project`, which this change does not do.
    # That is a gap in coverage, not a statement about the byte.
    0x0457: "in a routine no export covers: four bank1 read-modify-writes at "
            "0x8190/0x81D1/0x8246/0x826A, between the exported functions "
            "0x80EF, 0x8202, 0x820F and 0x8300",
    # No token, no name, no hex literal in any decompiled body and no "
    # `mov DPTR,#0x726` in any committed .asm. The registers.yaml note is the
    # record of what was tried: a driver write was accepted and the bit moved,
    # and no read of the address has ever been found by any method.
    0x0726: "not found by this method: no token, no name, no literal and no "
            "`mov DPTR` seed in any committed .asm; registers.yaml's OEM_9 row "
            "records an accepted write with no read found by any method",
    # BLIND_SPOT's first entry, and the one of the pair that is findable: it
    # is reached as a code pointer, `&DAT_CODE_0733` at bank0/94D0.c:55, inside
    # bank0:0x94D0=copy_code_table_into_0730_07a7.
    0x0733: "reached through a form the scan cannot see: behind a CODE "
            "pointer, `&DAT_CODE_0733` at bank0/94D0.c:55 -- BLIND_SPOT's "
            "findable half",
    # BLIND_SPOT's second entry, and the one no spelling reaches:
    # `sVar5 = 0x735; ... *(char *)(sVar5 + bVar2)` at bank0/94D0.c:66 and
    # :74, a base literal plus a runtime index.
    0x0735: "reached through a form the scan cannot see: a base literal plus a "
            "runtime index, `sVar5 = 0x735; *(char *)(sVar5 + bVar2)` at "
            "bank0/94D0.c:66 -- BLIND_SPOT's unspellable half",
    # The four AC-side lightbar bytes, one entry in registers.yaml split four
    # ways by gen_xdata_symbols.py's name-split. Nothing in the tree names or
    # seeds any of them, and the registers.yaml note records why that is not
    # this method's blind spot: a live write to each had no observable
    # effect, the vendor log names an ITE HID lightbar, and the board exposes
    # a second HID device the EC does not drive.
    0x0748: "not found by this method: no token, no name, no literal and no "
            "`mov DPTR` seed; registers.yaml records a live write with no "
            "observable effect, a vendor HID lightbar log line, and a second "
            "HID device the EC does not drive",
    0x0749: "not found by this method: as 0x0748 -- same registers.yaml "
            "name-split entry, same live null result",
    0x074A: "not found by this method: as 0x0748 -- same registers.yaml "
            "name-split entry, same live null result",
    0x074B: "not found by this method: as 0x0748 -- same registers.yaml "
            "name-split entry, same live null result",
    # A capability byte the driver reads. registers.yaml's note is that this
    # firmware build does not reference it; nothing in the tree or any
    # committed .asm names it.
    0x0765: "not found by this method: no token, no name, no literal and no "
            "`mov DPTR` seed; registers.yaml records that this firmware build "
            "does not reference it",
    # The repository's own canonical retraction, and the reason this block's
    # vocabulary has no word for absence. Four independent zero readings were
    # once called "definitively gone" and were all insufficient: the Windows
    # service writes exactly this address, and Windows genuinely caps charging.
    # Zero direct `mov DPTR` sites proves only that this scan cannot see how.
    # *** 2026-09-25, issue #256: the two rows `named_in_tree` was missing, added
    # here rather than worked around in the pin. #282 walked both bytes and gave
    # each a registers.yaml row with a note, and those notes are the evidence
    # this entry is derived from. The vocabulary is the block's own: no token, no
    # name, no hex literal and no `mov DPTR` seed in the committed tree, so the
    # zero is a property of the methods rather than of the bytes. Both are
    # `unknown-not-absent` in registers.yaml for exactly that reason, and
    # `ec-07d6-07d7-sites.md` §5 is where the computed-DPTR blind spot (#110)
    # that neither can rule out is worked through for the whole 0x07 page.
    0x07C7: "not found by this method: no token, no name, no hex literal and no "
            "`mov DPTR` seed in the committed tree; registers.yaml's XDATA_07C7 "
            "note records the same zero from trace_xdata_refs.py over both "
            "images, against the computed-DPTR blind spot of #110 that "
            "ec-07d6-07d7-sites.md 5 works through for this page",
    0x07C8: "not found by this method: as 0x07C7, the byte after it and outside "
            "the same DSDT field list, with registers.yaml's XDATA_07C8 note "
            "carrying the same two records and the same unexcluded blind spot",
    0x07B9: "not found by this method: zero direct `mov DPTR` sites, which is "
            "the signal findings.md retracted for this very address -- the "
            "Windows service writes it as part of BatteryProtection2",
    # The three battery-side lightbar bytes. **Not found by this method**: no
    # token, no name, no hex literal and no `mov DPTR` seed for any of them in
    # any committed .c or .asm -- so the whole of the evidence is in the image,
    # reached by a different method over different bytes, and it is recorded as
    # such rather than claimed as a form this tool can point at. The
    # registers.yaml 9/4/10 counts are file-wide and all of them are in the PD
    # image; `lightbar-bat-flow.md` tables them per site from
    # `trace_xdata_refs.py`, e.g. `0x07E3` at image 0x25F03 handing DPTR to
    # `lcall 0x10E8`, which writes 0x07E3-0x07E5. Re-derive with that sweep
    # over `ec/firmware/GMxMGxx_11.800`, not with this tool.
    0x07E3: "not found by this method: no token, no name, no literal and no "
            "`mov DPTR` seed in the committed tree; lightbar-bat-flow.md's "
            "trace_xdata_refs.py sweep puts a DPTR handoff to a writer at "
            "image 0x25F03, a different method over the image",
    0x07E4: "not found by this method: as 0x07E3, written by the same handoff "
            "as the middle byte of a 0x07E3-0x07E5 store",
    0x07E5: "not found by this method: as 0x07E3, plus the 0x6610 handoff to "
            "the PD writer at pd/1041.c, which stores four bytes from an entry "
            "pointer rather than naming one",
}

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
#
# 2026-09-25, issue #263: read 8317 -> 8341, passed-to-call 543 -> 534,
# address-taken 270 -> 267; write and read+write stand. Measured against a
# pristine checkout of the parent commit as well as against this branch, and the
# two do not agree about how much of the movement is this change's: 16 of the 24
# read references, and all 5 of the passed-to-call ones, were already there on
# `main` before this branch touched anything. The rest is the arity effect
# docs/findings.md 18 records, running in the direction #238 did not see --
# committing 88 signatures made 11 call sites pass more arguments and 17 pass
# fewer, and the three buckets that describe an argument rather than a plain
# access are where those land. See the dated block above ORACLE for the census
# totals and ec/annotations/xdata-register-map.md 7.2 for the per-address
# account.
BUCKET_TOTALS = {"read": 8341, "write": 3195, "read+write": 2482,
                 "passed-to-call": 534, "address-taken": 267}

# Issue #554: what `scan(export_ownership=True)` says on this tree, pinned the
# same way BUCKET_TOTALS is, so the de-duplicated census stays a measurement
# rather than a number in a paragraph. The default is unchanged and
# `xdata-06c2-06db-timers.md` 6a carries the before/after; these are the "after"
# half of that table.
#
# **The default is off and stays off.** The flip is a tree-wide renumbering --
# `cluster_key` and every citation keyed to one -- and it is the function
# boundary that has to land first (the sibling issue, recorded in-tree as
# xdata-06c2-06db-timers.md 8 item 7). Measured on this tree the flip moves
# `cluster_key` on 35 of the 430 clusters, breaks 5 of the 10 hand names in
# xdata-cluster-names.csv, and adds 2 clusters. Those four figures are the
# argument for deferring it, so they are pinned here too, and the --self-test
# ownership block asserts all four rather than leaving the promise to a reader.
#
# **The plan stage's estimate for this pass was 9112 references with 0x05E0
# falling out of the census entirely; the committed tool measures 9401 with
# nothing lost, and both are recorded because the difference is the detector,
# not the arithmetic.** The plan's detector folded `bank1/8E91.c` -- the only
# export in the tree that spells `DAT_EXTMEM_05e0` -- into a larger body, so
# the pass skipped the one file carrying the address. This one does not:
# 8E91.c owns its own two-file class, so the address survives. The plan's
# "loses an address" result is not a property of export ownership, it is a
# property of that grouping, which is why the rule is a committed tool and the
# figures are re-derived rather than carried forward.
OWNERSHIP = {
    "distinct": 1171, "refs": 9401,
    "main_distinct": 1062, "main_refs": 8543,
    "buckets": {"read": 4920, "write": 2707, "read+write": 1018,
                "passed-to-call": 500, "address-taken": 256},
    # Addresses present without the pass and absent with it. Empty here, and
    # that is a measurement rather than an absence: it is the failure the pass
    # would have if an owner were not a superset of its non-owners, and it is
    # pinned so a re-export that makes it non-empty says so.
    "lost": (),
    "moved": 228,
    # The cost of flipping the default, which is why it has not been flipped.
    "clusters": 432, "cluster_keys_kept": 395, "hand_names_kept": 5,
}

# Issue #280's corpus-wide direction invariant: the numbers
# `direction_invariant()` returns against the committed tree today, pinned the
# way BUCKET_TOTALS is so a re-export that moves either is visible in a diff.
#
# INTERNAL, like BUCKET_TOTALS and for the same reason -- these are this
# tool's own reading summed back to itself. What makes this one worth pinning
# anyway is the assertion it carries rather than the arithmetic: `write` and
# `read+write` imply an assignment follows, measured by a predicate that never
# consults the classifier that produced the bucket. The pre-fix `store_target()`
# fails it on 838 occurrences, which is what makes the width below a
# measurement and not a decoration.
DIRECTION_INVARIANT = {
    # Occurrences the census buckets `write` or `read+write`, and the distinct
    # addresses carrying at least one. The width, against HAND_CHECKED's five.
    #
    # 2026-09-25, issue #263: write_like 5662 -> 5677 and assign_shaped
    # 5664 -> 5679, with `deref_surplus` and `eq_after` unchanged. Measured
    # against a pristine checkout of the parent commit, the whole +15 was
    # **already on `main`** before this branch: this change moved neither. The
    # census totals in the same commit moved by one reference, so a reader who
    # assumed the two pins move together would have blamed this batch for a
    # drift it did not cause. The width is what a re-export changes and the
    # surplus is what it does not, and both are worth pinning for that reason.
    "write_like": 5677, "write_like_addrs": 1008,
    # What the second pass accepts. Two more than `write_like`, and the two
    # are not slop: they are 0x048A's `*`-dereference stores, which
    # `store_target()` excludes for cause and a necessary condition does not
    # have to exclude. The self-test asserts that is the *only* difference,
    # which is the exemption rule: a per-address allowlist inside the
    # invariant would be the five-address problem at larger scale, and this
    # instead pins the surplus, its size, and its shape.
    "assign_shaped": 5679, "deref_surplus": 2,
    # The tree-wide `==` count, quoted in the module docstring and in
    # xdata-register-map.md §4.3. Asserted so the prose and the code cannot
    # drift apart silently.
    "eq_after": 838,
}

# Direction, per address, derived by reading the decompiled C and re-derivable
# with the greps cited in each entry -- not by running this tool. That is the
# whole point: an internal consistency check passes on a misclassified
# comparison, because the misclassification is itself internally consistent, and
# 838 `==` comparisons were classified as stores for exactly that long (issue
# #178). Each value is the per-bucket reference counts plus `writers`, the
# number of distinct functions holding a write or read+write reference of their
# own. An entry here that the census disagrees with is a disagreement between a
# reading and a tool, and both are printed.
#
# **What this is for, now that DIRECTION_INVARIANT covers the whole tree.** The
# invariant says an assignment *follows*; this says the per-bucket *counts* are
# right, including `writers`, which is a distinct function and not a direction
# at all. A row can have every occurrence assignment-shaped and still count its
# writers wrongly, and nothing in the invariant would notice. That is the gap
# the five fill, and it is why the hand check is not redundant with the wider
# net.
#
# **Why five.** They are a shape catalogue, not a sample, and a sixth address
# that repeats one of the five shapes buys nothing: 0x0440 is all-read with no
# writer, 0x0860 is the misread dispatch byte, 0x0443 is the read-modify-write
# the `==` fix must *not* move, and 0x04FE/0x04FF are the 16-bit-half pair held
# together by a shared writer. What that leaves uncovered is named rather than
# glossed: an address whose *counts* are wrong while its shape is ordinary --
# a 0x0440-shaped read that a function is wrongly credited with writing, or a
# `writers` count built from a reader. A shape the five do not cover cannot be
# caught here, and widening the list without naming a new shape is how a
# hand check turns back into the five-address problem the invariant was added
# to replace.
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
    # 17 references: 14 `==` inside bank0/D091.c's dispatch test (lines 43, 47,
    # 69, 70, 73, 74 and 75 -- the later ones are multi-line boolean chains,
    # three occurrences to a line), the dispatch argument itself at
    # bank0/D091.c:81, a `= 0xff` at bank0/D281.c:18 and a `= 0` at
    # bank0/D289.c:17. Two stores in two functions, and the dispatch argument
    # is `passed-to-call` rather than a read. The worst-looking row the phantom
    # writers produced: it read as 0 read / 13 write / 3 read+write, a pure
    # write-side dispatch byte.
    #
    # CORRECTION (2026-09-24, issue #281): the line numbers above were 30, 34, 56,
    # 57, 60, 61 and 62, with the dispatch argument at :69 -- the seven `==` lines
    # 13 lower than the committed file and the dispatch argument 12. They were
    # right when this entry was written (#206) and still right at 40744da^; they
    # went stale in #225, which rewrote D091.c and grew its correction header by
    # 13 lines -- the `==` shift exactly, and the dispatch argument one less
    # because that rewrite also reflowed a closing paren onto the line above it.
    # Issue #281 quotes them verbatim, so the wrong ones stay visible here rather
    # than only in the history. A bucket total could never have caught it: every
    # number in this entry is still right, and a line number is not a number the
    # census sums. check_site_census.py re-checks them per site against
    # classify()'s own output and fails if they drift again.
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


def store_target(text: str, start: int, end: int, eq_guard: bool = True) -> bool:
    """True if this occurrence is the assignment target itself.

    Every `=`-taking occurrence in the committed tree has `;`, `{`, `}`, `(`,
    `:`, `,` or `*` immediately before it -- Ghidra never emits a store
    through a larger lvalue -- so "the `=` follows" is the whole test.

    Two things are then excluded, both about what the `=` belongs to rather
    than to the lvalue. `*` before the address: a store through a dereference
    is a store to wherever the pointer points, not to this address.
    `==` after it: that is a comparison, and a comparison uses the value
    without storing one.

    `eq_guard=False` is `--no-eq-guard`, and drops only that second exclusion:
    the pre-#178 classifier, kept runnable so the guard's effect stays
    measurable rather than becoming a paragraph of remembered numbers."""
    nxt = text[end:]
    stripped = nxt.lstrip()
    if not any(stripped.startswith(a) for a in ASSIGN):
        return False
    # A separate test rather than a reordering of ASSIGN, because the two
    # exclusions are unrelated and `==` is by far the commoner of them:
    # 838 occurrences in the committed tree against two dereference stores.
    if eq_guard and stripped.startswith("=="):
        return False
    left = text[:start].rstrip()
    return not (left and left[-1] == "*")


def assign_after(text: str, end: int) -> bool:
    """Does an assignment follow this occurrence? Issue #280's second pass.

    Deliberately not `store_target()` and not a call into it. The predicate is
    only "the text after the token begins with `=`, and does not begin with
    `==`", which is a *necessary condition* that `store_target()`'s first test
    already implies. Asserting a consequence of the classifier is a different
    act from re-running it: a re-run would agree with itself by construction,
    and would still have passed on the pre-fix classifier that `HAND_CHECKED`
    exists to catch.

    The `*`-dereference exclusion is deliberately absent, and leaving it out is
    what keeps this a necessary condition rather than a restatement. It is a
    second, independent conjunct in `store_target()`, and a store through a
    dereference still has an `=` after the address, so requiring it here would
    add nothing except a second copy of the thing under test."""
    nxt = text[end:].lstrip()
    return nxt.startswith("=") and not nxt.startswith("==")


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


def classify(text: str, start: int, end: int, addr: str, func_names,
             eq_guard: bool = True) -> str:
    """One occurrence -> one of BUCKETS. See the module docstring for why
    `passed-to-call` and `address-taken` are buckets of their own."""
    left = text[:start].rstrip()
    if left.endswith("&"):
        return "address-taken"
    if store_target(text, start, end, eq_guard):
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


def load_ownership() -> dict:
    """out_file -> the export-ownership row, from the committed map.

    Read, not re-derived: `export_ownership.py` owns that rule and `--check`
    there holds the CSV to a fresh derivation, so re-running it here would be a
    second implementation of the same decision in a file that does not own it.
    An `index.csv` row the map does not know is a failure, not a default -- it
    would mean the census was silently reading an export the map says is a
    copy, which is the whole defect."""
    out = {}
    with open(OWNERSHIP_CSV, newline="") as f:
        for row in csv.DictReader(f):
            out[row["out_file"]] = row
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


def scan(by_file, names, func_names, symbols, eq_guard: bool = True,
         export_ownership: bool = False, ownership=None):
    """(per-program census, call graph, raw occurrence count) over the tree.

    An address is reached from many files in one program, so the per-file
    counts accumulate into the program's entry rather than replacing it.

    The raw count is what the files say before comments are blanked, kept so
    the self-test can pin the difference the ORACLE block records rather than
    leave it as a claim in prose.

    **`export_ownership` reads each routine once, from the export that owns
    it.** `index.csv` splits `bank1:0x8001`-`0x8189` into 42 rows whose `.c`
    files all decompile the same routine -- 16 to 47 statements each, 0.87 to
    0.98 containment against the owner's 47 -- so the walk above counts that
    one routine 42 times: 0x0843 reads 168 references where the routine reads
    it 4, and 42 `funcs` entries stand for 1. When the flag is set, a file the
    map marks `shared` is not opened at all -- its references are already
    counted through the owner, because the owner's body is the superset. That
    is the whole of it, and the default stays off for the measured reason: the
    pass is a text heuristic rather than a function boundary, and flipping it
    renumbers the whole tree -- `cluster_key` on 35 of the 430 clusters and 5
    of the 10 hand names, in OWNERSHIP. The mechanism behind that is worth
    stating rather than only measuring: a non-owner whose owner is *not* a
    superset would take its references out of the census with them. On this
    tree none is, so `OWNERSHIP["lost"]` is empty; see
    annotations/xdata-export-ownership.md."""
    pattern = occurrence_re(symbols)
    by_name = {name: addr for addr, name in symbols.items()}
    census = {p: {} for p in MAIN_PROGRAMS + (PD_PROGRAM,)}
    calls = {}
    raw = collections.Counter({s: 0 for s in SPELLINGS})
    shared = {}
    if export_ownership:
        ownership = load_ownership() if ownership is None else ownership
        missing = sorted(set(by_file) - set(ownership))
        if missing:
            raise SystemExit(f"error: {OWNERSHIP_CSV} has no row for "
                             f"{len(missing)} index.csv exports, first "
                             f"{missing[0]}: run export_ownership.py --map")
        shared = {f for f, r in ownership.items() if r["shared"] == "yes"}
    for out_file, row in by_file.items():
        if out_file in shared:
            continue
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
            bucket = classify(text, m.start(), m.end(), m.group(0), func_names,
                              eq_guard)
            entry = per_addr[addr]
            entry["refs"] += 1
            entry["buckets"][bucket] += 1
            entry["funcs"][key] += 1
            entry["dirs"][key].add(bucket)
            entry["spellings"].add(spelling)
        for addr, entry in per_addr.items():
            absorb(census[row["program"]].setdefault(addr, blank_entry()), entry)
    return census, calls, raw


def direction_invariant(by_file, symbols, func_names):
    """(shaped, offenders, surplus, eq_after, eq_in_write) for issue #280.

    A second walk of the same committed text as `scan()`, asking a different
    question. `scan()` decides a bucket per occurrence; this one records, per
    occurrence, only what follows the token.

    **It is not a second pair of eyes.** Same files, same regex, same
    `strip_comments()`, and the bucket each occurrence is measured against is
    the one `scan()` just produced. What it is *not* is a re-implementation of
    the rule under test, and that is the whole of its value: the `==`
    rejection that issue #178 added lives inside `store_target()`, while
    `assign_after()` is a primitive that never consults it. Re-introduce the
    old classifier and the two disagree on 838 occurrences.

    The offender lists are why the return value is this shape. A count says a
    number moved; `file!line address` says where to look, so a failure here is
    a worklist rather than a diff to re-derive by hand.

    `surplus` is the exemption rule made measurable. `assign_after()` accepts
    strictly more than `store_target()` does, because it drops the `*` test.
    Every occurrence in `surplus` is therefore expected to be a dereference
    store, and the caller asserts exactly that -- so a new shape slipping
    through shows up as a named site instead of quietly widening a tolerance.
    """
    pattern = occurrence_re(symbols)
    by_name = {name: addr for addr, name in symbols.items()}
    shaped = collections.Counter()
    offenders, surplus = [], []
    eq_after = eq_in_write = 0
    for out_file in sorted(by_file):
        with open(os.path.join(DECOMPILED, out_file)) as f:
            text = strip_comments(f.read())
        for m in pattern.finditer(text):
            addr = (int(m.group(1), 16) if m.group(1) is not None
                    else by_name[m.group(2)])
            bucket = classify(text, m.start(), m.end(), m.group(0), func_names)
            nxt = text[m.end():].lstrip()
            store_shape = assign_after(text, m.end())
            site = (f"{out_file}!{text.count(chr(10), 0, m.start()) + 1} "
                    f"{hexaddr(addr)}")
            if store_shape:
                shaped[addr] += 1
            if nxt.startswith("=="):
                eq_after += 1
                if bucket in ("write", "read+write"):
                    eq_in_write += 1
            if bucket in ("write", "read+write") and not store_shape:
                offenders.append(f"{site} ({bucket})")
            elif store_shape and bucket not in ("write", "read+write"):
                # Accepted here and not counted by the census: the only shape
                # that can happen is a store through a `*` dereference, because
                # every other conjunct of `store_target()` is a *restriction*.
                left = text[:m.start()].rstrip()
                if not (left and left[-1] == "*"):
                    surplus.append(f"{site} ({bucket})")
    return shaped, offenders, surplus, eq_after, eq_in_write


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


def cluster_key(g: str, addrs) -> str:
    """The cluster's content hash: a function of the cluster, not of its rank.

    The program is in the hash because the two programs have separate XDATA
    maps and a shared address number is not a shared byte, so a main-EC cluster
    and a pd-image cluster with identical membership are different clusters and
    must not collide. `sorted()` is what makes the key order-independent: the
    membership is a set, and a key that changed because a CSV column was sorted
    a different way would be a key that lies."""
    text = g + " " + " ".join(hexaddr(a) for a in sorted(addrs))
    return "k" + hashlib.sha256(text.encode()).hexdigest()[:CLUSTER_KEY_HEX]


def load_cluster_names() -> dict:
    """`cluster_key` -> `cluster_name` from the hand-edited names file.

    `ec/annotations/xdata-cluster-names.csv` is this tool's editable surface for
    names, the way `ghidra-functions.csv` is for functions: the one file here a
    human adds a row to. It is keyed by `cluster_key` rather than by
    `cluster_id` because the rank is the thing that moves -- a row keyed by a
    rank would name a different cluster after every reshuffle, which is the
    whole problem. A missing file is an empty table and not an error: the
    census is complete without names, and a name is a label, not a count."""
    out = {}
    try:
        with open(NAMES_CSV, newline="") as f:
            for row in csv.DictReader(f):
                key = row["cluster_key"].strip()
                if key:
                    out[key] = row["cluster_name"].strip()
    except FileNotFoundError:
        return {}
    return out


def load_cluster_rows(path) -> list:
    """The rows of a clusters CSV, or [] when there is no file to read.

    A census written before the `cluster_key` and `cluster_name` columns are
    still a census: `carry_names()` reads it with `dict.get`, so a missing
    column is a cluster with no name rather than a crash."""
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def carry_names(old_rows, seeded, new_rows):
    """({new cluster_key: name}, one report record per new cluster).

    A hand name is a claim about a *cluster*, and a cluster is its membership,
    so the name follows the membership rather than the rank. Five outcomes, and
    they are five because they are five different claims:

        seeded   the names file names this exact key -- a human said so
        exact    a named row of the committed census has this exact key
        overlap  a named row's membership scores >= CARRY_MIN_JACCARD against
                 this one. A weaker claim, and the score is in the record with
                 it: a name carried at 0.98 and one carried at 0.51 are not the
                 same statement about the firmware
        tie      two named rows are the joint best match. Which of them the new
                 cluster is, is a fact about the clustering and not a coin this
                 function flips, so no name is carried and both are reported
        none     nothing cleared the threshold. **Not carried by this method**,
                 never gone -- a cluster the decompiler stopped producing is a
                 different claim from one that stopped existing, and the report
                 prints the best score it saw so a reader can tell "nothing came
                 close" from "nothing was even looked for"

    `old_rows` is read from the *committed* census rather than from
    `--out-clusters`, because the output is the thing being written: reading it
    back would make the carry a function of where this run happens to write.
    That is what lets a guard-off or a different-threshold run be carried from
    the census that is actually committed beside the prose."""
    old_named = [r for r in old_rows if (r.get("cluster_name") or "").strip()]
    by_key = {r.get("cluster_key", ""): r for r in old_rows}
    names, report = {}, []
    for row in new_rows:
        key, addrs = row["cluster_key"], set(row["addrs"].split())
        name, how, score, from_key, detail = "", "", 1.0, "", ""
        if seeded.get(key):
            name, how = seeded[key], "seeded"
        elif by_key.get(key, {}).get("cluster_name", "").strip():
            hit = by_key[key]
            name, how, from_key = hit["cluster_name"].strip(), "exact", key
        else:
            scored = sorted(
                ((jaccard(addrs, set(r["addrs"].split())),
                  r["cluster_name"].strip(), r.get("cluster_id", ""),
                  r.get("cluster_key", ""))
                 for r in old_named),
                key=lambda t: (-t[0], t[1], t[2], t[3]))
            best = scored[0][0] if scored else 0.0
            winners = [t for t in scored if t[0] == best]
            score = best
            if best >= CARRY_MIN_JACCARD and len(winners) == 1:
                _s, name, _cid, from_key = winners[0]
                how = "overlap"
            elif best >= CARRY_MIN_JACCARD:
                how = "tie"
                detail = " == ".join(f"{n} ({cid})" for _s, n, cid, _k in winners)
            else:
                how = "none"
        if name:
            names[key] = name
        report.append({"cluster_id": row["cluster_id"], "cluster_key": key,
                       "name": name, "how": how, "jaccard": score,
                       "from_key": from_key, "detail": detail})
    return names, report


def name_clusters(cluster_rows, old_rows, seeded):
    """Fill `cluster_name` in, and return the carry report for the modes to print."""
    names, report = carry_names(old_rows, seeded, cluster_rows)
    for row in cluster_rows:
        row["cluster_name"] = names.get(row["cluster_key"], "")
    return report


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


def co_reading_groups(census, funcs, floor: int):
    """(group of each function key, the groups) for the co-reading relation.

    Two `.c` files in one program are co-readings when they name the same
    `floor` or more XDATA addresses; a group is a connected component of that.
    The shape of the answer deliberately mirrors `components()`: components
    rather than a greedy cover, because the relation is not transitive and a
    greedy pass would make the output depend on file order, and every file
    landing in exactly one group so the caller can account for all of them.

    **Per program, and the split is the point.** The two images have separate
    XDATA maps and a shared address number is not a shared byte, so grouping a
    `bank1` sweep export with a `pd` reader on the same addresses would
    manufacture the co-reading it is supposed to measure. The self-test asserts
    that no group ever spans two programs.

    Pairs are enumerated through an address -> files index rather than over all
    pairs of files, because the relation is only decidable for files that share
    an address at all and most of the tree's 2,710 `.c` files name none. A pair
    is tested once and remembered, so a pair sharing forty addresses costs one
    intersection rather than forty.

    The returned group is the tuple of member keys, so it is hashable and can
    be a dict value; `groups` carries the same membership with the `out_file`
    names, the common core, and the listing sizes `index.csv` records for it,
    which is what the report's group table and the two new modes print. **The
    core is a count of addresses every member names, and a small one is the
    normal case for a transitive group** -- the six-file `bank0` group around
    `0x8749.c` has a one-address core -- `0x1804`, which all six read -- and
    those are six real readers that a neighbour connects. That is why the core is reported rather than the group
    being treated as one routine: the size pattern is the observable and "this
    file is a slice of a larger routine" is the hypothesis."""
    addrs_of = collections.defaultdict(set)      # out_file -> {addr}
    program_of = {}                             # out_file -> program
    key_of = {}                                 # out_file -> (program, addr)
    for program, block in census.items():
        for addr, entry in block.items():
            for key in entry["funcs"]:
                out_file = funcs[key]["out_file"]
                addrs_of[out_file].add(addr)
                program_of[out_file] = program
                key_of[out_file] = key
    group_of = {}
    groups = []
    for program in sorted(set(program_of.values())):
        files = sorted(f for f in addrs_of if program_of[f] == program)
        parent = {f: f for f in files}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        by_addr = collections.defaultdict(list)
        for f in files:
            for a in addrs_of[f]:
                by_addr[a].append(f)
        tested = set()
        for members in by_addr.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    x, y = members[i], members[j]
                    if (x, y) in tested:
                        continue
                    tested.add((x, y))
                    if len(addrs_of[x] & addrs_of[y]) < floor:
                        continue
                    rx, ry = find(x), find(y)
                    if rx != ry:
                        parent[rx] = ry
        members_of = collections.defaultdict(list)
        for f in files:
            members_of[find(f)].append(f)
        for _root, members in sorted(members_of.items()):
            if len(members) < 2:
                continue
            keys = tuple(sorted(key_of[f] for f in members))
            for key in keys:
                group_of[key] = keys
            groups.append({
                "program": program,
                "files": list(members),
                "core": set.intersection(*(addrs_of[f] for f in members)),
                # The listing sizes are the observable the boundary hypothesis
                # rests on: 42 files whose sizes sum to the run's 393 bytes, 16
                # of them a single instruction. `seed_basis` is deliberately
                # not read here -- it records how a listing was seeded, and
                # #179's annotation rows carried `annotation` with them, so it
                # no longer says which hypothesis produced the boundaries.
                # In `files` order, so a future reader can zip the two.
                "sizes": [int(funcs[key_of[f]]["size"]) for f in members],
            })
    return group_of, groups


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


def build(funcs, names, symbols, census, calls, threshold,
          group_of=None):
    """The two row sets the CSVs render, plus the summary the modes print.

    `group_of` is the co-reading relation's function-key -> group map from
    `co_reading_groups()`. It is a parameter and not a call inside so the
    modes that sweep the floor or collapse the groups can pass a relation built
    at a different floor or none at all, and so the two new columns and the
    clustering are computed from the same census in one pass. Defaulting to `{}`
    means "no groups", which is the honest reading of a relation that was not
    computed rather than one that found nothing."""
    groups = {g: merge_group(census, PROGRAM_COL[g]) for g in GROUPS}
    group_of = group_of or {}
    program_of = {}
    for g in GROUPS:
        for a in groups[g]:
            program_of.setdefault(a, []).append(g)

    clusters = {g: components(groups[g], threshold) for g in GROUPS}
    # **The ids are a rank, and a rank is not an identity.** Numbering is by
    # size, then references, then lowest address, so `main-ec-001` is whichever
    # cluster sorts into first place -- and one change anywhere in the ranking
    # reshuffles every id below the one that moved. Issue #253 is the measured
    # version of that: with the `==` guard removed the committed 427 ids become
    # a 439-cluster census, 48 surviving intact and 379 keeping their number and
    # changing what the number names. This comment used to say the ids were
    # "stable across regenerations" and that `main-01` was the same cluster today
    # and after a re-run; both halves were false, and the second named an id shape
    # this tool does not emit. `cluster_key` below and `cluster_name` after it
    # are the identity a prose citation can survive the ranking on, and
    # `cluster_id` stays exactly as it was because the two CSVs and every page in
    # the tree name it.
    cluster_id = {}
    cluster_key_of = {}
    cluster_rows = []
    for g in GROUPS:
        ordered = sorted(clusters[g].values(),
                         key=lambda v: (-len(v), -sum(groups[g][a]["refs"] for a in v), v[0]))
        for n, members in enumerate(ordered, 1):
            cid = f"{g}-{n:03d}"
            key = cluster_key(g, members)
            for a in members:
                cluster_id[(g, a)] = cid
                cluster_key_of[(g, a)] = key
            cluster_rows.append(cluster_rows_build(g, cid, key, members, groups[g],
                                                   names, funcs, calls, symbols,
                                                   group_of))

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
            "cluster_key": cluster_key_of.get((primary, addr), ""),
            # The two halves of the same statement about a *source count*.
            # `co_reading` is how many of this address's touching functions are
            # members of a multi-file group, and `sources_beyond` is the
            # difference -- the sources that are not copies of one another by
            # this relation. Neither moves `refs`: a source count that a
            # de-duplication would shrink is a claim about boundaries this
            # change deliberately does not make, and the arithmetic
            # `co_reading + sources_beyond == functions_touched` is what the
            # self-test holds on every row. On a `program=both` row the two are
            # counted over the combined function set, which is what
            # `functions_touched` counts too, so a `main-ec` sweep export and a
            # `pd` reader are never mistaken for co-readings of each other.
            "co_reading": sum(1 for f in funcs_touched if f in group_of),
            "sources_beyond": sum(1 for f in funcs_touched if f not in group_of),
        })
    return register_rows, cluster_rows, groups


def cluster_rows_build(g, cid, key, members, group, names, funcs, calls, symbols,
                       group_of):
    """One row of xdata-clusters.csv.

    `shared_functions` is the subset touching two or more of the cluster's
    addresses -- the co-occurrence that put them together. `callees` is the
    call-graph axis: the routines the most of those functions call, capped at
    TOP_CALLEES with the overflow counted in the cell.

    The three co-reading columns ask how much of that co-occurrence one set of
    files supplies. `co_reading` counts the cluster's touching functions that
    are in a group, `co_reading_refs` is what the largest single group supplies
    **of this cluster's own references**, and `co_reading_dominant` says
    whether that is more than half. The flag is a place to look and not a
    defect -- it is uninformative at size 1, where a single function is all of
    the cluster's refs by construction -- so the share is the readable number
    and the boolean is only a way to sort for it."""
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
    # What each co-reading group supplies of *this* cluster's references, so
    # the comparison is against the cluster's own `refs` and not against the
    # group's size. A group that names forty addresses contributes only what it
    # says about this cluster's forty-three.
    supplied = collections.Counter()
    for a in members:
        for f, n in group[a]["funcs"].items():
            if f in group_of:
                supplied[group_of[f]] += n
    top_group_refs = supplied.most_common(1)[0][1] if supplied else 0
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
        "cluster_key": key,
        # Filled in by name_clusters(), which is where a name carried forward
        # from the committed census lands. Empty is "no name", which is the
        # state of 417 of the 427 clusters and is not a claim about them.
        "cluster_name": "",
        "co_reading": sum(1 for f in touching if f in group_of),
        "co_reading_refs": top_group_refs,
        "co_reading_dominant": "yes" if top_group_refs * 2 > refs else "no",
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


def census_and_groups(args, funcs, by_file, names, symbols, floor=None):
    """(census, calls, co-reading group_of, raw occurrence counts) -- the one
    read of the tree.

    `--check`, the writing default, `--self-test` and the three new modes all
    need the same census and the same relation, and computing the relation in
    more than one place is how two of them would come to disagree about what a
    group is. The raw counts ride along because the self-test pins them, and
    re-reading the tree to get them would double its cost for no other reason.
    `floor=None` means COREADING_MIN_CORE, which is the floor the CSVs and every
    oracle are read at."""
    func_names = {r["name"] for r in funcs.values()}
    census, calls, raw = scan(by_file, names, func_names, symbols,
                              not args.no_eq_guard, args.export_ownership)
    group_of, _groups = co_reading_groups(
        census, funcs, COREADING_MIN_CORE if floor is None else floor)
    return census, calls, group_of, raw


def generate(args):
    """(register_rows, cluster_rows, groups, carry report), or None after
    printing why.

    The carry is part of the generation rather than of the writing, so `--check`
    and the default agree about what a named cluster is -- the same reason
    `outputs()` exists for the two CSVs."""
    funcs, by_file = load_index()
    problems = check_file_set(by_file)
    if problems:
        return None
    names = load_names(funcs)
    symbols = load_symbols()
    census, calls, group_of, _raw = census_and_groups(args, funcs, by_file,
                                                      names, symbols)
    register_rows, cluster_rows, groups = build(funcs, names, symbols, census,
                                               calls, args.threshold, group_of)
    report = name_clusters(cluster_rows, load_cluster_rows(OUT_CLUSTERS),
                           load_cluster_names())
    return register_rows, cluster_rows, groups, report


def outputs(args, built):
    """[(rows, columns, path, text)] for the two CSVs, in write order.

    Both modes go through this one list so `--check` and the writing default
    can never disagree about what a fresh generation is -- which is the whole
    reproducibility claim the two CSVs rest on."""
    register_rows, cluster_rows = built[0], built[1]
    out = []
    for rows, columns, path in ((register_rows, REGISTER_COLUMNS, args.out_registers),
                                (cluster_rows, CLUSTER_COLUMNS, args.out_clusters)):
        out.append((rows, columns, path, render(rows, columns)))
    return out


def print_carry(report) -> None:
    """What happened to every hand name, on stderr so the CSVs stay pipeable.

    Printed by every mode that builds a census, because a name that appears in
    `xdata-clusters.csv` without saying how it got there is the overclaim
    `CLAUDE.md` rules out: `seeded` and `exact` are the same claim, `overlap` is
    a weaker one with a score, a `tie` was not carried at all, and a `none` is
    this rule not firing rather than a cluster that went away."""
    tallies = collections.Counter(r["how"] for r in report)
    print("  names: " + ", ".join(
        f"{n} {tallies[h]}" for h, n in
        (("seeded", "seeded"), ("exact", "exact"), ("overlap", "carried by overlap"),
         ("tie", "tied, not carried"), ("none", "with no name"))), file=sys.stderr)
    for r in report:
        if r["how"] in ("seeded", "exact"):
            continue
        if r["how"] == "overlap":
            print(f"    {r['cluster_id']} carries {r['name']} by overlap, "
                  f"Jaccard {r['jaccard']:.2f} from {r['from_key'] or 'an unnamed old row'}"
                  f" -- re-key {os.path.relpath(NAMES_CSV, EC_DIR)} if the name moved",
                  file=sys.stderr)
        elif r["how"] == "tie":
            print(f"    {r['cluster_id']} is claimed by two names at Jaccard "
                  f"{r['jaccard']:.2f} ({r['detail']}); not carried by this method",
                  file=sys.stderr)


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
    print_carry(built[3])
    return rc


def write(args) -> int:
    built = generate(args)
    if built is None:
        return 1
    register_rows, cluster_rows, groups = built[:3]
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
    print_carry(built[3])
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
    census, calls, group_of, raw = census_and_groups(args, funcs, by_file, names,
                                                     symbols)
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

    # `--no-eq-guard` has to be a switch on the `==` exclusion and on nothing
    # else, or the before/after in xdata-06c2-06db-timers.md 6a stops being a
    # measurement of the guard and becomes a measurement of this flag. Pinned
    # against the same literal table: every `==` snippet flips to `write`, and
    # every other snippet is untouched. The count is an assertion rather than a
    # loop over the committed tree, so it cannot be satisfied by a tree that has
    # stopped containing comparisons.
    def buckets_of(snippet, eq_guard):
        m = pattern.search(snippet)
        return classify(snippet, m.start(), m.end(), m.group(0), func_names,
                        eq_guard)

    eq_snippets = [s for s, _ in CLASSIFIER_SHAPE if "== " in s]
    flips = [s for s, _ in CLASSIFIER_SHAPE
             if buckets_of(s, False) != buckets_of(s, True)]
    check(f"--no-eq-guard flips exactly the {len(eq_snippets)} `==` snippets in "
          f"CLASSIFIER_SHAPE and no other (flipped {len(flips)})",
          flips == eq_snippets and eq_snippets)
    check("and each flipped `==` snippet becomes a `write`, which is the "
          "pre-#178 miscount this flag exists to reproduce",
          all(buckets_of(s, False) == "write" for s in eq_snippets))

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
    # The count, and then the set behind it. Asserting the count alone left
    # "which 150" discoverable only from this message; asserting the set makes
    # the count arithmetic over NOT_IN_TREE, so an address that appears or
    # disappears is a named entry rather than a shifted total.
    not_in_tree = set(symbols) - everywhere
    check(f"of the {len(symbols)} named addresses, {ORACLE['named_in_tree']} "
          f"appear in the decompiled tree at all (got {len(named)}: "
          f"{', '.join(hexaddr(a) for a in named)})",
          len(named) == ORACLE["named_in_tree"])
    # Issue #280. Both directions, so neither a missed address nor a stale
    # entry passes, and the diff is printed address by address either way.
    only_blocked = sorted(set(NOT_IN_TREE) - not_in_tree)
    only_found = sorted(not_in_tree - set(NOT_IN_TREE))
    check(f"issue #280: the {len(NOT_IN_TREE)} addresses xdata-symbols.csv names "
          f"and the census does not reach are the NOT_IN_TREE set, address for "
          f"address, so the {ORACLE['named_in_tree']} at named_in_tree is "
          f"{len(symbols)} - {len(NOT_IN_TREE)} rather than a number to be "
          f"taken on trust (in NOT_IN_TREE but now in the census: "
          f"{', '.join(hexaddr(a) for a in only_blocked) or 'none'}; in the "
          f"census gap but with no reason recorded: "
          f"{', '.join(hexaddr(a) for a in only_found) or 'none'})",
          not only_blocked and not only_found)
    # The vocabulary is the assertion, not a promise in a comment: a reason
    # that drifts into claiming the byte is gone would make every row below it
    # unfalsifiable, which is the overclaim CLAUDE.md rules out.
    vocab = {r.partition(":")[0].strip() for r in NOT_IN_TREE.values()}
    check(f"every NOT_IN_TREE reason begins with one of the three recorded "
          f"reasons {list(NOT_IN_TREE_REASONS)} (got "
          f"{', '.join(sorted(vocab - set(NOT_IN_TREE_REASONS))) or 'all of them'})",
          vocab <= set(NOT_IN_TREE_REASONS))
    claimed = [f"{hexaddr(a)} says {w!r}"
               for a, r in NOT_IN_TREE.items()
               for w in NOT_IN_TREE_FORBIDDEN if w in r.lower()]
    check(f"and none of them contains a word that would claim the byte is gone "
          f"{list(NOT_IN_TREE_FORBIDDEN)} -- a scan that finds no reference has "
          f"found no reference (offending lines: "
          f"{', '.join(claimed) or 'none'})",
          not claimed)
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

    # Issue #259. The two halves of one fact, asserted together because either
    # alone is misleading and only the pair is the point: the committed .asm
    # still carries 0x0390's `mov DPTR` site, AND the census still has no row
    # for it. That pairing is what stops a zero reading as absence. A reader who
    # finds the first is not looking at a dead byte, and a reader who finds the
    # second is not looking at an unreferenced one.
    #
    # The census half is expected to be False by construction here, so this
    # cannot be re-derived from the tree the way the oracle above is -- it is a
    # pin on a *disagreement* between two methods, and it is the assertion that
    # will fail first if a future export makes the decompiler spell the address
    # again. Both facts together are the policy: the census counts C-level
    # references and is a lower bound on the machine code, and an address that
    # leaves it is "not found by this method" until an .asm witness says
    # otherwise. docs/findings.md 4 is the rule this phrasing comes from.
    bank1_asm = read_asm("bank1")
    witness = xdata_space(bank1_asm, 0x0390)
    census_has_0390 = any(0x0390 in groups[g] for g in GROUPS)
    # Built before the f-string, because a witness that is gone is the case this
    # has to report cleanly -- indexing `witness` inline would raise instead.
    site = ("not found by this method" if witness is None
            else f"bank1/{witness[1]}.asm:{witness[2]}")
    check(f"issue #259: 0x0390 is carried by a `mov DPTR,#imm16` in the "
          f"committed bank1 .asm, reached at {site} -- an .asm is never "
          f"rewritten by an annotation, so the byte has a site in the machine "
          f"code whatever the C spells",
          witness is not None)
    check(f"and it still has no row in the census, because the callee at "
          f"bank1 0x9EA1 renders the address as CONCAT11(r4_value,r3_value) "
          f"over register names and the call site passes only the constants "
          f"0x90 and 3, which this token pattern cannot reach (census row "
          f"present: {census_has_0390})",
          not census_has_0390)

    register_rows, cluster_rows, _ = build(funcs, names, symbols, census, calls,
                                           args.threshold, group_of)
    old_rows = load_cluster_rows(OUT_CLUSTERS)
    carry = name_clusters(cluster_rows, old_rows, load_cluster_names())
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
    # The co-reading relation, the same shape of oracle and the same reason:
    # these eight are read off the decompiled tree by hand, so a relation that
    # grouped the wrong files fails here rather than summing correctly into the
    # two new columns. `co_reading + sources_beyond` is the arithmetic both
    # sides of the table are read through, and it is asserted on every row
    # below as well -- this is the external half, that one the internal one.
    co_wrong = {}
    for addr, expected in COREADING_CHECKED.items():
        row = by_addr.get(addr)
        got = ({k: int(row[k]) for k in ("co_reading", "sources_beyond")} if row
               else {"co_reading": "no row", "sources_beyond": "no row"})
        if got != {"co_reading": expected[0], "sources_beyond": expected[1]}:
            co_wrong[addr] = (expected, got)
    check(f"the hand-read co-reading oracle: {len(COREADING_CHECKED)} "
          f"addresses, {', '.join(sorted(COREADING_CHECKED))}, each read off "
          f"the decompiled tree by hand rather than by this tool, as "
          f"(co_reading, sources_beyond)"
          + (f" -- disagreed on {', '.join(f'{a} (expected {e}, got {g})' for a, (e, g) in sorted(co_wrong.items()))}"
             if co_wrong else ""),
          not co_wrong)
    check("and on every register row the two columns are a partition of the "
          "address's source functions: co_reading + sources_beyond == "
          "functions_touched, which is what keeps the new columns a *count* of "
          "files rather than a second reference count (rows where it does not "
          "balance: "
          f"{', '.join(r['addr'] for r in register_rows if int(r['co_reading']) + int(r['sources_beyond']) != int(r['functions_touched'])) or 'none'})",
          all(int(r["co_reading"]) + int(r["sources_beyond"])
              == int(r["functions_touched"]) for r in register_rows))
    check("and neither column moved a counting column: `refs` is the ORACLE "
          "total and the five bucket totals still sum to it, with the co-reading "
          "columns reading off the same rows",
          sum(int(r["refs"]) for r in register_rows) == total_refs and
          all(int(r["co_reading"]) <= int(r["functions_touched"])
              for r in register_rows))
    # The three group figures, which is what makes COREADING_MIN_CORE a
    # recorded choice: `--co-reading-sweep` prints this curve, and the largest
    # group is the counter sweep at every floor from 6 to 16.
    _go, co_groups = co_reading_groups(census, funcs, COREADING_MIN_CORE)
    co_sizes = sorted((len(g["files"]) for g in co_groups), reverse=True)
    check(f"the co-reading relation at floor {COREADING_MIN_CORE} -- a common "
          f"core of that many addresses between two files in one program -- "
          f"finds {COREADING_GROUPS} groups over {COREADING_FILES} files, "
          f"largest {COREADING_LARGEST} (got {len(co_sizes)}, "
          f"{sum(co_sizes)}, {co_sizes[0] if co_sizes else 0}; sizes "
          f"{co_sizes})",
          (len(co_sizes), sum(co_sizes), co_sizes[0] if co_sizes else 0)
          == (COREADING_GROUPS, COREADING_FILES, COREADING_LARGEST))
    # The program split, asserted as a property of the answer rather than of the
    # code that computes it: the two images have separate XDATA maps, and a
    # group spanning both would be a co-reading manufactured out of a shared
    # address *number*.
    spanning = [g["files"] for g in co_groups
                if len({f.split("/")[0] for f in g["files"]}) > 1]
    check(f"and no co-reading group spans two programs, which is the same split "
          f"the clustering never crosses and the reason `0x00B6` is in "
          f"COREADING_CHECKED at all (spanning groups: "
          f"{', '.join(' '.join(g) for g in spanning) or 'none'})",
          not spanning)
    # The 42-file sweep is one group of exactly 42, over a 19-address common
    # core, and the group's ends are the sweep's own first and last listing. A
    # sweep split across two groups would be a different claim from one group,
    # and the file count is what tells them apart. **The core is asserted, not
    # only printed**: it is the number that says the group is 42 copies of
    # overlapping coverage rather than 42 identical bodies, so a reader who
    # trusts the timers page's "all 42 decompile the whole body" is trusting
    # something this holds still.
    big = max(co_groups, key=lambda g: len(g["files"]))
    check(f"and the counter sweep of xdata-06c2-06db-timers.md §2 is one group "
          f"of exactly {COREADING_LARGEST} files, {COREADING_SWEEP[0]} to "
          f"{COREADING_SWEEP[1]}, over a {len(big['core'])}-address common "
          f"core -- one group rather than several, which is a claim about the "
          f"files and not about the boundaries (got "
          f"{len(big['files'])} files, {big['files'][0]} to {big['files'][-1]}, "
          f"core {len(big['core'])})",
          (len(big["files"]), big["files"][0], big["files"][-1],
           len(big["core"]))
          == (COREADING_LARGEST,) + COREADING_SWEEP + (COREADING_SWEEP_CORE,))
    # The §2 size pattern, now reproduced by the tool rather than counted by
    # hand: the 42 listings tile the 393-byte run and 16 of them are a single
    # instruction. Those three numbers are the boundary *evidence*; the
    # hypothesis is that the files are slices of one routine, and this asserts
    # only what index.csv records.
    check("and the group's 42 `index.csv` listing sizes sum to the run's 393 "
          "bytes with 16 of them a single instruction, which is the observable "
          f"the boundary hypothesis rests on (got {sum(big['sizes'])} over "
          f"{sum(1 for s in big['sizes'] if s == 1)} one-instruction listings)",
          sum(big["sizes"]) == 393 and sum(1 for s in big["sizes"] if s == 1) == 16)
    # The cluster columns, the same partition at cluster width plus the two
    # bounds that keep `co_reading_refs` comparable against the cluster's own
    # `refs` rather than against a group's size.
    check("the cluster columns hold: co_reading is at most the cluster's "
          "functions_touched, co_reading_refs at most its refs, and the "
          "dominance flag is exactly `co_reading_refs * 2 > refs` -- so the flag "
          "cannot disagree with the share it summarises"
          + (f" (offending rows: {', '.join(r['cluster_id'] for r in cluster_rows if not (int(r['co_reading']) <= int(r['functions_touched']) and int(r['co_reading_refs']) <= int(r['refs']) and (r['co_reading_dominant'] == 'yes') == (int(r['co_reading_refs']) * 2 > int(r['refs']))))or 'none'})"),
          all(int(r["co_reading"]) <= int(r["functions_touched"]) and
              int(r["co_reading_refs"]) <= int(r["refs"]) and
              (r["co_reading_dominant"] == "yes")
              == (int(r["co_reading_refs"]) * 2 > int(r["refs"]))
              for r in cluster_rows))
    # The counter-sweep cluster, pinned as the worked example the report quotes:
    # 93% of its references come from the one group. This is a share, and a
    # share of a count that is itself 42-fold -- the column says how much of
    # the cluster's co-occurrence one set of files supplies, and does not say
    # the cluster is one routine.
    sweep_cluster = next((r for r in cluster_rows
                          if r["cluster_name"] == "counter-sweep"), None)
    check(f"and the cluster named `counter-sweep` is the one whose references "
          f"are dominated by the 42-file group"
          + (f" -- {sweep_cluster['cluster_id']} is "
             f"{int(sweep_cluster['co_reading_refs'])}/{sweep_cluster['refs']} = "
             f"{int(sweep_cluster['co_reading_refs']) / int(sweep_cluster['refs']):.0%}"
             if sweep_cluster else " -- it has no name in this generation"),
          sweep_cluster is not None and
          sweep_cluster["co_reading_dominant"] == "yes" and
          int(sweep_cluster["co_reading_refs"]) == 4642)
    # Issue #280: the same question, asked of the whole tree instead of five
    # addresses. `direction_invariant()` is a second code path over the same
    # text, not a re-implementation of store_target() -- assign_after() is a
    # primitive that never consults the rule under test -- so this fails on a
    # classifier that sums correctly while getting the direction wrong, which
    # is exactly what the oracle above cannot be widened into on its own.
    shaped, offenders, surplus, eq_after, eq_in_write = direction_invariant(
        by_file, symbols, func_names)
    check(f"the corpus-wide direction invariant: every one of the "
          f"{DIRECTION_INVARIANT['write_like']} occurrences across "
          f"{DIRECTION_INVARIANT['write_like_addrs']} distinct addresses that "
          f"the census buckets `write` or `read+write` has an assignment -- not "
          f"`==` -- after the address, measured by a second pass that does not "
          f"re-implement the classifier"
          + (f"; offenders, as `file!line address`: "
             f"{', '.join(offenders)}" if offenders else ""),
          not offenders)
    # The per-address form of the same necessary condition, so a failure here
    # says which address stopped balancing rather than only which occurrence.
    over = [hexaddr(a) for a in everywhere
            if sum(groups[g][a]["buckets"]["write"]
                   + groups[g][a]["buckets"]["read+write"]
                   for g in GROUPS if a in groups[g]) > shaped.get(a, 0)]
    check(f"and no single address is counted as more stores than the second "
          f"pass accepts, so the agreement is per address and not only in "
          f"aggregate (over-counted: {', '.join(over) or 'none'})",
          not over)
    # The exemption rule, stated as a measurement rather than as a tolerance.
    # `assign_after()` drops the `*` test that `store_target()` applies, so it
    # accepts strictly more; every extra is a dereference store, and the two
    # below are the whole of the difference. A new shape arriving here is a
    # named site, not a quietly widened exemption count.
    check(f"the only occurrences the second pass accepts and the census does "
          f"not are the {DIRECTION_INVARIANT['deref_surplus']} `*`-dereference "
          f"stores, the one exclusion a necessary condition does not need "
          f"(anything else: {', '.join(surplus) or 'none'})",
          not surplus and sum(shaped.values()) == DIRECTION_INVARIANT["assign_shaped"])
    # The mirror direction on the same pass, and the tree-wide `==` figure the
    # docstring and xdata-register-map.md §4.3 both quote. Asserted together so
    # the count cannot drift away from the prose that cites it.
    check(f"and none of the {DIRECTION_INVARIANT['eq_after']} `==` occurrences in "
          f"the tree is bucketed as a store (in a write bucket: "
          f"{eq_in_write or 'none'})",
          eq_in_write == 0 and eq_after == DIRECTION_INVARIANT["eq_after"])
    # Internal by construction, and labelled so: the report's §4.1 table read
    # off these, so a drift in any of them means the table and the CSVs have
    # parted. It cannot vouch for the direction -- only HAND_CHECKED can.
    check(f"the §4.1 bucket totals, "
          f"{' '.join(f'{k} {v}' for k, v in BUCKET_TOTALS.items())} "
          f"(got {' '.join(f'{k} {fired.get(k, 0)}' for k in BUCKET_TOTALS)})",
          all(fired.get(k, 0) == v for k, v in BUCKET_TOTALS.items()))

    # Issue #554's oracle, run in-process rather than through --export-ownership:
    # that flag is refused with --self-test, for the same reason --no-eq-guard
    # is (the committed CSVs are the other census), so the after figures have
    # to be reached here or they are a claim rather than a check. Nothing below
    # writes, and the default path above is untouched by any of it.
    own_map = load_ownership()
    census_own, _calls_own, _raw_own = scan(by_file, names, func_names, symbols,
                                            export_ownership=True,
                                            ownership=own_map)
    groups_own = {g: merge_group(census_own, PROGRAM_COL[g]) for g in GROUPS}
    fired_own = collections.Counter()
    for g in GROUPS:
        for e in groups_own[g].values():
            fired_own.update(e["buckets"])
    own_distinct = len(set(groups_own["main-ec"]) | set(groups_own["pd"]))
    own_refs = (sum(e["refs"] for e in groups_own["main-ec"].values())
                + sum(e["refs"] for e in groups_own["pd"].values()))
    check(f"oracle: the export-ownership census, both spellings -- "
          f"{OWNERSHIP['distinct']} distinct / {OWNERSHIP['refs']} references "
          f"(got {own_distinct}/{own_refs})",
          own_distinct == OWNERSHIP["distinct"] and own_refs == OWNERSHIP["refs"])
    check("and its bucket totals, "
          f"{' '.join(f'{k} {v}' for k, v in OWNERSHIP['buckets'].items())} "
          f"(got {' '.join(f'{k} {fired_own.get(k, 0)}' for k in OWNERSHIP['buckets'])})",
          all(fired_own.get(k, 0) == v for k, v in OWNERSHIP["buckets"].items()))
    lost = {hexaddr(a) for a in set(groups["main-ec"]) | set(groups["pd"])} - \
        {hexaddr(a) for a in set(groups_own["main-ec"]) | set(groups_own["pd"])}
    check(f"and the pass loses no address, which is the one thing it must never "
          f"do (lost: {', '.join(sorted(lost)) or 'none'}; if this ever names an "
          f"address, an owner was not a superset of its non-owners)",
          lost == set(OWNERSHIP["lost"]))
    moved = sum(1 for a in set(groups["main-ec"]) & set(groups_own["main-ec"])
                if groups["main-ec"][a]["refs"] != groups_own["main-ec"][a]["refs"])
    check(f"and it moves the reference count of {OWNERSHIP['moved']} addresses, "
          f"the width of the 6a before/after (got {moved})",
          moved == OWNERSHIP["moved"])
    # The cost of the flip, which is the reason the default stays off. These are
    # identities rather than counts -- `cluster_key` and the hand names are what
    # a citation in the tree survives a regeneration on -- so they are the half
    # of the argument the census figures above cannot make, and they are
    # asserted here so the "pinned" above them means a check and not a promise.
    _own_registers, own_clusters, _ = build(funcs, names, symbols, census_own,
                                            _calls_own, args.threshold)
    own_keys = {r["cluster_key"] for r in own_clusters}
    committed_keys = {r["cluster_key"] for r in old_rows if r["cluster_key"]}
    hand_keys = load_cluster_names()
    kept = len(committed_keys & own_keys)
    hand_kept = sum(1 for k in hand_keys if k in own_keys)
    check(f"and the flip would renumber: {len(own_clusters)} clusters against "
          f"the committed {len(committed_keys)}, {kept} of the committed "
          f"cluster_keys surviving, {hand_kept} of the {len(hand_keys)} hand "
          f"names in {os.path.relpath(NAMES_CSV, EC_DIR)} (got "
          f"{len(own_clusters)}/{kept}/{hand_kept})",
          len(own_clusters) == OWNERSHIP["clusters"]
          and kept == OWNERSHIP["cluster_keys_kept"]
          and hand_kept == OWNERSHIP["hand_names_kept"])
    # The 42 copies, counted from the map rather than from a hand list, because
    # the width is the claim: one routine exported 42 ways is what the whole
    # switch exists to stop being read 42 times.
    copies = [f for f, r in own_map.items()
              if r["owner_out_file"] == "bank1/8001.c" and f != "bank1/8001.c"]
    check(f"the bank1:0x8001 run is {len(copies) + 1} exports of one body, so "
          f"the default census reads 0x0843 168 times against "
          f"{groups_own['main-ec'][0x0843]['refs']} with the pass on",
          len(copies) + 1 == export_ownership.OWNERSHIP_ORACLE["largest_class"]
          and groups["main-ec"][0x0843]["refs"] == 168
          and groups_own["main-ec"][0x0843]["refs"] == 4
          and len(groups_own["main-ec"][0x0843]["funcs"]) == 1)
    # The default must be untouched. If a future change made the pass the
    # default, every figure above and every committed CSV would have to move at
    # once, and this is the assertion that says so first.
    check("and the default census is unchanged, so the committed CSVs are still "
          "what a plain run produces",
          not args.export_ownership
          and len(groups["main-ec"]) == ORACLE["main_distinct"]
          and sum(e["refs"] for e in groups["main-ec"].values())
          == ORACLE["main_refs"])
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

    # Issue #274. The rank above is a rank, so the identity a citation survives
    # a regeneration on is the content hash. Three things have to hold, and the
    # first is the one a truncated sha256 does not prove for itself: distinct
    # memberships must get distinct keys, and the place that has to hold is the
    # census **as committed** -- the file every `cluster_key` and `cluster_name`
    # citation in the tree resolves against. So the committed rows are checked
    # from the file, not only the fresh generation above: a collision that is
    # only in what this run would write is not one a reader can hit, and a
    # check that covered only the fresh rows while the prose said "as committed"
    # is the claim this file's own rule about calibration exists to catch.
    keys = [r["cluster_key"] for r in cluster_rows]
    dupes = sorted(k for k, n in collections.Counter(keys).items() if n > 1)
    check(f"every one of the {len(keys)} clusters has a distinct cluster_key, so "
          f"a key names a membership and not a rank (duplicates: "
          f"{', '.join(dupes) or 'none'})",
          not dupes)
    old_keys = [(r.get("cluster_key") or "").strip() for r in old_rows]
    old_dupes = sorted(k for k, n in collections.Counter(
        k for k in old_keys if k).items() if n > 1)
    check(f"every one of the {sum(1 for k in old_keys if k)} keys the committed "
          f"{os.path.relpath(OUT_CLUSTERS, EC_DIR)} carries is distinct, read "
          f"back from that file rather than from a fresh generation, so a "
          f"cluster_key citation resolves to one membership (duplicates: "
          f"{', '.join(old_dupes) or 'none'})",
          not old_dupes)
    key_of_id = {r["cluster_id"]: r["cluster_key"] for r in cluster_rows}
    addrs_of_key = {r["cluster_key"]: r["addrs"] for r in cluster_rows}
    check("the registers CSV's cluster_key agrees with the clusters CSV's, "
          "address for address, and every address is in a cluster that has one",
          all(r["cluster_key"] == key_of_id.get(r["cluster_id"], "")
              for r in register_rows))
    # The carry. A name is only ever reported with how it got here, a cluster
    # nothing matched is reported rather than dropped, and the score in a
    # report is the score re-measured from the CSVs rather than a number this
    # function remembered.
    by_old_key = {r.get("cluster_key", ""): r for r in old_rows}
    misreported = []
    for r in carry:
        if r["how"] != "overlap":
            continue
        old = by_old_key.get(r["from_key"])
        got = (jaccard(set(addrs_of_key[r["cluster_key"]].split()),
                       set(old["addrs"].split()))
               if old else None)
        if got is None or abs(got - r["jaccard"]) > 1e-9:
            misreported.append((r["cluster_id"], r["jaccard"], got))
    check(f"every name carried by overlap reports the Jaccard re-measured from "
          f"the CSVs ({sum(1 for r in carry if r['how'] == 'overlap')} carries; "
          + (f"disagreed on {misreported}" if misreported
             else "no disagreement") + ")",
          not misreported)
    old_names = {r["cluster_name"].strip() for r in old_rows
                 if (r.get("cluster_name") or "").strip()}
    # A tie's detail spells each claimant as `name (old id)`, so the name has
    # to be recovered from it -- a tie that quietly dropped a name would leave
    # the committed census carrying one this generation does not.
    reported = ({r["name"] for r in carry if r["name"]} |
                {n.rsplit(" (", 1)[0] for r in carry
                 for n in r["detail"].split(" == ") if n})
    check(f"every name the committed census carries is either carried again or "
          f"reported as a tie, and none is silently dropped ({len(old_names)} "
          f"names; unaccounted for: "
          f"{', '.join(sorted(old_names - reported)) or 'none'})",
          not (old_names - reported))
    check("every cluster has a carry record, so a name that is not carried is a "
          "reported outcome and not an absence",
          len(carry) == len(cluster_rows) and
          all(r["how"] in ("seeded", "exact", "overlap", "tie", "none")
              for r in carry))
    # Scoped to the **committed** census, which is what the names file is
    # anchored to and what every `cluster_key`/`cluster_name` citation in the
    # tree resolves against -- not to the fresh generation above. The two
    # differ on this tree, and the gap is the pre-existing census staleness the
    # next check reports in its own right; holding the names file to a census
    # that is not committed would make this check red for a reason the names
    # file does not own, and red twice for one cause. On the committed census
    # all ten resolve, and this still catches the thing it is for: a name
    # anchored to a membership the census has actually lost.
    stale = sorted(k for k in load_cluster_names()
                   if k not in {r.get("cluster_key", "") for r in old_rows})
    check(f"every key in {os.path.relpath(NAMES_CSV, EC_DIR)} names a cluster of "
          f"the committed census, which is what it is anchored to, so the names "
          f"file is not attached to a membership that has gone (stale: "
          f"{', '.join(stale) or 'none'})",
          not stale)

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


def co_reading_sweep(args) -> int:
    """Largest group / files in groups against the floor, for the report's
    choice of COREADING_MIN_CORE. Mirrors `--threshold-sweep`: same census, a
    different relation, nothing written.

    The curve is what makes the constant **recorded** rather than tuned, and it
    is why the report quotes the output rather than the constant. The two low
    floors are the trivially-equal-address-set artefact -- two files that each
    name one address have a Jaccard of 1.00 -- and the middle of the curve is
    where the counter sweep's 42 files stop breaking up.

    `--co-reading-group-table` prints the other half: every group over two
    files, with the common core and the listing-size pattern, which is the
    evidence the boundary hypothesis rests on and the reason a group is not read
    as one routine."""
    funcs, by_file = load_index()
    names = load_names(funcs)
    symbols = load_symbols()
    census, _calls, _group_of, _raw = census_and_groups(args, funcs, by_file,
                                                       names, symbols)
    print(f"floor,largest group,groups,files in groups,pd groups,pd files")
    for floor in list(args.floors) + ([COREADING_MIN_CORE]
                                      if COREADING_MIN_CORE not in args.floors
                                      else []):
        _go, groups = co_reading_groups(census, funcs, floor)
        sizes = sorted((len(g["files"]) for g in groups), reverse=True)
        pd = [g for g in groups if g["program"] == PD_PROGRAM]
        print(f"{floor},{sizes[0] if sizes else 0},{len(sizes)},"
              f"{sum(sizes)},{len(pd)},{sum(len(g['files']) for g in pd)}")
    return 0


def co_reading_group_table(args) -> int:
    """Every multi-file group, with the evidence a reader needs to judge it.

    `core` is the addresses *every* member names and `1-byte` the count of
    listings `index.csv` records as a single instruction, because that size
    pattern is the observable and "these files are slices of one routine" is the
    hypothesis. A group whose core is one address is a connected component
    rather than a set of lookalikes, and printing the core is what lets a reader
    tell the two apart without re-deriving anything."""
    funcs, by_file = load_index()
    names = load_names(funcs)
    symbols = load_symbols()
    census, _calls, _group_of, _raw = census_and_groups(args, funcs, by_file,
                                                       names, symbols)
    _go, groups = co_reading_groups(census, funcs, COREADING_MIN_CORE)
    groups.sort(key=lambda g: (-len(g["files"]), g["program"], g["files"][0]))
    print("program,files,common core,core addrs,listing bytes,1-byte listings,"
          "first,last")
    for g in groups:
        print(f"{g['program']},{len(g['files'])},{len(g['core'])},"
              f"{' '.join(hexaddr(a) for a in sorted(g['core']))},"
              f"{sum(g['sizes'])},{sum(1 for s in g['sizes'] if s == 1)},"
              f"{g['files'][0]},{g['files'][-1]}")
    print(f"{len(groups)} groups over {sum(len(g['files']) for g in groups)} "
          f"files at floor {COREADING_MIN_CORE}", file=sys.stderr)
    return 0


def collapse_co_readings(args) -> int:
    """What the boundary hypothesis would imply, printed and not written.

    Each multi-file group is mapped to one pseudo-function and the census is
    re-clustered with that as the only change, so the question "if the 42
    exports are one routine, what does the worklist look like?" has an answer
    instead of an assertion. **This writes neither CSV and is not the committed
    clustering**, for the reason the report repeats: the groups' boundaries are
    `seed_basis=call-target` -- a hypothesis
    `annotations/xdata-06c2-06db-timers.md` §2 records -- and correcting them
    needs `--mode rebuild-project` and its own branch. Adopting the collapsed
    clustering on the strength of this relation would decide the boundary
    question with a count of files.

    So the number printed here is a measurement of the hypothesis, and the
    per-group core in `--co-reading-group-table` is the reason it is not
    adopted: the six-file `bank0` group has a one-address core, and collapsing
    it would merge six real `0x1804` readers that only a neighbour connects,
    three of which are also `0x0440` readers."""
    funcs, by_file = load_index()
    names = load_names(funcs)
    symbols = load_symbols()
    census, _calls, group_of, _raw = census_and_groups(args, funcs, by_file,
                                                       names, symbols)
    groups = {g: merge_group(census, PROGRAM_COL[g]) for g in GROUPS}
    # The collapse, and only this: every group member's function key becomes
    # one synthetic key. `refs` is deliberately untouched, so a cluster's size
    # moves and its reference total does not -- which is the honest shape of the
    # question, since de-duplicating the counts is the part this change refuses.
    #
    # One pseudo-function per *group*, numbered over the sorted groups so the
    # numbering does not depend on dict order. Mapping each key to its own
    # pseudo-function instead would leave a 42-file group as 42 functions and
    # quietly measure a different thing.
    pseudo_of_group = {group: ("co-reading", f"g{n:03d}")
                       for n, group in
                       enumerate(sorted(set(group_of.values())), 1)}
    pseudo_of = {key: pseudo_of_group[group] for key, group in group_of.items()}
    collapsed = {}
    for g in GROUPS:
        collapsed[g] = {}
        for addr, entry in groups[g].items():
            new = blank_entry()
            for f, n in entry["funcs"].items():
                new["funcs"][pseudo_of.get(f, f)] += n
            new["refs"] = entry["refs"]
            collapsed[g][addr] = new
    comps = {g: (components(groups[g], args.threshold, not args.no_writer_axis),
                 components(collapsed[g], args.threshold, not args.no_writer_axis))
             for g in GROUPS}
    print(f"groups collapsed: {len(pseudo_of_group)} pseudo-functions over "
          f"{len(pseudo_of)} files")
    print(f"{'group':8} {'clusters':>9} {'largest':>8} {'singletons':>11}")
    for g in GROUPS:
        was, now = comps[g]
        sizes = sorted((len(v) for v in now.values()), reverse=True)
        print(f"{g:8} {len(was):9d}->{len(now):<6d} "
              f"{max((len(v) for v in was.values()), default=0):8d}->"
              f"{sizes[0] if sizes else 0:<6d} "
              f"{sum(1 for v in was.values() if len(v) == 1):11d}->"
              f"{sum(1 for c in sizes if c == 1):<6d}")
    ordered = sorted((sorted(v) for v in comps["main-ec"][1].values()),
                     key=lambda v: (-len(v),
                                    -sum(collapsed["main-ec"][a]["refs"] for a in v),
                                    v[0]))
    print("worklist head under the hypothesis (main-ec):")
    for n, members in enumerate(ordered[:3], 1):
        print(f"  {n:3d}. {len(members):3d} addresses, "
              f"{sum(collapsed['main-ec'][a]["refs"] for a in members):5d} refs, "
              f"{hexaddr(members[0])}-{hexaddr(members[-1])}")
    # Where the biggest clusters' addresses went, which is the question the
    # worklist head alone cannot answer: a cluster can keep its size, gain
    # neighbours, or come apart, and "the collapse" means something different
    # in each case. Reported for the three largest clusters as they stand now,
    # as `surviving together / originally together, into a cluster of N`.
    owner = {a: i for i, v in enumerate(ordered) for a in v}
    print("the three largest clusters as they stand, under the hypothesis:")
    was = sorted(comps["main-ec"][0].values(), key=len, reverse=True)[:3]
    for members in was:
        landed = collections.Counter(owner[a] for a in members if a in owner)
        if not landed:
            print(f"  {len(members):3d} addresses over {hexaddr(members[0])}-"
                  f"{hexaddr(members[-1])}: none of them is in the main-EC "
                  f"census's clustering at all")
            continue
        pick, n = landed.most_common(1)[0]
        # The *other* clusters, which is not the same as the destinations that
        # took more than one address: the picked cluster is one of them whenever
        # it took more than one, and counting it makes every line read one too
        # high.
        elsewhere = sum(1 for i in landed if i != pick)
        print(f"  {len(members):3d} addresses over {hexaddr(members[0])}-"
              f"{hexaddr(members[-1])}: {n} stay together in a "
              f"{len(ordered[pick])}-address cluster, {len(members) - n} do not"
              + (f", across {elsewhere} other "
                 f"{'cluster' if elsewhere == 1 else 'clusters'}"
                 if elsewhere else ""))
    print("neither CSV was written: the committed clustering is unchanged and "
          "this mode exists so the question has an answer, not so the answer "
          "becomes the census", file=sys.stderr)
    return 0


def map_census(args) -> int:
    """`--map OLD.csv`: where every row of an older clusters CSV went in this one.

    This is the report issue #253 needed and did not have, and the thing that
    makes the `main-ec-NNN` -> stable-id prose sweep mechanical rather than a
    hunt. The usual invocation runs this tool over a *changed* tree -- a guard
    removed, a threshold moved, a classifier fixed -- and names the committed
    census as OLD, so every stale citation gets an answer in one pass:

        python3 ec/tools/xdata_register_map.py \\
            --map ec/annotations/xdata-clusters.csv > /tmp/map.csv

    The rows go to stdout as CSV and the summary to stderr, so the report can be
    redirected into the sweep's working file without the prose ending up in it.

    `match` is how the old row found its way to a new cluster -- `key` when the
    content hash is identical, `overlap` when the membership scored at least
    `CARRY_MIN_JACCARD` against something else, `none` when nothing cleared it.
    `carried` is the new cluster's own name outcome, which is a different
    question: a cluster can be found by overlap and still hold no name. A
    `none` in either column means this tool's rule did not fire; neither is a
    claim that anything went away.

    `--out-clusters` and `--out-registers` are **not** honoured here: this mode
    reports, it does not write, and their defaults are the committed CSVs, so
    honouring them would have a `--map` run silently overwrite the census it is
    mapping. Produce a regeneration's CSVs with a separate writing run (the
    plain invocation with no mode flag) and point
    `check_cluster_citations.py --clusters/--registers` at those; both halves
    read the same tree, so the sentences check the same way."""
    built = generate(args)
    if built is None:
        return 1
    _registers, clusters, _groups, report = built
    by_key = {r["cluster_key"]: r for r in clusters}
    carried = {r["cluster_key"]: r for r in report}
    try:
        with open(args.map, newline="") as f:
            old_rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"{args.map} does not exist", file=sys.stderr)
        return 1

    rows = []
    claimed = collections.Counter()
    for old in old_rows:
        old_key = (old.get("cluster_key") or "").strip()
        old_addrs = set(old.get("addrs", "").split())
        hit = by_key.get(old_key) if old_key else None
        if hit is not None:
            match, score = "key", 1.0
        else:
            best = max(((jaccard(old_addrs, set(r["addrs"].split())), r)
                        for r in clusters), default=(0.0, None), key=lambda t: t[0])
            score, hit = best
            match = "overlap" if hit is not None and score >= CARRY_MIN_JACCARD \
                else "none"
        if hit is None:
            unmatched = dict.fromkeys(MAP_COLUMNS, "")
            unmatched.update({
                "old_cluster": old.get("cluster_id", ""),
                "new_cluster": "-", "key": "no match", "old_key": old_key,
                "cluster_name": "-", "carried": "-", "match": "none",
                "jaccard": f"{score:.2f}"})
            rows.append(unmatched)
            continue
        new_key = hit["cluster_key"]
        how = carried[new_key]
        # Only a row that actually matched counts as a claim. A sub-threshold
        # best guess is printed as its own row with `match=none`, and counting
        # it would report a 0.02-Jaccard near miss as a collision.
        if match != "none":
            claimed[hit["cluster_id"]] += 1
        rows.append({
            "old_cluster": old.get("cluster_id", ""),
            "new_cluster": hit["cluster_id"],
            "key": ("unchanged" if old_key == new_key else
                    "changed" if old_key else "absent"),
            "old_key": old_key or "-",
            "new_key": new_key,
            "cluster_name": how["name"] or "-",
            "carried": how["how"] if how["how"] != "overlap"
                       else f"overlap {how['jaccard']:.2f}",
            "match": match,
            "jaccard": f"{score:.2f}",
            "added": " ".join(sorted(set(hit["addrs"].split()) - old_addrs)),
            "removed": " ".join(sorted(old_addrs - set(hit["addrs"].split()))),
        })
    print(render(rows, MAP_COLUMNS), end="")

    moved = sum(1 for r in rows if r["key"] == "changed")
    delta = sum(1 for r in rows if r["added"] or r["removed"])
    nomatch = sum(1 for r in rows if r["match"] == "none")
    shared = sorted(cid for cid, n in claimed.items() if n > 1)
    print(f"{len(rows)} rows: {moved} whose cluster_key changed, {delta} whose "
          f"membership changed, {nomatch} with no match at "
          f"{CARRY_MIN_JACCARD:.2f}, {sum(1 for r in rows if r['cluster_name'] != '-')} "
          f"carrying a name", file=sys.stderr)
    if shared:
        print("  a new cluster claimed by more than one old row -- a fact about "
              "the clustering, so neither is picked: "
              + ", ".join(shared), file=sys.stderr)
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
    modes.add_argument("--co-reading-sweep", action="store_true",
                       help="print the largest co-reading group and the files in "
                            "groups against each floor in --floors, which is "
                            "what makes COREADING_MIN_CORE a recorded choice")
    modes.add_argument("--co-reading-group-table", action="store_true",
                       help="print every multi-file co-reading group with its "
                            "common core and listing-size pattern; the evidence "
                            "the boundary hypothesis rests on")
    modes.add_argument("--collapse-co-readings", action="store_true",
                       help="re-cluster with each co-reading group as one "
                            "pseudo-function and print the result; writes "
                            "nothing, because the group boundaries are a "
                            "hypothesis rather than a description")
    modes.add_argument("--map", metavar="OLD_CSV",
                       help="print one row per cluster of OLD_CSV saying where it "
                            "went in this generation: id, cluster_key, carried "
                            "name, Jaccard and the membership delta. The report "
                            "a prose sweep of the cluster ids is driven from")
    modes.add_argument("--reconcile", metavar="FIRMWARE",
                       help="cross-check every registers.yaml address against "
                            "register_ref_table.py on the given image; needs the "
                            "image and registers.yaml, unlike every other mode")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"Jaccard similarity for the clustering (default: "
                         f"{DEFAULT_THRESHOLD})")
    ap.add_argument("--thresholds", type=float, nargs="+", default=list(SWEEP_THRESHOLDS),
                    metavar="T", help="thresholds for --threshold-sweep")
    ap.add_argument("--floors", type=int, nargs="+",
                    default=list(SWEEP_COREADING_FLOORS), metavar="N",
                    help="common-core floors for --co-reading-sweep")
    ap.add_argument("--no-writer-axis", action="store_true",
                    help="for --threshold-sweep: cluster on the touching-function "
                         "relation alone, which is how the second relation's "
                         "contribution is measured")
    ap.add_argument("--no-eq-guard", action="store_true",
                    help="count `==` as a store, the way the pre-#178 classifier "
                         "did, so the guard's effect stays measurable; refused "
                         "with --check and --self-test")
    ap.add_argument("--export-ownership", action="store_true",
                    help="read each routine once, from the export that owns it, "
                         "so the 42 overlapping exports of bank1:0x8001 are not "
                         "counted 42 times. The default is OFF: the pass is a "
                         "text heuristic rather than a function boundary, and "
                         "the measured cost of flipping it is a tree-wide "
                         "renumbering (cluster_key on 35 of the 430 clusters, 5 "
                         "of the 10 hand names; annotations/xdata-export-"
                         "ownership.md 5). Refused with --check and --self-test, "
                         "and without scratch outputs")
    ap.add_argument("--out-registers", default=OUT_REGISTERS,
                    help=f"per-address CSV (default: {OUT_REGISTERS})")
    ap.add_argument("--out-clusters", default=OUT_CLUSTERS,
                    help=f"per-cluster CSV (default: {OUT_CLUSTERS})")
    ap.add_argument("--registers", default=os.path.join(EC_DIR, "annotations",
                                                         "registers.yaml"),
                    help="registers.yaml for --reconcile")
    args = ap.parse_args()

    # Refused here, before any mode runs, rather than inside the two of them:
    # both are gates, and a flag that re-buckets occurrences while writing
    # nothing must not be reachable from a mode whose claim is that the
    # committed CSVs already match. `--check` would go red and `--self-test`
    # would go red for the same reason, which is the point -- they should not
    # be answerable to a switch.
    if args.no_eq_guard and (args.check or args.self_test):
        ap.error("--no-eq-guard changes what the census says, so it cannot be "
                 "combined with --check or --self-test. To see the pre-#178 "
                 "buckets, write a census to a scratch path and diff it "
                 "against the committed one.")
    # The other way this flag could do damage is quieter: run bare it writes the
    # pre-#178 census over the committed CSVs, after which --check is green
    # because the files now agree with each other and the source of truth is
    # wrong. So a --no-eq-guard run must be given somewhere to write.
    if args.no_eq_guard and (args.out_registers == OUT_REGISTERS
                             or args.out_clusters == OUT_CLUSTERS):
        ap.error("--no-eq-guard would overwrite the committed census, so it "
                 "must be given scratch outputs: pass --out-registers and "
                 "--out-clusters (see annotations/xdata-06c2-06db-timers.md 6a).")

    # The same two refusals, for the same two reasons. The flag here is the
    # other way round from --no-eq-guard -- it turns the pass *on* rather than
    # reproducing a removed guard -- because the default has to stay where it
    # is: the committed CSVs are the 42-fold census, and flipping the default
    # would move the reference count of 228 of the 1,171 register rows, move
    # `cluster_key` on 35 of the 430 clusters and break 5 of the 10 hand
    # cluster names. Those are OWNERSHIP's, measured on this tree and quoted
    # here so a refusal is argued from the same numbers the rest of the file
    # pins. So the name says what it does, where --no-eq-guard's says what
    # removing its guard undoes. The guard itself is the same: a census this
    # tool does not otherwise produce has to be written somewhere scratch.
    if args.export_ownership and (args.check or args.self_test):
        ap.error("--export-ownership changes what the census says, so it "
                 "cannot be combined with --check or --self-test. To see the "
                 "de-duplicated census, write one to a scratch path and diff it "
                 "against the committed one.")
    if args.export_ownership and (args.out_registers == OUT_REGISTERS
                                  or args.out_clusters == OUT_CLUSTERS):
        ap.error("--export-ownership would overwrite the committed census, so "
                 "it must be given scratch outputs: pass --out-registers and "
                 "--out-clusters (see annotations/xdata-export-ownership.md).")

    if args.self_test:
        return self_test(args)
    if args.threshold_sweep:
        return threshold_sweep(args)
    if args.co_reading_sweep:
        return co_reading_sweep(args)
    if args.co_reading_group_table:
        return co_reading_group_table(args)
    if args.collapse_co_readings:
        return collapse_co_readings(args)
    if args.map:
        return map_census(args)
    if args.reconcile:
        args.firmware = args.reconcile
        return reconcile(args)
    if args.check:
        return check(args)
    return write(args)


if __name__ == "__main__":
    sys.exit(main())
