; common @ 018C   chan_arm_1709   [named]
; call_graph.py --self-test fixture, hand-written. See the README beside it.
; The mixed sentence lives here: this listing carries an lcall to 0x07D0 and
; one to 0x0A5A, and the annotation row below names the first as a call and
; the second only as the last byte of an XDATA run. Both addresses are real,
; reachable, anonymous functions in the fixture, so "the comment mentions a
; function" and "the comment cites a callee" are different questions.

018C     12 d0 07 lcall    0x07d0
018F     12 5a 0a lcall    0x0a5a
0192     22 - -   ret
