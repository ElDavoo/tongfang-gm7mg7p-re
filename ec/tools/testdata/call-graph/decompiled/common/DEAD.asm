; common @ DEAD   FUN_CODE_dead
; call_graph.py --self-test fixture, hand-written. Nothing reaches it. It is
; here so the self-test can pin "not found by this method" against a row the
; index does carry: an absent inbound edge is a limit of the scan, not a
; function that does not exist.

DEAD     22 - -   ret
