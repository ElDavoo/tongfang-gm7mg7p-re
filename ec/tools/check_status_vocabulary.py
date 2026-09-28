#!/usr/bin/env python3
r"""Check `ec/annotations/registers.yaml`'s `status:` values against the rules
its own header comment states, and print the sweep the PD-only question is
asked over.

`check_register_counts.py` holds the *numbers*: it recomputes every
`static_refs*` from the committed image and fails on a mismatch, and its
docstring says in as many words that it says nothing about whether a status is
right. This is the other half, and it is a new file rather than a mode on that
one for the reason CLAUDE.md gives -- a second question, a second set of rules.

**Three rules, all transcribed from the header comment, none of them new.**

  1. **Vocabulary closure.** Every `status:` is a value the header declares,
     optionally carrying a declared suffix (`-DO-NOT-WRITE-BLIND`). The
     declared list is *parsed out of that comment* rather than carried here:
     the comment is the single source of truth, and a second copy of it in
     this file is exactly how the two drift apart silently again. Issue #32
     found three forms the file uses and the comment never declared
     (`confirmed-working-partially`, `confirmed-not-this-mechanism`, and the
     suffix) -- a list nothing checked was a list nothing kept true.
  2. **Count warrant.** `present-untested` is the one value whose entire
     warrant is a reference count, so it requires `static_refs_main_ec` >= 1
     for *every* address in the entry. `0x07CC` carried it with six sites and
     none of them EC-side; the grade read as "the EC implements this, nobody
     has tried it", which is the claim the image split emptied. The rule is
     stated per address rather than per entry so a partly-split entry is
     caught on the address that fails, and not excused by a neighbour that
     passes.
  3. **Resolution warrant** (issue #1105). Rule 2 asks whether an EC-side
     site *exists*; this asks what the site is *worth*, and the two are not
     the same question -- widening rule 2 to cover it would make it a rule
     about something other than the reference count, which is what rule 2's
     own contract says it is. A `present-untested` address must have at least
     one EC-side site that `register_ref_table.py --callee-depth 1` resolves
     to a read, a write, or both. Those verdicts are read out of the
     committed `ec/annotations/site-resolution.csv`, so this tool still opens
     no image; the census behind it is `ec/tools/check_site_resolution.py`.

**The two exemptions are the part that must not be quietly dropped.**
`confirmed-working`, `confirmed-working-partially`, `confirmed-inert` and
`confirmed-not-this-mechanism` are live-warranted and exempt from rule 2,
because a live observation is a different kind of evidence from a scan: a
direct `MOV DPTR` scan cannot see a byte reached through indirect addressing,
and this repo has already paid for insisting that it could. `0x07B9` is a
byte Windows demonstrably writes and works, with zero direct sites anywhere in
the image (the §4c retraction), and `0x0748`-`0x074B` is a live-refuted
mechanism with no site in either image. A rule demanding EC-side sites of
either would re-introduce that error. `LIGHTBAR_AC_CTRL / RED / GREEN /
BLUE` is the committed proof the exemption has a user, so the exemption is
stated rather than implied -- and `--self-test` pins the case that would
re-introduce the error.

Rule 3's exemption is one entry and is a *tool* limit rather than an evidence
one, which is why it is named rather than reasoned around. `XDATA_0420`'s
single EC-side site hands the address across a `ret` in R1:R2 instead of
through an `lcall`, and `resolve_handoff()` models a DPTR passed to a call --
so the verdict is what the instrument cannot follow, not what the byte is.
#1103 owns the R1:R2 propagation; **when `0x0420`'s direction is established,
this exemption is deleted**, and the refusal below reappears with it.

**What this does not check, which is as much of the point:**

  * *Whether a status is the right grade.* All three rules are about the shape
    of a claim, never its strength. Nothing here distinguishes a well-argued
    `present-untested` from a badly-argued one, and rule 3 passing is not a
    status being correct. A resolved direction is a static instruction, not
    evidence the EC acts on the byte, so rule 3 moving no `status:` is the
    rule working, not the rule doing nothing.
  * *Whether the counts are right, or whether the census is.* That is
    `check_register_counts.py` and `check_site_resolution.py --check` and the
    image; this tool opens no image. Run the three together, because a status
    can satisfy rules 2 and 3 against a census that no longer describes the
    firmware. An address with no row in the census at all is reported rather
    than passed, so a missing or truncated table cannot make this rule pass
    vacuously.
  * *`absent` on a zero-in-both-images count.* Two entries carry it, while
    `0x07B9`, `0x07C7` and `0x07C8` carry `unknown-not-absent` on the
    identical shape. That is a second decision about a second value, recorded
    as a follow-up in the same write-up; folding it in here would make this
    tool a rule about something the header does not state.

**Corrected 2026-09-28 (issue #1105): this file no longer leaves "what a site
is worth once found" open.** It used to carry a fourth bullet saying exactly
that, and naming `0x0420` as the clearest case of an entry resting on a single
site that resolves no further -- the question two documents had deferred to
each other (`pd-only-status-vocabulary.md` 2, `walk-flow-follow.md` 4).
Rule 3 is the answer, `docs/findings/handoff-site-warrant.md` is the
reasoning, and the wrong sentence is left standing there beside its
correction per `docs/findings.md` §4a-4d rather than deleted from the record.

Usage:
    python3 ec/tools/check_status_vocabulary.py --check
    python3 ec/tools/check_status_vocabulary.py --self-test
"""
import argparse
import csv
import os
import re
import sys

import yaml

# `as_list` is imported rather than rewritten: it is how the sibling checker
# reads a scalar-or-list YAML value, and the two must not come to disagree
# about what a bare `static_refs_main_ec: 0` on a four-address entry means.
# `check_capture_names.py` imports `WATCH` from `check_capture_claims.py` for
# the same reason. `RESOLVED` and the two unresolved labels come from
# `check_site_resolution.py` for the same third reason: which labels count as
# a resolved direction is that tool's judgement, and a second copy of the
# list in this file is how a renamed label would leave rule 3 passing against
# a census it no longer understands. Importing it opens no image.
from check_register_counts import as_list
from check_site_resolution import (COMMITTED_CSV as SITE_CSV, RESOLVED,
                                   UNRESOLVED_HANDOFF, UNRESOLVED_NONE)

DEFAULT_YAML = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            os.pardir, "annotations", "registers.yaml")

SPLIT_KEYS = ("static_refs_main_ec", "static_refs_pd_image")

# The header block: `# status values:` opens it and the first non-comment line
# closes it, so the two rules written below it are not declarations. Three
# spaces is the file's own `#   value   : gloss` column and a continuation
# line is indented further, which is what keeps a gloss's own words out of the
# list; the two name shapes are how a value and the one suffix convention are
# told apart, and they are the file's too -- values are lower case, the suffix
# is upper case. Both matter: a re-indented or re-cased block is then a block
# this declares nothing, which is reported as missing rather than read as an
# empty vocabulary that would refuse every entry for an unrelated reason.
STATUS_BLOCK = re.compile(r"^#\s*status values:\s*$")
DECLARED = re.compile(r"^# {3}(-[A-Z0-9-]+|[a-z][a-z0-9-]*)\s+:\s")

# The statuses whose warrant is a live observation, and so are exempt from the
# count rule. Named here rather than parsed, because the header states the
# exemption in prose and prose is not a list; `--check` prints these beside the
# rule they exempt, so a change to either is visible in the output rather than
# silent.
LIVE_WARRANTED = ("confirmed-working", "confirmed-working-partially",
                  "confirmed-inert", "confirmed-not-this-mechanism")

# The one value whose warrant is the count itself.
COUNT_WARRANTED = ("present-untested",)

# Rule 3's one exemption, named rather than reasoned around, with the reason it
# is a limit of the instrument instead of a property of the byte. Keyed on the
# entry name because that is what registers.yaml calls it and what a reader
# will grep for; a name that no longer exists is a stale exemption, which is
# reported below rather than silently ignored.
RESOLUTION_EXEMPT = {
    "XDATA_0420":
        "its single EC-side site hands the address across a `ret` in R1:R2 "
        "rather than through an lcall, and --callee-depth models a DPTR passed "
        "to a call, so the unresolved verdict is a limit of the tool (#1103) "
        "and not evidence about the byte. Delete this exemption when 0x0420's "
        "direction is established",
}


def parse_declared(text):
    """(values, suffixes) out of the header comment in `text`.

    `None` when the block declares nothing: a file whose header no longer
    declares its values has not been narrowed, it has lost the list, and
    carrying on with an empty vocabulary would report every entry as
    undeclared while saying nothing about which is which.
    """
    values, suffixes, in_block = [], [], False
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        if STATUS_BLOCK.match(line):
            in_block = True
            continue
        if not in_block:
            continue
        m = DECLARED.match(line)
        if m:
            (suffixes if m.group(1).startswith("-") else values).append(
                m.group(1))
    return (values, suffixes) if values else None


def declared_statuses(path):
    """(values, suffixes) parsed out of the header comment of `path`."""
    with open(path) as f:
        return parse_declared(f.read())


def split_status(status, suffixes):
    """(base value, suffix or None) for one `status:` cell.

    Only a *declared* suffix is stripped, so an undeclared one is left on and
    is then refused as an undeclared value rather than being read as part of a
    name that happens to be declared. A suffix never changes which rule
    applies: `present-untested-DO-NOT-WRITE-BLIND` is still held to the count
    rule, and would have been had there been no suffix.
    """
    for suffix in suffixes:
        if status.endswith(suffix) and len(status) > len(suffix):
            return status[:-len(suffix)], suffix
    return status, None


def addrs_and_sites(entry):
    """[(address, main_ec, pd_image)] one per address, `None` where the entry
    records no count. `None` is kept rather than turned into a zero: "not
    audited" and "audited, no site" have to stay distinguishable, which is the
    same reason `check_register_counts.py` requires both keys to be present.
    """
    addrs = entry["addr"] if isinstance(entry["addr"], list) else [entry["addr"]]
    n = len(addrs)
    main = as_list(entry.get("static_refs_main_ec"), n)
    pd = as_list(entry.get("static_refs_pd_image"), n)
    return list(zip(addrs, main, pd))


def audited(sites):
    return all(m is not None and p is not None for _, m, p in sites)


def is_pd_only(sites):
    """True when no address in the entry has an EC-side site and one has a
    PD-image one. Wholly-EC-side and no-sites-anywhere entries are not this;
    `is_partly_split` is what names that third shape."""
    return (audited(sites)
            and all(m == 0 for _, m, _ in sites)
            and any(p > 0 for _, _, p in sites))


def is_partly_split(sites):
    """True when the entry mixes EC-side and PD-only addresses. Reported as a
    census line rather than a refusal: a partly-split entry is a legitimate
    shape (`0x04A6` is 3 EC-side / 4 PD-side), and what the count rule refuses
    is one *graded* `present-untested` with an address that has no EC-side
    site -- a different thing that happens to be detectable here."""
    return (audited(sites)
            and any(m > 0 for _, m, _ in sites)
            and any(m == 0 and p > 0 for _, m, p in sites))


def load_resolutions(path: str = SITE_CSV):
    """address -> {resolution label: count}, from the committed site census.

    Read rather than re-derived so this tool keeps opening no image, which is
    the whole reason rule 3 is here at all: a check that had to decode the
    firmware could not run in the gate beside the two that already do.

    A malformed `addr` cell raises rather than being skipped. A census that
    silently dropped a row would leave the address looking like one with no
    site, and rule 3 would then pass it for the wrong reason -- the vacuous
    pass `tools/run-tests.sh` documents, one level up.
    """
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            addr = int(row["addr"], 16)
            tally = out.setdefault(addr, {})
            label = row["resolution"]
            tally[label] = tally.get(label, 0) + 1
    return out


def resolution_problems(entry, resolutions):
    """Rule 3's refusals for one entry, as a list of strings.

    Stated per address, for the same reason rule 2 is: an entry's worth comes
    from the weakest address in it, and a neighbour that resolves does not
    excuse one that does not.
    """
    name = entry.get("name", "?")
    problems = []
    if name in RESOLUTION_EXEMPT:
        return problems
    for addr, _main, _pd in addrs_and_sites(entry):
        tally = resolutions.get(addr)
        if not tally:
            # Rule 2 has already refused a `present-untested` with no EC-side
            # site, so reaching here with no row means the census and this
            # entry disagree. Reported rather than passed, because a passing
            # rule over a missing row is a rule that has stopped reading.
            problems.append(
                f"{name} 0x{addr:04X}: {COUNT_WARRANTED[0]} needs an EC-side "
                "site that resolves to a direction, and ec/annotations/"
                f"site-resolution.csv has no row for this address at all. "
                "Run check_site_resolution.py --check; a missing row is not a "
                "resolved one")
            continue
        if any(tally.get(label) for label in RESOLVED):
            continue
        tally_txt = ", ".join(f"{k} {v}" for k, v in sorted(tally.items()))
        problems.append(
            f"{name} 0x{addr:04X}: {COUNT_WARRANTED[0]} needs an EC-side site "
            f"that resolves to a direction and this address's sites resolve to "
            f"none ({tally_txt}). A DPTR handoff the callee's entry point "
            f"settles is a warrant; {UNRESOLVED_HANDOFF} and "
            f"{UNRESOLVED_NONE} are not -- a handoff is positive evidence the "
            "address is passed somewhere, a `none` cell is not evidence of "
            "anything. Neither is a statement that the EC does not touch the "
            f"byte: 0x07B9 is the standing counter-example. See "
            "docs/findings/handoff-site-warrant.md")
    return problems


def entry_problems(entry, values, suffixes, resolutions):
    """What one entry breaks, as a list of strings. Empty is a pass."""
    name = entry.get("name", "?")
    problems = []
    status = entry.get("status", "")
    base, _suffix = split_status(status, suffixes)
    if base not in values:
        problems.append(
            f"{name}: status {status!r} is not a value the header comment "
            f"declares (one of: {', '.join(values)}"
            + (f", optionally carrying {', '.join(suffixes)}" if suffixes else "")
            + ")")
        # The base is undeclared, so the count rule has nothing to key on.
        return problems
    if base not in COUNT_WARRANTED:
        return problems

    sites = addrs_and_sites(entry)
    missing = [k for k in SPLIT_KEYS if entry.get(k) is None]
    if missing:
        problems.append(
            f"{name}: {base} is warranted by a reference count and the entry "
            f"records no {', '.join(missing)}, so there is no count to warrant "
            "it with. check_register_counts.py holds the same requirement; an "
            "unaudited entry is not a clean one")
        return problems
    for addr, main, _pd in sites:
        if main < 1:
            problems.append(
                f"{name} 0x{addr:04X}: {base} is warranted by a reference "
                f"count and this address has static_refs_main_ec = {main}, so "
                "there is no EC-side site to warrant it with. A status whose "
                "warrant is a live observation (" + ", ".join(LIVE_WARRANTED)
                + ") is exempt from that; this is not one")
    # Rule 3 runs even when rule 2 already spoke: a refused entry is still an
    # entry a reader is being shown, and the second reason is a different one
    # from the first.
    problems.extend(resolution_problems(entry, resolutions))
    return problems


def stale_exemptions(regs):
    """Exemptions naming an entry that is gone, or one that would pass anyway.

    An exemption that stops being needed is the failure mode a named exemption
    has: nothing breaks, and the next reader inherits a carve-out for a case
    nobody remembers. Reported rather than removed, because deleting a rule is
    not this tool's call to make.
    """
    names = {e.get("name", "?") for e in regs}
    out = []
    for name, why in sorted(RESOLUTION_EXEMPT.items()):
        if name not in names:
            out.append(
                f"rule 3's exemption names {name}, which no entry carries any "
                "more. The carve-out outlived its case; delete it rather than "
                "leaving it to be inherited by the next reader")
        elif (name, "present-untested") not in {
                (e.get("name", "?"), e.get("status", "")) for e in regs}:
            out.append(
                f"rule 3's exemption names {name}, which no longer carries "
                f"present-untested: {why}. Delete the exemption, it is no "
                "longer holding anything")
    return out


def report(regs, values, suffixes, resolutions):
    """Print the PD-only sweep, then return the refusals."""
    problems = []
    pd_only = 0
    for entry in regs:
        problems.extend(entry_problems(entry, values, suffixes, resolutions))
        sites = addrs_and_sites(entry)
        if is_pd_only(sites):
            pd_only += 1
            addrs = " ".join(f"0x{a:04X}" for a, _, _ in sites)
            print(f"  {addrs:<32} {entry.get('status', ''):<41} {entry['name']}")
    partly = sum(1 for e in regs if is_partly_split(addrs_and_sites(e)))
    print(f"{len(regs)} entries: {pd_only} PD-only (no EC-side site on any "
          f"address, at least one PD-image site), {partly} partly split. "
          "Every PD-only entry is listed above with the status it carries.")
    print(f"count rule: {', '.join(COUNT_WARRANTED)} needs static_refs_main_ec "
          ">= 1 on every address; exempt, because their warrant is a live "
          f"observation: {', '.join(LIVE_WARRANTED)}")
    unresolved = sorted(a for a in resolutions
                        if not any(resolutions[a].get(l) for l in RESOLVED))
    print(f"resolution rule: {', '.join(COUNT_WARRANTED)} needs one EC-side "
          f"site per address that resolves to {', '.join(RESOLVED)}; "
          f"{len(unresolved)} address(es) in the census resolve to nothing"
          + (f" ({', '.join(f'0x{a:04X}' for a in unresolved)}), held by the "
             f"named exemption: {', '.join(sorted(RESOLUTION_EXEMPT))}"
             if unresolved and RESOLUTION_EXEMPT else ""))
    problems.extend(stale_exemptions(regs))
    for p in problems:
        print(f"  REFUSED  {p}", file=sys.stderr)
    if problems:
        print(f"{len(problems)} refusal(s). A refusal is a shape a status is "
              "not allowed to take, not an argument that the grade is wrong.",
              file=sys.stderr)
    return problems


def self_test():
    """The refusals themselves, the exemption, and the header parser.

    Fixtures, not the committed entries: a rule tested only against the data
    it was derived from is not tested, and the entries move -- several issues
    are open against this tree. A check that has quietly stopped refusing
    looks exactly like a check that is working.
    """
    values = ["present-untested", "unknown-not-absent", "absent",
              "confirmed-working", "confirmed-working-partially",
              "confirmed-inert", "confirmed-not-this-mechanism"]
    suffixes = ["-DO-NOT-WRITE-BLIND"]
    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append(f"{label} {detail}")

    def entry(name, addrs, main, pd, status):
        """One entry in the shape registers.yaml uses, with `main`/`pd` given
        per address so a four-address entry reads the same as a one-address
        one."""
        n = len(addrs)
        return {"name": name,
                "addr": addrs if n > 1 else addrs[0],
                "static_refs_main_ec": main if n > 1 else main[0],
                "static_refs_pd_image": pd if n > 1 else pd[0],
                "status": status}

    # A constructed census, not the committed one, for the reason the docstring
    # gives: a rule tested only against the data it was derived from is not
    # tested, and site-resolution.csv moves every time an entry's grade does.
    # The labels are `check_site_resolution.py`'s, so a rename there is a
    # failure here rather than a silent pass.
    census = {
        0x043E: {"read": 14},
        0x0402: {"read": 1, "write": 2},
        0x0743: {"read": 5, "read+write": 2},
        0x0744: {"read": 1},
        0x07E2: {"read": 7, "write": 4},
        0x07E3: {"read": 2, "write": 2},
        0x07E4: {"read": 3, "write": 1},
        0x07E5: {"read": 5, "write": 3},
        0x0400: {"write": 1, UNRESOLVED_HANDOFF: 3, UNRESOLVED_NONE: 1},
        0x0410: {UNRESOLVED_HANDOFF: 1},
        0x0420: {UNRESOLVED_NONE: 1},
        0x0408: {"write": 1, UNRESOLVED_NONE: 1},
    }

    def refused(e, status=None, sites=None):
        e = dict(e)
        if status is not None:
            e["status"] = status
        return bool(entry_problems(e, values, suffixes, sites or census))

    # --- rule 1: the header is the vocabulary ------------------------------
    header = "\n".join([
        "# a comment above the block, which is not a declaration",
        "# status values:",
        "#   present-untested     : static-scan finds real references",
        "#   unknown-not-absent   : the references belong to the PD image",
        "#                            and the EC image has none -- not absent",
        "#                            either, per the note above",
        "#   -DO-NOT-WRITE-BLIND   : a suffix any value above may carry",
        "# rule 1 prose in the same column, which is not a value: 1. Every",
        "# status is one of the values above",
        "",
        "registers:",
        "#   present-untested     : after the block closed, so not declared",
    ])
    check("the header's values are read out of the comment",
          parse_declared(header)[0] == ["present-untested", "unknown-not-absent"],
          "(the block opens at its own header line and stops at the first "
          "non-comment line, so the declaration below it is not counted)")
    check("a continuation line is not a declaration",
          "and" not in parse_declared(header)[0],
          "(`and the EC image has none` is indented further than the value "
          "column and carries no ` : `)")
    check("the declared suffix is read as a suffix, not a value",
          parse_declared(header)[1] == ["-DO-NOT-WRITE-BLIND"],
          "(case is what tells a suffix from a value, as it does in the file)")
    check("a block that declares nothing is reported as missing",
          parse_declared("# status values:\nregisters:\n") is None,
          "(an empty vocabulary would refuse every entry for an unrelated "
          "reason, which is not a check saying anything)")
    check("the committed header is parsed into a non-empty vocabulary",
          bool((declared_statuses(DEFAULT_YAML) or ([], []))[0]),
          "(if this is red the block moved, was re-indented or was re-cased, "
          "and --check would be refusing every entry against an empty list)")

    check("an undeclared value is refused",
          refused(entry("MADE_UP", [0x043E], [15], [0], "present-untestd")),
          "(a typo, or a value invented rather than taken from the file)")
    check("an undeclared suffix is refused",
          refused(entry("SUFFIXED", [0x043E], [15], [0],
                        "present-untested-WRITE-BLIND")),
          "(only a declared suffix is stripped, so this is refused as an "
          "undeclared value rather than read as `present-untested`)")
    check("a declared suffix on a count-warranted value still counts",
          not refused(entry("SUFFIXED_OK", [0x043E], [15], [0],
                            "present-untested-DO-NOT-WRITE-BLIND")),
          "(the suffix must not launder the grade it rides on)")

    # --- rule 2: a status whose warrant is a count needs EC-side sites ------
    # The committed shape this rule was written for: six sites, none EC-side,
    # graded on the count.
    check("PD-only present-untested is refused",
          refused(entry("PD_ONLY", [0x07CC], [0], [6], "present-untested")),
          "(the 0x07CC case)")
    # Per address, not per entry: one address with no EC-side site is enough,
    # and a neighbour with sites does not excuse it. This is the shape a
    # partly-split entry has -- 0x04A6's 3 EC-side / 4 PD-side is a
    # legitimate entry, and what the rule refuses is the *grade*, not the
    # shape.
    check("partly-split present-untested is refused",
          refused(entry("SPLIT", [0x07C4, 0x07D3], [5, 0], [3, 7],
                        "present-untested")),
          "(one of two addresses has no EC-side site)")
    check("a present-untested with no split counts is refused",
          refused({"name": "UNAUDITED", "addr": 0x043E,
                   "static_refs_pd_image": 0, "status": "present-untested"}),
          "(unaudited is not clean: `as_list(None, 1)` is `[None]`, and a "
          "`None` count must be refused rather than compared or read as zero)")
    check("a wholly EC-side present-untested is not refused",
          not refused(entry("EC_SIDE", [0x0743, 0x0744], [7, 1], [0, 0],
                            "present-untested")))
    check("a four-address present-untested with all four EC-side is not refused",
          not refused(entry("FOUR", [0x07E2, 0x07E3, 0x07E4, 0x07E5],
                            [15, 9, 4, 10], [0, 0, 0, 0],
                            "present-untested")))

    # --- the exemption, which is the half a future edit would drop ---------
    # The committed LIGHTBAR_AC_* entry: a live-refuted mechanism with no site
    # in either image. A rule that demanded sites of it would re-introduce the
    # error of the `absent` note in registers.yaml's header.
    for status in LIVE_WARRANTED:
        check(f"{status} with no EC-side site is not refused",
              not refused(entry("LIVE", [0x0748, 0x0749, 0x074A, 0x074B],
                                [0, 0, 0, 0], [0, 0, 0, 0], status)),
              "(0x0748-0x074B is live-refuted with zero sites in both images)")
    check("PD-only absent is not refused",
          not refused(entry("NO_SITES", [0x0726], [0], [0], "absent")),
          "(`absent` is not the count-warranted value; the question of whether "
          "it is the right grade on a zero-in-both count is a second decision "
          "and is left to the write-up)")
    check("PD-only unknown-not-absent is not refused",
          not refused(entry("PD_ONLY_OK", [0x07D0], [0], [254],
                            "unknown-not-absent")))

    # --- rule 3: a site has to be worth something once it is found ---------
    # The half of rule 2 that decides an entry is fine is not enough: 0x0402's
    # three sites are all handoffs, and a handoff that resolves one call away
    # is a plain store or load at the callee's entry.
    check("a present-untested whose sites resolve to a direction is not refused",
          not refused(entry("RESOLVED", [0x0402], [3], [0],
                            "present-untested")),
          "(1 read and 2 writes reached through the pair accessors -- a "
          "handoff the callee settles is a warrant, not a gap)")
    check("one resolved site among unresolved ones is enough",
          not refused(entry("MOSTLY_UNRESOLVED", [0x0408], [2], [7],
                            "present-untested")),
          "(the rule asks whether the address has a warrant, not whether "
          "every site resolves; 0x0408 is one of the ten issue #1105 names "
          "and the write-up says so)")
    check("an address whose only site is an unresolved handoff is refused",
          refused(entry("UNRESOLVED_HANDOFF", [0x0410], [1], [5],
                        "present-untested")),
          "(DPTR goes to 0x889E, whose entry point --callee-depth does not "
          "read as a direction; that is a limit of the method, not a store)")
    check("an address whose only site is a none cell is refused",
          refused(entry("UNRESOLVED_NONE", [0x0420], [1], [11],
                        "present-untested")),
          "(`no movx in window` is not evidence in either direction, which is "
          "why it cannot be the whole warrant for a grade)")
    check("the exemption holds the committed XDATA_0420 entry",
          not resolution_problems(
              entry("XDATA_0420", [0x0420], [1], [11], "present-untested"),
              census),
          "(the one committed user of rule 3's carve-out, held by name so the "
          "exemption is stated rather than implied)")
    check("the exemption is the R1:R2 handoff, not a blank cheque",
          "R1:R2" in RESOLUTION_EXEMPT["XDATA_0420"]
          and "1103" in RESOLUTION_EXEMPT["XDATA_0420"],
          "(the reason has to name the tool limit that causes it and the issue "
          "that owns removing it, or the carve-out outlives its case)")
    check("an exemption naming an entry that no longer exists is reported",
          any("XDATA_0420" in p for p in
              stale_exemptions([entry("OTHER", [0x043E], [14], [0],
                                      "present-untested")])),
          "(a named exemption that stops being needed breaks nothing, which "
          "is exactly why it has to be checked)")
    check("an address with no row in the census is refused, not passed",
          refused(entry("NOT_CENSUSED", [0x0999], [1], [0],
                        "present-untested")),
          "(a passing rule over a missing row is a rule that has stopped "
          "reading; the refusal names the check that produces the row)")
    check("a live-warranted value is not held to the resolution rule",
          not refused(entry("LIGHTBAR_AC", [0x0748, 0x0749, 0x074A, 0x074B],
                            [0, 0, 0, 0], [0, 0, 0, 0],
                            "confirmed-not-this-mechanism")),
          "(rule 3 keys on the count-warranted value, so a live-refuted byte "
          "with no site in either image is never held to it -- the exemption "
          "is on the value, not on the census)")

    # --- the census loader, which is what keeps this tool image-free -------
    check("the committed census parses into per-address label tallies",
          bool((lambda t: t and all(isinstance(v, dict) for v in t.values()))(
              load_resolutions(SITE_CSV))),
          "(an empty or malformed table would make rule 3 pass vacuously, so "
          "the loader is checked against the committed file even though the "
          "cases above are not)")
    check("the committed census has the one address the exemption names",
          0x0420 in load_resolutions(SITE_CSV),
          "(an exemption whose address has no row is a rule that cannot be "
          "exercised on the case it was written for)")

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
                    help="fail on an undeclared status, or on a "
                         "`present-untested` whose entry has no EC-side site "
                         "(the gate's entry point); the default run prints "
                         "the same sweep and exits 0")
    ap.add_argument("--registers", default=DEFAULT_YAML,
                    help="registers.yaml to check (default: the one beside "
                         "this tool)")
    ap.add_argument("--site-csv", default=SITE_CSV,
                    help="ec/annotations/site-resolution.csv to read rule 3's "
                         "verdicts from; a path is taken so the positive "
                         "control can run against a constructed copy without "
                         "editing the committed census")
    ap.add_argument("--self-test", action="store_true",
                    help="pin both rules, the exemption and the header "
                         "parser against constructed entries")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    declared = declared_statuses(args.registers)
    if declared is None:
        print(f"{args.registers}: the header comment declares no status value, "
              "so there is no vocabulary to check an entry against", file=sys.stderr)
        return 1
    values, suffixes = declared

    with open(args.registers) as f:
        regs = yaml.safe_load(f)["registers"]

    problems = report(regs, values, suffixes, load_resolutions(args.site_csv))
    if args.check and problems:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
