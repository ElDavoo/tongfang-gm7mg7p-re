; pd @ 10E0   keil_product_10e0
; call_graph.py --self-test fixture, hand-written. Carries an lcall to the
; common area's 0x0CE1 and a comment below that names it, so the pair looks
; corroborated in both directions at once and the program-identity veto is the
; only thing that can refuse it. pd/10BC.asm has no transfer and so cannot
; carry this case. 0x0CE1 is its own row rather than 0x07D0 because a pd
; listing's transfer to an address the PD image has no row of its own resolves
; to the common row -- which would take 0x07D0's inbound to 3 and turn the
; fixture's own cited_by == inbound check into a disagreement. See the README
; beside it.

10E0     12 e1 0c lcall    0x0ce1
10E3     22 - -   ret
