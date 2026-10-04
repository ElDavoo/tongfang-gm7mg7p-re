# Three of the `pd` image's five interrupt vectors are wired to a `ret`, and that is now derived rather than guessed (issue #1062)

`ec/annotations/pd-image.md` §2.1 established that the `ITE8850-PD` image
dispatches its five interrupts through a constant table of five `CODE` words.
It fixed the addresses and the words. It did not read what the words point at,
and for four of the five it said so in as many words: **"Whether those four are
real handlers, padding, or an artefact of reading a constant pool as code is not
determined here."**

That is now determined, and the answer is a positive one about the wiring:

| vector | word | target | what is there |
|---|---|---|---|
| `0x03` external interrupt 0 | `0x0151`-`0x0153` | `0xA8AE` | a committed entry, `event_dispatch_ff80_ffe0` |
| `0x0B` timer 0 | `0x0154`-`0x0156` | `0xF7AE` | **`ret`**, and a `ret` ends a body |
| `0x13` external interrupt 1 | `0x0157`-`0x0159` | `0xF7AF` | **`ret`**, and a `ret` ends a body |
| `0x1B` timer 1 | `0x015A`-`0x015C` | `0xF790` | `lcall 0xEFEA`, then `ret` |
| `0x23` serial port | `0x015D`-`0x015F` | `0xF7B0` | **`ret`**, and a `ret` ends a body |

**Three of the five interrupt vectors are wired to a `ret`**, and a `ret` is this
image's way of spelling a handler that does nothing and returns. The other two go
to real code: `0x03` to a dispatcher that reads the XDATA event word at `0xFF80`,
and `0x1B` to a call into a routine at `0xEFEA` that is still undecoded.
Everything below is static reading of the committed `ec/firmware/GMxMGxx_11.800`. **No register was read back, nothing was run on
the machine, and whether those three vectors are ever enabled is a hardware
question this image cannot answer** — §"What is still open" says which.

The measurement is [`ec/tools/pd_vector_handlers.py`](../../ec/tools/pd_vector_handlers.py),
held by
[`ec/tools/test_pd_vector_handlers.py`](../../ec/tools/test_pd_vector_handlers.py),
and §"Re-deriving" at the end reproduces every figure from committed inputs.

---

## 1. The load-bearing part: a bare `ret` is a no-op here, not padding

The reading that decides the question is not "the byte is `0x22`". It is that
`0x22` is *this convention's* way of spelling "the handler does nothing", and
that comes off committed bytes in four links. Take any one of them away and
"a `ret` there returns to the wrapper" stops following from the image.

**Link 1 — the wrapper puts a return address on the stack.**
`ec/decompiled/pd/010E.asm` (`vector_wrapper_dp_015d`) is the `0x23` vector's
wrapper, the long form:

```
010E     c0 e0 -  push     A
0110     c0 f0 -  push     B
0112     c0 83 -  push     DPH
0114     c0 82 -  push     DPL
0116     c0 d0 -  push     PSW
0118     75 d0 00 mov      PSW, #0x0
011B     c0 00 -  push     0x00
  ...    (R0 through R7)
012B     90 01 5d mov      DPTR, #0x15d
012E     12 00 50 lcall    0x0050
0131     d0 07 -  pop      0x07
  ...    (everything back, in reverse)
0141     d0 d0 -  pop      PSW
  ...    (A last)
014B     32 - -   reti
```

The `lcall 0x0050` at `0x012E` is what puts a return address on the stack. The
first `pop` after it is at `0x0131`, which is the value that return address
holds, and the `reti` at `0x014B` is what runs once the pops are done.

**Link 2 — the shared body leaves with a jump, so it adds nothing on top.**
`ec/decompiled/pd/0050.asm` is two instructions:

```
0050     12 10 f1 lcall    0x10f1
0053     02 12 29 ljmp     0x1229
```

`0x0050` is `lcall 0x10f1` then `ljmp 0x1229`. A `call` would push a return
address of its own and leave the wrapper's underneath it; a `jump` pushes
nothing.

**Link 3 — and the body's own push is gone before the jump runs.** This is the
link that makes link 2 load-bearing rather than decorative, and it is the one a
naive check misses. `lcall` falls through, so a walk that only asked "does the
body end in a jump?" would keep saying yes after the tail jump had become a
*call* — it would simply find the next transfer further along.
`calls_left_open()` in the tool is the real check: every `lcall` on `0x0050`'s
straight line has to be popped by its own callee. `0x10f1` is
`read3_code_to_r3r1` and ends in a `ret` at `0x10FC`, so it is. A body whose
tail jump became an `lcall` would call `0x1229`, which does not return, and the
suite asserts that one byte makes the chain go red.

**Link 4 — the last transfer into a handler is a jump too.**
`ec/decompiled/pd/1229.asm` is four bytes and `ec/decompiled/pd/122D.asm` is two
more, and they are separate listings that happen to abut:

```
1229     8a 83 -  mov      DPH, R2
122B     89 82 -  mov      DPL, R1
122D     e4 - -   clr      A
122E     73 - -   jmp      @A+DPTR
```

`0x1229` builds DPTR from the two bytes `0x10f1` read and falls straight through
into `0x122D`, whose last instruction is `jmp @a+dptr` (`0x73`). A
`call @a+dptr` would push a return address that the handler's `ret` would then
pop *instead of the wrapper's*, which is the whole difference between the chain
working and not. The `0x73` is pinned by value in the suite, not by the
routine's name.

**Put together:** control reaches a handler by three jumps after the wrapper's
call. The top of stack on entry is the return address the `lcall 0x0050` at
`0x012E` pushed, and nothing has pushed over it. A `ret` at the handler pops
exactly that and resumes the wrapper at `0x0131`, which unwinds the 13 pushes
and executes `reti`. In this image's convention **a handler that does nothing
is spelled `ret`**, and a `ret` is therefore the terminator a real handler
would have too.

## 2. The negative control: the same bytes are demonstrably callable

Reading `0x22` as a terminator would still not rule out padding, because padding
*also* reads as `0x22` when you decode it. What rules it out is a caller.
Inside the same run, four bare-`ret` stubs are called by committed listings:

```
$ grep -E "lcall +0xf7b[2347]" ec/decompiled/pd/*.asm
ec/decompiled/pd/A8AE.asm: A943     12 f7 b4 lcall    0xf7b4
ec/decompiled/pd/DA44.asm: DA44     12 f7 b2 lcall    0xf7b2
ec/decompiled/pd/DA44.asm: DA4A     12 f7 b3 lcall    0xf7b3
ec/decompiled/pd/DA44.asm: DA6F     12 f7 b7 lcall    0xf7b7
```

`0xF7B2`, `0xF7B3`, `0xF7B4` and `0xF7B7` are each a single `0x22`, they are
carried as `ret_only_f7b2` … `ret_only_f7b7` in
`ec/annotations/ghidra-functions.csv`, and `poll_0208_0209_then_spin` and
`event_dispatch_ff80_ffe0` `lcall` them. **A `0x22` in this run is a no-op stub
that committed code calls.** Padding has no caller, and that is the whole of the
exclusion — it is a demonstration from committed code, not an argument from the
shape.

Each of those rows carried a clause this settles, and each now carries the
correction beside the sentence it replaces. The clause offered three readings —
"a deliberate empty stub, the default arm of a dispatch table, or an artefact of
the function split" — and a caller excludes two of them: these bytes are not
padding and not an artefact of how the export split the image. Whether they are
the default arm of a dispatch table is still open. The clause is left visible
rather than edited away, per the convention `pd-image.md` §2.1 already uses for
its own XDATA correction.

## 3. The run reads as code throughout, in three shapes

Between `0xF786 tailcall_7b14_with_r7_zero` and the committed `ret_only_f7b2`
rows, the whole of `0xF78B`-`0xF7B7` is a bank of short routines. The two
committed `forwarder` rows either side of it fix the shape of the thing:

```
$ python3 ec/tools/disasm8051.py /tmp/pd.bin --at 0xf78b -n 20
0x0f78b  020108   ljmp 0x0108
0x0f78e  04       inc  a
0x0f78f  1012ef   jbc  0x22.2,+0xef
0x0f792  ea       mov  a,r2
0x0f793  22       ret
0x0f794  ef       mov  a,r7
0x0f795  7f1c     mov  r7,#0x1c
0x0f797  22       ret
0x0f798  12e5eb   lcall 0xe5eb
0x0f79b  22       ret
0x0f79c  02d085   ljmp 0xd085
0x0f79f  024402   ljmp 0x4402
0x0f7a2  7f02     mov  r7,#0x02
0x0f7a4  22       ret
0x0f7a5  7f03     mov  r7,#0x03
0x0f7a7  22       ret
0x0f7a8  02f073   ljmp 0xf073
0x0f7ab  02f732   ljmp 0xf732
0x0f7ae  22       ret
0x0f7af  22       ret
```

Three shapes, and every entry in the run ends in one of them:

- **`ljmp` forwarders**, whose own body is nothing: the committed `0xF79C
  ljmp_d085` and `0xF79F ljmp_4402` already fix this, and `0xF78B`, `0xF7A8` and
  `0xF7AB` are the same shape.
- **`lcall`-then-`ret` bodies**: `0xF790` to `0xEFEA` and `0xF798` to `0xE5EB`,
  the same three-instruction idiom the `call_f739_then_return_dptr_07d0*` rows
  carry elsewhere in this image.
- **register-setting stubs that return a constant**: `0xF7A2` returns R7 = 2 and
  `0xF7A5` returns R7 = 3, the shape the `set_r7_*_tail_3fa4*` rows carry in the
  main EC.

**One address in the plan this was built from was wrong, and the bytes settled
it.** The `ljmp 0xF732` starts at `0xF7AB`, not `0xF7AC` — `0xF7AC` is that
`ljmp`'s low operand byte. A seed at `0xF7AC` would have disassembled from the
middle of an instruction, which is the "annotation whose address has no
function is a typo or needs a rebuild" case CLAUDE.md names.

## 4. The framing conflict, left standing

One thing in the run does not resolve, and it is reported rather than closed.

**A linear walk from `0xF78B` does not land on `0xF790`** — and `0xF790` is an
entry, because the `0x1B` vector's word at `0x015B`/`0x015C` names it and
`jmp @a+dptr` executes against it. The walk reads `inc a` at `0xF78E` (one
byte, `0x04`), then a three-byte `jbc` at `0xF78F` whose *operand bytes* are
`0x12 0xEF` — which are the first two bytes of the `lcall 0xEFEA` at `0xF790`.
So the two framings read `0xF78E`-`0xF792` two ways, and they cannot both be the
executed one.

`framing_conflict()` in the tool returns exactly this set — handler targets that
no committed listing holds and that the linear walk steps over rather than
landing on — instead of picking the reading that makes the gap close.
`disasm8051.py`'s own docstring is that it "cannot tell you that the byte you
pointed it at is the start of an instruction", and nothing else in this image
can either. The suite asserts the conflict is still there, so an edit that
quietly resolved it takes the run red rather than passing for a reading nothing
established.

What *is* decided: `0xF790` is reached, because the vector word says so and the
`jmp` is unconditional. Only the two bytes `0xF78E`-`0xF78F` in front of it are
unframed, and a scan of every transfer form in the region — absolute,
PC-relative and paged, at every byte offset — finds none naming either of them.
That is *not found by this method*, not an absence, and §6 carries the same
wording because the same claim is made twice.

## 5. `0xEFEA` and `0xE5EB` are not decoded here, and "not decoded" is a search

`0xF790` and `0xF798` call `0xEFEA` and `0xE5EB`. Neither has a committed
listing, neither is decoded here, and this write-up makes no claim about what
either does. The referrer census is reported as **two populations that are never
exchanged**, which is the arrangement `pd-e2e4-entry-forms.md` established on
another address:

| target | decoded `lcall`/`ljmp` in the committed pd listings | byte-scan candidates in the 64 KiB |
|---|---|---|
| the five handler targets | 0 | 0 |
| `0xEFEA` | 0 | two, at `0xF081` and `0xF790` |
| `0xE5EB` | 0 | two, at `0xE084` and `0xF798` |

The two columns answer different questions. The first reads *decoded
instructions* out of the committed listings, so an operand byte inside some
other instruction cannot be read as an opcode. The second counts every position
in the 64 KiB whose three bytes spell `lcall 0xEFEA`, which is byte-aligned and
cannot know whether it found the start of an instruction. **Every candidate is
a candidate, not a caller**, and in this image none of the four sits inside a
committed listing.

So the honest sentence is: **no committed `pd` listing contains an `lcall` to
`0xEFEA` or `0xE5EB`; a byte scan finds two sites for each, one of which is the
run's own call into it, and not one of them is inside a committed listing.**
That is *not found by this method*, and it is not *unreachable*. The suite
asserts the tool prints the token `not found by this method` and names the
search, and asserts that a target which *does* have callers does not carry the
token — a checker that always printed it would pass the null case and be
worthless everywhere else.

The five handler targets having **zero in both columns** is the other half of
the finding: nothing in this image names them by an instruction. They are
reached by `jmp @a+dptr` off a table, which is what the table is for.

## 6. What is still open

- **`0xEFEA` and `0xE5EB`.** The bodies behind the `0x1B` vector and behind
  `0xF798`. Neither is decoded, neither has a listing, and §5's null is a
  statement about a search.
- **Whether the three no-op vectors are ever enabled.** `0x0B`, `0x13` and
  `0x23` point at a `ret`. Whether an interrupt on those vectors fires and
  returns or is left masked **is not in the image**, and it is a live
  observation. This pipeline has no laptop; a human at the machine runs it, and
  the result is a register-style trace rather than anything here can produce.
- **Which physical source sits on each vector, and why the two timer vectors
  are the short-form wrappers.** Still §6 item 3 of `pd-image.md`, and still not
  what this question asked.
- **The two bytes `0xF78E`-`0xF78F`.** §4. Unframed, and a scan of every
  transfer form in the region finds none naming either — *not found by this
  method*.
- **The seed rows, and the export.** §7.

## 7. The seed is the next step, and a documented wall is why

The natural next move is to add rows to
`ec/annotations/ghidra-functions.csv` at the run's interior addresses and
re-export, so `ec/decompiled/pd/` carries these names. **That step is not in
this change**, and the reason is mechanical rather than a judgement:

- Seeding a new function needs `--mode rebuild-project`, because the default
  `export-only` copies the committed project and cannot carve a function into
  it. `build_ec_decompile.py` is explicit that only the rebuild writes the
  `.gpr`/`.rep`.
- `--mode rebuild-project` **cannot run for a contributor who does not own the
  committed project.** It aborts before reading a single annotation:

  ```
  ERROR Abort due to Headless analyzer error: ghidra.util.NotOwnerException: Project is owned by dave
  ```

  `ghidra/project_owner.py` fixes that for the *copy* the export-only mode
  makes, and refuses any `rep_dir` outside a scratch root — which is the guard
  that keeps it from ever writing the committed `.rep`.
  `docs/findings/ghidra-project-owner.md` records the consequence in its own
  words: `--mode rebuild-project` is "not covered, deliberately", because
  "there is no scratch copy for the rewrite to attach to", and it is "the mode
  an agent branch cannot usefully run".
- **An annotation row whose address has no function fails the build**, by
  design — that is how a typo is told apart from a project that needs a
  rebuild. So the rows cannot land on their own either. Verified here: with the
  rows added and no rebuild, `build_ec_decompile.py --check` goes red on each one
  with "resolves to no exported function -- either a typo or the project needs a
  rebuild", and on the manifest's `annotations_unmatched` counter.

So what lands instead is the half that is not blocked: the derivation, the tool
that derives it and holds the page to it, the page correction, and the
in-place correction of the committed rows that already carry listings.
`uncovered_in_run()` names the address spans a seed would have to cover, so the
next person does not re-derive them:

```
$ python3 ec/tools/pd_vector_handlers.py | grep "addresses in the run"
  addresses in the run no committed listing holds: 0xF78B-0xF79B, 0xF79D-0xF79E, 0xF7A0-0xF7B1, 0xF7B5-0xF7B6
```

**The five `vector_wrapper_dp_*` rows and the four `ret_only_f7b*` rows carry
the correction**, because CLAUDE.md is explicit that the annotation CSV is the
machine-readable layer and the page is the readable one, and that the two are
edited together in the same pull request. Each row keeps the sentence it
replaces visible beside the replacement.

Note that the decompiled `.c` files are **not** regenerated here, and that is
also the tree's own practice rather than an omission: `build_ec_decompile.py
--check` holds `c-digests.csv` against the committed `.c` files and does not
re-export, so an annotation comment change lands in the CSV and the exported
`.c` catches up on the next regeneration. The most recent commit to touch this
CSV (#1861) changed rows without re-exporting for the same reason.

## Re-deriving

Every figure above, from the repository root, with no Ghidra, no network and no
hardware:

```console
$ python3 ec/tools/pd_vector_handlers.py
$ python3 ec/tools/pd_vector_handlers.py --check
$ python3 ec/tools/pd_vector_handlers.py --run 0xF78B,0xF790
$ python3 -m unittest discover -s ec/tools -p test_pd_vector_handlers.py
$ python3 ec/tools/disasm8051.py /tmp/pd.bin --at 0xf78b -n 20
$ grep -E "lcall +0xf7b[2347]" ec/decompiled/pd/*.asm
$ python3 ec/tools/build_ec_decompile.py --work /tmp/ec --check
$ python3 ec/tools/pd_image_census.py --check
```

`/tmp/pd.bin` is the 64 KiB region at file `0x20000`:
`dd if=ec/firmware/GMxMGxx_11.800 of=/tmp/pd.bin bs=64k skip=2 count=1`.

The suite is found by `bash tools/run-tests.sh` with no registration, and the
tool is **not in any gate**: `.github/scripts/agent-gates.sh` is a pipeline file
and this branch's token has no `workflow` scope, so a gate call is a human's
change. That is the arrangement `pd-image.md` §0 records for
`pd_image_census.py`, for the same reason.

## Related

- [`pd-image.md`](../../ec/annotations/pd-image.md) §2.1 — the vector table and
  the five `CODE` words. Its "that target is" column and its §6 item 3 are
  corrected in place, with the previous wording left visible.
- [`pd-e2e4-entry-forms.md`](pd-e2e4-entry-forms.md) — the two-population
  referrer contract this borrows, on another address.
- [`pd-no-ret-fallthrough-boundaries.md`](pd-no-ret-fallthrough-boundaries.md) —
  the neighbouring question of where the export's function boundaries are, and
  why a byte alone does not settle it.
- [`ghidra-project-owner.md`](ghidra-project-owner.md) — §7's blocker, measured.
