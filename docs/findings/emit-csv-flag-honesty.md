# `--emit-csv` refused the three modes it knew about, and honoured nothing on the fourth

The write-up for [issue
#415](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/415), which asks
that `verify_reassembly.py`'s `--emit-csv` guard cover `--verify-provenance` as
well as the modes it already covered, and that a `--limit` run either refuse
`--emit-csv` or say in the emitted file that it is partial.

**Offline throughout.** No laptop, no Windows box, no EC register, no assembler
beyond the `sdas8051` already on this runner, and no git history beyond this
checkout. Every behaviour below was measured by running the tool against its own
committed inputs, over committed listings and the committed report. Nothing here
should be read as a hardware or firmware observation, because there is none.

## The two holes, on the tree this change starts from

Both were reproduced by running the parent revision of the tool, copied into
this tree so its paths resolve, with `sdas8051` present.

**`--verify-provenance` was never consulted.** `main()` returns from it before
`--emit-csv` is read at all, so `--emit-csv /tmp/p.csv --verify-provenance
--base no-such-revision-a --migration no-such-revision-b` printed the
provenance mode's own history failure and exited **1**:

```
  FAIL cannot resolve the base revision 'no-such-revision-a' in this clone.
  This mode answers from the repository's history, so it needs a full
  clone: ...
```

Nothing was written, nothing named `--emit-csv`, and the status a reader was
handed was provenance's. A reader seeing that would go and unshallow their
clone, which is not what was wrong. The same shape reaches the emit path with
*resolvable* revisions, and then the run audits the migration, exits 0, and has
never mentioned the flag.

**`--limit` produced a file shaped like the report.** `main()` threads `--limit`
into `verify()`, `emit_csv()` writes the result through `write_report()`, and
`write_report()` takes no row count and records none. `--emit-csv /tmp/l.csv
--limit 40` exited **0** and wrote `/tmp/l.csv`: byte-for-byte the committed
report's header, then 40 rows every one of which the committed report also
holds, with nothing in the file to say so. The one artefact `--emit-csv` exists
to produce is the one a reader is most likely to diff against
`ec/ghidra/reassembly.csv`, and that diff would read as every absent row being
a disagreement rather than as the limit.

That the comparison would be meaningless is not a matter of opinion.
`docs/findings.md` §14g, *"The nightly re-encode says which assembler answered
and what moved"*, already says that a `--limit` run prints the committed tally as
a labelled reference and compares nothing, because forty rows are not a
disagreement with the whole report. §14g protects the *console*. Nothing
protected the *file*.

Both are the same defect: a flag whose whole purpose is that two runs can be
compared, reaching a run that does not produce a comparable thing, and the run
saying nothing about it. The existing guard's own comment named the failure mode
it was written for — "Saying so beats exiting 0 having written nothing, which is
the whole failure mode the flag exists to avoid" — and reached it by a path one
flag over.

## Why refusal, and why not a marker

The issue offers both for `--limit`, and this takes the refusal and declines the
marker. Not a preference: two committed tools already hold the alternative out.

- `tools/check_deep_schedule_emit.py` asserts that the header `emit_csv()`
  writes is **byte-identical** to the first line of `ec/ghidra/reassembly.csv`,
  and it asserts it by calling the tool's own function.
- `ec/tools/test_reassembly_checked_bound.py`'s
  `test_the_committed_header_is_the_one_write_report_writes` holds the same
  thing from the other side, again by calling `V.emit_csv()`.

Both get that header by calling `write_report()`, whose column set is the
committed report's byte for byte — deliberately, as its own comment says,
because a column on one side only is how the `(program, addr)` join the nightly
artifact exists for stops working. A `limit` column, or a `# partial` line ahead
of the header, breaks both holds.

A refusal writes nothing at all, and nothing cannot be mistaken for a report.
It is also what the tool's consumer already does: `tools/check_deep_schedule_emit.py`
refuses an emit step that passes `--limit`, and the comment in
`docs/ci/agent-gates-deep-schedule.yml` says in its own words that passing no
`--limit` "is a requirement rather than an omission". This change makes the tool
enforce at the argument layer what the workflow checker already enforces at the
wiring layer — the wiring checker can only refuse a YAML file, and a person
typing the command by hand is not a YAML file.

## The shape of the fix

The modes that answer without re-encoding are now a tuple, `NO_RE_ENCODE`, and
`refuses_emit_csv()` asks it. `main()`'s existing guard calls that predicate at
the position it already occupied — before `--self-test`, before
`--verify-provenance`, before the committed report's own check — and returns 2,
as it did. So the second refusal costs the same millisecond the first did, rather
than the re-encode behind it, which is the property the committed-report check's
comment claims for itself and the one `--limit` needs most: it is the expensive
one to discover late.

The refusal lives in `main()`, not in `emit_csv()` or `write_report()`. Both of
those have three-argument signatures frozen by callers outside this tool — the
two header holds above both call `V.emit_csv([], "no-such-assembler", <path>)` as
a probe that needs no assembler — so a check inside them would have changed a
signature three other files depend on to guard something none of them can reach.

`NO_RE_ENCODE` carries each mode's own remedy sentence, because they are not the
same sentence. The other modes can be answered with `--work <dir>`, which is
the plain verify path; `--verify-provenance` cannot, because it reads git
history and re-encodes nothing. Offering `--work` to that mode would have named
a flag that does nothing for it, which is the same class of mistake as the
original bug.

When more than one of them is given, the predicate names the first it finds —
`--limit` before any mode — and the reader drops them one invocation at a time.
That is one sentence rather than a list of every offending flag, and it is
enough because each refusal says which flag it is about.

## What the self-test proves, and what it does not

The assertions live in `--self-test`, beside the argument handling they are
about, because `agent-gates.sh` already runs it with no assembler, no network and
no git. Three things per refused combination, driven through `main()` rather
than through the predicate, because `main()` is where the decision is made:

- the status is 2 — which the run could also reach by finding no assembler, so
  the printed sentence is what says which refusal answered;
- **the destination does not exist afterwards**, in a fresh `tempfile` directory
  per case, so the guard is *observed* to stop the write rather than believed
  to. A test for "the guard stops the write" that performs the write is worse
  than no test;
- and the sentence names the offending flag, so a guard that fires for some
  other reason — or silently — is not what passes.

The control sits with them: a namespace carrying only `--emit-csv` must return
`None` from the predicate and reach the write, so a guard that refuses
everything cannot pass.

The hold that keeps this from being the bug again is a set equality between
`NO_RE_ENCODE`'s dests and the `if args.<dest>` branches in `main()`'s own
source before `refuses_committed_report(args.emit_csv)`, both directions, read
with the `re` this tool already imports. It matches on the token rather than a
line number, so a rewrap does not redden it, and it is anchored on the `if` so
a validation clause that merely mentions a flag is not counted as a mode.
Without it the fix would be the same shape as the defect it fixes: a hand-kept
list a next mode is added beside.

### What each mutation showed

One scratch copy of the tool per mutation below, `--self-test` run against each.
This is the red-before evidence, and the mutations are the checks' real value
rather than a table of pass marks:

| mutation | what went red |
|---|---|
| the guard put back to the parent revision's three-flag condition | exactly two cases, and only the new ones: `--verify-provenance` (status 1, named the flag: no) and `--limit` (status 0, **wrote the file**: yes) |
| a mode added to `main()`'s dispatch but not to `NO_RE_ENCODE` | the completeness hold |
| an entry removed from `NO_RE_ENCODE` that `main()` does dispatch on | the completeness hold, and the `--verify-provenance` refusal |
| the predicate returning a refusal unconditionally | the control, the `--limit 0` case, and every refusal's "named it" check |

The first row is the one the issue is about, and it is worth reading closely:
under the parent revision's guard the `--limit` case performed the 40-row
re-encode and wrote the file *inside the self-test*, which is precisely the
behaviour the assertion exists to catch.

The hold has one stated limit, in its own comment: a dispatch branch written
`if not args.check and args.report:` is not counted, because it leads with a
negation rather than with `args.`. That is a conjunction of a listed mode with
something else rather than a mode of its own, so nothing is lost; a branch
written that way and needing to be listed wants rewriting instead.

## What this leaves open

**`--report --limit` is the adjacent hazard, and it is worse.** This change
refuses `--emit-csv --limit`; it does not touch `--report --limit`, and that
combination has the same property with more force behind it. Reading `main()`:
`--report` calls `write_report(results, sdas, version=version)` with the default
`path=REPORT`, and `results` came from `verify(limit=args.limit)`. So a
`--limit` run with `--report` opens the committed report for writing and puts a
truncated set of rows where the whole thing was — the same "indistinguishable
from a full report" property, except that here it destroys the file rather than
writing beside it. `refuses_committed_report()` does not help: it is checked
against `--emit-csv`'s destination, and `--report` names no destination to check.

**That was read, not measured.** Running it would truncate the committed
report, which is the one thing a finding like this must not do to the tree it is
describing, so the claim above is from the code path and nothing else. Deciding
what `--report --limit` should do — refuse, or a `--report` that refuses to run
over a report that already exists — is a separate decision and is not taken
here. It is the follow-up this finding opens.

Two smaller things, reported and not acted on:

- The `--limit` refusal names the flag and says the file would be
  indistinguishable from a full one, but it does not say how many rows the run
  would have covered. The run does not get that far, and the number belongs to
  the report rather than to an argument parser.
- `docs/ci/agent-gates-deep-schedule.yml`'s "no `--limit`" comment is left
  alone. Nothing runs that file, it is shared, and the invariant it states in
  prose is now enforced a tier earlier in code.

## One pre-existing condition, reported and not fixed

`verify_reassembly.py`'s comments still say the committed report has 2,705 rows
in several places. It does not: the committed
`ec/ghidra/reassembly.csv` holds 2,717 data rows today, which the tool's own
`--limit` output prints as "40 of the committed report's 2717 rows". The
comments are describing a report that has since been re-run, which is the normal
consequence of `--report` and not a defect in anything.

It is left alone deliberately. The number appears in comments spread through one
file several other changes may be open against, it is a *census* rather than a
claim about behaviour, and CLAUDE.md's own rule says a value every merge has to
edit is a value that should not be in a document at all. This change wrote one
new comment in that file and left the number out of it.

## How to re-check this

```console
python3 ec/tools/verify_reassembly.py --self-test
python3 ec/tools/verify_reassembly.py --emit-csv /tmp/x.csv --limit 40 ; echo $?
python3 ec/tools/verify_reassembly.py --emit-csv /tmp/x.csv --check ; echo $?
python3 -m unittest ec.tools.test_reassembly_checked_bound
python3 tools/check_deep_schedule_emit.py --check
bash tools/run-tests.sh
```

**The evidence is the mutation table above, not a pass count.** The refusals are
made before `verify()` is called, which is where the decision is made; spending
a full re-encode to confirm a return value decided one function earlier is not
evidence. The self-test says as much in its own output.