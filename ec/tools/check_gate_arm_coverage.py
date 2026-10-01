#!/usr/bin/env python3
"""Hold `check_ghidra_tooling()`'s tool list and its `case` arms together.

**The gap this fills.** `.github/scripts/agent-gates.sh`'s
`check_ghidra_tooling()` is one `for` loop over a list of tools with a `case`
dispatching each one, and the two halves are related by nothing but a reader
who happens to look. A tool added to the list and given no arm falls to `*)`,
which passes `--work "$scratch"`; for a tool whose argparse has no `--work`
that is not a degraded run but a hard exit 2, and for a tool that accepts it
silently it is a check that is not the one anyone read. Nothing reports either.
The gate script's own header gives the reason the arrangement is worth keeping
— "a deferral nobody can see is a check that gets dropped" — and this is the
same failure one level down, inside a single function.

**Three directions, and the second is what a one-way check gets wrong.**

1. **Listed, so dispatched.** Every tool in the `for` list is matched by some
   `case` pattern, or is named in the `*)` arm's own comment as one of the two
   that take `--work`. This is the direction that would have answered issue
   #318: the tool was in the list with no arm.
2. **Dispatched, so listed.** Every `case` pattern matches at least one listed
   tool. A dead glob is not a no-op — it sends its tool to `*)`, and whether
   that is a red run or a silently wrong one is then decided by the tool's own
   parser rather than by a person. A check that only fails direction 1 passes
   a renamed tool: the arm keeps its old glob, matches nothing, and the tool
   takes the fallback, which is green if the fallback's flags happen to parse.
3. **A claim, checked against reality.** A tool whose docstring says it lives
   in the gate has an arm that runs it. This is the shape of #318 from the
   other end — `xdata_register_map.py`'s docstring has claimed a place in
   `.github/scripts/agent-gates.sh` since it was written, and a claim nothing
   reads is a claim nothing keeps.

**What direction 3 reads, and the boundary that makes it usable.** Most
docstrings in this repository that name the gate are *disavowing* a place in
it — "it is not in `.github/scripts/agent-gates.sh`, and cannot be from an
agent branch" is a sentence several tools open with, and it is true. A
predicate that matched on the path alone would fire on fourteen files and
teach everyone to ignore the check, so the claim is read per *clause*: a
clause naming the gate, carrying a membership phrasing, carrying no negation.
"run under" is deliberately not a membership phrasing —
`pd_image_census.py`'s claim that it runs under the gate's `python3 syntax`
check is true, and it is not a tool-list claim. Only `xdata_register_map.py`
makes the affirmative claim on the committed tree, which is the honest reading:
the rest of the tree either declines membership or does not discuss it.

**What this does not check.** It reads no figure and asserts no count of the
tree — not how many tools the list carries, not how many arms there are. Every
assertion here is *membership*: this tool is dispatched by an arm, this glob
matches a listed tool, this claim has an arm. A census would be a value every
landing edit has to touch, which is the failure `CLAUDE.md` records four times
over; this file is meant to keep passing as `check_ghidra_tooling()` grows,
and a count is the one shape that cannot.

**What a green run is not.** It says the two halves of one function agree with
each other. It does not say any tool's `--check` passes — that is the gate's
own job — and it does not say the list is *complete*, because there is nothing
in the script naming what ought to be in it. That is what direction 3 is for,
and it is a floor: a tool whose docstring claims no place is not on this
checker's list of claims, and adding one that should be is a human's read.

Usage:
    python3 ec/tools/check_gate_arm_coverage.py [--check]
    python3 ec/tools/check_gate_arm_coverage.py --gate PATH
    python3 ec/tools/check_gate_arm_coverage.py --repo PATH --quiet
"""

import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
GATE_REL = os.path.join(".github", "scripts", "agent-gates.sh")
FUNCTION = "check_ghidra_tooling"

# The tool directories the gate list draws from. Direction 3 reads the
# docstrings of tools that live here, so a tool in one of them is one whose
# claim is checked; a tool elsewhere in the tree has no gate claim to read.
TOOL_DIRS = ("ec/tools", "bios/tools", "windows/tools", "tools")

# The `for` list and the `case` body, both anchored inside the function rather
# than anywhere in the file. `agent-gates-deep.sh` is a separate file and
# `.github/scripts/` holds several, and a parse that ran over the whole script
# would pick up a `case` belonging to some other function and report a glob
# dead against a tool list it borrowed from somewhere else.
FOR_LIST = re.compile(r"for tool in ((?:[^\n]*\\\n)*[^\n]*?); do")
CASE_BODY = re.compile(r'case "\$tool" in\n(.*?)\n\s*esac', re.S)
# An arm label: the `pattern)` that opens one, at the case body's own indent.
ARM = re.compile(r"^(\s+)(\S.*?)\)\s*$")

# The gate path as a docstring spells it, tolerating a line break inside the
# backticks -- several docstrings wrap it, and a docstring that names the gate
# across two lines is still naming the gate.
GATE_PATH = re.compile(r"\.github\s*/\s*scripts\s*/\s*agent-gates\.sh")

# Membership phrasings. `live in`, `wired into`, `listed in`, `registered in`,
# `part of` the gate, and the bare `is in the gate`. What is absent on purpose:
# "run under", which is `pd_image_census.py`'s true claim about the gate's
# `python3 syntax` check and not a tool-list claim at all.
MEMBERSHIP = re.compile(
    r"\b(?:live[sd]?|lives|living|wired|listed|registered|part)\b"
    r"(?:\s+\w+){0,3}?\s+\b(?:in|into|of)\b"
    r"|\b(?:is|are)\s+in\s+the\s+gate\b"
    r"|\bin\s+the\s+(?:cheap\s+|deep\s+)?gate\b", re.I)

# A clause carrying any of these is declining, not claiming. "no" and "nor" are
# in because the disavowals in this tree use them; "nothing" and "nobody" are
# in because "no job calls it" is the same statement.
NEGATION = re.compile(
    r"\b(?:not|never|cannot|can't|no|nor|neither|without|nothing|nobody|"
    r"isn't|aren't|doesn't|don't)\b", re.I)

# Clause boundaries. Sentence ends and semicolons, and a comma followed by one
# of the connectives that begin a new claim in this tree's prose — so "it is
# not in `agent-gates.sh`, and cannot be" splits into two clauses and the
# first is judged on its own.
CLAUSE_BREAK = re.compile(r"(?<=[.!?;:])\s+|,\s+(?:and\s+|which\s+|so\s+|but\s+)?")


class Unreadable(Exception):
    """The gate script could not be read as the shape this parses.

    Raised rather than returned, because every way of failing here has the
    same consequence: a checker that cannot find its target must not report
    empty, because empty is what a clean run reports.
    """


def gate_script(repo):
    path = os.path.join(repo, GATE_REL)
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise Unreadable("%s cannot be read: %s" % (GATE_REL, exc.strerror))


def function_body(text):
    """The text of `check_ghidra_tooling()`, braces matched rather than guessed.

    Bash does not nest these functions, but a brace counter is cheaper to
    trust than a regex that assumes the body has no other `{`, and the failure
    it prevents -- reading a `for` list out of the wrong function -- is the one
    that makes this checker confidently wrong.
    """
    start = text.find(FUNCTION + "()")
    if start < 0:
        raise Unreadable("no `%s()` in the gate script" % FUNCTION)
    brace = text.find("{", start)
    if brace < 0:
        raise Unreadable("`%s()` has no opening brace" % FUNCTION)
    depth = 0
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace:index]
    raise Unreadable("`%s()`'s closing brace is missing" % FUNCTION)


def tool_list(body):
    """The tools `for tool in` iterates, in the order the script lists them."""
    match = FOR_LIST.search(body)
    if not match:
        raise Unreadable("`%s()` has no `for tool in` loop" % FUNCTION)
    tools = [word for word in match.group(1).replace("\\\n", " ").split() if word]
    if not tools:
        raise Unreadable("`%s()`'s tool list is empty" % FUNCTION)
    return tools


def arms(body):
    """-> [(patterns, body)] for each `case` arm, `*)` included.

    The label is read at the indent the case body opens at, so a `)` closing a
    subshell deeper in an arm's body is not mistaken for the next arm's
    patterns. `*)` is returned like any other arm and the caller tells it apart
    by its single `*` pattern.
    """
    match = CASE_BODY.search(body)
    if not match:
        raise Unreadable("`%s()` has no `case \"$tool\" in`" % FUNCTION)
    text = match.group(1)
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Comments are skipped before the label test, because a comment in
        # this function ends in `)` often enough to matter -- the census arm's
        # own note cites three `bank1:0x...` addresses in parentheses, and read
        # as a glob it is a dead pattern rather than a sentence. The comment
        # is kept in the body, which is where `fallback_own_tools` reads it.
        if stripped.startswith("#"):
            if out:
                out[-1][1].append(line)
            continue
        label = ARM.match(line)
        if label and len(label.group(1)) == 6:
            out.append((label.group(2).split("|"), []))
        elif out and stripped not in (";;", ""):
            out[-1][1].append(line)
    if not out:
        raise Unreadable("`%s()`'s case has no arms" % FUNCTION)
    return out


def is_fallback(patterns):
    """Whether an arm is the `*)` default rather than a named dispatch."""
    return [p.strip() for p in patterns] == ["*"]


def matches(pattern, tool):
    """Whether a `case` glob matches a tool path, as the shell would read it.

    `fnmatch` rather than a regex translation: the patterns are shell globs, and
    `*gen_xdata_symbols.py` matching `ec/tools/gen_xdata_symbols.py` is the
    whole of what an arm does. `fnmatchcase` rather than `fnmatch` so the
    match does not depend on the runner's filesystem case rules.
    """
    from fnmatch import fnmatchcase
    return fnmatchcase(tool, pattern)


def dispatch(arms_parsed, tools):
    """-> (dispatched, undispatched) over the listed tools.

    `dispatched` is every tool some *named* arm matches. `undispatched` is the
    rest -- every one of them reaches `*)`, which is why the caller cannot ask
    "does this tool reach the fallback" as its test and must ask "is this tool
    one the fallback claims". A `*)` glob matches by definition, so the first
    question has the same answer for every tool in the list and holds nothing.
    """
    dispatched = set()
    for patterns, _ in arms_parsed:
        if is_fallback(patterns):
            continue
        for tool in tools:
            if any(matches(p, tool) for p in patterns):
                dispatched.add(tool)
    return dispatched, [t for t in tools if t not in dispatched]


def fallback_own_tools(fallback_body):
    """The basenames the `*)` arm's own comment claims it handles.

    Read from the arm rather than listed here, because the arm is the
    authority: a tool that starts taking `--work` and is added there belongs in
    this set, and a hand-kept copy of it would be a second answer to the same
    question. The fallback's comment is the sentence that says which two tools
    those are, so the exemption is exactly what the script claims for itself.

    Basenames, because the comment writes `bios_extract.py` where the tool list
    writes `bios/tools/bios_extract.py`. Comparing the two as written would
    exempt nothing and red the committed tree on its own comment.
    """
    named = set()
    for line in fallback_body:
        if not line.strip().startswith("#"):
            continue
        for path in re.findall(r"[\w./-]+\.py\b", line):
            named.add(os.path.basename(path))
    return named


def tool_docstrings(repo):
    """-> {repo-relative path: module docstring} for every tool file."""
    out = {}
    for directory in TOOL_DIRS:
        root = os.path.join(repo, directory)
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, encoding="utf-8") as handle:
                    source = handle.read()
                tree = ast.parse(source)
            except (OSError, SyntaxError) as exc:
                raise Unreadable("%s/%s cannot be parsed: %s"
                                 % (directory, name, exc))
            out["%s/%s" % (directory, name)] = ast.get_docstring(tree) or ""
    return out


def claims(docstring):
    """The clauses of a docstring that put their tool *in* the gate.

    A claim is a clause that names the gate, carries a membership phrasing, and
    carries no negation. The third clause is what makes this usable: most of
    this tree's docstrings name the gate to decline it, and a predicate that
    fired on the path alone would be red on fourteen correct files.
    """
    flat = " ".join(docstring.split())
    if not GATE_PATH.search(flat):
        return []
    out = []
    for clause in CLAUSE_BREAK.split(flat):
        if not GATE_PATH.search(clause):
            continue
        if NEGATION.search(clause):
            continue
        if MEMBERSHIP.search(clause):
            out.append(" ".join(clause.split()))
    return out


def fallback_body(arms_parsed):
    """The `*)` arm's body, which is where the exemption is written down.

    A script with no `*)` arm has no fallback and so nothing to exempt, which
    makes every undispatched tool a finding rather than an error -- but it is
    read as a refusal rather than as a missing list entry, because an absent
    fallback is a shape this does not know how to judge, and guessing at one
    would decide which tools are exempt.
    """
    for patterns, body in arms_parsed:
        if is_fallback(patterns):
            return body
    raise Unreadable("`%s()`'s case has no `*)` arm, so there is no fallback "
                     "to dispatch to" % FUNCTION)


def check(repo, gate=None, quiet=False):
    """The three directions. Returns 0 clean, 1 on a finding, 2 on a refusal."""
    try:
        text = gate_script(repo) if gate is None else open(
            gate, encoding="utf-8").read()
    except (Unreadable, OSError) as exc:
        print("check_gate_arm_coverage: %s" % exc, file=sys.stderr)
        print("  A gate script that cannot be read is not a clean one. This "
              "tool declines rather than reporting nothing found.", file=sys.stderr)
        return 2

    try:
        body = function_body(text)
        tools = tool_list(body)
        parsed = arms(body)
        own = fallback_own_tools(fallback_body(parsed))
        docs = tool_docstrings(repo)
    except Unreadable as exc:
        print("check_gate_arm_coverage: %s" % exc, file=sys.stderr)
        print("  A gate script this cannot parse is not a clean one. This "
              "tool declines rather than reporting nothing found.", file=sys.stderr)
        return 2

    problems = []
    dispatched, undispatched = dispatch(parsed, tools)

    # Direction 1: listed, so dispatched. The exemption is the `*)` arm's own
    # comment naming the tool, not the arm's glob -- see `fallback_own_tools`.
    for tool in undispatched:
        if os.path.basename(tool) in own:
            continue
        problems.append(
            "%s is in check_ghidra_tooling()'s tool list and no `case` arm "
            "dispatches it.\n"
            "    It falls to `*)`, which runs "
            "`python3 \"$tool\" --work \"$scratch\" --check`. A tool whose "
            "argparse has no `--work` exits 2 on that, and one that accepts "
            "it silently runs a mode nobody wrote an arm for. Give it an arm, "
            "or -- if it is meant to take the fallback -- name it in the "
            "`*)` arm's comment, which is where the two that do are named." % tool)

    # Direction 2: dispatched, so listed. A glob matching no listed tool is a
    # dispatch nothing reaches.
    for patterns, _ in parsed:
        if is_fallback(patterns):
            continue
        if not any(matches(p, tool) for p in patterns for tool in tools):
            problems.append(
                "case pattern %s matches no tool in check_ghidra_tooling()'s "
                "list.\n"
                "    It is a dead glob: whatever it was written for has been "
                "renamed or dropped, and in the meantime every tool it meant "
                "to dispatch falls to `*)`. Whether that is a red run or a "
                "silently different one is decided by the tool's own parser "
                "rather than by a person, which is what this arm exists to "
                "prevent." % "|".join(patterns))

    # Direction 3: a claim, checked against reality.
    for rel, docstring in sorted(docs.items()):
        for clause in claims(docstring):
            if rel not in dispatched:
                problems.append(
                    "%s says it lives in the gate and no `case` arm runs it.\n"
                    "    The claim reads: %r\n"
                    "    A docstring's claim is the only place in this "
                    "repository that records why a tool belongs in a gate, "
                    "and one nothing reads is one nothing keeps." % (rel, clause))

    for problem in problems:
        print(problem)
    if problems:
        print("%d gate-arm coverage problem(s) found." % len(problems))
        return 1
    if not quiet:
        print("gate arm coverage: every listed tool is dispatched by an arm, "
              "every arm dispatches a listed tool, and every gate claim a "
              "docstring makes is met by one.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--repo", default=REPO,
                        help="repository root (default: this one)")
    parser.add_argument("--gate", default=None,
                        help="gate script to read (default: %s)" % GATE_REL)
    parser.add_argument("--check", action="store_true",
                        help="accepted for symmetry with the other checkers; "
                             "this tool has no write mode")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the verdict line")
    args = parser.parse_args(argv)
    return check(args.repo, args.gate, args.quiet)


if __name__ == "__main__":
    sys.exit(main())