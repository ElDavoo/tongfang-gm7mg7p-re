#!/usr/bin/env python3
"""The two hand transcriptions `--self-test` is checked against, read back out
of the committed markdown instead of trusted from a literal table.

`disasm8051.py` holds `SELF_TEST` and `REL_SITES` as tuples typed into it, and
cites `ec/annotations/charge-profile-flow.md` and `ec/annotations/bank-call-audit.md`
§8 in a comment as where those rows were transcribed from. That is provenance,
not a check. Before this module, an edit to either `.md` left the literals
holding the old text, `--self-test` stayed green, and a green run said nothing
about the two files a reader is told it reads -- worse, the failure line named a
file the run had never opened. This is that read-back, and it is the only place
in the tree where those two comments become sentences about the code beside them.

No CLI and no `main()`, on purpose. `--self-test` imports this from inside its
own body, so the eleven tools under `ec/tools/` that `import disasm8051` for its
opcode tables do not grow a dependency on a markdown parser none of them has a
use for.

**The two files are in two different listing dialects**, which is why this is
decidable rather than a text-diff guess. `charge-profile-flow.md` writes in the
decoder's own style -- two spaces after the mnemonic, no space after the comma,
lowercase hex, `; trailing comments` -- while `bank-call-audit.md` §8 quotes
`r2 -a 8051` verbatim inside a `console` fence, with a space after the comma
and r2's box-drawing branch glyphs ahead of the address column. Reconciling
the prose would need a normaliser for both spacings, and that normaliser would
be the fragile part, so the branch sites compare on **bytes and target** -- read
from the hex column and the trailing `0x....` -- and never on the text. Two
dialects are a problem for a text diff, not for a byte diff.

**What is not covered here, and why: found by this method, not absent.** The 11
`BIT_SITES` and the `TEXTBOOK_BIT_SITES` pair have no committed transcription
to reconcile against -- `grep -rn "0xEDA4\\|0xeda4" --include=*.md .` returns
nothing, and `0x9287` appears in the annotations only as one end of an anchor
span, never as a transcription -- so they stay literals, which is the same
wording `registers.yaml`'s own caveat and `charge-profile-flow.md` §3 use. Nor
is the `paged_target()` page-rule edge here: it is arithmetic, deliberately
stated rather than transcribed. Writing a listing to hold the other groups
would be a transcription project, not a parsing one.

Nothing here reads firmware, opens a capture, opens an EC or reads back a
register: two committed markdown files and a hard-coded table.
"""
import re

CHARGE_PROFILE_FLOW = "charge-profile-flow.md"
BANK_CALL_AUDIT = "bank-call-audit.md"

# The section of BANK_CALL_AUDIT holding the four branch decodes REL_SITES was
# transcribed from, and the `8` the rest of the repository spells it by. Matched
# as a heading prefix rather than as a whole line so the title is free to be
# reworded, and taken to the *next* `## ` so the earlier sections' own console
# fences -- which quote the same `r2` sessions -- are not parsed as though
# they named these sites.
SECTION = "8"

# charge-profile-flow.md, the decoder's own dialect: address, a gap of at least
# two spaces, the instruction. The gap has a lower bound of two so the `; tail`
# cannot be read as the instruction when a comment sits close under the address,
# and the tail is optional and dropped -- SELF_TEST holds the text without it,
# and a comment is prose *about* an instruction rather than part of what the
# decoder has to reproduce.
_WINDOW_ROW = re.compile(r"^(0x[0-9a-f]{4})\s{2,}(\S.*?)\s*(?:;.*)?$")

# What stands in for bytes the transcription did not copy, both as a whole line
# and after an address. Dropped rather than compared, which is what lets a
# window's span be compared without either span having to cover an elision --
# `0xb141` closes the 0xB12C window and `0xb2f0` sits one past the 0xB2E2 one,
# and a comparison that required them would fail on a file that is right.
# Dropping is also the honest reading: an elision is the absence of a
# transcription, so requiring one would be asking for something no reader can
# supply. A `...` on an address a window *does* cover is a deletion, and the
# row-count comparison catches it as one.
_ELISION = "..."

# bank-call-audit.md §8, r2's `pd` output quoted verbatim. r2 pads the hex and
# text columns to fixed widths and prefixes the address column with box-drawing
# glyphs showing branch flow -- `┌─<`, `╎╎`, `└─>` -- so the leading run is
# matched as glyphs-and-spaces rather than guessed at. The address is r2's own
# 8 hex digits, not the 4 the decoder prints, and the bytes are r2's unpadded
# run (`20e007`, not `20 e0 07`).
_SECTION_ROW = re.compile(
    r"^[\s┌│├└╨─]*[<>]?\s*(0x[0-9a-f]{8})\s+((?:[0-9a-f]{2})+)\s+(\S.*?)\s*$")

# The branch target as r2 prints it, at the end of the text. For every address
# REL_SITES names this *is* the target, and it is the only part of the text
# worth comparing: r2's mnemonic spelling and its spacing are r2's, and the
# decoder's rendering of the same instruction is checked by SELF_TEST instead.
_SECTION_TARGET = re.compile(r"0x([0-9a-f]{4})\s*$")


def _fenced(text):
    """Yield (line, inside_a_fence) over `text`, on ``` toggles.

    A file with no fence at all is refused by the callers rather than parsed as
    an empty listing: an empty parse and a right answer have to be told apart
    before either can be compared against anything.
    """
    inside = False
    seen = False
    for line in text.splitlines():
        if line.startswith("```"):
            inside = not inside
            seen = True
            continue
        yield line, inside
    if not seen:
        raise ValueError("no fenced block")


def parse_windows(text):
    """`charge-profile-flow.md`'s listing rows, as (address, text).

    The decoder's own dialect, so the text is what SELF_TEST holds and the
    comparison is on the whole of it. Elisions are dropped; a line that is not a
    listing row -- prose, a blank, the bare `...` -- yields nothing, which is
    also how the two `$ ` shell prompts in a `console` fence are declined.
    """
    rows = []
    for line, inside in _fenced(text):
        if not inside:
            continue
        m = _WINDOW_ROW.match(line)
        if m and m.group(2) != _ELISION:
            rows.append((int(m.group(1), 16), m.group(2)))
    return rows


def _section_body(text):
    """`bank-call-audit.md`'s SECTION, heading to the next `## `."""
    lines = text.splitlines()
    head = SECTION + "."
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## " + head):
            start = i
            break
    if start is None:
        raise ValueError(f"no '## {head}' heading")
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            return "\n".join(lines[start:i])
    return "\n".join(lines[start:])


def parse_section(text):
    """`bank-call-audit.md` §8's r2 listing rows, as {address: [(bytes, text)]}.

    Only fenced lines, and not the `$ r2 ...` prompt lines: a prompt carries an
    offset of its own (`s 0xb136`) in the same shape as an address column, and
    parsing one would put a *seek* into a table of *listings*. Every value is a
    list rather than a single row because two listings of one address in the
    same section are a disagreement the reconciler has to see, not a duplicate
    to collapse to the first.
    """
    listings = {}
    for line, inside in _fenced(_section_body(text)):
        if not inside or line.startswith("$"):
            continue
        m = _SECTION_ROW.match(line)
        if m:
            listings.setdefault(int(m.group(1), 16), []).append(
                (bytes.fromhex(m.group(2)), m.group(3)))
    return listings


def reconcile_windows(rows, windows):
    """Each SELF_TEST window against the rows its own span covers. (n, problems)

    The span comes from the expected rows themselves -- first address to last,
    no second copy of them in this module -- so a window cannot be checked
    against a range that has drifted from the table it is checking. Every parsed
    row whose address falls in the span is compared, so a `.md` line edited,
    added or removed all fail the same way, and a span that covers no parsed row
    at all is its own failure rather than an empty match -- a parser that
    quietly stopped finding things would otherwise pass every window by finding
    nothing in it.

    Compared **by address, not by position**, and that is the shape the three
    edits need. Pairing the two lists up in order and reporting the pairs that
    differ is the obvious version and it reports a *deletion* as a cascade of
    text disagreements one address to the right, none of which is the address
    that actually changed; the same pairing reports an elision written over a
    real row as nothing at all, because every surviving row still pairs with a
    row that agrees. Keyed on the address, each edit is one line naming the
    address it is about, and a row listed twice in one span is its own line
    rather than a silent last-wins.
    """
    checked, problems = 0, []
    for _start, expected in windows:
        lo, hi = expected[0][0], expected[-1][0]
        got = [row for row in rows if lo <= row[0] <= hi]
        if not got:
            problems.append(
                f"SELF_TEST window 0x{lo:04X}..0x{hi:04X} covers {len(rows)} "
                f"parsed row(s) of {CHARGE_PROFILE_FLOW} and none of them is "
                f"in it")
            continue
        want, have = dict(expected), {}
        for addr, text in got:
            if addr in have:
                problems.append(
                    f"{CHARGE_PROFILE_FLOW} lists 0x{addr:04X} twice inside "
                    f"0x{lo:04X}..0x{hi:04X}")
            have[addr] = text
        for addr in sorted(set(want) - set(have)):
            problems.append(
                f"0x{addr:04X} is `{want[addr]}` in SELF_TEST and is not "
                f"listed in {CHARGE_PROFILE_FLOW} inside 0x{lo:04X}..0x{hi:04X}")
        for addr in sorted(set(have) - set(want)):
            problems.append(
                f"{CHARGE_PROFILE_FLOW} lists 0x{addr:04X} as `{have[addr]}` "
                f"inside 0x{lo:04X}..0x{hi:04X} and SELF_TEST does not")
        for addr in sorted(set(want) & set(have)):
            if want[addr] != have[addr]:
                problems.append(
                    f"0x{addr:04X} is `{have[addr]}` in {CHARGE_PROFILE_FLOW} "
                    f"and `{want[addr]}` in SELF_TEST")
        checked += len(expected)
    return checked, problems


def reconcile_sites(listings, sites):
    """Each REL_SITES row against what §8 lists at that address. (n, problems)

    Bytes and target, never the text -- see the module docstring on why the two
    listing dialects never have to be reconciled. An address §8 does not list is
    a failure and not a skip: the oracle has gone, or the listing moved, and a
    skipped row would leave a `REL_SITES` entry that nothing has ever checked
    reading exactly like one that was checked and agreed.
    """
    checked, problems = 0, []
    for _foff, rt, raw, want in sites:
        entries = listings.get(rt)
        if not entries:
            problems.append(
                f"REL_SITES 0x{rt:04X} is no longer listed in {BANK_CALL_AUDIT} "
                f"{SECTION}")
            continue
        for got_raw, text in entries:
            m = _SECTION_TARGET.search(text)
            got_target = int(m.group(1), 16) if m else None
            if got_raw != raw or got_target != want:
                problems.append(
                    f"0x{rt:04X} is `{got_raw.hex(' ')}` -> "
                    f"{'?' if got_target is None else f'0x{got_target:04X}'} "
                    f"in {BANK_CALL_AUDIT} {SECTION} and "
                    f"`{raw.hex(' ')}` -> 0x{want:04X} in REL_SITES")
        checked += 1
    return checked, problems


def untranscribed(rows, windows):
    """The parsed rows no SELF_TEST window covers, as (lo, hi, count).

    A report, not a finding: `charge-profile-flow.md` §2 transcribes a second
    seven-row block at `0xB330` that the table has never carried. Nothing here
    checks it, and printing it is what stops "the two windows" from reading as
    "the file". The count is of rows the oracle parsed, so a file that grew a
    third block would show here rather than pass unnoticed.
    """
    covered = {a for _s, expected in windows for a, _t in expected}
    loose = sorted(a for a, _t in rows if a not in covered)
    if not loose:
        return None
    return loose[0], loose[-1], len(loose)


def reconcile(annotations, windows, sites):
    """Read both files under `annotations` and reconcile them.

    Returns `(reconciled, problems, untranscribed)`: how many of the table's
    rows were compared, every disagreement found (empty when they agree), and
    the parsed rows the table does not carry. One call so the caller gets one
    number and one problem list, and so a file that cannot be read or parsed
    is a *problem* rather than a traceback -- a prepared gate that crashes on
    a renamed annotation file is a gate whose first run after the rename looks
    like a broken tool.

    The two halves are read independently, so a file that stopped parsing does
    not take the other one's verdict down with it. That is what lets a partial
    answer report a count rather than nothing: a run whose `charge-profile-flow.md`
    is unreadable has still checked the four branch sites against §8, and
    saying so is more use than reporting a total that means nothing.
    """
    problems = []
    try:
        with open(f"{annotations}/{CHARGE_PROFILE_FLOW}") as f:
            rows = parse_windows(f.read())
        n, found = reconcile_windows(rows, windows)
    except (OSError, ValueError) as exc:
        n, rows, found = 0, [], []
        problems.append(f"{CHARGE_PROFILE_FLOW} could not be read: {exc}")
    try:
        with open(f"{annotations}/{BANK_CALL_AUDIT}") as f:
            listings = parse_section(f.read())
        m, missing = reconcile_sites(listings, sites)
    except (OSError, ValueError) as exc:
        m, missing = 0, []
        problems.append(f"{BANK_CALL_AUDIT} could not be read: {exc}")
    return n + m, problems + found + missing, untranscribed(rows, windows)
