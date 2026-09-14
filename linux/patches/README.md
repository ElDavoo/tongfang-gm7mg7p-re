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
  only) did not stop charging either — see `docs/findings.md` §4c. Whether
  it works when both `0x07B9` and `0x07D0` are written together, matching
  what Windows actually does, is still open.

The patch is still a reasonable, low-risk way to *test* the charge-limit
path (it doesn't touch `0x07D0` or claim success on its own) — just don't
read the comment as an established conclusion.
