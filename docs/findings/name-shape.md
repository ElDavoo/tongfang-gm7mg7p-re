# A hand name is a citation wherever its words appear, so it is held to a shape before it is committed (issue #436)

`ec/annotations/xdata-cluster-names.csv` is the one hand-edited surface the
XDATA census adds: `ec/README.md` is explicit that it must not join the
generated list in `agent-conflicts.yml`, and `ec/README.md` also says "Adding
a name is a one-row edit." So the file grows one row at a time, by hand, and
`ec/README.md` is right that it should be easy.

What makes a row worth a check is the other end of the same file.
`check_cluster_citations.py`'s `name_re()` builds `\b(?:name1|name2|...)\b`
from the census's own `cluster_name` values and applies it to **every unit that
also makes a membership claim**. A name is therefore a citation wherever those
words appear, and that checker's own docstring named the failure and declined
to fix it:

> *A name too generic to be distinctive.* Names are matched as whole tokens
> wherever they appear in a unit that also makes a membership claim, so a name
> like `charge-target` would be read as a citation in a sentence that only means
> the words. The ten committed names are all multi-token slugs; this is a limit
> on how a name should be chosen, not a check.

Nothing held the next row to it. This adds the check, in
`ec/tools/cluster_name_shape.py`, and rewrites that bullet in place to say what
is now checked and what is still only advice.

## The four rules

Each returns `(name, what_would_pass)`, and a refusal names its offender and
the shape that would pass — a bare `FAIL` sends whoever chose the name back to
the tool to work out which of the four it was.

| | rule | what it refuses |
|---|---|---|
| R1 | `multi_slug` | anything not `\A[a-z0-9]+(?:-[a-z0-9]+)+\Z`: one token (`gate`), `_`-separated (`charge_target`), a bare address slug |
| R2 | `inside_another_name` | a name that is a substring of another, e.g. `level-block` beside the committed `level-block-086x` |
| R3 | `collides_with_a_known_token` | a name that equals a known address spelling, carries a `0x`-prefixed known address, or equals a known function/symbol name once `-`/`_` are one separator |
| R4 | `prefixes_a_known_identifier` | a name that is a `_`-delimited word prefix of a known identifier |

R1 fixes the separator as well as the count, so a name cannot spell the same
words two ways. R3's containment arm reads the `0x` form only, and that is
forced by the data rather than chosen: four committed names carry a bare
four-hex slug that **is** a real XDATA address — `flag-pair-0442`,
`countdown-06c6`, `countdown-06cd`, `fan-step-08a0` — so "contains no known
address" read on the bare hex is red on four of the nine names the check has to
keep passing. The `0x` form is also the only one `check_cluster_citations.py`'s
own `ADDRESS` regex matches, so it is a boundary that file already draws.

The vocabulary is four committed CSVs — `ec/annotations/ghidra-functions.csv`'s
`name`, `ec/annotations/xdata-clusters.csv`'s `cluster_name`,
`ec/annotations/xdata-registers.csv`'s `name`, and `ec/ghidra/xdata-symbols.csv`'s
`name` — less the census's own `cluster_name` values, because every name is by
construction equal to its own census row and leaving those in makes R3's
equality fire on all nine and mean nothing. `vocabulary()` returns the size it
built; the run prints it only in the summary line a refusal produces, so a
clean run says nothing and a reader who wants the number asks the function.

## Measurement 1: the issue's own example needs a rule the issue does not name

`charge-target` is two `-`-separated slugs, so **R1 passes it**. It is not a
substring of a committed name, so **R2 passes it**. It is not an address, so
**R3 passes it**. A change implementing exactly the three rules the issue spells
out would ship green on the name the issue says to "take seriously rather than
as a hypothetical."

What catches it is R4, and the case for R4 over an equality rule is the shape
of the data rather than a preference: the name is *shorter* than everything the
tree already calls the same thing. Normalised (`-` and `_` as one word
separator) `charge-target` is the word prefix of four identifiers —

- `charge_target_update` and `charge_target_minus_r3_times_0a47`, both in
  `ec/annotations/ghidra-functions.csv`
- `CHARGE_TARGET_MV_0` and `CHARGE_TARGET_MV_1` at `0x0522`/`0x0523` in
  `ec/ghidra/xdata-symbols.csv`

— so equality would pass what a word prefix catches. R4 is green on all nine
committed names. `test_a_word_prefix_of_a_known_identifier_is_refused` asserts
both halves, and asserts that the equality rule still does **not** catch it, so
the day R4 stops being load-bearing the suite says so.

`fan-level` is the issue's second example, and R4 does not catch it either.
§3 below.

## Measurement 2: the rule that would catch `fan-level` is red today, so it is not here

The natural rule for a name that is already being read as a citation is "a name
may not already occur as a whole token in a unit that makes no cluster claim."
It is measured, and it is red on the names the issue asks to keep passing.

**The recipe, so the figures can be re-derived rather than believed:** walk the
same three roots `check_cluster_citations.py` walks (`ec/`, `docs/`,
`evidence/`), split each file into the same units its `units()` makes, keep the
units in which its `MEMBERSHIP` regex does not match, and count the units in
which the name occurs as a whole token. Measured on `main` before this change,
over the `.md` files that walk reads. That corpus is named by the walk rather
than by a figure here, because a count of the tree is a value every landing
write-up has to edit.

**Both columns, and the second one is the argument.** This file is one of the
files that walk reads, and naming a name in prose moves its own row — so the
"with this write-up" column is what the same recipe returns on the tree this
change lands on.

| name | on `main` | with this write-up |
|---|---|---|
| **`charge-target`** | **32** | **37** |
| `mode-oem-init` | 22 | 23 |
| `level-block-086x` | 18 | 20 |
| `counter-sweep` | 15 | 18 |
| `flag-pair-0442` | 4 | 6 |
| `countdown-06c6` | 4 | 6 |
| `fan-step-08a0` | 4 | 6 |
| `ff-fill-stubs` | 4 | 5 |
| `countdown-06cd` | 2 | 4 |
| `user-clear-bytes` | 2 | 3 |

One document, added for an unrelated reason, moved all nine and the file count
beside them. **A gate on this number is a value every write-up has to edit** —
the failure `CLAUDE.md` names, and the reason the check belongs on the shape of
a name rather than on how often the prose happens to repeat it. A check that
goes red because a page was written is a check a page gets edited to make
quiet.

A check on it is not a check on the eleventh row either; it is a check that
fails on nine rows the issue asks to keep. It is left out and recorded here
instead, per CLAUDE.md's calibration rule, so the next reader sees the
measurement rather than rediscovering the omission. Note what the table does
**not** show: that `fan-level` has **zero** such occurrences on `main` — the
occurrences it has on the tree this change lands on are this file's own, by the
argument the nine rows above it are on — and that `charge-target`, the name
that needs refusing, is not three times the median but roughly on top of the
largest committed name. The count barely separates the two cases the rule
exists to tell apart, which is a third and last reason not to gate on it.

So `fan-level` is refused by nothing here, and a green run is not a claim that
it would be. Both `cluster_name_shape.py`'s docstring and
`test_and_fan_level_is_still_refused_by_nothing` say so in those words; the
test is there so the stated limit is a fact somebody checks rather than a
sentence that rots, and it goes **red on an improvement** — if a rule ever
starts reading the corpus, the response is to record the new reach, not to
weaken the rule that caught it.

## Measurement 3: the same hazard, at its smallest

`counter-sweep` is committed, and it is a substring of the committed file stem
`docs/findings/counter-sweep-entry-set.md`. That stem occurs **five times**
outside this file — `docs/findings/INDEX.md`, `docs/findings.md`, and three in
`ec/annotations/xdata-06c2-06db-timers.md` — and this paragraph is a sixth, so
the figure is a floor rather than a total. `name_re()` reads every one of them
as a name-form citation of the `counter-sweep` cluster.

They are caught by nothing today only because the membership cue happens to be
absent from each of those units — a word away from each one, and the checker
would read a cluster citation out of a file link. No rule here fires on it: the
stem is not a name, and `counter-sweep` is committed, so R2's subject is not a
name at all and R1–R4 never see it. Enforcing the file-stem collision would
fail on a committed name, so it is reported here rather than checked. It is
worth a reader seeing in miniature, because it is the same hazard the issue
describes with a larger number in it.

## The check fired on this change

Worth recording, because it is the smallest possible instance of the hazard and
it happened to this change rather than to a hypothetical eleventh row.

`gen_findings_index.py` renders one line per write-up, and the whole list is
one paragraph as far as `check_cluster_citations.py` is concerned. This file
was first named `cluster-name-shape.md`, and the word inside that file name is
exactly the cue that checker's `MEMBERSHIP` regex looks for. So one new index
line made its list count as a membership claim — and the same list carries an
XDATA address belonging to a `0751-*` write-up, and an entry for the
counter-sweep write-up, whose stem `name_re()` resolves to a real cluster. The
checker reported an address in a list of file links as a membership claim about
a cluster the list never names.

Nothing was wrong with either file, and nothing was repaired. The finding was
correct under the rule as written, and the fix was to name this file
`name-shape.md` and regenerate the index. That is the four rules' argument in
reverse and it is worth seeing land: the cost of a name — or of a name-shaped
thing a name gets matched inside — is charged to the file that carries it, and
to nobody else.

## Where the check runs

`xdata_register_map.py --self-test`, next to the existing
`every key in ... names a cluster of the committed census` check, so the label
sits with the other names-file refusal and `agent-gates.sh` picks it up without
a gate edit — that gate already runs `--check && --self-test` for this tool.
The rules live in the sibling module rather than in that 5,000-line file
because its line numbers are pinned by `check_eq_guard_citations.py`, and every
line added to it is a line that checker has to re-resolve. The whole of the
shared-file edit is an import beside `import export_ownership` — which already
puts `TOOL_DIR` on `sys.path` for exactly this — and one `check(...)` call.

## What this does not claim

"Not found by this method" is the category, the same one
`ec/annotations/registers.yaml` uses for a static scan.

- **It cannot see the corpus.** All four rules read the names file and four
  CSVs. Nothing here reads `ec/`, `docs/` or `evidence/`, so a name that is
  *already* being read as a citation in prose is invisible to it — which is
  the whole of measurement 2, and why `fan-level` survives.
- **It cannot see a symbol the census does not carry.** A collision with a
  Windows-side class, a BIOS symbol or a plain English word is outside all four
  CSVs.
- **It does not say whether a name is a good name.** Nothing here reads the
  `note` column's evidence or asks whether the name describes the membership it
  is attached to; that is `TheNamesFile`'s `note` case and a reader's judgement.
- **Nothing here is about the firmware.** Every input is a committed CSV. No
  image is opened, no register is read back, and no laptop, EC or Windows
  machine is involved.

## The count

The issue says "the ten committed names" and "the eleventh row." There are
**nine**: nine rows in `xdata-cluster-names.csv` and nine named rows in
`xdata-clusters.csv`. The tenth, `page-0300`, was dropped when its nine-address
cluster was absorbed. The drift is recorded as deliberately unfixed in
[`xdata-4-4-identity-rederivation.md`](xdata-4-4-identity-rederivation.md):460
(`ec/README.md:400`'s "Ten of the 427 clusters have one"; the names file holds
nine of 439) and in
[`xdata-no-eq-guard-census-scale-join.md`](xdata-no-eq-guard-census-scale-join.md):300
(`check_cluster_citations.py`'s "the ten committed names"). That first sibling
pins the same `ec/README.md` sentence to a stale line, left as it is rather than
corrected here, so re-deriving it is what finds it: this `:400` was read off the
file rather than copied from the citation it corrects.

One of the two stops being true here, and it is worth saying which and why.
`check_cluster_citations.py`'s bullet was the one sentence carrying the numeral
that this change had to edit in any case, so the numeral is **dropped rather
than corrected** — the check is cited in its place, and a check's output is not
a hand-kept number. `ec/README.md` keeps its "ten" and gets no edit: it is a
shared file, the sentence is about the census rather than about names, and
nothing here makes it less true. No file gains a count of names, because a
count of names is a value every merge has to edit and the claim to make is
that each committed name passes.
