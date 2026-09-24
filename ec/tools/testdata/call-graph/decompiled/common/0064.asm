; common @ 0064   FUN_CODE_0064
; call_graph.py --self-test fixture, hand-written. Its only job is to exist:
; the fixture's 0xEA2 comment writes "0x64" as a data value, and this row is
; what that short form would wrongly be credited to.

0064     85 82 83 mov      0x82, 0x83
0067     22 - -   ret
