# uniwill-laptop-force_charge_limit.patch

Applied against upstream `Wer-Wolf/uniwill-laptop` commit in `BASE_COMMIT`.
Adds a `force_charge_limit` module parameter so `force=1` can expose
`UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` (the numeric `charge_control_end_threshold`,
EC `0x07B9`) instead of `UNIWILL_FEATURE_BATTERY_CHARGE_MODES` (the three-preset
`charge_types`, EC `0x07A6`) for boards where the modes turn out not to be
the useful interface.

**The patch's own comment is now known to overstate its conclusion — left
unedited below deliberately, corrected here instead, per this repo's policy
of keeping wrong conclusions visible with their correction rather than
quietly editing them out (see `../../docs/findings.md`).** It says:

> so the charge modes are inert and the charge limit is the only working
> interface

Both halves turned out to be wrong as stated:

- The charge modes are **not inert** — `docs/findings.md` §4b shows they do
  change the current-taper curve near 100%, just not a hard stop. "Inert"
  was based on a batch test that couldn't attribute cause correctly.
- The charge limit was **not confirmed working** at the time this comment
  was written, and the one live test of it (threshold=80, upper register
  only) did not stop charging either — see `docs/findings.md` §4c. The paired
  write this left open has since been run: `docs/findings.md` §4f wrote
  `0x07B9` and `0x07D0` at the physical address Windows' own `ECRW` path lands
  on — the first attempt `0x07B9` alone, then the pair, from above the cap and
  armed from below it, with the 60/55 write repeated under each of the three
  `0x07A6` profiles — and charging never stopped. §4k then closed the service
  side from decrypted source: the two methods that would write the pair are
  private with no caller, so on Control Center Service 3.1.39.0 nothing writes
  them at all. The limit is not a working interface on this firmware.

The patch is still a reasonable, low-risk way to *test* the charge-limit
path (it doesn't touch `0x07D0` or claim success on its own) — just don't
read the comment as an established conclusion.

## What to claim upstream, and how to word it

[`gm7mg7p-charge-features.md`](gm7mg7p-charge-features.md) is the note to read
before writing the descriptor for #10: which feature bits this board should
claim, why `UNIWILL_FEATURE_BATTERY_CHARGE_LIMIT` should not be one of them
(with the commands that reproduce each line), what `charge_types` actually
does — a floor on a per-cell voltage derating, not a percentage cap — and a
drafted PR description to lift.

[`gm7mg7p-ec-register-names.md`](gm7mg7p-ec-register-names.md) is the other
half of #10: the two places where `uniwill-laptop`'s own register *names*
disagree with the DSDT and the vendor service, what this tree can and cannot
show about each, and the question text to put to a maintainer. It ships no
patch, and `docs/findings.md` §7's "New questions" bullet is the record behind
both of them.
