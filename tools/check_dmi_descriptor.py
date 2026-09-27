#!/usr/bin/env python3
r"""Check the prepared TongFang GM7MG7P DMI entry against what this repository
can actually evidence.

`linux/patches/gm7mg7p-dmi-entry/` is issue #10's deliverable: a prepared
`uniwill-laptop` table row and the PR body a human pastes into it, for
`Wer-Wolf/uniwill-laptop`, which no stage here may open itself (CLAUDE.md).

**The failure this exists to prevent is not a patch that will not apply.** It
is a patch that applies cleanly, gets a descriptor, and is wrong on a board
nobody in this pipeline can test. Every rule below is a way that specific
outcome gets caught offline, from committed files, with no laptop.

**What the descriptor is allowed to claim** is decided by the evidence already
in `ec/annotations/registers.yaml`, not by issue #10's prose. The issue's own
list is a snapshot of 2026-09-14 and has since been overtaken in at least one
place -- it calls `NVIDIA_CTGP_CONTROL` untested, `registers.yaml` grades
`0x0743` `confirmed-working` -- and `registers.yaml` is the source of truth for
status (CLAUDE.md). Rule 2 is what holds the map to it, so a stale issue list
becomes a red run rather than a wrong descriptor.

**Rules, each traced to the thing it catches.**

  1. **Vocabulary closure.** Every `registers_status` is a value
     `registers.yaml`'s own header comment declares, parsed out of that
     comment rather than copied here. A second copy of the list in this file is
     exactly how the two drift apart silently, which is the whole argument
     `check_status_vocabulary.py` makes about its own copy not existing.
  2. **Addresses are real.** Every `reg_addr` is an address `registers.yaml`
     records, and the row's `registers_status` is the status it records there.
     A status typed into the map by hand and left behind by a `registers.yaml`
     edit fails here rather than in a maintainer's review of the PR.
  3. **The base commit agrees three ways** -- `linux/patches/BASE_COMMIT`,
     the `rev` in `linux/nix/uniwill-laptop.nix`, and the rev the patch header
     names. The nix recipe is what actually gets built, so a patch cut
     against a different rev is one whose context nobody will ever re-derive.
  4. **Additive only.** The patch removes no line. This is the guard that makes
     the entry safe for every *other* board already in the table, and it is the
     one `git apply --check` waves straight through: a re-cut that rewrites
     somebody else's row applies perfectly and is still the wrong patch.
  5. **Bits and rows agree, in both directions.** A bit the patch sets with no
     `in_descriptor=yes` row is claimed in the diff and evidenced nowhere; a row
     marked included whose bit the patch never sets is evidenced in prose and
     missing in the artifact. Both are failures and they are different bugs.
  6. **The include rule.** `in_descriptor=yes` requires a `confirmed-*` status,
     an address this repository records, and a bit spelling it can source. This
     is CLAUDE.md's calibration rule made mechanical, and it is what keeps
     `BATTERY_CHARGE_LIMIT` and the four other open features out.
  7. **Bit sourcing.** Every bit spelling is either quoted by a committed file
     the row names, or read off the driver at `BASE_COMMIT` and backed by the
     patch. **This is the rule the tree is currently red on, and being red is
     correct.** Only two upstream bit spellings are recoverable from committed
     files, both quoted in `linux/patches/README.md`; the driver is not
     vendored here, and `ec/annotations/static-refs-audit.md` records hitting
     that same wall and declining to invent around it. So the descriptor
     reduces to one bit today, and says so rather than guessing the rest.
  8. **The PR body carries the board identity**, and names no bit the map does
     not. A PR body is prose a maintainer reads in a browser tab, so this is
     the last place a stale claim can survive a correct diff.

**What this does not check**, which is as much of the point:

  * *Whether any of it is right on hardware.* Every rule here is about the
    shape of a claim, never its strength. `BATTERY_CHARGE_MODES` is included
    because `registers.yaml` grades the byte `confirmed-working-partially`,
    and this tool cannot tell you whether the *driver's* interface drives that
    byte the way the vendor's does. The offline check proves the artifact is
    internally consistent. It does not prove the descriptor is correct, and
    `PR_DESCRIPTION.md` says so in the words a maintainer will read.
  * *Whether a bit name is the right bit name.* Rule 7 checks that a spelling
    is sourced. Reading `UNIWILL_FEATURE_FAN_SPEED` off `uniwill-acpi.c` and
    recording it as the fan bit is a human's judgement; this cannot make it.

**The missing patch is a first-class state, not a pass.** The patch is the one
deliverable in that directory which needs the network: it is cut against
`uniwill-acpi.c` at `BASE_COMMIT`, which is not committed here and could not
be fetched when this was written. So when the patch is absent, `--check`
refuses, names the file, and points at the one command that produces it --
rather than checking the map and exiting 0, which is what "a check quietly
stopped running" looks like from the outside. A rule is skipped only when the
thing it reads is absent, and only with a line saying so.

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

# The status vocabulary is *parsed* out of registers.yaml's header, and the
# parser is imported rather than rewritten. `check_status_vocabulary.py`'s
# docstring is the argument: the declared list is a single source of truth and
# a second copy is how it drifts apart silently. Its `parse_declared` is the
# one that reads that comment, so the two checkers cannot come to disagree
# about which values are declared. Imported across directories, so `ec/tools`
# goes on the path explicitly rather than by relying on a sibling layout.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "ec", "tools"))
from check_status_vocabulary import parse_declared  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir))
ENTRY = os.path.join("linux", "patches", "gm7mg7p-dmi-entry")
MAP = os.path.join(ENTRY, "feature-map.csv")
PATCH = os.path.join(ENTRY, "uniwill-acpi-dm-gm7mg7p.patch")
PR_BODY = os.path.join(ENTRY, "PR_DESCRIPTION.md")
REGISTERS = os.path.join("ec", "annotations", "registers.yaml")
BASE_COMMIT = os.path.join("linux", "patches", "BASE_COMMIT")
NIX = os.path.join("linux", "nix", "uniwill-laptop.nix")

COLUMNS = ("repo_feature", "upstream_bit", "bit_source", "reg_addr",
           "registers_status", "verdict", "in_descriptor", "reason")

# The two sentinels this tool declares, and the reason each is a closed value
# rather than a blank cell. A blank would parse as "" and be refused by rules
# 1 and 2 for a reason that has nothing to do with the claim; naming the state
# means a row that means it is legible without reading this docstring.
#
# `unsourced`: no committed file in this repository records the upstream
# spelling of the bit. Two of the twelve rows are *not* this -- the two charge
# rows quote `linux/patches/README.md`. See rule 7.
UNSOURCED = "unsourced"
# `not-recorded-here`: this repository records no EC address for the feature at
# all. `ec/annotations/static-refs-audit.md` hit this wall already, named these
# features, and left the cells empty rather than inventing addresses.
NO_ADDRESS = "not-recorded-here"
# ...and the status cell that goes with it, for the same reason. It is not a
# `registers.yaml` status and rule 1 must not read it as one.
NO_ADDR_STATUS = "no-address"

# A `bit_source` of `upstream@<rev>` means the spelling was read off
# `uniwill-acpi.c` at that rev rather than out of a committed file. It is
# accepted only when the patch actually sets the bit, so a name nobody can
# back up cannot sit in the map looking sourced.
UPSTREAM_SOURCE = re.compile(r"^upstream@([0-9a-f]{7,40})$")
BIT = re.compile(r"UNIWILL_FEATURE_[A-Z0-9_]+")
# The one rev pattern, read out of the same shapes `BASE_COMMIT` and the nix
# recipe use, so the three are compared as strings and not as guesses about
# what a short rev abbreviates to.
REV = re.compile(r"\b([0-9a-f]{7,40})\b")
NIX_REV = re.compile(r'rev\s*=\s*"([0-9a-f]{7,40})"')


def read_text(relpath):
    with open(os.path.join(REPO, relpath), encoding="utf-8") as handle:
        return handle.read()


def read_map():
    """The map's rows as dicts, with the header checked against COLUMNS.

    `restkey`/`restval` rather than a bare DictReader so a *short* row is a
    refusal here instead of an `AttributeError` three rules later, where it
    reads as a crash rather than as the malformed row it is.
    """
    path = os.path.join(REPO, MAP)
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, restkey="_extra", restval="")
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(
                f"{MAP} header is {reader.fieldnames}, expected {list(COLUMNS)}")
        return [dict(row) for row in reader]


def registers_index():
    """`{0xADDR: status}` over every address `registers.yaml` records.

    A four-address entry contributes the same status at each of its addresses,
    because that is what a single `status:` on such an entry means.
    """
    with open(os.path.join(REPO, REGISTERS), encoding="utf-8") as handle:
        regs = yaml.safe_load(handle)["registers"]
    out = {}
    for entry in regs:
        addrs = entry["addr"]
        for addr in (addrs if isinstance(addrs, list) else [addrs]):
            out[addr] = entry.get("status", "")
    return out


def declared_statuses():
    """(values, suffixes) parsed out of `registers.yaml`'s header comment."""
    declared = parse_declared(read_text(REGISTERS))
    if declared is None:
        return None
    values, suffixes = declared
    return values + [NO_ADDR_STATUS], suffixes


def split_status(status, suffixes):
    """(base value, suffix or None), as `check_status_vocabulary` splits it.

    Imported logic rather than re-derived: a suffix here must mean the same
    thing it means there, or a `-DO-NOT-WRITE-BLIND` row could pass rule 1 here
    and fail it there.
    """
    for suffix in suffixes:
        if status.endswith(suffix) and len(status) > len(suffix):
            return status[: -len(suffix)], suffix
    return status, None


def base_rev():
    """The rev in `linux/patches/BASE_COMMIT` -- `5a24248 Bump minimum ...`.

    The file is `<rev> <subject>`, so the rev is the first whitespace-delimited
    field and the subject is not part of it. That is read rather than assumed:
    a `BASE_COMMIT` holding a bare full sha, or a tag, is a different file
    shape and rule 3 refuses it rather than half-matching it.
    """
    text = read_text(BASE_COMMIT).strip()
    return text.split()[0] if text else ""


def nix_rev():
    """The `rev` the build actually fetches, out of the nix recipe."""
    match = NIX_REV.search(read_text(NIX))
    return match.group(1) if match else ""


def patch_parts(text):
    """(header, added, removed) for a unified diff.

    `+++`/`---` are the file headers, not content: a removed line and an added
    line both start with their marker, and the `---` header is the one `-` line
    rule 4 has to tolerate or every patch reads as touching an existing file.
    """
    cut = text.find("diff --git ")
    header = text if cut < 0 else text[:cut]
    body = text[cut:] if cut >= 0 else text
    added = [ln[1:] for ln in body.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    removed = [ln[1:] for ln in body.splitlines()
               if ln.startswith("-") and not ln.startswith("---")]
    return header, added, removed


def patch_bits(added):
    """Every `UNIWILL_FEATURE_*` name the patch's added lines mention."""
    return {bit for line in added for bit in BIT.findall(line)}


# --- the rules --------------------------------------------------------------

def rule_vocabulary(rows, values, suffixes):
    """Rule 1: every status is a value the header comment declares."""
    problems = []
    for row in rows:
        status = row["registers_status"]
        base, _suffix = split_status(status, suffixes)
        if base not in values:
            problems.append(
                f"{row['repo_feature']}: registers_status {status!r} is not a "
                f"value registers.yaml's header declares (one of: "
                f"{', '.join(values)}). The map carries statuses; it does not "
                "grade them.")
    return problems


def rule_addresses(rows, statuses, suffixes):
    """Rule 2: the address is real and the status is the one recorded there.

    Compared on the *base* value, so a row may carry `-DO-NOT-WRITE-BLIND` or
    not without failing -- the suffix is a warning about writing a byte, and
    this map never writes one, so grading on the base is what
    `check_status_vocabulary` means by a suffix not changing which rule
    applies. Dropping it loses a warning, not a grade, and is the map's call
    to make.
    """
    problems = []
    for row in rows:
        feature, addr = row["repo_feature"], row["reg_addr"]
        status = row["registers_status"]
        if addr == NO_ADDRESS:
            if status != NO_ADDR_STATUS:
                problems.append(
                    f"{feature}: reg_addr is {NO_ADDRESS} so there is no "
                    f"address to take a status from, but registers_status is "
                    f"{status!r} rather than {NO_ADDR_STATUS!r}.")
            if row["in_descriptor"] != "no":
                problems.append(
                    f"{feature}: reg_addr is {NO_ADDRESS} -- this repository "
                    "records no EC address for the feature "
                    "(ec/annotations/static-refs-audit.md names these) -- so "
                    "the descriptor cannot claim it. in_descriptor is "
                    f"{row['in_descriptor']!r}.")
            continue
        if not re.fullmatch(r"0x[0-9A-Fa-f]{4}", addr):
            problems.append(
                f"{feature}: reg_addr {addr!r} is neither a 0xNNNN address nor "
                f"the {NO_ADDRESS!r} sentinel.")
            continue
        if int(addr, 16) not in statuses:
            problems.append(
                f"{feature}: reg_addr {addr} is not an address "
                f"registers.yaml records, so there is no status to agree with.")
            continue
        recorded = statuses[int(addr, 16)]
        if (split_status(status, suffixes)[0]
                != split_status(recorded, suffixes)[0]):
            problems.append(
                f"{feature}: registers_status is {status!r} but registers.yaml "
                f"records {recorded!r} for {addr}.")
    return problems


def rule_base_commit(patch_rev):
    """Rule 3: BASE_COMMIT, the nix rev and the patch header agree."""
    problems = []
    base, pinned = base_rev(), nix_rev()
    if not base:
        problems.append(f"{BASE_COMMIT} records no rev.")
    if base and pinned and base != pinned and not pinned.startswith(base):
        problems.append(
            f"{BASE_COMMIT} names {base} but {NIX} fetches {pinned}. The nix "
            "recipe is the build, so a patch cut against a rev the build does "
            "not use is a patch nobody can reproduce.")
    if patch_rev is not None:
        known = {base, pinned} - {""}
        if patch_rev not in known and not any(
                k.startswith(patch_rev) or patch_rev.startswith(k)
                for k in known):
            problems.append(
                f"the patch header names rev {patch_rev}, which is neither "
                f"{BASE_COMMIT} ({base}) nor the nix rev ({pinned}).")
    return problems


def rule_additive_only(removed):
    """Rule 4: the patch removes nothing.

    The one a `git apply --check` waves through. A re-cut that edits another
    board's row, or a shared bit, applies perfectly; it is the other boards
    that break, and no test in this repository or upstream's would notice.
    """
    if not removed:
        return []
    return [f"the patch removes {len(removed)} line(s), and this entry has to "
            "be additive only -- it is added to a table every other Uniwill "
            "board in it is matched against:\n  "
            + "\n  ".join(ln.rstrip() for ln in removed[:8])
            + ("\n  ..." if len(removed) > 8 else "")]


def rule_bits_agree(rows, bits):
    """Rule 5: the patch's bits and the map's included rows, both ways.

    Only a real `UNIWILL_FEATURE_*` name counts as a bit. A row that says
    `in_descriptor=yes` over the `unsourced` sentinel is naming no bit at all,
    so it cannot disagree with the diff -- rule 6 is what refuses that row, and
    reporting it here too would turn one mistake into two messages.
    """
    problems = []
    included = {row["upstream_bit"]: row["repo_feature"]
                for row in rows
                if row["in_descriptor"] == "yes"
                and BIT.fullmatch(row["upstream_bit"])}
    for bit in sorted(bits - set(included)):
        problems.append(
            f"the patch sets {bit}, which no feature-map row marks "
            "in_descriptor=yes. A bit in the diff with no evidence behind it "
            "is the overclaim this whole artifact exists to prevent.")
    for bit, feature in sorted(included.items()):
        if bit not in bits:
            problems.append(
                f"{feature} is marked in_descriptor=yes and names {bit}, but "
                "the patch never sets it. The evidence is in the map and the "
                "artifact does not carry it.")
    return problems


def rule_include(rows, values):
    """Rule 6: inclusion needs a confirmed status, a real address, a source."""
    problems = []
    for row in rows:
        if row["in_descriptor"] != "yes":
            continue
        feature = row["repo_feature"]
        base, _suffix = split_status(row["registers_status"], values[1])
        if not base.startswith("confirmed-"):
            problems.append(
                f"{feature}: in_descriptor=yes on status {base!r}. Only a "
                "confirmed-* status may be claimed in a descriptor; a static "
                "scan or an untested write is not a confirmed behaviour.")
        if row["reg_addr"] == NO_ADDRESS:
            problems.append(
                f"{feature}: in_descriptor=yes with no EC address recorded in "
                "this repository.")
        if row["upstream_bit"] == UNSOURCED:
            problems.append(
                f"{feature}: in_descriptor=yes with no sourced bit spelling. "
                "The descriptor names an upstream constant; naming one this "
                "repository cannot source is inventing it.")
    return problems


def rule_bit_sourcing(rows, patch_bits_set, base):
    """Rule 7: every bit spelling is backed by a file or by the patch."""
    problems = []
    for row in rows:
        bit, source = row["upstream_bit"], row["bit_source"]
        if bit == UNSOURCED:
            if source:
                problems.append(
                    f"{row['repo_feature']}: upstream_bit is {UNSOURCED} but "
                    f"bit_source names {source!r}. An unsourced spelling has "
                    "no source to name.")
            continue
        if not BIT.fullmatch(bit):
            problems.append(
                f"{row['repo_feature']}: upstream_bit {bit!r} is not a "
                "UNIWILL_FEATURE_* name.")
            continue
        if not source:
            problems.append(
                f"{row['repo_feature']}: {bit} is given with no bit_source, so "
                "nothing says where the spelling came from. Name the committed "
                f"file that quotes it, or upstream@{base}.")
            continue
        upstream = UPSTREAM_SOURCE.match(source)
        if upstream:
            if not patch_bits_set or bit not in patch_bits_set:
                problems.append(
                    f"{row['repo_feature']}: {bit} claims {source}, but the "
                    "patch does not set it. A spelling read off the driver has "
                    "to be backed by the diff that uses it, or it is a name "
                    "with nothing behind it.")
            continue
        try:
            quoted = read_text(source)
        except OSError:
            problems.append(
                f"{row['repo_feature']}: bit_source {source!r} is not a file in "
                "this repository.")
            continue
        if bit not in quoted:
            problems.append(
                f"{row['repo_feature']}: bit_source {source} does not quote "
                f"{bit}. If the spelling moved, point at the file that has it; "
                "do not leave the citation behind the rename.")
    return problems


def rule_pr_body(text, rows):
    """Rule 8: the PR body carries the board identity and no stray bit."""
    problems = []
    for needed in ("0x0F", "PCSpecialist", "TongFang", "GM7MG7P"):
        if needed not in text:
            problems.append(
                f"{PR_BODY} does not mention {needed}. The board identity in "
                "docs/hardware-identity.md is what the row is matched on, and "
                "a PR body without it cannot be reviewed for correctness.")
    known = {row["upstream_bit"] for row in rows if row["upstream_bit"]}
    for bit in sorted(set(BIT.findall(text)) - known):
        problems.append(
            f"{PR_BODY} names {bit}, which no feature-map row carries. Prose "
            "is the last place a claim can outlive the evidence for it.")
    return problems


# --- the run ----------------------------------------------------------------

def check():
    """Every rule, against the committed files. Returns the refusals."""
    problems = []
    try:
        rows = read_map()
    except (OSError, ValueError) as exc:
        # A refusal, not a traceback. A map whose header no longer matches is
        # the same class of thing as a map with a status the vocabulary does
        # not declare, and reporting it as one keeps `--check` a thing that
        # answers rather than a thing that crashes.
        return [f"{MAP}: {exc}"]
    values = declared_statuses()
    if values is None:
        return [f"{REGISTERS}'s header comment declares no status value, so "
                "there is no vocabulary to check the map against."]
    statuses = registers_index()
    base = base_rev()

    problems += rule_vocabulary(rows, values[0], values[1])
    problems += rule_addresses(rows, statuses, values[1])

    patch_path = os.path.join(REPO, PATCH)
    bits, header_rev = set(), None
    if os.path.exists(patch_path):
        header, added, removed = patch_parts(read_text(PATCH))
        bits = patch_bits(added)
        named = REV.findall(header)
        header_rev = named[0] if named else None
        if header_rev is None:
            problems.append(
                f"{PATCH} carries no header comment naming the base rev, so "
                "rule 3's third leg has nothing to compare. Give it the `#` "
                "header the patches in docs/ci/ carry -- a patch cut against "
                "an unrecorded rev cannot be re-derived by the next reader.")
        problems += rule_additive_only(removed)
        problems += rule_bits_agree(rows, bits)
    else:
        # Rules 3's third leg, 4 and 5 read a file that is not here. Saying so
        # is the difference between "the artifact is incomplete" and "the
        # checker passed", which look identical from outside and are not.
        print(f"INCOMPLETE  {PATCH} is not committed.")
        print("  It is the one deliverable here that needs the network: it is")
        print("  cut against uniwill-acpi.c at BASE_COMMIT, which this")
        print("  repository does not vendor, and which could not be fetched")
        print("  when this was written. Rules 3 (third leg), 4 and 5 are")
        print("  skipped until it exists, and the run is not a pass without it.")
        print("  To produce it, and then re-run this:")
        print("    curl -fsSL -o /tmp/uw.tar.gz \\")
        print("      https://codeload.github.com/Wer-Wolf/uniwill-laptop/"
              "tar.gz/" + base)
        print("    tar xzf /tmp/uw.tar.gz -C /tmp && see README.md")
        print("  The rows that would then become includable are named in the")
        print("  map's `unsourced` cells, one per feature.")
        print("  Every other rule below ran, and the map-level results stand.")
        # A refusal, not only a banner, so `--check` is red and not merely
        # noisy. The directory's deliverable is the patch; a checker that
        # passed over the directory without one would be reporting on an
        # artifact that does not exist yet.
        problems.append(
            f"{PATCH} is not committed, so the prepared entry does not exist "
            "yet. Rules 3 (third leg), 4 and 5 could not run. This is the one "
            "refusal here that is about a missing file rather than an "
            "unsupported claim.")

    problems += rule_base_commit(header_rev)
    problems += rule_include(rows, values)
    problems += rule_bit_sourcing(rows, bits, base)
    if os.path.exists(os.path.join(REPO, PR_BODY)):
        problems += rule_pr_body(read_text(PR_BODY), rows)
    else:
        problems.append(f"{PR_BODY} is not committed.")

    counts = {
        "rows": len(rows),
        "included": sum(1 for r in rows if r["in_descriptor"] == "yes"),
        "sourced bits": sum(1 for r in rows
                            if r["upstream_bit"] not in (UNSOURCED, "")),
        "patch": os.path.exists(patch_path),
    }
    print(f"{counts['rows']} feature rows, {counts['included']} in the "
          f"descriptor, {counts['sourced bits']} with a bit spelling this "
          f"repository can source; patch committed: {counts['patch']}.")
    print("include rule: in_descriptor=yes needs a confirmed-* status, an "
          "address registers.yaml records, and a sourced bit.")
    # Flushed before the refusals so the two streams cannot arrive out of
    # order: stdout is block-buffered when it is a pipe, so without this the
    # INCOMPLETE banner above lands *after* the refusals it introduces, and
    # the run reads as if the missing patch were an afterthought.
    sys.stdout.flush()
    for problem in problems:
        print(f"  REFUSED  {problem}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} refusal(s). A refusal is a claim this "
              "repository cannot back, not an argument that it is wrong.",
              file=sys.stderr)
    return problems


def self_test():
    """The refusals themselves, each against the mutation it is meant to catch.

    Fixtures, not the committed rows: a rule tested only against the data it
    was written for is not tested, and these rows will move -- issue #1, #3
    and #4 all own statuses this map cites. A check that has quietly stopped
    refusing looks exactly like a check that is working.
    """
    statuses = {0x043E: "confirmed-working", 0x07B9: "unknown-not-absent",
                0x07A6: "confirmed-working-partially",
                0x07D0: "unknown-not-absent-DO-NOT-WRITE-BLIND"}
    values = ["confirmed-working", "confirmed-working-partially",
              "unknown-not-absent", NO_ADDR_STATUS]
    suffixes = ["-DO-NOT-WRITE-BLIND"]
    failures = []

    def check_that(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    def row(feature="F", bit=UNSOURCED, source="", addr="0x043E",
            status="confirmed-working", verdict="v", include="no"):
        return {"repo_feature": feature, "upstream_bit": bit,
                "bit_source": source, "reg_addr": addr,
                "registers_status": status, "verdict": verdict,
                "in_descriptor": include, "reason": "r"}

    def refused(rules, *args):
        return bool(rules(*args))

    # --- rule 1 -------------------------------------------------------------
    check_that("an undeclared status is refused",
               refused(rule_vocabulary, [row(status="confirmed-wroking")],
                       values, suffixes),
               "(a typo, or a value invented rather than taken from the file)")
    check_that("a declared status passes",
               not refused(rule_vocabulary, [row()], values, suffixes))
    check_that("a DO-NOT-WRITE-BLIND status is not refused as undeclared",
               not refused(rule_vocabulary,
                           [row(addr="0x07D0",
                                status="unknown-not-absent-DO-NOT-WRITE-BLIND")],
                           values, suffixes),
               "(the suffix is stripped before the vocabulary is consulted, so "
               "a suffixed status is graded, not spelled wrong)")
    check_that("the no-address sentinel passes rule 1",
               not refused(rule_vocabulary,
                           [row(addr=NO_ADDRESS, status=NO_ADDR_STATUS)],
                           values, suffixes),
               "(it is a declared value of this tool's own, not a registers.yaml "
               "status read as one)")
    check_that("the committed header parses to a non-empty vocabulary",
               bool((declared_statuses() or ([], []))[0]),
               "(if this is red the block in registers.yaml moved, was "
               "re-indented or was re-cased, and rule 1 would be refusing every "
               "row against an empty list)")

    # --- rule 2 -------------------------------------------------------------
    check_that("an address registers.yaml does not record is refused",
               refused(rule_addresses, [row(addr="0x0999")], statuses, suffixes),
               "(a register that is not in the corpus has no status to agree "
               "with, so the row is claiming against nothing)")
    check_that("a status that disagrees with registers.yaml is refused",
               refused(rule_addresses,
                       [row(addr="0x07B9", status="confirmed-working")],
                       statuses, suffixes),
               "(the 0x07B9 case: a `absent`-shaped status typed in by hand and "
               "left behind by a later registers.yaml edit)")
    check_that("a status that agrees passes",
               not refused(rule_addresses,
                           [row(addr="0x07B9", status="unknown-not-absent")],
                           statuses, suffixes),
               "(the 0x07B9 case, and the shape rule 2 exists for: the map "
               "agrees with registers.yaml rather than restating it)")
    check_that("a suffixed status in the map is graded on its base",
               not refused(rule_addresses,
                           [row(addr="0x07D0",
                                status="unknown-not-absent-DO-NOT-WRITE-BLIND")],
                           statuses, suffixes))
    check_that("no address recorded but a real status given is refused",
               refused(rule_addresses,
                       [row(addr=NO_ADDRESS, status="confirmed-working")],
                       statuses, suffixes),
               "(there is no address to read the status off, so the cell is "
               "claiming a grade for a byte this repository has not located)")
    check_that("no address recorded and the row claims inclusion is refused",
               refused(rule_addresses,
                       [row(addr=NO_ADDRESS, status=NO_ADDR_STATUS,
                            include="yes")],
                       statuses, suffixes),
               "(this is the PRIMARY_FAN shape, and the refusal is the point: "
               "the feature works, but nothing here says which byte)")
    check_that("a malformed address is refused",
               refused(rule_addresses, [row(addr="7b9")], statuses,
                        suffixes))

    # --- rule 3 -------------------------------------------------------------
    base, pinned = base_rev(), nix_rev()
    check_that("BASE_COMMIT names a rev", bool(base) and bool(REV.fullmatch(base)),
               f"(read as {base!r})")
    check_that("BASE_COMMIT and the nix recipe agree",
               pinned.startswith(base) or base.startswith(pinned),
               f"({base} vs {pinned}; the nix recipe is the build, so these "
               "are the same rev or one is stale)")
    check_that("a patch header naming an unrelated rev is refused",
               refused(rule_base_commit, "deadbee"),
               "(the patch is cut against something the build never fetches)")

    # --- rule 4 -------------------------------------------------------------
    added_only = [" \t{ 0x0F }, /* GM7MG7P */", " \t};"]
    check_that("a patch that only adds lines is not refused",
               not refused(rule_additive_only, []))
    check_that("a patch removing a line is refused",
               refused(rule_additive_only, ["-\t{ 0x0A }, /* another board */"]),
               "(a re-cut that edits another board's row applies perfectly and "
               "breaks every other Uniwill machine, and git apply says nothing)")
    check_that("the --- file header is not read as a removed line",
               not refused(rule_additive_only, patch_parts(
                   "diff --git a/u.c b/u.c\n--- a/u.c\n+++ b/u.c\n"
                   "@@ -1 +1 @@\n+\tnew line\n")[2]),
               "(without this every patch in the tree would be red)")

    # --- rule 5 -------------------------------------------------------------
    # Two rows, both included. Rule 5's two directions cannot both be
    # provoked with one row each, because a single mismatch trips whichever
    # side it is on: a patch bit with no included row *and* an included row
    # the patch never sets are the same single-bit edit seen from two ends.
    rows = [row(feature="BATTERY_CHARGE_MODES", bit="UNIWILL_FEATURE_X",
                include="yes"), row(feature="CPU_TEMP", bit="UNIWILL_FEATURE_Y",
                                    include="yes")]
    check_that("a patch bit with no included row is refused",
               refused(rule_bits_agree, rows, {"UNIWILL_FEATURE_Z"}),
               "(claimed in the diff, evidenced nowhere)")
    check_that("an included row the patch never sets is refused",
               refused(rule_bits_agree, rows, {"UNIWILL_FEATURE_X"}),
               "(evidenced in the map, missing from the artifact -- the "
               "opposite direction, and a different bug)")
    check_that("a patch and a map that agree are not refused",
               not refused(rule_bits_agree, rows,
                           {"UNIWILL_FEATURE_X", "UNIWILL_FEATURE_Y"}))
    check_that("an excluded row's bit in the patch is not a disagreement here",
               refused(rule_bits_agree,
                       [row(feature="CPU_TEMP", bit="UNIWILL_FEATURE_Y")],
                       {"UNIWILL_FEATURE_Y"}),
               "(a bit the map does not mark included is rule 5's *first* "
               "direction: the diff is claiming something the map does not "
               "endorse, and that is the failure to report, not a pass)")
    check_that("an included row naming the unsourced sentinel is not counted "
               "as a bit",
               not refused(rule_bits_agree,
                           [row(feature="CPU_TEMP", include="yes"),
                            row(feature="FAN", bit="UNIWILL_FEATURE_X",
                                include="yes")],
                           {"UNIWILL_FEATURE_X"}),
               ("`unsourced` is not a bit name, so it cannot disagree with the "
               "diff in either direction; rule 6 is what refuses that row, and "
               "rule 7 what says the name is missing"))

    # --- rule 6 -------------------------------------------------------------
    check_that("inclusion on a non-confirmed status is refused",
               refused(rule_include,
                       [row(bit="UNIWILL_FEATURE_X", addr="0x07B9",
                            status="unknown-not-absent", include="yes")], values),
               "(this is BATTERY_CHARGE_LIMIT, and it is the rule that keeps it "
               "out -- `unknown-not-absent` is not a weaker confirmed-*, it is a "
               "different statement)")
    check_that("inclusion on present-untested is refused",
               refused(rule_include,
                       [row(bit="UNIWILL_FEATURE_X", addr="0x043E",
                            status="present-untested", include="yes")], values))
    check_that("inclusion on a confirmed-* status with everything else present "
               "is not refused",
               not refused(rule_include,
                           [row(bit="UNIWILL_FEATURE_X", include="yes")],
                           values),
               "(BATTERY_CHARGE_MODES: the one shape that is allowed through)")
    check_that("inclusion without a sourced bit is refused",
               refused(rule_include, [row(include="yes")], values),
               "(confirmed-working and nothing else -- a bit name this "
               "repository cannot source is the invention rule 7 exists for)")
    check_that("inclusion with no address recorded is refused",
               refused(rule_include,
                       [row(bit="UNIWILL_FEATURE_X", addr=NO_ADDRESS,
                            status=NO_ADDR_STATUS, include="yes")], values))

    # --- rule 7 -------------------------------------------------------------
    rev = base
    check_that("a bit with no source at all is refused",
               refused(rule_bit_sourcing, [row(bit="UNIWILL_FEATURE_X")],
                       set(), rev),
               "(a spelling with nothing saying where it came from)")
    check_that("a bit citing a file that does not quote it is refused",
               refused(rule_bit_sourcing,
                       [row(bit="UNIWILL_FEATURE_X", source=NIX)],
                       set(), rev),
               "(a citation left behind by a rename reads exactly like a "
               "sourced name and is not one)")
    check_that("a bit citing a file that is not in the repository is refused",
               refused(rule_bit_sourcing,
                       [row(bit="UNIWILL_FEATURE_X", source="linux/nope.md")],
                       set(), rev))
    check_that("a real upstream@ citation with the patch behind it passes",
               not refused(rule_bit_sourcing,
                           [row(bit="UNIWILL_FEATURE_X",
                                source=f"upstream@{rev}")],
                           {"UNIWILL_FEATURE_X"}, rev),
               "(the route a human takes once the source is fetched: name the "
               "rev it was read at, and the diff has to agree)")
    check_that("an upstream@ citation with no patch behind it is refused",
               refused(rule_bit_sourcing,
                       [row(bit="UNIWILL_FEATURE_X",
                            source=f"upstream@{rev}")],
                       set(), rev),
               ("upstream@<rev> is not a licence to assert a spelling; without "
                "the diff it is an unverifiable name)"))
    check_that("the two charge bits are sourced from the file that quotes them",
               not refused(rule_bit_sourcing,
                           [row(bit="UNIWILL_FEATURE_BATTERY_CHARGE_MODES",
                                source="linux/patches/README.md")],
                           set(), rev),
               "(linux/patches/README.md quotes both charge spellings, which is "
               "the only reason the map has any sourced bit at all)")
    check_that("an unsourced cell must not name a source",
               refused(rule_bit_sourcing,
                       [row(bit=UNSOURCED, source="linux/patches/README.md")],
                       set(), rev),
               ("`unsourced` plus a citation reads as sourced, and is the one "
                "combination that would make rule 7 look satisfied on nothing)"))
    check_that("a name that is not a UNIWILL_FEATURE_* is refused",
               refused(rule_bit_sourcing,
                       [row(bit="FAN", source="linux/patches/README.md")],
                       set(), rev))

    # --- rule 8 -------------------------------------------------------------
    body = ("0x0F, PCSpecialist, TongFang GM7MG7P and "
            "UNIWILL_FEATURE_BATTERY_CHARGE_MODES")
    map_rows = [row(feature="BATTERY_CHARGE_MODES",
                    bit="UNIWILL_FEATURE_BATTERY_CHARGE_MODES")]
    check_that("a complete PR body is not refused",
               not refused(rule_pr_body, body, map_rows))
    check_that("a PR body missing the project id is refused",
               refused(rule_pr_body, body.replace("0x0F", "0F"), map_rows),
               "(the row is matched on the id, so a body without it cannot be "
               "reviewed for correctness)")
    check_that("a PR body naming a bit the map does not is refused",
               refused(rule_pr_body, body + " and UNIWILL_FEATURE_WHATEVER",
                       map_rows),
               ("prose is the last place a claim can outlive the evidence for "
                "it, because a diff is read and a paragraph is skimmed)"))

    # --- the parse ----------------------------------------------------------
    check_that("the patch parse separates header, added and removed",
               patch_parts(
                   "# base rev 5a24248\n"
                   "diff --git a/u.c b/u.c\n--- a/u.c\n+++ b/u.c\n@@ -1 +1 @@\n"
                   "-\told\n+\tnew with UNIWILL_FEATURE_X\n")
               == ("# base rev 5a24248\n",
                   ["\tnew with UNIWILL_FEATURE_X"], ["\told"]),
               "(a header cut *before* `diff --git`, a `---` that is not a "
               "removal and a `+++` that is not an addition -- the three that "
               "make a naive parse wrong in the direction that matters)")
    check_that("a patch with no header comment yields an empty header, not the "
               "whole file",
               patch_parts("diff --git a/u.c b/u.c\n--- a/u.c\n")[0] == "",
               "(every patch under docs/ci/ and linux/patches/ is written one "
               "way or the other, and reading the other as a header would put "
               "the whole diff into rule 3's rev search)")

    if failures:
        for failure in failures:
            print(f"  FAIL  {failure}")
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on a claim this repository cannot back, or on "
                         "the prepared patch not being committed; the default "
                         "run prints the same refusals and exits 0")
    ap.add_argument("--self-test", action="store_true",
                    help="pin every rule against the mutation it is meant to "
                         "catch")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    problems = check()
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())
