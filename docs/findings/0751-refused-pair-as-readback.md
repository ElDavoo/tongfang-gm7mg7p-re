# §4.6 named a pair the whole-block section had refused, and the hint ended in a pre-write dump (issue #386)

The write-up for [issue
#386](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/386), the sibling
of [`0751-readback-written-value-notice.md`](0751-readback-written-value-notice.md)
(#387). #202 added two checks to `ec/tools/grade_0751_isolation.py` — the
"a `--dump-pair` does cover it" hint in §4.6, and the same-file refusal in the
whole-block section — and each was written against its own question. Coverage
is what §4.6 selects a pair on; whether the pair is a bracket at all is what
the whole-block section checks. Nothing carried the second answer to the first,
so §4.6 named a pair the other section had just called not a bracket.

**Offline throughout, and nothing here is a claim about the machine.** No EC
was read, no §3 run was performed, no laptop or Windows box was reached, and no
register was observed. The whole of the evidence is this tree's Python printing
sections over the committed fixtures in
`ec/tools/testdata/0751-isolation-run/`, which are **hand-written input, not a
capture**: every file there carries a `# CONSTRUCTED INPUT, NOT A CAPTURE`
header, no byte in it was read from an EC, and `ec/tools/testdata/README.md` is
where that rule is written down. Every sentence below is about which files were
handed in and what the report said about them.

---

## The two readers, and what each one knows

`report_dumps` groups the `--dump`s by the block they name and hands each group
to `report_readback`. Where the group's last `--dump` does not reach `0x0751`,
`report_readback` prints the coverage notice and then walks `pairs` for the
first one where `MANUAL_FAN_CTRL in set(before) & set(after)`, names it, and
breaks. That intersection is the right question for a hint — a readback needs
both sides of the pair to hold the byte — and it is the only question asked.

`report_dump_pairs` is handed the same `pairs` list later, and refuses any pair
whose two paths `os.path.realpath` to the same file. The refusal lives in that
loop's body as a test, with its reason as a literal, and it stops there: no
return value, no shared predicate, nothing for §4.6 to consult. Two readers,
one fact about the two files, and the fact written down once.

## The reproduction, over §6's committed files

No new fixture is involved. §6's own `0x0700` before-dump is paired with
itself, and the two `0x0F00` dumps are passed last so the block's final
`--dump` stops short of `0x0751` — the ordering mistake §6's command block
warns about. In the output below, `…/` stands for
`ec/tools/testdata/0751-isolation-run/`, which is a long prefix repeated on
every line and changes nothing about the shape.

```
$ D=ec/tools/testdata/0751-isolation-run
$ python3 ec/tools/grade_0751_isolation.py $D/2026-01-01-0751-isolation-0700-07ff.csv \
    --dump $D/2026-01-01-0751-isolation-a0-before-0f00.txt \
    --dump $D/2026-01-01-0751-isolation-a0-after-0f00.txt \
    --dump-pair $D/2026-01-01-0751-isolation-a0-before-0700.txt $D/2026-01-01-0751-isolation-a0-before-0700.txt \
    --wrote 0xA0
```

Before, the §4.6 section read:

```
  the last --dump does not cover 0x0751, so the §4.6 readback was not taken -- nothing here says what the byte held after the write
    a --dump-pair does cover it: …/2026-01-01-0751-isolation-a0-before-0700.txt -> …/2026-01-01-0751-isolation-a0-before-0700.txt; both files reach 0x0751
      pass the after file as the last --dump to take the readback: …/2026-01-01-0751-isolation-a0-before-0700.txt
```

and eleven lines further down, in the whole-block section, over the same pair:

```
  …/2026-01-01-0751-isolation-a0-before-0700.txt -> …/2026-01-01-0751-isolation-a0-before-0700.txt
    both sides are the same file, so this pair is not graded: a read compared with itself proves nothing. Pass the before and after dumps of one range as two different files.
```

The tool names one pair, and in the next section says it is not a pair.

## Following the hint produces a substantive wrong claim

The hint ends in an instruction, and the instruction is the whole of the harm:
the pair is a self-diff, so its *after* file is its *before* file. Doing
exactly what §4.6 says — dropping the self-diff pair and passing the named file
last — reads the pre-write dump:

```
$ python3 ec/tools/grade_0751_isolation.py $D/2026-01-01-0751-isolation-0700-07ff.csv \
    --dump $D/2026-01-01-0751-isolation-a0-before-0f00.txt \
    --dump $D/2026-01-01-0751-isolation-a0-before-0700.txt \
    --wrote 0xA0
```

```
  …/2026-01-01-0751-isolation-a0-before-0700.txt: 0x0751 = 0x10
  the last dump holds 0x10, not the written 0xA0 -- something put it back; §3a's service-stopped run is what separates the vendor service from the EC.
```

`0x10` is what that fixture's own byte holds **before** the write — a byte
written by hand, to put the pre-write value on the page. The two files say so at
the same line of each:

```
$ sed -n 14p $D/2026-01-01-0751-isolation-a0-before-0700.txt
0750: 00 10 00 00 00 00 00 00 00 00 00 64 50 00 00 00
$ sed -n 14p $D/2026-01-01-0751-isolation-a0-after-0700.txt
0750: 00 a0 00 00 00 00 00 00 00 00 00 6a 51 00 00 00
```

`0x0751` is the second byte of that line. So the run reads a pre-write value,
and the report says of it that something put the value back — a claim about the
vendor service and the EC, made out of a mistyped flag. This is the shape
§4.6's hint produces here, and it is why the fix belongs before the run
[#380](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/380) asks a human
to make at the laptop.

## The `break` makes this the likely case, not an edge

The hint's loop breaks on the first covering pair, so a refused entry in front
of a usable one hides it. The issue names this shape and does not show it; here
it is over the same fixtures, with the refused pair first and §6's real `0x0700`
pair second.

Before, §4.6 named the self-diff and said nothing about the pair behind it:

```
    a --dump-pair does cover it: …-a0-before-0700.txt -> …-a0-before-0700.txt; both files reach 0x0751
      pass the after file as the last --dump to take the readback: …-a0-before-0700.txt
```

After, the refused pair is named with its reason and the walk goes on:

```
    a --dump-pair reaches 0x0751 and is not one to read from: …-a0-before-0700.txt -> …-a0-before-0700.txt
      both sides are the same file, so this pair is not graded: a read compared with itself proves nothing. Pass the before and after dumps of one range as two different files.
    a --dump-pair does cover it: …-a0-before-0700.txt -> …-a0-after-0700.txt; both files reach 0x0751
      pass the after file as the last --dump to take the readback: …-a0-after-0700.txt
```

Following that hint — whose last `--dump` is the pair's after file,
`…-a0-after-0700.txt` — now lands on `0xA0` and prints `the last dump still
holds the written 0xA0`: the wording for a last dump holding what was written to
it, over this fixture's own hand-written byte.

This is the likely case because §6's own command line lists the `0x0700` pair
first, and it is the only §6 pair whose two dumps reach `0x0751` — the `0x0F00`
and `0x0400` pairs do not cover the address. An operator who mistypes that one
entry has nothing behind it to fall back on.

## The closing paragraph, and the same cause one step down

The whole-block section's closing note qualified every `unchanged` line above
it. It is printed outside the group loop, and the `graded` counter the section
already returns was not consulted — so a run whose only pair was refused ended
the section with a paragraph about a read that was never taken, over a body
whose only line was a refusal:

```
  …-a0-before-0700.txt -> …-a0-before-0700.txt
    both sides are the same file, so this pair is not graded: a read compared with itself proves nothing. Pass the before and after dumps of one range as two different files.

  Every `unchanged` above says the byte did not differ between these two reads, which is not a claim that it did not move inside the block: §5, …
```

There is no `unchanged` anywhere in the section. The gate is now the counter
the section already had, and it is strictly narrower than before: an empty
`pairs` returns above this point, so the only runs it stops the paragraph
printing on are the ones where it was describing lines that do not exist. Over
the same run the section now ends:

```
  no dump pair here was compared, so there is no whole-block read to qualify: the pairs above were not compared, and each says why
```

Said rather than dropped, because a silent ending after a pair goes
un-compared is the same defect one step down: a reader who reaches the end of
the section has to be able to tell *compared nothing* from *compared nothing
and said so here*.

The closing sentence reads *were not compared*, not the *were refused* it used
to. `pair_refusal` is not the only thing that keeps a pair out of `graded`: this
section already reported, under what it does not close, a pair whose two names
name different blocks (skipped without being refused) and, on a `--block` run, a
pair belonging to another block (named and skipped), and
[`0751-dump-value-vs-block-value.md`](0751-dump-value-vs-block-value.md) adds a
pair whose before side is mis-filed, withheld in place of the bracket. *Refused*
covered `pair_refusal` and none of those, so it overstated what the paragraph
speaks for. *Not compared* is what the paragraph has always claimed — that every
pair it names above the closing sentence has said why — and it is the wording
that claim survives under.

## The fix, and why it is one predicate rather than a second test

`pair_refusal(before, after)` sits beside `dump_block` and `dump_pair_block`
and answers the one question: can this pair be read at all? It returns the
reason or `None`, and the reason is the constant `SAME_FILE_PAIR`, printed
from both readers so a refusal has one spelling the way `GROUP_NOTE` does. The
whole-block reader's existing line is kept verbatim inside that constant, so
the suite's `both sides are the same file` assertion is over the reason rather
than over one reader's phrasing of it.

Path identity, not the `<value>-before-` / `<value>-after-` spelling, and for
the reason `report_dump_pairs` already gave: a pair is whatever the operator
says it is, `x.txt` and `./x.txt` are the same mistake written two ways, and
§6's naming is a convention the flag does not require.

`report_readback` skips a refused pair rather than breaking on it. Dropping
the `break` alone would name *every* covering pair, which is a different and
noisier change; the predicate is what decides, and the `break` stays for the
first pair that is both covering and readable.

## What this does not close

`report_readback` is handed the whole `pairs` list and selects on coverage, so
a pair `report_dump_pairs` refuses for a reason that is *not* about whether it
is a bracket can still be named there. Two are real:

- a `disagree` pair — `dump_pair_block` returns no value when the two file
  names name different blocks, and the pair is not compared;
- on a `--block` run, a pair belonging to another block, which the section
  names and skips as "not read for §4.1-§4.3 here".

Both are about which block a bracket is filed under, where this is about
whether it is a bracket at all, and both change which pair §4.6 names on
shapes no committed *test* drives — which is its own change, and one that
belongs with a test over the committed fixtures. `pair_refusal` is the place
they go: it already has two callers and one spelling, so a third refusal is a
new constant and a line in one function rather than a second copy of the walk.

## Offline reproduction

Everything above is reproducible from a clean checkout with the committed
fixtures, in the order given. The three cases that hold the behaviour live in
`RefusedPairReadbackTests` in `ec/tools/test_grade_0751_isolation.py`:
`test_a_refused_pair_is_withheld_as_the_readback_not_named`,
`test_a_refused_pair_does_not_hide_a_valid_one_behind_it`, and
`test_the_closing_paragraph_is_gated_on_a_pair_having_been_read` — the last
one asserting the paragraph is still printed over a run that did compare, so
the gate cannot be inverted into never-print.
