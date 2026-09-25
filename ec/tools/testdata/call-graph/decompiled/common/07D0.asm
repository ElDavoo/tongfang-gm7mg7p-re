; common @ 07D0   FUN_CODE_07d0
; call_graph.py --self-test fixture, hand-written. Anonymous and reachable,
; which is the whole collision the frame guard is for: the same 0x07D0 is an
; XDATA byte in the comments of the other program. Reached by 0x018C and
; 0x029B, the two rows that say "calls 0x07D0".

07D0     90 d0 07 mov      DPTR, #0x07d0
07D3     e0 - -   movx     A, @DPTR
07D4     22 - -   ret
