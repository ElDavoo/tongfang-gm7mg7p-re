# `PD_MARKER` is a pair of bytes, and every module that reads it decides for itself what a failed comparison means

(2026-10-04, issue #857. Static reading and AST walk over committed sources;
the regression is reproduced over a scratch copy of `ec/firmware/GMxMGxx_11.800`
whose marker bytes were overwritten in memory. No capture opened, no EC, no
hardware, no Windows, no `registers.yaml` row touched.)

`trace_xdata_refs.PD_MARKER` is `(0x20040, b"ITE8850-PD")`. It is two values and
it cannot refuse anything on its own. The comment above it records one of the
several contracts the modules importing it implement — *"a different dump whose
0x20000 region is something else gets labelled `unknown` instead of inheriting
this image's conclusion"* — without saying that it is one contract among them,
and without saying which is which.

This makes that decision recorded rather than inferred. `check_pd_marker_contract.py`
walks `ec/tools/` by AST, finds every statement that reads the marker and
compares it, and files the enclosing guard under one of seven tokens; the
census is committed as `ec/annotations/pd-marker-caller-contracts.csv` and
`--check` reproduces it byte for byte. The one module whose contract was wrong
in a way that reached a published number has been changed.

## The taxonomy is seven-way, and the issue's table has two columns for it

[#857](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/857) put it as
*refuse* or *continue*, with a third shape — a bare `pd_verified()` helper —
noted in passing. Measured, there are seven:

| token | what the failing branch does |
|---|---|
| `refuse` | the run stops: a non-zero `return`, a sentinel the caller turns into one, or a `raise` |
| `note-stderr` | continues, and says why on stderr |
| `note-stdout` | continues, and says why on stdout |
| `silent` | continues, and says nothing |
| `unverified` | the marker's bytes reach the output and nothing here compares them |
| `predicate` | the function returns the boolean; its callers resolve it |
| `assert` | a `--self-test` assertion over the comparison, not a run guard |

Each is read off the enclosing function rather than asked for, and
`MEANING` in the tool carries the same wording in `--report` so the table can be
read on its own. The three that matter for the claim below are `silent` (a
site whose comparison is computed and used, with no branch and no note),
`unverified` (a module that prints the marker's own bytes and never compares
them), and `predicate` — the shape the issue noticed in a single module, and
the one that decides where every decision in the table below actually lives.

## What the census shows, and how to re-derive it

```console
$ python3 ec/tools/check_pd_marker_contract.py
$ python3 ec/tools/check_pd_marker_contract.py --contract silent
$ python3 ec/tools/check_pd_marker_contract.py --csv > ec/annotations/pd-marker-caller-contracts.csv
```

The recorded known-answer run for the two rows the argument below turns on —
one site still noting on stdout, and the one module that names the marker
without comparing it:

```console
$ python3 ec/tools/check_pd_marker_contract.py --contract note-stdout
...
note-stdout -- the run continues, says why on stdout
  check_image_map.py:253 report() [marker imported]

$ python3 ec/tools/check_pd_marker_contract.py --contract unverified
...
unverified -- the marker's bytes reach the output and nothing here compares them
  pd_call_targets.py:872 report_lines() [marker imported]
```

(`check_image_map.py` is the surviving one and it is not the defect this issue
is about: its note says the measurements above it stand on their own, which is
a deliberate statement about what the tool declines to claim. `scan_refs.py`
was the other, and §3 is what it printed.)

The table is the finding and the command above prints it; nothing here restates
its tallies, because a tool landing in `ec/tools/` moves them and a write-up
that has to be edited by the next merge is the thing CLAUDE.md is about. What
is worth saying in words is the *shape* of what is there.

**The committed table carries no line number, and that is deliberate.** It is
keyed on `module` and `function`. A `line` column would be a value that every
merge growing one of the listed modules has to edit to keep a `--check` it never
touched green — and `--check` failing turns this suite red, which turns the
`tests` job red, for a branch with no other interest in the census. The same
applies to the `@NNN` a `caller` cell used to carry, which is why a cell is now
the caller's name and its contract and nothing else. `--report` still prints a
line, because a person reading it wants to be told where to look, and that
output is not committed or diffed. The transcripts above are `--report`
transcripts, which is why they show `:253` and `:872` while the CSV does not.

**Refusals are the common case and they are not all the same refusal.** The
census's `exit` column names how each one ends, and the forms are: `return 1`
for most of them, `pd_dispatch_key.py` and `pd_image_census.py` each
raise their own `Refusal`, `code_pointer_sites.require_pd()` raises
`SystemExit`, `pd_site_clusters.require_pd()` raises `NotPdImage`, and
`check_site_resolution.load_image()` returns a `(None, False)` sentinel that its
`main()` turns into a non-zero exit. A tool reaching the census through one of
those inherits a contract whatever it does with the rest of its output.

**The modules that compute the answer and say nothing are these:**
`a73f_notify_census.scan()`, `addc_dph_sites.main()`,
`pd_pop_order_oracle.print_pd_siblings()` and `r1r2_predecessor.main()`. Each
binds the comparison, passes it to `region_of()` and carries on, so the band
leaves both split columns and nothing tells the reader. They are recorded here
rather than changed: none of them turns a count into a verdict the way
`scan_refs.py` did.

**And one module names the marker without ever comparing it.**
`pd_call_targets.py`'s `report_lines()` writes `marker b'ITE8850-PD' at 0x20040`
into the report it prints, and no statement anywhere in that module compares the
marker to anything. That is the advisory treatment a census is supposed to
surface rather than rule out, and it is the `unverified` row.

**The method, and its limit.** The walk searches one directory,
`ec/tools/`, and inside it every `*.py` except `test_*.py`. A site is reached by
two searches and either can miss: by *name* — `PD_MARKER` appearing in an
assignment, a comparison or a subscript — and by *shape* — the statement that
reads the marker, and the `if` in the same block that tests what it bound. A
module that reads the marker's bytes through a local alias, spells the offset
and the magic as its own constants, or defers the comparison to a helper the
walk does not follow, has **no row**, which is "not found by this method" and
never "there are none". Nothing here is a claim about `bios/tools/` or
`windows/tools/`; a grep for the name over `*.py` in this tree reaches only
`ec/`, which is a fact about where the constant is imported and not about those
two directories:

```console
$ grep -rlE "PD_MARKER" --include='*.py' . | grep -v "/test_" | cut -d/ -f2 | sort -u
ec
```

Two further limits are the walk's, and are recorded rather than worked around:
a note routed into a report buffer rather than a `print` reads as `silent`
here, and a `predicate` caller that passes the boolean straight into another
call is filed `inline`, because that call's own contract is then the one that
governs.

## The regression: `scan_refs.py` found seven sites and then said `ABSENT`

The issue's diagnosis of `scan_refs.py` holds and its severity is understated.
The counts do print — but **the verdict flips**, and it flips to the one word
`docs/findings.md` §4 records having to be retracted twice.

Reproduced over a scratch copy of the committed image with the ten bytes at
`0x20040` overwritten, every site still at its original offset:

| address | committed image | marker overwritten |
|---|---|---|
| `0x0001` (seven sites, all in the PD image) | `referenced in the PD image ONLY, not by the EC` | `ABSENT (see blind-spot caveat above)` |

```console
$ python3 ec/tools/scan_refs.py ec/firmware/GMxMGxx_11.800 0x0001 | tail -1
0x0001  refs=7     ec=0     pd=7     referenced in the PD image ONLY, not by the EC   in_data_region=0   0x0001

$ python3 -c "d=bytearray(open('ec/firmware/GMxMGxx_11.800','rb').read()); " \
      d[0x20040:0x2004A]=b'ITE8850-XX'; open('/tmp/clobbered.bin','wb').write(d)"

$ python3 ec/tools/scan_refs.py /tmp/clobbered.bin 0x0001 | tail -1
0x0001  refs=7     ec=0     pd=0     ABSENT (see blind-spot caveat above)   in_data_region=0   0x0001
```

Both lines are what the tree did **before** the fix this change carries;
`ec/tools/test_pd_marker_contract.py` rebuilds that second image in a
`TemporaryDirectory` and asserts it no longer reaches `ABSENT`.

The mechanism is the census's own `silent` and `note-stdout` shapes in one
module. `scan()` books each site file-wide, so `refs=` is honest at seven.
`region_of()` relabels the band `unknown` the moment the marker fails, so
`ec=` and `pd=` both read 0 and no region claims the site. The verdict branch in
`main()` then has nothing left to work with and falls through to `ABSENT` — on
an address the scan had just found seven sites for. And because the note went
to **stdout** rather than stderr, a reader who redirected the table to a file
would have had the reason interleaved into it.

`ec/tools/test_pd_marker_contract.py` pins this. It builds the clobbered image
in a `TemporaryDirectory`, so nothing here can touch the committed firmware,
and asserts the three things that together close the hole: a non-zero exit,
nothing at all on stdout, and the string `ABSENT` absent from both streams.

## The fix, and why refusing rather than relabelling

`scan_refs.py`'s `main()` now takes the contract its siblings in this directory
already have — the note to stderr, and `return 1` instead of a count. That is
the narrowest correct change, and the reasoning is the same one
`inc_dptr_sites.py` gives at its own guard: the tool's `pd=` column is the
column that reads 0 for every row when the region is unidentified, so continuing
is precisely what forces the `ABSENT` fallthrough. A refusal turns "this image
is not the one these counts were taken from" into the only thing the run can
say, which is what the `return 1` sites in the census already do.

Relabelling the verdicts instead was considered and is wider than it looks. The
machine-readable line is `refs=… ec=… pd=… <verdict>`, and
`.github/scripts/agent-gates.sh`'s `scan_refs.py` smoke test greps `refs=15` and
`referenced` out of it; a fourth verdict would have to be invented, documented,
and taught to every consumer, to fix a condition a refusal already prevents.
The refusal was chosen because it is the contract the family already has, not
because it is the smallest edit.

The committed image is unaffected, and the cheap gate's smoke test is
unchanged — `0x043E` still reports `refs=15` and `referenced` — which the suite
asserts as well, so a refusal too broad to fire only on a broken image fails
here rather than as a bare gate line.

## Two corrections, left visible

**The issue's census does not hold, and its line pins no longer resolve.** It
names twelve modules. The tree has more, reached by the same AST walk. Its line
references are stale — the marker block in `scan_refs.py` and the one in
`xdata_span_survey.py` have both moved down their `main()`s since, and the
comment over `trace_xdata_refs.PD_MARKER` is not where the issue left it.
Nothing here cites a line number for the same reason; the census names
`main()`, `scan()`, `PD_MARKER` and `region_of()` instead.

**The issue's two-way split is a seven-way one**, and the shape it missed in the
middle is the one that decides where the decision lives: `predicate`. A bare
`pd_verified(d)` helper has no decision of its own, so its row carries the
caller's — which is how the *second* `note-stdout` site was found at all.
`intmem_refs.main()` compares nothing near its `print`; it asks
`intmem_refs.pd_verified()`, and the note it prints on a lost marker goes to
**stdout**. That module is not in this change's scope — its loops are bounded
by `len(d)` and its counts are not read as verdicts the way `scan_refs`'s are —
but it is a second site with the defect this issue is about, and the census says
so rather than leaving it to be found a second time.

## Where the `0x2004A` length floor actually comes from

Two write-ups lean on the marker as though it established a length floor for
everybody. It does not, and the correction is in place in both:
[`rel8-displacement-bound.md`](rel8-displacement-bound.md) and
[`descend-index-guard.md`](descend-index-guard.md). What `d[0x20040:0x2004A] ==
b"ITE8850-PD"` establishes is a floor of `0x2004A` bytes **for the module whose
`main()` refuses on it** — that is a property of `audit_call_targets`'s refusal,
and the floor is a statement about its call sites, not about `PD_MARKER` and
not about the other modules in the table above. A `continue`-shaped site
establishes no floor at all: a truncated image is walked as far as the code
walks it.

## Not done here, and named so they are not mistaken for settled

* **The other continuation sites are unchanged.** The ones whose note already
  reaches stderr — `trace_xdata_refs`, `xdata_span_survey`,
  `computed_dptr_sites`, `find_indirect_xdata`, `stride_index_table`,
  `boot_xdata_sites` and `dsdt_ec_fields` — degrade honestly: they say which
  band is unidentified, and their loops are bounded by `len(d)`. Rewriting a
  working sibling is not what this issue asked for. `intmem_refs.main()` is the
  exception, because its note does *not* reach stderr; that one is recorded here
  and in its `caller` cell, and left for a change that can weigh what its counts
  are read as.
* **The `predicate` modules keep their own decisions.** Their callers own
  the refusal, and the census links each row to its caller rather than
  second-guessing it.
* **`check_pd_marker_contract.py` is not in `agent-gates.sh`.** Adding a gate is
  a change to `.github/`, which this repository's pipeline rule keeps out of an
  agent branch. `check_site_resolution.load_image()` already refuses, so a tool
  built on it inherits the contract; the tool is run by hand and by its suite.
* **Nothing here was measured on hardware.** Every claim is reproducible from
  committed bytes by a reader on any machine, which is what the reproducing
  block above is for.
