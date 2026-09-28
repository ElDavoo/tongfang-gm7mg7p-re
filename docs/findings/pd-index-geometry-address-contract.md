# The three address flags on `pd_index_geometry.py` have one contract, and this is the change that made it legible from `--help` rather than from a findings file

(2026-09-28, issue #860. Static reading and commands over one committed image.
No capture opened, no EC, no hardware, no Windows.)

`pd_index_geometry.py` takes a bare address on three flags — `--helpers`,
`--sites` and `--callers` — and the issue behind this file reported three
different contracts behind one `metavar="ADDR"`. **The important finding is that
the three contracts are the same one at this tree**, and the reason is that the
work the issue asks for had already landed. Re-measuring the issue's own table
puts every row it reported as broken on `pd_index_geometry.py: error:` and
exit 2, with `--helpers 0xFFE8` and `--helpers 0xFFE9` still exiting 0 — the
deferral recorded in the table below.

So this is not a re-implementation. What was genuinely left is three things, and
each is measured below rather than asserted: the contract was still only in
prose and not in the `--help` strings, so nothing distinguished the flags to a
reader at the point they would look; `--helpers` wrote a line to stdout *before*
it refused, which the other two do not; and `--callers` had no assertion of its
own anywhere, despite being the mode whose check it inherits most indirectly.

## What the issue's table said, and what this tree does

The left column is the issue's own table, as filed. The right column was
re-measured at `49158e83`, this branch's first parent, before this change was
made — the same commit the reproduction block below diffs against. The left
column is already stale for six of its nine rows, which is itself the finding:
the issue was accurate when written and the tool moved under it.

| command | as filed in #860 | re-measured at `49158e83` |
|---|---|---|
| `--sites zzz` | exit 2, `invalid literal for int() with base 16: 'zzz'` | **unchanged** |
| `--helpers zzz` | exit 1, unhandled `ValueError` traceback | **exit 2**, same message |
| `--callers zzz` | exit 1, unhandled `ValueError` traceback | **exit 2**, same message |
| `--sites 0x1FFFF` | exit 2, `check_site_addr()` names the region and both ranges | **unchanged** |
| `--callers 0x1FFFF` | **exit 0**, prints a byte-scan caller list | **exit 2**, same message |
| `--sites 0x23478` | exit 2, plus the `file_offset` second line | **unchanged** |
| `--callers 0x23478` | exit 1, `IndexError` traceback | **exit 2**, same message |
| `--helpers 0x1FFFF` | exit 1, `IndexError` traceback | **exit 2**, same message |
| `--callers 0x1FFE9` | exit 0 | **exit 2** |
| `--helpers 0xFFE8` | exit 0 | **unchanged**, still exit 0 |
| `--helpers 0xFFE9` | exit 0 | **unchanged**, still exit 0 |

All three now print the same diagnostic for the same argument, and none of them
distinguishes itself in the message. `check_site_addr()`'s docstring already
named all three modes, and that is the right shape for it: a message that named
its caller would have been a second contract to keep in step.

### One check, three routes to it

Nothing calls `check_site_addr()` three times, and that is worth writing down
because the third route is the one a future edit can quietly remove:

- `--sites` reaches it through `site_rows()`, which checks the whole run
  (`:728-729`) before returning a row.
- `--helpers` reaches it through `print_helpers()`'s own loop (`:1057`).
- `--callers` **has no call of its own**. `caller_rows()` reaches it through
  the `site_rows(d, [site])` it already makes to decode each site's index
  registers (`:983`).

A non-hex argument is a separate path and lands the same way: `main()` wraps
each of the three `int(a, 16)` conversions in its own `try`/`except ValueError`
→ `ap.error` (`:2463`, `:2472`, `:2479`).

## The one that was not: `--helpers` printed before it refused

The three modes had one contract and one of them leaked. `--helpers 0x1FFFF`
exited 2 as it should, and left **50 bytes on stdout** before it did:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0x1FFFF >/tmp/h.txt
$ echo $?; wc -c </tmp/h.txt
2
50
```

Those 50 bytes are the `1 helper entry/entries named on the command line` count
line and its blank line. `--sites` and `--callers` left **0 bytes**, because
`site_rows()` checks over the whole run before returning a row and
`print_callers()` therefore raises before it prints anything. One contract, and
the third mode wrote a partial result into a redirect first — which is the
failure mode a redirect is the usual way of *not* noticing.

The fix is to move the existing check loop above the existing print, which is
what the comment already sitting there asks for ("Over the whole run first, as
`site_rows()` does"). The code was reordered to match its own stated intent
rather than to a new rule, and after it every one of the nine combinations in
the table above leaves stdout at 0 bytes.

**Nothing on the legal range moved.** The pre-change file was extracted from
`49158e83` — this branch's first parent, the commit that carries the pre-change
`pd_index_geometry.py` and is named by hash rather than by a moving ref so the
recipe still works after this one lands — and both copies run over the same
image; `--helpers`, `--helpers` with addresses, `--bases all`, `--strides all`,
`--callers 0x0860`, `--accesses` and `--helpers-csv` are byte-identical, and
the eight-command diff is in "Reproducing it" below. The multi-entry
command-line branch was compared too, since that is the branch that moved:
`--helpers 0x0860` and `--helpers 0x0860 0x0C2E` are byte-identical,
`--helpers 0x1FFE9 0x0860` differs by the two lost stdout lines and **nothing
else** — stderr is byte-identical and the exit is still 2.

## Item 3: the anchor is checked, the image's own targets are not

The issue asked for a decision on whether `--helpers`' caller's anchor gets the
range check, and to record it at the flag and in `main()`. The anchor is
checked. What is deliberately still not checked is the targets `chain_from()`
decodes out of the image's own branch operands and hands to `walk_helper()` at
`:645`, which is a different contract from a user-typed anchor: those are not
the caller's assertion, they are what the bytes say.

**That deferral is intact and is #843's ground.** `--helpers 0xFFE9` still
exits 0, and still reports the walk leaving the region rather than raising:

```console
$ python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0xFFE9
1 helper entry/entries named on the command line

0xFFE9  (file 0x2FFE9)  unmodelled: walk left the pd-image at runtime 0x10000, its end at file 0x30000
    0xffe9  ff       mov  r7,a
    ...
```

23 listing lines, and they are the `0xFF` fill at the region's **top**, not
past its end. `pd_bounds()` puts the region at file `0x20000-0x2FFFF`, runtime
`0xFFE9` is file `0x2FFE9`, so the listing runs `0x2FFE9`-`0x2FFFF` — the last
23 bytes *inside* the region, which are the same fill the erased area beyond it
holds. The walk stops **at** the region end rather than crossing it, and that
is what the run's own note says: runtime `0x10000` is file `0x30000`, the first
byte beyond the region, and it is not listed. (`0xFFE8` is the address that
lists 24, one more byte of the same fill, and the one the self-test's comment
at `../../ec/tools/pd_index_geometry.py:2171` counts.)

**#843 was closed by the `count-bounded-walk-invariant.md` work this same
paragraph credits; this change touches no walker, so it neither reopens #843
nor pre-empts what is left of it.** What the deferral now rests on is worth
stating because it is not the reason the issue gave: the walker itself no
longer discards `pd_bounds()`'s `hi`. `walk_helper()` takes both ends and
clamps `hi = min(hi, len(d))`, so the region end bounds the walk — that is
`count-bounded-walk-invariant.md`, which is what the self-test's own comment
points at.

**The issue's "the only two" premise is stale in the same way, and correcting
it is a retraction rather than an addition.**
[`pd-sites-address-range.md`](pd-sites-address-range.md) measured `grep -n 'lo,
_ = pd_bounds()'` at twelve sites and corrected #843 with it. Re-run at this
tree that grep returns **fourteen**, and the two functions #843 names are no
longer among them for the reason just given. That file's count and table are
corrected in place, its old figures left visible, and the narrower total is
left unrestated there because its definition is #843's and its two entries have
left the set. A branch cannot edit #843 itself, so this is where the correction
lands, as the file already explains it does.

## `--callers` had no assertion, and that was the real gap

`--sites` and `--helpers` each had a loop in `self_test()` pinning that the mode
refuses an out-of-region address. `--callers` had none — and it is the mode
whose refusal depends on the *least* local code. An edit to `caller_rows()`
that stopped calling `site_rows()` would drop `--callers`'s refusal silently:
the check would simply stop running, nothing would raise, and the mode would go
back to answering questions about addresses that are not PD runtime addresses.

The new loop pins the claim, and it is load-bearing rather than decorative —
replacing `caller_rows()`'s `site_rows()` call with a literal in a scratch copy
turns it red with `<no refusal>`, which is the whole failure it exists to catch:

```console
  !   --callers 0x1FFFF is refused naming pd-image and both ranges (got '<no refusal>')
```

It is `print_callers()` that the assertion calls rather than `caller_rows()`,
because the contract in question is the flag's, and stdout is suppressed so
that the mutation's failure mode — printing a caller list where the diagnostic
belongs — cannot corrupt the self-test's own output.

## What this does not establish

- **No live test ran.** No EC was opened, no register read back, no capture
  taken, no hardware and no Windows involved. Every number here is a static read
  of a committed file or the output of a command over one.
- **"Exits 0 is a statement about these commands on this image"**, not a
  property of the code. The byte-identical diffs are what make the regression
  claim; on their own they would be a formality.
- **The check tests the argument, not the image.** `0 <= addr < hi - lo` is a
  property of the interface — a runtime address is 16 bits on this target — and
  holds for any dump. `pd-sites-address-range.md` argues why that is a different
  kind of guard from the reachability one the census declined; that argument is
  not restated here, only inherited.
- **The instruction-boundary precondition is untouched.** A caller naming a
  mid-instruction address still gets a visibly wrong listing rather than a
  refusal, because nothing in an image says where a routine's instructions
  begin. No check was added there and none should be.
- **The self-test pins that the message keeps naming what a reader needs** —
  the region and both ranges — not that the wording is the best wording. It
  deliberately does not pin the stdout ordering that this change fixed; that is
  a one-line diff with a measurement behind it, and a test for it would pin the
  shape of a function rather than a claim.
- **No suite was added.** The tool's `--self-test` is its established idiom, and
  a committed `test_*.py` would need a row in `../../tools/README.md`'s table
  and corrected totals in two long shared files, for a change whose regression
  surface is the assertion loop above. The runner's tally is unchanged.
- **`registers.yaml` is not involved.** Nothing here is about a register; this
  is Python walking a `bytes` object.

## Reproducing it

From the repository root. The first block is the contract — nine refusals, and
all nine now leave stdout empty.

```sh
T="python3 ec/tools/pd_index_geometry.py ec/firmware/GMxMGxx_11.800"

# the shared contract: a non-hex argument and an out-of-region address, refused
# the same way by all three, with nothing on stdout before the refusal
for m in sites helpers callers; do
  for a in zzz 0x1FFFF 0x23478; do
    $T --$m $a >/tmp/out.txt 2>/tmp/err.txt
    echo "--$m $a -> exit $?, $(wc -c </tmp/out.txt) bytes on stdout"
  done
done

# the file_offset-versus-runtime second line, on the wrong column
$T --callers 0x23478        # 0x23478 is ../annotations/ec-0x07d0-sites.csv's
                            # first file_offset; its runtime column reads 0x3478

# item 3's deferral, intact: exit 0, 23 fill lines, the region-exit note
$T --helpers 0xFFE9

# the tool's own suite, which now pins --callers too
$T --self-test

# the legal range, byte-for-byte against the pre-change file. 49158e83 is this
# branch's first parent and the last commit before this change; a hash rather
# than a ref because HEAD is this file once the change lands. The extracted
# copy keeps the real basename, since argparse's prog is the file's name and
# the stderr comparison below depends on it, and imports its siblings by module
# name, so PYTHONPATH is what makes it runnable outside ec/tools.
mkdir -p /tmp/pd-pre && git show 49158e83:ec/tools/pd_index_geometry.py \
  >/tmp/pd-pre/pd_index_geometry.py
for m in "--helpers" "--helpers 0x0860" "--helpers 0x0860 0x0C2E" \
         "--bases all" "--strides all" "--callers 0x0860" \
         "--accesses" "--helpers-csv"; do
  PYTHONPATH=ec/tools python3 /tmp/pd-pre/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 $m >/tmp/before.txt 2>&1
  $T $m >/tmp/after.txt 2>&1
  diff -q /tmp/before.txt /tmp/after.txt && echo "IDENTICAL $m"
done

# the one branch that must differ, and only on stdout: the old copy writes the
# 50-byte count line before refusing, the new one refuses first
PYTHONPATH=ec/tools python3 /tmp/pd-pre/pd_index_geometry.py ec/firmware/GMxMGxx_11.800 --helpers 0x1FFE9 0x0860 >/tmp/b.out 2>/tmp/b.err; echo "old exit=$? stdout=$(wc -c </tmp/b.out)"
$T --helpers 0x1FFE9 0x0860 >/tmp/a.out 2>/tmp/a.err; echo "new exit=$? stdout=$(wc -c </tmp/a.out)"
diff /tmp/b.err /tmp/a.err && echo "STDERR IDENTICAL"

# #843's count, re-derived from the committed source: fourteen at this tree,
# and neither walk_helper nor chain_from in it
grep -c 'lo, _ = pd_bounds()' ec/tools/pd_index_geometry.py
grep -n 'lo, hi = pd_bounds()' ec/tools/pd_index_geometry.py

# the repo's mechanical gates
bash tools/run-tests.sh ec/tools
python3 ec/tools/gen_findings_index.py --check
```

The last block is the load-bearing one. The refusal changes must not move a
single byte of output on the legal range, and comparing against the extracted
pre-change file is what makes that a measurement rather than an intention. The
one branch that is *supposed* to differ is the refusal path, and its diff is
the two lost stdout lines and nothing else.

`bash tools/run-tests.sh ec/tools` ends red at this tree, and not from this
change: `test_check_cluster_citations`, `test_check_doc_figure_pins`,
`test_check_eq_guard_citations` and `test_check_pin_table_rows` fail with the
same failure counts (1, 1, 3 and 3) on a checkout of `origin/main` at
`49158e83`, and the failing assertions cite files this diff does not touch.
`.github/scripts/agent-gates.sh` is the gate that passes clean.
