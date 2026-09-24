; common @ 0EE8   FUN_CODE_0ee8
; call_graph.py --self-test fixture, hand-written. See the README beside it.

0EE8     90 8d -  mov      DPTR, #0x8d
0EEB     74 fd -  mov      A, #0xfd
0EED     f0 - -   movx     @DPTR, A
0EEE     a4 - -   mul      AB
0EEF     f0 - -   movx     @DPTR, A
0EF0     d2 8c -  setb     0x8c
0EF2     22 - -   ret
