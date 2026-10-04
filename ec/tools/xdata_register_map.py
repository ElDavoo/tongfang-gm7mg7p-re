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
    read+write       an `=` target naming itself on the right, or `&=` and kin
    passed-to-call   an argument of a call to a routine `index.csv` records
    address-taken    `&DAT_EXTMEM_xxxx`, but not the `&&` of a comparison

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

**The direction split is checked corpus-wide.** Every occurrence the census
buckets `write` or `read+write` is asserted to have an assignment -- not `==`
-- after the address, measured over the whole tree. It holds with no
exemptions: the only occurrences the second pass accepts and the census does
not are `*`-dereference stores, which `store_target()` excludes for cause and
a necessary condition does not need to exclude.

**It is a second code path over the same text, not a second pair of eyes.**
Same files, same regex, same `strip_comments()`, and the buckets it is measured
against are the ones this tool just produced. What it is *not* is a
re-implementation, and that is what makes it worth asserting: the `==`
rejection lives in `store_target()`, and the second pass's predicate is only
"an `=` that is not `==` follows", so it never consults the thing under test.
Re-introduce the pre-fix classifier and the two disagree on every `==`
occurrence. What it cannot reach is everything a shape test over C text cannot
reach -- a store the decompiler mis-spelled, a write through a pointer, and a
per-address *count* that is wrong while every occurrence is assignment-shaped.
`CLASSIFIER_SHAPE`'s literal snippets hold the classifier's shapes; nothing
here holds a per-address count, because every such count moves when a routine
touching the address is seeded.

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

**`spelled_as` is a union across programs, and `spellings_by_program` is the
column that says which half is which.** A `program=both` row's `spelled_as` is
every spelling *either* program gives that address number, so `0x04A3` reads
`DAT_EXTMEM+pair-literal` there while the main EC spells it `pair-literal` and
the PD image spells it `DAT_EXTMEM`. That is not cosmetic: it is the whole of
the difference between the per-program mixed set and the CSV's own, and
on a reader who takes the cell at face value it is a wrong statement about one
program rather than a loose one about two. So the registers CSV carries a second
spelling column, `spellings_by_program` -- `main-ec=<spellings>` on a main-EC
row, `pd=<spellings>` on a pd one, `main-ec=<spellings>;pd=<spellings>` on a
`both` row -- and that is what a per-program question is read from.

**The counts were the same mistake one column later, and the twelve
per-program cells at the end of the row are the column that says which half is
which.** `refs` and the five direction buckets on a `both` row are the *sum*
over the two programs, which reads as a statement about one of them: `0x04A3`
carries 4 `read` / 3 `write` / 0 / 0 / 1, and a reader looking for a writer
sees three bank1 writes and a single pd `address-taken` with nothing in the row
to say which program each came from. So the row now also carries
`refs_<program>` and the five buckets once per program -- twelve new columns at
22-33, with `spellings_by_program` still at 21, so thirteen per-program columns
on the row -- written on **every** row and not only on the 49 `both` ones, so
`refs == refs_main_ec + refs_pd` holds on all 1,326 and `csv.DictReader`
consumers never meet an empty cell. It is a split, not a second pass: `refs`,
the five buckets, `readers`, `writers`, `co_reading`, `sources_beyond` and
every census total are exactly what they were, and a
shared address *number* is still not a shared byte -- the two are separate
address spaces and a per-program `write` is a static shape, not evidence the
EC acts on the byte. The unsuffixed cells stay the row's own figures, which
is the only reason a reader who reads them still gets the census.
`../../docs/findings/xdata-per-program-counts.md` has the worked rows, the
arithmetic, and what a zero in the other program's column does and does not
say.

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
export, taking the census to 9,404 references with 0x0843 at 4 and one function
behind it.

**The default stays off, and that is the calibrated answer rather than a
cowardly one.** The pass is a containment heuristic over decompiled text, not a
function boundary: a non-owner is skipped rather than reconciled against its
owner, so an owner that is not a superset takes the references with it. On
this tree that costs a tree-wide renumbering of `cluster_key` and of the hand
names in `xdata-cluster-names.csv` (measured in
`annotations/xdata-export-ownership.md` §4 and §5), to land on top of a
detector known to be approximate.
The root cause is the export boundary, and fixing it needs
`--mode rebuild-project`, which cannot share a branch
(annotations/xdata-06c2-06db-timers.md 8 item 7). So the pass ships measured,
measured by `--export-ownership`, and the flip is its own
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
clustering, so it is reported and no winner is picked. `duplicate` is its
mirror -- one old name reached by two new clusters at the same score -- and is
refused the same way, so no name is written to two rows. And `none` is **not
carried by this method** -- never *gone*, never *lost*, never *disappeared*: a
function that stopped decompiling, a threshold that moved, a guard that was
removed and a cluster that stopped existing are four different things, and this
column can only report that its own rule did not fire.

**Those six are counted per new *cluster*, so they do not account for every
hand name.** A name the names file lists whose key no cluster of this run has,
and which no new cluster reaches at `CARRY_MIN_JACCARD`, is in no cluster's
record and in no cell of that tally; on a run that re-clusters the difference
is several names. So the carry block has a second half as well,
`xdata_name_coverage.coverage()`'s list, which is one record per **row of the
names file** and therefore produces an outcome for every hand name on every run
that builds a census. `print_carry()` prints both, and the tally's two optional
clauses are the parts of it that come from the second half.

**`--no-eq-guard` re-runs the census with the `==` rejection turned off**, and
is refused with `--check` and `--self-test` because both are gates: a flag that
can change a bucket without changing anything on disk must not be reachable
inside a mode whose whole claim is that nothing changed. It is also refused
unless it is given `--out-registers` and `--out-clusters`, for the same reason
one step removed: run bare it would write the pre-#178 census over the
committed CSVs, and `--check` would then go red, because the refusal above
regenerates guard-on and a guard-off file cannot match. It exists because
`annotations/xdata-06c2-06db-timers.md` §6a measures what the guard bought, and
that measurement has to stay re-derivable from the committed tree forever. It
could not be, from a commit pointer: `git log --oneline -S 'startswith("==")' --
ec/tools/xdata_register_map.py` reaches **two commits on `origin/main`** -- #206,
which is itself the commit that added the guard, and #302, whose tree-wide
invariant added two more occurrences of the same string. Neither is the
pre-#178 classifier, which appears only at #206's parent, a revision the search
does not name, so the recipe was "copy the tool and patch it", which is how §6a
came to compare the tool against itself. The numbers that recipe produced are
real and the recipe is the problem; this flag is the recipe, kept. Both
refusals are pinned by `test_xdata_register_map.py`, which holds that no mode
runs before either of them fires.

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

# export_ownership and cluster_name_shape are sibling tools here, imported by bare
# module name the way check_site_census.py imports this one; sys.path is set for
# them above. This block is four lines: `ASSIGN` is below it, and a fifth would
# move an anchor `check_eq_guard_citations.py` resolves and five files cite.
if TOOL_DIR not in sys.path:
    sys.path.insert(0, TOOL_DIR)
import export_ownership  # noqa: E402
import cluster_name_shape  # noqa: E402
import xdata_name_coverage  # noqa: E402

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
# The two spellings, spelled as they appear in the decompiled C. `raw` counts
# occurrences of these two and nothing else, so the `pair-literal` spelling
# below is deliberately *not* one of them: it is not a token the decompiler
# wrote, it is a fact this tool derived about an argument, and counting it here
# would move `extmem_raw` for a reason no reader of that pin could see.
SPELLINGS = ("DAT_EXTMEM", "symbol")
# The third value `spelled_as` can carry, and the only one this tool infers
# rather than reads. An address reaches it through a call this tool resolved
# (see `pair_sites()`), so it is orthogonal to the two token spellings above:
# an address can be `symbol+pair-literal`, and the self-test asserts the real
# invariant -- never `symbol` and `DAT_EXTMEM` together in one program -- rather
# than the old "one spelling per address" that only held while there were two.
PAIR_SPELLING = "pair-literal"
# The order both spelling columns are written in: the exporter's two token
# spellings first and the inferred one last. A fixed tuple rather than a walk
# over `entry["spellings"]` because that is a set, and a set walk would make the
# committed CSV differ between two runs of the same tree.
SPELLING_ORDER = ("symbol", "DAT_EXTMEM", PAIR_SPELLING)
# The two values `pair_role` can carry, and the order it writes them in -- the
# byte the call site names first, the byte the accessor's own `inc DPTR` walks
# onto second. A fixed tuple for the reason `SPELLING_ORDER` is one: the set is
# a set, and a set walk would make the committed CSV differ between two runs of
# the same tree.
PAIR_SEED = "seed"
PAIR_INC = "inc-dptr"
PAIR_ROLE_ORDER = (PAIR_SEED, PAIR_INC)
ASSIGN = ("=", "|=", "&=", "+=", "-=", "*=", "/=", "^=", "%=", "<<=", ">>=")

# The metrics the per-program count columns carry: the row's whole `refs` and
# each of the five buckets, in the same order the unsuffixed columns above sit
# in ($6 through $11), so `$6` and `$22`/`$23` answer the same question about
# different address spaces.
PER_PROGRAM_METRICS = ("refs",) + BUCKETS


def program_suffix(g: str) -> str:
    """The per-program columns' suffix for one `GROUPS` key: `main-ec` ->
    `_main_ec`.

    A function rather than a table, so the `program` column's two spellings of
    a program and the column names' two cannot come to be different mappings.

    **`_pd`, not `_pd_image`,** deliberately.
    `ec/annotations/registers.yaml` writes its own per-program reference
    figures `static_refs_main_ec` / `static_refs_pd_image`, and that is the
    precedent; this CSV's vocabulary is already `pd` -- the `program` column's
    value, the `cluster_id` prefix, the `pd=` label in `spellings_by_program`
    two columns to the left on the same row -- so writing `_pd_image` here would
    put two spellings of one program in one line, which is the confusion the
    columns exist to remove. The divergence from `registers.yaml` is recorded
    here and in the write-up rather than left for a reader to trip over.
    """
    return "_" + g.replace("-", "_")


def per_program_columns() -> tuple:
    """The twelve per-program count columns, in CSV order.

    Metric first, then program: `refs_main_ec`, `refs_pd`, `read_main_ec`,
    `read_pd`, and so on through the five buckets, so one program's whole half
    is a contiguous run and a `cut -d, -f22-33` gives the main EC while
    `-f23,25,27,29,31,33` gives the pd image's. Metric-major rather than
    program-major because the two halves of a `both` row are what a reader
    compares, and metric-major puts the two numbers for one metric next to
    each other with the summed cell 16 columns to their left.

    A function rather than a literal list so the column names and the cells
    `build()` writes cannot come to describe different sets -- the same
    "the tool that writes the column and the tool that checks it" argument
    `spellings_of()` makes for the two spelling columns, and it answers the one
    failure mode `DictWriter` cannot report: a name in `fieldnames` with no
    cell in a row is written as `''` rather than raised, so a drift here would
    leave a plausible CSV with empty numeric cells in it, which `--check`
    catches only as a byte diff and `--self-test` only as a `ValueError` that
    points at the wrong line. The self-test asserts the two halves against each
    other.
    """
    return tuple(f"{metric}{program_suffix(g)}" for metric in PER_PROGRAM_METRICS
                 for g in GROUPS)


REGISTER_COLUMNS = [
    "addr", "program", "spelled_as", "span_group", "cluster_id", "refs",
    "read", "write", "read+write", "passed-to-call", "address-taken",
    "readers", "writers", "functions_touched", "single_function", "name",
    "functions", "cluster_key", "co_reading", "sources_beyond",
    # `spellings_by_program` is **appended rather than placed beside
    # `spelled_as`**, because committed `awk -F,` / `cut -d,` commands read
    # this file by position: `docs/findings/xdata-census-totals.md` sums `$6`
    # and adds up `$7`-`$11`, and
    # `docs/findings/xdata-export-ownership-page-census.md` does the same over
    # its two scratch files; that page already names this as "the thing that
    # would break first if a column were added". Inserting beside column 3
    # moves every one of those fields; appending leaves each meaning what it
    # means today. No committed Python tool reads the file by index --
    # `check_cluster_citations.py`, `check_site_census.py`,
    # `test_xdata_cluster_names.py`, `rank_common_runtime.py` and
    # `check_capture_claims.py` all go through `csv.DictReader` or a regex over
    # a named cell.
    "spellings_by_program",
    # The twelve per-program count columns are appended **on the same terms**,
    # for the same reason and by the same argument: `$6`-`$11` keep meaning
    # what they mean today, and the two positional readers above are unchanged
    # rather than only un-broken. Two things follow from the append that did
    # not hold for a first append. **`spellings_by_program` is no longer the
    # last column** -- it is `$21` and the fields after it are interior, so
    # `cut -d, -f21` still selects it and a reader who asks for "the last
    # column" now gets `address-taken_pd`. And **comma-free is load-bearing
    # here in a way it was only advisory for a spelling cell**: every one of
    # these twelve is a bare integer read by the positional readers, so a
    # thousand separator or a unit suffix in any one of them would make
    # `awk -F,` shift the field. `per_program_counts_of()` can only write an
    # `int`, which is what makes the guarantee mechanical rather than a rule
    # somebody has to remember. The write-up is
    # `../../docs/findings/xdata-per-program-counts.md`.
    *per_program_columns(),
    # `pair_role` is appended **on those terms again**: a third append, same
    # argument, so `$6`-`$11` and `$21`-`$33` all still mean what they mean. It
    # is written on every row rather than only on the pair-reached ones,
    # because an empty cell is the answer "no pair call reaches this address"
    # and a column that is blank on most of the file is the `int('')`-where-
    # `int`-is-natural failure `per_program_counts_of()` names -- and because
    # a cell written on every row is one a check can hold to every row. The
    # write-up is `../../docs/findings/xdata-pair-role-column.md`.
    "pair_role",
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

# The census's own figures are not pinned in this file. Every one of them moves
# when a routine is seeded or a register named, which is the work the census
# measures, and a pin on them was a line every such branch had to edit. The
# figures are the committed CSVs, which `--check` regenerates, and
# `--self-test` asserts what holds at any size. The history of the pins that
# stood here is `git log -p` on this file.

# The counter sweep of `annotations/xdata-06c2-06db-timers.md` §2, as the first
# and last `out_file` of the largest co-reading group. A sweep split across two
# groups would be a different claim from one group. The last is `0x80EF`, not
# `0x8189`: the listings are the *seeds* inside the run, and `0x8189` is where
# the run ends.
COREADING_SWEEP = ("bank1/8001.c", "bank1/80EF.c")

# Issue #279: the routines `load_pair_accessors()` selects, pinned as a *set* so
# the rule is asserted rather than the constant. A sixth accessor annotated
# without a change here is not a failure by itself -- the rule finds it, and its
# callers are resolved through it -- but a *retreat* from one of these six
# would be the resolver quietly narrowing, and that has to fail.
#
# Four are the issue's: 0x8886/0x888C/0x8892/0x889E. `0x8898` is the fifth the
# issue does not name, of identical shape and already annotated; `0x9193` is a
# sixth, byte-for-byte the same body as `0x888C` and reached only with a
# register (`bank1/D946.c:43`, `bank1/D4D3.c:25`), so it resolves nothing.
# Including it is what it means to read the set out of the tree instead of
# listing the ones that pay: a name that happens to be on the list is not what
# makes a call site resolve.
#
# The pd image's own pair accessor, `read_be16_from_dptr` at `pd:0x38D3`, is
# selected by the same rule and its single caller passes no argument, so the
# whole set resolves inside bank1. That is why no program carve-out appears in
# `load_pair_accessors()`: scoping it to bank1 would have been a boundary with
# a number behind it, and the number is zero.
PAIR_ACCESSORS = (
    ("read_xdata_pair_to_r1r2", "read"),
    ("read_xdata_pair_to_b_and_a", "read"),
    ("read_xdata_pair_to_r3r4", "read"),
    ("read_be16_from_dptr", "read"),
    ("store_r1_r2_to_xdata_at_dptr", "write"),
    ("write_r1r2_to_xdata_pair", "write"),
    ("write_r3r4_to_xdata_pair", "write"),
)
# **The one address the two readings of "mixed" disagree on.** The census keys
# spellings per program, and `xdata-registers.csv` records one `spelled_as` per
# address, whose `program=both` cell is the union across the two programs.
# `0x04A3` is `pair-literal` in the main EC and a `DAT_EXTMEM_` token in the pd
# image, so it is pair-only within a program and mixed in the CSV. The
# self-test asserts that this is the whole of the difference, as a set. The
# write-up is `../../docs/findings/xdata-spelled-as-union.md`.
PAIR_UNION_ONLY = (0x04A3,)
# **The four `both` rows whose union carries `pair-literal`, and what each half
# actually is.** The CSV's one `spelled_as` column cannot say which program
# contributed which token, and these are the rows where that is load-bearing:
# three of them are genuinely `DAT_EXTMEM+pair-literal` *inside the main EC*,
# and `0x04A3` is not. `(main-ec spellings, pd spellings)`.
PAIR_BOTH_PAIR_LITERAL = {
    0x04A3: (("pair-literal",), ("DAT_EXTMEM",)),
    0x0834: (("DAT_EXTMEM", "pair-literal"), ("DAT_EXTMEM",)),
    0x0835: (("DAT_EXTMEM", "pair-literal"), ("DAT_EXTMEM",)),
    0x0836: (("DAT_EXTMEM", "pair-literal"), ("DAT_EXTMEM",)),
}
# The two worked examples the issue asks for, as the exact multiset of resolved
# sites rather than a bucket total. `0x0402` is the address whose decompile
# Ghidra invented a *routine* at (`common/0402.c`, spelled `FUN_CODE_0402` at
# ten bank1 call sites), and `0x0408` the second of the same; between them they
# are the whole of the `FUN_CODE_` half of the pass.
#
# **10 against 3 is not a disagreement, it is the two methods.** The image has
# three `mov DPTR,#0x0402` + `lcall <accessor>` encodings in bank1, which is
# what `registers.yaml`'s `static_refs_main_ec: 3` counts and this pass does
# not touch. The census counts ten because the decompiler emitted one block
# into five overlapping `.c` files (B407 forwards to B40E; B40E/B415/B41C/B43B
# are successive seeds over 0xB40E-0xB4B6, and the `mov DPTR,#0x0402` at
# 0xB4BD is inside that span). The census is per-`.c`-file in its counting and
# has always been a lower bound on the machine code; the inflation is a
# pre-existing property of the whole census, not of this pass.
PAIR_RESOLVED = {
    # 7 read / 3 write, all ten in bank1, the writers being the three
    # `write_r3r4_to_xdata_pair` / `write_r1r2_to_xdata_pair` sites. 0x0403
    # picks up a writer for the first time as the `inc DPTR` half.
    0x0402: (("bank1/AD85.c", "read"), ("bank1/B33B.c", "read"),
             ("bank1/B407.c", "read"), ("bank1/B40E.c", "read"),
             ("bank1/B415.c", "read"), ("bank1/B41C.c", "read"),
             ("bank1/B43B.c", "read"), ("bank1/DB0B.c", "write"),
             ("bank1/DEE8.c", "write"), ("bank1/DEF1.c", "write")),
    # 3, all write, and all the same accessor: `write_r1r2_to_xdata_pair`.
    0x0408: (("bank1/DB0B.c", "write"), ("bank1/DEE8.c", "write"),
             ("bank1/DEF1.c", "write")),
}
# The double-count trap, pinned as a set. `bank1/9354.c:19` passes
# `DAT_EXTMEM_0318` to `read_xdata_pair_to_r3r4`, and `occurrence_re` already
# counts that argument as a `passed-to-call` reference. Resolving it as a pair
# as well would give `0x0318` a read it has no site for and `0x0319` a reference
# with no site behind it.
#
# **Three independent gates stop that and no single-point edit opens it** --
# see `pair_sites()`. The literal gate is what does it today
# (`DAT_EXTMEM_0318` is not one of its forms); the `fullmatch` gate catches a
# widening of the literal gate; and the `int()` catches dropping that one. The
# self-test pins the outcome rather than any of them: `0x0318` is reached
# through an accessor in exactly two other files, and its row keeps the two
# spellings separable -- 14 references spelled `DAT_EXTMEM_` and 2 spelled
# `pair-literal`, out of 16 in all.
PAIR_ALREADY_COUNTED = (0x0318, "bank1/DEE8.c", "bank1/DEF1.c")

# The two symbol-table addresses register_ref_table.py finds main-EC sites for
# that the census does not. Both are inside
# bank0:0x94D0=copy_code_table_into_0730_07a7: 0x0733 is spelled
# `puVar3 = &DAT_CODE_0733;`, as a code pointer, and 0x0735 is not spelled at
# all -- `sVar5 = 0x735; ... *(char *)(sVar5 + bVar2)` is an indexed access off
# a raw base literal. Only the first is findable, so only it is checked; see
# the self-test and the report's blind-spot section.
#
# **Unmoved by issue #279, and that is the point of the pair of them.** The
# pair pass reads a `FUN_CODE_`/`DAT_CODE_` literal in exactly one context --
# the first argument of a routine whose committed `.asm` is two `movx @DPTR`
# an `inc DPTR` apart -- and neither address is reached that way. 0x0733 is a
# real code pointer into `copy_code_table_into_0730_07a7`; the reason the
# exclusion was ever relaxed for `0x0402` is that a *callee's* `movx` settles
# the address space, and 0x0733 is not handed to such a callee. The self-test
# asserts `code_only == {0x0733}` after the pass, not before it.
BLIND_SPOT = (0x0733, 0x0735)

# The addresses the generated symbol table names and the census does not reach:
# `set(symbols) - everywhere`. Issue #280 pins this as a *set* rather than as
# the `named_in_tree` count alone, so "which addresses" is re-derivable here
# instead of only from a failure message, and so the count of named addresses
# in the tree is arithmetic over this dict rather than a number to be taken on
# trust.
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
    #
    # *** 2026-09-25, issue #279: the first reason below is the one this pass
    # acts on, and 0x0402 and seven of its neighbours have left the dict
    # because the reason stopped being true. `occurrence_re` still matches no
    # function name -- that has not changed and should not. What changed is
    # that `pair_sites()` resolves a `FUN_CODE_` literal handed to a callee
    # whose committed `.asm` is two `movx @DPTR` an `inc DPTR` apart, which is
    # the discriminator this issue is about: `movx` names the external space,
    # so the address is XDATA whatever Ghidra called it. The 25-entry set here
    # is 17. The eight that closed are 0x0402 0x0404 0x0408 0x040A 0x040C
    # 0x040E 0x0410 and 0x043A, and `0x0420` is deliberately *not* one of
    # them: it is passed to `add_full_product_to_dptr`, which is a record
    # helper rather than a two-byte accessor and is not selected by
    # `pair_accessor()`, so the same spelling with a different callee still
    # says nothing. The address space is a property of the callee, not of the
    # token.
    0x0420: "reached through a form the scan cannot see: passed to a record "
            "helper as a bare hex literal, `add_full_product_to_dptr"
            "(0x420,0x60,...)` at pd/34A5.c:18 -- the callee is not a "
            "consecutive-pair accessor, so issue #279's `movx` discriminator "
            "does not reach it",
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
    # Issue #30's ten: the DSDT ECMG field sweep landed these as entries, and
    # none of the ten is in the decompiled tree, so each needs the reason the
    # vocabulary above is for. Two different ones, and the difference matters.
    #
    # CTL1-CTL7 (0x0EA9-0x0EAF) are in the EC firmware and the export simply
    # does not reach them: their one site each is inside the straight-line copy
    # at bank0 0xF335-0xF374, which lies in the gap between the exported
    # functions bank0:0xF239 and bank0:0xF424. Seeding that routine needs
    # `--mode rebuild-project`. 0x0EA8 and 0x0EB8 are NOT in this set, and that
    # is the copy explaining it -- they have a second site each, in
    # bank0:0xF221, which *is* an exported function, so the census reaches them
    # by that route.
    0x0EA9: "in a routine no export covers: the single `mov DPTR,#0x0ea9` is at "
            "bank0 0xF33D, inside the copy at 0xF335-0xF374 and in the gap "
            "between the exported functions bank0:0xF239 and bank0:0xF424",
    0x0EAA: "in a routine no export covers: as 0x0EA9, at bank0 0xF345",
    0x0EAB: "in a routine no export covers: as 0x0EA9, at bank0 0xF34D",
    0x0EAC: "in a routine no export covers: as 0x0EA9, at bank0 0xF355",
    0x0EAD: "in a routine no export covers: as 0x0EA9, at bank0 0xF35D",
    0x0EAE: "in a routine no export covers: as 0x0EA9, at bank0 0xF365",
    0x0EAF: "in a routine no export covers: as 0x0EA9, at bank0 0xF36D",
    # AP01/AP02/AP10 (0x07C0-0x07C2) are the three the sweep graded
    # unknown-not-absent, and the reason is a different one again: the only
    # `mov DPTR` for each in the whole 256 KiB dump is in the ITE8850-PD image,
    # where DPTR is handed to a PD subroutine. That is a reference to another
    # program's byte, so the EC decompile this census reads has nothing to find
    # -- not a coverage gap. Uncovered anyway, as those PD routines are not
    # exported either, which is why the second reason would also be true; the
    # wrong-program fact is the one that decides what these three are, so it
    # leads. Re-derive with trace_xdata_refs.py, which is the split the
    # registers.yaml rows are graded on.
    0x07C0: "not found by this method: the sole `mov DPTR,#0x07c0` in the dump "
            "is at pd 0xE7EE, handing DPTR to lcall 0x9c8a -- the ITE8850-PD "
            "image's own byte, whose XDATA map is its own, so the EC export "
            "this census reads has no reference to find. That is a statement "
            "about the scan and not about the byte, which is why "
            "registers.yaml's AP01 row takes the status it takes rather than "
            "an absence one",
    0x07C1: "not found by this method: as 0x07C0, at pd 0xE810 handing DPTR to "
            "lcall 0x9c8f",
    0x07C2: "not found by this method: as 0x07C0, at pd 0xE7FC handing DPTR to "
            "lcall 0x9c8f",
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
    # A compound assignment reads what it writes -- what `&=` cannot say on its
    # right-hand side. Measured over the committed tree none follows an address
    # token (#424), so the pair costs no bucket: it was pinned as the measured
    # `write`, which is the misclassification this corrects. `<<=` and `>>=` are
    # here so the prefix test is pinned for three-character operators as well as
    # two-character ones.
    ("DAT_EXTMEM_0440 &= 0x0f;", "read+write"),
    ("DAT_EXTMEM_0440 |= 0x0f;", "read+write"),
    ("DAT_EXTMEM_0440 <<= 1;", "read+write"),
    ("DAT_EXTMEM_0440 >>= 1;", "read+write"),
    ("if (DAT_EXTMEM_0440 == 0) {", "read"),
    # `&&`, with a leading operand `occurrence_re` does not match. The self-test
    # resolves a snippet with `pattern.search`, the *first* match only, so what
    # has to follow the `&&` is the first address token in the literal -- and a
    # literal that begins with one cannot test this clause at all, however the
    # operands are ordered. `bank0/A747.c` puts its address second, so the tree's
    # own shape cannot supply it; `param_1` supplies a leading operand that is
    # not an address. The second literal is `==`-free.
    ("if (param_1 == '\\0' && DAT_EXTMEM_0440 == 0) {", "read"),
    ("if (param_1 && DAT_EXTMEM_0440) {", "read"),
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
# The same spelling, anchored, for the one context that may read it: a literal
# first argument to a routine `pair_accessor()` selected. `pair_sites()` is the
# only reader outside the self-test, and the self-test asserts the two sets it
# resolves to are the ones the issue named and nothing else.
CODE_SPELLING = re.compile(r"(?:FUN|DAT)_CODE_([0-9a-fA-F]{4})")
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
# The first argument of a pair-accessor call, in the three literal forms the
# export produces for an XDATA address. `FUN_CODE_`/`DAT_CODE_` are the
# decompiler's own spelling for a routine it *invented* at an address its caller
# used as data -- `common/0402.c` is such a routine -- and the resolver accepts
# them for exactly the accessors `pair_accessor()` selects, and for nothing
# else. The decimal alternative is not decoration: all six of the tree's
# decimal *first* arguments are decimal, `900` for `0x0384` at `C931.c:26`,
# `C979.c:22`, `CFB1.c:24` and `D946.c:85` and `1000` for `0x03E8` at
# `CF0B.c:23` and `CF3C.c:26`. The decimal `100` in `D2A3.c`, `F3D7.c` and
# `F416.c` is a *second* argument to a call whose address is the first
# (`read_xdata_pair_to_r1r2(0x438,100,0)`), and is not what this reads.
PAIR_LITERAL = re.compile(
    r"^(?:0[xX][0-9a-fA-F]{1,4}|(?:FUN|DAT)_CODE_[0-9a-fA-F]{4}|[0-9]+)$")
# Direction a pair accessor carries, keyed by the annotation `type` that says
# the same thing. The two are cross-checked against each other rather than one
# being derived from the other, so an annotation that stops matching its own
# committed `.asm` is a failure here and not a silent reclassification.
PAIR_TYPE_DIR = {"reader": "read", "writer": "write"}
# Registers a pair accessor may shuffle between its two dereferences. Anything
# else in the body -- an `add`, an `rrc`, a branch -- means the routine is more
# than an accessor, and it is left out rather than resolved.
PAIR_SHUFFLE = ("A", "B", "R0", "R1", "R2", "R3", "R4", "R5", "R6", "R7")


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
    and would still have passed on the pre-fix classifier that
    `CLASSIFIER_SHAPE` exists to catch.

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
    is the oracle; 149 of this tree's listing lines are not contiguous, because
    a listing legitimately includes jump tables and string data, so a blanket
    contiguity assertion would be false. `xdata_register_map
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


def pair_accessor(seq) -> str:
    """`"read"` or `"write"` if this listing is a consecutive-XDATA-pair
    accessor, else None.

    **The discriminator is the callee's own encoding, never the caller's
    spelling.** `movx` is the instruction that names the external data space, so
    a routine whose whole body is two `movx @DPTR` dereferences an `inc DPTR`
    apart hands its caller two adjacent XDATA bytes whatever Ghidra called the
    address. That is what makes `FUN_CODE_0402` a *data* address and not a code
    pointer, and it is why `BLIND_SPOT`'s `0x0733` -- a real code pointer, at
    `bank0:0x94D0` -- stays excluded: it is not handed to an accessor at all.

    The test is deliberately strict about the rest of the body. Everything
    outside the two dereferences must be an `inc DPTR` between them, a `mov` of
    a register or the accumulator, or the closing `ret`, so a routine that reads
    a pair and then does arithmetic on it is not an accessor and its callers'
    literals are not resolved through it. `bank1:0x9182` is that case on this
    tree: two `movx` and an `inc DPTR`, then `add`/`addc`/`rrc`, and its two
    callers pass a variable rather than a literal anyway.
    """
    deref = [i for i, (_, mnem, oper) in enumerate(seq)
             if mnem == "movx" and "@DPTR" in oper]
    if len(deref) != 2 or seq[-1][1] != "ret":
        return None
    first, second = deref
    if not any(m == "inc" and o == "DPTR"
               for _, m, o in seq[first + 1:second]):
        return None
    for i, (_, mnem, oper) in enumerate(seq):
        if mnem == "movx" and "@DPTR" in oper:
            continue
        if mnem == "inc" and oper == "DPTR" and first < i < second:
            continue
        if mnem == "ret" and i == len(seq) - 1:
            continue
        if (mnem == "mov"
                and oper.split(",")[0].strip() in PAIR_SHUFFLE):
            continue
        return None
    ops = (seq[first][2], seq[second][2])
    if ops == ("A, @DPTR", "A, @DPTR"):
        return "read"
    if ops == ("@DPTR, A", "@DPTR, A"):
        return "write"
    return None


def load_pair_accessors() -> dict:
    """{accessor name: direction} for the routines `pair_accessor()` selects.

    **Derived from the annotation and the disassembly together, and from neither
    alone.** `ghidra-functions.csv` supplies the name and the direction it
    claims; the committed `.asm` beside it says whether the body really is two
    `movx` an `inc DPTR` apart, and a disagreement is raised rather than
    resolved, because one of the two is then wrong about a routine this pass is
    about to resolve callers through.

    Reading the set out of the tree rather than hardcoding it is the point. The
    issue named four accessors; `0x8898` is a fifth of identical shape that
    happens already to carry a name, and `0x9193` a sixth whose two callers
    both pass a register, so it resolves nothing. Both are found by the rule, so
    neither needed a decision about whether to include it, and a seventh
    annotated accessor is found the same way.

    Tree-wide the rule selects six routines in bank1 and one in the pd image
    (`read_be16_from_dptr`), whose single caller passes no argument at all. All
    seven resolve nothing outside bank1, which is what the census moves.
    """
    asm = {}
    out = {}
    with open(ANNOT_CSV, newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r["type"] in PAIR_TYPE_DIR]
    for row in sorted(rows, key=lambda r: (r["scope"], r["addr"])):
        scope = row["scope"]
        if scope not in asm:
            asm[scope] = read_asm(scope)
        got = pair_accessor(asm[scope].get(row["addr"], ()))
        if got is None:
            continue
        want = PAIR_TYPE_DIR[row["type"]]
        if got != want:
            raise SystemExit(
                f"error: {ANNOT_CSV} types {scope}:0x{row['addr']}="
                f"{row['name']} as a {row['type']}, but its committed .asm is "
                f"a {got} (two `movx @DPTR` an `inc DPTR` apart): the "
                "annotation and the disassembly disagree about the direction "
                "this pass resolves its callers in")
        out[row["name"]] = got
    return out


def pair_sites(text: str, accessors: dict, pattern):
    """[(addr, direction)] for each pair-accessor call in `text`.

    Three gates, in this order. **They are not equally load-bearing and the
    difference is measured, not assumed** -- which is why the second is here at
    all when the third already excludes everything it would catch:

    - **The callee must be a selected accessor.** This is the only place in the
      tool that reads a `FUN_CODE_`/`DAT_CODE_` argument, and it does so only
      for the routines whose committed `.asm` dereferences XDATA. Everywhere
      else the code-pointer exclusion above stands.
    - **The argument must be a bare literal.** Arithmetic (`DAT_EXTMEM_04ab +
      0xa6`), a `CONCAT11(3,bVar3)` index and a register all describe a byte
      this tool cannot name without guessing which one runs, and the honest
      answer for each is the one `NOT_IN_TREE` already gives elsewhere: not
      found by this method.
    - **The argument must not already be an occurrence.** `bank1/9354.c` passes
      `DAT_EXTMEM_0318` to the same accessor and `occurrence_re` already counts
      that argument, so resolving it as a pair as well would give `0x0318` a
      read it has no site for and `0x0319` a reference with no site behind it.

      **This gate is one of three independent defences against that, and on
      this tree it is the one that does least.** Zero of the tree's 461 first
      arguments are both a literal and an occurrence, so the gate above has
      already rejected all of them; widening the literal gate to admit
      `DAT_EXTMEM_` is then caught by this one, and dropping *this* one is
      caught by the `int()` below, which cannot read `DAT_EXTMEM_0318` as a
      number and skips it. There is no single-point edit that opens the trap,
      which is the property worth having and the reason the redundancy is here
      rather than trimmed to the shortest form that works today.
      `--self-test` pins the **outcome** -- `0x0318` is reached through an
      accessor from exactly two files, and its row keeps 14 `DAT_EXTMEM_`
      references separable from 2 `pair-literal` ones out of 16 -- rather than
      any one gate, because the outcome is the fact and the gates are the
      current means to it.

    A call site's first argument can be followed by more arguments -- the
    decompiler gives these accessors a three-parameter signature it never
    established, so `write_r1r2_to_xdata_pair(0x434,0,0)` is the common shape --
    so the argument is read to the first top-level comma rather than to the
    closing paren.
    """
    if not accessors:
        return
    call = re.compile(r"\b(" + "|".join(sorted(map(re.escape, accessors),
                                              key=len, reverse=True))
                      + r")\s*\(")
    for m in call.finditer(text):
        # The alternation is built from `accessors`, so every name it matches
        # is a key -- but `.get` rather than `[]` because a caller passing a
        # table this function did not build is a wrong answer, not a crash the
        # reader should have to read a traceback to understand.
        direction = accessors.get(m.group(1))
        if direction is None:
            continue
        depth, i, start = 1, m.end(), m.end()
        while i < len(text) and depth:
            c = text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if not depth:
                    break
            elif c == "," and depth == 1:
                break
            i += 1
        arg = text[start:i].strip()
        if not PAIR_LITERAL.match(arg) or pattern.fullmatch(arg):
            continue
        lit = CODE_SPELLING.fullmatch(arg)
        try:
            addr = (int(lit.group(1), 16) if lit
                    else int(arg, 16) if arg[:2].lower() == "0x"
                    else int(arg, 10))
        except ValueError:
            # `PAIR_LITERAL` was widened to a form the arithmetic below cannot
            # read. Skipping is the right answer and raising is not: a literal
            # this function cannot name is "not found by this method", the
            # same as any other first argument it declines.
            continue
        yield addr, direction


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
    if left.endswith("&") and not left.endswith("&&"):
        return "address-taken"
    if store_target(text, start, end, eq_guard):
        # Tested by prefix over the same tuple `store_target()` uses, so a
        # three-character operator like `<<=` can match at all; a fixed-length
        # slice could not.
        stripped = text[end:].lstrip()
        return ("read+write" if any(stripped.startswith(op) for op in ASSIGN[1:])
                or addr in rhs_of(text, text.index("=", end)) else "write")
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
    0x06E6's 50 touchers a writer when 3 of its 72 references write it.

    `spelled_refs` is what the two *token* spellings are about, kept apart
    from `refs` on purpose. While the spellings were disjoint
    within a program the two were the same number, and the self-test's
    `DAT_EXTMEM_`-only figure could be had by summing `refs` over the addresses
    that carry the spelling. Issue #279 ended that: an address reached both as
    a token and as a pair-accessor argument has references of both kinds, so
    `refs` no longer answers "how many references are spelled `DAT_EXTMEM_`?" --
    and a pin whose *meaning* moves under a number that moves is the one
    conflation this file exists to prevent."""
    return {"refs": 0, "buckets": collections.Counter(),
            "funcs": collections.Counter(), "dirs": collections.defaultdict(set),
            "spellings": set(), "spelled_refs": collections.Counter(),
            "pair_roles": set()}


def absorb(entry, src):
    """Fold one file's (or one scope's) contribution into an address."""
    entry["refs"] += src["refs"]
    entry["buckets"].update(src["buckets"])
    entry["funcs"].update(src["funcs"])
    entry["spellings"].update(src["spellings"])
    entry["spelled_refs"].update(src["spelled_refs"])
    entry["pair_roles"].update(src["pair_roles"])
    for f, buckets in src["dirs"].items():
        entry["dirs"][f].update(buckets)
    return entry


def touches(entry, bucket: str):
    """The functions of `entry` that used `bucket` themselves."""
    return {f for f, buckets in entry["dirs"].items() if bucket in buckets}


def spellings_of(entry) -> str:
    """One entry's spellings, as a `+`-joined cell in SPELLING_ORDER.

    Both spelling columns render through this one function, so the two cells
    cannot come to describe different sets -- the same "the tool that writes
    the column and the tool that checks it" argument
    `ec/annotations/README.md` makes for `name_basis`."""
    return "+".join(s for s in SPELLING_ORDER if s in entry["spellings"])


def pair_role_of(entry) -> str:
    """One entry's pair role, as a `+`-joined cell in PAIR_ROLE_ORDER, or "".

    `spelled_as` answers *how* the address was reached and is deliberately
    blind to which half of the pair it is: `scan()` folds a call's `addr` and
    `addr + 1` into one `pair-literal` row under the same spelling. This is
    the column that takes the two apart -- `seed` for the byte a committed call
    site passed, `inc-dptr` for the one the accessor's own `inc DPTR` walked
    onto -- and empty for every row no pair call reaches, which is a real
    answer rather than a missing one and is what makes the column checkable
    corpus-wide.

    **A set, joined in a fixed order, because an address can be both.** Two
    call sites can pass `a` and reach `a + 1` themselves, so the two halves are
    not disjoint by construction; on the committed tree they are, and the
    self-test measures that rather than assuming it. A cell reading
    `seed+inc-dptr` would then be a true statement about one address rather
    than the writer silently dropping one role for the other.

    Comma-free for the reason `REGISTER_COLUMNS` gives -- this can only join
    from a fixed tuple, so there is no path by which a comma reaches the cell,
    and the positional `awk -F,` readers keep every field they have today.
    """
    return "+".join(r for r in PAIR_ROLE_ORDER if r in entry["pair_roles"])


def spellings_by_program_of(groups, addr) -> str:
    """The same spellings, one `program=…` clause per program the row touches.

    `main-ec=…` alone on a main-EC row, `pd=…` alone on a pd one, and
    `main-ec=…;pd=…` on a `both` row. A `program=both` row's `spelled_as` is
    the union across the two, and a shared address number is not a shared byte,
    so this is what a per-program question has to be read from. Comma-free --
    only `+`, `;` and `=` appear -- so the positional `awk -F,` / `cut -d,`
    commands `REGISTER_COLUMNS` names keep working, and the same reason those
    two columns cannot contain a comma is what makes `-F,` safe on this file at
    all (`docs/findings/xdata-census-totals.md`)."""
    return ";".join(f"{g}={spellings_of(groups[g][addr])}"
                    for g in GROUPS if addr in groups[g])


def per_program_counts_of(groups, addr) -> dict:
    """Every count on a row, once per program, from the per-program entries.

    The same per-program entries `spellings_by_program_of()` reads and the
    union in `build()` is absorbed out of, so the halves and the sum cannot
    disagree about which reference went where -- and this is a *split*, not a
    second pass: no reference is counted here that the unsuffixed columns do not
    already carry, which is what leaves `refs`, the five buckets and every
    census total exactly where they were.

    **All twelve cells are written on every row, not only on the 49 `both`
    ones.** On a `main-ec` row `refs_main_ec` is the row's whole `refs` and
    `refs_pd` is `0`; on a `pd` row the reverse. A column populated on 49 rows
    and empty on 1,277 is a shape no `csv.DictReader` consumer can rely on --
    `int('')` where `int` is the natural read -- and the partition
    `refs == refs_main_ec + refs_pd` is only checkable corpus-wide if every row
    carries both halves.

    **A zero in the other program's column means the census found no reference
    in that program, and nothing more.** It is "not found by this method over
    the committed decompiled tree", never "absent from the image" and never a
    claim that the program cannot reach the byte; see the calibration rule in
    `CLAUDE.md` and the write-up's "What this does not establish". Nor is a
    per-program `write` anything but a static shape: not evidence the EC acts on
    the byte.

    Comma-free -- bare integers and nothing else -- which is what keeps the
    positional `awk -F,` / `cut -d,` readers `REGISTER_COLUMNS` names exact.
    `int` in, `int` out, so the constraint is mechanical rather than a rule
    somebody has to remember."""
    out = {}
    for metric in PER_PROGRAM_METRICS:
        for g in GROUPS:
            half = groups[g].get(addr)
            out[f"{metric}{program_suffix(g)}"] = (
                0 if half is None
                else half["refs"] if metric == "refs"
                else half["buckets"].get(metric, 0))
    return out


def scan(by_file, names, func_names, symbols, eq_guard: bool = True,
         export_ownership: bool = False, ownership=None, accessors=None):
    """(per-program census, call graph, raw occurrence count) over the tree.

    An address is reached from many files in one program, so the per-file
    counts accumulate into the program's entry rather than replacing it.

    The raw count is what the files say before comments are blanked, kept so
    the self-test can assert that the census never counts more tokens than
    the files hold. It counts the two *token* spellings only; a
    pair-accessor site is this tool's own reading of an argument, so it lands
    in the census and not in `raw`.

    **`accessors` is the `load_pair_accessors()` table, and it is a parameter
    rather than a call so the self-test can pass a subset.** Every routine it
    names contributes two references per call site -- the accessor's `inc DPTR`
    makes the access a pair, so `a` and `a+1` are both touched -- in the
    *callee's* direction, because the direction is the callee's body and the
    caller's own expression says nothing about it. `0x889E`'s
    `write_r3r4_to_xdata_pair(0x834,uVar1,uVar2)` is the case: the arguments
    after the first are the decompiler's unestablished parameters, and reading
    the `=` that follows one of them as a store is how this tool used to get
    directions wrong.

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
    renumbers the whole tree -- `cluster_key` and the hand names, measured in
    `annotations/xdata-export-ownership.md` §5. The mechanism behind
    that is worth stating rather than only measuring: a non-owner whose owner
    is *not* a superset would take its references out of the census with them.
    On this tree none is, and the self-test asserts the pass loses no address;
    see
    annotations/xdata-export-ownership.md."""
    pattern = occurrence_re(symbols)
    by_name = {name: addr for addr, name in symbols.items()}
    accessors = load_pair_accessors() if accessors is None else accessors
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
            entry["spelled_refs"][spelling] += 1
        # The pair accessors, resolved the other way round: the address is not
        # written in this file at all, it is an *argument* to a callee whose
        # committed `.asm` dereferences two adjacent XDATA bytes. Folded into
        # the same `per_addr` so the readers/writers/functions columns and the
        # clustering all see it as any other reference of the caller's own.
        for addr, direction in pair_sites(text, accessors, pattern):
            for byte in (addr, addr + 1):
                entry = per_addr[byte]
                entry["refs"] += 1
                entry["buckets"][direction] += 1
                entry["funcs"][key] += 1
                entry["dirs"][key].add(direction)
                entry["spellings"].add(PAIR_SPELLING)
                entry["spelled_refs"][PAIR_SPELLING] += 1
                # `spelled_as` folds both halves into one `pair-literal`, so
                # the role is the only thing on the row that says which of the
                # two this is. Recorded in *this* loop rather than derived
                # afterwards, so it comes out of the same `pair_sites()` walk
                # that decided which calls resolve -- the same walk
                # `inc_dptr_sites.pair_pass()` takes, which is what makes the
                # two tools unable to disagree about the population.
                entry["pair_roles"].add(PAIR_SEED if byte == addr else PAIR_INC)
        for addr, entry in per_addr.items():
            absorb(census[row["program"]].setdefault(addr, blank_entry()), entry)
    return census, calls, raw


def direction_invariant(by_file, symbols, func_names, accessors=None):
    """(shaped, census_side, offenders, surplus, eq_after, eq_in_write).

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

    **`census_side` is what makes the invariant's population a measurement.**
    The walk already computes `bucket` for every occurrence and used to throw
    it away except to compare against `assign_after()`; it now also counts the
    occurrences the census buckets `write`/`read+write` and the addresses they
    land on, which is the population the check is about. `pair_refs` is the
    same sweep's by-direction pair count, so the caller can close the census
    against this pass without either side carrying a written-down figure.

    **It is a second code path, not a second opinion.** These counts come from
    the walk below and the census's own columns, so agreeing is arithmetic
    rather than corroboration; what the identity buys is that a figure nobody
    typed cannot drift away from the pass that measured it. `accessors` is the
    `load_pair_accessors()` table, defaulted here for the same reason `scan()`
    defaults it, so a caller holding a subset can pass one.
    """
    pattern = occurrence_re(symbols)
    accessors = load_pair_accessors() if accessors is None else accessors
    by_name = {name: addr for addr, name in symbols.items()}
    shaped = collections.Counter()
    offenders, surplus = [], []
    eq_after = eq_in_write = 0
    write_like = 0
    write_like_addrs = set()
    deref_addrs = set()
    pair_refs = collections.Counter()
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
            if bucket in ("write", "read+write"):
                write_like += 1
                write_like_addrs.add(addr)
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
                if left and left[-1] == "*":
                    deref_addrs.add(addr)
                else:
                    surplus.append(f"{site} ({bucket})")
        # A pair site names two bytes and `scan()` counts both, so the by-
        # direction figures the caller reconciles against are references, not
        # sites: the census's `spelled_refs[PAIR_SPELLING]` has no direction
        # split, which is the whole reason this sweep exists.
        for _, direction in pair_sites(text, accessors, pattern):
            pair_refs[direction] += 2
    census_side = {"write_like": write_like,
                   "write_like_addrs": write_like_addrs,
                   "deref_addrs": deref_addrs,
                   "pair_refs": pair_refs}
    return shaped, census_side, offenders, surplus, eq_after, eq_in_write


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
    census is complete without names, and a name is a label, not a count.

    It is anchored to the **committed** census -- the two CSVs as committed,
    which is the run `--check` reproduces: the `==` guard on, no
    `--export-ownership`, `--threshold 0.5`. A run that re-classifies
    occurrences re-clusters, so its keys are not the committed ones, and this
    file says nothing about that run's clusters. `--self-test` holds it to the
    committed census for the same reason."""
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
    column is a cluster with no name rather than a crash. The registers CSV
    goes through this same reader -- there is one parsing path for the two
    census files, not two."""
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []


def spellings_by_program(row) -> dict:
    """A committed row's `spellings_by_program` cell, as {program: spellings}.

    Read out of the file rather than re-rendered from a fresh generation: the
    column's claim is about the artifact a reader opens, and a check that
    compared the tool's output against itself would pass against a column
    written wrong in both. `row.get` is deliberate -- a census written before
    the column existed has none, which is a self-test failure to report rather
    than a KeyError to traceback out of the run."""
    out = {}
    for clause in row.get("spellings_by_program", "").split(";"):
        name, _, spellings = clause.partition("=")
        if name:
            out[name] = tuple(spellings.split("+"))
    return out


def per_program_cell(row, column) -> int:
    """One per-program count cell, as an int, from a committed row.

    `int(row[column])` would raise on a census written before the column
    existed, and -- worse for whoever is reading the failure -- on an **empty**
    cell. `render()` writes a name in `fieldnames` that a row does not carry as
    `''` rather than raising (`extrasaction` governs the other direction), so a
    name added to `REGISTER_COLUMNS` and forgotten in one `build()` branch
    produces a plausible CSV that `--check` catches only as a byte diff and this
    mode only as a `ValueError` pointing at the wrong line. A missing or blank
    cell is a self-test failure to report with the address beside it, which is
    what this returns: -1 for "this row has no usable cell here", a value
    outside every count in the census so no partition can be satisfied by it."""
    raw = (row.get(column) or "").strip()
    try:
        return int(raw)
    except ValueError:
        return -1


def carry_names(old_rows, seeded, new_rows):
    """({new cluster_key: name}, one report record per new cluster).

    A hand name is a claim about a *cluster*, and a cluster is its membership,
    so the name follows the membership rather than the rank. Six outcomes, and
    they are six because they are six different claims:

        seeded    the names file names this exact key -- a human said so
        exact     a named row of the committed census has this exact key
        overlap   a named row's membership scores >= CARRY_MIN_JACCARD against
                  this one. A weaker claim, and the score is in the record with
                  it: a name carried at 0.98 and one carried at 0.51 are not
                  the same statement about the firmware
        tie       two named rows are the joint best match. Which of them the new
                  cluster is, is a fact about the clustering and not a coin this
                  function flips, so no name is carried and both are reported
        duplicate this cluster and another both reached the name the loop picked
                  here. The mirror of `tie`, and the same refusal: no winner is
                  picked, and the second pass below takes the name away from
                  every cluster in the pair
        none      nothing cleared the threshold. **Not carried by this method**,
                  never gone -- a cluster the decompiler stopped producing is a
                  different claim from one that stopped existing, and the report
                  prints the best score it saw so a reader can tell "nothing
                  came close" from "nothing was even looked for"

    `old_rows` is read from the *committed* census rather than from
    `--out-clusters`, because the output is the thing being written: reading it
    back would make the carry a function of where this run happens to write.
    That is what lets a guard-off or a different-threshold run be carried from
    the census that is actually committed beside the prose.

    **A name is attached to at most one cluster, and the refusal is a second
    pass.** The loop above scores every new cluster and picks one name for it,
    which is a claim per *cluster*; nothing in it notices that two new clusters
    picked the same name, and `names` would then write that name to two rows of
    `xdata-clusters.csv`. So the first pass's scores stand exactly as they are
    and only the attachment is settled afterwards, by
    `xdata_name_coverage.duplicate_claims()`: the losers keep `name` in the
    record and take `how = "duplicate"`, so the report still says which name
    was refused, and `xdata_name_coverage.resolve_duplicate()` picks the
    survivor -- a `seeded`/`exact` record over any guess, then the best score,
    and **neither** on a tie. Two new clusters at the same score is a 2-address
    split of one membership, which is a fact about the clustering rather than a
    coin this function flips, exactly as the `tie` branch above refuses the
    mirror case."""
    old_named = [r for r in old_rows if (r.get("cluster_name") or "").strip()]
    by_key = {r.get("cluster_key", ""): r for r in old_rows}
    report = []
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
        report.append({"cluster_id": row["cluster_id"], "cluster_key": key,
                       "name": name, "how": how, "jaccard": score,
                       "from_key": from_key, "detail": detail})
    # The second pass, and the only thing in this function that changes what
    # gets written. `names` is left empty by the loop above on purpose: a name
    # two new clusters both reach has to be resolved before either of them can
    # be given it, and that is not a question the per-cluster loop can answer.
    how_of = {r["cluster_id"]: r["how"] for r in report}
    for name, claimants in xdata_name_coverage.duplicate_claims(report).items():
        keepers = xdata_name_coverage.resolve_duplicate(claimants, how_of)
        detail = ", ".join(cid for cid, _s in claimants)
        for cid, _score in claimants:
            if cid in keepers:
                continue
            for r in report:
                if r["cluster_id"] == cid and r["name"] == name:
                    r["how"] = "duplicate"
                    r["detail"] = detail
    names = {r["cluster_key"]: r["name"] for r in report
             if r["name"] and r["how"] in xdata_name_coverage.CARRIED}
    return names, report


def name_clusters(cluster_rows, old_rows, seeded):
    """Fill `cluster_name` in, and return `(carry report, name coverage)`.

    Two values rather than three, and the shape is deliberate: `carry_names()`
    keeps its 2-tuple because `xdata_guard_off_row_join.py` and three call sites
    in `test_xdata_cluster_names.py` unpack it, and widening *that* would be a
    second question. The coverage list is one record per row of the names file
    -- the transpose of the report's one record per new cluster, and the half
    that makes every hand name produce an outcome on a run where no cluster
    reaches it. See `xdata_name_coverage.py`."""
    names, report = carry_names(old_rows, seeded, cluster_rows)
    cov = xdata_name_coverage.coverage(old_rows, seeded, cluster_rows, report,
                                      CARRY_MIN_JACCARD)
    for row in cluster_rows:
        row["cluster_name"] = names.get(row["cluster_key"], "")
    return report, cov


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
            # `pair-literal` is the third value and the only one this tool
            # infers: it means the address is also reached as a literal argument
            # to one of the accessors `load_pair_accessors()` selected. On a
            # `program=both` row this cell is the **union** across the two
            # programs -- which is what `spellings_by_program`, at the far end
            # of the row, takes apart.
            "spelled_as": spellings_of(entry),
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
            # The `both` row's per-program halves, from the same per-program
            # entries the union above was absorbed out of -- not a second
            # spelling pass. The spelling was split first and the counts were
            # not; the twelve cells after this one split them, out of the same
            # entries and on the same terms. `refs`, the five buckets and the
            # two co-reading columns **stay** summed over both programs -- the
            # union is the row's own figure and moving it would move every
            # published reference figure the census quotes -- so a per-program
            # question is read from the suffixed cells and nothing else changes
            # meaning. `docs/findings/xdata-per-program-counts.md` has the
            # worked rows and the arithmetic.
            "spellings_by_program": spellings_by_program_of(groups, addr),
            **per_program_counts_of(groups, addr),
            # Which half of a pair this address is, and the last column so the
            # positional readers above are untouched. Rendered through
            # `pair_role_of()`, like both spelling cells, so the cell written
            # here and the one the self-test reads back are the same function's
            # output. A `program=both` row's is the union across the two
            # programs, the same as `spelled_as` -- and benign for the reason
            # `PAIR_BOTH_PAIR_LITERAL`'s block gives: every pair-reached
            # address is a main-EC one, so the union never merges two
            # programs' disagreeing roles.
            "pair_role": pair_role_of(entry),
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
    """First differing line named; both counts are file lines, not data rows."""
    print(f"{name} differs from a fresh generation "
          f"({len(on_disk.splitlines())} lines on disk vs "
          f"{len(generated.splitlines())} lines generated) -- run without --check "
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
    """(register_rows, cluster_rows, groups, carry report, name coverage), or
    None after printing why.

    The carry is part of the generation rather than of the writing, so `--check`
    and the default agree about what a named cluster is -- the same reason
    `outputs()` exists for the two CSVs. The name coverage is its transpose and
    rides along for the same reason: a mode that printed the report without it
    would be a mode that could still not account for every hand name."""
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
    report, cov = name_clusters(cluster_rows, load_cluster_rows(OUT_CLUSTERS),
                                load_cluster_names())
    return register_rows, cluster_rows, groups, report, cov


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


def census_shape(args) -> str:
    """The flags that put this run's cluster ids off the committed census, or
    `""` when this run *is* the committed census.

    `xdata-cluster-names.csv` is anchored to the committed pair of CSVs -- the
    `==` guard on, no `--export-ownership`, `--threshold 0.5`, exactly the run
    `--check` reproduces, so only a run whose keys are the committed ones can
    turn a carry into a re-key request. The flags that re-cluster or re-key:

        --threshold          the clustering floor itself, so the memberships
                             can differ, though not uniformly: a higher floor
                             splits the weakly-merged clusters and leaves the
                             strongly-merged ones alone. Measured on this tree
                             at 0.6: 631 clusters against the committed 439,
                             of which 361 `cluster_key`s survive unchanged
        --no-eq-guard        counts `==` as a store, so occurrences are
                             re-bucketed and the memberships differ
        --export-ownership   reads each routine from the export that owns it,
                             so the reference counts differ, and committed
                             `cluster_key`s do not survive into it

    `--no-writer-axis` is deliberately **not** among them: `build()` calls
    `components(groups[g], threshold)` with the writer axis always on, and
    `main()` refuses it outside the two modes that read it, so no write has it.

    Order is `main()`'s own declaration order; the set is derived from
    `generate()`'s AST by `test_xdata_census_shape_set.py`, not kept here.
    """
    off = []
    if args.threshold != DEFAULT_THRESHOLD:
        off.append(f"--threshold {args.threshold:g}")
    if args.no_eq_guard:
        off.append("--no-eq-guard")
    if args.export_ownership:
        off.append("--export-ownership")
    return " ".join(off)


def carry_advice(shape) -> str:
    """The clause an overlap line ends with, for a run of this shape.

    The committed census keeps the original wording verbatim, because on that
    census the line *is* the re-key request: the keys are the committed ones,
    so a name arriving by overlap is a name whose membership moved.

    Any other run is a statement about its own clustering. `--export-ownership`
    on this tree breaks 5 of the hand names outright
    (`annotations/xdata-export-ownership.md` 5), so its three `carried by
    overlap` lines are arithmetic over a different set of ids -- they are not
    three names that moved, and a reader who re-keys the file from them would be
    re-anchoring it to a census it is not anchored to. So the line says which
    flags did the re-clustering, names the file, and denies the request. The
    names are not thereby wrong or gone; this run simply cannot say whether
    they moved, and does not claim to.
    """
    names_csv = os.path.relpath(NAMES_CSV, EC_DIR)
    if not shape:
        return f" -- re-key {names_csv} if the name moved"
    return (f" -- this run's ids are not the committed census's ({shape}), and "
            f"{names_csv} is anchored to the committed one, so a carry here is "
            f"arithmetic over a different clustering, not a re-key request")


def print_carry(report, cov, shape) -> None:
    """The carry block, on stderr so the CSVs stay pipeable.

    Printed by every mode that builds a census, because a name that appears in
    `xdata-clusters.csv` without saying how it got there is the overclaim
    `CLAUDE.md` rules out: `seeded` and `exact` are the same claim, `overlap` is
    a weaker one with a score, a `tie` was not carried at all, and a `none` is
    this rule not firing rather than a cluster that went away.

    **Two halves, and the tally sums only the first.** `report` is one record
    per new *cluster*, so its counters are a count of clusters that carried a
    name -- not of names in `annotations/xdata-cluster-names.csv`, and on a run
    that re-clusters the two are different numbers. `cov` is one record per row
    of that file, so it is the half that accounts for every hand name, and
    `xdata_name_coverage.print_coverage()` prints the names this run did not
    carry. Both halves are printed because neither is the other: a name no
    cluster reached is in the second and in no cluster's line, and a cluster
    that took a wrong name is in the first.

    `cov` is required and has no default. A default a future caller forgets is
    the exact failure this signature exists to prevent -- a mode that printed
    the cluster half and silently left the names out is how the two halves
    drifted apart in the first place.

    The *advice* on an overlap line is the part that is not mode-independent,
    and the split is deliberate (issue #851). The tally, the tie line above and
    here, and every line either half prints are about this run's own arithmetic
    whatever flags produced it, so they stay as they are. Whether a carry is a
    re-key request is a question about the run: only a run whose cluster keys
    are the committed ones can answer it, so `shape` -- `census_shape(args)` --
    decides, and a run that is not the committed census says so on the line
    rather than advising a re-key it has no standing to advise."""
    tallies = collections.Counter(r["how"] for r in report)
    print("  names: " + ", ".join(
        f"{n} {tallies[h]}" for h, n in
        (("seeded", "seeded"), ("exact", "exact"), ("overlap", "carried by overlap"),
         ("tie", "tied, not carried"), ("none", "with no name")))
          + xdata_name_coverage.tally_clauses(cov, os.path.relpath(NAMES_CSV, EC_DIR)),
          file=sys.stderr)
    for r in report:
        if r["how"] in ("seeded", "exact"):
            continue
        if r["how"] == "overlap":
            print(f"    {r['cluster_id']} carries {r['name']} by overlap, "
                  f"Jaccard {r['jaccard']:.2f} from {r['from_key'] or 'an unnamed old row'}"
                  f"{carry_advice(shape)}",
                  file=sys.stderr)
        elif r["how"] == "tie":
            print(f"    {r['cluster_id']} is claimed by two names at Jaccard "
                  f"{r['jaccard']:.2f} ({r['detail']}); not carried by this method",
                  file=sys.stderr)
    xdata_name_coverage.print_coverage(cov, CARRY_MIN_JACCARD, sys.stderr)


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
    print_carry(built[3], built[4], census_shape(args))
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
    print_carry(built[3], built[4], census_shape(args))
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
        # Membership, not equality. It was equality while the two token
        # spellings were disjoint within a program, which is what the check
        # below asserts; with `pair-literal` a third value, an address reached
        # both as a token and through an accessor carries two of them and
        # `==` would silently drop it from the DAT_EXTMEM_ half of the census.
        return {a: e for a, e in groups[g].items() if spelling in e["spellings"]}

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
    # comparisons. The wide one is the corpus-wide direction invariant below.
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

    # ---- issue #279: the pair-accessor pass ----------------------------------
    #
    # Four assertions, in the order the pass could fail: the *set* it resolves
    # through, the *encoding* each member of that set really has, the *sites*
    # it resolves, and the *exclusions* it must not have moved. The first two
    # are the discriminator -- a resolver keyed on the spelling rather than on
    # the callee's `movx` would pass a site check and fail the set one -- and
    # the last is the code-pointer exclusion that relaxing the first is only
    # safe because of.
    accessors = load_pair_accessors()
    check(f"the pair-accessor set is read out of ghidra-functions.csv and the "
          f"committed .asm rather than listed here, and it is the "
          f"{len(PAIR_ACCESSORS)} routines below -- the issue's four, plus "
          f"0x8898 and 0x9193, which the same rule finds and the issue did not "
          f"name (got {len(accessors)}: {', '.join(sorted(accessors))}; "
          f"missing {', '.join(sorted(n for n, _ in PAIR_ACCESSORS if n not in accessors)) or 'none'}"
          f"{'; unexpected ' + ', '.join(sorted(set(accessors) - {n for n, _ in PAIR_ACCESSORS})) if set(accessors) - {n for n, _ in PAIR_ACCESSORS} else ''})",
          sorted(accessors.items()) == sorted(PAIR_ACCESSORS))
    # The encoding half of the discriminator, read back out of the `.asm` and
    # not out of the table: every accessor the pass resolves through must still
    # be two `movx @DPTR` an `inc DPTR` apart, and its direction must be the
    # one the annotation's own `type` claims. `load_pair_accessors()` already
    # refuses a disagreement, so reaching this line means both agree -- the
    # check is here so that "the .asm still says so" is a fact the run
    # asserts rather than an assumption the loader makes.
    annotated = {r["name"]: r for r in csv.DictReader(open(ANNOT_CSV, newline=""))}
    asm_by_program = {}
    unbacked = []
    for name, direction in sorted(accessors.items()):
        row = annotated[name]
        scope = row["scope"]
        if scope not in asm_by_program:
            asm_by_program[scope] = read_asm(scope)
        listing = asm_by_program[scope].get(row["addr"], ())
        movx = [o for _, m, o in listing if m == "movx"]
        got = pair_accessor(listing)
        if got != direction or len(movx) != 2:
            unbacked.append(f"{scope}:0x{row['addr']}={name} ({got})")
    check(f"and every one of them has two `movx` in its committed .asm, the "
          f"instruction that names the external space -- so a literal handed to "
          f"one of them is XDATA whatever the decompiler called the spelling, "
          f"and `FUN_CODE_0402` is a data address rather than a code pointer "
          f"(not backed: {', '.join(unbacked) or 'none'})",
          not unbacked)
    # The resolved set itself, by file and direction, for the two addresses the
    # issue works through. This is the assertion the issue asks for "so this
    # cannot regress the way the last classifier drift did": a per-address
    # multiset fails on *which* site moved, where a bucket total does not.
    resolved = collections.defaultdict(list)
    token_re = occurrence_re(symbols)
    for out_file in sorted(by_file):
        text = strip_comments(open(os.path.join(DECOMPILED, out_file)).read())
        for addr, direction in pair_sites(text, accessors, token_re):
            resolved[addr].append((out_file, direction))
    for addr, expected in sorted(PAIR_RESOLVED.items()):
        got = tuple(sorted(resolved[addr]))
        check(f"the {hexaddr(addr)} worked example: {len(expected)} resolved "
              f"sites, {sum(1 for _, d in expected if d == 'read')} read / "
              f"{sum(1 for _, d in expected if d == 'write')} write, at "
              f"{', '.join(f for f, _ in expected)} (got {len(got)}: "
              f"{', '.join(f'{f} {d}' for f, d in got) or 'none'})",
              got == tuple(sorted(expected)))
    # The double-count trap, asserted on the *outcome*. `bank1/9354.c:19`
    # hands `DAT_EXTMEM_0318` to the same accessor and `occurrence_re` already
    # counts that argument, so resolving it here as well would give `0x0318` a
    # read it has no site for and `0x0319` a reference with no site behind it.
    # `PAIR_LITERAL` rejects it before the `fullmatch` gate is reached (see
    # `pair_sites()`), so this pins the fact rather than the mechanism, and it
    # is the fact that a widened literal gate would break.
    _a, _f1, _f2 = PAIR_ALREADY_COUNTED
    _ea = groups["main-ec"].get(_a)
    check(f"and {os.path.basename(_f1)}/{_f2} are the only files that reach "
          f"{hexaddr(_a)} through an accessor -- `bank1/9354.c:19` passes "
          f"`DAT_EXTMEM_{_a:04x}` to the same routine, which the token pass "
          f"already counts, so resolving it again would give "
          f"{hexaddr(_a)} a phantom read (got "
          f"{', '.join(f for f, _ in resolved[_a]) or 'none'})",
          tuple(sorted(f for f, _ in resolved[_a])) == tuple(sorted((_f1, _f2))))
    check(f"and the two spellings of {hexaddr(_a)} stay separable on the row "
          f"itself: {(_ea['spelled_refs']['DAT_EXTMEM'] if _ea else '?')} "
          f"references spelled `DAT_EXTMEM_` against "
          f"{(_ea['spelled_refs'][PAIR_SPELLING] if _ea else '?')} resolved "
          f"through an accessor, out of "
          f"{(_ea['refs'] if _ea else '?')} in all -- which is the shape a "
          f"double-counted row would not have",
          _ea is not None
          and _ea["spelled_refs"]["DAT_EXTMEM"] == 14
          and _ea["spelled_refs"][PAIR_SPELLING] == 2
          and _ea["refs"] == 16)
    # What the pass must NOT have done: reached a code pointer. `0x0733` is a
    # real one, inside bank0:0x94D0, and the relaxation above is safe only
    # because the gate is the callee's `movx` rather than the spelling -- so
    # this is asserted after the pass has run, not before it. The
    # `code_only == {0x0733}` check further down is the same claim from the
    # other side; this one is here because it is the invariant the relaxation
    # could have broken.
    check("and no `FUN_CODE_`/`DAT_CODE_` literal is resolved through anything "
          "but a selected accessor, so the code-spelled set the census does "
          "not read is still exactly BLIND_SPOT's findable half",
          0x0733 not in resolved and 0x0735 not in resolved)

    def tally(g, spelling=None):
        # `spelling` asked for means *references spelled that way*, not
        # references to addresses that carry the spelling somewhere. The two
        # were the same number until `pair-literal` joined the vocabulary, and
        # 59 addresses are now reached both ways.
        if spelling is None:
            sub = groups[g]
            return len(sub), sum(e["refs"] for e in sub.values())
        sub = of(g, spelling)
        return len(sub), sum(e["spelled_refs"][spelling] for e in sub.values())

    distinct = {g: tally(g) for g in GROUPS}
    refs = {g: distinct[g][1] for g in GROUPS}
    both = {a for a in groups["main-ec"] if a in groups["pd"]}
    pd_only = set(groups["pd"]) - both
    total_distinct = len(set(groups["main-ec"]) | set(groups["pd"]))
    total_refs = refs["main-ec"] + refs["pd"]
    extmem = {g: tally(g, "DAT_EXTMEM") for g in GROUPS}
    syms = {g: tally(g, "symbol") for g in GROUPS}

    # No figure of the census is asserted here: every one of them moves when a
    # routine is seeded or a register named, which is the work this census
    # exists to measure. What holds whatever the tree's size is asserted
    # instead, and the committed CSVs, which `--check` regenerates, are where a
    # move shows up as a reviewable diff. CLAUDE.md, "No totals of the
    # repository's own text".
    check(f"every DAT_EXTMEM_ token the census counts is one of the file-wide "
          f"occurrences, and the rest are the repository's own annotation text "
          f"quoting the decompile (raw: {dict(raw)}; counted: "
          f"{extmem['main-ec'][1] + extmem['pd'][1]})",
          raw["DAT_EXTMEM"] >= extmem["main-ec"][1] + extmem["pd"][1])
    check(f"the PD image has no address spelled by symbol (got {syms['pd']})",
          syms["pd"] == (0, 0))
    # Within a program the two *token* spellings are disjoint: the exporter
    # applied its symbol table to the EC programs and not to the PD image
    # (gen_xdata_symbols refuses to name PD), so no address there is both.
    # Across programs they differ -- 0x07D8 is
    # `MODE_TCC_OFFSET_DEFAULTS_GAMING_0` in the EC and `DAT_EXTMEM_07d8` in the
    # PD image -- which is why `spelled_as` can carry both.
    #
    # **The assertion is about the two token spellings, not about the width of
    # the set.** It read `len(e["spellings"]) == 1` while there were only two
    # and they were disjoint, which is the same claim written a cheaper way;
    # `pair-literal` is a third value and 59 addresses now carry it alongside a
    # token spelling, so the width is no longer one and the *exclusivity* is
    # what still has to hold. `spelled_as` reads all of them out, so a version
    # of this that kept the old test would have failed on the very rows the
    # issue is about.
    check("within each program the two token spellings are disjoint address for "
          "address, so a named address is never also a DAT_EXTMEM_ token "
          f"(both at once: {', '.join(hexaddr(a) for g in GROUPS for a, e in groups[g].items() if {'symbol', 'DAT_EXTMEM'} <= e['spellings']) or 'none'})",
          all(not ({"symbol", "DAT_EXTMEM"} <= e["spellings"])
              for g in GROUPS for e in groups[g].values()))
    check("the PD image is spelled entirely in DAT_EXTMEM_ tokens, which is "
          "gen_xdata_symbols.py's own refusal to name it",
          all(e["spellings"] <= {"DAT_EXTMEM", PAIR_SPELLING}
              for e in groups["pd"].values()))
    # The third spelling's own presence, because a resolver that silently
    # stopped resolving would move the census back the other way and nothing
    # about the two token spellings would notice. The worked examples below
    # (`PAIR_RESOLVED`) say which sites; this says the pass still runs.
    pair_rows = {a: e for g in GROUPS for a, e in groups[g].items()
                 if PAIR_SPELLING in e["spellings"]}
    pair_mixed = sorted(a for a, e in pair_rows.items() if len(e["spellings"]) > 1)
    check(f"the pair-accessor pass reached {len(pair_rows)} addresses, "
          f"{len(pair_mixed)} of them also spelled a token -- and every one of "
          f"them is in the main EC, because pd's own `read_be16_from_dptr` is "
          f"called once with no argument (elsewhere: "
          f"{', '.join(hexaddr(a) for g in GROUPS for a, e in groups[g].items() if PAIR_SPELLING in e['spellings'] and g != 'main-ec') or 'none'})",
          pair_rows and pair_mixed
          and all(PAIR_SPELLING in groups["main-ec"][a]["spellings"]
                  for a in pair_rows))
    # ---- issue #709: the per-program column, and what it reconciles ---------
    #
    # Three assertions, in the order they can fail: the column's own contract
    # on every row, the four rows the union is load-bearing for, and the
    # reconciliation between this file's per-program pins and the CSV's own
    # union split. All three read the **committed** registers CSV rather than a
    # fresh generation -- the whole of the issue is that the artifact a reader
    # opens cannot answer the question, so a check that ran against what this
    # run would write would not be answering it.
    committed_registers = load_cluster_rows(OUT_REGISTERS)
    csv_rows = {r["addr"]: r for r in committed_registers}
    union_wrong = [r["addr"] for r in committed_registers
                   if {s for half in spellings_by_program(r).values()
                        for s in half} != set(r["spelled_as"].split("+"))]
    # Capped, and the overflow counted in the message rather than dropped: a
    # silent cap reads as "covered" when it is not, which is the same objection
    # TOP_CALLEES' cap is answered with.
    shown = ", ".join(union_wrong[:8]) or "none"
    if len(union_wrong) > 8:
        shown += f" (and {len(union_wrong) - 8} more)"
    check(f"issue #709: on all {len(committed_registers)} rows of "
          f"{os.path.relpath(OUT_REGISTERS, EC_DIR)} the spelling tokens in "
          f"`spellings_by_program` are exactly the ones in `spelled_as` -- the "
          f"new column partitions the union rather than adding to it (rows "
          f"where the two differ: {shown})",
          not union_wrong and len(committed_registers) == total_distinct)
    halves_wrong = []
    for a, (main, pd) in sorted(PAIR_BOTH_PAIR_LITERAL.items()):
        row = csv_rows.get(hexaddr(a))
        halves = spellings_by_program(row) if row else {}
        if (row is None or halves.get("main-ec") != main
                or halves.get("pd") != pd
                or int(row["refs"]) != ((groups["main-ec"].get(a) or {}).get("refs", 0)
                                        + (groups["pd"].get(a) or {}).get("refs", 0))):
            halves_wrong.append(hexaddr(a))
    four = ", ".join(hexaddr(a) for a in PAIR_BOTH_PAIR_LITERAL)
    check(f"and the four `both` rows whose union carries `pair-literal` say "
          f"which program spelled what: {four} -- 0x04A3 is "
          f"`pair-literal` in the main EC and `DAT_EXTMEM` in the PD image, "
          f"the other three carry both spellings in the main EC and "
          f"`DAT_EXTMEM` alone in the PD image, and each row's single `refs` "
          f"cell is still the sum of its two halves, because the column splits "
          f"the spelling and not the reference count (rows that disagree: "
          f"{', '.join(halves_wrong) or 'none'})",
          not halves_wrong)
    # The reconciliation itself, as a set relation rather than two equal counts:
    # a second cross-program row would keep the arithmetic true and quietly move
    # a published figure, so what is asserted is that the two mixed sets differ
    # by exactly PAIR_UNION_ONLY in both directions.
    csv_mixed = {int(r["addr"], 0) for r in committed_registers
                 if PAIR_SPELLING in r["spelled_as"] and "+" in r["spelled_as"]}
    csv_pair_only = {int(r["addr"], 0) for r in committed_registers
                     if r["spelled_as"] == PAIR_SPELLING}
    per_pair_only = set(pair_rows) - set(pair_mixed)
    only_per_program = sorted(set(pair_mixed) ^ csv_mixed)
    only_per_program_shown = ", ".join(hexaddr(a) for a in only_per_program) \
        or "identical"
    check(f"and the mixed / pair-only split within a program and the CSV's union "
          f"split are the same addresses differing by exactly "
          f"{', '.join(hexaddr(a) for a in PAIR_UNION_ONLY) or 'nothing'} -- "
          f"the one row the main EC spells `pair-literal` and the PD image "
          f"spells `DAT_EXTMEM`, so the union reads it as mixed (the "
          f"per-program mixed set against the CSV's: {only_per_program_shown})",
          set(pair_mixed) ^ csv_mixed == set(PAIR_UNION_ONLY)
          and per_pair_only ^ csv_pair_only == set(PAIR_UNION_ONLY)
          and set(pair_rows) == csv_mixed | csv_pair_only)
    # ---- issue #713: the twelve per-program count columns ------------------
    #
    # Four assertions, in the order they can fail: what the columns claim on
    # their own, where they sit; what they claim against a **fresh
    # generation**; the arithmetic that says the split partitions this census
    # rather than re-counting it; and the four `pair-literal` rows the union is
    # load-bearing for. Three of the four read the **committed** registers CSV
    # rather than a fresh one -- the whole of the issue is that the artifact a
    # reader opens could not answer the question, so a check against what this
    # run would write would not be answering it. The second is the deliberate
    # exception: a file and a tool wrong *together* is a failure only something
    # outside both can catch, which is why it compares the committed cells to
    # `groups` rather than to a rendered row.
    #
    # #711's three assertions above are untouched. A new column is not a
    # licence to weaken what the old one is held to, and the one thing a reader
    # of that block is entitled to assume is that `refs` on a `both` row is
    # still the sum -- which is what the first assertion below holds.
    columns = per_program_columns()
    split_bad = []
    for r in committed_registers:
        cells = {c: per_program_cell(r, c) for c in columns}
        for metric in PER_PROGRAM_METRICS:
            halves = sum(cells[f"{metric}{program_suffix(g)}"] for g in GROUPS)
            if per_program_cell(r, metric) != halves:
                split_bad.append(f"{r['addr']}:{metric}")
        # The `program` column's own contract, and it is a two-way one: a
        # single-program row must carry nothing at all for the program it is
        # not, and a `both` row must carry something in both. The second half
        # is a real assertion rather than a tautology -- an address in
        # `groups[g]` has at least one reference there by construction, so a
        # `both` row with a zero half means the file and the tool disagree
        # about which programs touch the address number at all, which is the
        # `program=both` collision the column exists to make checkable.
        #
        # The two branches are exclusive and the `both` one is checked first,
        # because `"both"` is not a `GROUPS` key: a loop that skipped on
        # `g == row["program"]` would never skip on a `both` row and would
        # then read "every cell is non-zero" as "every cell is zero".
        if r["program"] == "both":
            if any(cells[f"refs{program_suffix(g)}"] <= 0 for g in GROUPS):
                split_bad.append(f"{r['addr']}:both/zero-half")
        else:
            for g in GROUPS:
                if g == r["program"]:
                    continue
                for metric in PER_PROGRAM_METRICS:
                    if cells[f"{metric}{program_suffix(g)}"] != 0:
                        split_bad.append(
                            f"{r['addr']}:{r['program']}"
                            f"/{metric}{program_suffix(g)}")
    split_shown = ", ".join(split_bad[:8]) or "none"
    if len(split_bad) > 8:
        split_shown += f" (and {len(split_bad) - 8} more)"
    check(f"issue #713: the {len(columns)} per-program columns sit at "
          f"{REGISTER_COLUMNS.index(columns[0]) + 1}-"
          f"{REGISTER_COLUMNS.index(columns[-1]) + 1} with "
          f"`{REGISTER_COLUMNS[20]}` still at "
          f"{REGISTER_COLUMNS.index(REGISTER_COLUMNS[20]) + 1}, and on all "
          f"{len(committed_registers)} rows of "
          f"{os.path.relpath(OUT_REGISTERS, EC_DIR)} each of the six "
          f"unsuffixed counts is the sum of its two halves -- `refs == "
          f"refs_main_ec + refs_pd` and the same for all five buckets -- "
          f"while a `main-ec` row carries nothing for `pd`, a `pd` row nothing "
          f"for `main-ec`, and a `both` row carries both (rows that disagree: "
          f"{split_shown})",
          not split_bad and len(committed_registers) == total_distinct
          and REGISTER_COLUMNS[20] == "spellings_by_program"
          # Narrowed from `[21:]` when `pair_role` was appended: the claim is
          # "the per-program columns occupy a contiguous run starting at 22",
          # and a run to the end of the list would assert that too -- which
          # stops being true the moment anything is appended after them, and
          # would have failed #713's own assertion for a column that has
          # nothing to do with #713. Sliced on the columns' own length rather
          # than a typed end index so the assertion keeps saying what it says
          # if a fourteenth per-program metric is ever added.
          and REGISTER_COLUMNS[21:21 + len(columns)] == list(columns))
    # The cross-check that makes the file's own columns mean something. A
    # column written wrongly in *both* `build()` and the CSV is internally
    # consistent and the assertion above would pass it; this one compares the
    # committed cells to the per-program entries they were supposed to be
    # rendered from, and an address in no program of `groups` expects a zero
    # rather than being skipped -- a row the file has and the tree does not is
    # a failure, not an absence.
    attributed_bad = []
    for r in committed_registers:
        addr = int(r["addr"], 0)
        for g in GROUPS:
            half = groups[g].get(addr)
            for metric in PER_PROGRAM_METRICS:
                want = 0 if half is None else (
                    half["refs"] if metric == "refs"
                    else half["buckets"].get(metric, 0))
                if per_program_cell(r, f"{metric}{program_suffix(g)}") != want:
                    attributed_bad.append(f"{r['addr']}/{g}/{metric}")
    attributed_shown = ", ".join(attributed_bad[:8]) or "none"
    if len(attributed_bad) > 8:
        attributed_shown += f" (and {len(attributed_bad) - 8} more)"
    check(f"and every one of those cells is the per-program entry it claims "
          f"to be, read against a fresh generation of the census rather than "
          f"against a rendered row -- {len(groups['main-ec'])} main-EC and "
          f"{len(groups['pd'])} pd program-addresses, so a `both` row's halves "
          f"come out of two different entries and a single-program row's other "
          f"half comes out of nothing at all (cells that disagree: "
          f"{attributed_shown})",
          not attributed_bad)
    # The reconciliation, which is what says the split *partitions* this census:
    # each column sums to its own program's measured references, and the `both`
    # rows' halves sum to what the rows' own `refs` cells carry. A column that
    # moved a reference between programs would keep `refs == refs_main_ec +
    # refs_pd` true on every row and fail here.
    both_rows = [r for r in committed_registers if r["program"] == "both"]
    col = {g: sum(per_program_cell(r, f"refs{program_suffix(g)}")
                  for r in committed_registers) for g in GROUPS}
    both_col = {g: sum(per_program_cell(r, f"refs{program_suffix(g)}")
                       for r in both_rows) for g in GROUPS}
    both_summed = sum(per_program_cell(r, "refs") for r in both_rows)
    check(f"and the split partitions the census rather than re-counting it: "
          f"the two columns sum to each program's own references over all "
          f"{len(committed_registers)} rows (got {col['main-ec']} + {col['pd']} "
          f"against {refs['main-ec']} + {refs['pd']}), and the "
          f"{len(both_rows)} `both` rows' halves sum to what their own `refs` "
          f"cells carry (got {both_col['main-ec']} + {both_col['pd']} against "
          f"{both_summed})",
          col["main-ec"] == refs["main-ec"]
          and col["pd"] == refs["pd"]
          and len(both_rows) == len(both)
          and both_col["main-ec"] + both_col["pd"] == both_summed)
    # ---- issue #734: `pair_role`, which half of a pair a row is ------------
    #
    # Five assertions, in the order they can fail: where the column sits, what
    # it says on every row of the committed CSV, that a cell can only be the
    # vocabulary rendered in the declared order, that the two roles *partition*
    # what `scan()`'s pair loop reaches, and the one row where the `both` union
    # is doing real work. All read the **committed** registers CSV for the same
    # reason the two blocks above do -- the claim is about the artifact a
    # reader opens, not about what this run would write.
    #
    # **No size is typed.** The population the pair loop reaches is measured
    # here rather than asserted at a figure; the numbers that are findings live
    # in the write-up, beside the command that prints them.
    role_seed = {int(r["addr"], 0) for r in committed_registers
                 if PAIR_SEED in r["pair_role"].split("+")}
    role_inc = {int(r["addr"], 0) for r in committed_registers
                if PAIR_INC in r["pair_role"].split("+")}
    role_any = {int(r["addr"], 0) for r in committed_registers if r["pair_role"]}
    pair_literal = {int(r["addr"], 0) for r in committed_registers
                    if PAIR_SPELLING in r["spelled_as"].split("+")}
    role_at = REGISTER_COLUMNS.index("pair_role")
    check(f"issue #734: `pair_role` is the last column, at {role_at + 1} and "
          f"immediately after the {len(columns)} per-program columns -- "
          f"appended rather than placed beside `spelled_as`, so the positional "
          f"`awk -F,` readers `REGISTER_COLUMNS` documents keep every field "
          f"they have today",
          REGISTER_COLUMNS[-1] == "pair_role"
          and REGISTER_COLUMNS[role_at - 1] == columns[-1])
    # The column's own contract, over every row and not only the pair-reached
    # ones: an empty cell is the answer "no pair call reaches this address",
    # so emptiness has to be the whole answer and not an omission. Split on
    # `+` rather than substring-matching, so a row carrying both roles is not
    # read as carrying a role when the test is about the spelling.
    role_wrong = [r["addr"] for r in committed_registers
                  if bool(r["pair_role"]) != (PAIR_SPELLING in r["spelled_as"])]
    role_shown = ", ".join(role_wrong[:8]) or "none"
    if len(role_wrong) > 8:
        role_shown += f" (and {len(role_wrong) - 8} more)"
    check(f"and on all {len(committed_registers)} rows of "
          f"{os.path.relpath(OUT_REGISTERS, EC_DIR)} the cell is non-empty "
          f"exactly when `spelled_as` carries `pair-literal` -- the column "
          f"takes one value apart rather than adding a new one, so a writer "
          f"that labelled an address no pair call reaches fails here as loudly "
          f"as one that failed to label one it does (rows that disagree: "
          f"{role_shown})",
          not role_wrong and role_any == pair_literal)
    # A cell is legal only if re-rendering it from the declared order gives it
    # back. That is one test carrying four properties -- the vocabulary, the
    # order, no repeated role, and no comma -- and it is derived from
    # `PAIR_ROLE_ORDER` rather than spelled out, so a third role widens the
    # vocabulary here instead of failing this line. The comma is the one that
    # matters mechanically: it would shift every field after it for the
    # positional readers `REGISTER_COLUMNS` documents.
    def ordered_roles(cell) -> bool:
        return bool("+".join(r for r in PAIR_ROLE_ORDER if r in cell.split("+"))
                    == cell) if cell else False
    check(f"and every non-empty cell is the vocabulary in "
          f"`{', '.join(PAIR_ROLE_ORDER)}` order, once each and joined with "
          f"`+` -- nothing else can appear in it, so a comma cannot reach the "
          f"column and shift the positional readers",
          all(ordered_roles(r["pair_role"]) for r in committed_registers
              if r["pair_role"]))
    # The partition, and the disjointness `inc_dptr_sites.py` measures on its
    # own. The two halves are disjoint by no construction -- `a` can be a seed
    # in one call and another call's `+1` -- so this is the assertion that
    # says so rather than the writer's assumption, and the sizes close on the
    # population this file already pins. An overlap is named, not summarised,
    # for the reason the failure would otherwise be unfindable.
    overlap = sorted(role_seed & role_inc)
    overlap_shown = ", ".join(hexaddr(a) for a in overlap[:8]) or "none"
    if len(overlap) > 8:
        overlap_shown += f" (and {len(overlap) - 8} more)"
    check(f"and the two roles partition what the pair pass reaches: "
          f"{len(role_seed)} rows read `{PAIR_SEED}` and {len(role_inc)} read "
          f"`{PAIR_INC}`, the two sets share {len(overlap)} address(es) "
          f"({overlap_shown}), and together they are exactly the {len(role_any)} "
          f"rows carrying a cell -- which are the addresses `scan()`'s pair "
          f"pass reaches, whether or not the column agrees",
          not overlap and role_seed | role_inc == role_any
          and role_any == set(pair_rows))
    # `0x04A3` is the row where the union is not decorative: `spelled_as` reads
    # it `DAT_EXTMEM+pair-literal` because the two programs spell it
    # differently, and `PAIR_BOTH_PAIR_LITERAL` above is what establishes that
    # its `pair-literal` is the main EC's. Its role is pinned by value because
    # it is the one row where a reader could reasonably wonder which program's
    # half the union is talking about.
    check(f"and {', '.join(hexaddr(a) for a in PAIR_UNION_ONLY)} -- the one "
          f"row the CSV's union reads as mixed where the main EC alone spells "
          f"it `{PAIR_SPELLING}` -- reads `{PAIR_INC}`, being the `+1` of a "
          f"seed, so the role stays unambiguous on a row whose `spelled_as` is "
          f"a union across both programs",
          all(csv_rows.get(hexaddr(a), {}).get("pair_role") == PAIR_INC
              for a in PAIR_UNION_ONLY))
    check("main + PD equals the file-wide total on both axes",
          distinct["main-ec"][0] + len(pd_only) == total_distinct and
          refs["main-ec"] + refs["pd"] == total_refs)

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
    check(f"of the {len(symbols)} named addresses, all but the "
          f"{len(NOT_IN_TREE)} in NOT_IN_TREE appear in the decompiled tree "
          f"(got {len(named)}: {', '.join(hexaddr(a) for a in named)})",
          len(named) == len(symbols) - len(NOT_IN_TREE))
    # Issue #280. Both directions, so neither a missed address nor a stale
    # entry passes, and the diff is printed address by address either way.
    only_blocked = sorted(set(NOT_IN_TREE) - not_in_tree)
    only_found = sorted(not_in_tree - set(NOT_IN_TREE))
    check(f"issue #280: the {len(NOT_IN_TREE)} addresses xdata-symbols.csv names "
          f"and the census does not reach are the NOT_IN_TREE set, address for "
          f"address, so the {len(named)} named addresses in the tree are "
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
    carry, cov = name_clusters(cluster_rows, old_rows, load_cluster_names())
    # The per-address hand oracles that stood here (`HAND_CHECKED` for the
    # direction buckets, `COREADING_CHECKED` for the co-reading columns) held
    # reference counts, and a count of an address moves whenever a routine
    # that touches it is seeded. The direction rule is held by
    # `CLASSIFIER_SHAPE`'s literal snippets above and by the corpus-wide
    # invariant below, neither of which a new routine can move.
    check("and on every register row the two columns are a partition of the "
          "address's source functions: co_reading + sources_beyond == "
          "functions_touched, which is what keeps the new columns a *count* of "
          "files rather than a second reference count (rows where it does not "
          "balance: "
          f"{', '.join(r['addr'] for r in register_rows if int(r['co_reading']) + int(r['sources_beyond']) != int(r['functions_touched'])) or 'none'})",
          all(int(r["co_reading"]) + int(r["sources_beyond"])
              == int(r["functions_touched"]) for r in register_rows))
    check("and neither column moved a counting column: the rows' `refs` sum "
          "to the census total, with the co-reading columns reading off the "
          "same rows",
          sum(int(r["refs"]) for r in register_rows) == total_refs and
          all(int(r["co_reading"]) <= int(r["functions_touched"])
              for r in register_rows))
    # The groups themselves are printed rather than pinned: `--co-reading-sweep`
    # prints the curve that makes COREADING_MIN_CORE a recorded choice.
    _go, co_groups = co_reading_groups(census, funcs, COREADING_MIN_CORE)
    co_sizes = sorted((len(g["files"]) for g in co_groups), reverse=True)
    check(f"the co-reading relation at floor {COREADING_MIN_CORE} -- a common "
          f"core of that many addresses between two files in one program -- "
          f"finds groups at all (got {len(co_sizes)} over {sum(co_sizes)} "
          f"files; sizes {co_sizes})",
          bool(co_sizes))
    # The program split, asserted as a property of the answer rather than of the
    # code that computes it: the two images have separate XDATA maps, and a
    # group spanning both would be a co-reading manufactured out of a shared
    # address *number*.
    spanning = [g["files"] for g in co_groups
                if len({f.split("/")[0] for f in g["files"]}) > 1]
    check(f"and no co-reading group spans two programs, which is the same split "
          f"the clustering never crosses (spanning groups: "
          f"{', '.join(' '.join(g) for g in spanning) or 'none'})",
          not spanning)
    # The counter sweep of xdata-06c2-06db-timers.md §2 is the largest group,
    # one group from its first listing to its last. A sweep split across two
    # groups would be a different claim from one group.
    big = max(co_groups, key=lambda g: len(g["files"]))
    check(f"and the counter sweep of xdata-06c2-06db-timers.md §2 is the "
          f"largest group, one group from {COREADING_SWEEP[0]} to "
          f"{COREADING_SWEEP[1]} rather than several (got "
          f"{len(big['files'])} files, {big['files'][0]} to {big['files'][-1]}, "
          f"core {len(big['core'])})",
          (big["files"][0], big["files"][-1]) == COREADING_SWEEP)
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
          sweep_cluster["co_reading_dominant"] == "yes")
    # Issue #280: the same question, asked of the whole tree instead of five
    # addresses. `direction_invariant()` is a second code path over the same
    # text, not a re-implementation of store_target() -- assign_after() is a
    # primitive that never consults the rule under test -- so this fails on a
    # classifier that sums correctly while getting the direction wrong, which
    # is exactly what the oracle above cannot be widened into on its own.
    shaped, census_side, offenders, surplus, eq_after, eq_in_write = (
        direction_invariant(by_file, symbols, func_names))
    # The population the invariant is about, measured by the pass that checks
    # it rather than written down beside it. `expected` is the census's own
    # arithmetic and `got` is this walk's, so the line states a population it
    # compared rather than one it merely repeated.
    census_write_like = sum(e["buckets"]["write"] + e["buckets"]["read+write"]
                            for g in GROUPS for e in groups[g].values())
    check("the corpus-wide direction invariant: every occurrence that "
          "the census buckets `write` or `read+write` has an assignment -- not "
          "`==` -- after the address, measured by a second pass that does not "
          "re-implement the classifier, over the population that pass measured "
          f"itself ({census_side['write_like']} occurrences across "
          f"{len(census_side['write_like_addrs'])} distinct addresses)"
          + (f"; offenders, as `file!line address`: "
             f"{', '.join(offenders)}" if offenders else ""),
          not offenders)
    # The identity that makes those two figures a cross-path agreement rather
    # than the census's own arithmetic restated by the walk measuring it. The
    # census counts a resolved pair site in a direction bucket without an `=`
    # for the second pass to find, so the two sides balance only once that
    # half is added back; `spelled_refs[PAIR_SPELLING]` is direction-blind, so
    # the by-direction count comes from the sweep above rather than a column.
    pair_write = census_side["pair_refs"]["write"]
    check("and the two passes account for the same write-like population: the "
          "occurrences this walk measured plus the write-direction half of the "
          "pair references it does not visit are the census's own `write` and "
          f"`read+write` occurrences (expected {census_write_like}, got "
          f"{census_side['write_like'] + pair_write})",
          census_side["write_like"] + pair_write == census_write_like)
    # The width is the other half of the population, and the two candidate
    # counts are *not* the same set: `shaped` holds every address the second
    # pass accepts an assignment on, while the write-like set holds every
    # address the census buckets a store on. Asserting the difference is
    # exactly the `*`-dereference addresses is what stops a re-deriver from
    # reaching for `len(shaped)` and reading the width one too high, and it
    # names the site rather than leaving the gap to be divided by hand.
    shaped_only = set(shaped) - census_side["write_like_addrs"]
    deref_only = census_side["deref_addrs"] - census_side["write_like_addrs"]
    check(f"and the two address counts differ by exactly the `*`-dereference "
          f"stores a necessary condition does not have to exclude -- the "
          f"write-like set is {len(census_side['write_like_addrs'])} where "
          f"`len(shaped)` is {len(shaped)}, the difference being "
          f"{', '.join(hexaddr(a) for a in sorted(shaped_only)) or 'none'}",
          shaped_only == deref_only)
    # The per-address form of the same necessary condition, so a failure here
    # says which address stopped balancing rather than only which occurrence.
    #
    # **Issue #279: the `write` side is taken over occurrences only, and the
    # subtraction is wider than "the pair writes".** `direction_invariant()`
    # walks the decompiled text with `occurrence_re`, and its hypothesis is "a
    # `write` is followed by an assignment". A resolved pair site is a `write`
    # bucket entry that deliberately does *not* satisfy that hypothesis: its
    # direction is read out of a callee's committed `.asm`, six bytes away in
    # another routine, and the caller's own expression carries no `=` to be
    # followed. Counting them on both sides would have widened the invariant to
    # cover evidence it never examines; counting them on neither would have let
    # a real misclassification hide behind them. So the pair sites are
    # subtracted from the census side.
    #
    # **What is subtracted is every pair-resolved _reference_, read-direction
    # included, while the sum it is subtracted from only ever holds writes.** A
    # site touches two bytes and the pass resolves 241 read and 196 write sites,
    # so `spelled_refs[PAIR_SPELLING]` is 874 and the left side below is
    # occurrence-writes minus pair *reads* as well as minus pair writes. The
    # slack is one-directional and stated rather than assumed: it can only push
    # an address down, so it makes this check more permissive, never less, and
    # an over-count still has to clear the read-direction references before it
    # is flagged. **Subtracting only the write-direction half was measured, not
    # assumed: on this tree it flags the same `none`**, so the width is not what
    # carries the assertion. It is kept anyway because the narrow form needs a
    # per-address count of pair sites *by direction*, which no census column
    # carries -- deriving one here would make the check depend on a second walk
    # of the tree that the oracle above does not make.
    over = [hexaddr(a) for a in everywhere
            if sum(groups[g][a]["buckets"]["write"]
                   + groups[g][a]["buckets"]["read+write"]
                   - groups[g][a]["spelled_refs"][PAIR_SPELLING]
                   for g in GROUPS if a in groups[g]) > shaped.get(a, 0)]
    check(f"and no single address is counted as more stores than the second "
          f"pass accepts, so the agreement is per address and not only in "
          f"aggregate -- over the occurrences, with the "
          f"{sum(e['spelled_refs'][PAIR_SPELLING] for g in GROUPS for e in groups[g].values())} "
          f"pair-resolved references subtracted rather than the write-direction "
          f"half of them, since a resolved site's direction is the callee's and "
          f"not a following `=`; the left side is therefore occurrence-writes "
          f"*minus pair reads* as well, which can only make this check more "
          f"permissive (over-counted: {', '.join(over) or 'none'})",
          not over)
    # The exemption rule, stated as a measurement rather than as a tolerance.
    # `assign_after()` drops the `*` test that `store_target()` applies, so it
    # accepts strictly more; every extra is a dereference store, and the two
    # below are the whole of the difference. A new shape arriving here is a
    # named site, not a quietly widened exemption count.
    check(f"the only occurrences the second pass accepts and the census does "
          f"not are `*`-dereference stores, the one exclusion a necessary "
          f"condition does not need (anything else: {', '.join(surplus) or 'none'})",
          not surplus)
    # The mirror direction on the same pass.
    check(f"and none of the {eq_after} `==` occurrences in the tree is bucketed "
          f"as a store (in a write bucket: {eq_in_write or 'none'})",
          eq_in_write == 0 and eq_after > 0)
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
    own_distinct = len(set(groups_own["main-ec"]) | set(groups_own["pd"]))
    own_refs = (sum(e["refs"] for e in groups_own["main-ec"].values())
                + sum(e["refs"] for e in groups_own["pd"].values()))
    # The pass collapses duplicate exports of one body, so it can only remove
    # references, and it must never remove an address: an owner is a superset
    # of its non-owners. Both are asserted rather than the census's figures,
    # which move with every seeded routine.
    lost = {hexaddr(a) for a in set(groups["main-ec"]) | set(groups["pd"])} - \
        {hexaddr(a) for a in set(groups_own["main-ec"]) | set(groups_own["pd"])}
    check(f"the export-ownership census reads {own_distinct} distinct / "
          f"{own_refs} references against the default's {total_distinct} / "
          f"{total_refs}: it loses no address, which is the one thing it must "
          f"never do, and adds no reference (lost: "
          f"{', '.join(sorted(lost)) or 'none'}; if this ever names an "
          f"address, an owner was not a superset of its non-owners)",
          not lost and own_distinct == total_distinct and own_refs <= total_refs)
    # The 42 copies, counted from the map rather than from a hand list, because
    # the width is the claim: one routine exported 42 ways is what the whole
    # switch exists to stop being read 42 times.
    copies = [f for f, r in own_map.items()
              if r["owner_out_file"] == "bank1/8001.c" and f != "bank1/8001.c"]
    check(f"the bank1:0x8001 run is {len(copies) + 1} exports of one body, so "
          f"the default census reads 0x0843 "
          f"{groups['main-ec'][0x0843]['refs']} times against "
          f"{groups_own['main-ec'][0x0843]['refs']} with the pass on, all of "
          f"them in the one owner",
          len(copies) + 1 == export_ownership.OWNERSHIP_ORACLE["largest_class"]
          and groups_own["main-ec"][0x0843]["refs"]
          < groups["main-ec"][0x0843]["refs"]
          and len(groups_own["main-ec"][0x0843]["funcs"]) == 1)
    # The default must be untouched: the pass is a flag, and the committed
    # CSVs are the default census. The last check below compares them.
    check("and the default census is the one this run measured, not the "
          "ownership pass",
          not args.export_ownership)
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
          all(r["how"] in ("seeded", "exact", "overlap", "tie", "none",
                           "duplicate")
              for r in carry))
    # The name-indexed half, and the check the cluster-indexed one above cannot
    # make. That one reads `old_names` off the *committed* census, so it is
    # green precisely where nothing is lost: a name the committed census does
    # not carry is not in its denominator, and a run that re-clusters is not
    # its subject. These three are about this run's own report, and they are
    # the ones a re-clustering run can fail.
    check(f"every row of {os.path.relpath(NAMES_CSV, EC_DIR)} produces a "
          f"coverage record, so a name no cluster reaches is an outcome and not "
          f"an absence (names: {len(load_cluster_names())}, records: "
          f"{len(cov)})",
          len(cov) == len(load_cluster_names()))
    # The duplicate rule, asserted on what was *written* rather than on the
    # record: two new clusters reaching one name is a refusal, so the name may
    # appear in at most one row of this run's clusters. A `cluster_name` cell
    # holding it twice is the failure this pass exists to stop.
    written = [r["cluster_name"] for r in cluster_rows if r["cluster_name"]]
    twice = sorted({n for n in written if written.count(n) > 1})
    check(f"no name is written to two clusters of this run, so a name two new "
          f"clusters both reach is a reported duplicate rather than a row "
          f"written twice (written twice: {', '.join(twice) or 'none'})",
          not twice)
    duped = [r for r in carry if r["how"] == "duplicate"]
    # `from_key` is deliberately **not** asserted empty here. It records where
    # the name came from, which a duplicate does not falsify: the name did come
    # from that old row, it simply is not carried to this cluster. What a
    # duplicate must not be is a carry, and "is a carry" is `how in CARRIED`,
    # already checked by the vocabulary check above.
    check(f"every duplicate record keeps the name it refused and names the "
          f"clusters that claimed it, so the report says which name was "
          f"refused rather than only that some name was (duplicates: "
          f"{len(duped)}; without a name or a detail: "
          f"{', '.join(r['cluster_id'] for r in duped if not (r['name'] and r['detail'])) or 'none'})",
          all(r["name"] and r["detail"] for r in duped))
    # The three checks above are about **this** run, and on the committed census
    # they hold vacuously: every hand name is `seeded` onto its own cluster, so
    # there is no duplicate to refuse and none to leave unwritten. A gate that
    # cannot fail is not a gate, so the duplicate rule is driven once on the
    # shape it exists for -- `flag-pair-0442`'s two addresses split into two
    # one-address clusters, each scoring exactly CARRY_MIN_JACCARD against the
    # pair -- and the committed census's green is read as "no case here" rather
    # than as "the rule holds". The fixture is the committed row for that key,
    # read out of the CSV rather than spelled as addresses, so it cannot drift
    # away from the membership the names file actually names.
    pair_key = "kb07a0f522a7d"
    pair_row = next((r for r in old_rows if r.get("cluster_key") == pair_key), None)
    split = []
    if pair_row is not None:
        pair_addrs = pair_row.get("addrs", "").split()
        for i, a in enumerate(pair_addrs):
            split.append({"cluster_id": f"main-ec-{900 + i}",
                          "cluster_key": f"ksplit{i:011d}",
                          "addrs": a})
    dup_names, dup_report = carry_names(old_rows, load_cluster_names(), split)
    dup_outcomes = [r["how"] for r in dup_report if r["name"] == "flag-pair-0442"]
    check(f"the duplicate rule fires on the shape it is for: a two-address name "
          f"whose addresses {pair_key} names split into one cluster each, every "
          f"one of them at exactly CARRY_MIN_JACCARD, so the name is written to "
          f"neither rather than to both (outcomes: "
          f"{', '.join(dup_outcomes) or 'none recorded'}; written: "
          f"{len(dup_names)})",
          pair_row is not None and len(pair_row.get("addrs", "").split()) > 1
          and dup_outcomes == ["duplicate"] * len(split) and not dup_names)
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
    # The other half of the names file, and the half that is about a row that
    # *is* anchored: a name is read as a citation wherever its words appear, so
    # one too generic to be distinctive turns ordinary prose about charging
    # into a membership claim. The rules and the "not found by this method" list
    # are the sibling module's; the label names the offender and the shape that
    # would pass, the way the `stale:` above names its own.
    shaped = cluster_name_shape.problems()
    check(f"every name in {os.path.relpath(NAMES_CSV, EC_DIR)} is multi-slug, "
          f"inside no other name, and not an address, a symbol or a word "
          f"prefix of one, so a name cannot read as a citation in a unit that "
          f"only means the words (refused: "
          f"{'; '.join(f'{n} -- {w}' for n, w in shaped) or 'none'})",
          not shaped)

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
    _registers, clusters, _groups, report, _cov = built
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
                         "renumbering of cluster_key and the hand names "
                         "(annotations/xdata-export-ownership.md 5). Refused "
                         "with --check and --self-test, and without scratch "
                         "outputs")
    ap.add_argument("--out-registers", default=OUT_REGISTERS,
                    help=f"per-address CSV (default: {OUT_REGISTERS})")
    ap.add_argument("--out-clusters", default=OUT_CLUSTERS,
                    help=f"per-cluster CSV (default: {OUT_CLUSTERS})")
    ap.add_argument("--registers", default=os.path.join(EC_DIR, "annotations",
                                                         "registers.yaml"),
                    help="registers.yaml for --reconcile")
    args = ap.parse_args()

    # Refused here, before any mode runs: both are gates, and a flag that
    # re-buckets occurrences while writing nothing must not be reachable
    # from a mode whose claim is that the committed CSVs already match.
    # What it costs, measured by ec/tools/xdata_guard_off_row_join.py:
    # cluster_id moves on 507 of the 1,326 register rows and cluster_key on
    # 15 of the 439 clusters: docs/findings/xdata-no-eq-guard-census-scale-join.md
    if args.no_eq_guard and (args.check or args.self_test):
        ap.error("--no-eq-guard changes what the census says, so it cannot be "
                 "combined with --check or --self-test. To see the pre-#178 "
                 "buckets, write a census to a scratch path and diff it "
                 "against the committed one.")
    # The other way this flag could do damage is by writing at all: run bare
    # it overwrites the committed CSVs with the pre-#178 census. --check would
    # catch that, but only because the guard above refuses the two together
    # and so regenerates guard-on; don't rely on it. Write somewhere scratch.
    if args.no_eq_guard and (args.out_registers == OUT_REGISTERS
                             or args.out_clusters == OUT_CLUSTERS):
        ap.error("--no-eq-guard would overwrite the committed census, so it "
                 "must be given scratch outputs: pass --out-registers and "
                 "--out-clusters (see annotations/xdata-06c2-06db-timers.md 6a).")

    # The same two refusals, for the same two reasons. The flag here is the
    # other way round from --no-eq-guard -- it turns the pass *on* rather than
    # reproducing a removed guard -- because the default has to stay where it
    # is: the committed CSVs are the 42-fold census, and flipping the default
    # would move reference counts, `cluster_key`s and hand cluster names across
    # the tree (annotations/xdata-export-ownership.md §4 and §5). So the name
    # says what it does, where
    # --no-eq-guard's says what removing its guard undoes. The guard itself is
    # the same: a census the tool does not otherwise produce goes to scratch.
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

    # The third of the three, and the only one refused by which mode asked for
    # it rather than by what the run would do. `--no-writer-axis` drops the
    # writer axis in `components()`, and only two modes pass it; every other
    # mode parsed it and ignored it, so `--check --no-writer-axis` was a run
    # whose numbers are a default run's wearing a flag that says it measured
    # the second relation. Accepted and ignored is the same shape as a constant
    # with no reader, so it is refused with the other two. Which two is derived
    # rather than written: `test_xdata_census_shape_set.py` reads the readers
    # out of the tool's own AST, so a third one goes red there.
    if args.no_writer_axis and not (args.threshold_sweep
                                    or args.collapse_co_readings):
        ap.error("--no-writer-axis only changes what --threshold-sweep and "
                 "--collapse-co-readings cluster on, so it is refused with "
                 "every other mode rather than ignored by it.")

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


# *** 2026-10-03, issue #575: four NOT_IN_TREE entries for the bytes the
# routine at bank0 0xD8A0 alone touches in the 0x20xx page.
#
# **Placed here and updated into the dict, for the reason the block above
# gives about `diff()`.** The entries belong in the `NOT_IN_TREE` literal
# beside their siblings, and putting them there moves every line below that
# point -- including the `--no-eq-guard` anchors `check_eq_guard_citations.py`
# resolves by line -- and turns red every citation of them.
# This is the one window that avoids both horns: it is below every line those
# citations name, so none of them shifts, and above the `__main__` guard, so
# the update has run by the time `main()` reaches `--self-test` and counts the
# set. Appended below the guard instead, it would be dead on a script run and
# only visible to an import, which is exactly the sort of split a test that
# imports the module cannot see.
#
# The reason is the 0x0EAF one, not the 0x07C0 one: not the wrong program's
# byte, but a routine no export covers. Each of the four has exactly one
# `mov DPTR,#imm16` in the whole 256 KiB image and that site is inside
# 0xD8A0, which has no index row and no listing, so the census -- which reads
# the committed decompile -- has no function to attribute the site to. That is
# a coverage gap, and it is expected to close when the deferred annotation row
# and the export that carries it land; nothing here predicts the count.
# Re-derive with `python3 ec/tools/disasm8051.py ec/firmware/GMxMGxx_11.800
# --at 0x0D8A0 --runtime 0xD8A0 -n 61`, which prints all four sites, and with
# `scan_refs.py` on each address, which reports one EC-side site apiece. The
# reading is docs/findings/d8a0-init-routine.md.
NOT_IN_TREE.update({
    0x2012: "in a routine no export covers: as 0x0EAF, the sole site is at "
            "bank0 0xD90E, inside the routine at 0xD8A0, which has no index "
            "row and no listing",
    0x2014: "in a routine no export covers: as 0x2012, the sole site is at "
            "bank0 0xD915",
    0x2015: "in a routine no export covers: as 0x2012, the sole site is at "
            "bank0 0xD91B",
    0x201C: "in a routine no export covers: as 0x2012, the sole site is at "
            "bank0 0xD8CC",
})

# Issue #1444. Two rings whose extent the committed listings fix by the index
# arithmetic rather than by naming every byte, so the census -- which reads the
# decompiled tree -- reaches the base of each and not the slots above it. The
# same reason as 0x0390 and the same window as the block above: below every line
# those citations name, so none of them shifts, and above the `__main__` guard.
#
# The first is the mailbox's. bank1 0x89B5 masks the byte at 0x09F1 with
# `ANL A,#0x07` and adds it to DPTR, which the export writes as
# CONCAT11/index arithmetic over register names, and bank1 0x8955 clears all
# eight slots at init from the base with an 8-iteration `DJNZ R0` -- which is
# what fixes the ring at eight bytes. 0x09F6 and 0x09F9 have sites of their own
# and are here for the same reason as the rest, the .asm naming what the C does
# not; 0x09F9's two sites being in the PD image rather than the EC makes that
# plainer rather than different.
#
# The second is the sixteen-byte ring at 0x0710. bank1 0x88F0 masks 0x070F with
# `ANL A,#0x0F` and forms DPTR as 0x0710 plus that nibble, which the export
# spells CONCAT11(7,...). Re-derive with `python3 ec/tools/disasm8051.py
# ec/firmware/GMxMGxx_11.800 --at 0x108F0 -n 16`, which decodes the increment,
# the mask and the `MOV DPTR,#0x0710` past the listing's truncation, and with
# `python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0710`, which
# reports the one EC-side site the census resolves no direction for. The reading
# is docs/findings/a73f-09f1-mailbox-payload.md.
NOT_IN_TREE.update({
    0x09F3: "reached through a form the scan cannot see: as 0x09F2, a slot of "
            "the mailbox ring, reached by `ANL A,#0x07` and `ADD A,DPL` at "
            "bank1/89B5.asm and bank1/89E7.asm",
    0x09F4: "reached through a form the scan cannot see: as 0x09F3, a slot of "
            "the mailbox ring",
    0x09F5: "reached through a form the scan cannot see: as 0x09F3, a slot of "
            "the mailbox ring",
    0x09F6: "reached through a form the scan cannot see: as 0x09F3, a slot of "
            "the mailbox ring; its one EC-side site at bank1 0x8C59 is a DPTR "
            "seed the listing overwrites with no MOVX between",
    0x09F7: "reached through a form the scan cannot see: as 0x09F3, a slot of "
            "the mailbox ring",
    0x09F8: "reached through a form the scan cannot see: as 0x09F3, a slot of "
            "the mailbox ring",
    0x09F9: "reached through a form the scan cannot see: as 0x09F3, a slot of "
            "the mailbox ring; both of its sites are in the PD image",
    0x0710: "reached through a form the scan cannot see: the base of the ring "
            "bank1/88F0.asm forms as 0x0710 plus a nibble masked at 0x070F, "
            "which the export spells CONCAT11(7,...)",
    0x0711: "reached through a form the scan cannot see: as 0x0710, a slot of "
            "the sixteen-byte ring",
    0x0712: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0713: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0714: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0715: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0716: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0717: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0718: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x0719: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x071A: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x071B: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x071C: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x071D: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x071E: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
    0x071F: "reached through a form the scan cannot see: as 0x0711, a slot of "
            "the sixteen-byte ring",
})

if __name__ == "__main__":
    sys.exit(main())


# *** 2026-10-04, issue #1360: `functions_touched` counts one committed
# `index.csv` row per `out_file`, and the "one frame of code" reading is not it.
#
# **Placed at the end of the file.** The ruling belongs in this module's
# docstring, and it was written there first; it cannot stay there. This module is cited by
# line -- `check_eq_guard_citations.py` resolves the anchors below to line
# numbers and holds every page citing them, `docs/findings.md` among them, to
# what it finds there -- and the docstring is above every one of those anchors,
# so a paragraph added to it moves all of them and turns every citation to a
# line below the docstring red. `docs/findings.md` is frozen, so those citations
# cannot be re-anchored from here. The prose goes where the earlier dated
# blocks go and the code does not move at all.
#
# What the column counts: a function key is a `(program, addr)` pair, `scan()`
# credits every occurrence in *that row's own* `.c` to it, and
# `functions_touched` / `readers` / `writers` / `single_function` are `len()` of
# sets of keys -- one credit per committed row, each named once.
#
# The other reading -- **one frame of code**, where a listing the export nested
# inside another hands its credit to the frame holding it, so two `.c` files
# that decompile the same bytes are counted once -- is a different column.
# `nested_frame_census.py` measures that the export nests its own frames, so
# this is a real alternative and not a hypothetical one. It is **not this
# column**, for two reasons that are properties of the inputs rather than
# preferences.
#
# **First, the collapse is not well-defined for part of the population.**
# Handing a nested listing to "its container" needs a single outermost
# container, and there is not always one: seven rows sit inside two containers
# at once, and the census records those two in *different* buckets, so picking
# either would be wrong about the other; `common 0x6A02` and `common 0x6D46`
# nest in *each other* with neither span containing the other, so their chain
# never terminates. A column built on it would assert a container the inputs do
# not name -- `nested_frame_census.bucket_of()`'s "refusal rather than a third
# bucket", reached from the other end.
#
# **Second, and this is the binding one, not every collapse is a
# de-duplication.** The census reads *address*-inside-a-listing, which is weaker
# than its *span*-inside-a-listing predicate: a row whose listing runs past its
# container's last byte is held at its address only, so the container's `.c`
# does not re-decompile the tail and handing the row over would delete credit
# for statements no frame repeated. Beyond that, `similar()` takes the Jaccard
# of these same sets, so changing them re-clusters the tree -- a tree-wide
# renumbering, which is the cost that keeps `--export-ownership` off.
#
# `ec/tools/xdata_frame_credit.py` derives both readings from the build above
# and prints the rows that differ, the two refusal classes by name, the
# partial-overlap collapses, and the clustering cost. It writes nothing.
# `python3 ec/tools/xdata_frame_credit.py --check` asserts that the committed
# columns already encode the reading above, on every row. The write-up is
# `docs/findings/xdata-frame-credit-column.md`.
