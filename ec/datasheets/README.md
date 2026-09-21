# EC datasheets (reference inputs)

Third-party ITE datasheets kept as committed reference inputs, so the register
semantics this repo cites are checkable from a file rather than from memory.

## `IT5570_A_V0.3.1.pdf`

ITE IT5570 (A version) preliminary specification, V0.3.1.

- **Provenance.** Downloaded 2026-09-21 from the public Internet Archive mirror
  `https://ia800805.us.archive.org/18/items/it-5570-a-v-0.3.1-u/IT5570_A_V0.3.1_U.pdf`.
  SHA-256 `01666ebe44ece4a436b5ffaad40c9570c17f0b3480862caf224953585c59102f`,
  5,247,804 bytes, `%PDF-1.6`.
- **Why this part.** It is *not* this machine's EC — the target is an ITE
  `EC-V14.6` reporting firmware 1.18 (`docs/findings.md` §6). The IT5570 is the
  closest public sibling: same ITE 8051 EC family and, crucially, the same SMFI /
  H2RAM host-interface register file. Treat every offset as a sibling-part
  reference to be confirmed against *this* image's behaviour before it is relied
  on, exactly as `docs/related-projects.md` treats sibling boards.
- **What it was used for here.** §6.4.4.38–46 documents the Host RAM Window
  registers (`HRAMWC` 0x5A, `HRAMW0-3BA`, `HRAMW0-3AAS`) — the size / read- /
  write-protect bit semantics behind the host-write-window map decoded from this
  firmware's own init routine (bank0 `0xDBE2`–`0xDC16`). Cross-checked against
  Chromium EC `chip/it83xx/lpc.c`, which documents the same fields.
