#!/usr/bin/env python3
"""Check every cluster citation in the prose against the committed census.

Two rules over one walk of the committed markdown under `ec/`, `docs/` and
`evidence/`, both keyed on the same two CSVs, and independent of each other.

**Membership.** A cluster id in a sentence is a pointer: a reader who follows
it into `ec/annotations/xdata-clusters.csv` has to land on the membership the
sentence describes. Issue #253 is four sentences where the pointer drifted —
the ids moved when issue #4.3's census regeneration landed (#133 / #238), and
prose written against the old numbering kept the old ids. The ids are numbered
by size, then references, then lowest address (`xdata_register_map.py`'s
`build()`), which makes them a *rank*, and a rank is not an identity: it holds
only against one ranking, and one change anywhere in that ranking reshuffles
every id below the one that moved. Issue #274 measured that rather than
assuming it — regenerating with the `==` guard removed, the classifier change
#178 made, turns the 427 committed clusters into 439, of which 48 survive
intact and 379 keep their number and change what it names; a threshold change
to 0.45 gives 425 clusters, where 59 of the 427 ids are intact, 366 name a
different membership, 2 have no cluster at that number, and 413 of the 427
keys still name a cluster.

Because that is the weak handle, the id stopped being a rank (2026-10-04,
below), and three citation forms are accepted:

  * `main-ec-0300` / `pd-FF10` — the id, `<program>-<lowest address>`. An
    identity for as long as the cluster's lowest member is that address.
  * `k<12 hex>` — the `cluster_key` column, a content hash over the program
    and the sorted membership. An identity for as long as the membership is
    that membership.
  * a `cluster_name` — a hand name from `annotations/xdata-cluster-names.csv`,
    carried across a regeneration in changed form, which is the only one of the
    three that survives a cluster that changed. Names are read from the census
    rather than hard-coded here, so a name is added by editing one CSV.

All three resolve to a cluster id before anything is checked, so a sentence
citing one is held to exactly what a `main-ec-NNN` sentence was.

**Ids are not ranks any more** (2026-10-04). They were numbered by size, then
references, then lowest address, so one seeded routine renumbered clusters it
never touched: #1849's regeneration rewrote 461 rows of `xdata-registers.csv`
for their `cluster_id` alone, every seeding branch conflicted with every other
on both census CSVs, and this rule went red across write-ups nobody had edited.
`xdata_register_map.cluster_id_of` now names a cluster by its program and lowest
address, and the clusters CSV is sorted by it. Prose that cited a rank the
committed census validated was rewritten to the new id in the same change; a
legacy `main-ec-NNN` left anywhere else is what the prose measured on an older
census, resolves to nothing in this one, and a unit citing one is passed over
under its own counted reason. `check()` still reads ranks by default, for the
fixture censuses that number their clusters that way. `--clusters`
and `--registers` take an alternate census, which is what lets the same
sentences be run against a regeneration (`xdata_register_map.py --map` is what
says which clusters moved, and this is what says whether a sentence still
describes one).

**Counts.** `xdata-register-map.md` §5 is a hand-typed copy of twelve rows of
that CSV, and nothing held its numbers: four of the twelve rows disagreed with
the census beside them before issue #272. A *census row* — a markdown table row
whose first cell is one `main-ec-NNN` id — has its address range held to the
same CSV. Its size, reference count and named count are not held (2026-10-04):
they are figures of the census, which seeding a routine or naming a register
moves, and CLAUDE.md's rule for those in prose is not to hold them; the CSV,
which `--check` regenerates, is where they are current. It is a second gate rather
than an extension of the membership one and inherits none of its conditions:
a §5 row carries a range and a title but never the word "member", so the
membership rule skips every one of them, and this rule reads cells the
membership rule never sees. The first cell of such a row is read as a
`main-ec-NNN` id and not through the three forms above, because a census row's
columns are figures about one cluster, and a key or a name does not say which
the figures would be about.

The columns are found by the row's own range cell rather than by a fixed index,
which is what lets one reader cover §5's nine-column header and the shorter
five-column shape alike; `census_row()` carries why, and what a row without a
range is.

**What the membership rule does not check, which is as much of the point:**

  * *Denials.* A unit that says an address is **not** in a cluster is skipped
    rather than checked, so "X is not in main-ec-003" is never verified and a
    denial that has itself gone stale is not caught.
  * *A census-regeneration transcript.* A unit inside a fenced block that runs
    `ec/tools/xdata_register_map.py` under a flag which **changes** the census
    (`--no-eq-guard`, `--export-ownership`) is passed over, and the reason is
    counted and printed rather than left silent. A `main-ec-NNN` in such a
    block is a rank in a census the reader cannot open, and a `k<12 hex>` in
    one is not a key of the committed census at all — `kc0f2a0be0103` has zero
    rows in `xdata-clusters.csv`. That is "not found by this method" rather
    than a disagreement, and it is the same verdict `cited_clusters()` already
    gives a key or a name this generation does not carry. `--map` and
    `--check` are deliberately **not** in it: both are keyed to the committed
    identifiers, so a membership claim beside one of those is a claim about
    the committed census and is still checked. It is the fence that scopes it,
    not the prose around it — a sentence naming the same command in running
    text is an ordinary citation.
  * *Proximity.* A unit that mentions a cluster word without claiming
    membership ("the `0x06E6`/`0x0860` gate block" in a `main-ec-002` table row,
    where `0x06E6` is a byte the shared function reads and not a member) is
    skipped. Requiring the membership cue is what keeps the census summary
    table in `xdata-register-map.md` §5 — its *ranges* — out of the membership
    results; its *numbers* are the count rule's.
  * *A split written as a list.* An address is held to the cluster its own
    words put it with — "`0x06C6` in `main-ec-121` and `0x06CD` in
    `main-ec-198`" — but only where a preposition joins the two tokens and no
    clause boundary falls between them. The same claim with the ids first and
    the addresses in a trailing list ("the two cut into `main-ec-121` and
    `main-ec-198` (`0x06C6`, `0x06CD`)") pairs nothing and is satisfied by
    either id; the two in it can be exchanged without this noticing. So a
    unit naming two clusters is caught when its own wording says which is
    which, and only in the weaker sense of "a wrong id at all" where it does
    not. That weaker sense is also all a unit gets where a `cluster_name` or a
    `cluster_key` supplies the second cluster, since `pairings()` reads the
    `main-ec-NNN` token the preposition has to join.
  * *How a name was carried.* A `cluster_name` resolves to whichever cluster
    holds it today; whether it got there by an identical key or by a 0.51
    Jaccard is `xdata_register_map.py --map`'s to report, and a name that
    resolves is not thereby evidence the sentence is right.
  * *A name too generic to be distinctive.* Names are matched as whole tokens
    wherever they appear in a unit that also makes a membership claim, so a
    name like `charge-target` would be read as a citation in a sentence that
    only means the words. What a name may **look** like is a check rather than
    advice: `ec/tools/cluster_name_shape.py`, run from
    `xdata_register_map.py --self-test`, refuses a name that is not a
    multi-slug, one that sits inside another name, and one that collides with a
    known address, a known function or symbol, or a word prefix of one. What
    that cannot see is a name already being read as a citation in the prose
    this file walks -- it reads the names file and four CSVs, and the corpus is
    not among them -- so `fan-level`, which none of its rules catches, is still
    a limit on how a name should be chosen rather than a check. A smaller limit
    than the one this bullet used to carry, not none of one.
  * *An address introduced as a bound or operand.* The any-of fallback has no
    exemption for one, and the proposal to add it was measured and **not
    adopted** -- `ec/tools/census_citation_exemptions.py` enumerates the set it
    would admit, by calling this file's own `census()`, `units()`,
    `skip_reason()`, `cited_clusters()` and `pairings()` rather than walking a
    second time, and `docs/findings/operand-bound-exemption-census.md`
    records the decision and the criterion it was taken against. Two measured
    results decide it. The role lexicon is `bound`, `immediate`, `operand`,
    `target`, and it fires on **no** address's own clause anywhere in the
    committed corpus: every hit is a word in a neighbouring clause or elsewhere
    in the unit, which is the `charge-target` false positive above reproduced
    in the output rather than described. And the one sentence the proposal is
    for -- §26's re-packed summary, which `OneAttributionPerUnit` holds as
    *expected to report* -- **would** be admitted by it, and admitting it
    silences exactly the `0x0800` disagreement that case exists to keep
    reported. A rule whose only demonstration is the sentence that motivated
    it is the half-measure `reset-vector-dptr-targets.md` declines. The
    addresses a `SPAN` token makes a range are the one wordless case; they are
    a separate exemption with a separate reading, the census reports them
    separately rather than folding them into the lexicon figure, and none is
    recorded as agreed. What the census measured is the prose committed here --
    not a claim that the exemption would be wrong in general. The same census
    turned up a live defect in this file's *walk*, which is fixed rather than
    written up: see `LIST_ITEM` and `units()`.
  * *Where a quoted paragraph happened to be wrapped.* `line.strip()` takes a
    blockquote's indentation but not its `>`, so a sentence boundary inside a
    quote used to be recognised only where the marker did not fall between the
    period and the next capital: the same text read as one unit or two on the
    strength of where an author wrapped it, with no change in the words.
    `TERMINATOR` now carries `>`, so a wrap point that lands on the marker is a
    boundary like any other. Stripping the marker before the join -- the other
    way to make the wrap irrelevant -- was measured and **not adopted**: with the
    `>` gone `LIST_ITEM` can see the `-` of a quoted tight list, so a quote
    splits into one unit per item, and in `xdata-06c2-06db-timers.md` that
    separates a cluster id from the addresses it governs and the address item is
    passed over for making no membership claim. An attribution the walk holds
    today stops being held. Both readings report no disagreement over the
    committed corpus, so coverage decided it and the verdicts could not.
    `docs/findings/blockquote-terminator-wrap.md` records the measurement. What
    is *not* decided here is whether a blockquoted correction should be a unit of
    its own: a quotation's membership claims arguably belong to the source it
    quotes rather than to this repository's prose, and that is a question about
    what the gate is for rather than a wrapping defect.
  * *Anything outside the three roots*, and any address the census does not
    know, so a code address that collides with an XDATA one is not examined.

**And what the count rule does not check.** A cell is read as a count only if
it is a bare decimal integer — thousands commas allowed, so `1,136` is 1136 —
in the size or reference column; the "named inside" column is not read at all.
Everything else in a census row is left alone, which is most
of why the rule can sit in the tree without flagging the corpus:

  * *A span.* `` `0x030E`-`0x1809` `` is two addresses of a range. The count
    rule reads it as the row's range and holds it against `addr_range`, but it
    is never read as a number of anything, in any column.
  * *Free text.* `**43 addresses, 4,965 refs**` in
    `xdata-06c2-06db-timers.md:491` is a deliberate contrast between the
    committed cluster and the shape a code guard would produce, and the prose
    under it says that shape carries no id. Reading counts out of free text
    would flag those two figures permanently and for no reason.
  * *A dash in a size or reference column.* The same corpus writes `—` there
    for "this figure does not apply to this row", which is not a claim of
    zero.
  * *A row naming more than one cluster id.* Which row's figures would apply
    is ambiguous, so a row that names two is not read as a census row at all.
  * *A row whose cluster id is not in its first cell.* The
    `gpu-tgp-07c4-07d7-door.md` cross-reference table puts `main-ec-001` in a
    cross-reference column beside `dsdt.dsl:52204` source line numbers, which
    are not counts of anything this census knows.
  * *A row with no range cell to anchor the columns.* The range is what says
    which cell is the size and which is the reference count, so a row without
    one — or with one so near the front that neither has room before it — has
    not said, and none of its three figures is read. No committed row is in
    that state today; it is the shape a table would be left in if it lost the
    column, and reading it on a guess is what the fixed-index reader this
    replaced was doing silently.

Every one of those is "not found by this method", never "absent" — the same
caveat `ec/annotations/registers.yaml` carries for a static scan. Passing this
means the checked sentences and the checked counts agree with the committed
CSVs; it does not mean the prose is right about the firmware, and where the
count rule cannot read a cell it says nothing about that figure.

Usage:
    python3 ec/tools/check_cluster_citations.py [--verbose]
    python3 ec/tools/check_cluster_citations.py --clusters /tmp/after-clusters.csv
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EC = os.path.join(HERE, os.pardir)
REPO = os.path.join(EC, os.pardir)
ROOTS = ("ec", "docs", "evidence")

CLUSTERS = os.path.join(EC, "annotations", "xdata-clusters.csv")
REGISTERS = os.path.join(EC, "annotations", "xdata-registers.csv")

# A cluster id: `<program>-<lowest address>` since 2026-10-04, which is an
# identity (`xdata_register_map.cluster_id_of`), or the legacy `main-ec-NNN`
# rank every id was before then. `RANK` is the legacy form alone: the committed
# census carries none, so on the committed tree a rank resolves to nothing and
# a unit citing one is passed over rather than read.
CLUSTER_ID = re.compile(r"\b(?:main-ec|pd)-[0-9A-F]{4}\b|main-ec-\d{3}\b")
RANK = re.compile(r"\bmain-ec-\d{3}\b")
CLUSTER_KEY = re.compile(r"\bk[0-9a-f]{12}\b")
ADDRESS = re.compile(r"0x([0-9A-Fa-f]{4})\b")


def name_re(names):
    """Whole-token alternation over the census's own cluster names.

    Built from the names rather than from a pattern, because a name is a human's
    to choose and the tool should not hold a shape on them. Longest-first so
    `counter-sweep-06c6` cannot be read as `counter-sweep` inside it, and
    word-bounded on both ends so no name matches inside a longer one.
    """
    alt = "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True) if n)
    return re.compile(r"\b(?:" + alt + r")\b") if alt else None


# A unit only makes a membership claim if it says membership somewhere. The
# word "cluster" alone is not enough -- `xdata-register-map.md` §5's rows carry
# cluster ids and address ranges with no claim that the ranges are the rows'
# members -- but "member" is, and so is "clustering", which is how the
# sentences that drifted in #253 phrase it.
MEMBERSHIP = re.compile(r"\b(?:clustering|clusters?|members?)\b", re.IGNORECASE)

# Phrases that take an address *out* of the cluster the unit names. These units
# are skipped, not checked: see the docstring.
DISCLAIM = re.compile(
    r"\b(?:not|isn't|aren't|never|no longer)\s+(?:in|among|part of|a member|member of)\b"
    r"|\b(?:on|of) its own\b"
    r"|\bsingleton\b",
    re.IGNORECASE,
)

# A fenced block, opened or closed. Every fence line in the committed corpus
# is exactly three backticks, so the width is not read off a variable here, but
# a block closes on a fence of *its own* width rather than on the next one of
# any, which is the rule that keeps an outer ```` block from being closed by an
# inner ``` one. The corpus has no nested fence to exercise that, so it is a
# claim about today's prose and not a guarantee; the unterminated case below is
# the one the corpus does reach.
FENCE = re.compile(r"^\s*(?P<fence>`{3,})")

# The one tool whose flags *change* the census rather than report it, so a
# fenced block running one of them is showing a generation this run is not
# holding prose to. `--map` and `--check` are excluded on purpose: both are
# keyed to the committed identifiers, so a membership claim beside one of
# those commands is a claim about the committed census and is checked like any
# other. The fence is what scopes this, so the command has to be *inside* the
# block -- the same command named in running prose is an ordinary citation.
REGENERATES = re.compile(
    r"xdata_register_map\.py[^\n]*--(?:no-eq-guard|export-ownership)\b")

# The closed list of reasons a unit is passed over rather than checked, in
# `skip_reason()`'s own order, and the one place they are written down. A skip
# that cannot be named is a blind spot nobody is looking at, so the run counts
# them per reason and prints the counts rather than staying quiet; the suite
# holds this list to the reasons the committed run actually exercised, in both
# directions, so a reason added to `skip_reason()` without being added here is
# named by name rather than arriving as a figure that moved.
SKIPS = ("census-regeneration transcript", "disclaims membership",
         "no membership claim", "cites a rank")
RANK_ONLY = SKIPS[-1]

# The preposition that turns two tokens into one claim. Both orders occur in
# the corpus -- "`0x06C6` in `main-ec-121`", and "`main-ec-011` is the
# 10-address, 91-reference cluster of `0x0875 0x089C ...`" -- so a pair is
# read whichever way round the two tokens sit.
MEMBERSHIP_PREP = re.compile(r"\b(?:in|into|within|of|inside|to)\b", re.IGNORECASE)

# A span crossing one of these is not one claim, so nothing is paired across
# it. The brackets are the conservative half: a preposition on one side of a
# parenthetical is not a claim about a token on the other side of it, which is
# what "cut into `main-ec-121` and `main-ec-198` (`0x06C6`, `0x06CD`)" would
# otherwise invite. A unit is one joined line by `units()`, so there is no
# newline to break on.
CLAUSE_BREAK = re.compile(r"[;:.()]")

# A sentence ends at a terminator followed by something that starts a new one.
# The trailing set matters in a corpus written as wrapped prose inside list
# items and tables: without the `-` and `|` here, one list item's sentence runs
# on into the next item's and drags its addresses along with it.
#
# `>` is here for the same reason, and `line.strip()` is why it was missing:
# stripping takes a blockquote's indentation but not its marker, so a boundary
# inside a quoted paragraph was recognised only where the `>` did not land
# between the period and the next capital -- the same text read as one unit or
# two on the strength of where an author wrapped it. Carrying the marker is the
# fix that keeps the wrap irrelevant; stripping it before the join was measured
# and not adopted, see the docstring and `docs/findings/blockquote-terminator-wrap.md`.
TERMINATOR = re.compile(r"(?<=[.!?])\s+(?=[A-Z`*_|>-])")

# A range, which is what anchors a census row's columns. §5 writes it
# `` `0x030E`-`0x1809` ``, one backtick per address, so it is only recognisable
# as a span once `clean` has taken the backticks out.
SPAN = re.compile(r"0x[0-9A-Fa-f]{4}-0x[0-9A-Fa-f]{4}")
MARKUP = re.compile(r"[`*]")

# A list item is its own unit, for the reason a table row is: the items mean
# different things, and joining them makes one item's cluster id reach into the
# next item's addresses. A *tight* list -- consecutive items with no blank line
# between them, which is what `gen_findings_index.py` renders -- has no
# paragraph break for the walk to cut on, so the whole list read as one unit and
# whether it was membership-checked at all turned on whether any single title
# anywhere in it contained a cue word. That is a live defect rather than a
# hypothetical: naming one write-up `cluster-citation-operand-exemption.md`
# moved the word `cluster` into that unit and turned this checker from exit 0 to
# exit 1 on a tree whose prose had not changed, with a dozen unrelated
# write-ups' addresses reported as disagreements. See
# `docs/findings/operand-bound-exemption-census.md`.
#
# A continuation line does not start with a marker and so stays with the item it
# continues, which is what keeps a wrapped item whole. `TERMINATOR`'s lookahead
# carries `-` for the same reason and is left in place: it also separates a
# sentence from a `-` that opens a line inside a paragraph this does not flush.
LIST_ITEM = re.compile(r"^(?:[-*+]\s|\d+[.)]\s)")


def clean(cell):
    """The cell's own text, without the markdown wrapped around it.

    A §5 cell is bolded or backticked or both, and the id cell is both at
    once (`**`main-ec-003`**` in `xdata-06c2-06db-timers.md`). The backticks
    go throughout rather than off the ends, because a range is written
    `` `0x030E`-`0x1809` `` and it is only the range once they are gone.
    """
    return MARKUP.sub("", cell).strip()


def cells(unit):
    """(the cells of a markdown table row) or () if the unit is not one."""
    if not (unit.startswith("|") and unit.endswith("|")):
        return ()
    return [c.strip() for c in unit[1:-1].split("|")]


def census(clusters_csv=None, registers_csv=None):
    """(membership per id, known addresses, counts, key -> id, name -> id).

    Membership and the counted columns all come from the clusters CSV, which is
    keyed by program, so a `main-ec-NNN` id is unambiguous on its own. The
    registers CSV is read only for its address column: an address that is not
    in the census is a code address in a sentence full of them, not a cluster
    member claim.

    The key and name maps are what the two durable citation forms resolve
    through. Every column past `addrs` is read with `.get(..., "")` so a census
    written before those columns existed -- an `--clusters` fixture, or the
    committed file as it stood before #274 -- still resolves every
    `main-ec-NNN` sentence rather than failing on the file.
    """
    members, counts, by_key, by_name = {}, {}, {}, {}
    with open(clusters_csv or CLUSTERS, newline="") as f:
        for r in csv.DictReader(f):
            cid = r["cluster_id"]
            members[cid] = set(r["addrs"].split())
            counts[cid] = {"size": int(r.get("size") or 0),
                           "refs": int(r.get("refs") or 0),
                           "named": len((r.get("named_addrs") or "").split()),
                           "addr_range": r.get("addr_range") or ""}
            if (r.get("cluster_key") or "").strip():
                by_key[r["cluster_key"].strip()] = cid
            if (r.get("cluster_name") or "").strip():
                by_name[r["cluster_name"].strip()] = cid
    with open(registers_csv or REGISTERS, newline="") as f:
        known = {r["addr"] for r in csv.DictReader(f)}
    return members, known, counts, by_key, by_name


def fence_spans(lines):
    """[(open, close)] line numbers of every properly-paired fenced block.

    A block still open at the end of the file is not one, and its lines are
    left to the ordinary walk. That is not a hypothetical: the seven fence
    lines of `pd-only-status-vocabulary.md` do not pair the way the prose
    between them reads -- one closes a block whose opener is not there, and so
    every later fence in the file is off by one -- and the last of them opens a
    block that runs to the end. Reading the tail of that page as block body
    would join thirty lines of prose into one unit nothing can adjudicate,
    which is the opposite of what a conservative walk is for. An unterminated
    block is not found by this method, and the unit boundary it would have
    made is a boundary this walk does not claim to know.
    """
    spans, start, width = [], None, None
    for lineno, line in enumerate(lines, 1):
        m = FENCE.match(line)
        if not m:
            continue
        if start is None:
            start, width = lineno, m.group("fence")
        elif m.group("fence") == width:
            spans.append((start, lineno))
            start, width = None, None
    return spans


def transcript_lines(text):
    """{line} of every line inside a fenced block that regenerates the census.

    A set of line numbers rather than a predicate over the unit, because the
    sentence that gets skipped is not the sentence carrying the command: the
    command is on the block's first line and the membership it produced is
    lines later, and joining them is what makes the skip mean anything. The
    walk in `units()` is what puts them in one block; this is the one place
    that says which blocks those are.

    Empty for a file with no fence at all, which is most of the corpus, so
    `check()` computes it behind the same cheap pre-filter that skips the
    files naming no cluster.
    """
    lines = text.split("\n")
    return {lineno
            for open_at, close_at in fence_spans(lines)
            for lineno in range(open_at, close_at + 1)
            if REGENERATES.search("\n".join(lines[open_at:close_at]))}


def units(text):
    """(line number, unit) for each attribution-sized piece of prose.

    A table row is its own unit: the columns of a census table mean different
    things, and letting a row run into the next would make the unit's addresses
    mean nothing in particular. A **list item** is its own unit for the same
    reason, and where a list is tight -- consecutive items with no blank line
    between them, which is how `gen_findings_index.py` renders every write-up
    title -- there is no paragraph break to cut on, so without this the whole
    list was one unit and a single cue word in any title anywhere in it decided
    whether every address in the index was checked. A continuation line carries
    no marker and so stays with the item it continues, which keeps a wrapped
    item whole. A fenced block is a paragraph boundary for the same reason and
    by the same route, but it is still cut into sentences inside itself --
    `reset-vector-dptr-targets.md:451` puts a membership claim
    in a fence and a second, unrelated claim in the sentence after it *inside
    that fence*, and the split between them is the whole of the #605 fix.
    Making the block one uncut unit would put both claims back in one sentence
    and report `0x0800`, which is the shape that fix took out. Everything else
    is joined per paragraph and cut into sentences, because this corpus wraps
    sentences across lines and a line-based scan misses an attribution that
    straddles a wrap -- which is exactly how the `manual-fan-ctrl-0751.md` one
    hides.
    """
    lines = text.split("\n")
    closes = {open_at: close_at for open_at, close_at in fence_spans(lines)}

    def sentences(buf):
        joined = " ".join(t for _, t in buf)

        def line_at(offset):
            walked = 0
            for lineno, t in buf:
                if offset < walked + len(t) + 1:
                    return lineno
                walked += len(t) + 1
            return buf[-1][0]

        start = 0
        for end in [m.end() for m in TERMINATOR.finditer(joined)] + [len(joined)]:
            chunk = joined[start:end].strip()
            if chunk:
                yield line_at(start), chunk
            start = end

    def flush(buf):
        if buf:
            yield from sentences(buf)

    buf = []
    lineno = 1
    while lineno <= len(lines):
        stripped = lines[lineno - 1].strip()
        if lineno in closes:
            # The delimiters themselves are not unit text: a fence line names
            # no cluster and no address, and the block's own lines are what
            # the rules read. Inside the block the sentence split still runs,
            # which is the point the docstring makes.
            yield from flush(buf)
            buf = []
            body = [(n, lines[n - 1].strip())
                    for n in range(lineno + 1, closes[lineno])
                    if lines[n - 1].strip()]
            yield from sentences(body)
            lineno = closes[lineno] + 1
        elif stripped.startswith("|") and stripped.endswith("|"):
            yield from flush(buf)
            buf = []
            yield lineno, stripped
            lineno += 1
        elif not stripped:
            yield from flush(buf)
            buf = []
            lineno += 1
        elif buf and LIST_ITEM.match(stripped):
            # A new item opens where the paragraph would have continued. Only
            # when `buf` is non-empty: a list straight after a blank line is
            # already its own paragraph, and treating its first item as a flush
            # would drop the text before it.
            yield from flush(buf)
            buf = [(lineno, stripped)]
            lineno += 1
        else:
            buf.append((lineno, stripped))
            lineno += 1
    yield from flush(buf)


def line_of_address(unit, address):
    """The line a unit's address token is on, for the report.

    Not the line the unit starts on: in a wrapped sentence the cluster id and
    the address it is wrong about are often not on the same line, and a report
    that points at the wrong line is worse than none.
    """
    for lineno, sentence in units(unit):
        if address in sentence.upper():
            return lineno
    return 0


def pairings(unit, addresses):
    """{address: cluster id} for the address/id pairs the unit's wording makes.

    A unit saying "`0x06C6` in `main-ec-121` and `0x06CD` in `main-ec-198`" is
    claiming the split between two clusters, and reading it as "in either" is
    how `xdata-06c2-06db-timers.md`'s stale `main-ec-118` got past #253. An
    address pairs with an id where a preposition joins the two tokens and
    nothing else does: no second address, no second id, no clause boundary in
    between. Where several ids qualify for one address the nearest wins, and
    where none does the address is left to the any-of rule.

    Only the `main-ec-NNN` token is paired, not a `cluster_key` or a
    `cluster_name`. The preposition is what makes a split a claim, and the
    committed corpus states every split that way, so the two durable forms
    reach the any-of rule rather than a stricter one -- which the docstring
    lists under what is not checked.
    """
    addr_spans = [m.span() for m in ADDRESS.finditer(unit)]
    id_spans = [m.span() for m in CLUSTER_ID.finditer(unit)]
    all_spans = addr_spans + id_spans
    pairs = {}
    for match in ADDRESS.finditer(unit):
        address = "0x" + match.group(1).upper()
        if address not in addresses:
            continue
        nearest = None
        for span in id_spans:
            lo, hi = sorted((match.span(), span))
            between = unit[lo[1]:hi[0]]
            if not MEMBERSHIP_PREP.search(between) or CLAUSE_BREAK.search(between):
                continue
            if any(lo[1] < s[0] < hi[0] for s in all_spans):
                continue
            if nearest is None or hi[0] - lo[1] < nearest[0]:
                nearest = (hi[0] - lo[1], unit[span[0]:span[1]])
        if nearest:
            pairs[address] = nearest[1]
    return pairs


def census_row(path, lineno, unit, counts):
    """(problems) for a census row's hand-typed range.

    Only the range is held (2026-10-04). The size, the reference count and the
    named count beside it are figures of the census, and seeding one routine
    moves them: #1849 went red on §5 rows of `xdata-register-map.md`, a
    shared file every such branch would then have to edit. CLAUDE.md's rule for a census figure in prose is to stop holding
    it; `xdata-clusters.csv`, which `--check` regenerates, is where they are
    current. The range is the cell that says which cluster the row is about.

    Independent of the membership rule and run before it, because a §5 row
    never reaches the membership rule: it has an address range and a title,
    and not one of its cells says "member". So a row is read here, and only a
    row is: the first cell has to be one cluster id the census knows.
    """
    row = cells(unit)
    if len(row) < 3:
        return []
    head = clean(row[0])
    ids = CLUSTER_ID.findall(head)
    # `findall` rather than a `fullmatch`, so a cell naming two clusters is
    # not a census row: whose figures would they be?
    if len(ids) != 1 or head != ids[0]:
        return []
    facts = counts.get(ids[0])
    if facts is None:
        return []

    problems = []
    # The range cell is what says which columns are which, so it is found
    # by content rather than at a fixed index: the two cells before it are the
    # size and the reference count. A fixed index does not work
    # on §5's own header -- `cluster | key | name | size | refs | range |
    # named inside | co-reading | functions` -- where `row[1]` is a
    # `cluster_key` and `row[2]` a `cluster_name`, so both `number()` reads
    # returned None and the count rule checked neither figure on any real row
    # while its docstring claimed it held both (#1240).
    #
    # The anchor rather than the header, for two reasons. `units()` yields one
    # table row at a time and carries no table with it, so a header-resolving
    # reader would have to reach past the unit for state the walk does not
    # keep; and the corpus's shorter shape (`cluster | size | refs | range |
    # named inside`) has no header row at all, so a header-only reader would
    # check less than this one does. The range is the one cell whose *content*
    # says which column it is, and both shapes carry it.
    anchor = None
    for i, cell in enumerate(row[2:], start=2):
        if SPAN.fullmatch(clean(cell)):
            anchor = i
            break
    # No anchor, or one too near the front for a size and a reference count to
    # sit before it: which columns these figures occupy is not found by this
    # method, and a row that does not say is left alone rather than guessed at.
    if anchor is None or anchor < 3:
        return problems

    # The size and the reference count, the two cells before the range, are
    # not held; see the docstring. A census problem has no paired id: the
    # `kind` says which rule raised it, and only a membership one names a
    # cluster for the unit's own wording to have paired the address with.
    #
    # The range is held to the row's own `addr_range`. Only the first span is
    # an anchor, which is what keeps a span written in the named column from
    # being read as a range. An `--clusters` CSV with no `addr_range` column has
    # nothing to hold the row to, so the range is left alone rather than
    # checked against an empty string.
    stated = clean(row[anchor])
    if facts["addr_range"]:
        if stated.upper() != facts["addr_range"].upper():
            problems.append((path, lineno, ids,
                             f"range `{facts['addr_range']}` in the census, "
                             f"`{stated}` in the row", "census range", None))
        # The named count, the cell after the range, is not held. It counts
        # the addresses `registers.yaml` names, so it is a census of this
        # repository's own text and every branch that names a register moves
        # it: #1919 named one in `main-ec-004` on a base without #1891's read
        # of that column, both were green, and main went red on the pair.
        # CLAUDE.md's rule for such a total is to stop holding it.
    return problems


def cited_clusters(unit, by_key, by_name, names):
    """The cluster ids a unit cites, by whichever of the three forms it used.

    A token is only counted if the census can resolve it, so a `k<12 hex>` that
    is not a key of this census and a name this generation does not carry are
    both ignored rather than reported as a cluster with no membership -- the
    same "not found by this method" the rest of the file uses. The three forms
    are additive: a sentence naming an id and a name of the same cluster cites
    one cluster, and the membership test below is satisfied by either.

    The count rule is not routed through here and is not meant to be: it reads
    a census row's first cell as a `main-ec-NNN` id, because a row of figures
    is about one cluster and a name does not say which."""
    found = set(CLUSTER_ID.findall(unit))
    found |= {by_key[k] for k in CLUSTER_KEY.findall(unit) if k in by_key}
    if names is not None:
        found |= {by_name[n] for n in names.findall(unit) if n in by_name}
    return sorted(found)


def skip_reason(lineno, unit, transcripts):
    """Why this unit is passed over rather than checked, or None to check it.

    `SKIPS`, in the order they are returned, most specific first. A unit inside
    a census-regeneration transcript is not a citation about the committed
    census at all -- its `main-ec-NNN` is a rank in a generation the reader
    cannot open -- so whether it also disclaims membership or merely mentions a
    cluster is not the question, and it is asked first. The other two are
    properties of the unit's own words and are decided from the text alone,
    which is why they take no `transcripts`.

    Ordered the other way round, the transcript reason would be a fact about
    the corpus rather than about the rule: a block that disclaims membership
    would be counted as a denial, and a reader counting skip reasons would be
    counting the prose instead of the blind spot.
    """
    if lineno in transcripts:
        return "census-regeneration transcript"
    if DISCLAIM.search(unit):
        return "disclaims membership"
    if not MEMBERSHIP.search(unit):
        return "no membership claim"
    return None


def check(path, members, counts, known, by_key=None, by_name=None, verbose=False,
          ranks=True):
    """(problems, lines read, skip reasons) for one file.

    `ranks=False` is the committed-tree run: a unit naming a legacy
    `main-ec-NNN` rank is skipped as `RANK_ONLY`, since the committed census
    has no ranks to resolve it against. The default reads ranks, for a fixture
    census that still numbers its clusters that way.

    The skip reasons come back rather than being counted here, so `main()` can
    print one figure for the whole corpus instead of one per file. They are the
    reasons and not the units, because a count of units is the hand-kept total
    `docs/findings.md` §4a warns about: the run prints what it found and the
    suite asserts that the reason is exercised, never how many times.
    """
    by_key = by_key or {}
    by_name = by_name or {}
    names = name_re(by_name)
    problems, skipped = [], []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # The cheap pre-filter, for the same reason the old one existed: most of the
    # corpus names no cluster at all, and reading every file twice is the
    # difference between a check a human runs and one they do not.
    if ("main-ec-" not in text and not CLUSTER_KEY.search(text)
            and not (names and names.search(text))):
        return problems, len(text.split("\n")), skipped
    transcripts = transcript_lines(text)
    for lineno, unit in units(text):
        ids = cited_clusters(unit, by_key, by_name, names)
        if not ids:
            continue
        problems += census_row(path, lineno, unit, counts)
        addresses = sorted({"0x" + a.upper() for a in ADDRESS.findall(unit)
                            if "0x" + a.upper() in known})
        if not addresses:
            continue
        # The exemption is the membership rule's, so it is applied where the
        # membership rule is: the count rule above has already read this unit,
        # and a hand-typed census row inside a fence is still held to the
        # committed CSV. The two rules stay apart the way the docstring's
        # second one is.
        reason = skip_reason(lineno, unit, transcripts)
        if not reason and not ranks:
            if RANK.search(unit):
                reason = RANK_ONLY
        if reason:
            skipped.append(reason)
            if verbose:
                print(f"  skip ({reason}) {path}:{lineno}", file=sys.stderr)
            continue
        # Ordered after the skips above: a denial is not a claim, and a pairing
        # rule reached first would read "a size-1 cluster of its own" as an
        # attribution. The fallback is per address, not per unit, so a unit
        # that pairs one byte still has its other addresses checked.
        pairs = pairings(unit, addresses) if len(ids) > 1 else {}
        for address in addresses:
            expected = [pairs[address]] if address in pairs else ids
            if not any(address in members.get(cid, ()) for cid in expected):
                at = line_of_address(unit, address)
                problems.append((path, at or lineno, ids, address, "membership",
                                 pairs.get(address)))
    return problems, len(text.split("\n")), skipped


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="report every unit skipped, and why")
    ap.add_argument("--clusters", default=CLUSTERS,
                    help=f"clusters CSV to check against (default: {CLUSTERS}). "
                         "Point it at a regeneration's output to run the same "
                         "sentences against it")
    ap.add_argument("--registers", default=REGISTERS,
                    help=f"registers CSV whose address column bounds what is an "
                         f"XDATA address (default: {REGISTERS})")
    args = ap.parse_args()

    members, known, counts, by_key, by_name = census(args.clusters, args.registers)
    paths = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                      if f.endswith(".md")]
    paths.sort()

    problems = []
    read = 0
    skipped = []
    for path in paths:
        found, lines, reasons = check(path, members, counts, known, by_key,
                                      by_name, args.verbose, ranks=False)
        problems += found
        read += lines
        skipped += reasons

    # Printed before the problems rather than with the closing line, because
    # the reason a run is red is sometimes one of these skips having stopped
    # firing: a reader who sees two citations disagree needs to be able to see
    # that a third unit was passed over and why, in the same run.
    by_skip = collections.Counter(skipped)
    print("skipped: " + ", ".join(
        f"{reason} {count}" for reason, count
        in sorted(by_skip.items(), key=lambda kv: (-kv[1], kv[0]))))

    for path, lineno, ids, what, kind, paired in problems:
        where = f"{os.path.relpath(path, REPO)}:{lineno}"
        named = ", ".join(f"`{cid}`" for cid in ids)
        if kind == "membership":
            if paired:
                claim = f"not in `{paired}`, the cluster this line pairs it with"
            else:
                claim = f"not a member of any cluster this line names ({named})"
            print(f"{where}: {what} is {claim}; it is a member of "
                  f"{cluster_of(what, members)}", file=sys.stderr)
        else:
            print(f"{where}: {kind} disagrees for {named}: {what}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} citation(s) disagree with "
              f"{os.path.relpath(args.clusters, REPO)}", file=sys.stderr)
        return 1
    print(f"{len(paths)} files / {read} lines: every checked cluster citation "
          f"(id, `cluster_key` or `cluster_name`) resolves to the membership it "
          f"names, and every census row's range agrees with "
          f"{os.path.relpath(args.clusters, REPO)}; {len(skipped)} unit(s) "
          f"passed over under the {len(SKIPS)} reasons above, each of them: "
          f"not checked, not absent")
    return 0


def cluster_of(address, members):
    """The id the census does give this address, for the error message."""
    for cid in sorted(members):
        if address in members[cid]:
            return f"`{cid}`"
    return "no main-ec cluster (a pd-image cluster, or none)"


if __name__ == "__main__":
    sys.exit(main())
