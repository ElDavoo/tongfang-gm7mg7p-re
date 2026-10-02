# The `ecrw` fixture's mirror claim, measured, and narrowed to what it carries (issue #356)

`windows/tools/ecrw_fake.py` asserts a mirror of the real module. Two of its
docstrings and one sentence of `tools/README.md` said so, and nothing held any
of it to anything: no suite ever compares the two files, and the cheap gate's
`check_python_syntax` cannot see a cross-file shape difference. What this
change adds is `windows/tools/test_ecrw_fake.py`, which parses both with `ast`
and holds them to each other — and, on the way, **narrows the claim** from the
whole surface to the surface the tools actually reach, because the measurement
says the whole-surface wording was wrong by three names rather than one.

**Nothing here was observed on hardware.** No EC was opened, no register read
back, no ioctl issued. Both files are read as source and compared as shapes.

## The measurement, re-taken

The issue's table names `_ioctl` as the only absent member. Parsing both files
with `ast` on this tree gives three, and one member present in both files is
missing from that table entirely:

| | `windows/tools/ecrw.py` | `windows/tools/ecrw_fake.py` |
|---|---|---|
| `Ec` methods | `__init__`, `close`, `__enter__`, `__exit__`, `_ioctl`, `read`, `read_dword`, `read_dword_unaligned`, `readmany`, `write` | `__init__`, `read`, `readmany`, `write`, `close`, `__enter__`, `__exit__` |
| absent from the fixture | | `_ioctl`, **`read_dword`**, **`read_dword_unaligned`** |
| `readmany` (in both) | yes | yes — not in the issue's table |
| `EcError` base | `RuntimeError` | `RuntimeError` |
| module-level | `block_runs`, `_int`, `main` | `block_runs`, `install` |

So the **signature** half of the claim holds: every member both files carry has
the same name and the same argument list. The **coverage** half does not, by
three names rather than one. The suite works from the measurement above, not
from the issue's table.

`ecrw.py` cannot be imported off Windows — `ctypes.WinDLL("kernel32", …)` runs
at module scope — which is the whole reason the fixture exists and the reason
this comparison has to be static. The suite therefore imports neither file:
`ast.parse` over the two sources is enough, and staying static keeps it clear of
the shared-interpreter machinery in
`tools/test_windows_tools_shared_interpreter.py` (see "Shared-file rules").

## The decision: narrow the claim, keep the fixture's member set

`_ioctl` does **not** get added, and neither do `read_dword` or
`read_dword_unaligned`. The three stay out; the "whole surface" / "whole
protocol" wording comes out of the fixture's two docstrings and out of
`tools/README.md`; and the new suite asserts the rule that replaces it:

> the fixture carries every member of `ecrw.Ec` that a tool in
> `windows/tools/` reaches, with identical signatures; the members it omits are
> exactly those no tool reaches, and that residual is named in the test.

Why, in the order that decided it.

**The fixture's own stated purpose already implies this.** `Ec`'s docstring says
the bodies exist so that an import, "or an accidentally unpatched call", does
not fail on a missing attribute. Which members an accidentally-unpatched call
can reach is exactly the question of which members the tools call — and every
member the fixture has today is one a tool calls. The three omitted ones are
called by nothing outside `ecrw.Ec` itself: measured over `windows/tools/*.py`,
the only `read_dword` / `read_dword_unaligned` calls are inside `ecrw.py`, and
the only `mmrd` command callers are `test_ecrw.py`, which loads the *real*
module behind a fake `ctypes.WinDLL`. Their absence is a consequence of the
design, not an oversight — which is exactly the thing the issue says no reader
of the diff can currently tell.

**Adding them would be a safety regression on the one path that matters.** Today
an unpatched `read_dword` on the fixture raises `AttributeError`, loudly. A
`bytes(4)`-returning body converts that into a silent four-zero answer on the
MMRD path — the path `test_ecrw.py` guards hardest, precisely because an
unaligned four-byte read over `0x0460-0x046F` is issue #94's access
(`test_the_escape_is_the_only_unaligned_mmrd_any_block_path_issues`). A fixture
that answers that silently is the wrong thing to add, so it does not go in.

**The replacement rule is strictly stronger where it bites.** "The same
surface" is a census nobody can check. "Every member a tool reaches is on the
fixture, with the same signature" fails the moment a tool grows a dword call —
and the residual is a small named allowlist with
`ec/tools/check_pin_message_names.py`'s discipline, where an entry that stops
violating must be deleted rather than left standing.

If a tool ever reaches `read_dword` or `_ioctl`, the suite goes red, and that is
the signal to add the member — at which point the decision about its body, and
about the guards, is made against a caller that exists.

## How the reached set is derived, and what that costs

The suite never lists the members it compares. It walks every `.py` directly
under `windows/tools/`, keeps those with a **module-level** `from ecrw import …
Ec`, and takes two things from each:

1. every attribute name spelled anywhere in it, and
2. the context-manager protocol, which is not spelled as an attribute at all:
   `with Ec() as ec` reaches `__enter__` and `__exit__`, and the `Ec()` inside
   it reaches `__init__`.

Intersected with `ecrw.Ec`'s own members, that is the reached set. On this tree
it is `{__init__, __enter__, __exit__, close, read, readmany, write}`, and the
residual is the three named members.

**Both rules err toward counting too much rather than too little**, and that is
deliberate rather than incidental. A member wrongly believed needed has to be on
the fixture — a cost paid once, in a docstring. A member wrongly believed
unneeded stays in `RESIDUAL` — a cost paid the moment a tool calls it, in a red
run naming the member. Rule 1 is the blunt one: `fh.read` on a file object
counts `read`, which the fixture carries anyway, because telling the handle from
every other name in a module would need a dataflow analysis nothing here has a
use for. So the residual is "no tool *spells* this", which is a weaker claim than
"no tool *calls* this" and is stated as such in the suite's own docstring.

The population is the tools, not the suites: a `test_*.py` installs the fixture
and then patches its own class over the tool, so a member it calls is not one
the fixture owes. `test_ecrw.py` is the case that would go wrong if suites were
counted — it reaches the whole dword pair, against the real module, on purpose.
The module-level-`from ecrw import` filter excludes the suites and the two files
under test for free, since neither has one.

## What the suite asserts, and the two ways it could have been decorative

Structure is a parse helper over both files, then cases. Every case names the
claim it holds and why that claim rather than a nearby one.

**Non-vacuity, first.** `Ec` parses in both files, the real class has more than
one member, the fixture's is non-empty, and the reached set is non-empty.
`tools/test_readme_suite_table.py`'s `ParseTests` and `run-tests.sh`'s
empty-glob guard exist because an empty parse against an empty discovery passes
silently; a suite asserting a *relation between two files* can pass the same
way, and `class_of` returning `None` rather than raising makes it likelier.

**The properties.** Every member of `ecrw_fake.Ec` exists on `ecrw.Ec` with an
identical signature; every member of `ecrw.Ec` a tool reaches exists on the
fixture; nothing on the fixture is outside the reached set; and the residual is
*equal* — not a superset — to the named three. `EcError`'s bases and
`block_runs`'s signature are compared as text.

**The negative control.** Five scratch copies of the two files — add a member to
the real class, drop one, re-signature one, drop one from the fixture, add one
to it — each asserted to be reported *under the key the matching case reads*.
That last part is the one worth stating. An earlier draft of this suite had the
cases and the control compute the comparison independently, which meant the
control proved a second implementation worked while the first could be broken;
they are now one `mirror_problems`, keyed by rule, and each control perturbs the
function the passing case reads. `tools/test_windows_tools_shared_interpreter.py`
is the precedent for having a control at all.

Verified by perturbing the committed files rather than by reading the code:
re-signaturing `read` in either file, dropping `readmany` from the fixture,
adding a member to either class, and dropping `write` from the real class each
turn the suite red, and each file was restored afterwards.

## Calibration on `EcError`

The issue asks for the `RuntimeError` base to be asserted so the claim that it
is load-bearing is *held rather than asserted*. The base-equality assertion is
cheap and true and is in the suite. **The justification is not, and does not go
in as stated.**

The fixture's `EcError` docstring says the base is load-bearing because
`ec_watch.py` wraps its whole run in `except EcError`, so an exception class
that were not a `RuntimeError` would change what that clause covers. Nothing in
the tree demonstrates that. Every `except EcError` in `windows/tools/` catches
the *class object* the tool bound at import, not its base — and the two broad
`except Exception` sites in `ec_watch.py` (the grader's `--label-vocab` load,
and the mark prompt's `stdin`) are nowhere near the EC. So the base is a
precaution whose necessity is **not established**: matching it keeps the two
classes substitutable and costs nothing, which is a good reason to keep it, and
not a reason to call it load-bearing.

This is §4a-4d applied to a claim the tree itself made, and it is left where it
is. The fixture's docstring is not edited to sound more certain than the tree is.

## Shared-file rules the new suite lives inside

All read from the tree by `tools/test_windows_tools_shared_interpreter.py`, so
they apply to any new `test_*.py` in `windows/tools/` automatically:

- No `sys.modules.setdefault`
  (`InstallShapeTests::test_no_suite_reaches_for_sys_modules_setdefault`).
- No line matching `sys.modules['ecrw'] =` —
  `test_a_suite_writing_the_ecrw_name_is_the_one_that_may` allows
  `{'test_ecrw'}` and nothing else.
- No line beginning `from ecrw import ` at column 0: `FakeSurfaceTests.wanted()`
  scans every `windows/tools/*.py` except the two fixtures, and would treat such
  a line as a name the fake must export.
- **Stay static.** No `import ecrw` (un-importable off Windows) and no
  `install()` call — under the one-interpreter run (`CollectionTests`), leaving
  `sys.modules['ecrw']` pointing at the fixture is state a sibling suite
  inherits. Reading through `Path(__file__).with_name(...)` also makes the suite
  correct inside `OrderingTests`' scratch mirror, which copies
  `windows/tools` wholesale and symlinks everything above it.
- Its placement in `windows/tools/` is correct here, unlike
  `tools/test_windows_tools_shared_interpreter.py`'s: that suite lives in
  `tools/` because it runs `unittest discover` over the directory it is in and
  would spawn a copy of itself once per rename. This one runs no discovery, so
  it belongs beside the file it describes.

## What was left out, and why

- **Running any of this against the driver or on Windows.** `ecrw.py` still
  cannot be imported off Windows, and the four `ValueError` guards and the
  open-failure `EcError` are only ever read here as source. Nothing in this
  change is hardware evidence and nothing in it implies a live run.
- **Giving the fixture `ValueError` guards.** The issue lists this as optional,
  and it is the wrong side to close. Copying the bounds into `ecrw_fake.py`
  would make the fixture a second implementation of `ecrw.py`, which is the one
  thing its own docstring says it is not. The guards are already pinned against
  the *real* module by four cases in `windows/tools/test_ecrw.py`
  (`test_read_outside_the_window_is_refused_before_the_ioctl`,
  `test_a_dword_start_off_the_block_grid_is_refused`,
  `test_a_range_off_the_end_of_the_window_is_refused`,
  `test_the_escape_loosens_alignment_and_not_the_window`), so "accounted for
  somewhere" is satisfied by pointing there. The hazard the issue names — a
  suite relying on the fake's silent `0x00` instead of the real refusal — is
  closed from the other end instead: the fixture has no dword path at all, so no
  silent four-zero can be reached through it.
- **`docs/findings.md` §16.** Frozen at 97 sections and
  `ec/tools/check_findings_frozen.py` enforces it; `CLAUDE.md` is explicit that
  adding a summary section is "the one edit to this file that a change is not
  allowed to make". §16's 2026-09-24 correction is the fourth restatement of the
  mirror claim ("carries `Ec` and `EcError` over the real `ecrw.py`'s whole
  surface … the fake mirrors its surface, it does not replace it"). It is left
  exactly as written. Its wording is superseded by this page's; the correction
  pattern §4a-4d asks for lives here, in a new file, which is where a
  correction belongs.
- **`windows/tools/ecrw.py`** — unchanged, per its own docstring and the note
  §16 already carries.
- **`ecrw_fake.install()`'s docstring.** "Both suites install these same two
  class objects" is a separate claim about object identity, and it is already
  held — by
  `test_the_installer_replaces_whatever_was_under_the_name` and
  `test_charge_target_test.py`'s `EcError` case. Rewording it here would be a
  drive-by edit.
- **`ec/annotations/registers.yaml`** — nothing here touches the EC, so no
  register's status moves.

## Follow-ups this opens

Recorded here rather than fixed, because each is an edit to a file several
branches touch.

- **`docs/findings/ecrw-fake-one-shape.md` states the mirror as a flat
  premise.** Its "What this does not buy" section says "the fake mirrors the
  real module's surface; it does not replace it" and never measures it. This
  change measures it; that sentence is superseded by the residual above.
- **`tools/test_windows_tools_shared_interpreter.py`'s docstring carries stale
  prose.** It says `test_gpu_block_watch.py` "currently fails four cases reading
  `registers.yaml`". Measured on this tree it passes. That file's
  `CollectionTests` deliberately does not depend on the sentence, so nothing is
  red — but it is stale prose in a shared file.
- **`gen_findings_index.py --check` has no caller in CI**, so every future
  write-up can ship a stale index silently. `docs/findings/findings-index-staleness.md`
  records both causes and says in so many words that the index is checked by
  hand, in the same commit, by whoever adds a write-up. The patch that would
  give it a caller is prepared at
  `docs/ci/agent-gates-findings-frozen.patch`; it needs a human with a
  `workflow`-scoped token, because `.github/` is template-copied and this
  branch's token cannot edit it.

## The reading this takes

The narrowest reading that is still useful: **hold the two files to each other
mechanically, and narrow the claim rather than widen the fixture.** The
alternative the issue leaves open — add `_ioctl` and the two members it missed,
and keep "whole surface" — is rejected above with a reason rather than a
preference.

What is left out is any claim about *behaviour*. The fixture's bodies are not
compared to `ecrw.py`'s, because comparing them would mean importing a module
that cannot be imported off Windows, and because behaviour is `test_ecrw.py`'s
job against a fake `ctypes.WinDLL`. The four `ValueError` guards and the
open-failure `EcError` are the visible part of that gap, and the issue is right
that they are unheld; the answer is that they are held against the real module,
which is the one whose behaviour anyone is relying on.