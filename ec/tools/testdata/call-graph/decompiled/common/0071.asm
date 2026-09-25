; common @ 0071   dispatch_setup
; call_graph.py --self-test fixture, hand-written. One lcall site to each of
; the fixture's own 0x1400 and 0x1410, and a comment below whose two mentions
; fall outside the frame window. The listing is what settles them, which is
; the shape the three calls in common,0x0070 are: a real citation the bounded
; window reports as undecided, and the listing carries the transfer. See the
; README beside it.

0071     12 00 14 lcall    0x1400
0074     12 10 14 lcall    0x1410
0077     22 - -   ret
