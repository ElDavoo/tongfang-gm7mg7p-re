#!/usr/bin/env python3
"""Turn the one committed probe console log into the capture the grader reads.

`evidence/ec-watch/2026-09-23-0751-isolation.txt` is the only real capture of
the isolation test this repository holds, and it is free-form console text: a
`=== write 0x0751=0xA0 (hold 20s) ===` line, per-row offsets from the start of
that block, a `restored` line and a `SUMMARY:` block. `grade_0751_isolation.py`
reads `ts,addr,old,new` plus `ts,MARK,,label`, so it cannot open the file and
the one run that matters was graded by eye -- which is the drift #120 set out to
remove. This writes the one in terms of the other.

**It is a reader for one committed artifact, not a step in the next run.** The
probe grew a `--csv` mode after that run and writes the capture schema itself
(`MarkCsv`, four columns, one `MARK` row per arm), so the next run needs none of
this: it produces the gradeable file directly and the grader opens it. What
needed it was the 2026-09-23 file, and the write-up is
`docs/findings/probe-log-capture-conversion.md`.

**Why it lives here and not in `windows/tools/`.** It reads a Windows tool's log
and writes the EC grader's format, and the directory is the one holding the
grader, its reader and the fixtures both are read over. It cannot import the
probe to borrow its formatters -- `ecrw` binds kernel32 at import time, so the
import is Windows-only -- which is the same reason `EARLY_EXIT_TAG` is spelled
twice in this tree. What it borrows instead is the *grader*, which is stdlib-only
and loaded here by path the way `windows/tools/ec_watch.py`'s `--label-vocab`
loads it: `parse_mark` decides whether a mark label is one the grader can
place, and `MARK_MERGE_SECONDS` is the number the spacing refusal is measured
against. Two names, one source, and a derived file that cannot drift from what
the grader accepts.

**What is faithful and what is assumed, in the file's own terms.** Faithful:
which block each row belongs to, the block order, and each row's offset inside
its own block -- `build_windows` files a change at exactly a mark's timestamp
into that mark's window. Assumed, and named on `--anchor` and `--block-gap`:
the absolute anchor and the inter-block gap. The source carries **one**
absolute stamp for the whole run and per-block offsets relative to each block's
start, and the inter-block spacing is in no line of it. Both land in the derived
file's own `#` header, next to the source's real run timestamp, so a reader who
opens the capture sees what was chosen rather than having to ask.

**What the header also has to carry, because the grader cannot.** The source's
closing note records that its `0x075B`/`0x075C` PWM rows are "changes omitted
above", and the file holds no fan-table row and no temperature row at all. The
grader prints a line of zeros for every §4.1-§4.3 address in every window and
closes by calling the run consistent with the static prediction. Both are true
of the file and silent about the run, so the four caveats below ride in the
header instead: *transcribed, not captured*; *timestamps reconstructed*; *rows
the excerpt omits are absent from the record, not observed to hold still*; and
*no control arm*. The last one is checkable from the file and from nothing else
-- there is no `no-op wrote` mark in it, so §4.4's control-vs-write comparison
is not available over this capture, and the header says so rather than the tool
inventing a control arm to make the comparison runnable.

**The one check the format honestly supports, run as a refusal.** The source's
`SUMMARY:` lines are the transcriber's own claim about what moved in that block,
and they are checkable against the block's own `+ T.Ts` rows: same address set,
same first old value, same last new value. So this checks them and refuses on a
disagreement, naming the block and the address, and writes no output file. That
is the "graded by eye" step replaced by a check -- it does not say the source is
*true*, only that its summary and its rows are the same claim.

**It refuses rather than guesses, and every refusal is named**: no run timestamp
in the header; a block with no `restored` line; a line it does not recognise; a
`+ T.Ts` that is not a number; a change offset that goes backwards inside a
block; a block with no `SUMMARY:` section to check the rows against; a mark
label the grader's `parse_mark` cannot place; and an anchor/gap pair that leaves
two marks no further apart than `MARK_MERGE_SECONDS`, where `coalesce_marks`
would fold a restore into the next write and the block walk would report a day
that never happened. On any of them nothing is written, to a path or to stdout.

**One normalisation, and it is deliberate.** The source's `restored 0x0751 ->
0x10` is written as `restored 0x0751=0x10`, because `MARK_VALUE` needs the `=`
and a label without one is a mark the grader cannot place. The third block is
*not* relabelled: the source writes `=== write 0x0751=0x10 ===` for what is
functionally a no-op, and calling that `no-op wrote` would be inventing §3's
control-arm form, which `parse_mark` reads as a different role on purpose.

Nothing here opens an EC or reads a register. It is a file-to-file conversion,
and the file it reads is a 2026-09-23 artifact.

Usage:
    python3 ec/tools/probe_log_to_capture.py log.txt --anchor TS [--out CSV]
    python3 ec/tools/probe_log_to_capture.py log.txt --anchor TS --block-gap 30
    python3 ec/tools/probe_log_to_capture.py --self-test

`--anchor` is required rather than defaulted, because it is an assumption and a
default would let a reader believe a reconstructed timestamp was an observed one.
`--out` writes a file and stdout is the default sink.
"""
import argparse
import csv
import datetime
import importlib.util
import io
import os
import re
import subprocess
import sys

# The names borrowed from the grader, and the module they come from. The
# grader is a sibling in this directory and is stdlib-only, so importing it by
# path is what `windows/tools/ec_watch.py` already does with the same file; it
# is what keeps this tool's idea of a placeable mark and of the merge window
# from being a second spelling of either.
GRADER_FILE = "grade_0751_isolation.py"
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))

# The suite `--self-test` runs, and the directory it is discovered in, spelled
# the way `grade_0751_isolation.py` spells its own: absolute, so the mode works
# from any cwd, and by file name rather than by `test_*.py`, because `ec/tools/`
# holds other suites and the gate's cost should be this one.
SUITE_FILE = "test_probe_log_to_capture.py"

# The run's block spacing, as a default and not as a fact. The source has none,
# so this is a named choice on the command line and in the derived header; the
# one property it has to have is that two marks end up further apart than
# `MARK_MERGE_SECONDS`, which `derive` checks and refuses rather than assuming.
DEFAULT_BLOCK_GAP = 30.0

# The derived file's four caveats, as one string each. They are the whole of
# what the grader cannot say for itself, and they are lines rather than a
# paragraph because a reader has to be able to find them: `read_capture` drops
# every `#` row, so a caveat has to be found by a reader who opened the file to
# look at the marks.
CAVEATS = (
    ("transcribed, not captured",
     "the source is a transcription of a console session, so a row here is a "
     "row somebody typed and not a byte the EC was observed to hold"),
    ("timestamps reconstructed",
     "the absolute anchor and the inter-block gap are stated in the header "
     "below and are choices; the source carries one run timestamp and "
     "per-block offsets, and no inter-block spacing at all"),
    ("absent from the record, not observed to hold still",
     "the source's own closing note records its 0x075B/0x075C PWM rows as "
     "changes omitted above, and it holds no fan-table row and no temperature "
     "row, so every zero the grader prints over one of those addresses is a "
     "zero over a file with no row rather than a byte seen to stay"),
    ("no control arm",
     "there is no 'no-op wrote' mark anywhere in the source, so §4.4's "
     "control-vs-write comparison is not available over this capture and the "
     "grader's report is a read of the write arms alone"),
)

# The source's own line shapes, each one the thing it is and nothing else. A
# line none of them matches is refused with its number and its text: the source
# is a hand-maintained transcript, and a shape this tool has never seen is a
# question about what it means rather than something to skip past.
BLOCK_OPEN = re.compile(r"^=== write (0x[0-9a-fA-F]{1,4})=(0x[0-9a-fA-F]{1,2})"
                        r" \(hold ([0-9.]+)s\) ===$")
ARM_LINE = re.compile(r"^(0x[0-9a-fA-F]{1,4}) currently (0x[0-9a-fA-F]{1,2}); "
                      r"writing (0x[0-9a-fA-F]{1,2}), holding ([0-9.]+)s$")
CHANGE_ROW = re.compile(r"^\s*\+ (\S+)\s*s\s+(0x[0-9a-fA-F]{1,4}): "
                        r"(0x[0-9a-fA-F]{1,2}) -> (0x[0-9a-fA-F]{1,2})$")
RESTORE_LINE = re.compile(r"^restored (0x[0-9a-fA-F]{1,4}) -> "
                          r"(0x[0-9a-fA-F]{1,2})$")
SUMMARY_HEAD = "SUMMARY: addresses that moved while only 0x0751 was written:"
SUMMARY_ROW = re.compile(r"^\s+(0x[0-9a-fA-F]{1,4}): (0x[0-9a-fA-F]{1,2}) -> "
                         r"\.\.\. \(last (0x[0-9a-fA-F]{1,2})\)$")

# The run timestamp, as a shape rather than as a parse: what the header has to
# carry is the source's own text, quoted verbatim, so the test is that it looks
# like an instant this repository has used elsewhere. It is not the anchor --
# `--anchor` is -- and the two are kept apart everywhere below.
RUN_STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?"
                       r"(?:Z|[+-]\d\d:\d\d))")


class Refusal(Exception):
    """A log this tool will not convert, with the sentence it is refused by.

    Carried as an exception rather than returned as a value because every
    refusal has to abort the conversion before anything is written: a
    half-converted capture on disk is a file the grader would open and report
    on, and the report would be as confident as any other. `main` prints the
    message on stderr and returns 1, the way `grade_0751_isolation.py`'s own
    refusals are printed, so a caller scripting both sees one shape.
    """


class Block:
    """One `=== write ... ===` section of the source, as parsed.

    Held across the section's lines rather than assembled in one pass, because
    what makes a log convertible is that its parts agree: the restore has to be
    there at all, and the `SUMMARY:` block has to say the same thing as the
    change rows. Either check needs the whole block, and both are refusals
    rather than corrections.
    """

    def __init__(self, number, addr, value, hold, line):
        self.number = number
        self.addr = addr
        self.value = value
        self.hold = hold
        self.line = line
        self.changes = []        # (offset, addr, old, new), in source order
        self.restored = None     # (addr, value) once the restore line is read
        self.summary = []        # (addr, first old, last new)
        self.summarised = False

    def mark_label(self):
        """The `write` label this block opens with, in §3's spelling.

        Built from the address and value the source wrote rather than from
        `0x0751` hard-coded, so a source that named a different address is
        refused by `check_labels` instead of having its address quietly
        rewritten into one the grader would accept.
        """
        return f"wrote {self.addr}=0x{self.value:02X}"

    def restore_label(self):
        """The `restore` label this block closes with, with the `=` MARK_VALUE
        needs and the source's `->` does not have."""
        addr, value = self.restored
        return f"restored {addr}=0x{value:02X}"


def source_label(path):
    """How the derived header names the file it was made from.

    Repository-relative when the file is in the repository, and the path as
    given otherwise. The header line is compared byte for byte by
    `test_probe_log_to_capture.py`, so an absolute path would put whichever
    checkout produced it into the first line of a committed fixture and make
    that file differ on every machine -- which is the whole property the
    comparison exists to protect.
    """
    root = os.path.dirname(os.path.dirname(TOOL_DIR))
    try:
        inside = os.path.commonpath([os.path.abspath(path), root]) == root
    except ValueError:                     # different drives, on Windows
        inside = False
    return os.path.relpath(os.path.abspath(path), root) if inside else path


def load_grader():
    """The grader module, by path, from beside this file.

    Loaded rather than imported so the module name cannot collide with a
    `grade_0751_isolation` anything else in the interpreter has already bound,
    and read here rather than at import time so `--help` does not pay for
    reading a file whose absence the help text has nothing to say about.
    """
    path = os.path.join(TOOL_DIR, GRADER_FILE)
    spec = importlib.util.spec_from_file_location("grade_0751_isolation", path)
    if spec is None or spec.loader is None:
        raise Refusal(f"{path} has no loader: this tool reads the mark forms "
                      f"and the merge window out of the grader, so a copy it "
                      f"cannot import is a copy it cannot be honest about")
    grader = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(grader)
    except Exception as exc:                      # a staged copy, mostly
        raise Refusal(f"{path} is there but will not load: {exc}")
    return grader


def seconds(text, source, number, what):
    """`text` as a float, or a refusal naming where it was read.

    The two places this tool turns text into a duration are both looser than a
    number: a block's `(hold [0-9.]+s)` takes `1.2.3`, and a change row's offset
    is matched as any non-space run, so `+ abc s` is a line this recognises and
    has to refuse rather than one it never saw. A `ValueError` out of either
    would be a traceback over a log an operator is holding, so the shape says
    what the line looks like and this says whether the number in it is one.
    """
    try:
        return float(text)
    except ValueError:
        raise Refusal(f"{source}:{number}: {text!r} is not a number of seconds, "
                      f"and {what} is one: '(hold 20s)' in the block's opening "
                      f"line, '+ 0.0s' in a change row")


def parse(lines, source):
    """(run timestamp, blocks, notes) from the source's lines.

    A walk with a block held open until something closes it, and every line
    matched against the shapes above. The parts that can only be checked
    against each other -- the restore, the offsets, the summary -- are the
    block's own and are checked once the whole block is in, by `close_block`
    for the restore and `check_summary` for the summary.

    A `#` line closes an open block the way a blank line does not and the next
    `===` line does. The committed file annotates only between its blocks, so a
    note arriving mid-block is a source this does not model; it is refused by
    name when the block it interrupted has no restore, because that is the
    problem the operator has to fix, rather than by a line this recognised
    somewhere else.
    """
    stamp, notes, blocks, block, summary = None, [], [], None, False
    for number, text in enumerate(lines, 1):
        if not text.strip():
            continue
        if text.startswith("#"):
            if block is not None:
                close_block(block, source)
                block, summary = None, False
            body = text.lstrip("#").strip()
            match = RUN_STAMP.match(body)
            if match and stamp is None:
                stamp = match.group(1)
            notes.append(body)
            continue

        match = BLOCK_OPEN.match(text)
        if match:
            if block is not None:
                close_block(block, source)
            addr = int(match.group(1), 16)
            value = int(match.group(2), 16)
            block = Block(len(blocks) + 1, f"0x{addr:04X}", value,
                          seconds(match.group(3), source, number,
                                  "this block's hold"), number)
            blocks.append(block)
            summary = False
            continue

        if block is None:
            raise Refusal(f"{source}:{number}: {text!r} is not a line this "
                          f"reads. A block opens with '=== write ... ===', the "
                          f"file's own notes are '#' lines, and a blank line "
                          f"separates the two")

        if text == SUMMARY_HEAD:
            summary = True
            block.summarised = True
            continue
        match = SUMMARY_ROW.match(text) if summary else None
        if match:
            # Formatted like a change row's address rather than left as the int
            # the regex gave, so `check_summary` compares two spellings of the
            # same address rather than a `str` with an `int`.
            addr, old, last = (int(g, 16) for g in match.groups())
            block.summary.append((f"0x{addr:04X}", old, last))
            continue
        match = RESTORE_LINE.match(text)
        if match:
            if summary:
                raise Refusal(f"{source}:{number}: block {block.number}'s "
                              f"restore comes after its SUMMARY:, so this is "
                              f"not the block's shape")
            block.restored = (f"0x{int(match.group(1), 16):04X}",
                              int(match.group(2), 16))
            continue
        match = CHANGE_ROW.match(text)
        if match:
            offset = seconds(match.group(1), source, number,
                             "this line's offset into the block")
            addr, old, new = (int(g, 16) for g in match.groups()[1:])
            if block.changes and offset < block.changes[-1][0]:
                raise Refusal(
                    f"{source}:{number}: + {offset:g}s comes before the + "
                    f"{block.changes[-1][0]:g}s row above it, so this block's "
                    f"rows are not in the order the offsets say they are in")
            if summary:
                raise Refusal(f"{source}:{number}: a change row comes after "
                              f"block {block.number}'s SUMMARY:, so this is "
                              f"not the block's shape")
            block.changes.append((offset, f"0x{addr:04X}", old, new))
            continue
        match = ARM_LINE.match(text)
        if match and not block.changes and block.restored is None:
            # Recognised, not cross-checked against the `===` line above it.
            # It has to be a line this reads -- an unrecognised line is a
            # refusal, and the arm line is in every block of the committed
            # file -- and what it agrees with is the one thing the block's own
            # change rows and SUMMARY already have to agree about. It is here
            # because it is a shape, not because it is evidence.
            continue

        raise Refusal(f"{source}:{number}: {text!r} is not a line this reads, "
                      f"inside block {block.number}")

    if block is not None:
        close_block(block, source)
    if stamp is None:
        raise Refusal(f"{source}: no run timestamp in the header. One '#' line "
                      f"has to open with an instant (2026-09-23T16:31:01Z, the "
                      f"shape the committed file's does), because the derived "
                      f"header quotes it beside the reconstructed timestamps: "
                      f"a reader has to be able to see which are which")
    if not blocks:
        raise Refusal(f"{source}: no '=== write ... ===' block in it, so there "
                      f"is nothing to convert")
    return stamp, blocks, notes


def close_block(block, source):
    """Whether the block read whole, refusing by name if it did not.

    The restore is what the grader's block walk closes a block on, so a
    section without one is a section the derived capture would leave open and
    the grader would report `void` over -- correctly, and about a file this
    tool made rather than about the run. Better said here, where the operator
    is holding the log, than found there.
    """
    if block.restored is None:
        raise Refusal(f"{source}: block {block.number} (line "
                      f"{block.line}) has no "
                      f"'restored ...' line, so there is no mark to close it on")
    if not block.summarised:
        raise Refusal(
            f"{source}: block {block.number} (line {block.line}) has "
            f"no {SUMMARY_HEAD!r} section, so the transcriber's own claim about "
            f"what moved in it cannot be checked against its change rows, and "
            f"this tool will not convert a block it cannot check")


def check_summary(block, source):
    """The block's `SUMMARY:` block against its own change rows.

    Three things per address -- that the two name the same set, that the first
    old value is the first row's, and that the last new value is the last
    row's -- which is what makes the summary a claim about the block rather
    than a caption beside it. A block whose summary is empty and whose rows are
    empty agrees with itself, which is the third block of the committed file:
    its no-op recorded nothing, and its summary says so.

    This is the check the format supports and no more. Agreement says the two
    halves of one transcription are the same claim; it does not say either is
    true of the machine, and nothing downstream of here says that either.
    """
    rows = {}
    for _, addr, old, new in block.changes:
        rows.setdefault(addr, []).append((old, new))
    said = {addr: (old, last) for addr, old, last in block.summary}

    for addr in sorted(set(rows) | set(said)):
        if addr not in rows:
            raise Refusal(f"{source}: block {block.number}'s SUMMARY: names "
                          f"{addr} as having moved and the block records no "
                          f"change row for it")
        if addr not in said:
            raise Refusal(f"{source}: block {block.number} records {addr} "
                          f"moving and its SUMMARY: does not name it")
        first_old, last_new = said[addr]
        if first_old != rows[addr][0][0]:
            raise Refusal(f"{source}: block {block.number}'s SUMMARY: says "
                          f"{addr} started at 0x{first_old:02X} and its first "
                          f"change row says 0x{rows[addr][0][0]:02X}")
        if last_new != rows[addr][-1][1]:
            raise Refusal(f"{source}: block {block.number}'s SUMMARY: says "
                          f"{addr} ended at 0x{last_new:02X} and its last "
                          f"change row says 0x{rows[addr][-1][1]:02X}")


def check_labels(blocks, grader, source):
    """Every mark label the conversion produces, through the grader's own parse.

    A label `parse_mark` cannot place is a mark the grader's block walk cannot
    attribute to a block, which `UNREAD_MARK_NOTE` is a whole refusal about --
    so the refusal belongs here, where the label was written, rather than at
    the grading, over a file this tool produced.
    """
    for block in blocks:
        for label in (block.mark_label(), block.restore_label()):
            if grader.parse_mark(label)[0] is None:
                raise Refusal(
                    f"{source}: block {block.number} would open or close with "
                    f"{label!r}, which grade_0751_isolation.py's parse_mark "
                    f"cannot place. Its forms are "
                    f"{', '.join(grader.REQUIRED_LABEL_FORMS)}; a restore also "
                    f"needs the '=' this tool adds to the source's '->'")


def mark_row(label):
    """One mark row's three fields, after the timestamp.

    The shape is `ts,MARK,,label`, and it is written here rather than at each
    of the two places `derive` emits one so the row is stated once in this file
    the way `MarkCsv` states it in its own. Four columns, not five: the fifth
    is `ec_watch.py`'s `provenance` (#739) and a mark row written without it
    reads as *not recorded*, which is what `existing_mark_provenance`'s
    docstring says a four-column row means -- not as a process that held no
    vocabulary.
    """
    return ("MARK", "", label)


def derive(blocks, anchor, gap, grader, source):
    """(rows, marks) for the derived capture, and the checks the rows rest on.

    Row order is mark first, then the block's change rows, then the restore:
    the mark is what opens the window and the rows belong to it, and `+ 0.0s`
    is the same instant as the mark, so the order in the file is this one's
    choice and not something the source said.

    The restore is stamped at the block's own `hold` rather than at the gap,
    because the hold is in the source and the gap is not: the section wrote
    `(hold 20s)` and held it, and the restore is what ended it.

    The spacing check is here rather than in `main` because it is a property of
    the marks these rows produce, not of the two flags: a `--block-gap` under
    the source's own hold puts one block's restore at or after the next block's
    write, and two marks that close are one window to `coalesce_marks` and a
    day that never happened to the block walk.
    """
    rows, marks = [], []
    for n, block in enumerate(blocks):
        start = anchor + datetime.timedelta(seconds=n * gap)
        rows.append((start, mark_row(block.mark_label())))
        marks.append(start)
        for offset, addr, old, new in block.changes:
            rows.append((start + datetime.timedelta(seconds=offset),
                         (addr, f"0x{old:02X}", f"0x{new:02X}")))
        end = start + datetime.timedelta(seconds=block.hold)
        rows.append((end, mark_row(block.restore_label())))
        marks.append(end)

    close = grader.MARK_MERGE_SECONDS
    for earlier, later in zip(marks, marks[1:]):
        apart = (later - earlier).total_seconds()
        if apart <= close:
            raise Refusal(
                f"{source}: --anchor {anchor.isoformat()} with --block-gap "
                f"{gap:g}s "
                f"leaves two marks {apart:g}s apart, which is not more than "
                f"grade_0751_isolation.py's MARK_MERGE_SECONDS ({close:g}s): "
                f"coalesce_marks would fold them into one window and the "
                f"block walk would report a day that never happened. Widen "
                f"--block-gap")
    return rows


def header(source, stamp, anchor, gap, notes):
    """The derived file's `#` block, whole.

    Four caveats, then the two choices and the source's own stamp beside them,
    then the source's notes transcribed -- because a note the transcriber left
    is evidence about what they left out, and dropping it would leave the
    zeros it explains unexplained.

    Every line opens with `#`, which is what `skippable_row` drops. The one
    row that reader does *not* drop is `EARLY_EXIT_TAG`, and a source note
    beginning with that phrase is indented three spaces under a `#` so it
    cannot become one: the derived line is `#   the run ended early: ...`,
    which is not `# the run ended early: ...`, and a header the grader read as
    a crash would charge every block's windows and withhold all of them over a
    file that records no crash at all. The indent is what makes that true, so
    it is not a decoration -- `test_probe_log_to_capture.py` pins the property
    on the committed file rather than trusting the spacing here to hold.
    """
    out = [f"# derived from {source_label(source)} by "
           f"{os.path.basename(__file__)}; the source is a transcription and "
           f"this is not a capture of its own."]
    for title, body in CAVEATS:
        out.append(f"# caveat: {title}. {body[0].upper()}{body[1:]}.")
    out += [f"# run timestamp in the source's own header: {stamp}",
            f"# anchor this file was given: {anchor.isoformat()} "
            f"(--anchor, a choice, not an observation)",
            f"# inter-block gap this file was given: {gap:g}s "
            f"(--block-gap, a choice; the source records no inter-block "
            f"spacing at all)",
            f"# every timestamp below is one of those two choices applied to an "
            f"offset the source did record.",
            "# the source's own notes, transcribed:"]
    out += [f"#   {note}" for note in notes]
    return out


def convert(source, anchor, gap):
    """The derived capture as text, from the source at `source`.

    Everything is built in memory and returned, so a refusal anywhere above
    leaves no file: the caller writes once, at the end, and a log this tool
    cannot convert whole does not become half a capture.
    """
    grader = load_grader()
    try:
        with open(source, "r", encoding="utf-8") as handle:
            lines = handle.read().split("\n")
    except UnicodeDecodeError as exc:
        raise Refusal(f"{source}: is not utf-8, and this format is declared in "
                      f"utf-8: {exc}")
    except OSError as exc:
        # A path that is not there is the one input error an operator makes
        # most, and a traceback over it is the shape this file's refusals are
        # written against. Deliberately narrower than `except Exception`: this
        # is about the open, and a bug further down is still a bug worth seeing.
        raise Refusal(f"{source}: cannot be read: {exc}")

    stamp, blocks, notes = parse(lines, source)
    for block in blocks:
        check_summary(block, source)
    check_labels(blocks, grader, source)

    rows = derive(blocks, anchor, gap, grader, source)
    buf = io.StringIO()
    buf.write("\n".join(header(source, stamp, anchor, gap, notes)))
    buf.write("\n")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["ts", "addr", "old", "new"])
    for ts, fields in rows:
        writer.writerow([ts.isoformat(), *fields])
    return buf.getvalue()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if "--self-test" in argv:
        return self_test()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log", help="the probe console log, e.g. "
                                "evidence/ec-watch/2026-09-23-0751-isolation.txt")
    ap.add_argument("--anchor", required=True, metavar="TS",
                    help="the instant this file's first mark carries. Required "
                         "and not defaulted, because it is the one number in "
                         "the derived capture that no line of the source "
                         "supports; it is written into the derived header, "
                         "beside the source's own run timestamp")
    ap.add_argument("--block-gap", type=float, default=DEFAULT_BLOCK_GAP,
                    metavar="SECONDS",
                    help=f"the gap between one block's restore and the next "
                         f"block's write (default {DEFAULT_BLOCK_GAP:g}). A "
                         f"choice too: the source records per-block offsets "
                         f"and no spacing between them. Marks closer together "
                         f"than the grader's MARK_MERGE_SECONDS are refused "
                         f"rather than folded")
    ap.add_argument("--out", metavar="CSV",
                    help="where to write the capture; stdout when not given")
    args = ap.parse_args(argv)

    try:
        anchor = datetime.datetime.fromisoformat(
            args.anchor.replace("Z", "+00:00"))
    except ValueError:
        print(f"\n--anchor {args.anchor!r} is not an instant this can read "
              f"(2026-01-01T12:00:00, 2026-01-01T12:00:00Z). It is a choice "
              f"about where the reconstructed marks start, and a value it "
              f"cannot read is not one.", file=sys.stderr)
        return 1
    if args.block_gap < 0:
        print(f"\n--block-gap {args.block_gap:g}s is negative: a block cannot "
              f"start before the one before it.", file=sys.stderr)
        return 1

    try:
        text = convert(args.log, anchor, args.block_gap)
    except Refusal as refusal:
        print(f"\n{refusal}", file=sys.stderr)
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


def self_test(run=None):
    """Run the committed suite in a subprocess and return its exit code.

    `run` is `subprocess.run` unless a caller passes its own, the seam
    `grade_0751_isolation.py` exposes for its own `--self-test` and the one
    this mode's case in the suite drives it through: a `--self-test` case that
    ran the mode for real would have the mode run the suite that contains it,
    which runs the case again, and so on.
    """
    cmd = [sys.executable, "-m", "unittest", "discover",
           "-s", TOOL_DIR, "-p", SUITE_FILE]
    proc = (subprocess.run if run is None else run)(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = proc.stdout or ""
    if out and not out.endswith("\n"):
        out += "\n"
    if proc.returncode:
        print(out, end="")
        print(f"{SUITE_FILE}: FAILED")
        return 1
    if "Ran 0 test" in out:
        # A discovery that matched nothing exits 0 and prints OK, which from
        # the outside is indistinguishable from a suite that passed.
        print(out, end="")
        print(f"{SUITE_FILE}: FAILED -- no test ran, which is not a pass. It "
              f"is discovered at {os.path.relpath(TOOL_DIR)}; if that is not "
              f"where the suite is, this mode is looking in the wrong place.")
        return 1
    print(f"{SUITE_FILE}: passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())