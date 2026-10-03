#!/usr/bin/env python3
"""Does every committed `--self-test` transcript under `ec/annotations/` quote
the run that mode prints today?

`test_disasm8051_oracle.py`'s `TranscriptContract` holds the *producer* -- the
summary line and the four `REL_SITES` rows, byte for byte, as `self_test()`
prints them. It held nothing about the *copies*: every committed transcript is
a fence somebody pasted by hand, and adding a clause to the mode left all of
them saying something the run no longer says. Some were already stale when that
suite was written, which its own docstring recorded rather than fixed.

This holds the copies against the producer. The summary line is compared
byte-for-byte to whatever the mode prints on its own: this file carries no
literal of that line, so a check restating it would go stale exactly the way
the markdown does, one merge later. `test_disasm8051_oracle.py`'s
`TranscriptContract.SUMMARY` does hold the line as a string, but that assertion
runs the other way -- the run's last line against what the mode prints -- and
it is the half that already existed. Reading the committed fences is the half
that was missing.

**A prompt is what makes a fence findable, and that is the whole scoping rule.**
A `self-test passed:` line is a transcript only when a fenced block above it
names this tool with `--self-test`; the same line in a block whose prompt names
`check_site_resolution.py` is another tool's output. The flag is part of the
test because this tool is invoked all over `ec/annotations/` as `--at 0x...`,
one decode after another, and a rule without it would read every one of those as
a transcript with a missing summary. A fence counts as a fence in every shape
the directory writes one -- at column one, indented into a list item, or inside a
blockquote -- because a marker recognised in only one of those would drop the
others out of the corpus without declining them, which is the quiet version of
the defect this tool exists for. See `blocks()`.

`docs/findings/` is out of scope rather than half-covered, and not because its
copies lack prompts -- several carry a valid one and this walk would find them.
It is because the same directory holds copies this rule cannot reach: two are
quoted in gate-output blocks whose `$ ` prompt is the scratch gate rather than
the command that printed them. A rule aimed at that directory would cover it
unevenly and quietly, which is worse than a stated boundary. Named in
`docs/findings/disasm8051-transcript-copies.md`, not here.

**What is declined, counted, printed, and never failed** -- every negative here
is *not read by this method*, never *absent*, which is the caveat
`ec/annotations/registers.yaml` carries for a static scan and
`census_test_line_pins.py` prints for a citation walk. Two shapes:

  * the command in an `sh` fence, which lists reproduction steps rather than
    quoting a session. `pd-index-geometry.md` 8.2 does this, and it must not be
    edited into a transcript;
  * a `self-test passed:` line under a prompt naming a *different* tool, which
    is that tool's mode -- `pd-index-geometry.md`'s block quotes
    `pd_index_geometry.py --self-test`.

Neither is a failure, and the run says how many of each it passed over so
"found nothing wrong" cannot read as "found nothing".

**Two shapes of the same-looking hole *are* failures**, because in both the
corpus has quietly shrunk and the run would otherwise stay green:

  * a summary line with **no prompt above it at all**. It is not another
    tool's mode -- something else's prompt would say so -- it is a transcript
    of nothing: this mode's `$ ...` line was lost, and the summary is now held
    by no reader.
  * a `console` fence naming the command and quoting **no summary**. A fence
    written to quote a session promised one; the fence's info string is what
    makes that decidable rather than a guess, and `sh` versus `console` is the
    distinction the committed tree already draws.

Declining either would be the quiet version of the defect this tool exists for.
The suite has both, and the vacuity guard below is their extreme.

**The lines between the prompt and the summary are not held, deliberately.**
Transcripts elide the run's middle with `...` inconsistently -- some do, some
quote it whole -- so holding those lines would mean either accepting two shapes
or pinning the generated `BIT_SITES` and `TEXTBOOK_BIT_SITES` rows into
markdown files, which turns a legitimate addition to either table into a merge
conflict in five documentation files. The claim held here is the summary line,
and it is the line a reader cites.

**There is no asserted count of the corpus.** No "there are N transcripts"
constant is written in this file and no test asserts one, because that figure is
a value every merge adding a transcript would have to edit, which is the shape
that has bitten this repository repeatedly. The message the run prints *does*
carry the number, and that number is computed from what the run found on this
tree: a merge that adds or removes a transcript moves it with no edit anywhere.
The guard below is that the corpus is *not empty*, not that it is a particular
size.

**A red mode is not a documentation drift.** If `self_test()` exits non-zero
this prints the run's own output and exits 2 without comparing anything: the
mode disagreesing with its transcriptions is a different defect, and reporting
it as N stale `.md` files would be wrong in the direction that is hardest to
diagnose from the message alone.

Nothing here reads firmware beyond that one `self_test()` call, which reads
the committed image the gate's own arm reads. No capture, no EC, no register
read back, nothing deferred to a human at the machine.

Usage:
    python3 ec/tools/check_disasm8051_transcripts.py
    python3 ec/tools/check_disasm8051_transcripts.py --verbose
"""
import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
EC = HERE.parent
DEFAULT_FIRMWARE = str(EC / "firmware" / "GMxMGxx_11.800")
DEFAULT_ANNOTATIONS = str(EC / "annotations")

# A fence marker: ``` and the info string after it, preceded by whitespace,
# `>` blockquote markers, or both. Group 1 is that prefix, which the block's
# body is dedented by -- see `blocks()` and `_dedent`.
FENCE = re.compile(r"^([ \t]*(?:>[ \t]*)*)```(.*)$")

# The mode's own success line, read as a prefix rather than as the whole
# string: the run's text is the producer's to choose, and this holds the copies
# against whatever it prints today. Matching on the prefix also means a block
# quoting a *different* tool's `self-test passed: ...` is still recognised as a
# summary-shaped line and declined by prompt rather than missed.
SUMMARY = "self-test passed:"

# The prompt that makes a fenced block a transcript: this tool's name and the
# mode's flag on one line. Both are required because the same tool is invoked
# without `--self-test` throughout `ec/annotations/` (`--at 0x...` decodes
# quoted one after another), and a prompt match without the flag would read
# every one of those as a transcript with a missing summary.
PROMPT = ("disasm8051.py", "--self-test")

# The decline reasons and the unattributed-line problem, as text. Spelled once
# so the reason a reader sees is the same string the suite asserts on, rather
# than a paraphrase of each.
_NO_SUMMARY = ("names `disasm8051.py --self-test` and quotes no `self-test "
               "passed:` line at all. In a `console` fence that line was there "
               "and has been deleted, which leaves a transcript with nothing "
               "in it for this check to hold")
_RECIPE = ("names `disasm8051.py --self-test` and quotes no `self-test passed:` "
           "line, in a shell fence that lists reproduction steps rather than "
           "quoting a session, so it is a recipe and not a transcript")
_OTHER_MODE = ("a `self-test passed:` line under a prompt naming another "
               "tool, so it is that tool's mode")
_NO_PROMPT = ("a `self-test passed:` line with no prompt above it at all. It "
              "reads as a transcript of nothing: either this mode's `$ ...` "
              "line was lost, and the line is now held by nothing, or it "
              "belongs to a mode whose prompt was not transcribed")

# A shell prompt in a transcript fence. `$ ` is what the `console` fences use;
# the `sh` fence in `pd-index-geometry.md` 8.2 writes the bare command. Both
# are stripped before the PROMPT test so a leading `$` cannot hide the flag.
PROMPT_PREFIXES = ("$ ", "python3 ")


def is_prompt(line):
    """Whether a fenced line is a shell prompt rather than program output."""
    return line.startswith(PROMPT_PREFIXES) or line.startswith("$")


def _dedent(line, prefix):
    """Strip a fence's own prefix from one of its lines.

    A fence that is indented, or written inside a blockquote, indents its body
    with it. Read verbatim, a body line then starts with two spaces or with
    `> `, and matches neither the prompt test nor the `self-test passed:`
    prefix -- so an indented transcript would be found as a block that quotes
    nothing, or not as a block at all. Stripping what the opening marker was
    preceded by is what makes the indented shape read the same as a column-one
    one; a line that does not carry the prefix (a lazy blockquote continuation)
    gives up the same number of leading spaces instead.
    """
    if prefix and line.startswith(prefix):
        return line[len(prefix):]
    n = 0
    while n < len(prefix) and n < len(line) and line[n] in " \t":
        n += 1
    return line[n:]


def blocks(text):
    """Yield (info_string, [(lineno, line)]) for each fenced block.

    A fence marker is ``` preceded by whitespace, `>` blockquote markers, or
    both -- the shapes a fenced block takes inside a list item or a quote,
    which `ec/annotations/` uses in several files. The marker is matched with a
    leading-whitespace-and-quote pattern rather than `startswith("```")` on
    purpose: a marker at column one is only one of the shapes, and a reader
    that recognised only that one would drop an indented transcript out of the
    corpus silently, which is the same quiet shrinkage the two failure shapes
    below exist to prevent. The marker found opening the block is stripped from
    its body by `_dedent`, so the caller sees the same lines either way.

    The info string after the marker is carried out with the block because it is
    what tells a transcript from a recipe -- see `quotes_output()`. A file with
    no fence at all yields nothing rather than raising: the caller reports an
    empty corpus as its own failure, and a parser that threw would say the same
    thing less legibly.
    """
    inside = False
    start, tag, prefix, cur = 0, "", "", []
    for lineno, line in enumerate(text.splitlines(), 1):
        match = FENCE.match(line)
        if match:
            if inside:
                yield tag, cur
                cur = []
            else:
                start, prefix = lineno, match.group(1)
                tag = match.group(2).strip()
            inside = not inside
            continue
        if inside:
            cur.append((lineno, _dedent(line, prefix)))
    if inside and cur:
        # An unterminated fence: the block is still a block, and refusing it
        # would let a truncated file pass by having nothing to compare.
        yield tag, cur


def quotes_output(tag):
    """Whether a fence is written to quote a session rather than list commands.

    `console` is the transcript convention in `ec/annotations/` and every
    committed transcript uses it; `sh` is the recipe convention, and the one
    block that names the command without quoting it is `sh`. That is what makes
    a missing summary decidable rather than ambiguous: in a `console` fence the
    summary line was there and has gone, and in an `sh` fence it was never
    promised. An untagged fence is read as quoting, because that is the
    conservative direction -- it reports a missing summary rather than passing
    one that is not there.
    """
    return tag in ("", "console")


def _report_missing(pending, tag, problems, declined):
    """Record a matching prompt that quoted no summary line, into the right list.

    A `console` fence is quoting a session, so a summary it does not quote is
    one that was deleted -- and a transcript that has lost its only held line is
    indistinguishable from a correct one, so that is a problem. An `sh` fence
    lists reproduction steps and never promised a summary, so that is declined.
    """
    if quotes_output(tag):
        problems.append((pending, _NO_SUMMARY))
    else:
        declined.append((pending, _RECIPE))


def transcripts(text):
    """-> (found, problems, declined) for one file's fenced blocks.

    `found` is [(lineno, prompt_lineno, quoted_summary_line)] for every summary
    line under a matching prompt; `declined` is [(lineno, reason)] for the two
    shapes this reader refuses; `problems` is [(lineno, reason)] for a summary
    line **nothing** claims.

    Scanned prompt-first, and the **nearest** prompt above a summary line
    decides whose it is -- which is what keeps a block quoting two tools'
    output, as `bank-call-audit.md`'s does, from attributing one tool's line to
    the other. Three answers, and the third is the one that has to fail:

      * a prompt naming this mode -- ours, compare it;
      * a prompt naming something else -- declined, another mode's summary.
        `pd-index-geometry.md`'s block quotes `pd_index_geometry.py`'s;
      * **no prompt at all** -- nothing claims the line. Declining it would be
        the quiet version of the defect this tool exists for: a transcript that
        loses its `$ ...` prompt stops being findable, and a reader is left
        with a green run over a corpus one smaller. It is reported instead.
    """
    found, problems, declined = [], [], []
    for tag, rows in blocks(text):
        # `ours` is the lineno of the nearest matching prompt, None when the
        # nearest prompt named something else; `seen` says whether any prompt
        # has appeared in this block at all. The two are separate questions and
        # one of the three answers is a failure, so none of them is inferred
        # from another.
        ours, seen = None, False
        pending = None          # a matching prompt that has quoted no summary yet
        for lineno, line in rows:
            if is_prompt(line):
                seen = True
                stripped = line.lstrip("$ ").strip()
                ours = lineno if all(p in stripped for p in PROMPT) else None
                if ours is not None:
                    if pending is not None and pending != ours:
                        _report_missing(pending, tag, problems, declined)
                    pending = ours
                elif pending is not None:
                    # A later prompt superseded a matching one that quoted
                    # nothing, so it is reported at its own line either way.
                    _report_missing(pending, tag, problems, declined)
                    pending = None
                continue
            if not line.startswith(SUMMARY):
                continue
            if ours is not None:
                found.append((lineno, ours, line))
                pending = None
            elif seen:
                declined.append((lineno, _OTHER_MODE))
            else:
                problems.append((lineno, _NO_PROMPT))
        if pending is not None:
            _report_missing(pending, tag, problems, declined)
    return found, problems, declined


def scan(annotations):
    """-> (found, problems, declined, unreadable) over every `*.md` under
    `annotations`.

    `rglob`, so an annotation file that moves into a subdirectory is still
    covered rather than silently dropping out of the corpus.
    """
    found, problems, declined, unreadable = [], [], [], []
    root = Path(annotations)
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            unreadable.append((str(rel), exc))
            continue
        here, lost, skipped = transcripts(text)
        found.extend((str(rel), n, p, line) for n, p, line in here)
        problems.extend((str(rel), n, why) for n, why in lost)
        declined.extend((str(rel), n, why) for n, why in skipped)
    return found, problems, declined, unreadable


def current_summary(firmware, annotations):
    """-> (exit code, the run's last line, every line it printed).

    `self_test()` is run whole rather than its summary reconstructed, so this
    file carries no literal of that line: the whole point of the check is that
    the committed markdown is held against the producer rather than against
    another literal that would drift the same way. (`TranscriptContract.SUMMARY`
    in `test_disasm8051_oracle.py` is a literal of the line too, but it pins
    the producer -- the run's last line against the mode -- which is the half
    that was already held.) The full output comes back too because the
    red-mode path prints the run rather than a paraphrase of it.
    """
    sys.path.insert(0, str(HERE))
    import disasm8051

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = disasm8051.self_test(firmware, annotations)
    lines = buf.getvalue().splitlines()
    return rc, (lines[-1] if lines else ""), lines


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--firmware", default=DEFAULT_FIRMWARE,
                    help="the committed EC image (default: %(default)s)")
    ap.add_argument("--annotations", default=DEFAULT_ANNOTATIONS,
                    help="the annotation directory to scan (default: %(default)s)")
    ap.add_argument("--verbose", action="store_true",
                    help="print every transcript and every decline with its "
                         "reason, so a reader can see the population rather "
                         "than trust it")
    args = ap.parse_args()

    try:
        rc, summary, run_lines = current_summary(args.firmware, args.annotations)
    except OSError as exc:
        print(f"the firmware cannot be read: {exc}", file=sys.stderr)
        return 2
    if rc:
        # The mode is red, so there is no trustworthy producer to hold the
        # copies against. Report the run and refuse to compare.
        for line in run_lines:
            print(line)
        print(f"`disasm8051.py --self-test` exited {rc}, so no transcript was "
              f"compared. That is a red mode, not documentation drift: the "
              f"disagreement is between the mode and its own transcriptions.",
              file=sys.stderr)
        return 2

    found, unattributed, declined, unreadable = scan(args.annotations)
    problems = [f"{rel}:{n}  {why}" for rel, n, why in unattributed]
    for rel, n, _prompt, line in found:
        if line == summary:
            if args.verbose:
                print(f"  ok  {rel}:{n} quotes the run's summary line")
        else:
            problems.append(f"{rel}:{n} quotes\n    {line}\n  and the run prints\n"
                            f"    {summary}")
    for rel, why in unreadable:
        problems.append(f"{rel} could not be read: {why}")

    if not found:
        # The vacuity guard, and the same one `disasm8051_oracle.py` applies to
        # a span its parser covers no row of: a corpus that matched nothing is
        # a failure, not a pass. Without it a rename of every transcript out of
        # the scanned directory would report this tool working.
        problems.append(
            f"no `disasm8051.py --self-test` transcript was found under "
            f"{args.annotations}, so nothing was compared. That is a red run, "
            f"not a clean one: either the transcripts have moved or the prompt "
            f"this reader keys on has been reworded.")

    print(f"{args.annotations}: {len(found)} committed transcript(s) agree "
          f"with the run, {len(declined)} line(s) declined and listed under "
          f"--verbose")
    if args.verbose:
        for rel, n, why in declined:
            print(f"  --  {rel}:{n}  {why}")
    for line in problems:
        print(line, file=sys.stderr)
    if problems:
        print(f"{len(problems)} problem(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
