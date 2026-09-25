; bank1 @ F6A0   FUN_CODE_f6a0
; call_graph.py --self-test fixture, hand-written. An unbroken 0xFF run:
; `mov R7, A` repeated to the end of the function, which is what a fill region
; disassembles to and what makes it unable to make the call its comment names.
; Seven bank1 listings in the committed tree have this shape; the address here
; is deliberately not one of them, so the assertion pins the shape rather than
; the seven addresses. See the README beside it.

F6A0     ff - -   mov      R7, A
F6A1     ff - -   mov      R7, A
F6A2     ff - -   mov      R7, A
F6A3     ff - -   mov      R7, A
