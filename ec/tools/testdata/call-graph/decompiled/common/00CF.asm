; common @ 00CF   table_walker_00cf   [named]
; call_graph.py --self-test fixture, hand-written. Reached by a single ljmp
; and no lcall at all -- the case a lcall-only scan calls unreachable. Named
; so the self-test can pin that a named callee keeps its row and its inbound
; count when a tranche annotation renames it.

00CF     90 6f 39 mov      DPTR, #0x6f39
00D2     e0 - -   movx     A, @DPTR
00D3     22 - -   ret
