#!/usr/bin/env python3
"""Decide whether a comment's `0x` + 4-hex-digit mention names a *code* address
or a *data* byte, and whether a comment may cite a function in another program.

`call_graph.py` credits a comment's canonical-width address to the callee row it
resolves to. On this firmware that is wrong often enough to matter, because the
same 4-digit token is both a function entry and an XDATA byte: 0x07D0 is
`FUN_CODE_07d0` in the index and `DBD1` in `registers.yaml`, and a comment
saying "stores the caller's byte at XDATA 0x07D0" names the byte. The
canonical-width rule in `call_graph.py` stops the *short* form (`0x64`, which
is overwhelmingly a data value) and does nothing about a 4-digit one, so the
ranking's top rows were XDATA.

**The frame test is lexical, and it is a guard on a number, not a parser.** It
reads a bounded window around the mention, not the comment: a code frame is
*necessary* and a data frame is a *veto*, and anything neither settles is
returned as `undecided` so `call_graph.py` can report it instead of quietly
keeping it. A purely syntactic veto is not sufficient on its own either -- the
list form "calls to 0x110A, 0x158E, 0x0F75, 0x1594 and 0x00CF" carries a data
marker ("to") and is a genuine citation of all five -- so the window is walked
rather than pattern-matched against the sentence.

**What it will get wrong, stated first.** It is a bag of words. A comment that
reaches a call target through two or more ordinary nouns ("the borrow chain
over 0x08CD") reads as undecided, not as a call; a comment that says "the
0x07D0 sites" reads as data, which is right for the PD image's own 0x07D0 sites
and would be wrong for a call to a function that happens to be reached 8 times.
Both failures shrink or grow a *count*, and the populations they move are
printed by `call_graph.py` rather than dropped. The frame is never allowed to
invent a citation the comment does not make: `undecided` is a third answer, not
a synonym for `code`.

**Program identity is the other half, and it is not lexical.** The 256 KiB dump
holds two 8051 programs: the EC firmware and, at file 0x20000, a separate
ITE8850-PD image with its own vectors and its own XDATA map
(`ec/annotations/registers.yaml`'s own `static-scan` caveat, and
`build_ec_decompile.py` refusing an EC XDATA name on a `pd` row). A comment
annotated against a `pd` listing therefore cannot cite a `common` or `bank` row
at the same address -- the two 0x07D0s are one byte in each program, and
`Index.resolve` hands the PD comment the EC row only because the PD image has
no row of its own there. The reverse is not decidable this way and must not be:
a `bank0`/`bank1` comment citing a `common` row is legitimate, because a
common-area function is exported once and reached from both banks (the `Index`
docstring in `call_graph.py` encodes exactly that). Cross-bank citations
therefore fall to the frame test alone.

Usage:
    from citation_frames import classify, program_reason
    classify(comment, span).verdict        # 'code' | 'data' | 'undecided'
    program_reason('pd', 'common')         # 'cross-program' | ''
"""
import collections
import re

CODE = "code"
DATA = "data"
UNDECIDED = "undecided"

VERDICTS = (CODE, DATA, UNDECIDED)

# A code frame: the mention is what a verb does, not what a verb does to it.
# `jmp`, `jump`, `jumps` and `jumping` are four entries because `jmps?` does
# not match "jumps" -- the `u` is missing from the pattern, not from the
# comments -- and a lexicon that silently fails to match costs a citation.
CODE_VERB = re.compile(r"""^(?:
      call | calls | called | calling
    | lcall | lcalls | ljmp | ljmps | ajmp | acall
    | jmp | jump | jumps | jumping
    | tail-?call(?:s|ing)? | tail-?jump(?:s|ing)?
    | branch(?:es)? | reach(?:es|ed)? | poll(?:s|ed)?
    | invoke(?:s|d)? | dispatch(?:es)?
    | enter(?:s|ed)? | re-?enter(?:s|ed)? | hand(?:s)? | run(?:s)?
    | execute(?:s|d)? | fall(?:s)? | continue(?:s|d)?
    | entry | callee | callers? | routines? | handlers? | functions?
)$""", re.VERBOSE | re.IGNORECASE)

# A data frame. Split in two only so the report can name which half matched:
# a marker is a noun the address is ("the byte at 0x1606"), a verb is something
# done to it ("stores 0x0F at 0x0A5A"). `pair`/`pairs` are deliberately absent
# -- "the callee pairs 0x4AB8/0x4A69" is a code list, and listing them here
# would reject two real citations to protect none.
DATA_VERB = re.compile(r"""^(?:
      write | writes | wrote | store | stores | stored
    | set | sets | clear | clears | cleared | clearing
    | zero | zeroes | zeros | zeroing
    | read | reads | load | loads | loaded
    | reload | reloads | reloading | reloading
    | copy | copies | copied | move | moves | moved
    | point | points | pointed | increment | increments
    | decrement | decrements | test | tests | tested
    | compare | compares | compared | against | swap | swaps | xor | masked
)$""", re.VERBOSE | re.IGNORECASE)

DATA_MARKER = re.compile(r"""^(?:
      xdata | xdata_ | dptr | dpl | dph | iram | sfr | ram | direct
    | byte | bytes | bit | bits | word | words | half
    | block | field | fields | register | registers
    | counter | counters | value | values
    | divisor | divisors | index | indices | stride | mask | masks
    | limit | limits | count | slot | slots
    | argument | arguments | buffer | array | arrays | table | pointer
    | flag | flags | address | addresses | data
)$""", re.VERBOSE | re.IGNORECASE)
# `entry` is in CODE_VERB and deliberately not here: "the six ljmp 0xF040
# entries" is a code target, and one committed comment writes exactly that.

# The right-hand veto, read as the one word immediately after the mention and
# nothing else. Keeping it that tight is the point: "calls 0xDFA0 with that
# 16-bit pair" must survive it, so the window may not skip a word. Of this list
# the committed comments actually exercise `sites`, `block` and `divisor`; the
# rest are the obvious members of the same family, and a list this short is
# cheap to extend when a case shows up.
DATA_RIGHT = re.compile(r"""^(?:
      site | sites | byte | bytes | bit | bits | block | blocks
    | field | fields | pair | register | registers
    | value | values | counter | counters | word | words
    | divisor | index
)$""", re.VERBOSE | re.IGNORECASE)

# Transparent: they carry no frame, and a list ("calls 0xA, 0xB and 0xC")
# walks straight through them to the verb that governs the whole list. A bare
# number is in here for the same reason -- "reached by 8 of the 0x07D0 sites".
CONNECTIVE = re.compile(r"""^(?:
      to | into | through | from | at | in | on | with | of | about
    | the | a | an | that | which | what | whether | when | while | if
    | is | are | was | were | its | their | it | they | them
    | and | or | then | also | next | followed | by
    | first | last | only | before | after | again | once | per
    | but | so | nor | than | there | here | else | instead | both
    | each | every | any | all | up | down | out | over | inside | across
    | past | still | now | never | always | not | no | unlike | non-zero
)$""", re.VERBOSE | re.IGNORECASE)

# Clause boundaries: a sentence end and nothing else. `--` is deliberately not
# one, because the comments use it to introduce a list ("it calls six routines
# -- 0x14C8, 0x012F, 0x018C"), and cutting there lost the one list the measured
# tree has whose head is on the far side. The prose an aside usually wraps is
# stopped by the filler budget instead, which is the bound that was measured.
BOUNDARY = re.compile(r"[;.]\s")

# A token that is structure rather than prose: another address in the same
# list, a pair's other half, a range's other end, the `0x` in a listing
# operand, the index of an `XDATA[...]` subscript. The trailing punctuation is
# part of the token because "calls to 0x110A, 0x158E, 0x0F75" writes it there,
# and a hex run that did not match would be charged to the filler budget and
# stop the walk two items into a list it is supposed to be walking.
STRUCTURAL = re.compile(
    r"^(?:0[xX][0-9A-Fa-f]{1,4}[.,;:()\[\]/+-]*"
    r"|[.,;:()\[\]/+#-]|[-+]?[0-9]+)$")

# Punctuation the comments glue to a word rather than spacing out.
GLUE = re.compile(r"[,;#()\[\]/]")

# How many non-connective, non-structural words may sit between the mention and
# the verb that frames it. One, and the number is measured rather than guessed.
# Widening the window to 2 over the committed comments credits **no new
# citation** and converts 7 unsettled pairs into rejections, 6 of which name
# code addresses -- "then 0x1E1A twice", "the same bytes as ACALLs to 0xD673",
# "returns zero, and it is byte-identical to the exits at 0xE7B8" -- because the
# data word the walk reaches into describes something other than the address.
# The first new credits arrive at 3, by which point 9 of the new rejections are
# wrong. A wrong rejection is worse than an unsettled pair: one becomes a fact
# in a census, the other stays a line in a report asking for a human to read
# the sentence.
FILLER_BUDGET = 1

Frame = collections.namedtuple("Frame", "verdict reason")

# (callee, citer, reasons) for a candidate the guard did not credit, plus the
# frame verdicts its mentions drew. `verdicts` carries a default so a caller
# that only reads the reason strings -- `rejected_rows`, `reason_counts`, the
# unit tests -- can keep constructing the three-argument form. It is carried
# because the reasons alone cannot answer the question the program-identity
# sentence in `call_graph.py` asks: a `cross-program` pair that also lists a
# data marker may still have had a mention the frame test called `code`, and
# those are the pairs the program veto decided that no lexicon reaches.
Candidate = collections.namedtuple(
    "Candidate", "callee citer reasons verdicts", defaults=((),))


def _token_word(token):
    """The token as a word: trailing clause punctuation and a possessive `s`
    off, so `copies` and `image's` both reach a lexicon entry. Only a real
    apostrophe is stripped -- `rstrip("'s")` also eats the `s` of `copies`."""
    return re.sub(r"'s$", "", token.strip(".,;:()[]"))


def _clause_before(comment, start):
    """The text between the last clause boundary and the mention."""
    left = comment[:start]
    cut = 0
    for m in BOUNDARY.finditer(left):
        cut = m.end()
    return left[cut:]


def _walk_left(comment, start):
    """The nearest code or data frame to the left of the mention, or `None`.

    Walks back over the list the mention sits in -- other addresses,
    `and`/`or`/`then`, commas -- and stops at the first verb that carries a
    frame. Running out of clause first is a `None`, not a `DATA`: a comment can
    name a code address with no verb anywhere near it ("the next entry,
    0xE6F4"), and guessing either way there is how a count gets corrupted
    quietly.
    """
    clause = _clause_before(comment, start)
    # The listing operands glue their punctuation to the word -- "MOV
    # DPTR,#0x08CE" is one whitespace token -- so the glue is split off first.
    # Without that, "DPTR" never reaches the lexicon and the mention is
    # undecided, which is the quiet direction: a data frame that goes missing
    # credits a byte.
    tokens = [part for token in clause.split()
              for part in GLUE.split(token) if part]
    filler = 0
    for token in reversed(tokens):
        if STRUCTURAL.fullmatch(token):
            continue
        word = _token_word(token)
        if CODE_VERB.match(word):
            return Frame(CODE, "code-verb:" + word.lower())
        if DATA_VERB.match(word) or DATA_MARKER.match(word):
            return Frame(DATA, "data-marker:" + word.lower())
        if CONNECTIVE.match(word):
            continue
        filler += 1
        if filler > FILLER_BUDGET:
            return None
    return None


def _word_after(comment, end):
    """The one word immediately after the mention, or `''`."""
    tail = comment[end:]
    tail = tail.lstrip()
    cut = len(tail)
    for ch in " \t\n,;.()":
        found = tail.find(ch)
        if found != -1:
            cut = min(cut, found)
    return _token_word(tail[:cut])


def classify(comment, span):
    """`Frame` for one mention: a code frame, a data frame, or `undecided`.

    `span` is the mention itself -- a `re.Match` or any `(start, end)` pair.
    The data veto is evaluated first because it is the one that has to hold: a
    mention can be governed by a code verb and still be data, which is what
    "reached by 8 of the 0x07D0 sites" is (the `sites` are the PD image's own
    bytes being handed to the helper, not calls to it).
    """
    start, end = (span.start(), span.end()) if hasattr(span, "start") else span
    right = _word_after(comment, end)
    if right and DATA_RIGHT.match(right):
        return Frame(DATA, "data-noun:" + right.lower())
    left = _walk_left(comment, start)
    if left is not None:
        return left
    return Frame(UNDECIDED, "no-frame-in-window")


def program_reason(citing_scope, callee_program):
    """`'cross-program'` when a comment cannot cite the row it resolved to.

    Only the one direction is decidable. A `pd` comment reads a `pd` listing and
    a `common`/`bank` row at the same address belongs to a different program;
    a `common` function is genuinely shared by both bank programs, so a bank
    comment citing one is correct and is left to the frame test.
    """
    if citing_scope == "pd" and callee_program != "pd":
        return "cross-program"
    return ""


def rejected_rows(candidates, limit=0):
    """`candidates` as report lines, largest callee first.

    Reported rather than dropped, following `audit_call_targets.py`: a guard
    that silently discards what it rejects cannot be told apart from a guard
    that rejects too much. Each line carries the reason, so a reader who
    disagrees with one call can see which pattern made it.
    """
    counts = collections.Counter(c.callee for c in candidates)
    ordered = sorted(candidates,
                     key=lambda c: (-counts[c.callee], c.callee, c.citer))
    if limit:
        ordered = ordered[:limit]
    return ["  %s,%s cited by %s:%s -- %s"
            % (c.callee[0], c.callee[1], c.citer[0], c.citer[1],
               "+".join(c.reasons))
            for c in ordered]


def reason_counts(candidates):
    """How many candidates each reason took part in, over `candidates`.

    One candidate can carry two (`cross-program` and a data frame agree), so
    the counts are per reason and do not sum to the population.
    """
    counts = collections.Counter()
    for c in candidates:
        for reason in c.reasons:
            counts[reason] += 1
    return counts
