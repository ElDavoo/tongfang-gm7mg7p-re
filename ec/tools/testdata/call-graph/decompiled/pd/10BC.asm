; pd @ 10BC   FUN_CODE_10bc
; call_graph.py --self-test fixture, hand-written. No transfer in it, so it
; contributes no edge; it is here so the annotation row below has a listing
; and an index row of its own, and can be cited *into* the common area's
; 0x07D0 -- a citation a program-identity check has to refuse and a lexical
; one cannot. The PD image is a separate program with its own XDATA map
; (ec/annotations/registers.yaml's static-scan caveat).

10BC     90 bc 10 mov      DPTR, #0x10bc
10BF     22 - -   ret
