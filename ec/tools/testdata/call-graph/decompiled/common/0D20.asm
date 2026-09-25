; common @ 0D20   wait_then_jump_0d40
; call_graph.py --self-test fixture, hand-written. Its only job is to carry
; the `sjmp` that TRANSFERS above does not scan: the graph counts no edge to
; 0x0D40 from here, while the comment on this row reads the verb and credits
; the citation. The two sets being different sets is the point.

0D20     90 07 24 mov      DPTR, #0x724
0D23     e0 - -   movx     A, @DPTR
0D25     70 19 -  jnz      0x0d40
0D27     80 17 -  sjmp     0x0d40
0D29     22 - -   ret
