# An unreadable `--dump` is named, and the §4.6 readback still runs (issue #388)

The write-up for [issue
#388](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/388): `read_dump`
opened its file with no handling, so a `--dump-pair` or `--dump` path that
cannot be opened ended the run in a bare `FileNotFoundError` — and because the
file lists are read before either section prints, it took the §4.6 section down
with it, which is the one section whose whole job is to be trustworthy about
two files on disk.

**Offline throughout.** No EC, no laptop, no Windows box was reached, and no
capture was taken. Every figure below is this tree's Python reading bytes this
repository committed under `ec/tools/testdata/0751-isolation-run/`, plus paths
under a `tempfile` directory that were never written to. Nothing here should be
read as a live observation of the machine.

## The defect, on §6's own file list

The issue's command line, over the committed fixtures:

```console
D=ec/tools/testdata/0751-isolation-run
python3 ec/tools/grade_0751_isolation.py $D/2026-01-01-0751-isolation-0700-07ff.csv \
  --dump $D/2026-01-01-0751-isolation-a0-before-0700.txt \
  --dump $D/2026-01-01-0751-isolation-a0-after-0700.txt \
  --wrote 0xA0 \
  --dump-pair $D/2026-01-01-0751-isolation-a0-before-0700.txt after-0700-typo.txt
```

Run against the tool as of `d8d98b79`, the window report and the block section
print in full — including the block's `intact` verdict and §7's caveat — and
then:

```
Traceback (most recent call last):
  File "grade_0751_isolation.py", line 5233, in <module>
    sys.exit(main())
  File "grade_0751_isolation.py", line 4755, in main
    pairs = [(b, a, read_dump(b), read_dump(a))
  File "grade_0751_isolation.py", line 2065, in read_dump
    with open(path, newline="", encoding="utf-8") as f:
FileNotFoundError: [Errno 2] No such file or directory: 'after-0700-typo.txt'
```

rc=1, and `=== 0x0751 across the dumps (§4.6) ===` never appears — although
**both** `--dump`s on that command line were readable and would have answered
it. The window report the operator got is not wrong; it is just not the whole
report, and it ends looking like the run finished.

The ordering that makes this cost a section rather than a line is load-bearing
and was kept. `main` reads both file lists before printing either, so §4.6 can
name a `--dump-pair` that covers `0x0751` while it is saying the readback was
not taken. The fix is that the read can no longer *end* the run, not that it
moved.

## The exit status, read off the code rather than picked

Two places in this tool already handle a bad `--dump-pair` input, and both say
what they do in their own words:

- `report_dump_pairs`, on a pair given one file twice: *"Flagged and skipped
  rather than fatal, so the window report and the §4.6 readback the operator
  also needs still get printed."*
- `dump_pair_block`, on two names that disagree about their block: *"the same
  non-fatal handling the same-file-twice pair gets, because it is the same
  class of thing: an input error, stated, with the window report and the §4.6
  readback the operator also needs still printed."*

A file that is not there is that same class of thing, so the handling is the
same one: **named, not compared, rc 0, run carried on.**

The fatal precedents are the captures and the value under test — a repeated
capture, and a `--block`/`--wrote` that disagree or name no block — and `main`'s
comment on the repeat draws the line this sits on the other side of: skipping a
*capture* "would hand back a report that is quietly a single-capture run",
because every section of this report is about the captures. A skipped dump is
not that; the section that would have read it prints the omission in full.

## The shape that was easy to get wrong

`read_dumps` returns **every** `--dump` in the order it was handed in, with
`values` of `None` where the file would not open, rather than the subset that
opened. That is not tidiness — it is the bug a "just skip it" implementation
walks into.

`report_dumps` takes the §4.6 readback from the **last** `--dump` of the block
under test. Delete an unreadable entry and the dump before it is promoted into
that place, and the section prints:

```
the last dump still holds the written 0xA0.
```

which is a true sentence about a file the operator did not name last, in the
wording that says it is the last one. So the unreadable entry keeps its place
and prints its own line where its byte would have been:

```
after-0700-typo.txt: not read: [Errno 2] No such file or directory: 'after-0700-typo.txt'
```

`report_readback` grew the matching third precondition beside the two it
already prints — the last dump does not cover `0x0751`, and nothing names the
value that was written — so a group whose last entry has no bytes behind it
says the readback was not taken, names the file, and hands over the same
remedy the coverage notice gives (a `--dump-pair` that does cover the byte,
with its after file to pass last). That precondition is the load-bearing half:
without it the fix produces a true sentence about the wrong file, which is
exactly the overclaim CLAUDE.md's calibration rule is about.

For a `--dump-pair` the direction is the other one. A pair with either side
unreadable is **dropped whole** rather than compared over the survivor, because
a whole-block read is the intersection of two files and one of them not being
there is not a bracket: `0 address(es) compared` over what survived would be a
result about nothing, which is the same false green `SAME_FILE_PAIR`'s own line
is written against. The dropped pair is still printed where it was handed in —
path, which side raised, and the error — so the operator can see which entry
was not read instead of finding a shorter list.

## The two "nothing was given" lines

`report_dumps` and `report_dump_pairs` both have a line for a run that was
handed no files at all, and both stay **byte for byte** — no test asserts their
spelling, so what holds them is that they are true of every run they print for.
A run that handed in files and had every one of them fail to open is a different
fact, and reusing the sentence would be false: the operator did give files, and
this is what became of them. So those cases print the named failures and, for
the dumps, their own line:

```
none of the 1 dump(s) given could be read, so §4.6 was not checked; each is named above
```

## One sentence that had to stop firing

`report_dump_pairs` has a footer for a `--block` run handed no pair for the block
under test, and it ends "the pairs named above are another block's". That is a
claim about which block a pair belongs to, and a pair whose before file could
not be read was never filed under one — the grouping runs over the pairs that
opened. On a `--block` run whose only pair would not open, the section was
saying the pair was another block's, under a header about attribution and on no
evidence at all.

It is now gated on there being a group to attribute *and* on no pair having
failed to open. The second term is not the same case twice: put a readable pair
naming another block beside an unreadable one and the readable pair files a
group, so gating on a group alone still fires the footer with the unreadable
pair named under it — and takes the first half with it, since a pair that named
the block under test and would not open is a pair that was given. The pair's
own line above still says what became of it, the readable pair's own line still
says whose it is, and the paragraph below still says nothing was compared, so
the section loses the unfounded sentence and not the fact; and the same footer
still fires where it is earned, on a pair that names another block outright.
`report_dumps` needs no such gate: an unreadable `--dump` stays in its group,
so its block attribution is off its filename's `<value>`, which is exactly what
the footer there claims.

## What the catch covers, and what it deliberately does not

`OSError`, and nothing wider. A dump that opens and is not decodable raises
`UnicodeDecodeError`, and one holding a line that is not hex raises
`ValueError`. Those are different faults from a file that is not there, and
swallowing them under "not read" would report a parse failure as an input one —
which is a false statement about the file in the direction that matters least,
which is how such a claim gets made. A narrow catch that has to grow later is
visible in a diff; an over-wide one here is not. `read_dump`'s signature and
body are unchanged and it still raises, so the fixture-reading test helper that
calls it directly is untouched and this is not a second parse path.

## Scope this does not reach

- **A nonexistent or unreadable positional capture CSV.** Same traceback, and
  it is a different decision. The captures are what *every* section of the
  report is about — the census, the agreement checks, the void check, the block
  walk — so a capture that cannot be opened belongs beside the repeated-capture
  refusal in `main`, which is fatal and runs before any file is read. Widening
  that is a question about the captures, not this issue's. Reported here as the
  obvious sibling defect.
- **A dump that opens but is malformed**, for the reason above.
- **Reversing the read-before-print order** of issue #202, which is load-bearing
  in `main`'s own comment and in `report_dumps`'s docstring alike.
- **Running the procedure on the laptop.** Nothing here needs one: the change is
  entirely about how a file that cannot be opened is reported, and the fixtures
  that prove it are already committed. No live test is claimed or implied.

## How to re-check this

```console
python3 ec/tools/grade_0751_isolation.py --self-test
bash tools/run-tests.sh ec/tools
python3 ec/tools/gen_findings_index.py --check
python3 ec/tools/check_no_append_logs.py
python3 ec/tools/check_findings_frozen.py
```

and the issue's command line above, which now ends rc=0 with §4.6 printed:

```
=== 0x0751 across the dumps (§4.6) ===
  block 0xA0, from the <value> in these files' §6 names
  …-a0-before-0700.txt: 0x0751 = 0x10
  …-a0-after-0700.txt: 0x0751 = 0xA0
  the last dump still holds the written 0xA0. Per CLAUDE.md that is a readback, not evidence the EC acted on it.

=== whole-block dump pairs (§4.1-§4.3) ===

  …-a0-before-0700.txt -> after-0700-typo.txt
    after: not read: [Errno 2] No such file or directory: 'after-0700-typo.txt'
    this pair is not compared: a whole-block read is the intersection of two files and it needs both of them
```

**The evidence is those two runs, not a pass count.** The dumps are §6's
committed fixtures and the failing paths are ones this checkout never wrote.