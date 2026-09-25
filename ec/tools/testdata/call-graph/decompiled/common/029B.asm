; common @ 029B   chan_arm_1708   [named]
; call_graph.py --self-test fixture, hand-written. The second 0x07D0 caller,
; which is what makes the self-test's cited_by == inbound check a real
; agreement between two framings rather than a number that happens to match.

029B     12 d0 07 lcall    0x07d0
029E     22 - -   ret
