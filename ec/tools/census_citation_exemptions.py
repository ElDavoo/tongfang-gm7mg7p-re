#!/usr/bin/env python3
"""Enumerate the units an operand/bound exemption would admit, and decide on it.

`check_cluster_citations.py` holds a cluster citation to the membership the
sentence claims. Its any-of fallback is the part under question: where a unit
names two clusters and no preposition pairs an address to one of them, the
address is held to *either*. Issue #605 is the case that fell out of it --
`reset-vector-dptr-targets.md` §26's summary packed a membership claim and a
`setb c` operand into one unit, `0x0800` fired, and the summary was reworded
rather than the rule loosened. Follow-up 5 in that page records the open half:
the fallback has no exemption for an address a sentence introduces as a bound
or operand, and the set such an exemption would newly admit "is not enumerable
from the committed tree". This is that enumeration, and the decision that
follows from it.

**It imports the checker's functions rather than re-walking.** `census()`,
`units()`, `skip_reason()`, `cited_clusters()`, `pairings()`, `name_re()` and
`cluster_of()` are called, not reimplemented. A tool that repeated the walk or
the skip rules would be a *second* census, free to disagree with the rule it is
meant to bound, and a disagreement between the two would be uninterpretable --
either the checker is wrong or this is, and nothing in the output would say
which. Sharing the functions is what makes "the set an exemption would admit" a
statement about the actual rule rather than about a reading of it.

**It reports every membership-checked unit, not only the failing ones.** The
issue asks for the units carrying an address that is not a member of any
cluster the unit names, and on the committed tree that set is empty -- the
checker exits zero. An exemption therefore admits no existing failure, and the
surface worth measuring is *prospective*: how many currently-passing checked
units it would newly silence, so that future drift in them goes unreported. A
census printing only the failing rows would print nothing here and measure the
wrong thing. The failing rows are reported too, and they are empty because the
corpus agrees with its CSVs -- not because the walk found none.

**Two lexicon figures, not one.** The role lexicon (`bound|immediate|operand|
target`) is applied twice per address: within the address's own clause, and
anywhere in the unit. Where both fire the word introduced the address. Where
only the second does, a word was matched in a sentence that only means the
words -- the `charge-target` false positive the checker's own docstring names.
Printing both turns the lexicon's looseness from an assumption into a measured
property, and the gap between them is what the decision turns on.

**`SPAN` is the one role visible without words.** `0xAAAA-0xBBBB` is a single
token (`check_cluster_citations.SPAN`), so an address inside one is a bound or
an operand of a range whatever its prose says. It is classified `range` on the
token alone, ahead of any lexicon word, and that is the only classification here
that does not rest on a word being where it means.

**`admitted` is prospective, and it means the whole unit.** A unit counts as
`admitted` only when **every** address the checker reads in it is introduced as
a bound or operand, because an exemption would then leave it no address to fail
on and any future drift in it silent. A unit where only some addresses qualify
is `partly`: the exemption would silence an address, not the unit, and the
check would keep running. The three verdicts are not gradations of one answer;
the middle one is a different proposal.

**What this measures, and what it does not.** Committed prose, against the
committed `ec/annotations/xdata-clusters.csv` and `xdata-registers.csv`. No EC
image is opened, no register is read, nothing was observed on hardware. And no
classification below is *absent*: the lexicon is word-based, so "no address in
this unit is introduced as a bound" is **not found by this method** -- the same
caveat `ec/annotations/registers.yaml` carries for a static scan. This does not
claim an exemption would be wrong in general. It reports what the enumeration
measured over the prose committed here, and `docs/findings/
operand-bound-exemption-census.md` records the decision that follows.

**The population moved when `units()` learned to split a tight list.** This
module calls `units()`, so the walk fix that write-up describes changes what it
reads: a tight list is several units here where it was one. The decision is
unmoved by it -- the lexicon figure is zero under both walks -- but the
population this tool prints is larger than it was, and a figure quoted from an
earlier run of it is not comparable with a figure from this one.

**Not in `.github/scripts/agent-gates.sh`, and cannot be from an agent branch**
-- the plan stage's push token has no `workflow` scope. It runs by hand, beside
the other censuses in this directory.

Usage:
    python3 ec/tools/census_citation_exemptions.py
    python3 ec/tools/census_citation_exemptions.py --verbose
"""
import argparse
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
sys.path.insert(0, HERE)

# The checker's own functions, called rather than repeated. See the docstring's
# second paragraph: re-deriving any of these here would be the second-census
# defect this module exists to avoid.
from check_cluster_citations import (  # noqa: E402
    ADDRESS, CLAUSE_BREAK, CLUSTER_KEY, ROOTS, SPAN, census, cited_clusters,
    RANK_ONLY, RANK, clean, name_re, pairings, skip_reason,
    transcript_lines, units)

# The role lexicon the issue names: an address introduced as a bound, an
# immediate, an operand or a target. A word-based test, necessarily -- markdown
# marks the role no other way -- which is why it is reported at two scopes and
# why every `unclassified` below reads "not found by this method". `\b` and the
# plural, so `bounds` and `operands` are read; hyphenated spellings come along
# because `\b` treats `-` as a boundary.
ROLE = re.compile(r"\b(bound|immediate|operand|target)s?\b", re.IGNORECASE)

# The roles a census-known address can be introduced in. `range` is structural
# (a `SPAN` token); the other three are a `ROLE` hit inside the address's own
# clause.
RANGE = "range"
UNCLASSIFIED = "unclassified"

# The three verdicts, in the order `report()` prints them and the order the
# decision reads. See the docstring on `admitted`.
ADMITTED = "admitted"
PARTLY = "partly"
NOT_ADMITTED = "not admitted"
VERDICTS = (ADMITTED, PARTLY, NOT_ADMITTED)

# One census-known address as the census reads it. `clusters` is every id the
# unit names, `paired` the one a preposition resolved this address to (None for
# the any-of fallback an exemption would cut across), `role` the classification,
# `in_clause`/`in_unit` the two lexicon figures, and `exempt` whether an
# exemption would silence this address on its own.
Address = collections.namedtuple(
    "Address", "token clusters paired role in_clause in_unit exempt fails")


def clause_of(unit, span):
    """The clause holding one address token.

    The same `CLAUSE_BREAK` the pairing rule splits on, so "the address's own
    clause" is measured against boundaries the checker already uses rather than
    a second notion of clause this module would have to keep in step with it.
    A unit that is one clause yields the whole unit, which is the honest
    reading: there is nothing narrower to scope to.
    """
    lo, hi = 0, len(unit)
    for match in CLAUSE_BREAK.finditer(unit):
        if match.end() <= span[0]:
            lo = max(lo, match.end())
        elif match.start() >= span[1]:
            hi = min(hi, match.start())
            break
    return unit[lo:hi]


def in_span(unit, span):
    """Whether one address token is half of a `SPAN` (`0xAAAA-0xBBBB`).

    A span is one token, so the checker reads it as a range rather than as two
    member claims -- though only inside a census *row* (`census_row()`). Here
    it is the structural signal that the address is an operand of a range
    whatever the prose says, and it is consulted ahead of any word.

    Matched through `check_cluster_citations.clean()` rather than against the
    raw unit, and that is not cosmetic: the corpus writes a range as
    `` `0x030E`-`0x1809` ``, one backtick per address, so `SPAN` finds nothing
    in the raw text and finds the range in the cleaned text. `clean`'s own
    docstring says the backticks go throughout *because* of this, and a
    structural signal that silently matched nothing would read as "no ranges in
    this corpus" -- the absence this file must never claim.

    Offsets are recomputed against the cleaned unit rather than carried over
    from the raw one: `clean()` removes characters, so a raw span is not a
    span in the cleaned string. The two are reconciled by *text* -- the address
    token is looked up where `SPAN` put it -- which is what makes the check
    independent of where the markup sat.
    """
    token = unit[span[0]:span[1]]
    return any(token in match.group(0) for match in SPAN.finditer(clean(unit)))


def classify(unit, span, token, members, ids, paired):
    """One census-known address as an `Address`.

    `range` wins over every word because a `SPAN` is the one role the corpus
    marks structurally. The two lexicon figures are recorded whatever the role,
    so a `range` whose clause also says "bound" shows both rather than hiding
    the word behind the stronger signal -- which is what makes the gap between
    them readable at all.

    `exempt` is this address alone; whether it silences its *unit* is
    `verdict_for()`, because that is a fact about a unit's whole address set.
    """
    in_clause = sorted({m.group(0).lower()
                        for m in ROLE.finditer(clause_of(unit, span))})
    in_unit = sorted({m.group(0).lower() for m in ROLE.finditer(unit)})
    expected = [paired] if paired else ids
    fails = not any(token in members.get(cid, ()) for cid in expected)
    if in_span(unit, span):
        role, exempt = RANGE, True
    elif in_clause:
        role, exempt = in_clause[0].rstrip("s"), True
    else:
        # Not introduced as a bound or operand by any word in its own clause.
        # "Not found by this method", not "is not one": a role marked some
        # other way, or not marked at all, reads the same here.
        role, exempt = UNCLASSIFIED, False
    return Address(token, ids, paired, role, in_clause, in_unit, exempt, fails)


def verdict_for(addresses):
    """The unit's verdict from its addresses', and which signal admits it.

    `admitted` only when every address is exempt -- the unit an exemption
    leaves nothing to check. `partly` when at least one is exempt and at least
    one is not, which is an exemption that narrows the check without silencing
    it.

    **A repeated address votes once.** A unit naming `0x0800` twice is one
    address to the checker, and an exemption that silences it silences both
    mentions, so counting a repeat twice would let a unit read as `partly` for
    no reason a reader could name. An address is exempt if *any* of its
    occurrences is: the mention that matters is the one the writer introduced
    as a bound, and it need not be the first.

    The second half is which signal did the exempting, and it is not a detail.
    A `range` address is exempt because a `SPAN` token made it one, which is
    structural; an address exempt on a word is exempt on a lexicon. They are
    different proposals with different failure modes, and a report that folded
    them into one count would let a decision be taken on the structural figure
    while the prose argued about the lexicon. `range` is reported first when
    both apply, because it is the stronger signal and the one a reader can
    check by looking at the token.
    """
    per_token = collections.OrderedDict()
    for address in addresses:
        per_token.setdefault(address.token, []).append(address)
    exempt = {token: any(a.exempt for a in rows)
              for token, rows in per_token.items()}
    if all(exempt.values()):
        return ADMITTED, signal_for(
            [a for rows in per_token.values() for a in rows if a.exempt])
    if any(exempt.values()):
        return PARTLY, signal_for(
            [a for rows in per_token.values() for a in rows if a.exempt])
    return NOT_ADMITTED, None


def signal_for(addresses):
    """`range` where any exempt address is one, else `lexicon`.

    Which of the two signals the exemption would be resting on here. A `None`
    from an empty list would be a caller bug rather than a reading -- every
    address reaching this function is exempt by construction -- so it answers
    `lexicon`, the weaker of the two, which is the safe direction to be wrong
    in: a report that overstates the lexicon's reach is contradicted by the
    clause column beside it, and one that understates it is not.
    """
    return (RANGE if any(a.role == RANGE for a in addresses)
            else "lexicon")


def census_known(unit, known):
    """[(span, "0xNNNN")] for each census-known address token in a unit.

    `ADDRESS.finditer` rather than `findall` because the role classification is
    positional -- it has to know which clause a token sits in -- and the token
    comes back normalised to the census's spelling so a row's address joins the
    checker's `known` set however the prose spelled it.

    **Every occurrence, including repeats of one address.** The checker holds
    each address once (`check()` sorts a set), so a unit naming `0x0800` twice
    is one address to it and two rows here. That is deliberate: the two
    occurrences can sit in different clauses and only one of them can be the
    bound, so collapsing them to the first would classify the unit by whichever
    mention the writer happened to put first. `report()` counts the distinct
    tokens for its population figure, and `verdict_for()` collapses repeats
    where a verdict needs them collapsed.
    """
    return [(m.span(), "0x" + m.group(1).upper()) for m in ADDRESS.finditer(unit)
            if "0x" + m.group(1).upper() in known]


def markdown_paths(repo):
    """Every `.md` under the checker's `ROOTS`, in the checker's order."""
    paths = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(repo, root)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            paths += [os.path.join(dirpath, f) for f in sorted(filenames)
                      if f.endswith(".md")]
    paths.sort()
    return paths


def cites_a_cluster(text, names):
    """The checker's cheap pre-filter, on its own terms.

    Most of the corpus names no cluster at all, and reading every file twice is
    the difference between a census a human runs and one they do not.
    """
    return ("main-ec-" in text or bool(CLUSTER_KEY.search(text))
            or bool(names and names.search(text)))


def census_of(repo=None, clusters_csv=None, registers_csv=None, ranks=True):
    """(units, skip reasons) over every file the checker would walk.

    Each unit is `(path, lineno, text, ids, (verdict, signal), addresses)`,
    in walk order. The walk is `check_cluster_citations.main()`'s over the same
    `ROOTS`, and every decision inside it is one of that module's functions,
    so this population *is* the checker's population by construction rather
    than by a comparison some later merge could invalidate.

    `repo` is defaulted at call time and not as `repo=REPO`, for
    `census_evidence_citations.census()`'s reason: a def-time default binds at
    import and silently defeats a caller that patches the base, so a suite
    case would read the committed tree while believing it had read its fixture.

    `ranks` is the checker's own switch. It defaults to holding ranks, unlike
    the checker's committed-tree run, because what this measures is the rank
    corpus an exemption would act on; `ranks=False` skips a unit citing any
    cluster by rank as `RANK_ONLY`, the way that run does.
    """
    if repo is None:
        repo = REPO
    members, known, _counts, by_key, by_name = census(clusters_csv, registers_csv)
    names = name_re(by_name)

    found, skipped = [], collections.Counter()
    for path in markdown_paths(repo):
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        if not cites_a_cluster(text, names):
            continue
        transcripts = transcript_lines(text)
        for lineno, unit in units(text):
            ids = cited_clusters(unit, by_key, by_name, names)
            if not ids:
                continue
            known_here = census_known(unit, known)
            if not known_here:
                continue
            reason = skip_reason(lineno, unit, transcripts)
            if not reason and not ranks:
                if RANK.search(unit):
                    reason = RANK_ONLY
            if reason:
                skipped[reason] += 1
                continue
            # The checker's own pairing rule, applied under its own condition:
            # one id named cannot be paired, since there is nothing to choose
            # between.
            pairs = (pairings(unit, [t for _, t in known_here])
                     if ranks and len(ids) > 1 else {})
            addresses = [classify(unit, span, token, members, ids,
                                 pairs.get(token))
                         for span, token in known_here]
            found.append((path, lineno, unit, ids,
                          verdict_for(addresses), addresses))
    return found, skipped


def report(found, skipped, members, repo=None, out=None, verbose=False):
    """Print the enumeration. Every figure here is derived from the tree.

    `out` is resolved at call time rather than bound as `out=sys.stdout`, for
    `census_evidence_citations.report()`'s reason: a def-time default captures
    the stream the module was imported with, so a caller that redirects stdout
    -- which is how a run's transcript is read off a scratch tree -- watches
    the report go past it and reads back an empty string.
    """
    if repo is None:
        repo = REPO
    stream = sys.stdout if out is None else out

    def say(line=""):
        print(line, file=stream)

    by_verdict = collections.Counter(u[4][0] for u in found)
    roles = collections.Counter(a.role for u in found for a in u[5])
    local = [a for u in found for a in u[5] if a.in_clause]
    loose = [a for u in found for a in u[5] if a.in_unit and not a.in_clause]
    failing = [(u, a) for u in found for a in u[5] if a.fails]
    # The admitted units split by which signal exempts them, because that is
    # what decides whether the prose question ("is this address an operand?")
    # and the structural one ("is it half of a range?") have the same answer.
    signals = collections.Counter(u[4][1] for u in found
                                  if u[4][0] == ADMITTED)

    say("census_citation_exemptions.py -- what an operand/bound exemption "
        "would admit")
    say()
    say("population: the checker's own walk, over %s"
        % ", ".join(f"`{r}/`" for r in ROOTS))
    say("  %d membership-checked unit(s) carrying %d census-known address(es), "
        "over %d address\n  token(s); %d of the units name more than one cluster"
        % (len(found), sum(len({a.token for a in u[5]}) for u in found),
           sum(len(u[5]) for u in found),
           sum(1 for u in found if len(u[3]) > 1)))
    say("  passed over under %d reason(s): %s"
        % (len(skipped), ", ".join(
            f"{reason} {count}" for reason, count
            in sorted(skipped.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"))
    say()
    say("what an exemption would admit -- prospective, since nothing fails now")
    for verdict in VERDICTS:
        say("  %-12s %d unit(s)" % (verdict, by_verdict.get(verdict, 0)))
    say("  `admitted` is the only one that silences a unit: every address in "
        "it is introduced\n  as a bound or operand, so an exemption leaves it "
        "nothing to fail on. `partly`\n  silences an address and leaves the "
        "unit checked.")
    say("  of those admitted, by the signal that exempts them: %s"
        % ", ".join(f"{signal} {n}" for signal, n in sorted(signals.items()))
           or "none")
    say("  `range` is a `SPAN` token and needs no words; `lexicon` is a role "
        "word in the\n  address's own clause. They are different exemptions "
        "and the distinction is the\n  decision.")
    say("  every admitted unit, with the token that admits it:")
    for path, lineno, _text, ids, (verdict, signal), addresses in found:
        if verdict != ADMITTED:
            continue
        say("    %s:%d  [%s] %s"
            % (os.path.relpath(path, repo), lineno, signal,
               ", ".join(f"`{a.token}`" for a in addresses)))
    say()
    say("the role lexicon at two scopes")
    say("  %d address(es) carry a role word in their own clause, %d carry one "
        "anywhere in the unit." % (len(local), len(local) + len(loose)))
    say("  The %d in between are the gap: a word matched in a sentence that "
        "only means the\n  words. That is the `charge-target` false positive "
        "the checker records, here as a\n  measured count rather than an "
        "assumption." % len(loose))
    say("  roles over every address read: %s"
        % ", ".join(f"{role} {n}" for role, n in sorted(roles.items())))
    say()
    say("what fails today, with no exemption in force")
    say("  %d address(es) disagree with the census." % len(failing))
    for unit, address in failing:
        say("    %s:%d  `%s` against %s"
            % (os.path.relpath(unit[0], repo), unit[1], address.token,
               ", ".join(f"`{c}`" for c in address.clusters)))

    if verbose:
        say()
        say("every membership-checked unit, and every address it carries")
        for path, lineno, _text, ids, (verdict, signal), addresses in found:
            say("  %s:%d  [%s]  %s"
                % (os.path.relpath(path, repo), lineno,
                   signal and f"{verdict}/{signal}" or verdict,
                   ", ".join(f"`{c}`" for c in ids)))
            for address in addresses:
                say("    %-8s %-12s paired=%-13s clause=%-10s unit=%s"
                    % (address.token, address.role,
                       address.paired or "(any-of)",
                       ",".join(address.in_clause) or "-",
                       ",".join(address.in_unit) or "-"))

    say()
    say("  every negative above is not named by this method, never absent: "
        "the lexicon is word-")
    say("  based, so a role marked some other way reads as `%s`. Nothing was "
        "opened," % UNCLASSIFIED)
    say("  read back or observed -- committed prose against two committed "
        "CSVs.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name every checked unit and every address in it")
    args = ap.parse_args(argv)

    found, skipped = census_of()
    if not found:
        print("census_citation_exemptions.py: no membership-checked unit was "
              "read at all, so the enumeration had no population -- that is a "
              "broken census, not an empty one", file=sys.stderr)
        return 1
    members = census()[0]
    report(found, skipped, members, verbose=args.verbose)
    return 0


if __name__ == "__main__":
    sys.exit(main())