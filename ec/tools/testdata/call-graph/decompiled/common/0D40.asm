; common @ 0D40   FUN_CODE_0d40
; call_graph.py --self-test fixture, hand-written. Reached only by the
; `sjmp` in 0D20.asm, and it makes no transfer of its own, so a
; TRANSFERS-based scan reports it as one of the anonymous rows nothing
; reaches. A comment still cites it, which is the `unranked` case report()
; counts rather than the absent one.

0D40     7e 10 -  mov      R6, #0x10
0D42     22 - -   ret
