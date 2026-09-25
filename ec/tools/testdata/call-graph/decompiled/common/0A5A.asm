; common @ 0A5A   FUN_CODE_0a5a
; call_graph.py --self-test fixture, hand-written. Reached by 0x018C's
; lcall, and named in 0x018C's comment only as the top byte of the
; XDATA 0x0A56-0x0A5A run, so it is a real callee the comment never cites.

0A5A     90 56 0a mov      DPTR, #0x0a56
0A5D     22 - -   ret
