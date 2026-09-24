#!/usr/bin/env python3
"""Cross-decode the instructions sdas8051 cannot re-encode.

`verify_reassembly.py` covers 45,394 of the 45,537 committed instructions by
having an assembler that never saw this firmware encode the listing back to
bytes and letting the firmware arbitrate. The remaining 143 use five forms
`sdas8051` either refuses outright or encodes differently from the 8051
manual, so no assembler reaches them and they were read by no check at all.
`docs/findings.md` 11a.

This tool closes that by asking a different question of the same bytes, with
`disasm8051.py` -- which shares no code with Ghidra's SLEIGH -- as the
answer. For every instruction `verify_reassembly.to_sdas()` declines, it
decodes the instruction from the firmware image and compares that reading to
the listing's text.

**The evidence here is weaker than the re-encode's, and the two are not
interchangeable.** The re-encode is constructive: an independent tool produces
bytes, and the image says whether they are the right ones. This is
comparative: two decoders, no code in common, read the same byte column. What
is being agreed is the *text* -- the bytes were already settled, by
`verify_reassembly.check_listing_bytes()`, which covers all 45,537 and needs
no assembler. So a `disagree` here is a text error with a known-correct
answer, and an `agree` is two decoders having said the same thing about bytes
that are not in question. A listing whose bytes are right and whose mnemonic
is wrong passes the byte check and is exactly what this tool is for.

**Nothing here makes the 1:1 claim 100%.** It stays 45,394 of 45,537
(99.69%), because `sdas8051` still cannot express these five forms and no tool
has changed that. What changes is coverage: every instruction in the committed
listing is now read by an independent check, and this is the check for the
last 0.31%.

**The set is recomputed, never transcribed.** It is whatever
`to_sdas()` declines over a fresh walk of every listing, so it cannot drift
from the `instructions_unchecked` column of `ghidra/reassembly.csv` that
`verify_reassembly.py` writes. Every declined instruction also records *which*
predicate declined it, and an instruction declined for a reason with no
cross-decode handler fails the run rather than being skipped: a sixth form
must not join the set silently. That is the failure of `docs/findings.md` 11
turned into a check.

`--report` writes `ghidra/gap-text-check.csv` and is the only thing that does.
Unlike `reassembly.csv`, regenerating it *is* a verification rather than a
re-arming -- `--report` re-derives every `disasm_text` from the current bytes
and the current `disasm8051.py` tables, so a listing edit or a decoder-table
edit cross-checks the new text rather than pinning whatever it now says. It
still needs no assembler, unlike `--report` next door.

Usage:
    python3 ec/tools/verify_gap_text.py --report     # write gap-text-check.csv
    python3 ec/tools/verify_gap_text.py --check      # no assembler
    python3 ec/tools/verify_gap_text.py --self-test  # known answers
"""
import argparse
import csv
import os
import re
import sys
import tempfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disasm8051 as D                                        # noqa: E402
import verify_reassembly as V                                 # noqa: E402

REPO = V.REPO
REPORT = os.path.join(REPO, "ec", "ghidra", "gap-text-check.csv")

COLUMNS = ["program", "row_addr", "row_name", "insn_addr", "bytes",
           "ghidra_text", "disasm_text", "ghidra_canonical", "disasm_canonical",
           "reason", "verdict"]

# Known answers, measured on this export with sdas8051
# 05.50.4+NoICE+SDCCmods-WIP-R14, and asserted in --self-test. They are stated
# here rather than read out of the committed CSV, because an oracle derived
# from the thing it is testing asserts nothing -- see the note in
# verify_reassembly.self_test(). A listing edit that moves any of them fails
# --self-test rather than quietly re-basing the claim.
EXPECT_INSTRUCTIONS = 143
EXPECT_ROWS = 84
EXPECT_PARTIAL = 73
EXPECT_ASSEMBLER_GAP = 11
EXPECT_FORMS = 5
EXPECT_CHECKED = 45394

# Operands the 8051 manual gives as `bit` addresses, as opcode -> the operand
# positions that are one. Needed so a bit operand can be canonicalised to the
# number it encodes: disasm8051 prints `0xd5` as `psw.5` and Ghidra prints the
# same bit as `0xd5`, and the canonical form has to be the number or the two
# can never agree. The discriminator is the opcode, never the operand text --
# `clr 0x8e` is both CLR direct and CLR bit depending on the byte in front of
# it, and a text matcher has to guess (verify_reassembly.BIT_UNSUPPORTED says
# the same thing about the assembler side).
BIT_OPERANDS = {
    0x10: (0,), 0x20: (0,), 0x30: (0,),                    # JBC / JB / JNB
    0x82: (1,), 0x92: (0,), 0xA0: (1,), 0xA2: (1,),        # ANL C,bit / MOV bit,C
    0xB0: (1,), 0xB2: (0,),                                # ORL C,/bit / CPL bit
    0xC1: (0,), 0xD2: (0,),                                # CLR bit / SETB bit
}

# `direct` operands the manual gives that verify_reassembly.DIRECT_OPERANDS
# does not list, because to_sdas only consults its table for forms it can
# otherwise express and these are excluded before it gets that far. The
# canonicaliser needs them anyway: the single `djnz A, 0xa581` in the gap set
# is DJNZ direct,rel, and `A` is how Ghidra renders direct 0xE0.
DIRECT_EXTRA = {
    0xA6: (1,), 0xA7: (1,),                                 # MOV @Ri,direct
    0xB5: (1,),                                             # CJNE A,direct,rel
    0xD5: (0,),                                             # DJNZ direct,rel
}

# Ghidra renders a direct address by substituting the SFR it belongs to, and
# disasm8051 never does, so `djnz A, 0xa581` and `djnz 0xe0,0xa581` are the
# same instruction written two ways. Reusing disasm8051.BIT_SFR for the eleven
# names that are both bit bases and SFRs, and adding the four that are not in
# it. `A` and `B` are the spellings this set actually contains; 0xE0 is left
# reachable under both `a` and `acc` because Ghidra uses the first and r2 the
# second.
SFR_BY_NAME = {name: addr for addr, name in D.BIT_SFR.items()}
SFR_BY_NAME.update({"a": 0xE0, "b": 0xF0, "sp": 0x81, "dpl": 0x82, "dph": 0x83})

# The bit bases by name, which is the direction bit_token() reads: a printed
# `psw.5` has to resolve back to the address 0xD0 it came from. Taken from
# disasm8051's table rather than transcribed, so a change there is a change here
# and not a second list to drift.
BIT_BASE = {name: addr for addr, name in D.BIT_SFR.items()}


def bit_token(token):
    """The bit address a disasm8051 `bit_name()` token encodes, or None.

    The two ranges fold differently and getting that wrong is silent, so it is
    the one arithmetic in this file that gets a self-test of its own. Above
    0x80 the printed base is already a bit address and the digit is an offset
    from it: `psw.5` is 0xD0 + 5 = 0xD5. Below 0x80 it is a *byte* address
    and the digit selects within it, so the base has to be scaled: `0x25.3` is
    (0x25 - 0x20) * 8 + 3 = 0x2B. Folding them the same way would resolve half
    the bit operands to an address no instruction has.
    """
    t = token.strip().lower()
    if re.fullmatch(r"0x[0-9a-f]{1,2}", t):
        return int(t, 16)
    m = re.fullmatch(r"([0-9a-z]+)\.([0-7])", t)
    if not m:
        return None
    head, digit = m.group(1), int(m.group(2))
    if head.startswith("0x"):
        base = int(head, 16)
    elif head in BIT_BASE:
        base = BIT_BASE[head]
    else:
        return None
    return base + digit if base >= 0x80 else (base - 0x20) * 8 + digit


def sfr_token(token):
    """The direct address a Ghidra SFR name encodes, or None.

    Only valid for a `direct` operand. Naming an SFR where a *bit* is expected
    is a different mistake and does not come through here -- a bit operand
    always prints with its digit, and `bit_token()` is the one that reads it.
    """
    return SFR_BY_NAME.get(token.strip().lower())


def canonical(mnem, ops, opcode):
    """`mnemonic op0|op1|...` with the two decoders' spellings of one
    instruction reduced to a common form.

    Folded: case, whitespace, the space after a comma, a bit operand's
    rendering (`psw.5` == `0xd5` == `acc.4`) and a direct operand's (`A` ==
    `0xe0`). None of those is a difference in what the instruction does.

    Not folded: the mnemonic itself, the bit number, the direct byte, the
    immediate, a register, and a branch's absolute target. Those are the
    instruction. A canonicaliser that folded the mnemonic would report
    `cpl 0xd5` against `cpl 0xe4` as an agreement, which is the one thing this
    check must never do -- `--self-test` asserts that pair is a disagreement.

    An operand whose class is unknown is kept as its own lower-cased token
    rather than guessed at, so a form this table has not been taught to fold
    shows up as a disagreement and gets looked at.
    """
    bit_at = set(BIT_OPERANDS.get(opcode, ()))
    direct_at = set(V.DIRECT_OPERANDS.get(opcode, ())) | set(DIRECT_EXTRA.get(opcode, ()))
    out = []
    for i, tok in enumerate(_operand_list(ops)):
        low = tok.strip().lower()
        # The carry is a flag, not an address, and the two decoders spell it
        # differently (`CY` against `c`).
        if low in ("cy", "c"):
            out.append("c")
            continue
        if i in bit_at:
            # A bit operand never falls through to the direct case: the opcode
            # says which it is, and re-reading it as the other one is how a
            # disagreement gets turned into an agreement.
            v = bit_token(tok)
            out.append(low if v is None else "0x%02x" % v)
            continue
        if i in direct_at:
            if re.fullmatch(r"0x[0-9a-f]+", low):
                out.append(low)
                continue
            v = sfr_token(tok)
            if v is not None:
                out.append("0x%02x" % v)
                continue
        out.append(low)
    return (mnem.strip().lower() + " " + "|".join(out)).strip()


def _operand_list(ops):
    """Operand tokens, split on commas, the way verify_reassembly does it.

    disasm8051 separates with bare commas and Ghidra with comma-space, so the
    split has to be on the comma alone and the space folded afterwards, or the
    two disagree on formatting before either is read.
    """
    return [o for o in re.split(r"\s*,\s*", ops.strip()) if o] if ops.strip() else []


def split_text(text):
    """`mnemonic rest` -> (mnemonic, operands)."""
    head, _, tail = text.strip().partition(" ")
    return head.strip(), tail.strip()


def why(mnem, ops, pc, size, opcode, hexbytes):
    """Which predicate in `to_sdas()` declined this instruction, or None.

    Checked in the order `to_sdas()` applies them, and for the same reasons --
    `GAP_FORMS` before `GAP_MNEMONICS`, the opcode before the operand text. The
    set of instructions is `to_sdas()`'s to decide; this only names the reason,
    so the two cannot disagree about *which* instructions. A `None` here means
    `to_sdas()` returned None and nothing in its source explains why, which is
    a form this file has not been taught to cross-decode: the caller fails
    rather than recording a set it cannot explain.
    """
    key = re.sub(r"\s*,\s*", ",", ("%s %s" % (mnem, ops)).lower())
    for gap in sorted(V.GAP_FORMS):
        if key.startswith(gap):
            return 'GAP_FORMS "%s"' % gap
    if mnem in V.GAP_MNEMONICS:
        return "GAP_MNEMONICS %s" % mnem
    if opcode is not None and opcode in V.BIT_UNSUPPORTED:
        return "BIT_UNSUPPORTED 0x%02X" % opcode
    if mnem == "a" and not ops.strip():
        return "reserved `da A`"
    parts = _operand_list(ops)
    if mnem == "cjne" and parts and parts[0].lower().startswith("0x"):
        return "CJNE direct operand"
    if mnem in V.RELATIVE_BRANCH and pc is not None and parts:
        try:
            rel = int(parts[-1], 16) - (pc + size)
        except ValueError:
            return None
        if not -128 <= rel <= 127:
            return "branch displacement out of range"
    return None


def verdict_of(ghidra_text, disasm_text, opcode):
    """`agree`, `disagree` or `undecodable`.

    A `db` on *either* side is `undecodable`, never `agree`. disasm8051's
    mnemonic table is partial by design -- anything it does not know prints as
    `db` -- so a comparison against one could only match vacuously, and
    counting that as agreement is how a hole would read as coverage. The 19
    `mov <bit>,CY` in this set were exactly that before `disasm8051.py` grew a
    case for 0x92.
    """
    g_mnem, g_ops = split_text(ghidra_text)
    d_mnem, d_ops = split_text(disasm_text)
    if g_mnem == "db" or d_mnem == "db":
        return "undecodable"
    if canonical(g_mnem, g_ops, opcode) == canonical(d_mnem, d_ops, opcode):
        return "agree"
    return "disagree"


def load_images():
    """{program: bytes} for the three flat bank images, rebuilt if absent.

    Cached where `verify_reassembly.check_listing_bytes()` caches them, so the
    two tools share one build rather than each shelling out to
    make_bank_image.py. Address == image offset for all three programs, which
    is what make_bank_image.py arranges and why nothing here does address
    arithmetic of its own.
    """
    paths = {p: os.path.join(V.IMAGE_DIR, p + ".bin")
             for p in ("bank0", "bank1", "pd")}
    if not all(os.path.isfile(p) for p in paths.values()):
        V.build_images(V.IMAGE_DIR)
    return {p: open(path, "rb").read() for p, path in paths.items()}


def cross_listing(row, image, path=None):
    """Cross-decode one listing's instructions that `to_sdas()` declines.

    Returns (rows, unclassified, parsed, unchecked). Split out of `collect()`
    so `--self-test` can drive the *same* path on a synthetic listing: the
    point of the check is that the decoder's side comes from the image bytes
    and not from the listing's text, and an assertion that builds its own
    `verdict_of()` call cannot tell a regression in that line from a
    regression in the code the line is supposed to be.
    """
    path = path or os.path.join(V.DECOMPILED, row["out_file"])
    rows, unclassified = [], []
    parsed = unchecked = 0
    for addr, hexbytes, mnem, ops in V.parse_listing(path):
        parsed += 1
        opcode = int(hexbytes[:2], 16) if len(hexbytes) >= 2 else None
        if V.to_sdas(mnem, ops, pc=addr, size=len(hexbytes) // 2,
                     opcode=opcode, hexbytes=hexbytes) is not None:
            continue
        unchecked += 1
        reason = why(mnem, ops, addr, len(hexbytes) // 2, opcode, hexbytes)
        if reason is None:
            unclassified.append((row["program"], row["addr"], addr,
                                 hexbytes, mnem, ops))
            continue
        want = bytes.fromhex(hexbytes) if hexbytes.isalnum() else b""
        ghidra_text = ("%s %s" % (mnem, ops)).strip()
        if addr + len(want) > len(image):
            # Out of the image, so there is nothing to decode and no honest
            # verdict. Said rather than guessed.
            disasm_text, verdict = "", "undecodable"
        else:
            # From the image at the instruction's own runtime address, never
            # from the listing's text. A decode taken from the text would
            # agree with it by construction, which is the one thing this
            # whole file exists not to do.
            disasm_text = D.mnemonic(image, addr, addr)
            verdict = verdict_of(ghidra_text, disasm_text, opcode)
        rows.append({
            "program": row["program"],
            "row_addr": row["addr"],
            "row_name": row["name"],
            "insn_addr": "%04X" % addr,
            "bytes": hexbytes.lower(),
            "ghidra_text": ghidra_text,
            "disasm_text": disasm_text,
            "ghidra_canonical": canonical(mnem, ops, opcode),
            "disasm_canonical": canonical(*split_text(disasm_text), opcode)
            if disasm_text else "",
            "reason": reason,
            "verdict": verdict,
        })
    return rows, unclassified, parsed, unchecked


def collect(images=None):
    """Walk every listing and cross-decode what `to_sdas()` declines.

    Returns (rows, unclassified, totals). `rows` is one dict per unchecked
    instruction, keyed by program|row_addr|insn_addr. `unclassified` is the
    list of instructions no reason explains, and a non-empty one is a failure
    rather than a footnote. `totals` carries the instruction census, which
    `--self-test` compares against known answers.
    """
    images = images if images is not None else load_images()
    rows, unclassified = [], []
    parsed = unchecked = 0
    for row in csv.DictReader(open(V.LISTING_INDEX, newline="")):
        rel = row["out_file"]
        if not rel or rel.startswith("("):
            continue
        path = os.path.join(V.DECOMPILED, rel)
        if not os.path.isfile(path):
            continue
        # `common` is an export grouping rather than a fourth image, so it
        # reads against bank 0 -- the same fallback verify_reassembly uses,
        # and the reason nothing here needs address arithmetic of its own.
        image = images.get(row["program"]) or images["bank0"]
        got, unclassified_here, n_parsed, n_unchecked = cross_listing(row, image, path)
        rows += got
        unclassified += unclassified_here
        parsed += n_parsed
        unchecked += n_unchecked
    keys = {(r["program"], r["row_addr"], r["insn_addr"]) for r in rows}
    return rows, unclassified, {
        "parsed": parsed,
        "unchecked": unchecked,
        "checked": parsed - unchecked,
        "rows": len({(r["program"], r["row_addr"]) for r in rows}),
        "keys": len(keys),
        "forms": len({r["reason"] for r in rows}),
    }


def report(rows, path=REPORT):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def key(r):
    return "%s|%s|%s" % (r["program"], r["row_addr"], r["insn_addr"])


def check():
    """No assembler: the committed CSV still describes the live set, and every
    verdict in it still recomputes from the current bytes and tables.

    Four things, and the first two are what keep it from being a staleness
    check that only notices edits. Every live unchecked instruction has a row
    and every row has a live instruction, so the set cannot drift in either
    direction. Each row's bytes are compared against both the listing's byte
    column and the firmware image -- the same comparison
    `verify_reassembly.check_listing_bytes()` makes, reused rather than
    restated. Each row's `ghidra_text` is compared against the listing's
    current text and its `disasm_text` and both canonical forms are recomputed,
    so editing a listing *or* a `disasm8051.py` table leaves no stale verdict.
    And the recomputed totals have to equal the CSV's own.
    """
    ok = True
    images = load_images()
    rows, unclassified, totals = collect(images)
    for prog, row_addr, addr, hexbytes, mnem, ops in unclassified:
        print("  FAIL %s %s at %04X (%s %s) is declined by to_sdas() and no "
              "reason here explains it.\n"
              "       A new form cannot be cross-decodeable by default. Teach "
              "why() and the\n"
              "       canonicaliser the form, and say why in the self-test; do "
              "not skip it." % (prog, row_addr, addr, mnem, ops))
    if unclassified:
        return 1
    if not os.path.isfile(REPORT):
        print("  FAIL no gap-text report at %s; run verify_gap_text.py --report"
              % os.path.relpath(REPORT, REPO))
        return 1
    committed = list(csv.DictReader(open(REPORT, newline="")))
    live = {key(r): r for r in rows}
    have = {key(r): r for r in committed}

    for k in sorted(set(live) - set(have)):
        print("  FAIL %s is unchecked now but has no row in %s"
              % (k, os.path.relpath(REPORT, REPO)))
        ok = False
    for k in sorted(set(have) - set(live)):
        print("  FAIL %s is in %s but is not unchecked now: the report is stale"
              % (k, os.path.relpath(REPORT, REPO)))
        ok = False
    for k in sorted(set(live) & set(have)):
        for col in COLUMNS:
            if live[k][col] != have[k].get(col, ""):
                print("  FAIL %s %s: report says %r, the live recompute is %r"
                      % (k, col, have[k].get(col, ""), live[k][col]))
                ok = False

    # The bytes themselves, against the image and not only against the
    # listing. collect() already decodes from the image, so a listing whose
    # byte column had drifted would arrive here as a verdict disagreement --
    # but a disagreement names a *canonical form*, which is a derived thing to
    # read, and this names the byte. Same comparison
    # verify_reassembly.check_listing_bytes() makes over all 45,537, run over
    # the 143 for the same reason the whole tool exists: these are the ones no
    # other check reaches.
    byte_checked = 0
    for r in rows:
        want = bytes.fromhex(r["bytes"]) if r["bytes"].isalnum() else b""
        if not want:
            continue
        byte_checked += 1
        image = images.get(r["program"]) or images["bank0"]
        addr = int(r["insn_addr"], 16)
        got = image[addr:addr + len(want)]
        if got != want:
            print("  FAIL %s %s at %s: the listing says %s, the firmware has %s"
                  % (r["program"], r["row_addr"], r["insn_addr"],
                     want.hex(), got.hex()))
            ok = False
    print("  gap text bytes: %d instruction(s) compared against the firmware"
          % byte_checked)
    print("  gap text: %d instruction(s) in %d row(s), %d form(s), "
          "%d checked by re-encode" % (totals["unchecked"], totals["rows"],
                                       totals["forms"], totals["checked"]))
    tally = Counter(r["verdict"] for r in rows)
    print("  gap text verdicts: %s"
          % (", ".join("%d %s" % (v, k) for k, v in sorted(tally.items())) or "none"))
    for r in rows:
        if r["verdict"] != "agree":
            print("  %-12s %s %s at %s: listing `%s`, disasm8051 `%s` "
                  "(canonical `%s` against `%s`)"
                  % (r["verdict"].upper(), r["program"], r["row_addr"],
                     r["insn_addr"], r["ghidra_text"], r["disasm_text"],
                     r["ghidra_canonical"], r["disasm_canonical"]))
    if totals["unchecked"] != len(committed):
        print("  FAIL %d unchecked live, %d row(s) in the report"
              % (totals["unchecked"], len(committed)))
        ok = False
    print("  all checks passed" if ok else "  FAILURES ABOVE")
    return 0 if ok else 1


def self_test():
    """Known answers, so a change to the folding or the comparison cannot
    quietly start passing everything.

    Every oracle here is stated from the 8051 manual or from a transcription of
    the firmware, never recorded from this tool. A self-test that derives its
    oracle from the tool it is testing asserts nothing, which is what the
    digest assertions in verify_reassembly.self_test() say about themselves.
    """
    ok = True

    def assert_that(cond, what):
        nonlocal ok
        print("  %s %s" % ("ok  " if cond else "FAIL", what))
        ok = ok and bool(cond)

    # bit_token's two ranges, which fold differently. From the 8051 manual's
    # bit-addressing rule: a bit above 0x80 is bit n of the SFR at 0xD0, a bit
    # below it is bit n of internal RAM 0x20-0x2F.
    assert_that(bit_token("psw.5") == 0xD5, "an SFR bit name resolves: psw.5 = 0xd5")
    assert_that(bit_token("acc.4") == 0xE4, "and again: acc.4 = 0xe4")
    assert_that(bit_token("p3.4") == 0xB4, "and again: p3.4 = 0xb4")
    assert_that(bit_token("0x25.3") == 0x2B,
                "an internal-RAM bit name resolves, and scales rather than "
                "offsets: 0x25.3 = 0x2b")
    assert_that(bit_token("0xd0.5") == 0xD5,
                "the >= 0x80 form offsets rather than scales: 0xd0.5 = 0xd5")
    assert_that(bit_token("0x20.7") == 0x07,
                "the base prints as a byte address, so 0x20.7 is bit 7 of "
                "internal RAM 0x20 -- that is, 0x07")
    assert_that(bit_token("0x24.7") == 0x27,
                "and one byte along is 0x24.7 = 0x27")
    assert_that(bit_token("tcon") is None and bit_token("nonsense.9") is None,
                "a token that is not a bit address resolves to None rather than "
                "to a guess")

    # The five forms' canonical encodings, stated as the manual's.
    assert_that(canonical("mov", "0xd5, CY", 0x92) == canonical("mov", "psw.5,c", 0x92),
                "`mov 0xd5,CY` and `mov psw.5,c` are one instruction")
    assert_that(canonical("cpl", "0xd5", 0xB2) == canonical("cpl", "psw.5", 0xB2),
                "`cpl 0xd5` and `cpl psw.5` are one instruction")
    assert_that(canonical("cpl", "0x2b", 0xB2) == canonical("cpl", "0x25.3", 0xB2),
                "`cpl 0x2b` and `cpl 0x25.3` are one instruction")
    assert_that(canonical("cpl", "0xb4", 0xB2) == canonical("cpl", "p3.4", 0xB2),
                "`cpl 0xb4` and `cpl p3.4` are one instruction")
    # The one djnz of the set. Ghidra writes the accumulator where disasm8051
    # writes the address; the firmware arbitrates the target, and both decoders
    # agree it is 0xa581.
    assert_that(canonical("djnz", "A, 0xa581", 0xD5) == "djnz 0xe0|0xa581",
                "`djnz A, 0xa581` canonicalises to the direct byte 0xe0")
    assert_that(canonical("djnz", "0xe0, 0xa581", 0xD5) == "djnz 0xe0|0xa581",
                "and disasm8051's own rendering of it is the same form")
    # The AJMP page rule, at the site verify_reassembly cites: 0x8044 & 0xF800
    # = 0x8000, 0x81 & 0xE0 = 0x80 -> 0x8400, | 0x5D.
    assert_that(D.paged_target(0x81, 0x5D, 0x8044) == 0x845D,
                "`81 5d` at 0x8044 is ajmp 0x845d by the manual's page rule")
    assert_that(canonical("ajmp", "0x845d", 0x81) == canonical("ajmp", "0x845d", 0x81)
                == "ajmp 0x845d", "and both decoders spell that target alike")

    # The comparisons that keep the canonicaliser from folding everything into
    # "both are cpl". Each is a *text* difference with no byte behind it, so
    # the verdict is decided by the canonical form and nothing else can decide
    # it -- which is why they are the interesting cases.
    assert_that(verdict_of("cpl 0xd5", "cpl psw.5", 0xB2) == "agree",
                "a rendering difference is an agreement")
    assert_that(verdict_of("mov 0xd5, CY", "mov psw.5,c", 0x92) == "agree",
                "and so is one carrying the carry under both spellings")
    assert_that(verdict_of("cpl 0xd5", "cpl 0xe4", 0xB2) == "disagree",
                "the same mnemonic with a different bit is a disagreement")
    assert_that(verdict_of("ajmp 0x845d", "ajmp 0x845e", 0x81) == "disagree",
                "a one-digit branch target difference is a disagreement")
    assert_that(verdict_of("cpl 0xd5", "setb psw.5", 0xB2) == "disagree",
                "a different mnemonic is a disagreement")
    assert_that(verdict_of("db 0x92", "mov psw.5,c", 0x92) == "undecodable",
                "a db on the listing side is undecodable, never an agreement")
    assert_that(verdict_of("mov 0xd5, CY", "db 0x92", 0x92) == "undecodable",
                "and a db on the decoder side is too -- this is the 19 `mov "
                "<bit>,CY` of the set before 0x92 had a case in disasm8051.py, "
                "and counting it as agreement would have been a hole reading "
                "as coverage")

    # A corrupted byte column must be reported, through the same path
    # `collect()` uses. `92 d4` is `mov psw.4,c`, so a listing that reads it as
    # `mov 0xd5, CY` disagrees with the firmware, and the correction is
    # named: the byte says 0xd4. Asserted on a synthetic listing precisely
    # because a self-test that called verdict_of() itself would not notice
    # `collect()` had stopped reading the image.
    img = bytearray(0x100)
    img[0x40:0x42] = b"\x92\xd4"
    row = {"program": "bank0", "addr": "0040", "name": "synthetic",
           "out_file": "verify_gap_text.selftest.asm"}
    fd, spath = tempfile.mkstemp(prefix="gap-selftest-", suffix=".asm")
    with os.fdopen(fd, "w") as f:
        f.write("0040  92 d4 -     mov   0xd5, CY\n")
    try:
        got, _unc, _p, _u = cross_listing(row, bytes(img), spath)
        assert_that(len(got) == 1 and got[0]["verdict"] == "disagree",
                    "a byte column that contradicts its own text is a "
                    "disagreement, read through the path --check uses")
        assert_that(got[0]["disasm_canonical"] == "mov 0xd4|c",
                    "and the disagreement names the byte that is actually "
                    "there (%s)" % got[0]["disasm_canonical"])
        with open(spath, "w") as f:
            f.write("0040  92 d4 -     mov   0xd4, CY\n")
        got, _unc, _p, _u = cross_listing(row, bytes(img), spath)
        assert_that(got[0]["verdict"] == "agree",
                    "and the same listing with the text the bytes support agrees")
    finally:
        os.remove(spath)
    # A reason with no handler must be reported, not skipped. A relative branch
    # with a symbolic target is the live example: to_sdas() declines it --
    # `int(target, 16)` raises, and it returns None rather than emitting a
    # plausible-looking line -- while nothing in why()'s list explains why,
    # because it is a listing this firmware does not contain today. That is
    # what a sixth form looks like from here, and it has to fail the run
    # rather than join the 143 with a verdict nobody computed.
    img2 = bytearray(0x100)
    img2[0x40:0x42] = b"\x80\x0a"
    fd, spath2 = tempfile.mkstemp(prefix="gap-selftest2-", suffix=".asm")
    with os.fdopen(fd, "w") as f:
        f.write("0040  80 0a -     sjmp  label\n")
    try:
        _got, unc, _p, _u = cross_listing(row, bytes(img2), spath2)
        assert_that(len(unc) == 1 and unc[0][5] == "label",
                    "an exclusion no reason explains is reported as "
                    "unclassified rather than given a verdict (%d reported)"
                    % len(unc))
    finally:
        os.remove(spath2)
    assert_that(why("sjmp", "label", 0x0040, 2, 0x80, "800a") is None,
                "and why() declines to invent a reason for it")
    # And the decoder's side is a rendering of the same instruction, not a copy
    # of the listing's: the 32 bit-form instructions in the live set come out
    # spelled `psw.5` against Ghidra's `0xd5`, and a decode taken from the text
    # could not do that.
    live, _unc, _t = collect()
    differing = [r for r in live if r["disasm_text"] != r["ghidra_text"]]
    assert_that(len(differing) >= 32,
                "%d of the %d decode to text that differs from the listing's "
                "spelling, so the two sides are not one side twice"
                % (len(differing), len(live)))

    # A reason with no handler has to be reported, not skipped.
    assert_that(why("mov", "0xd5, CY", 0x9287, 2, 0x92, "92d5")
                == "BIT_UNSUPPORTED 0x92", "0x92 names the opcode that declined it")
    assert_that(why("ajmp", "0x845d", 0x8044, 2, 0x81, "815d") == "GAP_MNEMONICS ajmp",
                "ajmp names the mnemonic set that declined it")
    assert_that(why("djnz", "A, 0xa581", 0xA599, 3, 0xD5, "d5e0e5")
                == 'GAP_FORMS "djnz a,"', "djnz a names the form prefix")
    assert_that(why("mov", "0xd5, CY", 0x9287, 2, 0x92, "92d5") is not None,
                "and why() naming a reason is what keeps an unexplained "
                "exclusion from joining the set silently")
    assert_that(why("nop", "", 0x0040, 1, 0x00, "00") is None,
                "an instruction to_sdas() accepts has no reason to report")

    # The live census, against the known answers. If a listing edit moves any
    # of these, --self-test fails rather than the claim quietly re-basing.
    rows, unclassified, totals = collect()
    assert_that(not unclassified,
                "every instruction to_sdas() declines has a reason this tool "
                "can name (%d unexplained)" % len(unclassified))
    assert_that(totals["unchecked"] == EXPECT_INSTRUCTIONS,
                "%d unchecked instructions, measured" % totals["unchecked"])
    assert_that(totals["checked"] == EXPECT_CHECKED,
                "%d checked by re-encode" % totals["checked"])
    assert_that(totals["parsed"] == EXPECT_CHECKED + EXPECT_INSTRUCTIONS,
                "and the two together are the whole instruction stream (%d)"
                % totals["parsed"])
    assert_that(totals["rows"] == EXPECT_ROWS,
                "%d rows carry at least one of them" % totals["rows"])
    assert_that(totals["keys"] == EXPECT_INSTRUCTIONS,
                "and every one of the %d sits at its own program|addr|insn "
                "key, so --check's join cannot lose a row" % totals["keys"])
    assert_that(totals["forms"] == EXPECT_FORMS,
                "%d forms, not the seven the prose used to name" % totals["forms"])
    tally = Counter(r["verdict"] for r in rows)
    assert_that(tally.get("undecodable", 0) == 0,
                "no instruction is undecodable (%d)" % tally.get("undecodable", 0))
    assert_that(tally.get("disagree", 0) == 0,
                "no instruction disagrees (%d)" % tally.get("disagree", 0))

    # The 73/11 split, which the committed reassembly report carries and which
    # the prose used to leave out: 11 of the 58 assembler-gap rows carry
    # unchecked instructions too.
    outcomes = {}
    for r in rows:
        outcomes.setdefault(r["program"] + "|" + r["row_addr"], None)
    for r in csv.DictReader(open(V.REPORT, newline="")):
        k = r["program"] + "|" + r["addr"]
        if k in outcomes:
            outcomes[k] = r["outcome"]
    split = {}
    for v in outcomes.values():
        split[v] = split.get(v, 0) + 1
    assert_that(split.get("partial", 0) == EXPECT_PARTIAL,
                "%d of the rows are `partial`" % split.get("partial", 0))
    assert_that(split.get("assembler-gap", 0) == EXPECT_ASSEMBLER_GAP,
                "%d are `assembler-gap` and also carry unchecked instructions"
                % split.get("assembler-gap", 0))
    assert_that(sum(split.values()) == EXPECT_ROWS,
                "and the two together are the %d rows" % EXPECT_ROWS)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", action="store_true",
                    help="write ec/ghidra/gap-text-check.csv (no assembler)")
    ap.add_argument("--check", action="store_true",
                    help="CI: the committed report still describes the live "
                         "set and every verdict recomputes (no assembler)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.check:
        return check()
    rows, unclassified, totals = collect()
    for prog, row_addr, addr, hexbytes, mnem, ops in unclassified:
        print("  FAIL %s %s at %04X (%s %s): to_sdas() declines it and why() "
              "has no reason, so it cannot be cross-decodeable yet"
              % (prog, row_addr, addr, mnem, ops))
    if unclassified:
        return 1
    tally = Counter(r["verdict"] for r in rows)
    print("  gap text: %d instruction(s) in %d row(s) across %d form(s); "
          "%d checked by re-encode"
          % (totals["unchecked"], totals["rows"], totals["forms"],
             totals["checked"]))
    for reason, n in sorted(Counter(r["reason"] for r in rows).items()):
        print("    %-28s %d" % (reason, n))
    print("  verdicts: %s" % (", ".join("%d %s" % (v, k)
                                       for k, v in sorted(tally.items())) or "none"))
    if args.report:
        print("\n  wrote %s" % os.path.relpath(report(rows), REPO))
    return 1 if tally.get("disagree", 0) else 0


if __name__ == "__main__":
    sys.exit(main() or 0)
