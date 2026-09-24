; bank0 @ 1F00   FUN_CODE_1f00
; call_graph.py --self-test fixture, hand-written. Anonymous on purpose: it
; is what makes callers != named_callers checkable. See the README beside it.

1F00     12 e8 05 lcall    0x05e8
1F03     02 00 -  ajmp     0x5a43
1F05     22 - -   ret
