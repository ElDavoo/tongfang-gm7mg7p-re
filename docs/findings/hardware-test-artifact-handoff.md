# Every procedure's "Where the output goes" is now held to its own commands, in both directions (issue #1190)

`CaptureHandoffTests` in
[`windows/tools/test_gpu_block_watch.py`](../../windows/tools/test_gpu_block_watch.py)
holds one document: it fails when §8 names an artifact no run produces, and when
§3 writes a file §8 does not name, with both negatives demonstrated on a scratch
list carrying the old `-marks.txt`. That is a real hold and it is correct. It is
also scoped to the single document whose §3 command spells its output directory
out, and extending it is a design job rather than a copy — for three reasons that
are in the documents and not in the tooling.

**Nothing here is a behavioural claim and no run happened.** The suite reads
markdown files and one directory listing. It opens no capture, runs no probe, and
reaches no machine; a green run says these files agree with each other, not
that any run produced anything.

## The two conventions that did not generalise

**The path convention.** `command_output_paths()` keeps a token only if it
carries a `/` or `\`, which works for the door because its §3 spells
`evidence\ec-watch\` in the `--csv` argument
([`gpu-tgp-07c4-07d7-door.md`](../hardware-tests/gpu-tgp-07c4-07d7-door.md) §3).
**Every other procedure passes a bare filename** —
`ctgp_dben_probe.py --csv <date>-ctgp-dben-07c4-bit3.csv`,
`ec_watch.py --csv <date>-0751-isolation-0700-07ff.csv`,
`manual_fan_ctrl_probe.py --csv <date>-086x-level-block.csv` — while their §6
lists carry the `evidence/ec-watch/` prefix. Copied as-is, the producer set comes
back empty for every sibling and every list entry read as unaccounted-for: a
green-to-red inversion, not a no-op. A new tool would have been another class
in the door's suite, which binds `ecrw_fake` and imports `gpu_block_watch` at
module scope; a repository-wide document check has no business under
`windows/tools/`. So the generalised hold is
[`tools/test_hardware_test_artifacts.py`](../../tools/test_hardware_test_artifacts.py),
and the ~30 lines of heading-boundary parsing the two files share are a
deliberate, stated non-merge — the same duplication argument
`CaptureHandoffTests` already makes for the watch table.

**The hand-saved allowance.** `HUMAN_SAVED_SUFFIXES` is
`frozenset({".pml"})`, correctly tied to the `File ▸ Save As` step in §4a.
Sibling procedures hand-save a **`.txt`**: the sole artifact of
[`ac-autoboot-0726-0765.md`](../hardware-tests/ac-autoboot-0726-0765.md) §7,
assembled by hand from `ecmem.py read`/`write` calls that print to stdout; the
snapshot in [`manual-fan-ctrl-0751-isolation.md`](../hardware-tests/manual-fan-ctrl-0751-isolation.md)
§6; the snapshot in
[`system-id-0456-bit6-divisor.md`](../hardware-tests/system-id-0456-bit6-divisor.md)
§6; and §7's untemplated text file in
[`pd-controller-enumeration.md`](../hardware-tests/pd-controller-enumeration.md).
A blanket `.txt` allowance is unavailable anyway — the door's own negative,
`assertFalse([p for p in self.artifacts if p.endswith(".txt")])`, is what a
blanket allowance would have forced someone to delete.

## The decision: normalise the prefix, not the command

The issue offers two readings and asks for one. **This takes the first: normalise
§6's prefix against a bare command filename.** Both sides are compared on the
basename, with separators normalised, and both are compared *as templates* — the
documents spell `<date>` and `<value>` in the list and in the command alike, so
an entry that is a template is compared to a template and never to a capture.

The alternative — require the directory in the command, as the door procedure
does, and hold every procedure to it — is not free, and the reason is in the
documents as they stood when this was decided (the first bullet below is one of
the four corrections further down, so it no longer describes the tree):

- `level-block-0860-086e.md` §3's service-stopped pass gives **no command at
  all**; it delegates to `manual-fan-ctrl-0751-isolation.md` §3a.
- `remain-capacity-0436.md` §4's Linux arm is
  `sudo linux/battery-trace/remain-capacity-probe <date>-0436-capacity.csv`.
  The probe's own default is `evidence/ec-watch/$(date +%F)-…`
  ([`remain-capacity-probe`](../../linux/battery-trace/remain-capacity-probe)),
  but §4 passes an explicit bare name. Forcing a directory here means editing a
  committed tool's documented invocation, or editing the tool.
- Five further procedures would have their §3 prose rewritten to satisfy a
  convention none of them states.

**What this reading gives up** is that the *directory* half of a §6 entry is
compared at all. It is taken back by a separate, cheap assertion rather than
absorbed: **every listed artifact's directory must exist in the tree**, or be
spelled with the placeholders that make it a template. The door's own strict
`startswith("evidence/ec-watch/")` assertion stays where it is, untouched,
because that document does spell the directory out.

**Out of scope, stated so a reader can disagree:** rewriting the sibling §3
command blocks to carry `evidence\ec-watch\`. If the review prefers the strict
reading, the same suite works with that discriminator swapped and five more §3
blocks edited; nothing in the test design depends on the choice.

## Three refinements the door's helpers did not need

1. **A producer must be in a producer position** — following a flag or a `>`/
   `>>` redirection target. Without it, `level-block-0860-086e.md` §3's
   `### Reading the capture` block (`grade_0751_isolation.py
   <date>-086x-level-block.csv`) stands in as a producer for a file whose real
   producer has been deleted. An unlabelled reference is still held by the
   producer-position rule in the sense that it *cannot* excuse a listing; it is
   not itself a producer, so it is not a second thing to hold in the other
   direction.
2. **A producer token must carry an extension, and not `.py`, `.sh` or `.md`.**
   That drops `ec/tools/ecmem.py` and `ec/tools/grade_0751_isolation.py` — the
   tools, which are inputs — with no rule naming either, and it keeps working
   when §3 grows a `--dump` or a `--marks`. It also drops `--grader <path>`,
   which is a placeholder with no extension. A **letter** is required before the
   dot, or `--interval 0.5` reads as a producer called `0.5`.
3. **Hand-saved is per document, per name, and tied to a named step.** A table
   entry is a basename glob, an anchor section, and a quoted phrase from that
   section, all three asserted present in the source document. A *glob*, not a
   suffix, because `manual-fan-ctrl-0751-isolation.md` §6 lists six dump `.txt`
   files that §3 does produce by redirection, and a per-document `.txt`
   allowance would excuse those six the moment their commands disappeared. The
   door's `.pml` becomes one row of the same table and is not weakened.

## The exclusion rule, stated

A document is held **iff** it carries a `## N. Where the output goes` section
whose first fenced block is a file list. The two that fail it do so for reasons
carried in the suite's `EXCLUDED` table rather than in a comment beside it:

- `pd-controller-enumeration.md` — §7 is prose naming a destination
  (`evidence/pd-controller/`, a directory the tree does not have) and naming no
  file. There is nothing to compare.
- `xdata-06c2-06db-sweep.md` — a report of a run that already happened: §2 is
  "How it was run" and §4 names six captures already committed under
  `evidence/ec-watch/`. No such section.

`doc_section`'s raising on a missing heading stays correct — it fails loudly
instead of passing vacuously — so the two are excluded rather than made to
parse. A test asserts that `HELD` and `EXCLUDED` together **partition**
`docs/hardware-tests/*.md`, so a new procedure cannot silently escape the hold
and an exclusion cannot outlive the heading it was granted for.

## The four corrections, in place

Each is an edit to a procedure's own text rather than a note appended to it; the
retraction of a wrong sentence is recorded here, which is where
`check_no_append_logs.py` expects history to live.

**`ctgp-dben-07c4-bit3.md` — both directions failed at once.** §6 listed
`-ac.csv` and `-gate-closed.csv`; §3's one command wrote
`<date>-ctgp-dben-07c4-bit3.csv`, which is in neither list. §3's own prose
already says the second run goes "to its own CSV", so the fix is the second
command the prose describes, one per run, each with its own `--csv`.

**`manual-fan-ctrl-0751-isolation.md` — a false producer, corrected in place.**
§6 said the snapshot "is in the set because §3's step 0 writes it". §3's step 0
is three `ecrw.py dump` calls redirected to the `-before-` dumps and writes none
of it; the snapshot is hand-written in §2's last bullet, which names the format
to copy. The sentence now names §2. **The artifact itself is real and was never
in question** — only the stated producer was wrong, which is a different defect
from the one #402 found and would not have been caught by listing the file.

**`level-block-0860-086e.md` — prose naming an artifact nothing wrote.** §6
carried one CSV; `<date>-086x-level-block-service-stopped.csv` was named in
prose only, and §3's second pass delegated to the fan-ctrl procedure's §3a
without giving a command. §6 gains the second entry in its fenced list and §3's
delegation gains the `--csv` that pass has to use, so the artifact is produced
by the document that owns it. The grader command in §3's `### Reading the
capture` then grades the new file, **in a second invocation rather than as a
second argument** — and that is the grader's contract rather than a choice about
how many files are convenient. `grade_0751_isolation.py` takes one capture per
watcher (`--help`: "one per watcher ... never the same file twice"; docstring:
"the cross-console checks engage at two or more captures"), and the two files
are two passes of one watcher. Handed both, it grades nothing: run over the
committed three-block fixture and a time-shifted two-block copy of it, every
action reports `in 1 of 2 capture(s): -- did not record it`, all five blocks
print `NOT GRADED`, and the exit code is 1. Run one at a time, the same two
files print `block 1..3 of 3` and `block 1..2 of 2` and grade their own blocks.
**The direction of the error matters: naming only one file is not a defect this
suite can see, and the fix that reads as the minimal one — add the second path to
the existing command — is the one that silently turns a grading run into a
no-op.** §6's stated reason for the split changed with it: it was "so the grader
does not window the two conditions together", which is the one thing two
invocations now make impossible rather than merely avoided.

**`remain-capacity-0436.md` — two claims around a correct file list.** §7
credited append-behaviour to both producers, where the Linux probe opens its
`$OUT` with `>` and truncates and only `ec_validate.py`'s `--csv` appends; and
it said the file "lands under `evidence/ec-watch/` already named" when §3 and §4
both pass a bare relative name. Both sentences corrected in place, and the
second correction has to say which of the two tools does what, because they do
not resolve alike: `ec_validate.py` resolves `--csv` against the directory the
command was started in, and `remain-capacity-probe` `cd`s to the repository root
on the way in, so §4's bare name lands there whatever directory the operator was
standing in. The same sentence's "both probes take the path as their first
argument" went with them: `ec_validate.py` takes it through `--csv`, and leaving
that half standing while correcting the other would have been the same defect in
a smaller window.

*** CORRECTION 2026-10-03 (issue #216), leaving the paragraph above as it was
written.*** **The clause naming `remain-capacity-probe` no longer describes it.**
The probe still `cd`s to the repository root on the way in, but it now resolves
an output name carrying no `/` under `evidence/ec-watch/`, so §4's bare name
lands where §7 lists it rather than at the top of the tree, whatever directory
the operator was standing in. **The `ec_validate.py` half above is unchanged,
and so is the reasoning of the paragraph below it:** §3 still passes a bare
`--csv` name that resolves against the directory the command was started in, so
§3's `rem` block still needs the correction described next, and the three
documents it names are still unexamined against their own tools.

**The bare-name boilerplate, and the three documents left carrying it.** The
correction above fixed one of the two sites in `remain-capacity-0436.md`
carrying that claim, and §3's `rem` block was the other: it still said following
§3 "produces the §7 set with no rename step", which §7 as corrected now denies.
It is corrected here the way §7 was, rather than by putting the directory into
§3's `--csv` — that would make §3's sentence true and §7's false in one edit,
and §7's is the half that had just been checked against both tools' sources.
**The same `rem` boilerplate stands in three more documents, whose §3 commands
also pass bare names: `level-block-0860-086e.md`,
`manual-fan-ctrl-0751-isolation.md` and `system-id-0456-bit6-divisor.md`, at
their §3 `rem` blocks.** None was touched: none was in the scope this change
declared, no correction above reaches them, and their §6 sections have not been
read against their tools' path resolution the way `remain-capacity-0436.md` §7
was. **That is a known remaining instance of a defect this change has already
found elsewhere, not a claim that those three documents are sound** — a §3 not
read against its own §6's directory is unchecked, which is the reading
`CLAUDE.md` asks for where a check has not been run.

## What this hold does not claim

It reads documents and one directory listing. It proves the file list and the
commands agree, in both directions, and that each hand-saved artifact is tied to
a step that is still in the document. It does **not** prove that any run
produced a file: nothing here opens a capture, and a listed artifact's existence
is not checked beyond the spelling of its directory. `evidence/ec-watch/` being a
real directory says the name points somewhere the tree has, and says nothing
about what is or is not in it.

Whether these §6 lists match the captures actually in `evidence/ec-watch/` is a
different question, and it is `ec/tools/check_capture_claims.py`'s — committed
captures against committed prose, rather than a procedure's list against its own
commands. Checking them here would need the captures to exist for runs that have
not happened, which is a `needs-hardware-test` step for a human at the machine
and is not what this suite does.
