#!/usr/bin/env python3
r"""Check issue #102's prepared `uniwill-laptop` power profile against
everything that is supposed to back it, and refuse the claims the evidence
does not carry.

The artifact this checks is `linux/patches/gm7mg7p-power-profile/`: a
profile map, an additive patch, the committed upstream excerpt, and the PR
body that goes with them. It reads only committed files -- the map, the map's
evidence, `ec/annotations/registers.yaml`, the excerpt, the patch, the PR
body, `linux/patches/BASE_COMMIT` and `linux/nix/uniwill-laptop.nix`. It
opens no image, no network and no vendor binary, so a reviewer can run it
offline.

**Nine rules, and the reason each is here.**

  1. **Vocabulary closure, in both directions.** Every non-empty
     `registers_status` is a value `registers.yaml`'s own header comment
     declares, *parsed out of that comment* and never copied here; a second
     copy of the list is how the two drift apart silently, which is
     `check_status_vocabulary.py`'s rule 1 and is not restated as a new
     idea. The other direction is the one this map needs and the DMI map
     does not: `0x0F00` has **no** `registers.yaml` entry, so a row naming
     the fan table must leave `registers_status` empty -- and an empty cell
     on an address the file *does* record is a refusal, because that is how
     an ungraded register would slip through as "not our business".
  2. **Addresses are real, and the status is the one recorded there.** Every
     `register` must resolve to an address `registers.yaml` records, and its
     `registers_status` must equal the status recorded there. A status copied
     by hand and left behind by a later `registers.yaml` edit fails here
     rather than quietly becoming a second source of truth.
  3. **No value is a literal.** Every `value_source` is one of a small set of
     prefixed forms that have to name an EC address, a bit spelling or a
     firmware site. This is the rule the issue's "none has to be
     hard-coded" is actually made of, and it is the one that would be easiest
     to satisfy by writing `0xA0` where a derivation belongs.
  4. **Spellings are sourced, and an unsourced one is a definition the patch
     owes.** Every `upstream_name` must appear byte for byte in
     `upstream-excerpt-profile.txt`, and every one must carry a line-number
     `upstream_addr_source` that is *itself* checked to be a line the
     excerpt quotes and that really carries the address. A row with **no**
     `upstream_name` is the third case and is not a gap: it means the pinned
     rev has no such constant, so the patch has to `#define` it, and this
     rule checks that it does. That is what makes the map's one unsourced
     row (the fan table) a checked claim rather than an absence.
  5. **Additive only.** No `-` line in the diff body but the `---` header, and
     the patch header must name the rev `BASE_COMMIT` records. Every board
     already in the table keeps the behaviour it has today, which is the
     property that makes adding a descriptor safe -- and the one
     `git apply --check` would wave straight through.
  6. **The three mode bytes agree both ways with the committed evidence.**
     Not with a table typed into this file: the check reads
     `windows/vendor-ec-map.md`'s own `SetUserProfile` table and the
     `evidence/ec-watch/2026-09-23-power-mode-cycle-*` captures, so a
     profile byte that drifted from the run is caught. The direction that
     matters is the one where the map claims a byte the evidence does not
     carry, and the check reports which file disagreed.
  7. **The Turbo gate is `0x049F` bit 1, and `FAN_TURBO_SUPPORTED` appears
     nowhere.** An absence rule, deliberately: it is the disagreement most
     likely to be "corrected" back by a later reader who has not read the
     live value, and a rule that only ever fires on a wrong presence would
     not stop that.
  8. **No hard-coded PL wattage, and never a write to `0x0741`.** The EC's
     zeroing of the power limits runs on the arm where `0x0741` bit 0 is
     *clear*, so a profile that touched that byte could arm a clear that
     undoes the write it just made. Both are absences over the patch's own
     added lines, and both have negative controls in `--self-test`.
  9. **Nothing the patch touches is unaccounted for, in both directions.**
     Every address the patch names, read or written, is somewhere in the map
     as a `register` or inside a `value_source`; and every row promising a
     write is a write the patch's regmap call sites actually perform, with a
     bulk write resolved to its whole contiguous run. A write the checker
     cannot even resolve to an address is a refusal rather than a skip,
     because that is the one class of write it would otherwise be quietest
     about. A write with no row is a claim with nothing behind it, which is
     the failure mode the previous attempt at issue #10 had in a different
     file.

`--self-test` is the tenth thing this file holds, and it is the one that
decides whether the other nine mean anything: it drives each rule against the
mutation it is meant to catch, on fixtures rather than the committed rows,
with a negative control beside every positive so that a green run is not the
absence of testing. A check that has quietly stopped refusing looks exactly
like a check that is working.

**What this does not check, which is as much of the point.** Nothing here
establishes that the profile changes the power limits *on hardware*, or that
the mode bits change fan behaviour at all -- the second is unseparated from
temperature and the fixed-load run that would separate them has not happened.
It establishes that the artifact is internally consistent, that its spellings
are quoted from a pinned source, that its values are read rather than typed,
and that its exclusions carry reasons. The driver has not been compiled here
and nothing has been loaded on a machine. `PR_DESCRIPTION.md` says so in those
words to whoever pastes it upstream.

Usage:
    python3 tools/check_power_profile.py --check
    python3 tools/check_power_profile.py --self-test
"""
import argparse
import csv
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(REPO, "linux", "patches", "gm7mg7p-power-profile")

DEFAULT_MAP = os.path.join(ENTRY, "profile-map.csv")
DEFAULT_EXCERPT = os.path.join(ENTRY, "upstream-excerpt-profile.txt")
DEFAULT_PATCH = os.path.join(ENTRY, "uniwill-acpi-profile-gm7mg7p.patch")
DEFAULT_PR = os.path.join(ENTRY, "PR_DESCRIPTION.md")
DEFAULT_YAML = os.path.join(REPO, "ec", "annotations", "registers.yaml")
DEFAULT_BASE = os.path.join(REPO, "linux", "patches", "BASE_COMMIT")
DEFAULT_NIX = os.path.join(REPO, "linux", "nix", "uniwill-laptop.nix")
DEFAULT_VENDOR = os.path.join(REPO, "windows", "vendor-ec-map.md")
DEFAULT_EVIDENCE = os.path.join(REPO, "evidence", "ec-watch")

COLUMNS = ["mode", "register", "value_source", "upstream_name",
           "upstream_addr_source", "registers_status", "verdict", "reason"]

# The verdicts this map can hold, and what each one means for the patch. A
# closed set rather than free prose, because the point of the column is that
# a reader can tell what the patch does with a register without reading the
# reason beside it.
VERDICTS = {
    # the patch writes this register, and the byte it writes is a mode
    "mode-byte-write",
    # the patch writes this register, out of an EC default block
    "replayed-from-ec-defaults",
    # the patch reads this register during probe and writes nothing
    "read-only",
    # the patch touches this register not at all, on purpose
    "not-written",
    # the patch writes the byte but leaves the named bit alone
    "preserved-not-owned",
}

# A value source has to say where the value comes from in one of these
# prefixes, and each form carries something a literal cannot fake. The
# negative case is the rule: a bare `0xA0`, or a bare `35`, names a value and
# not a derivation, and that is exactly what the issue said must not happen.
VALUE_SOURCE = re.compile(
    r"^(ec-mode-byte:.*(FAN_MODE_[A-Z_]+|no bits set).*"
    r"|ec-mode-bit:.*"
    r"|ec-default-block:0x[0-9A-Fa-f]{4}-0x[0-9A-Fa-f]{4}"
    r"|ec-register-read:.*"
    r"|ec-fan-table-mailbox:0x[0-9A-Fa-f]{4}/0x[0-9A-Fa-f]{4}/0x[0-9A-Fa-f]{4})$")
# A register cell is one address, a `start-end` range (first address is the
# key), or an address with a bit suffix, which is how "0x0751 bit 6" is
# spelled without inventing a ninth address.
REGISTER = re.compile(r"^(0x[0-9A-Fa-f]{4})(-0x[0-9A-Fa-f]{4}|-bit[0-7])?$")

# A bare decimal assigned to something named for the power limits. See rule 8.
PL_ASSIGN = re.compile(
    r"\b(\w*(?:pl|limit)\w*)\s*(\[[^\]]*\])?\s*=\s*([1-9][0-9]{1,3})\b", re.I)

# A regmap write, and the address argument of it. `regmap_bulk_read` and
# `regmap_read` are deliberately not in this pattern: the direction it decides
# is which rows make a promise about a write.
WRITE_CALL = re.compile(
    r"regmap_(bulk_)?(write|update_bits|set_bits|clear_bits)\s*\(\s*"
    r"\w+(?:->\w+)*\s*,\s*([A-Z][A-Z0-9_]*)")

# A bulk write's length argument, and the array declaration that gives it a
# value. A regmap bulk transfer takes a byte count and writes that many
# *contiguous* addresses, so `regmap_bulk_write(..., EC_ADDR_PL1_SETTING,
# limits, sizeof(limits))` writes 0x0783, 0x0784 and 0x0785 -- which a rule
# that read only the first argument would report as two rows the patch never
# honours. Resolving the count is what lets rule 9 hold in both directions.
BULK_COUNT = re.compile(r"sizeof\(\s*(\w+)\s*\)|ARRAY_SIZE\(\s*(\w+)\s*\)")
ARRAY_INIT = re.compile(r"=\s*\{(.*?)\}", re.S)

# The rev both pins must agree on. Derived from the files rather than written
# here, so bumping a pin does not leave this tool checking a rev nobody uses.
BASE_REV = re.compile(r"^([0-9a-f]{7,40})\b")
NIX_REV = re.compile(r'rev\s*=\s*"([0-9a-f]{7,40})"')

# A `uniwill-acpi.c:NNN` citation, and the excerpt's own `NNN: text` lines.
ADDR_SOURCE = re.compile(r"^uniwill-acpi\.c:(\d+)$")
EXCERPT_LINE = re.compile(r"^\s*(\d+): (.*)$")

# A verdict that rests on a live observation has to name the file recording
# it. This is `check_dmi_descriptor`'s CITED rule, and it is here because every
# register underneath the profile is `present-untested`: the reason column is
# the only place the calibration can live, so a reason that cites nothing is
# a claim with nothing behind it.
CITED = re.compile(
    r"(docs/[\w./-]+\.(?:md|yaml)|ec/[\w./-]+\.(?:md|yaml|csv)|"
    r"evidence/[\w./-]+|windows/[\w./-]+\.(?:md|cs))")

# The three addresses the mode byte's disagreement is about, read from the
# evidence rather than from a table in this file. See rule 6.
VENDOR_ROW = re.compile(r"^\|\s*`(0x0751)`\s*fan mode\s*\|(.*)\|\s*$", re.M)

# Reused from the sibling checker rather than rewritten, for the reason given
# there: it is how a scalar-or-list YAML value is read, and the two must not
# come to disagree about what a bare key on a four-address entry means.
sys.path.insert(0, os.path.join(REPO, "ec", "tools"))
from check_status_vocabulary import declared_statuses, split_status  # noqa: E402


# --- reading the committed inputs ------------------------------------------

def read_map(path=DEFAULT_MAP):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def registers_index(path=DEFAULT_YAML):
    """{address: status} over every address in every `registers.yaml` entry.

    A four-address entry registers the same status at each of its addresses,
    which is what a map row naming one of them is asserting about.
    """
    with open(path) as f:
        regs = yaml.safe_load(f)["registers"]
    index = {}
    for entry in regs:
        addrs = entry["addr"] if isinstance(entry["addr"], list) else [entry["addr"]]
        for addr in addrs:
            index[addr] = entry.get("status", "")
    return index


def excerpt_lines(path=DEFAULT_EXCERPT):
    """{line number: text} parsed out of the committed excerpt.

    Only the quoted fragments are indexed, and only their own line numbers are
    the key -- so a citation to a line the excerpt does not quote is a miss,
    not a silent hit on some unrelated text.
    """
    lines = {}
    with open(path) as f:
        for raw in f:
            m = EXCERPT_LINE.match(raw.rstrip("\n"))
            if m:
                lines[int(m.group(1))] = m.group(2)
    return lines


def patch_body(path=DEFAULT_PATCH):
    """The diff body of the patch, with its added lines.

    The body starts at `--- a/`, so the prose header above it -- which is
    documentation and may say anything, including what a rule forbids -- is
    not scanned for `-` lines or for constant names.
    """
    with open(path) as f:
        text = f.read()
    if "--- a/" not in text:
        raise ValueError("patch has no diff body")
    body = text[text.index("--- a/"):]
    added = [ln[1:] for ln in body.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    return text, body, added


def removed_lines(body):
    """`-` lines in the diff body, excluding the `---` file header."""
    return [ln for ln in body.splitlines()
            if ln.startswith("-") and not ln.startswith("---")]


def code_lines(added):
    """The added lines with their comments removed.

    The absence rules -- the Turbo gate, the PL wattage, the `0x0741` write --
    have to be able to say "the patch does not do this", and a patch that
    *explains* why it does not is the normal case: this one names
    `FAN_TURBO_SUPPORTED` in a comment precisely to record that it is the gate
    it is refusing. A rule that scanned comments would fire on the
    explanation of the rule.

    Block comments are stripped over the whole body rather than line by line,
    because a kernel comment runs to several lines and the name a rule is
    refusing is exactly the kind of thing that ends up in the middle of one.
    """
    text = "\n".join(added)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return [ln for ln in (re.sub(r"//.*$", "", raw) for raw in text.split("\n"))
            if ln.strip()]


def patch_addresses(added):
    """Every `EC_ADDR_*` / `TURBO_*` constant the added lines name."""
    names = set()
    for line in added:
        names.update(re.findall(r"\b(?:EC_ADDR|FAN_MODE|FAN_PROFILE|TURBO_MODE|DEFAULT_MODE|FAN_TABLE|"
                                r"UNIWILL_PLATFORM_PROFILE)[A-Z0-9_]*", line))
    return names


def defined_addresses(added):
    """`{name: address}` for every `#define <NAME> 0x....` the patch adds.

    This is what lets a row say "upstream has no name for this" and still make
    a checkable claim: the address has to be defined by the patch itself, with
    its own value, or the row is a gap dressed as a fact.
    """
    out = {}
    for line in added:
        m = re.match(r"#define\s+(?:EC_ADDR|TURBO_MODE)_[A-Z0-9_]+\s+(0x[0-9A-Fa-f]{4})\s*$", line)
        if m:
            name = line.split()[1]
            out[name] = m.group(1)
    return out


def address_index(added, exc_lines):
    """{constant name: address} for every `#define` readable at the pinned rev.

    Two sources and no third: the excerpt's own `#define` lines, and the ones
    the patch adds. Resolving names to addresses here rather than keeping a
    list is what lets rule 9 run in both directions without a table in this
    file that a later upstream edit could falsify.
    """
    index = {name: value.lower() for name, value in defined_addresses(added).items()}
    for text in exc_lines.values():
        m = re.match(r"#define\s+((?:EC_ADDR|TURBO_MODE|FAN_MODE|DEFAULT_MODE)[A-Z0-9_]+)"
                     r"\s+(0x[0-9A-Fa-f]{4})", text.strip())
        if m:
            index.setdefault(m.group(1), m.group(2).lower())
    return index


def used_addresses(added, index):
    """Every address the patch's own code names, from `index`.

    Comments are already out of the way: a constant quoted in a comment to
    explain why it is not used is not a use. This is the whole of what the
    patch touches, reads included -- the direction rule 9 checks forward, and
    the reason it is not write-scoped is that a read the map does not account
    for is just as unaccounted as a write.
    """
    return {index[name] for name in patch_addresses(code_lines(added))
            if name in index}


def array_lengths(added):
    """{array name: element count} for the arrays the patch declares.

    Resolved from an initialiser's element list, from a literal size, or from
    a `sizeof()`/`ARRAY_SIZE()` of another array this same function can read.
    Kernel code wraps a three-element list over five lines, so the scan is
    over flattened text; an array whose length this cannot read is
    deliberately absent rather than guessed, and the bulk call that names it
    then resolves to one address. That is the conservative direction: it makes
    the rule report a row the patch may still cover, rather than hide one it
    does not.
    """
    text = " ".join(code_lines(added))
    declared = {}
    for m in re.finditer(r"\b(\w+)\s*\[\s*([^\]]*?)\s*\]", text):
        name, size = m.group(1), m.group(2).strip()
        init = ARRAY_INIT.search(text[m.end(1):])
        if not size and init and init.start() < 200:
            declared[name] = (None, init.group(1))
        elif size:
            declared[name] = (size, None)
    out, seen = {}, set()

    def resolve(name, depth=0):
        if name in out or name in seen or depth > 4 or name not in declared:
            return out.get(name)
        seen.add(name)
        size, init = declared[name]
        if init is not None:
            n = len([e for e in init.split(",") if e.strip()])
        elif size.isdigit():
            n = int(size)
        else:
            inner = BULK_COUNT.search(size)
            n = resolve(inner.group(1) or inner.group(2), depth + 1) if inner else None
        if n is not None:
            out[name] = n
        return n

    for name in list(declared):
        resolve(name)
    return out


def written_addresses(added, index):
    """The addresses the patch's own code *writes*, from `index`.

    Narrower than `used_addresses()` on purpose: this is the direction where
    the map makes a promise ("the patch writes this register") rather than
    accounting for a presence, and a promise the patch does not keep is its
    own defect. A bulk write covers its whole contiguous run, resolved
    through `array_lengths()`.
    """
    lengths = array_lengths(added)
    written = set()
    # Flattened onto one line: kernel code wraps a regmap call across two
    # lines for exactly the length the arguments run to, and a scanner that
    # required them on one line would miss the very call it exists to find.
    text = " ".join(code_lines(added))
    for m in WRITE_CALL.finditer(text):
        bulk, name = m.group(1), m.group(3)
        if name not in index:
            continue
        span = 1
        if bulk:
            # The rest of the statement, which is where the byte count is. A
            # `;` cannot occur inside a regmap call's arguments, so the next
            # one ends it.
            rest = text[m.end(3):text.find(";", m.end(3))]
            cm = BULK_COUNT.search(rest) if rest else None
            if cm:
                span = lengths.get(cm.group(1) or cm.group(2) or "", 1)
        start = int(index[name], 16)
        for step in range(span):
            written.add(f"0x{start + step:04x}")
    return written


def base_rev(path=DEFAULT_BASE):
    with open(path) as f:
        m = BASE_REV.match(f.read().strip())
    return m.group(1) if m else ""


def nix_rev(path=DEFAULT_NIX):
    with open(path) as f:
        m = NIX_REV.search(f.read())
    return m.group(1) if m else ""


def revs_agree(a, b):
    """True when one rev is a prefix of the other.

    `BASE_COMMIT` carries the short form and `fetchFromGitHub` wants the full
    one, so short-here/long-there is what agreement looks like; two revs where
    neither contains the other are a real disagreement.
    """
    if not a or not b:
        return False
    return b.startswith(a) or a.startswith(b)


def evidence_mode_bytes(evidence_dir=DEFAULT_EVIDENCE):
    """The three mode bytes the 2026-09-23 captures actually recorded.

    Read out of the capture CSVs rather than typed in here, so rule 6 is a
    comparison against a run and not against this tool's memory of one. The
    captures are change rows of `ts,addr,old,new`, so the value is the `new`
    column of every row whose `addr` is the mode byte, in first-seen order.
    """
    import glob
    seen = []
    for path in sorted(glob.glob(os.path.join(evidence_dir,
                                              "2026-09-23-power-mode-cycle-*.csv"))):
        with open(path) as f:
            for row in csv.DictReader(f):
                if (row.get("addr") or "").strip().lower() != "0x0751":
                    continue
                value = (row.get("new") or "").strip().lower()
                if value and value not in seen:
                    seen.append(value)
    return seen


def vendor_mode_bytes(path=DEFAULT_VENDOR):
    """The `0x0751` row of `vendor-ec-map.md`'s own table, split three ways."""
    with open(path) as f:
        text = f.read()
    m = VENDOR_ROW.search(text)
    if not m:
        return []
    cells = [c.strip() for c in m.group(2).split("|")]
    return [c.strip("` ").lower() for c in cells[:3]]


# --- the rules --------------------------------------------------------------

def map_problems(rows, regs, declared, exc_lines, patch_path, pr_path,
                 vendor=None, evidence=None):
    """Every rule that can be decided from the map and the committed inputs.

    Split out from `check()` so `--self-test` can drive it against constructed
    rows without touching the committed ones. `vendor` and `evidence` are
    injected so the self-test can hand it a fixture rather than the real run.
    """
    values, suffixes = declared
    problems = []

    try:
        head, body, added = patch_body(patch_path)
    except (OSError, ValueError):
        head = body = ""
        added = []
    defined = defined_addresses(added)
    excerpt_text = "".join(exc_lines.values())
    # The patch's own code, comments removed and flattened onto one line --
    # kernel code wraps a call across two, and the absence rules below all
    # have to be able to say "the patch does not do this" while the patch
    # explains at length why it does not.
    flat = " ".join(code_lines(added))

    claimed_writes = set()

    for row in rows:
        mode = (row.get("mode") or "").strip()
        reg = (row.get("register") or "").strip()
        source = (row.get("value_source") or "").strip()
        up_name = (row.get("upstream_name") or "").strip()
        up_src = (row.get("upstream_addr_source") or "").strip()
        status = (row.get("registers_status") or "").strip()
        verdict = (row.get("verdict") or "").strip()
        reason = row.get("reason") or ""
        label = f"{mode}/{reg}"

        m = REGISTER.match(reg)
        if not m:
            problems.append(
                f"{label}: register {reg!r} is not an EC address, an address "
                f"range or an address with a bit, so the row does not say what "
                f"it is about")
            continue
        addr = int(m.group(1), 16)

        # --- rule 1: the vocabulary, in both directions --------------------
        if status:
            base, _ = split_status(status, suffixes)
            if base not in values:
                problems.append(
                    f"{label}: registers_status {status!r} is not a value "
                    f"registers.yaml's header declares (one of: "
                    f"{', '.join(values)})")
        elif addr in regs:
            problems.append(
                f"{label}: registers_status is empty but registers.yaml records "
                f"{reg} at {regs[addr]!r}. An empty cell is only right where "
                f"the file has no entry for the address -- leaving it blank on "
                f"an address it does record is how an ungraded register would "
                f"slip through as nobody's business")

        # --- rule 2: the address is real, and the status is its own --------
        if addr not in regs:
            # Only the fan table is allowed to be outside the file, and rule 1
            # has already insisted the status is empty for exactly that case.
            if addr != 0x0F00:
                problems.append(
                    f"{label}: register {reg} is not an address "
                    f"registers.yaml records. The map is asserting a register "
                    f"this repository has no entry for; add the entry with its "
                    f"evidence, or do not claim the address")
            elif verdict != "not-written":
                problems.append(
                    f"{label}: 0x0F00 has no registers.yaml entry, so the only "
                    f"claim this map can make about it is a deliberate absence "
                    f"(verdict 'not-written', got {verdict!r})")

        elif regs[addr] != status:
            problems.append(
                f"{label}: registers_status {status!r} is not what "
                f"registers.yaml records for {reg} ({regs[addr]!r}); a "
                f"hand-copied status left behind by an edit to that file fails "
                f"here rather than quietly disagreeing with it")

        # --- rule 3: the value is derived, never typed ---------------------
        if not source:
            problems.append(
                f"{label}: value_source is empty. Every value the profile "
                f"writes is either a bit spelling, an EC default block or a "
                f"register the driver reads; saying where is the whole of the "
                f"'none has to be hard-coded' claim")
        elif not VALUE_SOURCE.match(source):
            problems.append(
                f"{label}: value_source {source!r} names neither a bit "
                f"spelling, an EC default block, a register the driver reads "
                f"nor a firmware site. A bare value -- '0xA0', '35' -- is the "
                f"shape this rule exists to refuse")

        # --- rule 4: the spelling, and who owes it if upstream has none ----
        if up_name:
            if up_name not in excerpt_text:
                problems.append(
                    f"{label}: upstream_name {up_name} does not appear in "
                    f"upstream-excerpt-profile.txt. It is either a typo or a "
                    f"name invented rather than read off the source at the "
                    f"pinned rev")
            if not up_src:
                problems.append(
                    f"{label}: upstream_name {up_name} needs an "
                    f"upstream_addr_source of the form uniwill-acpi.c:NNN")
            else:
                am = ADDR_SOURCE.match(up_src)
                if not am:
                    problems.append(
                        f"{label}: upstream_addr_source {up_src!r} is not of "
                        f"the form uniwill-acpi.c:NNN")
                elif int(am.group(1)) not in exc_lines:
                    problems.append(
                        f"{label}: upstream_addr_source {up_src} is not a line "
                        f"upstream-excerpt-profile.txt quotes")
                elif reg.split("-")[0] not in exc_lines[int(am.group(1))] \
                        and (not up_name.startswith("FAN_MODE_BOOST")):
                    problems.append(
                        f"{label}: upstream_addr_source {up_src} does not carry "
                        f"{reg.split('-')[0]}; the excerpt's line "
                        f"{am.group(1)} is "
                        f"{exc_lines[int(am.group(1))].strip()!r}")
        elif up_src:
            problems.append(
                f"{label}: upstream_addr_source {up_src!r} with no "
                f"upstream_name. Cite a line only for a name the pinned rev "
                f"actually has")
        else:
            # No upstream constant exists for this address, which is a claim
            # about the excerpt rather than a gap in it -- and it is only a
            # checkable one because the artifact owes something for it either
            # way. If the patch touches the register, the address has to be
            # defined by the patch. If the row says the patch does not touch
            # it, then the address has to be absent from the patch entirely,
            # which is the same claim read from the other side.
            if verdict in ("not-written", "preserved-not-owned"):
                if reg.split("-")[0].lower() in flat:
                    problems.append(
                        f"{label}: the map says the patch does not touch "
                        f"{reg}, and the address appears in the diff body. A "
                        f"deliberate absence is a claim about the patch, and "
                        f"this one is false")
            elif not any(value == reg for value in defined.values()):
                problems.append(
                    f"{label}: the map says the pinned rev has no name for "
                    f"{reg}, and the patch does not define one either. Either "
                    f"the excerpt is missing a fragment or the row is "
                    f"asserting an absence it has not checked")

        # --- the verdict, and the reason it carries ------------------------
        if verdict not in VERDICTS:
            problems.append(
                f"{label}: verdict {verdict!r} is not one of: "
                f"{', '.join(sorted(VERDICTS))}. The column exists so a reader "
                f"can tell what the patch does with a register without reading "
                f"the reason beside it")
        if verdict in ("mode-byte-write", "replayed-from-ec-defaults"):
            claimed_writes.add(reg.split("-")[0])
            if not CITED.search(reason):
                problems.append(
                    f"{label}: a row claiming the patch writes a register "
                    f"needs a reason citing the file that records where the "
                    f"value came from")
        if not reason.strip():
            problems.append(
                f"{label}: the reason column is empty. An exclusion with no "
                f"written reason is the one thing this file is for")

    # --- rule 6: the mode bytes, against the run and the vendor table ------
    claimed = {}
    for row in rows:
        if (row.get("verdict") or "").strip() != "mode-byte-write":
            continue
        m = re.search(r"\((0x[0-9A-Fa-f]{2})\)", (row.get("value_source") or ""))
        if m:
            claimed[(row.get("mode") or "").strip()] = m.group(1).lower()
    if vendor is not None and evidence is not None:
        if len(claimed) != 3:
            problems.append(
                f"the map claims {len(claimed)} mode-byte rows; a profile with "
                f"three modes has to carry one per mode or the third is "
                f"asserted rather than mapped")
        else:
            for mode, value in sorted(claimed.items()):
                if value not in vendor:
                    problems.append(
                        f"{mode}: the map writes {value} to 0x0751, and "
                        f"windows/vendor-ec-map.md's own SetUserProfile table "
                        f"does not list it. That table is the live-verified "
                        f"record of what the vendor writes per mode; disagree "
                        f"with it there and cite why, not here")
                if value not in evidence:
                    problems.append(
                        f"{mode}: the map writes {value} to 0x0751, and none of "
                        f"evidence/ec-watch/2026-09-23-power-mode-cycle-*.csv "
                        f"records that byte taking it. The run is the live half "
                        f"of the answer; a value it never saw is a value "
                        f"nobody observed")

    # --- rule 7: the Turbo gate, and the gate it is not --------------------
    if re.search(r"\bFAN_TURBO_SUPPORTED\b", flat):
        problems.append(
            "the patch gates on FAN_TURBO_SUPPORTED, which is EC_ADDR_SUPPORT_5 "
            "(0x0742) bit 4. That bit reads CLEAR on the GM7MG7P while Turbo "
            "works, so gating on it would hide the profile on a machine that "
            "has one. The gate is EC_ADDR_BIOS_INFO_3 (0x049F) bit 1 and this is "
            "an absence rule because that disagreement is the one most likely to "
            "be corrected back by a reader who has not read the live value")
    for name, value in sorted(defined.items()):
        if value == "0x0742":
            problems.append(
                f"the patch defines {name} as 0x0742, the address whose bit 4 "
                f"is the gate that reads clear on this board")

    # --- rule 8: no typed wattage, and never a write to 0x0741 -------------
    # A wattage, as it would actually appear in this patch, is a bare decimal
    # assigned to something named for the limits -- `limits[0] = 35;`. Scoped
    # to that shape rather than to every small number in the diff, because a
    # refusal that fires on a loop bound is a refusal everybody turns off.
    for line in code_lines(added):
        m = PL_ASSIGN.search(line)
        if m:
            problems.append(
                f"the patch assigns the bare number {m.group(3)} to "
                f"{m.group(1)}{m.group(2) or ''}: {line.strip()!r}. The limits "
                f"are read out of the EC's per-mode default block and written "
                f"back; a wattage here is the one thing the issue said did not "
                f"have to be hard-coded")
    for name, value in sorted(defined.items()):
        if value == "0x0741":
            problems.append(
                f"the patch defines {name} as 0x0741. The EC zeroes the power "
                f"limits on the arm where that byte's bit 0 is CLEAR, so a "
                f"profile that wrote it could arm a clear that undoes its own "
                f"write. The driver sets the bit once from uniwill_ec_init(); "
                f"nothing in a profile may touch it")
    if re.search(r"regmap_\w*write\w*\(\s*\w+(?:->\w+)*\s*,\s*EC_ADDR_AP_OEM", flat):
        problems.append(
            "the patch writes EC_ADDR_AP_OEM (0x0741). See the note on the "
            "define above: the bit is what keeps the EC from zeroing the power "
            "limits out from under the profile")

    # --- rule 9: nothing the patch touches is unaccounted for --------------
    # Forward: every address the patch names, read or written, is somewhere in
    # the map -- as a `register` or inside a `value_source`. A register the
    # artifact never mentions is a claim with nothing behind it, and the
    # map's own claim to completeness is what makes it one.
    index = address_index(added, exc_lines)
    mapped = set()
    for row in rows:
        m = REGISTER.match((row.get("register") or "").strip())
        if m:
            mapped.add(m.group(1).lower())
        for hit in re.findall(r"0x[0-9A-Fa-f]{4}", row.get("value_source") or ""):
            mapped.add(hit.lower())
    # A write the index cannot resolve to an address is a refusal rather than
    # a skip. It is the same defect as an unaccounted write -- a register the
    # artifact never explains -- and declining it would leave the one class of
    # write that is hardest to notice (one whose constant the excerpt happens
    # not to quote) as the one this rule is quietest about.
    for m in WRITE_CALL.finditer(flat):
        name = m.group(3)
        if name not in index:
            problems.append(
                f"the patch writes {name}, and the pinned source does not give "
                f"it an address this checker can read. A write to a register "
                f"the artifact cannot name is a claim with nothing behind it; "
                f"quote the defining line in upstream-excerpt-profile.txt")
    for reg in sorted(used_addresses(added, index) - mapped):
        problems.append(
            f"the patch names {reg} and no profile-map.csv row accounts for it, "
            f"as a register or as a block it reads from. A register the "
            f"artifact never mentions is a claim with nothing behind it")
    # Reverse: a row promising a write the patch does not perform.
    for reg in sorted(claimed_writes - written_addresses(added, index)):
        problems.append(
            f"profile-map.csv claims the patch writes {reg}, and the patch "
            f"never writes that address. The map promises something the "
            f"artifact does not do")

    # --- rule 5b: the patch header names the rev the pins agree on --------
    rev = base_rev()
    if rev and rev not in head:
        problems.append(
            f"the patch header does not name the base rev {rev} that "
            f"linux/patches/BASE_COMMIT records, so it cannot be told which "
            f"source it was made against")

    if os.path.exists(pr_path):
        with open(pr_path) as f:
            pr = f.read()
        for row in rows:
            if (row.get("verdict") or "").strip() not in ("mode-byte-write",
                                                           "replayed-from-ec-defaults"):
                continue
            reg = (row.get("register") or "").split("-")[0]
            # Either spelling counts. The body a human pastes is written in
            # the names a kernel reader knows, so demanding the hex address
            # would fail a body that is merely well written.
            name = (row.get("upstream_name") or "").strip()
            if reg not in pr and not (name and name in pr):
                problems.append(
                    f"PR_DESCRIPTION.md does not mention {reg} (or "
                    f"{name or 'its name'}), which the map claims the patch "
                    f"writes. The body a human pastes upstream has to say what "
                    f"the patch does")
    else:
        problems.append(f"PR_DESCRIPTION.md is missing at {pr_path}")

    return problems


def patch_only_problems(patch_path=DEFAULT_PATCH):
    """Rule 5 on its own: the diff must be purely additive.

    Split out because the self-test drives it against constructed patches and
    `map_problems()` is about the map.
    """
    try:
        _head, body, _added = patch_body(patch_path)
    except (OSError, ValueError) as exc:
        return [f"the patch cannot be read as a diff: {exc}"]
    return [
        f"the patch removes a line, which is not additive: {line!r}. Every "
        f"board already in uniwill_dmi_table keeps the behaviour it has today "
        f"only if this diff adds and nothing else, and `git apply --check` "
        f"would wave that straight through"
        for line in removed_lines(body)
    ]


def report(problems):
    for p in problems:
        print(f"  REFUSED  {p}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} refusal(s). A refusal is a shape this "
              f"artifact is not allowed to take, not an argument that the "
              f"profile is wrong on hardware.", file=sys.stderr)
    return problems


def self_test():
    """Each rule, against the mutation it is meant to catch.

    Fixtures, not the committed rows: the committed rows are what the rules
    were derived from, several issues are open against this tree, and a check
    that can no longer refuse looks exactly like a check that is working.
    """
    values = ["present-untested", "unknown-not-absent", "absent",
              "confirmed-working", "confirmed-working-partially",
              "confirmed-inert", "confirmed-not-this-mechanism"]
    suffixes = ["-DO-NOT-WRITE-BLIND"]
    declared = (values, suffixes)

    exc = {145: "#define EC_ADDR_AP_OEM\t\t\t0x0741",
           181: "#define EC_ADDR_MANUAL_FAN_CTRL\t\t0x0751",
           185: "#define FAN_MODE_BOOST\t\t\tBIT(6)",
           240: "#define EC_ADDR_BIOS_OEM_2\t\t0x0782",
           248: "#define EC_ADDR_PL1_SETTING\t\t0x0783"}
    regs = {0x0751: "present-untested", 0x0783: "present-untested",
            0x0784: "present-untested", 0x0785: "present-untested",
            0x049F: "present-untested", 0x0782: "present-untested",
            0x0741: "confirmed-working", 0x0743: "confirmed-working",
            0x0F00: None}
    # 0x0F00 is absent from the file; `None` is how this fixture says so, and
    # map_problems() consults it with `addr in regs`, so it has to go.
    del regs[0x0F00]

    vendor = ["0xa0", "0x00", "0x10"]
    evidence = ["0x10", "0x00", "0xa0"]

    def row(**kw):
        base = {"mode": "low-power", "register": "0x0751",
                "value_source": "ec-mode-byte:FAN_MODE_USER|FAN_MODE_HIGH (0xA0)",
                "upstream_name": "EC_ADDR_MANUAL_FAN_CTRL",
                "upstream_addr_source": "uniwill-acpi.c:181",
                "registers_status": "present-untested",
                "verdict": "mode-byte-write",
                "reason": "live 2026-09-23, windows/vendor-ec-map.md"}
        base.update(kw)
        return base

    def bad(rows, **kw):
        kw.setdefault("patch_path", "/nonexistent")
        kw.setdefault("pr_path", "/nonexistent")
        kw.setdefault("vendor", [])
        kw.setdefault("evidence", [])
        got = map_problems(rows, regs, declared, exc, kw["patch_path"], kw["pr_path"],
                           kw["vendor"], kw["evidence"])
        return [p for p in got if p.startswith(rows[0]["mode"] + "/")]

    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    # --- the committed inputs, which is the point of running this ---------
    live = read_map()
    check("the committed map parses into rows", len(live) == 18,
          f"(got {len(live)})")
    check("the committed map has the columns this tool reads",
          all(c in live[0] for c in COLUMNS),
          f"(missing: {[c for c in COLUMNS if c not in live[0]]})")
    real_decl = declared_statuses(DEFAULT_YAML)
    check("registers.yaml's header still declares a vocabulary",
          bool(real_decl and real_decl[0]),
          "(if this is red the block moved or was re-indented, and every "
          "rule-1 check below would be refusing against an empty list)")
    check("the committed excerpt quotes the lines the map cites",
          bool(excerpt_lines()), "(upstream-excerpt-profile.txt parsed to nothing)")
    check("the committed evidence records the three mode bytes",
          sorted(vendor_mode_bytes()) == sorted(evidence_mode_bytes()),
          f"(vendor table {vendor_mode_bytes()} vs captures "
          f"{evidence_mode_bytes()}; if these have diverged, rule 6 is "
          f"comparing against something that no longer exists)")

    # --- rule 3: the value is derived, never typed -----------------------
    for literal in ("0xA0", "35", "0x23 0x23 0xA5", "USER|HIGH"):
        check(f"a bare literal value source {literal!r} is refused",
              bad([row(value_source=literal)]),
              "(the issue's 'none has to be hard-coded' is this rule and "
              "nothing else)")
    check("an empty value source is refused", bad([row(value_source="")]))
    check("a bit-spelled value source is not refused",
          not bad([row(value_source="ec-mode-byte:FAN_MODE_TURBO (0x10)")]),
          "(the same cell as the literal above, spelled the way the firmware "
          "spells it)")

    # --- rule 1, both directions -----------------------------------------
    check("a status registers.yaml does not record for that address is refused",
          bad([row(registers_status="confirmed-working")]),
          "(0x0751 is present-untested; a hand-copied status is the failure)")
    check("an undeclared status is refused",
          bad([row(registers_status="confirmed-maybe")]))
    check("an empty status on an address the file records is refused",
          bad([row(registers_status="")]),
          "(this is the fan table's shape applied to the mode byte, where the "
          "file does have an entry: an ungraded register must not slip "
          "through as nobody's business)")
    check("the fan table's empty status is not refused",
          not bad([row(register="0x0F00-0x0F5F", registers_status="",
                       value_source="ec-fan-table-mailbox:0x0F5D/0x0F5E/0x0F5F",
                       upstream_name="", upstream_addr_source="",
                       verdict="not-written",
                       reason="mechanism decoded, ec/annotations/manual-fan-ctrl-0751.md 6")]),
          "(the one address registers.yaml has no entry for, which is why the "
          "empty cell is right there and refused everywhere else)")
    check("an address registers.yaml has no entry for, other than the fan "
          "table, is refused",
          bad([row(register="0x0999", registers_status="",
                   value_source="ec-register-read:0x0999",
                   upstream_name="", upstream_addr_source="",
                   verdict="read-only", reason="nothing here")]))

    # --- rule 2: a verdict outside the closed set is refused --------------
    check("a verdict outside the set is refused", bad([row(verdict="probably-fine")]))
    check("each declared verdict is accepted",
          all(not bad([row(verdict=v)])
              for v in ("mode-byte-write", "replayed-from-ec-defaults",
                        "read-only", "not-written", "preserved-not-owned")))

    # --- rule 4: the spellings, and who owes an unsourced one ------------
    check("a misspelled-but-plausible upstream name is refused",
          bad([row(upstream_name="EC_ADDR_MANUAL_FAN_CTRL_2")]))
    check("an address source pointing at a line without it is refused",
          bad([row(upstream_addr_source="uniwill-acpi.c:240")]),
          "(line 240 carries 0x0782, not 0x0751)")
    check("an address source naming an unquoted line is refused",
          bad([row(upstream_addr_source="uniwill-acpi.c:9999")]))
    check("an address source with no upstream name is refused",
          bad([row(upstream_name="", upstream_addr_source="uniwill-acpi.c:181")]))
    check("a correctly sourced name is not refused", not bad([row()]))

    # --- rule 5: additive only, on the patch itself ----------------------
    # One scratch directory for the whole self-test, removed once at the end.
    # It is a fixture, not the artifact: nothing here writes a file the
    # checker reads, and nothing here writes the artifact a human submits.
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", ".check_profile_selftest")
    tmpdir = os.path.abspath(tmpdir)
    os.makedirs(tmpdir, exist_ok=True)
    try:
        good = ("Subject: x\n"
                "Base commit: 5a24248\n"
                "--- a/uniwill-acpi.c\n"
                "+++ b/uniwill-acpi.c\n"
                "@@\n"
                "+\tUNIWILL_PLATFORM_PROFILE_BALANCED,\n")
        badp = good.replace("+\tUNIWILL_PLATFORM_PROFILE_BALANCED,\n",
                            "-\tUNIWILL_PLATFORM_PROFILE_BALANCED,\n"
                            "+\tUNIWILL_PLATFORM_PROFILE_BALANCED,\n")
        # A header with prose that begins a line with a dash must not be read
        # as a removal: the body starts at `--- a/`.
        dashed = good.replace("Subject: x\n",
                              "Subject: x\n- this is prose in the header\n")
        for name, text, want in (
                ("good", good, []),
                ("removal", badp, ["-\tUNIWILL_PLATFORM_PROFILE_BALANCED,"]),
                ("dashed_header", dashed, [])):
            p = os.path.join(tmpdir, f"{name}.patch")
            with open(p, "w") as f:
                f.write(text)
            _h, body, _a = patch_body(p)
            got = removed_lines(body)
            check(f"the {name} patch reads its removed lines as {want}",
                  got == want, f"(got {got})")
            check(f"rule 5 fires on the {name} patch only where it should",
                  bool(patch_only_problems(p)) == (name == "removal"),
                  "(a removal is the defect; prose in the header is not)")
    finally:
        for name in ("good", "removal", "dashed_header"):
            f = os.path.join(tmpdir, f"{name}.patch")
            if os.path.exists(f):
                os.remove(f)

    # --- rules 6, 7, 8: driven against a constructed patch ----------------
    # These read the patch, not the map, so they need a real diff body; the
    # three are checked here rather than through `bad()` because `bad()`
    # passes a nonexistent patch and would silence them.
    tri = [row(mode="low-power"), row(mode="balanced",
                                      value_source="ec-mode-byte:no bits set (0x00)",
                                      upstream_addr_source="uniwill-acpi.c:181"),
           row(mode="performance", value_source="ec-mode-byte:FAN_MODE_TURBO (0x10)",
               upstream_addr_source="uniwill-acpi.c:181")]

    def with_patch(extra_added, rows_in, only=None, **kw):
        """Drive the map rules against a constructed diff body.

        `only` narrows the result to the refusals carrying one phrase, the way
        `bad()` does for the map-only rules. Without it every case would also
        collect the fixture's unrelated rule-9 noise, and a case that passes
        because the right refusal was somewhere in the list would be passing
        for the wrong reason.
        """
        body = ("Subject: x\n"
                "Base commit: 5a24248\n"
                "--- a/uniwill-acpi.c\n"
                "+++ b/uniwill-acpi.c\n"
                "@@\n" + "".join(f"+{ln}\n" for ln in extra_added))
        p = os.path.join(tmpdir, "drive.patch")
        with open(p, "w") as f:
            f.write(body)
        kw.setdefault("vendor", vendor)
        kw.setdefault("evidence", evidence)
        got = map_problems(rows_in, regs, declared, exc, p,
                           kw.get("pr_path", "/nonexistent"),
                           kw["vendor"], kw["evidence"])
        return [g for g in got if only in g] if only else got

    try:
        # Carries no regmap call, so nothing here names an address and rule 9
        # stays quiet: these cases are about rules 6, 7 and 8.
        clean = ["#define TURBO_MODE_SUPPORTED\t\tBIT(1)",
                 "#define EC_ADDR_BIOS_INFO_3\t\t0x049F",
                 "\tdata->turbo_supported = !!(value & TURBO_MODE_SUPPORTED);"]

        check("the three bytes the evidence records are not refused for rule 6",
              not with_patch(clean, tri, only="the map writes"),
              "(the negative control: rule 6 must not fire on the values the "
              "run and the vendor table actually record)")
        invented = [r if r["mode"] != "performance" else
                    dict(r, value_source="ec-mode-byte:FAN_MODE_TURBO (0x99)")
                    for r in tri]
        check("a mode byte the evidence never recorded is refused",
              with_patch(clean, invented, only="the map writes"),
              "(rule 6's real half: a byte the captures never saw is a byte "
              "nobody observed, and the run is the live half of the answer)")
        check("a mode byte vendor-ec-map.md does not list is refused",
              with_patch(clean, tri, only="the map writes",
                         vendor=["0x00", "0x10", "0x20"]),
              "(rule 6's other half, against the live-verified vendor table)")
        check("a map carrying two of the three mode rows is refused",
              with_patch(clean, tri[:2], only="mode-byte rows"),
              "(a profile with three modes has to carry a row per mode or the "
              "third is asserted rather than mapped)")

        check("a patch gating on FAN_TURBO_SUPPORTED is refused",
              with_patch(clean + ["\tif (value & FAN_TURBO_SUPPORTED)"],
                         tri, only="FAN_TURBO_SUPPORTED"),
              "(rule 7: the bit that reads clear while Turbo works)")
        check("a patch that only names FAN_MODE_BOOST is not refused by rule 7",
              not with_patch(clean + ["\tmask |= FAN_MODE_BOOST;"], tri,
                             only="FAN_TURBO_SUPPORTED"),
              "(the negative control: FAN_TURBO_SUPPORTED and FAN_MODE_BOOST "
              "are adjacent names in the same header block, and only one of "
              "them is the wrong gate)")
        check("a patch that only *explains* the gate is not refused by rule 7",
              not with_patch(clean + ["\t/* not FAN_TURBO_SUPPORTED, which is "
                                      "clear here */"], tri,
                             only="FAN_TURBO_SUPPORTED"),
              "(the negative control that decides whether rule 7 survives: "
              "this patch names the wrong gate in a comment precisely to "
              "record that it is refusing it, and a rule that scanned "
              "comments would fire on its own explanation")
        check("a patch that *defines* 0x0742 is refused",
              with_patch(clean + ["#define EC_ADDR_TURBO_CAP\t\t0x0742"],
                         tri, only="0x0742"))

        check("a hard-coded PL wattage is refused",
              with_patch(clean + ["\tlimits[0] = 35;"], tri, only="wattage"))
        check("a decimal that is not a wattage is not refused",
              not with_patch(clean + ["\tfor (i = 0; i < 3; i++)"], tri,
                             only="wattage"),
              "(the negative control: rule 8 has to be about watts, not about "
              "small numbers)")
        check("a limit read out of a default block is not refused",
              not with_patch(clean + ["\t.pl_defaults = 0x0734,"], tri,
                             only="wattage"),
              "(the negative control for the other half: the address the "
              "driver reads the limit out of is not a wattage)")

        check("a patch defining 0x0741 is refused",
              with_patch(clean + ["#define EC_ADDR_X_SOMETHING\t0x0741"],
                         tri, only="0x0741"))
        check("a patch writing EC_ADDR_AP_OEM is refused",
              with_patch(clean + ["\tregmap_write(data->regmap, EC_ADDR_AP_OEM, 0);"],
                         tri, only="EC_ADDR_AP_OEM"))
        check("a patch that only reads EC_ADDR_AP_OEM is not refused by rule 8",
              not with_patch(clean + ["\tregmap_read(data->regmap, EC_ADDR_AP_OEM, &v);"],
                             tri, only="EC_ADDR_AP_OEM"),
              "(the negative control: the driver already reads and sets this "
              "byte, and the rule is about writes)")

        # --- rule 9, in both directions ---------------------------------
        check("a write the map does not account for is refused",
              with_patch(clean + ["\tregmap_write(data->regmap, EC_ADDR_MANUAL_FAN_CTRL, v);"],
                         tri, only="no profile-map.csv row accounts for it"),
              "(rule 9 forward: an address the artifact never mentions is a "
              "claim with nothing behind it)")
        pl_only = [row(register="0x0783",
                       upstream_name="EC_ADDR_PL1_SETTING",
                       upstream_addr_source="uniwill-acpi.c:248",
                       value_source="ec-default-block:0x0730-0x0732",
                       verdict="replayed-from-ec-defaults")]
        check("a row claiming a write the patch never makes is refused",
              with_patch(clean, pl_only, only="never writes that address"),
              "(rule 9 reverse: the map promising something the artifact "
              "does not do")
        check("a bulk write over a declared array is resolved to its run",
              not with_patch(
                  clean + ["static const u16 uniwill_pl_settings[] = { EC_ADDR_PL1_SETTING, EC_ADDR_PL2_SETTING, EC_ADDR_PL4_SETTING };",
                           "\tregmap_bulk_write(data->regmap, EC_ADDR_PL1_SETTING, limits, sizeof(limits));"],
                  pl_only, only="never writes that address"),
              "(the negative control for the resolution: a bulk write covers "
              "every address in its run, so 0x0784 and 0x0785 being written "
              "here is what stops a rule reporting them as promised-but-absent")
    finally:
        p = os.path.join(tmpdir, "drive.patch")
        if os.path.exists(p):
            os.remove(p)

    # --- rules 3 and 9, against the committed files ----------------------
    _head, _body, added = patch_body(DEFAULT_PATCH)
    check("the committed patch is additive only",
          not patch_only_problems(DEFAULT_PATCH),
          f"(removes: {removed_lines(_body)})")
    b, n = base_rev(), nix_rev()
    check("BASE_COMMIT and uniwill-laptop.nix agree on the rev",
          revs_agree(b, n), f"(BASE_COMMIT {b!r} vs nix {n!r})")
    rows = read_map()
    index = address_index(added, excerpt_lines())
    claimed = {r["register"].split("-")[0].lower() for r in rows
               if r["verdict"] in ("mode-byte-write", "replayed-from-ec-defaults")}
    check("every address the patch writes is a row claiming a write, and every "
          "such row is a write the patch performs",
          written_addresses(added, index) == claimed,
          f"(patch-only: {sorted(written_addresses(added, index) - claimed)}; "
          f"map-only: {sorted(claimed - written_addresses(added, index))})")
    mapped = set()
    for row in rows:
        m = REGISTER.match(row["register"].strip())
        if m:
            mapped.add(m.group(1).lower())
        for hit in re.findall(r"0x[0-9A-Fa-f]{4}", row["value_source"]):
            mapped.add(hit.lower())
    check("every address the patch names is accounted for in the map",
          not (used_addresses(added, index) - mapped),
          f"(unaccounted: {sorted(used_addresses(added, index) - mapped)}; "
          f"the patch names {sorted(used_addresses(added, index))})")

    if os.path.isdir(tmpdir) and not os.listdir(tmpdir):
        os.rmdir(tmpdir)

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
    ap.add_argument("--map", default=DEFAULT_MAP, help="profile-map.csv")
    ap.add_argument("--excerpt", default=DEFAULT_EXCERPT,
                    help="upstream-excerpt-profile.txt, the committed source "
                         "the map's spellings are checked against")
    ap.add_argument("--patch", default=DEFAULT_PATCH)
    ap.add_argument("--pr", default=DEFAULT_PR)
    ap.add_argument("--registers", default=DEFAULT_YAML)
    ap.add_argument("--self-test", action="store_true",
                    help="pin each rule against the mutation it catches")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    declared = declared_statuses(args.registers)
    if declared is None:
        print(f"{args.registers}: the header comment declares no status value, "
              f"so there is no vocabulary to check the map against",
              file=sys.stderr)
        return 1

    rows = read_map(args.map)
    problems = map_problems(rows, registers_index(args.registers), declared,
                            excerpt_lines(args.excerpt), args.patch, args.pr,
                            vendor_mode_bytes(), evidence_mode_bytes())
    problems += patch_only_problems(args.patch)

    written = sorted({r["register"].split("-")[0] for r in rows
                      if r["verdict"] in ("mode-byte-write",
                                          "replayed-from-ec-defaults")})
    print(f"{len(rows)} register row(s) mapped: {len(written)} written by the "
          f"patch ({', '.join(written)}), the rest read, preserved or "
          f"deliberately untouched.")
    print("no-literals rule: every value_source names a bit spelling, an EC "
          "default block, a register the driver reads or a firmware site.")
    report(problems)
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
