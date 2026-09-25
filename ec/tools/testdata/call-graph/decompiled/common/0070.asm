; common @ 0070   reset_entry   [named]
; call_graph.py --self-test fixture, hand-written. Four lcall sites in a row,
; which the annotation row below writes as one enumeration: "then calls to
; 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF". "to" is a data marker and every
; item after the first is governed by a verb four tokens and a list away, so
; this is the shape a whole-sentence data veto rejects and a windowed one does
; not. See the README beside it.

0070     12 0a 11 lcall    0x110a
0073     12 8e 15 lcall    0x158e
0076     12 75 0f lcall    0x0f75
0079     12 94 15 lcall    0x1594
007C     22 - -   ret
