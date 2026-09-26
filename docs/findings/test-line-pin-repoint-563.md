# The two `:563` pins of finding 7 are repointed, and finding 6's four stale pins are deliberately not (issue #930)

**Nothing here is a hardware claim, and nothing here is a firmware claim.** No
image is opened, no register is read back, no capture is taken, and no laptop, EC
or Windows machine is involved anywhere below. Every figure is a count of lines
in files in this repository, and the one command that produces them is in it.
Same framing as [`test-line-pin-census.md`](test-line-pin-census.md) and
[`doc-figure-pin-audit.md`](doc-figure-pin-audit.md): a census of text about text.

**This is a two-line repair, and the reasoning is the point.** Two line numbers
in one markdown file, and the counts that read them. The argument is here rather
than in the four shared files it touches, because all four are merge magnets with
open PRs against them and the argument belongs in none of them.

## What moved

`docs/findings/xdata-moved-ranks-key-collision.md` §3 and §5 each cited
`ec/tools/test_xdata_cluster_names.py` at `:563` for the suite's `> 300` floor,
`assertGreater(len(moved), 300)`. That was **correct when #888 wrote it**: the
floor was at `:563` on that tree. #890 then put 25 lines into that file above it,
so the floor is at `:588` and `:563` is now a fixture row,
`("0x0843", ("84", "42"), ("126", "0"))):`. Both sentences became defective, and
in §5's bullet defective in a second way — it is a calibration bullet asserting
*the merge touched nothing*, and it named a line the merge's sibling moved under.

Both citations are now `:588`, with the superseded `:563` written **bare** beside
them, and §5's amendment — the one recording that the split had stopped being a
split — is taken back in place rather than deleted or rewritten, per
`../findings.md` §4a-4d. It stays as it was written because it was true of the
tree it was written on, and a correction that has itself been overtaken is
corrected the same way an uncorrected one is.

**"Both carry" is a reading, and it is a reading somebody looked at.** The
repointed line is `self.assertGreater(len(moved), 300)`, sitting directly under
the two lines §3 describes as *"the suite's own two lines, string for string"*
that the floor is applied to. `census_test_line_pins.py` renders no verdict on
that and cannot: its docstring declines to, and *Why no checker* in
[`test-line-pin-census.md`](test-line-pin-census.md) is the measurement for the
refusal. The table records the reading; the tool records the spelling, the target
and the landing shape.

## The run, before and after

```console
$ python3 ec/tools/census_test_line_pins.py
105 pin(s) in 27 markdown file(s): 78 distinct spelling(s), 57 distinct resolved target(s)
  73 resolves, 0 out-of-range, 0 unresolved-path, 0 ambiguous-path, 32 declined
  5 def test_, 19 assertion, 10 comment, 6 blank, 33 other (of the pins that resolve)
  read 148 markdown file(s) under the tree, excluding .git/vendor/ and docs/findings/test-line-pin-census.md; resolved against 35 test file(s) in it
  no claim is measured here: whether a cited line still carries the claim it is cited for is a reading, and it is docs/findings/test-line-pin-census.md's table
$ echo $?
0
```

Against the run immediately before it — the `#885 × #771` merge's, which
[`test-line-pin-census.md`](test-line-pin-census.md) publishes verbatim under the
transcript:

| figure | before | after | why |
|---|---|---|---|
| pins (occurrences) | 105 | **105** | one spelling out, one in |
| markdown files with a pin | 27 | **27** | the same two rows of one file |
| distinct spellings | 78 | **78** | `:563` by-name out, `:588` by-name in |
| distinct resolved targets | 58 | **57** | `:588` was already a target; `:563` loses its last name |
| resolves / declined | 73 / 32 | **73 / 32** | both pins still resolve |
| shapes | 5/17/10/6/35 | **5/19/10/6/33** | `:588` is an `assertion` again |
| `carries` | 48 | **50** | a table reading, not a test assertion |
| does not carry | 13 | **11** | finding 7's two come out |
| markdown files read | 147 | **148** | this file |

**`105` and `78` are the load-bearing numbers, and they are the reason this file
is allowed to exist at all.** They are the same on both runs, so the correction
added no pin and deleted none: the two rows were re-spelled, not written or
removed. The figure that moves is the target count, and it moves because `:588`
was *already* a target — the checklist carries the same span by path — so the
repoint moved an existing name onto an existing target while `:563` lost the
last name it had. The superseded `:563` is written bare here, and in the shared
files, for the reason `../findings.md` §65 gives: a correction spelled as a
`test_*.py:NNN` would be the 79th spelling in the census it is reporting on, and
would move two of the very figures it reports. The `148` is what this file costs,
and it is named rather than absorbed into a denominator nobody would notice.

**This pass landed on a tree that already carried two further merges, and the
figures above are measured on that tree rather than on the one the repoint was
first written against.** #885's two citations of the same assertion merged under
#888's, and then #771's write-up landed beside those, which is why the counts on
both sides of the table are the `#885 × #771` ones rather than the
`#888 × #885` ones — #885's two are two of the 105 occurrences, one of the 27
files, one of the 78 spellings, one of the 57 targets and two of the 73
resolving pins, and #771's thirty-two are thirty-two more occurrences in one
more file, none of either set being a target the other already had. Of the
thirteen that did not carry on that tree, four were #850's, two #888's and two
#885's; this pass's repoint took #888's two off the list, and the eleven that
remain are the nine #850 left and #885's two.
Nothing about the repoint's own arithmetic changes: two rows re-spelled,
`assertion` back, one target fewer, one file read more. **The same two rows are
the reason the target count is the one figure three trees disagree about**: the
spelling count reads 46, then 78, then 78, and the target count reads 42, then
58, then 57 — a count nothing but the citing line moved.

## Why these two and not the six that are #920's

`:588` is named by three pins in the corpus, and this pass repointed two of them.
The third is
[`xdata-census-rederivation-checklist.md`](xdata-census-rederivation-checklist.md):334,
which names it by path and did so before this pass. **The six this pass leaves
alone do not name `:588` at all**: finding 6's say `:417` three times over and
`:412-414` once, and finding 8's say `:392` twice. The reason for stopping there
is provenance, not effort:

- **Finding 6's four and finding 8's two** were *stale in the tree* when the census
  found them. #850
  moved the floor from `:392` and repointed one citation of five, so four
  sentences in two other files still named where it was; #885 then wrote two more
  against that same number from a tree where it was still right. They were wrong
  before the census looked, and wrong on the commits that made them so.
- **Finding 7's two** were *correct when written*, and were made wrong by a merge
  landing beside them in a third file, with nothing in #888 able to have known.

The two kinds reach `:588` only in the projected end state, and not all six of
them: follow-up 1 of [`test-line-pin-census.md`](test-line-pin-census.md) sends
finding 6's three and finding 8's two — five — to `:588` and
[`xdata-moved-ranks-fall.md`](xdata-moved-ranks-fall.md):427 to `:584-585`, which
is where the comment it quotes actually is. **Six is the count after #920, not
the count on this tree**, and it is written as a projection rather than a
measurement here because #920 has not run. With the pair this pass did repoint,
the eight `> 300` pins of the class all name `:588` or its comment once #920 lands.

The census counted thirteen that do not carry before this pass and counts eleven
after it, and the two that left the list are finding 7's pair — finding 6's four
and finding 8's two are inside both numbers. Doing all of them in one pass would
collapse the very
distinction the census exists to record, and would make the count of "pins this
repository's own merges broke" indistinguishable from "pins a commit forgot".
One line in one file per issue is what the census itself calls a follow-up.

## The standing rule, re-confirmed rather than relaxed

§7 of [`test-line-pin-census.md`](test-line-pin-census.md) is that **the merge
which makes citing prose stale does not repoint it** — the repointing lives in
that file's follow-up list, which is where one case can be weighed against the
rest of the class instead of each merge deciding on its own. This issue *is* that
follow-up list doing the repointing, one entry at a time, so it is the rule
working rather than an exception to it.

**It is not a licence to repoint the rest of the class in the same pass, and
nothing here should be read as one.** Each entry has a different author, a
different provenance and a different sentence that may need rewriting rather than
a number changing; that is why they are four issues rather than one sweep. #912's
five pins and the wider `.py:NNN` class are untouched for the same reason.

## What this does not do

- **No checker, and no gate.** `census_test_line_pins.py` stays a census: it
  exits 0 on a tree where every pin is wrong, and its docstring says so. The
  judgement half of this page is a reading, and *Why no checker* is the
  measurement for declining it on measurement. Adding a verdict here would be the
  thing that verdict declines, and this issue is not that measurement.
- **No register, no driver, no Windows claim.** `ec/annotations/registers.yaml`,
  `ec/decompiled/`, `bios/`, `windows/` and the annotation CSVs are not touched.
  Nothing here is evidence about a cluster, a fan, a lightbar or a battery.
- **No hardware, and no live run.** Nothing in this file may be read as a
  hardware observation. The one measurement is a count of lines in this
  repository, produced by a command a reader runs.
- **Nothing opened in another repository.** The mission's eventual
  `Wer-Wolf/uniwill-laptop`/`tuxedo-drivers` contribution stays a prepared patch
  in this repository for a human to submit, per issue #10. This touches no driver
  and no firmware.
- **No new tool.** The census already answers the question this issue asks.
  Nothing is bolted onto it, and the suite that holds its published figures has
  its three moved constants updated rather than a new case added — this change
  adds no behaviour to test.
