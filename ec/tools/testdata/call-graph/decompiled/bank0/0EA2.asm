; bank0 @ 0EA2   delay_calls_0ee8   [named]
; call_graph.py --self-test fixture, hand-written. Not generated: see
; ec/tools/testdata/call-graph/README.md. The byte encodings are the real
; 8051 ones for the site address and the printed target, so the fixture's
; listings are assemblable even though the bytes around them are not firmware.

0EA2     12 e8 0e lcall    0x0ee8
0EA5     12 e8 05 lcall    0x05e8
0EA8     02 15 -  ajmp     0x5a43
0EAB     02 cf 00 ljmp     0x00cf
0EAE     22 - -   ret
