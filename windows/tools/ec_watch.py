#!/usr/bin/env python3
r"""Watch EC RAM for changes while something else -- the vendor's Control Center,
usually -- is driving it, and report which addresses moved.

`ecrw.py` can sweep 2 KiB of EC space in about 150 ms, which is fast enough to
catch a settings write as it lands. That turns "which register does the vendor
service actually use for X" from a static-analysis question into an observation:
start this, change X in the vendor UI, stop, and read off the addresses that
changed at that moment.

The output separates two kinds of address, because they need reading differently:

  * *busy* -- changed on many sweeps. Sensors: temperature, fan tacho, battery
    current. A setting is essentially never here.
  * *quiet* -- changed only once or twice in the whole run. This is what a
    settings write looks like, and it is the column to read first.

Neither label is a claim about meaning. An address appearing here means only
that its byte changed while the run was going on; whether the vendor service
wrote it, the EC wrote it itself, or it moved for an unrelated reason is exactly
what a single run cannot distinguish -- run it again with and without the action
before believing any of it.

With both --mark and --csv, each mark is written into the CSV as its own row
(`ts,MARK,,label`) as well as printed, so the capture alone says when the
operator acted -- see ec/tools/grade_0751_isolation.py, which grades a capture
by what moved between one mark and the next. A blank line is not a mark: the
prompt records nothing, says so, and asks again, so no capture holds a mark
the operator did not describe. `ec_watch-marks.md` is why.

`--label-vocab 0751` is that refusal one step earlier, and opt-in: the prompt
refuses a label the 0751 grader's own `parse_mark` cannot read, quotes §3's
forms back, and asks again -- where a mistyped `=`, or the `0x` dropped
from the address, is corrected while the run is still going rather than at the
grading as `unplaceable_marks` and a withheld run. It refuses only what the
grader would refuse: a label that parses but names the wrong value is still
recorded, and so is a dropped hex digit, because a per-line prompt cannot know
which values the run means to write or what its actions should be. It is off
by default because `gpu_block_watch.py:59,166` imports this `Marker` and
stamps free-form labels through it, which a blanket check would refuse, while
`system_id_probe.py:232` has its own, still `strip() or` at `:252` (#483, #484).

The rule that check applies is read out of the grader rather than carried
here, so the grader is a startup dependency of that flag and of nothing else
in this tool: a checkout finds it at `ec/tools/grade_0751_isolation.py`, a
directory of tools staged onto a Windows box finds a copy of it beside this
file, and `--grader <path>` names a third place. A grader in none of them, or
one that is there and will not load, refuses before the CSV and long before the
EC, and the refusal names every place it looked.

That check is a per-process fact, and the `--csv` it appends to is a per-file
one. `CsvSink` opens the path in append mode without reading it, and §3 fixes
the three CSVs as one set for the whole run -- blocks 2 and 3 are meant to land
on the marks block 1 left there. So a file can carry marks this
process did not type and could not have checked: a pre-`--label-vocab` run, a
console started without the flag, a watcher restarted mid-block, or a
`manual_fan_ctrl_probe.py` capture, which writes the same `ts,MARK,,label` row.
A run that finds any says so, naming them, above the file and a long way above
the EC -- a warning rather than a refusal, because §3's own second block is
that collision and because no process can check a mark another one already
wrote. And it names two lists rather than one (#718): the mark rows the
grader's own reader takes, and the rows it will refuse the file over -- a
short row, a timestamp it cannot read, a change row whose hex does not parse,
a byte this interpreter's encoding cannot decode -- each with the reason from
`read_capture` rather than from a rule copied here, plus what the grader's
placement pass reports it cannot place. The reader is the grader's
`existing_mark_findings`, for the same reason the check is the grader's
`parse_mark` and `load_label_vocab` exists at all, and the notice says what
the mark counter counts while both sequences are in view: the marks this run
records, numbered from 1 whatever the file already holds. #548,
`ec_watch-marks.md`.

`--block` sweeps the same addresses four bytes per IOCTL through the driver's
`MMRD` instead of one byte per `ECRR`, so the default 2 KiB sweep is 512 calls
rather than 2048. It is off by default and nothing in this repository has run
it:
`ecrw.py`'s `readmany` is a reading of how the handler marshals, and whether
the BIOS answers with what four single reads would have is the comparison
written out in `manual_fan_ctrl_probe.py`'s docstring, for a human with the
machine. A block read that covers the fan-tach page is a *wider* access to the
page that stalled the fans on a sibling board (#94), not a narrower one, so
the tool warns rather than refuses: `0x0000-0x07FF`, this tool's default
range, contains it.

Usage:
  ec_watch.py                                  # 0x0000-0x07FF until Ctrl-C
  ec_watch.py --start 0x0700 --len 0x100
  ec_watch.py --seconds 60 --csv out.csv
  ec_watch.py --mark                           # type a label + Enter to stamp a mark
  ec_watch.py --mark --label-vocab 0751        # and refuse a label the 0751 grader cannot read
  ec_watch.py --mark --label-vocab 0751 --grader <path-to-grade_0751_isolation.py>
  ec_watch.py --mark --label-vocab 0751 --csv run.csv   # and name the marks run.csv already holds
  ec_watch.py --start 0x0700 --len 0x100 --block

`--label-vocab 0751` reads the grader from `ec/tools/grade_0751_isolation.py`
in a checkout, or from a copy of it in this file's own directory where the
tools have been staged onto a Windows box; `--grader` is a third place, and
needs `--label-vocab`.
"""
import argparse
import csv
import datetime
import importlib.util
from pathlib import Path
import sys
import threading
import time

from ecrw import Ec, EcError

# The fan-tach bytes, named as a range so the --block warning, this tool's
# self-description and its suite can all name the same sixteen addresses
# without each spelling the endpoints out again. Reading them through ECRR
# stalled the fans on a sibling board (#94, docs/related-projects.md); nothing
# here stops that, and --block does not help: a dword read that covers the page
# is a four-byte access to the page rather than a one-byte one.
FAN_TACH = range(0x0460, 0x0470)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="milliseconds")


class CsvSink:
    """The CSV, plus the lock that makes it safe to write from two threads.

    The sweep loop runs on the main thread and marks arrive on the stdin
    thread, so without this a mark can land in the middle of a change row.
    """

    def __init__(self, path):
        self._fh = open(path, "a", newline="")
        self._writer = csv.writer(self._fh)
        self._lock = threading.Lock()
        if self._fh.tell() == 0:
            self.row(["ts", "addr", "old", "new"])

    def row(self, values):
        with self._lock:
            # A mark typed as the run ends arrives after close(); dropping it
            # beats a traceback out of the stdin thread at the last moment.
            if self._fh.closed:
                return
            self._writer.writerow(values)
            self._fh.flush()

    def close(self):
        with self._lock:
            self._fh.close()


def grader_candidates(grader_path=None):
    """Every place the grader is looked for, in the order it is tried.

    `--grader` is the whole list when given, rather than the first entry of it:
    an explicit path that quietly fell through to a different file would be the
    silent fallback `load_label_vocab` refuses to make, and an operator who
    named a file has already been told where it is.

    The committed copy comes first among the built-ins so a checkout grades its
    prompts against the grader its own tests pin, and a copy staged beside this
    file can only matter where there is no checkout to have one -- which is what
    §3's three watchers meet when a directory of tools has been copied onto a
    Windows box rather than run out of the tree.
    """
    if grader_path:
        return [Path(grader_path)]
    here = Path(__file__).resolve()
    # The checkout copy is `here.parents[2]`, which a tools directory staged
    # onto a Windows box can be too shallow to have: `C:\tools\ec_watch.py` is
    # two levels down and `parents[2]` is off the drive, so indexing it there
    # is an IndexError rather than a candidate. A path that cannot be named is
    # not a place to look -- there is no checkout above a drive root -- so it
    # is offered only when the path is deep enough to have one. The
    # beside-the-tool copy below is what reaches that depth, and offering it
    # unconditionally is the whole of candidate 3.
    candidates = []
    if len(here.parents) > 2:
        candidates.append(here.parents[2] / "ec/tools"
                          / "grade_0751_isolation.py")
    candidates.append(here.with_name("grade_0751_isolation.py"))
    return candidates


def load_label_vocab(ap, name, grader_path=None):
    """(check, forms, existing_marks, existing_findings) for the vocabulary
    `name`, read from its grader.

    `--label-vocab 0751` names §3's forms, and
    `grade_0751_isolation.py` is where they are written down, so the prompt
    loads that module by path rather than carrying a second copy of any of the
    four: `check` is `parse_mark(label)[0] is not None`, the test
    `unplaceable_marks` applies to decide a mark is unreadable, `forms` is
    that module's own `REQUIRED_LABEL_FORMS` for the refusal to quote,
    `existing_marks` is its reader for the mark rows a `--csv` already holds,
    and `existing_findings` is the one that says which of those rows the
    grader's own reader takes and which it will refuse the file over.
    A copy could drift from the grader, and a prompt that has drifted promises
    something the grading does not do. The count is the grader's for the same
    reason: §3 has three action forms and three stage boundaries as of issue
    #472, and a word in this docstring saying which would be a fourth place to
    keep in step.

    The two readers ride on the one load rather than making a second, because
    it is the same rule seen from the other side (#548): a mark row is the
    grader's shape, and the marks already sitting in a file are the ones the
    check the other two return cannot reach. Both are preflights, and neither
    raises on the *content* `read_capture` would -- neither a row it rejects
    nor a byte the encoding cannot decode -- see their docstrings for why that
    is the point rather than an accident.

    The import is the one `manual_fan_ctrl_probe.py`'s self-test makes, and it
    is by path and only under this flag, for the reason that call gives: this
    tool is imported at module scope by `gpu_block_watch.py:59,166`, and a
    grader requirement it never asked for is not one it should inherit. What
    that call rules out is a dependency on the repository *layout*, and this
    lookup was one hard-coded path, which made the layout the whole of it. The
    layout is one of the places `grader_candidates` looks now; the dependency
    that is real is on the file existing somewhere, which is one -- §3's three
    commands carry the flag and will not start without it -- and is what this
    function's refusal is for rather than something to look past. The grader
    imports stdlib only and its module-level work is constants and a
    `__main__` guard, so loading it there opens no capture and touches no
    hardware.

    A grader that will not load is a refusal rather than a fallback, and so is
    one that is present and broken: the search advances past a candidate that
    is not there and stops at one that raises, naming that path. A staged copy
    silently standing in for a committed grader that has been broken since the
    checkout was made is a capture graded against a rule the tree does not
    hold. A run with the check silently off is #502's failure one step earlier
    -- a capture taken under a promise the tool did not keep -- and the
    operator would not find out until the grading. So a copy that loads but
    lacks one of the four names is refused the same way, and by the same
    message: the files a tools directory holds go stale when only the tool
    beside them is updated, and naming the path is what tells an operator to
    copy the current grader over rather than to work out which of the two is
    the old one.
    """
    tried = []
    for path in grader_candidates(grader_path):
        if not path.is_file():
            tried.append(path)
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                "grade_0751_isolation", path)
            if spec is None or spec.loader is None:
                # No loader for this suffix (a .txt and friends): there, and
                # there is no module to run. The same one refusal.
                raise ImportError("importlib has no loader for this file")
            grader = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(grader)
            # Read the four names here rather than in the return below, so a
            # staged copy that predates one of them is refused by the message
            # that names the path. A bare AttributeError out of the return
            # would name the name and not the file, which is the one thing an
            # operator standing at the box cannot act on -- and a staged copy
            # beside `ec_watch.py` is exactly the file that goes stale when
            # only the tool is updated (#718).
            vocab = (lambda label: grader.parse_mark(label)[0] is not None,
                     grader.REQUIRED_LABEL_FORMS,
                     grader.existing_mark_labels,
                     grader.existing_mark_findings)
        except Exception as e:
            ap.error(f"--label-vocab {name} needs grade_0751_isolation.py at "
                     f"{path}, and it is there but will not load: {e}")
        return vocab
    ap.error(f"--label-vocab {name} needs grade_0751_isolation.py, the module "
             f"this prompt reads its vocabulary from, and none of these is it:\n"
             + "".join(f"  {p}\n" for p in tried)
             + "Put a copy of it beside ec_watch.py, or run from a checkout "
               "that has one; --grader names a third place.")


def warn_unchecked_marks(path, existing_findings):
    """Name the marks `path` already holds, before `CsvSink` appends to it,
    and the rows of it the grader's own reader will refuse.

    A warning rather than a refusal, and the runbook is why: §3 fixes the
    three CSVs as one set for the whole run, so blocks 2 and 3 are *meant* to
    append to the marks block 1 left there, and a tool that refused
    a non-empty `--csv` would refuse the procedure it documents. What no
    process can do is check a mark another one wrote, and the grader judges
    the whole file rather than the rows this run added, so a mark already in
    the file that it cannot place refuses the day however it got there. Saying
    so at the top of the run is the only point at which the operator can still
    act on it: a day later the same fact is a withheld run and no remedy.

    Three sections and the order is the reading order: what is there, what
    stops the grader reading it, and what it will not be able to place in it.
    #718 split the first of those, because one list of every mark row the
    preflight returns cannot tell an operator which of six good marks and one
    half-written row is the one the run will be refused over -- and the
    preflight is deliberately the lenient reader, so its own list never could.
    The reasons are the grader's own rather than a second rule spelled here,
    which is the whole of what makes the refusal section worth acting on; see
    `existing_mark_findings` for why that lives in the grader.

    The counts are per list and never one total, because they count different
    things: a file of two good marks and one short row holds two marks this
    run is appending after and one row that has to be fixed, and folding the
    second into the first would report a mark the grader will never read. The
    header count is the accepted count, so a file of only good marks reads
    exactly as it did in #548 and the first section is unchanged.

    The unplaceable section says the grader's verdict over the *group* the
    consoles' marks form, and not that one label is unreadable, because that
    is what `unplaceable_marks` returns: a `coalesce_marks` window whose
    joined label no part of it places, or nothing. A window led by a label
    that does place is not reported, and a notice that said its second console
    was unreadable would be false.

    A refused file reports no unplaceable marks and says so in one line. That
    is not a gap in the check -- a label verdict needs a file the grader can
    read, and one it cannot read is already refused whole -- but an operator
    who is not told will read the silence as "the labels are fine".

    The refused section's remedy depends on what was refused. A row can be
    edited, and telling the operator to fix or delete one is the whole value
    of naming it. The encoding cannot: that refusal is the file's and names no
    row, so the remedy there is re-saving the capture rather than an
    instruction to edit a line that is not at fault.

    The closing paragraph is unchanged from #548 and its wording is
    load-bearing, so it is printed as it was whatever the sections above did.
    On a file holding no mark at all and only a bad row, its "those marks" has
    an empty set in front of it; that is vacuous rather than false, and the
    alternative is a second closing to keep in step with the first.

    The notice is worded in terms of this run and not of the file's history,
    because the file's history is not something this process can read. Block 1
    carries `--label-vocab` too, so in the case this notice calls expected the
    marks it names *were* checked against the forms, as they were typed, by the
    process that typed them -- and a sentence about the file rather than the run
    would have to be false in exactly that case. What is true is that this
    process did not check them, and cannot, having not written them.
    """
    accepted, refused, unplaceable = existing_findings(path)
    if not (accepted or refused or unplaceable):
        return
    if accepted:
        print(f"  appending to {path}, which already holds {len(accepted)} "
              "mark(s) placed by a process that did not type them here:")
        for ts, label in accepted:
            print(f"    {ts}  {label!r}")
    if refused:
        print(f"  and {len(refused)} row(s) of it the grader's own reader "
              "refuses, which refuses the file whole: every mark in it, not "
              "only the ones this run adds.")
        for row, reason in refused:
            # A refusal of the file rather than of a row has no row to name,
            # and the encoding is the one that is like this.
            print(f"    {'the file itself' if row is None else repr(row)}  "
                  f"-- {reason}")
        if any(row is not None for row, _ in refused):
            print("  fix or delete the row(s) above before the run: that is "
                  "the one thing here worth stopping for. The run itself "
                  "does not care -- it appends either way.")
        else:
            # Nothing above to edit. The refusal is the file's encoding, so
            # naming a row to fix would name something that is not there.
            print("  no row to fix: the file has to be readable by the "
                  "interpreter that grades it, and this one is not. The "
                  "bytes are whatever the writing process's locale wrote, so "
                  "re-saving the capture in an encoding this Python reads is "
                  "the fix.")
        print("  the marks it could not place are not reported while the "
              "file is refused: it is refused whole, so that would add "
              "nothing.")
    if unplaceable:
        print("  and the grader's own placement pass reports "
              f"{len(unplaceable)} mark(s) in it as unplaceable, which "
              "refuses the day whole. That is its verdict over the group the "
              "consoles' marks form, not one label's:")
        for _, _, message in unplaceable:
            print(f"    {message}")
    print("  this run did not check those marks and cannot: it did not write "
          "them. §3's three CSVs are one file for the whole run, so blocks 2 "
          "and 3 are expected to land here; the grader judges the whole file, "
          "though, so a mark it cannot place refuses the day however it got "
          "in. The mark numbers in this run's prompts count this run's marks "
          "only: they start at 1 whatever the file already holds.")


class Marker:
    """Lets the operator stamp 'I clicked the thing now' into the log.

    `check` and `forms` are the label vocabulary `load_label_vocab` returns,
    and both default to None rather than to a rule: this class is imported by
    `gpu_block_watch.py`, which takes free-form labels a 0751 check would
    refuse, so a default that checked anything would break it.
    """

    def __init__(self, sink=None, check=None, forms=None):
        self.marks = []
        self._n = 0
        self._sink = sink
        self._check = check
        self._forms = forms or ()

    def start(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while True:
            try:
                label = sys.stdin.readline()
            except Exception:
                return
            if not label:
                return
            label = label.strip()
            if not label:
                # A blank press is not a mark, and this used to make it one:
                # `strip() or f"mark {self._n}"` wrote a `mark N` row the 0751
                # grader cannot read, and read at the console as a mark
                # somebody meant to place. It was also a mark nobody described,
                # which is the one kind the grader cannot recover -- see
                # ec_watch-marks.md. So: record nothing, say so, ask again.
                # `_n` counts marks recorded rather than lines read, which is
                # what lets the notice name the number the press did not take.
                print("--- blank line: nothing recorded, no mark "
                      f"{self._n + 1} taken; type a label + Enter ---",
                      flush=True)
                continue
            if self._check and not self._check(label):
                # A described mark whose description is wrong, which the grader
                # is right to refuse and which `unplaceable_marks` treats as
                # fatal for the whole run. Refused here for the reason the
                # blank press is: the place to stop it is before a day of
                # hardware time is spent on it, not at the grading. Same shape
                # as the notice above -- nothing recorded, no mark N taken --
                # and before `_n += 1`, so the number it names is the number
                # the next accepted mark carries.
                print("--- unplaceable label: nothing recorded, no mark "
                      f"{self._n + 1} taken; one of: "
                      + " / ".join(self._forms)
                      + "; type a label + Enter ---", flush=True)
                continue
            self._n += 1
            ts = now()
            self.marks.append((ts, label))
            if self._sink:
                self._sink.row([ts, "MARK", "", label])
            print(f"--- {ts}  MARK: {label} ---", flush=True)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="0x0000")
    ap.add_argument("--len", dest="length", default="0x0800")
    ap.add_argument("--seconds", type=float, default=0,
                    help="stop after this long (default: until Ctrl-C)")
    ap.add_argument("--interval", type=float, default=0.25,
                    help="seconds between sweeps (default 0.25)")
    ap.add_argument("--csv", help="also write every change to this CSV")
    ap.add_argument("--mark", action="store_true",
                    help="read stdin; each line stamps a labelled mark, into "
                         "the CSV too if --csv is given. A blank line, and "
                         "any label --label-vocab refuses, records nothing "
                         "and the prompt asks again")
    ap.add_argument("--label-vocab", choices=("0751",),
                    help="refuse a mark label the named vocabulary cannot "
                         "read, with the blank press's notice and counting "
                         "rule, rather than recording a mark the grader will "
                         "not be able to place; on a --csv that already holds "
                         "mark rows, name them and say they were not checked, "
                         "because the file is graded whole and this run's "
                         "labels are the only ones it checks, and name the "
                         "rows of that file the grader's own reader will "
                         "refuse it over, each with its reason. Needs --mark. "
                         "Off by default: the other tools that take marks "
                         "through this one use their own free-form labels")
    ap.add_argument("--grader", metavar="PATH",
                    help="read the --label-vocab grader from this file rather "
                         "than from ec/tools/ in a checkout or from beside "
                         "this one. It is the only place looked, so a path "
                         "that will not load refuses rather than falling back; "
                         "needs --label-vocab")
    ap.add_argument("--block", action="store_true",
                    help="sweep 4 bytes per IOCTL (MMRD) instead of 1 (ECRR); "
                         "a path that has never been run against the driver, "
                         "and not a safety improvement over the byte path")
    args = ap.parse_args(argv)

    # The startup refusals, all of them above the CSV and a long way above the
    # EC: a run that cannot keep the promise has to say so before it starts,
    # not halfway through the first block. So is the append notice, which is
    # the same promise seen from the file's side rather than the process's: it
    # names what the --csv already holds, and the file has to exist to be
    # read, so the fresh path of §3's block 1 stays quiet on both counts.
    check = forms = None
    if args.grader and not args.label_vocab:
        # The same shape as the one below, and for the same reason: it is a
        # modifier of --label-vocab, and a grader path beside a run that reads
        # no vocabulary is a flag that reads as a setting and changes nothing.
        ap.error("--grader needs --label-vocab: it names where that flag's "
                 "grader is, and there is no vocabulary without that flag")
    if args.label_vocab:
        if not args.mark:
            ap.error("--label-vocab needs --mark: the mark prompt is the only "
                     "place a label is typed")
        check, forms, existing_marks, existing_findings = load_label_vocab(
            ap, args.label_vocab, args.grader)
        if args.csv and Path(args.csv).is_file():
            warn_unchecked_marks(args.csv, existing_findings)

    start = int(args.start, 0)
    length = int(args.length, 0)
    addrs = list(range(start, start + length))

    sink = CsvSink(args.csv) if args.csv else None

    marker = Marker(sink, check, forms)
    if args.mark:
        marker.start()

    changes = {}           # addr -> number of times it changed
    first_last = {}        # addr -> (first value seen, last value seen)
    t0 = time.time()
    sweeps = 0

    try:
        with Ec() as ec:
            def sweep():
                # One shape for both paths, so what the diff below reads is
                # the same {addr: byte} either way: readmany keys the range it
                # was asked for, not the blocks it covered. The byte path
                # therefore reports a sweep's changes after the sweep's reads
                # rather than between them, which is the only thing that moved
                # on the path that was already the default.
                if args.block:
                    return ec.readmany(start, length)
                return {a: ec.read(a) for a in addrs}

            prev = sweep()
            for a, v in prev.items():
                first_last[a] = (v, v)
            print(f"{now()}  baseline: 0x{start:04X}-0x{start + length - 1:04X} "
                  f"({length} bytes), sweeping every {args.interval}s")
            if args.block:
                print("  --block: reading 4 bytes per IOCTL (MMRD) instead of "
                      "1 (ECRR).\n  That path has never been run against the "
                      "driver, and it is not a safety improvement over the "
                      "byte read: see this tool's help")
                if start < FAN_TACH.stop and start + length > FAN_TACH.start:
                    print("  warning: this range covers the fan-tach bytes "
                          f"0x{FAN_TACH.start:04X}-0x{FAN_TACH.stop - 1:04X}, "
                          "whose ECRR reads stalled the fans on a sibling "
                          "board (#94). A 4-byte read across the page is a "
                          "different access shape, not a safer one -- run "
                          "per-byte, or move the range off it.")
            if args.mark:
                print("type a label + Enter to stamp a mark "
                      "(a blank line records nothing); Ctrl-C to stop")
            else:
                print("Ctrl-C to stop")

            while True:
                time.sleep(args.interval)
                sweeps += 1
                cur = sweep()
                for a in addrs:
                    v = cur[a]
                    old = prev[a]
                    if v != old:
                        prev[a] = v
                        changes[a] = changes.get(a, 0) + 1
                        first_last[a] = (first_last[a][0], v)
                        ts = now()
                        print(f"{ts}  0x{a:04X}: 0x{old:02X} -> 0x{v:02X}",
                              flush=True)
                        if sink:
                            sink.row([ts, f"0x{a:04X}",
                                      f"0x{old:02X}", f"0x{v:02X}"])
                if args.seconds and time.time() - t0 >= args.seconds:
                    break
    except KeyboardInterrupt:
        print()
    except EcError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    finally:
        if sink:
            sink.close()

    elapsed = time.time() - t0
    print(f"\n=== {sweeps} sweeps over {elapsed:.0f}s, "
          f"{len(changes)} addresses changed ===")
    if marker.marks:
        print("\nmarks:")
        for ts, label in marker.marks:
            print(f"  {ts}  {label}")

    if not changes:
        print("nothing moved.")
        return 0

    quiet = sorted(a for a, n in changes.items() if n <= 2)
    busy = sorted(a for a, n in changes.items() if n > 2)

    print(f"\nquiet -- changed once or twice; a settings write looks like this "
          f"({len(quiet)}):")
    for a in quiet:
        f, l = first_last[a]
        print(f"  0x{a:04X}  0x{f:02X} -> 0x{l:02X}   ({changes[a]}x)")

    print(f"\nbusy -- changed on many sweeps, most likely a sensor ({len(busy)}):")
    for a in busy:
        f, l = first_last[a]
        print(f"  0x{a:04X}  0x{f:02X} -> 0x{l:02X}   ({changes[a]}x)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
