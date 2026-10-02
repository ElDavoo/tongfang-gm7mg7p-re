#!/usr/bin/env python3
r"""Check issue #104's upstream-facing note for `0x0786` and the Turbo bit.

The artifact is `linux/patches/gm7mg7p-ec-register-names.md`: a note a human
will lift into an upstream PR, saying per register what `uniwill-laptop`
asserts, what this tree's evidence shows, how confident that is, and what a
maintainer would need from other boards. It reads only committed files -- the
note, the two upstream excerpts it quotes, `ec/annotations/registers.yaml`, the
decompiled vendor sources, the 2026-09-23 EC-watch captures, and
`evidence/acpi/dsdt.dsl`. It opens no image, no network and no hardware, so a
reviewer can run it offline and check every citation the note makes.

**Six rules, and the reason each is here.**

  1. **Upstream spellings are sourced, and the note's own names are accounted
     for.** Every row of the note's "what upstream asserts" table must name a
     symbol that a committed excerpt really carries, at the line the note
     cites, with the value the note claims. And the other direction: every
     `EC_ADDR_*` / `FAN_*` token anywhere in the note is a row of that table,
     so a name cannot be used in prose and never graded against the pinned
     rev. A `#define` is the only accepted shape, which is what keeps the
     excerpt files' own `[bracket]` annotations -- one of which names
     `FAN_TURBO_SUPPORTED` in prose -- out of the pass.
  2. **The `registers.yaml` rows are real, and `0x0742`'s absence is
     enforced.** Every address the note makes a claim about resolves to an
     entry that file has, at the name and status the note quotes. The one
     address with **no** entry is `0x0742`, and a row calling it an entry is
     refused -- as is a row *claiming* it has none once the file grows one,
     which is the other direction of the same gap. Without this rule a later
     reader "fixes" the note into a citation that resolves to nothing, and a
     note that grades an address nobody graded is the failure this rule is
     for. The closure is over the note's tables rather than its whole text,
     because firmware *code* addresses share the `0xNNNN` shape and are not
     register claims.
  3. **Decompiled citations land.** Every `file:line` in the note's citation
     table must resolve to a line that file has, and every identifier and
     decimal the cell names must be in the cited span, in the order the cell
     names them. Hex is exempt: the note's whole job is translating between a
     vendor that writes `1926` and an upstream that writes `0x0786`, and both
     ends are anchored elsewhere -- the vendor half here, the upstream half in
     rule 1 -- so the arithmetic is left to the reader rather than guessed at
     by a shape match.
  4. **Live values are in the committed snapshot, and "held" means no
     transition.** Every value the note quotes must be a line of the capture
     the note names, and a `read from` cell naming one of the `*-cycle-*.csv`
     files is refused outright. That is the delta-log confusion the issue
     this note answers got wrong: those files have the header `ts,addr,old,new`
     and record transitions, so the *absence* of a row means no change was
     observed and never that a value was read. The second half holds the other
     direction: an address the note calls unchanged across the mode cycle must
     have no row in those files, and one it calls changed must have one.
  5. **The DSDT field list says what the note says**, and is *derived* rather
     than transcribed. Each row names the field list and the byte, and the
     checker walks that device's ASL, accumulates the bit positions and reports
     which fields cover that byte, at what width and at which bits of it.
     Holding the note to a table typed into this file would test the typing.
     Two things go wrong here if the walk is careless, and both are load-bearing
     rather than defensive: another device's field list covers the same offset
     (`UCSI` is at `0x786` in a USB controller's), so the walk has to stop at
     the named `Device`; and the enable bit of that byte is its *second* field,
     so the test is overlap rather than "begins at the byte's first bit".
  6. **The two declines, and the one that can go stale.** Every claim in the
     note's standing table carries a `kind` and a `standing` from closed sets,
     and the two kinds this note exists to keep open -- a claim about
     upstream's *use* of a name, and a claim about a bit's *generality across
     boards* -- may only be carried as `not-established`. Separately, the
     `FAN_TURBO_SUPPORTED` decline is held against the excerpts: no quoted
     upstream line outside a `#define` may carry that symbol, so the day a
     fragment showing a read lands, this rule goes red and says the note has
     to say more. That is the one rule here that can be falsified by evidence
     rather than by an edit, which is why it is a rule and not a sentence.

`--self-test` drives each rule against the mutation it is meant to catch, on
fixtures rather than the committed note, with a negative control beside every
positive so that a green run is not the absence of testing. A check that has
quietly stopped refusing looks exactly like a check that is working.

**What this does not check, which is as much of the point.** Nothing here says
upstream's names are wrong, or that a rename is warranted, or that `0x049F`
bit 1 is the capability bit on any other board. It says the note's citations
resolve, that its values come from the capture it names, and that the two
claims this note declines to make are still declined. The decisive observation
for the Turbo question is a Uniwill board *without* Turbo, which is a human at
a machine; the note asks for it in `§5` instead of predicting it.

Usage:
    python3 tools/check_upstream_register_names.py --check
    python3 tools/check_upstream_register_names.py --self-test
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NOTE = os.path.join(REPO, "linux", "patches",
                            "gm7mg7p-ec-register-names.md")
PATCHES = os.path.join(REPO, "linux", "patches")
DEFAULT_REGISTERS = os.path.join(REPO, "ec", "annotations", "registers.yaml")
DEFAULT_WATCH = os.path.join(REPO, "evidence", "ec-watch")
DEFAULT_DSDT = os.path.join(REPO, "evidence", "acpi", "dsdt.dsl")

# The note's tables, by the first cell of their header row, matched exactly.
# Keying on the header rather than on position is what lets a note gain a
# paragraph without the checker reading the wrong table; matching exactly
# rather than by prefix is what stops a summary table whose first column
# happens to start with the same two words from being read as a real one. A
# missing table is a refusal, not a skip, because a rule with nothing to read
# has stopped checking rather than passed.
TBL_UPSTREAM = "upstream symbol"
TBL_REGISTERS = "ec address"
TBL_DSDT = "dsdt field"
TBL_CITED = "what"
TBL_LIVE = "observed address"
TBL_STANDING = "claim"
REQUIRED_TABLES = (TBL_UPSTREAM, TBL_REGISTERS, TBL_DSDT, TBL_CITED,
                   TBL_LIVE, TBL_STANDING)

# The cell that says an address has no `registers.yaml` entry, compared with
# its punctuation and emphasis stripped. `unquote()` is not reused for this:
# it would also strip the parentheses out of `BIT(4)`, which is a value rule 1
# does need them for.
NO_ENTRY = "no entry"


def flag(cell):
    """A cell read as a bare word: `*(no entry)*` is `no entry`."""
    return re.sub(r"[^\w\s]", "", cell or "").strip().lower()


# What a standing may say, and what a claim is *about*. Both closed sets: the
# standing column exists so a reader can discount a claim without reading the
# sentence beside it, and a vocabulary nobody can enumerate is a column that
# says nothing. The last two kinds are the ones rule 6 constrains.
STANDINGS = {
    "confirmed-live",        # a value in a committed capture
    "confirmed-static",      # read off committed source
    "hypothesis-agreeing-sources",  # two authorities agree, no live test
    "present-untested",      # mirrors registers.yaml, no new evidence
    "not-established",       # declined here; needs something this tree lacks
}
KINDS = {"this-board", "cross-board", "upstream-use", "pinned-source"}
DECLINED_KINDS = {"cross-board", "upstream-use"}

# The name whose "is it read?" question rule 6 holds open, and the rule 1
# token families. The families are the prefixes `uniwill-acpi.c` uses for the
# fan-block and address-block constants; a `TURBO_*` or `UNIWILL_*` name in
# this note would be upstream's own vocabulary rather than a register the note
# is asking about, and would need its own row and its own rule to be honest.
UPSTREAM_SYMBOL = re.compile(r"\b(?:EC_ADDR|FAN)_[A-Z0-9_]+\b")
# The symbol rule 6's read-decline is about. Spelled here rather than
# inherited from the note, because a checker that reads the claim it is
# checking cannot refuse it.
TURBO_BIT_NAME = "FAN_TURBO_SUPPORTED"

ADDRESS = re.compile(r"0x[0-9A-Fa-f]{4}")
# An EC address, and an ASL offset. The DSDT spells the same byte `0x786` with
# three digits and the register tables spell it `0x0786` with four, and both
# have to resolve to the same number for the note's two tables to agree.
OFFSET = re.compile(r"0x[0-9A-Fa-f]{3,4}")
# A `file:line` or `file:start-end` citation, repo-relative.
CITATION = re.compile(r"^([\w./-]+\.\w+):(\d+)(?:-(\d+))?$")
# A `name` cell, and the line number a capture's own value line carries.
PINNED = re.compile(r"^([\w./-]+):(\d+)(?:-(\d+))?$")
HEX = re.compile(r"^0x[0-9A-Fa-f]+$")
DECIMAL = re.compile(r"^[0-9]+$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
BACKTICKED = re.compile(r"`([^`]+)`")

# An excerpt's own quoted fragment: `  254: #define EC_ADDR_FAN_DEFAULT 0x0786`.
EXCERPT_LINE = re.compile(r"^\s*(\d+): (.*)$")
# A `#define`, so that a fragment quoting something other than a definition
# cannot satisfy rule 1 and a fragment showing a *read* can be told apart from
# one showing a definition.
DEFINE = re.compile(r"^#define\s+([A-Z][A-Z0-9_]*)\s+(.*)$")

# A DSDT field-list line, in both the named and the reserved (`    ,   1, `)
# spellings iasl emits.
DSDT_OFFSET = re.compile(r"^\s*Offset \((0x[0-9A-Fa-f]+)\),\s*$")
DSDT_FIELD = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*,\s*(\d+)\s*,\s*$")
DSDT_RESERVED = re.compile(r"^\s*,\s*(\d+)\s*,\s*$")


# --- reading the note ------------------------------------------------------

def read_tables(text, header_key):
    """Every table keyed by its first header cell, as `(header, rows)` pairs.

    The key is matched **exactly**, and that is deliberate rather than
    incidental: a prefix match reads a summary table whose first column starts
    with the same two words as the citation table's as though it were the
    citation table, and then refuses the note for a row that has no citation
    in it. Every header here is now a whole cell of its own, so nothing needs
    a looser match. Only lines opening with `|` count and only a well-formed
    separator row starts a table, so the note's prose cannot be collected as if
    it were one.

    *Every* match, not the first: the note carries two citation tables under
    the same `what | citation` header, one per discrepancy, and a reader that
    stopped at the first would hold half the note's citations and report
    nothing about the other half -- the defect this exists to prevent, one
    level up from a citation that does not resolve.
    """
    found = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("|") or i + 1 >= len(lines):
            continue
        if not re.fullmatch(r"\|(?:\s*:?-+:?\s*\|)+", lines[i + 1].strip()):
            continue
        header = [c.strip() for c in line.strip().strip("|").split("|")]
        if unquote(header[0]).lower() != header_key:
            continue
        rows = []
        for raw in lines[i + 2:]:
            if not raw.startswith("|"):
                break
            cells = [c.strip() for c in raw.strip().strip("|").split("|")]
            cells += [""] * (len(header) - len(cells))
            rows.append({header[n].strip().lower(): cells[n]
                         for n in range(len(header))})
        found.append((header, rows))
    return found


def table_rows(text, header_key):
    """Every row of every table keyed by `header_key`, or `[]`.

    A key that is not there reads as an empty list, and `note_problems()`
    treats an empty required table as a refusal rather than as a pass.
    """
    return [row for _header, rows in read_tables(text, header_key)
            for row in rows]


def unquote(cell):
    """A cell with its backticks, emphasis and whitespace removed.

    Whether the note wrote `0x0742` or `0x0742` or **0x0742** is not part of
    any claim, and a comparison that made it one would be a rule about
    formatting.
    """
    return re.sub(r"[`*]", "", cell or "").strip()


# --- reading the committed inputs -----------------------------------------

def file_lines(path):
    """{file line number: text} for a committed file a citation may name."""
    out = {}
    with open(path) as f:
        for n, raw in enumerate(f, 1):
            out[n] = raw.rstrip("\n")
    return out


def quoted_fragment(line):
    """`(upstream line number, text)` for an excerpt line quoting upstream.

    `None` for anything else -- a blank, a `[bracket]` annotation naming what
    the fragment below it is about, a section heading. Only the `NNN: text`
    form is a quotation, which is what stops an excerpt's own prose from
    standing in for a definition or for a read.
    """
    m = EXCERPT_LINE.match(line or "")
    return (int(m.group(1)), m.group(2).rstrip()) if m else None


def registers_index(path=DEFAULT_REGISTERS):
    """{address: (entry name, status)} over every address in registers.yaml.

    An `addr: 0x049F` cell is a YAML hex integer, so the keys here are ints and
    a note's `0x049F` is converted to one before it is looked up. A four
    address entry registers the same pair at each of its addresses, which is
    what a note naming one of them is asserting about.
    """
    import yaml
    with open(path) as f:
        regs = yaml.safe_load(f)["registers"]
    out = {}
    for entry in regs:
        addrs = entry["addr"] if isinstance(entry["addr"], list) else [entry["addr"]]
        for addr in addrs:
            out[int(addr)] = (entry.get("name", ""), entry.get("status", ""))
    return out


def snapshot_values(path):
    """{ADDRESS: VALUE} out of a read-only EC capture's own value lines.

    `0x049F = 0x0A`, uppercased on both sides so a note that writes `0x49f` is
    not refused for its case. A file that has none -- a `ts,addr,old,new` delta
    log, which records transitions rather than readings -- parses to an empty
    mapping, and rule 4 says so by name rather than letting it pass as a
    capture that happened to hold nothing.
    """
    out = {}
    for raw in open(path):
        m = re.match(r"^\s*(0x[0-9A-Fa-f]+)\s*=\s*(0x[0-9A-Fa-f]+)\s*$", raw)
        if m:
            out[m.group(1).upper()] = m.group(2).upper()
    return out


def cycle_addresses(watch_dir=DEFAULT_WATCH):
    """Every address that appears as a row of any `*-power-mode-cycle-*.csv`."""
    import csv
    import glob
    out = set()
    for path in sorted(glob.glob(os.path.join(
            watch_dir, "*power-mode-cycle-*.csv"))):
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                addr = (row.get("addr") or "").strip()
                if addr:
                    out.add(addr.upper())
    return out


def dsdt_field_at(dsdt_lines, device, offset):
    """The field-list fields covering `offset` in `device`, derived from the ASL.

    Walks from the `Device (<device>)` line, and within it each field list as
    a sequence of `Offset (0xNNN),` groups whose following `NAME, WIDTH,`
    lines advance a running bit position -- including the unnamed reserved
    fields iasl emits. Returns `[(name, first bit within the byte, width), ...]`
    for the fields that *overlap* `offset`, or `None` when no field list of
    that device covers it.

    Two things this gets wrong if it is not careful, and both are why it is
    written this way rather than as a scan for the offset. The walk is bounded
    to the named device because the file holds several field lists and an
    earlier one covers the same offset -- `UCSI` is at 0x786 in a USB
    controller's list, which is what an unbounded walk finds. And the test is
    *overlap* rather than "starts inside the byte", because the enable bit of
    the byte the note is about is the second field of that byte: a test for a
    field beginning at the byte's first bit finds `APTC` and stops one field
    short of the bit that is the claim.

    Derived rather than transcribed on purpose: a checker holding the note to
    a table of expected field names typed here would be testing the typing.
    """
    dev = re.compile(r"^\s*Device \(([^)]*)\)")
    start = None
    for n, raw in enumerate(dsdt_lines):
        m = dev.match(raw)
        if m and m.group(1).strip() == device:
            start = n + 1
            break
    if start is None:
        return None
    base = bit = None
    group = []
    for raw in dsdt_lines[start:]:
        m = DSDT_OFFSET.match(raw)
        if m:
            if group:
                return group
            base, bit, group = int(m.group(1), 16), 0, []
            continue
        if base is None:
            continue
        named = DSDT_FIELD.match(raw)
        reserved = DSDT_RESERVED.match(raw)
        if not named and not reserved:
            # A line that is neither an `Offset` nor a field ends the field
            # list: iasl closes each one before the next `Field (...)`.
            if raw.strip() and group:
                return group
            continue
        name, width = ((named.group(1), int(named.group(2))) if named
                       else ("", int(reserved.group(1))))
        at = base * 8 + bit
        bit += width
        if at < (offset + 1) * 8 and at + width > offset * 8:
            group.append((name, at - offset * 8, width))
    return group or None


# --- the rules -------------------------------------------------------------

def note_problems(text, *, regs, sources, values, cycles, field_at):
    """Every rule, decided against the note and the committed inputs.

    Split out from `main()` so `--self-test` can drive it against a fixture
    without touching the committed note. Every input is injected, because a
    self-test that mutated the real files to prove a refusal works would be a
    self-test that could damage the artifact it is checking.
    """
    problems = []
    for key in REQUIRED_TABLES:
        if not table_rows(text, key):
            problems.append(
                f"the note has no table headed {key!r}. "
                f"Every rule below is decided against one of those tables, and "
                f"a rule with no table to read has stopped checking rather "
                f"than passed")

    # --- rule 1: the spellings, and the names the note uses ---------------
    upstream = table_rows(text, TBL_UPSTREAM)
    named = set()
    for n, row in enumerate(upstream, 1):
        symbol = unquote(row.get("upstream symbol", ""))
        value = unquote(row.get("value at the pinned rev", ""))
        pin = unquote(row.get("quoted from", ""))
        label = f"upstream table row {n} ({symbol or '?'})"
        if not symbol or not value or not pin:
            problems.append(
                f"{label}: a row needs an upstream symbol, its value at the "
                f"pinned rev, and the excerpt line it was read from. One of "
                f"the three is empty, so the row asserts something it does not "
                f"say")
            continue
        named.add(symbol)
        pm = PINNED.match(pin)
        if not pm:
            problems.append(
                f"{label}: quoted from {pin!r} is not of the form "
                f"`<excerpt>:<line>`")
            continue
        rel, first = pm.group(1), int(pm.group(2))
        last = int(pm.group(3) or pm.group(2))
        lines = sources.get(rel)
        if lines is None:
            problems.append(
                f"{label}: {rel} is not a committed excerpt the note can quote "
                f"(looked for it under linux/patches/)")
            continue
        for n_line in range(first, last + 1):
            if n_line not in lines:
                problems.append(
                    f"{label}: {rel} has {len(lines)} line(s), so there is no "
                    f"line {n_line} to have quoted")
                continue
            fragment = quoted_fragment(lines[n_line])
            if fragment is None:
                problems.append(
                    f"{label}: {rel} line {n_line} is "
                    f"{lines[n_line].strip()!r}, which is not a quoted "
                    f"fragment. An excerpt's own `[bracket]` annotation names "
                    f"what the fragment below it is about, and reading one as "
                    f"the quotation is how a name the source never defines "
                    f"would pass")
                continue
            _upstream_line, quoted = fragment
            quoted = " ".join(quoted.split())
            dm = DEFINE.match(quoted)
            if not dm or dm.group(1) != symbol:
                problems.append(
                    f"{label}: {rel} line {n_line} quotes {quoted!r}, which is "
                    f"not `#define {symbol} ...`. A definition is the only "
                    f"shape this rule accepts")
                continue
            rest = " ".join(dm.group(2).split())
            if rest != value and not rest.startswith(value + " "):
                problems.append(
                    f"{label}: the note gives {symbol} the value {value!r}, and "
                    f"the excerpt's line defines it as {rest!r}")
    for symbol in sorted(set(UPSTREAM_SYMBOL.findall(text)) - named):
        problems.append(
            f"the note uses the upstream name {symbol} but the table above has "
            f"no row for it. Every name the note quotes has to be read off a "
            f"committed excerpt at the pinned rev, including the ones that "
            f"appear only in prose")

    # --- rule 2: the registers.yaml rows, and 0x0742's absence ------------
    graded = table_rows(text, TBL_REGISTERS)
    known = {}
    for n, row in enumerate(graded, 1):
        addr = unquote(row.get(TBL_REGISTERS, ""))
        entry = unquote(row.get("registers.yaml entry", ""))
        status = unquote(row.get("status", ""))
        label = f"registers table row {n} ({addr or '?'})"
        if not ADDRESS.fullmatch(addr):
            problems.append(
                f"{label}: {addr!r} is not a four-digit EC address, so the row "
                f"does not say which register it grades")
            continue
        value = int(addr, 16)
        if flag(entry) == NO_ENTRY:
            known[value] = addr.lower()
            if value in regs:
                name, _status = regs[value]
                problems.append(
                    f"{label}: the note says registers.yaml has no entry for "
                    f"{addr}, and it now has one -- {name!r}. A note that "
                    f"records a gap which has been closed is a stale claim, "
                    f"and the gap is the thing to update")
            continue
        if value not in regs:
            problems.append(
                f"{label}: registers.yaml records no entry for {addr}, so the "
                f"note is citing a register this repository has not graded. "
                f"Cite where the address actually is, or add the entry with its "
                f"evidence")
            continue
        known[value] = addr.lower()
        name, real = regs[value]
        if entry != name:
            problems.append(
                f"{label}: the note names the entry {entry!r}, and "
                f"registers.yaml calls it {name!r}. The entry names carry the "
                f"reading, so a paraphrase here is a claim about a different "
                f"register")
        if status != real:
            problems.append(
                f"{label}: the note gives {addr} the status {status!r}, and "
                f"registers.yaml records {real!r}")

    # The closure is over the tables, not over the whole note: firmware *code*
    # addresses share the `0xNNNN` shape and are not register claims, so a
    # whole-text rule would refuse this note's own citation of the EC's Turbo
    # path rather than anything false.
    live = table_rows(text, TBL_LIVE)
    for n, row in enumerate(live, 1):
        addr = unquote(row.get("observed address", ""))
        if ADDRESS.fullmatch(addr) and int(addr, 16) not in known:
            problems.append(
                f"live table row {n}: the note quotes a live value for {addr}, "
                f"and the registers.yaml table above has no row for it. An "
                f"address the note reports a value for is one it is making a "
                f"claim about, and a claim with no grading behind it is the "
                f"defect this closure exists for")
    for row in upstream:
        value = unquote(row.get("value at the pinned rev", ""))
        if ADDRESS.fullmatch(value) and int(value, 16) not in known:
            problems.append(
                f"upstream table row: the note says upstream names {value}, and "
                f"the registers.yaml table above has no row for it")

    # --- rule 3: the decompiled citations land ---------------------------
    for n, row in enumerate(table_rows(text, TBL_CITED), 1):
        what = row.get("what", "")
        pin = unquote(row.get("citation", ""))
        label = f"citation table row {n} ({pin or '?'})"
        cm = CITATION.match(pin)
        if not cm:
            problems.append(
                f"{label}: {pin!r} is not a citation of the form "
                f"`<path>:<line>` or `<path>:<start>-<end>`")
            continue
        rel, first = cm.group(1), int(cm.group(2))
        last = int(cm.group(3) or cm.group(2))
        lines = sources.get(rel)
        if lines is None:
            problems.append(
                f"{label}: {rel} is not a file this repository holds, so the "
                f"citation resolves to nothing")
            continue
        if first < 1 or last < first or last > len(lines):
            problems.append(
                f"{label}: {rel} has {len(lines)} line(s), so the cited span "
                f"{first}-{last} is not inside it. A `file:line` that has "
                f"drifted off the end of its file is a citation to nowhere")
            continue
        span = "\n".join(lines[n] for n in range(first, last + 1))
        # Identifiers and decimals have to be there, and the order of the
        # identifiers is part of the claim: the DSDT row says `APTN` is set
        # before `APTC`, and that is a statement about the file, not a
        # spelling. Hex is exempt -- this note's job is translating between a
        # vendor that writes `1926` and an upstream that writes `0x0786`, and
        # both ends are anchored by other rules.
        found = [t for t in BACKTICKED.findall(what)
                 if IDENT.fullmatch(t) or DECIMAL.fullmatch(t)]
        for token in found:
            if token not in span:
                problems.append(
                    f"{label}: the note names {token!r} in the claim, and no "
                    f"line of {rel}:{first}-{last} carries it. The citation "
                    f"does not support the sentence beside it")
        # Order is checked over identifiers only. A bare digit has no
        # position of its own -- `3` is found inside `1183` three characters
        # earlier -- so an order test over decimals would be a test of where
        # the numbers happen to sit in the source, not of the claim.
        idents = [t for t in found if IDENT.fullmatch(t)]
        if len(set(idents)) == len(idents) and len(idents) > 1:
            positions = [span.find(t) for t in idents]
            if positions != sorted(positions):
                problems.append(
                    f"{label}: the claim names {idents} in that order, and they "
                    f"do not appear in that order in {rel}:{first}-{last}")

    # --- rule 4: the live values, and what "held" means -------------------
    for n, row in enumerate(live, 1):
        addr = unquote(row.get("observed address", ""))
        value = unquote(row.get("value", "")).upper()
        source = unquote(row.get("read from", ""))
        held = unquote(row.get("changed during the mode cycle", "")).lower()
        label = f"live table row {n} ({addr or '?'})"
        m = ADDRESS.fullmatch(addr)
        if not m or not source:
            problems.append(
                f"{label}: a live row needs a four-digit address and the "
                f"capture it was read from")
            continue
        if "cycle" in source:
            problems.append(
                f"{label}: read from {source}, which is a transition log. That "
                f"file has the header `ts,addr,old,new` and records only "
                f"changes, so it never read this address: the absence of a row "
                f"means no change was observed, not that a value was seen. "
                f"Cite the snapshot for the value and the cycle log for the "
                f"unchanged-across-the-run claim")
            continue
        read = values.get(source)
        if read is None:
            problems.append(
                f"{label}: read from {source}, which is not a capture under "
                f"evidence/ec-watch/ that this note can read")
            continue
        if read.get(addr.upper()) != value:
            problems.append(
                f"{label}: the note gives {addr} the value {value}, and "
                f"{source} records "
                f"{read.get(addr.upper(), 'nothing at all')}. A value the "
                f"capture does not carry is a value nobody observed")
        if held not in ("yes", "no"):
            problems.append(
                f"{label}: `changed during the mode cycle` is {held!r}, which "
                f"is neither `yes` nor `no`. The column has to say which, "
                f"because the answer is checked against the transition log "
                f"rather than taken on trust")
            continue
        moved = addr.upper() in cycles
        if (held == "no") == moved:
            problems.append(
                f"{label}: the note says {addr} "
                f"{'changed' if held == 'yes' else 'did not change'} during the "
                f"mode cycle, and the 2026-09-23 cycle capture "
                f"{'has' if moved else 'has no'} row for it")

    # --- rule 5: the DSDT field list, derived -----------------------------
    # The rows are grouped by the field list and byte they name, because a
    # note may describe more than one byte and each is derived on its own.
    # Comparing the whole table against one group would be a rule that only
    # works while the table has one row group in it.
    groups = []
    for row in table_rows(text, TBL_DSDT):
        key = (unquote(row.get("field list", "")), unquote(row.get("byte at", "")))
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(row)
    for (device, byte), rows in groups:
        label = f"DSDT table row for {device or '<no field list>'} {byte or '<no byte>'}"
        if not (device and OFFSET.fullmatch(byte)):
            problems.append(
                f"{label}: a row needs the field list it is read from and the "
                f"`0xNNN` byte it describes, and one of the two is missing")
            continue
        derived = field_at(device, int(byte, 16))
        if not derived:
            problems.append(
                f"{label}: no field list of {device} covers offset {byte} in "
                f"evidence/acpi/dsdt.dsl. That is 'not found by this method' "
                f"rather than a false claim -- the walk is bounded to the named "
                f"device, because another device's field list covers the same "
                f"offset -- but a claim the ASL cannot reach is not one to put "
                f"upstream")
            continue
        got_names = [unquote(r.get(TBL_DSDT, "")) for r in rows]
        want_names = [d or "<reserved>" for d, _b, _w in derived]
        got_widths = [unquote(r.get("width in bits", "")) for r in rows]
        want_widths = [str(w) for _d, _b, w in derived]
        got_bits = [unquote(r.get("bits in that byte", "")) for r in rows]
        want_bits = [f"{b}-{b + w - 1}" for _d, b, w in derived]
        if got_names != want_names:
            problems.append(
                f"{label}: the ASL names {want_names} there and the note names "
                f"{got_names}. Every field covering the byte has to be a row, "
                f"and named as the ASL names it")
        if got_widths != want_widths:
            problems.append(
                f"{label}: the note gives {got_names} the widths {got_widths} "
                f"and the field list gives {want_widths}")
        if got_bits != want_bits:
            problems.append(
                f"{label}: the note places {got_names} at bits {got_bits} of "
                f"the byte at {byte}, and the field list puts them at "
                f"{want_bits}")

    # --- rule 6: the two declines, and the one that can go stale ---------
    standings = table_rows(text, TBL_STANDING)
    kinds = set()
    for n, row in enumerate(standings, 1):
        claim = unquote(row.get("claim", ""))
        kind = unquote(row.get("kind", "")).lower()
        standing = unquote(row.get("standing", "")).lower()
        label = f"standing table row {n} ({claim[:48] or '?'})"
        if not claim:
            problems.append(
                f"{label}: a standing with no claim beside it says how sure "
                f"the note is about nothing")
            continue
        if kind not in KINDS:
            problems.append(
                f"{label}: kind {kind!r} is not one of: {', '.join(sorted(KINDS))}")
        else:
            kinds.add(kind)
        if standing not in STANDINGS:
            problems.append(
                f"{label}: standing {standing!r} is not one of: "
                f"{', '.join(sorted(STANDINGS))}. The column exists so a reader "
                f"can discount a claim without reading the sentence beside it")
            continue
        if kind in DECLINED_KINDS and standing != "not-established":
            problems.append(
                f"{label}: a {kind} claim is carried as {standing!r}. Whether "
                f"upstream reads a name, or whether a bit means the same thing "
                f"on every board, cannot be settled from this repository, and "
                f"the standing that says so is the only one this rule accepts "
                f"for it")
    for kind in sorted(DECLINED_KINDS):
        if kind not in kinds:
            problems.append(
                f"the standing table carries no {kind} claim. The two "
                f"questions this note exists to ask -- does upstream read the "
                f"name, and is the bit the same on every board -- are the "
                f"calibration, and a table that dropped them would be "
                f"decorative")

    # The decline itself, held against the excerpts rather than against the
    # sentence that states it. This is the one rule here a new fragment can
    # falsify rather than an edit, which is why it is a rule and not a
    # sentence in the note.
    reads = []
    for rel, lines in sorted(sources.items()):
        for n in sorted(lines):
            fragment = quoted_fragment(lines[n])
            if not fragment:
                continue
            quoted = " ".join(fragment[1].split())
            if TURBO_BIT_NAME in quoted and not DEFINE.match(quoted):
                reads.append(f"{rel}:{n}")
    declined = any(
        TURBO_BIT_NAME in unquote(r.get("claim", ""))
        and unquote(r.get("kind", "")).lower() == "upstream-use"
        and unquote(r.get("standing", "")).lower() == "not-established"
        for r in standings)
    if declined and reads:
        problems.append(
            f"the note declines to claim upstream reads {TURBO_BIT_NAME}, and "
            f"a committed excerpt now shows it: {', '.join(reads)}. A decline "
            f"the tree no longer supports is a claim that has gone stale, and "
            f"the note has to say what the fragment shows")

    return problems


def load_inputs(note_path=DEFAULT_NOTE, registers=DEFAULT_REGISTERS,
                watch=DEFAULT_WATCH, dsdt=DEFAULT_DSDT, patches=PATCHES):
    """Read every committed input the rules are decided against.

    The excerpts are globbed rather than listed, so an excerpt directory that
    lands later is read without a line here, and every one of them counts
    towards rule 6's read-decline -- including one the note does not cite,
    which is exactly the fragment that would make the decline stale. The
    decompiled and DSDT sources come from the note's own citations, because
    those are the only files the note is claiming anything about.
    """
    import glob
    text = open(note_path).read()
    sources = {}
    for path in sorted(glob.glob(os.path.join(patches, "*", "upstream-excerpt*.txt"))):
        rel = os.path.relpath(path, patches).replace(os.sep, "/")
        sources[rel] = file_lines(path)
    for row in table_rows(text, TBL_CITED):
        cm = CITATION.match(unquote(row.get("citation", "")))
        if not cm:
            continue
        rel = cm.group(1)
        path = os.path.join(REPO, rel)
        if os.path.exists(path) and rel not in sources:
            sources[rel] = file_lines(path)
    values = {}
    for name in sorted(os.listdir(watch)):
        if name.endswith((".txt", ".csv")):
            values[name] = snapshot_values(os.path.join(watch, name))
    dsdt_lines = file_lines(dsdt)
    return {
        "regs": registers_index(registers),
        "sources": sources,
        "values": values,
        "cycles": cycle_addresses(watch),
        "field_at": lambda device, offset: dsdt_field_at(
            [dsdt_lines[n] for n in sorted(dsdt_lines)], device, offset),
    }


def report(problems):
    for p in problems:
        print(f"  REFUSED  {p}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} refusal(s). A refusal is a citation this note "
              f"does not support, not an argument that the note's conclusion "
              f"is wrong.", file=sys.stderr)
    return problems


# --- the self-test ---------------------------------------------------------

NOTE_HEAD = """# A fixture

| upstream symbol | value at the pinned rev | quoted from |
|---|---|---|
| `EC_ADDR_FAN_DEFAULT` | `0x0786` | `upstream-excerpt.txt:2` |
| `FAN_TURBO_SUPPORTED` | `BIT(4)` | `upstream-excerpt.txt:4` |

| EC address | registers.yaml entry | status |
|---|---|---|
| `0x0786` | `CPU_TCC_OFFSET (APTC/APTN)` | `present-untested` |
| `0x049F` | `BIOS_INFO_3 (Turbo mode supported)` | `present-untested` |
| `0x0742` | *(no entry)* | *(no entry)* |

| dsdt field | field list | byte at | width in bits | bits in that byte |
|---|---|---|---|---|
| `APTC` | `EC0` | `0x786` | `7` | `0-6` |
| `APTN` | `EC0` | `0x786` | `1` | `7-7` |

| what | citation |
|---|---|
| `SetCpuTccOffset` writes `1926` | `vendor.cs:1-2` |

| observed address | value | read from | changed during the mode cycle |
|---|---|---|---|
| `0x0786` | `0x00` | `snap.txt` | `no` |
| `0x049F` | `0x0A` | `snap.txt` | `no` |

| claim | kind | standing |
|---|---|---|
| `0x0786` is the TCC offset here | this-board | hypothesis-agreeing-sources |
| the name is wrong on every board | cross-board | not-established |
| upstream reads `FAN_TURBO_SUPPORTED` | upstream-use | not-established |
"""


def self_test():
    """Each rule, against the mutation it is meant to catch.

    Fixtures, not the committed note: the committed note is what the rules
    were derived from and other issues are open against this tree, so a check
    that can no longer refuse looks exactly like a check that is working.
    """
    # The excerpt, as a committed file: the quoted fragments carry their own
    # upstream line numbers, and line 5 is the `[bracket]` annotation that
    # names a symbol in prose without defining it.
    excerpt = {
        "upstream-excerpt.txt": {
            1: "",
            2: "  254: #define EC_ADDR_FAN_DEFAULT\t\t0x0786",
            3: "",
            4: "  151: #define FAN_TURBO_SUPPORTED\t\tBIT(4)",
            5: "  [the FAN_TURBO_SUPPORTED block, which this patch does not use]",
            6: "  152: #define FAN_SUPPORT\t\t\tBIT(5)",
        },
        "other-excerpt.txt": {1: "  9: #define EC_ADDR_NOTHING\t\t0x9999"},
    }
    regs = {
        0x0786: ("CPU_TCC_OFFSET (APTC/APTN)", "present-untested"),
        0x049F: ("BIOS_INFO_3 (Turbo mode supported)", "present-untested"),
    }
    values = {"snap.txt": {"0X0786": "0X00", "0X049F": "0X0A", "0X0742": "0X02"},
              "cycle-0700-07ff.csv": {}}
    cycles = set()
    sources = {**excerpt, "vendor.cs": {
        1: "private void SetCpuTccOffset(int v, bool bApExist)",
        2: "  if (bApExist) EcCtrl.Write(1926, v);",
    }}
    dsdt = [
        "Device (XUSB)", "    {", "        Field (RBUF, ByteAcc)", "        {",
        "            Offset (0x786),", "            UCSI,   8,", "        }", "    }",
        "Device (EC0)", "        {", "        Name (_HID, \"EC0\")",
        "        OperationRegion (IO, SystemIO, 0x60, 0x07)",
        "        Field (IO, ByteAcc, Lock, Preserve)", "        {",
        "            CMD0,   8,", "            Offset (0x02),", "            CMD2,   8,",
        "        }", "        Field (ECR, ByteAcc, Lock, Preserve)", "        {",
        "            Offset (0x783),", "            APL1,   8,",
        "            APL2,   8,", "            APL4,   8,",
        "            APTC,   7,", "            APTN,   1,",
        "            Offset (0x788),", "            CTWA,   8,", "        }",
        "        Method (WTCC, 2)", "        {",
        "            ^^EC0.APTN = One", "            ^^EC0.APTC = Arg1",
        "        }",
    ]
    field_at = lambda device, offset: dsdt_field_at(dsdt, device, offset)  # noqa: E731

    def run(text, **kw):
        return note_problems(text, regs=kw.get("regs", regs),
                             sources=kw.get("sources", sources),
                             values=kw.get("values", values),
                             cycles=kw.get("cycles", cycles),
                             field_at=field_at)

    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    # The fixture itself, or none of the cases below test anything: a `not
    # run(...)` case passes for the wrong reason when the fixture is already
    # red.
    check("the fixture note is clean", not run(NOTE_HEAD),
          f"({run(NOTE_HEAD)})")

    # --- rule 1 ---------------------------------------------------------
    check("a symbol no excerpt line carries is refused",
          run(NOTE_HEAD.replace("`EC_ADDR_FAN_DEFAULT`", "`EC_ADDR_FAN_DEFAUL`")),
          "(a misspelling that looks right is the case this rule is for)")
    check("a citation past the end of the excerpt is refused",
          run(NOTE_HEAD.replace("upstream-excerpt.txt:2",
                                "upstream-excerpt.txt:99")))
    check("a value the excerpt does not define is refused",
          run(NOTE_HEAD.replace("| `0x0786` | `upstream-excerpt.txt:2` |",
                                "| `0x0799` | `upstream-excerpt.txt:2` |")))
    check("an excerpt's bracket annotation is not a quotation",
          run(NOTE_HEAD.replace("`upstream-excerpt.txt:4`",
                                "`upstream-excerpt.txt:5`")),
          "(the negative case: line 5 names the symbol in prose, is not a "
          "quoted fragment at all, and a looser rule would read the "
          "annotation as if it were the definition below it")
    check("a fragment that defines a different symbol is refused",
          run(NOTE_HEAD.replace("| `FAN_TURBO_SUPPORTED` | `BIT(4)` | "
                                "`upstream-excerpt.txt:4` |",
                                "| `FAN_TURBO_SUPPORTED` | `BIT(4)` | "
                                "`upstream-excerpt.txt:6` |")),
          "(line 6 is a `#define` for a different name, so a rule matching "
          "`#define` without matching the symbol would pass it")
    check("a name used in prose but absent from the table is refused",
          run(NOTE_HEAD + "\nProse naming `FAN_CURVE_LENGTH` in passing.\n"))
    check("a name that is in the table is not refused for being in prose",
          not run(NOTE_HEAD + "\nProse naming `EC_ADDR_FAN_DEFAULT` again.\n"),
          "(the negative control: the closure is about names the table has "
          "never graded, not about repeating one that it has)")

    # --- rule 2 ---------------------------------------------------------
    check("an entry name registers.yaml does not use is refused",
          run(NOTE_HEAD.replace("`CPU_TCC_OFFSET (APTC/APTN)`",
                                "`CPU_TCC_OFFSET`")))
    check("a status registers.yaml does not record is refused",
          run(NOTE_HEAD.replace("| `0x049F` | `BIOS_INFO_3 (Turbo mode "
                                "supported)` | `present-untested` |",
                                "| `0x049F` | `BIOS_INFO_3 (Turbo mode "
                                "supported)` | `confirmed-working` |")))
    check("an address registers.yaml has no entry for is refused",
          run(NOTE_HEAD.replace("| `0x049F` | `BIOS_INFO_3 (Turbo mode "
                                "supported)` | `present-untested` |",
                                "| `0x0499` | `BIOS_INFO_3 (Turbo mode "
                                "supported)` | `present-untested` |")))
    check("a live address with no registers.yaml row is refused",
          run(NOTE_HEAD.replace(
              "| `0x049F` | `0x0A` | `snap.txt` | `no` |",
              "| `0x0751` | `0x10` | `snap.txt` | `no` |")),
          "(the closure: an address the note reports a value for is one it is "
          "claiming something about")
    check("0x0742 cannot be cited as a registers.yaml row",
          run(NOTE_HEAD.replace(
              "| `0x0742` | *(no entry)* | *(no entry)* |",
              "| `0x0742` | `USB_C_POWER_PRIORITY` | `unknown-not-absent` |")),
          "(the guard the plan asks for: a citation to a row that does not "
          "exist resolves to nothing, and a reader 'fixing' the note into one "
          "is the failure")
    check("a claim that 0x0742 has no row goes stale once the file grows one",
          any("now has one" in p for p in run(
              NOTE_HEAD, regs={**regs, 0x0742: ("NEWLY_ADDED", "present-untested")})),
          "(the other direction of the same gap, so the rule survives the gap "
          "being closed rather than turning red on a correct note")
    check("the no-entry row for an address the file really lacks is not refused",
          not run(NOTE_HEAD),
          "(the negative control beside the 0x0742 case above: the fixture's "
          "own table carries that row and the fixture is clean)")

    # --- rule 3 ---------------------------------------------------------
    check("a citation past the end of its file is refused",
          run(NOTE_HEAD.replace("`vendor.cs:1-2`", "`vendor.cs:1-99`")))
    check("a citation to a file this repository does not hold is refused",
          run(NOTE_HEAD.replace("`vendor.cs:1-2`", "`nowhere/vendor.cs:1`")))
    check("a value the cited span does not carry is refused",
          run(NOTE_HEAD.replace("`SetCpuTccOffset` writes `1926`",
                                "`SetCpuTccOffset` writes `1927`")),
          "(the value is the claim, and a citation that lands beside a "
          "different one supports nothing")
    check("a hex address beside the claim is exempt",
          not run(NOTE_HEAD.replace("`SetCpuTccOffset` writes `1926`",
                                    "`SetCpuTccOffset` writes `1926`, which is "
                                    "`0x786`")),
          "(the negative control: this note's whole job is translating "
          "between a vendor that writes 1926 and an upstream that writes "
          "0x0786, and both ends are anchored by other rules")
    check("a claim the cited line carries on its own is not refused",
          not run(NOTE_HEAD.replace("`SetCpuTccOffset` writes `1926`",
                                    "writes `1926`")
                  .replace("`vendor.cs:1-2`", "`vendor.cs:2`")),
          "(the negative control for the span: a one-token claim does not need "
          "a two-line span, and a rule that demanded the whole claim on one "
          "line would refuse a correct citation")
    check("identifiers named in the wrong order are refused",
          run(NOTE_HEAD.replace("`SetCpuTccOffset` writes `1926`",
                                "`bApExist` then `SetCpuTccOffset` writes "
                                "`1926`")),
          "(order is part of the claim: the DSDT row says `APTN` is set before "
          "`APTC`, and a rule that only checked membership would not notice")

    # --- rule 4 ---------------------------------------------------------
    check("a value the capture does not carry is refused",
          run(NOTE_HEAD.replace("`0x00` | `snap.txt`", "`0x77` | `snap.txt`")))
    check("a value cited to the transition log is refused",
          any("transition log" in p for p in run(
              NOTE_HEAD.replace("`0x00` | `snap.txt`",
                                "`0x00` | `cycle-0700-07ff.csv`"))),
          "(the issue's own citation got this wrong, and it is the one place "
          "an overclaim would have entered as a citation rather than a "
          "sentence)")
    check("an address the cycle capture did move cannot be called unchanged",
          any("did not change" in p for p in run(NOTE_HEAD, cycles={"0X0786"})),
          "(the second half of the rule: `no` is a claim about the transition "
          "log and is checked against it")
    check("an address the cycle capture did move can be called changed",
          not any("change" in p for p in run(
              NOTE_HEAD.replace("`0x00` | `snap.txt` | `no` |",
                                "`0x00` | `snap.txt` | `yes` |"),
              cycles={"0X0786"})),
          "(the negative control for that half: the other way round, with the "
          "log saying yes, is a correct claim and has to stay green")
    check("an address the cycle capture never moved is not refused",
          not run(NOTE_HEAD),
          "(the negative control for the other half, beside the case above)")
    check("a `changed` cell that says neither yes nor no is refused",
          any("neither" in p for p in run(
              NOTE_HEAD.replace("`snap.txt` | `no` |", "`snap.txt` | `held` |"))))

    # --- rule 5 ---------------------------------------------------------
    check("a width the field list does not give is refused",
          any("widths" in p for p in run(
              NOTE_HEAD.replace("| `EC0` | `0x786` | `7` | `0-6` |",
                                "| `EC0` | `0x786` | `8` | `0-7` |"))))
    check("a field name the field list does not give is refused",
          any("the ASL names" in p for p in run(
              NOTE_HEAD.replace("| `APTC` | `EC0` |", "| `APTZ` | `EC0` |"))))
    check("bit positions that are not where the field list puts them are refused",
          any("bits" in p for p in run(
              NOTE_HEAD.replace("| `1` | `7-7` |", "| `1` | `0-1` |"))))
    check("a table that drops a field covering the byte is refused",
          any("the ASL names" in p for p in run(
              NOTE_HEAD.replace("| `APTN` | `EC0` | `0x786` | `1` | `7-7` |\n",
                                ""))),
          "(APTN is the enable bit, the second field of the byte, and a note "
          "describing only the first would read as if bit 7 were spare")
    check("a byte no field of the named field list covers is refused",
          any("not found by this method" in p for p in run(
              NOTE_HEAD.replace("| `0x786` |", "| `0x0790` |"))))
    check("a field list the ASL does not declare is refused",
          any("not found by this method" in p for p in run(
              NOTE_HEAD.replace("| `EC0` |", "| `NOSUCH` |"))),
          "(rather than falling back on some other device's list -- the "
          "fixture's first device covers 0x786 with UCSI, which is what an "
          "unbounded walk finds)")
    check("the other device's field at the same offset is not substituted",
          not run(NOTE_HEAD
                  .replace("| `APTN` | `EC0` | `0x786` | `1` | `7-7` |\n", "")
                  .replace("| `APTC` | `EC0` | `0x786` | `7` | `0-6` |",
                           "| `UCSI` | `XUSB` | `0x786` | `8` | `0-7` |")),
          "(the negative control: the derivation is right, it just has to be "
          "asked about the right device")
    check("a row with no field list or no byte is refused",
          any("needs the field list" in p for p in run(
              NOTE_HEAD.replace("| `APTC` | `EC0` | `0x786` |",
                                "| `APTC` |  |  |"))))

    # --- rule 6 ---------------------------------------------------------
    check("a cross-board claim carried as anything but not-established is refused",
          any("cross-board" in p for p in run(
              NOTE_HEAD.replace("the name is wrong on every board | cross-board "
                                "| not-established",
                                "the name is wrong on every board | cross-board "
                                "| confirmed-static"))))
    check("an upstream-use claim carried as anything but not-established is refused",
          any("upstream-use" in p for p in run(
              NOTE_HEAD.replace("| upstream reads `FAN_TURBO_SUPPORTED` | "
                                "upstream-use | not-established |",
                                "| upstream reads `FAN_TURBO_SUPPORTED` | "
                                "upstream-use | confirmed-static |"))))
    check("a kind outside the closed set is refused",
          any("kind" in p for p in run(
              NOTE_HEAD.replace("| this-board |", "| every-board |"))))
    check("a standing outside the closed set is refused",
          any("not one of" in p for p in run(
              NOTE_HEAD.replace("| not-established |",
                                "| probably-fine |"))))
    check("a claim about this board at a real standing is not refused",
          not run(NOTE_HEAD.replace(
              "| `0x0786` is the TCC offset here | this-board | "
              "hypothesis-agreeing-sources |",
              "| `0x0786` is the TCC offset here | this-board | "
              "confirmed-static |")),
          "(the negative control: rule 6 constrains the two open kinds only, "
          "and a rule that constrained every row would refuse the note's own "
          "findings")
    check("a standing table with no cross-board claim is refused",
          any("no cross-board claim" in p for p in run(
              NOTE_HEAD.replace("the name is wrong on every board | cross-board "
                                "| not-established |", ""))))
    check("a standing table with no upstream-use claim is refused",
          any("no upstream-use claim" in p for p in run(
              NOTE_HEAD.replace("| upstream reads `FAN_TURBO_SUPPORTED` | "
                                "upstream-use | not-established |", ""))))
    check("the note naming the declined gate in prose is not refused by rule 6",
          not run(NOTE_HEAD + "\nThe excerpt never shows FAN_TURBO_SUPPORTED "
                              "being read.\n"),
          "(the case that decides whether rule 6 survives a week: the note "
          "names the wrong gate in prose precisely to record that it is "
          "declining to claim it, and a rule that scanned prose would fire on "
          "its own explanation")
    check("the decline goes stale when an excerpt shows a read",
          any("gone stale" in p for p in run(
              NOTE_HEAD, sources={**sources, "upstream-excerpt.txt": {
                  **sources["upstream-excerpt.txt"],
                  8: "  200: if (value & FAN_TURBO_SUPPORTED)"}})),
          "(the one rule here a new fragment can falsify rather than an edit, "
          "which is why it is a rule and not a sentence")
    check("a read in an excerpt the note never cites still counts",
          any("other-excerpt.txt" in p for p in run(
              NOTE_HEAD, sources={**sources, "other-excerpt.txt": {
                  **sources["other-excerpt.txt"],
                  2: "  11: if (raw & FAN_TURBO_SUPPORTED)"}})),
          "(the fragment that would make the decline stale is exactly the one "
          "no row of the note points at, so a rule that scanned only the "
          "cited excerpts would miss it")

    # --- the tables, both ways ------------------------------------------
    for key in REQUIRED_TABLES:
        # Split on the header, case-insensitively: the note capitalises its
        # column heads and the key is the lowercased form of one.
        truncated = re.split(r"\|\s*" + re.escape(key) + r"\s", NOTE_HEAD,
                             flags=re.I)[0]
        check(f"a summary table sharing a prefix with {key!r} is not read as one",
              not any(key in p and "citation table row" in p
                      for p in run(NOTE_HEAD.replace(
                          "# A fixture",
                          "# A fixture\n\n| what upstream calls it | what this "
                          "tree shows |\n|---|---|\n| a summary row | prose |\n"))),
              "(a prefix match here would read this table as the citation "
              "table and refuse the note for a row that carries no citation")
        check(f"a note without its {key!r} table is refused",
              any("no table headed" in p for p in run(truncated)),
              "(a rule with no table to read has stopped checking, and "
              "reading that as a pass is how a gate stops gating)")

    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on any refusal (the gate's entry point); the "
                         "default run prints the same sweep and exits 0")
    ap.add_argument("--note", default=DEFAULT_NOTE,
                    help="the upstream-facing note this checks")
    ap.add_argument("--registers", default=DEFAULT_REGISTERS)
    ap.add_argument("--watch", default=DEFAULT_WATCH)
    ap.add_argument("--dsdt", default=DEFAULT_DSDT)
    ap.add_argument("--patches", default=PATCHES,
                    help="the directory holding the committed upstream "
                         "excerpts, globbed for `*/upstream-excerpt*.txt`")
    ap.add_argument("--self-test", action="store_true",
                    help="pin each rule against the mutation it catches")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not os.path.exists(args.note):
        print(f"{args.note} does not exist; there is no note to check",
              file=sys.stderr)
        return 1
    text = open(args.note).read()
    problems = note_problems(
        text, **load_inputs(args.note, args.registers, args.watch, args.dsdt,
                            args.patches))
    print(f"{len(table_rows(text, TBL_UPSTREAM))} upstream spelling(s) and "
          f"{len(table_rows(text, TBL_LIVE))} live value(s) cited, every one "
          f"read off a committed file rather than a transcription of one.")
    print("calibration rule: a cross-board or upstream-use claim may only be "
          "carried as not-established, and the FAN_TURBO_SUPPORTED decline is "
          "held against the excerpts rather than against the sentence.")
    report(problems)
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
