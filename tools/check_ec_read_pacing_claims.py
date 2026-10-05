#!/usr/bin/env python3
r"""Check the two things a change to these two tools' defaults makes go stale.

`windows/tools/ec_watch.py` and `windows/tools/ecrw.py dump` leave the fan-tach
page `0x0460-0x046F` out by default and sleep `--gap-ms` after each read. Both
defaults change what committed prose about them can honestly say, and the class
of prose that says it has no natural stopping point: six review rounds on this
issue each fixed the sites a review named and each surfaced more, because
nothing enumerated the class. This tool is the enumeration, and it derives its
subject from the tools rather than from a list of files.

**Two properties, both derived, and no census anywhere.**

  1. **A rate claim about these tools must be one their defaults produce.** The
     sweep cost is computed here -- from `--gap-ms`, `--interval`, the default
     range and the page -- and a committed block that states a rate or a sweep
     period for one of these tools has to agree with it. Move a default and
     this goes red on the sentence that described the old one, with no edit to
     anything in this file.
  2. **A place attributing the open `ECRR` pacing work to #94 must name a tool
     that is still unpaced.** Which tools read the EC is read out of their own
     sources — they either bind `Ec` from `ecrw` at module level or, in
     `ecrw`'s own case, define it — and which of those pace themselves is
     read out of the same sources (`--gap-ms` declared or not). An attribution
     whose tools are all paced names no open work, and the two this diff paced
     drop out of every attribution on their own. `ecrw.py` is in that subject
     set for the same reason `ec_watch.py` is: it is one of the two tools the
     rule is written about, and a rule that could not see one of them was a
     rule a contributor could not trip on the tool named in half the issue's
     title.

**What a red run means and what it does not.** Both properties read prose, so
both are heuristics with a stated failure direction, and both are written to
fail *loudly and legibly* rather than to be right about everything:

  * Property 1 is skipped for a block that carries a record of a run -- an
    ISO date or an `evidence/` path. `evidence/README.md`'s "0.2 s sweeps"
    describes two committed captures and is exactly as true as it ever was.
    That is the distinction the review asked to be made explicit, and it is
    keyed on the block naming a *run* rather than on the tense of a verb.
  * A figure is admitted when it is within 5% of a computed one, so prose that
    rounds is prose that passes. A number outside every window is refused even
    if it happens to be defensible, because the remedy -- restating the
    sentence from the banner the tool now prints -- is cheap and the cost of
    a wrong refusal is a red run naming the sentence, not a silent pass.

A refusal prints the file, the line, what the block said and what the tool
computes, so the fix is a sentence to rewrite rather than a figure to look up.

**Where the refusals are held.** In
`tools/test_check_ec_read_pacing_claims.py`, one case per rule against the
string it refuses and against the string beside it that it must not. This tool
carries no `--self-test` of its own: two copies of the same refusals is one of
them to update and one of them to forget.

Usage:
    python3 tools/check_ec_read_pacing_claims.py
    python3 tools/check_ec_read_pacing_claims.py --check
"""
import argparse
import ast
import functools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir))

TOOLS = os.path.join("windows", "tools")
WATCH = "ec_watch.py"
DUMP = "ecrw.py"

# The shared offline fixture, which defines an `Ec` to be installed in place of
# `ecrw.py` and is not itself a tool. See `ec_tools`.
FAKE = "ecrw_fake.py"

# This file and its suite, which the discovery below would otherwise read.
# The suite's fixtures are prose shaped exactly like the sentences this refuses
# -- that is what makes them fixtures -- so scanning either would have the
# check reporting its own test data. Neither restates a retired figure, which
# is why skipping them costs no coverage.
SELF = ("check_ec_read_pacing_claims.py", "test_check_ec_read_pacing_claims.py")

# Text extensions the claim scan reads. Markdown for the write-ups and the
# runbooks, Python for the tool docstrings and the comments beside a default --
# which is where the two tools describe themselves, and which is why the
# claim this change makes has to be allowed to live in either.
SUFFIXES = (".md", ".py")

# `find` walks into these and the committed tree does not hold them. Same list
# and same reason as `run-tests.sh`'s and `tools/test_readme_suite_table.py`'s:
# a set defined three ways is three answers, and `.claude/` in particular holds
# a second checkout whenever a developer has a worktree open.
PRUNED = (".git", ".claude", "vendor")

# The two subjects of property 1, as they are spelled in prose.
SUBJECTS = (r"ec_watch(?:\.py)?", r"ecrw\.py")

# A frequency claim: "about 2.5 times a second", "2.5 sweeps/second".
FREQUENCY = re.compile(
    r"(?P<fig>\d+(?:\.\d+)?)\s*(?:times?\s+a\s+second|"
    r"sweeps?\s*(?:/|per)\s*second|sweeps?\s+a\s+second)", re.IGNORECASE)

# A duration claim. Four shapes, and each one has to carry a read or a sweep
# next to its figure -- a bare "20 s" is a `--seconds 20` and a "500 ms" is a
# timeout somewhere else, and a scan that read either as the tool's read rate
# would be refusing numbers it has no subject for. What is refused is a figure
# attached to how long a sweep takes or how long a read waits:
#
#   "sweeps 2 KiB of EC space in about 150 ms"     -> seconds/1000 = 0.15
#   "its 0.25 s default sweep"                      -> --interval
#   "12.2 s per sweep"                              -> the sweep cost
#   "a sweep of the default range, 12.2 s"          -> the sweep cost
#
# The first is the one that actually went stale, and it is matched by the
# word "sweep" rather than by anything to do with #94, so it keeps working
# against a sentence worded in a way nobody here would have predicted.
DURATION = re.compile(
    r"(?:(?:sweeps?|sweeping|reads?)\b[^.]{0,60}?\bin\s+(?:about\s+|roughly\s+)?"
    r"|(?:a|one|each)\s+sweep\b[^.]{0,40}?[,\s]+(?:about\s+|roughly\s+)?)"
    r"(?P<fig>\d+(?:\.\d+)?)\s*(?P<unit>ms|seconds?|secs?|s)\b"
    r"|(?P<fig2>\d+(?:\.\d+)?)\s*(?P<unit2>ms|seconds?|secs?|s)\s+"
    r"(?:of\s+sleeping\s+)?(?:default\s+)?sweeps?\b"
    r"|(?P<fig3>\d+(?:\.\d+)?)\s*(?P<unit3>ms|seconds?|secs?|s)\s+per\s+sweep\b",
    re.IGNORECASE)

# What makes a block a record of a run rather than a claim about a tool. Both
# are things a run has and a tool does not.
RECORD = re.compile(r"\d{4}-\d{2}-\d{2}|\bevidence/")

# The phrasings that attribute work to an issue. The list is a rule, not a
# census: these are the shapes this repository uses, and a new one is a new
# word in this tuple rather than a new file in a table.
#
# "unpaced" and "does not pace" are here because of what happened when they
# were not. The first version of this rule knew only the older wording -- "the
# open work", "#94 owns" -- so every attribution restated to the newer phrasing
# stopped matching it and went green without anybody deciding it should. A
# vocabulary that its own remedy can outrun is not a rule; these are the words
# the restatements actually use, so a site that stops being an attribution has
# to stop saying it is one rather than stopping being caught.
#
# "#94's open" rather than a bare "#94's", for the same reason in the other
# direction: #94 also owns an access shape, a watch-set contract and a runbook,
# none of which this rule has any standing over, and the sentences that say so
# were being refused with it.
OPEN_WORK = re.compile(
    r"open work|still the open|the open question|is the open|"
    r"owns making these tools|#94's open|"
    r"unpaced|does not pace|do not pace", re.IGNORECASE)

# `#94` and not `#940`: several issues are numbered in the 900s and this
# repository cross-references them by number in running prose, so a bare
# substring match reads half a dozen unrelated paragraphs as attributions.
ISSUE_94 = re.compile(r"#94\b")

TOOL_NAME = re.compile(r"\b([a-z_][a-z0-9_]*\.py)\b")

# How far a stated figure may sit from a computed one and still be the same
# figure written out. Prose rounds; 12.192 s is "about 12 s" in a runbook and
# 12.2 in a second one, and both are the same claim.
TOLERANCE = 0.05


# --- reading the tools --------------------------------------------------

def parse(path):
    with open(path, encoding="utf-8") as f:
        return ast.parse(f.read(), filename=path)


def declared_defaults(path):
    """`{flag: default}` for every `add_argument` in `path`, read by `ast`.

    `ast` rather than an import, so this reads committed text and opens
    nothing: `ec_watch.py` imports `ecrw` at module scope, and an import here
    would mean either running the tool's dependencies or installing a fake for
    them, for a value that is a literal in the source.
    """
    out = {}
    for node in ast.walk(parse(path)):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"
                and node.args and isinstance(node.args[0], ast.Constant)):
            continue
        keywords = {k.arg: k.value for k in node.keywords}
        if "default" not in keywords:
            continue
        try:
            out[node.args[0].value] = ast.literal_eval(keywords["default"])
        except (ValueError, SyntaxError):
            continue
    return out


def declared_range(path):
    """The module's own `FAN_TACH` as a set, or None when it declares none.

    Read rather than written here, because the page is the tools' statement of
    where the hazard is and a second copy would be the drift this whole tool
    exists to catch. A tool that renames the constant goes uncovered rather
    than wrong, which is the safe direction for a default to fail in.
    """
    for node in parse(path).body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "FAN_TACH"
                   for t in node.targets):
            continue
        value = node.value
        if (isinstance(value, ast.Call) and getattr(value.func, "id", None)
                == "range" and len(value.args) == 2):
            try:
                start, stop = (ast.literal_eval(a) for a in value.args)
            except ValueError:
                return None
            return set(range(start, stop))
    return None


def reads_ec(path):
    """Whether a tool binds `Ec` from `ecrw`, or is the module defining it.

    How the set of EC-reading tools is derived rather than listed: a new tool
    in `windows/tools/` that goes through the driver is covered by this the
    day it is written, and one that does not is not swept up by it.

    The second half is not decoration. `ecrw.py` is where `Ec` is *defined*,
    so the import test alone excludes the module every other tool in the
    directory gets it from — and `ecrw.py dump` is one of the two tools this
    checker is written about. A rule whose subject set silently drops one of
    the two tools a diff paced cannot hold an attribution resting on it, so
    "did you pace it" was unanswerable for exactly the tool named in half the
    issue's own title. Both tests read the same source they always did: one
    binds the name, the other defines it.
    """
    for node in parse(path).body:
        if isinstance(node, ast.ClassDef) and node.name == "Ec":
            return True
        if (isinstance(node, ast.ImportFrom) and node.module == "ecrw"
                and any(a.name == "Ec" for a in node.names)):
            return True
    return False


def paces_reads(path):
    """Whether a tool declares `--gap-ms`, read the same way as everything else.

    The definition of paced here, and deliberately a narrow one: a flag whose
    default is zero, or a sleep somewhere the sweep does not reach, would read
    as paced to a source scan and would then be offered as an open question
    that is not open. That direction is the safe one for this rule -- the
    attribution stays, and the reviewer reads it.
    """
    return "--gap-ms" in declared_defaults(path)


@functools.lru_cache(maxsize=1)
def ec_tools():
    """`{name: path}` for every tool in `windows/tools/` that reads the EC.

    Cached, and not for tidiness: every one of these calls parses a module's
    whole AST, and the scan asks once per file over a repository's worth of
    them. The tree does not change under a run, so the answer cannot go stale
    inside one.

    `ecrw_fake.py` is skipped by name because it is a fixture rather than a
    tool, and it is the one module here that defines an `Ec` without being one:
    every suite in this directory installs it in place of `ecrw.py`, and it
    opens no driver. It would otherwise be read as an EC tool and, having no
    `--gap-ms`, as an unpaced one -- an open question about a file whose whole
    purpose is to be a test double.
    """
    out = {}
    for name in sorted(os.listdir(os.path.join(REPO, TOOLS))):
        if not name.endswith(".py") or name.startswith("test_") \
                or name == FAKE:
            continue
        path = os.path.join(REPO, TOOLS, name)
        if reads_ec(path):
            out[name] = path
    return out


# --- what the tools' defaults produce -----------------------------------

def computed():
    """The figures these tools' own defaults produce, and what they are of.

    Every number here comes out of `ec_watch.py`'s argparse and its own
    `FAN_TACH`. Nothing is written down twice, which is the property that
    keeps this from going stale the way a table of prose sites would.
    """
    watch = os.path.join(REPO, TOOLS, WATCH)
    defaults = declared_defaults(watch)
    page = declared_range(watch) or set()
    start = int(str(defaults["--start"]), 0)
    length = int(str(defaults["--len"]), 0)
    addrs = [a for a in range(start, start + length) if a not in page]
    gap_s = defaults["--gap-ms"] / 1000.0
    interval = defaults["--interval"]
    sweep_s = len(addrs) * gap_s
    return {
        "gap_s": gap_s,
        "interval": interval,
        "addresses": len(addrs),
        "sweep_s": sweep_s,
        "sweeps_per_s": 1.0 / (interval + sweep_s),
    }


def admits(stated, figure):
    """Whether `stated` is `figure` written out rather than a different one."""
    return abs(stated - figure) <= abs(figure) * TOLERANCE + 1e-12


# --- reading the prose -------------------------------------------------

@functools.lru_cache(maxsize=None)
def read_lines(path):
    """A file's lines, read once per run.

    `blocks` splits them and `corrected_alongside` looks at them again, and
    both are asked once per block rather than once per file; reading the file
    each time made the scan cost a function call per block rather than a read
    per file.
    """
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def blocks(path):
    """`(line, text)` per blank-line-separated block of a file.

    A block rather than a line because the claims are wrapped: the tool name
    and the figure about it routinely land on different lines of the same
    paragraph, and a line-keyed scan would read half of each and pass on both.
    Code fences are split on their own so a `console` block reads as the
    operator-facing text it is rather than as part of the prose around it.
    """
    text = "\n".join(read_lines(path))
    out = []
    for start, body in enumerate(text.split("\n\n")):
        first = text[:text.index(body)].count("\n") + 1 if body else start + 1
        if "```" in body:
            parts = re.split(r"```[^\n]*\n?", body)
        else:
            parts = [body]
        for part in parts:
            if part.strip():
                out.append((first, part))
    return out


def prose_files():
    """Every committed `.md` and `.py` this scan reads, relative and sorted."""
    out = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in PRUNED]
        for name in sorted(filenames):
            if not name.endswith(SUFFIXES) or name in SELF:
                continue
            out.append(os.path.relpath(os.path.join(dirpath, name), REPO))
    return sorted(out)


def claim_figures(shape, body):
    """`(text, seconds)` for every figure `shape` reads in `body`.

    Each alternative of a shape names its figure and its unit in its own
    groups, so this walks `groupdict` rather than assuming one pair -- which is
    also what lets a shape that has no unit group at all, such as
    `FREQUENCY`, be read by the same function.
    """
    out = []
    for m in shape.finditer(body):
        groups = m.groupdict()
        for fig in ("fig", "fig2", "fig3"):
            if groups.get(fig) is None:
                continue
            value = float(groups[fig])
            unit = groups.get(fig.replace("fig", "unit"))
            if unit and unit.lower() in ("ms", "msec", "millis"):
                value /= 1000.0
            out.append((m.group(0).strip(), value))
    return out


def rate_problems(rel, figures):
    """Every rate claim in one file that its own defaults do not produce."""
    problems = []
    path = os.path.join(REPO, rel)
    for line, body in blocks(path):
        said = rate_disagreement(body, figures,
                                 corrected_alongside(path, line))
        if said is not None:
            problems.append({"file": rel, "line": line, "said": said,
                             "computed": describe(figures)})
    return problems


def rate_disagreement(body, figures, corrected=False):
    """The stale figure in `body`, or None.

    The two exemptions are here rather than in the file walk above, because
    they are part of the rule and not of where it is applied: a block that
    records a run may keep that run's figure, and a block whose figure a
    `CORRECTION` follows in the same section may keep the figure too. Split
    out from the walk so `tools/test_check_ec_read_pacing_claims.py` can hold
    each of them on a string, which is the only way either is testable.

    One refusal per block, on the first shape that objects: a sentence that
    repeats its own figure three ways is one stale claim, and three refusals
    for it would send somebody to fix one sentence three times.
    """
    if RECORD.search(body) or corrected:
        return None
    if not any(re.search(s, body) for s in SUBJECTS):
        return None
    for shape, frequency in ((FREQUENCY, True), (DURATION, False)):
        said = next((text for text, value in claim_figures(shape, body)
                     if not admits_seconds(value, figures, frequency)), None)
        if said is not None:
            return said
    return None


# The marker CLAUDE.md's `docs/findings.md` §4a-4d pattern puts beside a
# retracted figure: the wrong number stays, with its correction next to it, and
# a checker that demanded the number go would be demanding a silent edit.
CORRECTION = re.compile(r"\bCORRECTION\b")

HEADING = re.compile(r"^#{1,6}\s")


def corrected_alongside(path, line):
    """Whether a `CORRECTION` follows this line before the next heading.

    The repository's own retraction rule, read rather than restated: a wrong
    figure may stay visible where the correction to it is beside it, which is
    `CLAUDE.md` §4a-4d and the pattern §4g uses. Scoped to the section -- from
    the line to the next markdown heading -- so one correction somewhere in a
    long file does not exempt a stale claim two hundred lines away, and
    markdown-only, because a comment beside a default is not a record of a
    correction and is not exempt.
    """
    if not path.endswith(".md"):
        return False
    for text in read_lines(path)[line - 1:]:
        if HEADING.match(text):
            return False
        if CORRECTION.search(text):
            return True
    return False


def admits_seconds(value, figures, frequency):
    """Whether `value` is one of the durations -- or the one frequency."""
    if frequency:
        return admits(value, figures["sweeps_per_s"])
    return any(admits(value, figures[k])
               for k in ("sweep_s", "interval", "gap_s"))


def describe(figures):
    """The computed figures, in the words a refusal needs them in."""
    return (f"{figures['sweep_s']:.1f} s of sleeping per sweep over "
            f"{figures['addresses']} reads, "
            f"{figures['sweeps_per_s']:.3f} sweeps a second at "
            f"--interval {figures['interval']}")


def attribution_problems(rel, tools):
    """Every #94 attribution in one file that names no still-unpaced tool."""
    path = os.path.join(REPO, rel)
    paced = paced_tools()
    unpaced = {name for name in tools if name not in paced}
    mentions = None
    problems = []
    for line, body in blocks(path):
        if not ISSUE_94.search(body) or not OPEN_WORK.search(body):
            continue
        # An anaphoric attribution -- "the open work that would make these
        # tools safe" -- names nothing in its own paragraph, so the tools are
        # resolved against the rest of its file before the rule is asked
        # whether anything behind the claim is still open. That is not a
        # loophole: a runbook points at one tool and a tool's banner is talking
        # about itself, and in both cases the tool behind the claim is named
        # somewhere in the same file even where the sentence does not repeat
        # it.
        #
        # The two sources are *unioned*, not tried in order. Taking the first
        # that matches let a paragraph naming one paced tool throw away the
        # unpaced tool its own file is about: a runbook for
        # `gpu_block_watch.py` that happens to mention `ecrw.py` in the same
        # block was read as an attribution resting on `ecrw.py` alone, and
        # refused for work that is still open. The claim rests on everything
        # behind it, so any one still-unpaced tool carries it — which is the
        # same direction this rule takes everywhere else, where a stale
        # attribution a reviewer reads is safer than a silent pass.
        if mentions is None:
            mentions = file_mentions(path, rel, tools)
        resolved = {n for n in TOOL_NAME.findall(body) if n in tools} \
            | (mentions & unpaced)
        named = attribution_disagreement(
            body, {n: tools[n] for n in resolved if n in paced},
            {n: tools[n] for n in resolved if n in unpaced})
        if named is None:
            continue
        problems.append({"file": rel, "line": line,
                         "said": first_sentence(body), "named": named})
    return problems


@functools.lru_cache(maxsize=1)
def paced_tools():
    """Which tool in `ec_tools()` declares `--gap-ms`.

    Cached for the same reason `ec_tools` is, and taking no argument because
    the dict it would key on is not hashable. `attribution_problems` takes
    `tools` from its caller and asks this for the same `ec_tools()` both are
    cached over, so the two cannot disagree about which set they are reading.
    """
    return frozenset(name for name, path in ec_tools().items()
                     if paces_reads(path))


def file_mentions(path, rel, tools):
    """Every EC tool named anywhere in a file, plus the file itself if it is one.

    The last half is the tool's own name: a banner inside
    `manual_fan_ctrl_probe.py` saying "the open work that would make these
    tools safe" is an attribution about that probe, whether or not the sentence
    spells out which probe it is.
    """
    named = set(TOOL_NAME.findall("\n".join(read_lines(path))))
    own = os.path.basename(rel)
    if own in tools:
        named.add(own)
    return named & set(tools)


def first_sentence(body):
    """The sentence the attribution is in, trimmed to something quotable."""
    flat = " ".join(line.strip() for line in body.splitlines())
    flat = re.sub(r"\s+", " ", flat).strip()
    m = re.search(r"[^.]*#94\b[^.]*\.", flat)
    return (m.group(0) if m else flat)[:160]


def attribution_disagreement(body, paced, unpaced):
    """The paced tools an attribution in `body` rests on, or None.

    `paced` and `unpaced` are `{tool name: path}` maps as `ec_tools` returns
    them, passed in rather than read so the rule can be held against a pair of
    invented ones. The file walk above adds the anaphoric fallback -- an
    attribution naming no tool resolves against its file -- which is about
    where the sentence is rather than about what it says, and so stays there.

    What decides the rule is those two maps and nothing else: they are already
    the resolved set, block-named tools unioned with the file's. Re-deriving
    the names from `body` here silently discarded the file half, so a runbook
    whose own subject is an unpaced tool was refused the moment any paragraph
    of it also said `ecrw.py` -- a `gpu_block_watch.py` procedure refused for
    work that is still open, three times over. The names are read from the
    maps, deduplicated, and a `sorted` set keeps the message from repeating a
    tool once per mention.
    """
    if not ISSUE_94.search(body) or not OPEN_WORK.search(body):
        return None
    if unpaced:
        return None
    named = sorted(paced)
    return ", ".join(named) if named else None


# --- the run -----------------------------------------------------------

def report(problems):
    if not problems:
        print("no rate claim and no #94 attribution disagrees with the tools.")
        return
    for p in problems:
        print(f"\n{p['file']}:{p['line']}")
        if "computed" in p:
            print(f"  says:     {p['said']}")
            print(f"  computed: {p['computed']}")
        else:
            print(f"  says:     {p['said']}")
            print(f"  names:    {p['named']}")
    print(f"\n{problems and len(problems)} disagreement(s). Restate the sentence"
          "\nfrom the banner the tool now prints; see"
          "\ndocs/findings/ec-read-pacing-fan-page.md.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="fail on any disagreement; the default run prints "
                         "the same sweep and exits 0")
    args = ap.parse_args()

    figures = computed()
    tools = ec_tools()
    problems = []
    for rel in prose_files():
        problems.extend(rate_problems(rel, figures))
        problems.extend(attribution_problems(rel, tools))
    print(f"ec_watch.py defaults to --gap-ms {figures['gap_s'] * 1000:g} over "
          f"{figures['addresses']} addresses: {describe(figures)}.")
    print(f"prop 1: a rate claim about {WATCH} or {DUMP}'s dump has to be one "
          "of those figures. A block carrying a date or an evidence/ path is a"
          "\n        record of a run and is left alone.")
    paced = paced_tools()
    print("prop 2: a #94 attribution has to name a tool that still has no "
          "--gap-ms. Paced:\n        "
          + ", ".join(sorted(n for n in tools if n in paced))
          + "\n        unpaced: "
          + ", ".join(sorted(n for n in tools if n not in paced)))
    report(problems)
    return 1 if (args.check and problems) else 0


if __name__ == "__main__":
    sys.exit(main())