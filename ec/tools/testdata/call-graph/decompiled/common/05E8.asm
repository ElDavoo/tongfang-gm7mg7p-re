; common @ 05E8   FUN_CODE_05e8
; call_graph.py --self-test fixture, hand-written. See the README beside it.
; No transfer instruction in this body, deliberately: a callee's own listing
; contributing an inbound edge to something would make the site count depend
; on the callees as well as the callers.

05E8     c2 af -  clr      0xaf
05EA     00 - -   nop
05EB     00 - -   nop
05EC     00 - -   nop
05ED     00 - -   nop
05EE     22 - -   ret
