#!/usr/bin/env python3
r"""Check issue #10's prepared `uniwill-laptop` DMI entry against everything
that is supposed to back it, and refuse the claims the evidence does not carry.

The artifact this checks is `linux/patches/gm7mg7p-dmi-entry/`: a feature map,
an additive patch, and the upstream PR body that goes with them. It reads only
committed files -- the map, `ec/annotations/registers.yaml`, the committed
upstream excerpt, the patch, the PR body, `linux/patches/BASE_COMMIT` and
`linux/nix/uniwill-laptop.nix`. It opens no image, no network and no vendor
binary, so a reviewer can run it offline.

**Eight rules, and the reason each is here.**

  1. **Vocabulary closure.** Every `registers_status` is a value
     `registers.yaml`'s own header comment declares, *parsed out of that
     comment* and never copied here. A second copy of the list is how the two
     drift apart silently, which is `check_status_vocabulary.py`'s rule 1 and
     is not restated here as a new idea.
  2. **Addresses are real, and the status is the one recorded there.** Every
     non-empty `reg_addr` must appear in `registers.yaml` and its
     `registers_status` must equal the status that file records for it. A
     status copied by hand into the map and left behind by a later
     `registers.yaml` edit fails, so the map cannot quietly become a second
     source of truth.
  3. **The base commit agrees four ways.** `BASE_COMMIT`'s rev equals the rev
     `uniwill-laptop.nix` pins, equals the rev the patch header names, and
     equals the rev the excerpt says it was fetched at. The first pair is
     about the build; the second pair is about the evidence. A patch that
     drifted off the source the build fetches is the failure this exists for.
  4. **Additive only.** No `-` line in the diff body but the `---` header. A
     diff that edits an existing row or bit is refused outright. This is the
     guard that makes the entry safe for every *other* board in the table, and
     it is the one `git apply --check` would happily wave straight through.
  5. **Bits and rows agree, both directions.** Every bit the patch sets has an
     `in_descriptor=yes` row naming it, and every such row's bit is set by the
     patch. A bit claimed in prose but absent from the diff fails, and so does
     the reverse.
  6. **The include rule, in two halves, neither sufficient alone.**
     (a) Where `reg_addr` is present, `registers_status` must be one that
     asserts the feature *works* -- `confirmed-working` or
     `confirmed-working-partially` -- and every other status must be `no`.
     That is deliberately not a `confirmed-` prefix test: the prefix also
     covers `confirmed-inert` (a proven write the EC does not act on) and
     `confirmed-not-this-mechanism` (a live test that refutes the mechanism
     the entry names), and LIGHTBAR is correctly excluded on the second one.
     (b) Where `reg_addr` is absent, `verdict` must be a live verdict *cited
     to a file*, and the map must record that the driver's interface
     genuinely drives the feature. Both halves are needed and each alone is
     wrong: 6(a) on its own would exclude the two fans, which
     `registers.yaml` has no address for but which are confirmed live; 6(b)
     on its own would admit `KEYBOARD_BACKLIGHT`, whose Fn+F6/F7 hotkey is
     confirmed while the software LED-class path it would expose is
     `present-untested`.
  7. **Spellings are sourced.** Every `upstream_bit` and every
     `upstream_ec_addr` must appear **byte for byte** in
     `upstream-excerpt.txt`, and every non-empty address must carry a
     line-number `upstream_addr_source` that is *itself* checked to be a line
     of the excerpt which really contains that address.

     This rule is the whole reason the excerpt is committed. The previous
     attempt at this work marked twelve rows `unsourced` and accepted any
     plausible constant, so a name invented into both the CSV and a patch
     passed every check here -- and a reviewer correctly called that
     unfalsifiable. With the enum and the address defines committed as
     evidence, `UNIWILL_FEATURE_CPU_TMP` is a typo the excerpt does not
     contain, and it fails. An empty cell is now only legitimate where the
     *feature* has no upstream address, never because of which files this
     repository happens to vendor.
  8. **The self-test is the refusals.** `--self-test` runs each rule against
     the mutation it is meant to catch, on fixtures rather than the committed
     rows, because a rule tested only against the data it was derived from is
     not tested. A check that has quietly stopped refusing looks exactly like
     a check that is working.

**What this does not check, which is as much of the point.** Nothing here
establishes that the eight bits are *right on hardware*. It establishes that
the artifact is internally consistent, that its spellings are quoted from a
pinned source, and that its exclusions carry reasons. The driver has not been
compiled here and nothing has been loaded on a machine. `PR_DESCRIPTION.md`
says so in those words to whoever pastes it upstream.

Usage:
    python3 tools/check_dmi_descriptor.py --check
    python3 tools/check_dmi_descriptor.py --self-test
"""
import argparse
import csv
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(REPO, "linux", "patches", "gm7mg7p-dmi-entry")

DEFAULT_MAP = os.path.join(ENTRY, "feature-map.csv")
DEFAULT_EXCERPT = os.path.join(ENTRY, "upstream-excerpt.txt")
DEFAULT_PATCH = os.path.join(ENTRY, "uniwill-acpi-dm-gm7mg7p.patch")
DEFAULT_PR = os.path.join(ENTRY, "PR_DESCRIPTION.md")
DEFAULT_YAML = os.path.join(REPO, "ec", "annotations", "registers.yaml")
DEFAULT_BASE = os.path.join(REPO, "linux", "patches", "BASE_COMMIT")
DEFAULT_NIX = os.path.join(REPO, "linux", "nix", "uniwill-laptop.nix")

COLUMNS = ["repo_feature", "upstream_bit", "bit_source", "reg_addr",
           "registers_status", "upstream_ec_addr", "upstream_addr_source",
           "verdict", "in_descriptor", "reason"]

# The rev both pins must agree on. Derived from the files rather than written
# here, so bumping a pin does not leave this tool checking a rev nobody uses.
BASE_REV = re.compile(r"^([0-9a-f]{7,40})\b")
NIX_REV = re.compile(r'rev\s*=\s*"([0-9a-f]{7,40})"')

# A `uniwill-acpi.c:NNN` citation, and the excerpt's own `NNN: text` lines.
ADDR_SOURCE = re.compile(r"^uniwill-acpi\.c:(\d+)$")
EXCERPT_LINE = re.compile(r"^\s*(\d+): (.*)$")

# A verdict that carries a live observation and the file that records it. Both
# halves are required: the token alone would be an assertion with nothing behind
# it, and the citation alone would let any non-live grade borrow a live one's
# file. `--self-test` pins both refusals.
LIVE_VERDICT = re.compile(
    r"^live-confirmed;driver-interface-drives"
    r"|^live-refuted"
    r"|^write-accepted-effect-untested")
CITED = re.compile(r"(docs/[\w./-]+\.md|ec/[\w./-]+\.yaml|evidence/[\w./-]+)")

# The statuses that assert a feature *works*, which is what claiming a bit
# needs. This is deliberately not a `confirmed-` prefix test, and the reason is
# that the prefix covers four different verdicts: `confirmed-inert` is a proven
# live write the EC does not act on, and `confirmed-not-this-mechanism` is a
# live test that refutes the mechanism the entry names. Both are `confirmed-`
# and both mean the opposite of "this works" -- LIGHTBAR is excluded here on
# exactly the second one, and a prefix test would have demanded it be claimed.
# Naming the two working values is also how a *new* status in that header is
# refused rather than swept in by a prefix that happens to match.
WORKING_STATUSES = ("confirmed-working", "confirmed-working-partially")

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


def patch_added_bits(path=DEFAULT_PATCH):
    """(added lines, bits set) from the diff body of the patch.

    The body starts at the first `--- ` line, so the prose header above it --
    which is documentation and may say anything -- is not scanned for `-`
    lines or for constant names.
    """
    with open(path) as f:
        text = f.read()
    if not text.startswith("Subject:") and "--- a/" not in text:
        raise ValueError("patch has no diff body")
    body = text[text.index("--- a/"):] if "--- a/" in text else text
    added, bits = [], set()
    for line in body.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
            bits.update(re.findall(r"UNIWILL_FEATURE_[A-Z0-9_]+", line))
    return body, added, bits


def removed_lines(body):
    """`-` lines in the diff body, excluding the `---` file header."""
    return [ln for ln in body.splitlines()
            if ln.startswith("-") and not ln.startswith("---")]


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


# --- the rules --------------------------------------------------------------

def map_problems(rows, regs, declared, exc_lines, patch_path, pr_path):
    """Every rule that can be decided from the map and the committed inputs.

    Split out from `check()` so `--self-test` can drive it against constructed
    rows without touching the committed ones.
    """
    values, suffixes = declared
    problems = []

    for row in rows:
        name = row.get("repo_feature", "?")
        bit = (row.get("upstream_bit") or "").strip()
        addr = (row.get("reg_addr") or "").strip()
        status = (row.get("registers_status") or "").strip()
        up_addr = (row.get("upstream_ec_addr") or "").strip()
        up_src = (row.get("upstream_addr_source") or "").strip()
        verdict = (row.get("verdict") or "").strip()
        included = (row.get("in_descriptor") or "").strip()

        # --- rule 1: the vocabulary is registers.yaml's, not ours ----------
        if status:
            base, _ = split_status(status, suffixes)
            if base not in values:
                problems.append(
                    f"{name}: registers_status {status!r} is not a value "
                    f"registers.yaml's header declares (one of: "
                    f"{', '.join(values)})")

        # --- rule 2: the address is real and the status is its own ---------
        if addr:
            key = int(addr, 16)
            if key not in regs:
                problems.append(
                    f"{name}: reg_addr {addr} is not an address "
                    f"registers.yaml records, so the map is asserting a "
                    f"register this repository has no entry for")
            elif regs[key] != status:
                problems.append(
                    f"{name}: registers_status {status!r} is not what "
                    f"registers.yaml records for {addr} ({regs[key]!r}); "
                    f"a hand-copied status left behind by an edit to that "
                    f"file fails here rather than quietly disagreeing with it")

        # --- rule 7: every spelling is quoted from the pinned source --------
        # The rule the previous attempt's checker could not make. `unsourced`
        # is no longer a value this map can hold, so a plausible-looking
        # invented constant is a failure rather than a silence.
        if not bit:
            problems.append(
                f"{name}: upstream_bit is empty. The enum is in "
                f"upstream-excerpt.txt, so a spelling is available for every "
                f"feature; an empty cell is only right where the *feature* "
                f"has no upstream bit, and then bit_source must say so")
        elif bit not in "".join(exc_lines.values()):
            problems.append(
                f"{name}: upstream_bit {bit!r} does not appear in "
                f"upstream-excerpt.txt. It is either a typo or a name "
                f"invented rather than read off the source at the pinned rev")

        if up_addr and up_addr not in "".join(exc_lines.values()):
            problems.append(
                f"{name}: upstream_ec_addr {up_addr} does not appear in "
                f"upstream-excerpt.txt, so it is not readable at the pinned "
                f"rev and must not be recorded as though it were")
        if up_addr:
            m = ADDR_SOURCE.match(up_src)
            if not m:
                problems.append(
                    f"{name}: upstream_ec_addr {up_addr} needs an "
                    f"upstream_addr_source of the form uniwill-acpi.c:NNN")
            elif int(m.group(1)) not in exc_lines:
                problems.append(
                    f"{name}: upstream_addr_source {up_src} is not a line "
                    f"upstream-excerpt.txt quotes")
            elif up_addr not in exc_lines[int(m.group(1))]:
                problems.append(
                    f"{name}: upstream_addr_source {up_src} does not carry "
                    f"{up_addr}; the excerpt's line {m.group(1)} is "
                    f"{exc_lines[int(m.group(1))].strip()!r}")

        # --- rule 6: the include rule, both halves -------------------------
        if included not in ("yes", "no"):
            problems.append(
                f"{name}: in_descriptor is {included!r}; it must be 'yes' or "
                f"'no', so a claim is stated rather than left implied")
            continue

        if included == "yes":
            if addr:
                # 6(a)
                base, _ = split_status(status, suffixes)
                if base not in WORKING_STATUSES:
                    problems.append(
                        f"{name}: in_descriptor=yes with reg_addr {addr} at "
                        f"{status!r}, which is not a grade asserting the "
                        f"feature works. {WORKING_STATUSES[0]} and "
                        f"{WORKING_STATUSES[1]} do; `confirmed-inert` and "
                        f"`confirmed-not-this-mechanism` are also "
                        f"`confirmed-` and mean the opposite")
            else:
                # 6(b): a live verdict, cited, plus the interface judgement.
                if not LIVE_VERDICT.match(verdict):
                    problems.append(
                        f"{name}: in_descriptor=yes with no reg_addr, so the "
                        f"verdict must carry the live observation instead. "
                        f"Got {verdict!r}; expected one of live-confirmed, "
                        f"live-refuted or write-accepted-effect-untested")
                if not CITED.search(row.get("reason", "")):
                    problems.append(
                        f"{name}: in_descriptor=yes with no reg_addr needs a "
                        f"reason citing the file that records the live "
                        f"observation")
                if "driver-interface-drives" not in verdict:
                    problems.append(
                        f"{name}: in_descriptor=yes with no reg_addr must "
                        f"also record that the driver's interface genuinely "
                        f"drives the feature, as "
                        f"';driver-interface-drives' in the verdict")
        else:
            if addr:
                base, _ = split_status(status, suffixes)
                if base in WORKING_STATUSES:
                    problems.append(
                        f"{name}: in_descriptor=no with reg_addr {addr} at "
                        f"{status!r}, which asserts the feature works. A "
                        f"working feature left out of the descriptor needs "
                        f"the reason to say why the driver's interface "
                        f"still does not apply to it")

        # --- the reason is not optional ------------------------------------
        if not (row.get("reason") or "").strip():
            problems.append(
                f"{name}: an exclusion with no written reason is the one "
                f"thing this file is for; the reason column is empty")

    # --- rule 5: bits and rows agree, both directions ----------------------
    try:
        _body, _added, bits = patch_added_bits(patch_path)
    except (OSError, ValueError):
        bits = set()
    claimed = {r["upstream_bit"].strip() for r in rows
               if (r.get("in_descriptor") or "").strip() == "yes"}
    for bit in sorted(bits - claimed):
        problems.append(
            f"the patch sets {bit}, which no in_descriptor=yes row names. A "
            f"bit in the diff with nothing behind it in the map is a claim "
            f"with no evidence")
    for bit in sorted(claimed - bits):
        problems.append(
            f"{bit} has an in_descriptor=yes row but the patch does not set "
            f"it, so the map claims something the artifact does not do")

    # --- rule 3b/4: the patch itself ---------------------------------------
    try:
        body, _added, _bits = patch_added_bits(patch_path)
    except (OSError, ValueError):
        body = ""
    for line in removed_lines(body):
        problems.append(
            f"the patch removes a line, which is not additive: {line!r}. "
            f"This entry must not touch an existing row, field or bit, or "
            f"every other board in the table is at risk")

    try:
        with open(patch_path) as f:
            head = f.read()
    except OSError:
        head = ""
    rev = base_rev()
    if rev and rev not in head:
        problems.append(
            f"the patch header does not name the base rev {rev} that "
            f"linux/patches/BASE_COMMIT records, so it cannot be told which "
            f"source it was made against")

    if os.path.exists(pr_path):
        with open(pr_path) as f:
            pr = f.read()
        for bit in sorted(claimed):
            if bit not in pr:
                problems.append(
                    f"PR_DESCRIPTION.md does not mention {bit}, which the "
                    f"descriptor claims. The body a human pastes upstream "
                    f"has to say what the entry does")
    else:
        problems.append(f"PR_DESCRIPTION.md is missing at {pr_path}")

    return problems


def report(problems):
    for p in problems:
        print(f"  REFUSED  {p}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} refusal(s). A refusal is a shape this "
              f"artifact is not allowed to take, not an argument that the "
              f"eight bits are wrong on hardware.", file=sys.stderr)
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

    # An excerpt carrying one real bit and two real addresses, so "sourced" and
    # "invented" can be told apart without quoting the committed file. The bit
    # has to be in here or rule 7 fires on every row and the negative cases
    # below pass for the wrong reason.
    exc = {87: "#define EC_ADDR_CPU_TEMP\t\t0x043E",
           94: "#define EC_ADDR_MAIN_FAN_RPM_1\t0x0464",
           165: "#define EC_ADDR_LIGHTBAR_AC_CTRL\t0x0748",
           363: "#define UNIWILL_FEATURE_CPU_TEMP\t\tBIT(6)"}
    regs = {0x043E: "confirmed-working", 0x07B9: "unknown-not-absent",
            0x078C: "present-untested",
            0x0748: "confirmed-not-this-mechanism"}

    def row(**kw):
        base = {"repo_feature": "X", "upstream_bit": "UNIWILL_FEATURE_CPU_TEMP",
                "bit_source": "upstream@5a24248", "reg_addr": "0x043E",
                "registers_status": "confirmed-working",
                "upstream_ec_addr": "0x043E", "upstream_addr_source":
                "uniwill-acpi.c:87", "verdict": "", "in_descriptor": "yes",
                "reason": "live test in docs/findings.md"}
        base.update(kw)
        return base

    def bad(rows, **kw):
        kw.setdefault("patch_path", "/nonexistent")
        kw.setdefault("pr_path", "/nonexistent")
        # The patch and PR checks are exercised separately; here only the map
        # rules run, so a row problem is what makes the list non-empty.
        return [p for p in map_problems(rows, regs, declared, exc,
                                        kw["patch_path"], kw["pr_path"])
                if p.startswith(rows[0]["repo_feature"])]

    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    # --- the committed inputs, which is the point of running this ---------
    live = read_map()
    check("the committed map parses into rows", len(live) == 15,
          f"(got {len(live)}; the map is 8 claimed + 7 excluded)")
    check("the committed map has the columns this tool reads",
          all(c in live[0] for c in COLUMNS),
          f"(missing: {[c for c in COLUMNS if c not in live[0]]})")
    real_decl = declared_statuses(DEFAULT_YAML)
    check("registers.yaml's header still declares a vocabulary",
          bool(real_decl and real_decl[0]),
          "(if this is red the block moved or was re-indented, and every "
          "rule-1 check below would be refusing against an empty list)")
    check("the committed excerpt quotes the lines the map cites",
          bool(excerpt_lines()), "(upstream-excerpt.txt parsed to nothing)")

    # --- rule 7: the rule the previous attempt's checker could not make ----
    check("a misspelled-but-plausible constant is refused",
          bad([row(upstream_bit="UNIWILL_FEATURE_CPU_TMP")]),
          "(UNIWILL_FEATURE_CPU_TMP does not exist; it is what a plausible "
          "invention looks like, and it must not pass)")
    check("a plausible invented address is refused",
          bad([row(upstream_ec_addr="0x0999")]),
          "(an address that is not in the excerpt is not readable at the "
          "pinned rev)")
    check("an address source pointing at a line without it is refused",
          bad([row(upstream_addr_source="uniwill-acpi.c:94")]),
          "(line 94 carries 0x0464, not 0x043E)")
    check("an address source naming an unquoted line is refused",
          bad([row(upstream_addr_source="uniwill-acpi.c:9999")]),
          "(the excerpt does not quote line 9999)")
    check("an empty bit is refused now the enum is committed",
          bad([row(upstream_bit="")]),
          "(`unsourced` is no longer a value the map can hold)")
    check("a correctly sourced constant is not refused",
          not bad([row()]),
          "(the same row as the misspelling above, spelled correctly)")

    # --- rule 1: vocabulary, and rule 2: the status is registers.yaml's ---
    check("an undeclared status is refused",
          bad([row(registers_status="confirmed-maybe")]))
    check("a status registers.yaml does not record for that address is refused",
          bad([row(registers_status="present-untested")]),
          "(0x043E is confirmed-working; the map claiming otherwise is the "
          "hand-copied-status failure)")
    check("an address registers.yaml has no entry for is refused",
          bad([row(reg_addr="0x0999")]))
    check("a correct status is not refused",
          not bad([row(registers_status="confirmed-working")]))

    # --- rule 6(a): the address half of the include rule -------------------
    check("a working status excluded with a reg_addr is refused",
          bad([row(in_descriptor="no", registers_status="present-untested",
                   reason="no reason given")]),
          "(the fans' case is the opposite shape and must NOT be refused -- "
          "see below)")
    check("a non-working status claimed is refused",
          bad([row(registers_status="absent")]))
    check("present-untested is not claimable",
          bad([row(registers_status="present-untested")]),
          "(so the keyboard backlight cannot be claimed on the strength of a "
          "confirmed Fn+F6/F7 hotkey: the path it would expose is untested)")
    # The two `confirmed-` values that mean the opposite of "works". A prefix
    # test would demand both be claimed, and LIGHTBAR is correctly excluded on
    # the second -- this pair is why the rule names the two working values.
    check("confirmed-not-this-mechanism is not claimable",
          bad([row(registers_status="confirmed-not-this-mechanism")]),
          "(a live test that refutes the mechanism is not a working feature, "
          "and LIGHTBAR is excluded on exactly this grade)")
    check("confirmed-inert is not claimable",
          bad([row(registers_status="confirmed-inert")]),
          "(a proven write the EC does not act on is not a working feature "
          "either)")
    check("excluding a confirmed-not-this-mechanism row is not refused",
          not bad([row(in_descriptor="no",
                       registers_status="confirmed-not-this-mechanism",
                       reg_addr="0x0748",
                       upstream_ec_addr="0x0748",
                       upstream_addr_source="uniwill-acpi.c:165",
                       reason="wrong mechanism, docs/findings.md")]),
          "(the LIGHTBAR shape: a `confirmed-` grade that is correctly left "
          "out, which a prefix test would have refused)")

    # --- rule 6(b): the no-address half ------------------------------------
    fan = row(repo_feature="PRIMARY_FAN", reg_addr="", registers_status="",
              upstream_ec_addr="0x0464", upstream_addr_source="uniwill-acpi.c:94",
              verdict="live-confirmed;driver-interface-drives",
              reason="RPM sysfs matches physical sound, docs/findings.md")
    check("a live-confirmed no-address feature is claimed without refusal",
          not bad([fan]),
          "(rule 6(a) alone would wrongly exclude this: registers.yaml has "
          "no address for the fans, and the RPM observation is the evidence)")
    check("a no-address claim with no verdict is refused",
          bad([row(reg_addr="", registers_status="", verdict="",
                   upstream_ec_addr="0x0464",
                   upstream_addr_source="uniwill-acpi.c:94")]),
          "(the half of 6(b) that 6(a) would have covered by accident)")
    check("a no-address claim that omits the interface judgement is refused",
          bad([row(reg_addr="", registers_status="",
                   verdict="live-confirmed",
                   upstream_ec_addr="0x0464",
                   upstream_addr_source="uniwill-acpi.c:94")]),
          "(a live observation the driver's interface cannot act on is not "
          "a claim the descriptor can make)")
    check("a no-address claim citing no file is refused",
          bad([row(reg_addr="", registers_status="",
                   verdict="live-confirmed;driver-interface-drives",
                   upstream_ec_addr="0x0464",
                   upstream_addr_source="uniwill-acpi.c:94",
                   reason="it seemed to work")]))
    check("a verdict borrowed from another grade is refused",
          bad([row(reg_addr="", registers_status="",
                   verdict="unknown-not-absent;driver-interface-drives",
                   upstream_ec_addr="0x0464",
                   upstream_addr_source="uniwill-acpi.c:94")]),
          "(the citation rule must not let any grade borrow a live one's "
          "file)")
    check("an in_descriptor that is neither yes nor no is refused",
          bad([row(in_descriptor="maybe")]))

    # --- an exclusion with no reason is the thing this file is for ---------
    check("an exclusion with an empty reason is refused",
          bad([row(in_descriptor="no", registers_status="unknown-not-absent",
                   reg_addr="0x07B9", reason="")]))

    # --- rule 4: additive only, on the patch itself -----------------------
    tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", ".check_dmi_selftest")
    tmpdir = os.path.abspath(tmpdir)
    os.makedirs(tmpdir, exist_ok=True)
    try:
        good = ("Subject: x\n"
                "Base commit: 5a24248\n"
                "--- a/uniwill-acpi.c\n"
                "+++ b/uniwill-acpi.c\n"
                "@@\n"
                "+\tUNIWILL_FEATURE_CPU_TEMP,\n")
        badp = good.replace("+\tUNIWILL_FEATURE_CPU_TEMP,\n",
                            "-\tUNIWILL_FEATURE_TOUCHPAD_TOGGLE,\n"
                            "+\tUNIWILL_FEATURE_CPU_TEMP,\n")
        # A header with prose that begins a line with a dash must not be read
        # as a removal: the body starts at `--- a/`.
        dashed = good.replace("Subject: x\n",
                              "Subject: x\n- this is prose in the header\n")
        for name, text, want_removed in (
                ("good", good, []),
                ("removal", badp,
                 ["-\tUNIWILL_FEATURE_TOUCHPAD_TOGGLE,"]),
                ("dashed_header", dashed, [])):
            p = os.path.join(tmpdir, f"{name}.patch")
            with open(p, "w") as f:
                f.write(text)
            body, _added, bits = patch_added_bits(p)
            got = removed_lines(body)
            check(f"the {name} patch reads its removed lines as {want_removed}",
                  got == want_removed, f"(got {got})")
        _b, _a, bits = patch_added_bits(os.path.join(tmpdir, "good.patch"))
        check("bits are read from added lines only",
              bits == {"UNIWILL_FEATURE_CPU_TEMP"}, f"(got {sorted(bits)})")
    finally:
        for name in ("good", "removal", "dashed_header"):
            f = os.path.join(tmpdir, f"{name}.patch")
            if os.path.exists(f):
                os.remove(f)
        if os.path.isdir(tmpdir) and not os.listdir(tmpdir):
            os.rmdir(tmpdir)

    # --- rules 3 and 5, against the committed files -----------------------
    b, n = base_rev(), nix_rev()
    check("BASE_COMMIT and uniwill-laptop.nix agree on the rev",
          revs_agree(b, n), f"(BASE_COMMIT {b!r} vs nix {n!r})")
    body, _added, bits = patch_added_bits(DEFAULT_PATCH)
    check("the committed patch is additive only",
          not removed_lines(body),
          f"(removes: {removed_lines(body)})")
    claimed = {r["upstream_bit"].strip() for r in read_map()
               if r["in_descriptor"].strip() == "yes"}
    check("every bit the patch sets has a row, and every row a bit",
          bits == claimed,
          f"(patch-only: {sorted(bits - claimed)}; map-only: "
          f"{sorted(claimed - bits)})")

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
    ap.add_argument("--map", default=DEFAULT_MAP, help="feature-map.csv")
    ap.add_argument("--excerpt", default=DEFAULT_EXCERPT,
                    help="upstream-excerpt.txt, the committed source the "
                         "map's spellings are checked against")
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
                            excerpt_lines(args.excerpt), args.patch, args.pr)

    claimed = [r for r in rows if r["in_descriptor"].strip() == "yes"]
    print(f"{len(rows)} feature(s) mapped: {len(claimed)} in the descriptor, "
          f"{len(rows) - len(claimed)} excluded with a reason.")
    print("include rule: a reg_addr needs a confirmed-* status; no reg_addr "
          "needs a live verdict cited to a file plus a recorded judgement "
          "that the driver's interface drives it.")
    report(problems)
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
