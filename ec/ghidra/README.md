# Ghidra project — placeholder

Not started. Ghidra's SLEIGH processor spec for 8051/8052 exists upstream
(`Ghidra/Processors/8051`) but has no native concept of Keil BL51 bank
switching — the bank-switch stubs in `../annotations/` and the offsets from
`../tools/find_banks.py` would need to become a Ghidra memory-map / overlay
configuration (one overlay block per bank, common area shared) before
auto-analysis produces anything better than what `r2 -a 8051` already gives
per-bank.

If you pick this up: start from `../tools/make_bank_image.py`'s output per
bank, import each as a separate program, and manually cross-link via the
symbol names in `../annotations/registers.yaml` rather than trying to model
the bank switching itself in Ghidra first.
