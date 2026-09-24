#!/usr/bin/env python3
"""Grade every `name_basis` cell in the two annotation CSVs, and --check them.

A function name in this repository asserts a *mechanism*: `delay_polling_0a56`
says the routine waits on something at 0x0A56, `tr51_bank_select_1` says a
toolchain stub does the selecting. Before `name_basis` existed, nothing
recorded **what the assertion rests on**, so a name decoded from a register
map read exactly like a name guessed from instruction shape. Issue #135's
worked example is the case that made it matter: bank0 0x0EA2's own comment
contradicted its own name for a while (`docs/findings.md` §20).

**The rule is deliberately asymmetric: the strongest footing actually
traceable to a committed input, else `code-shape`.** The default points at
the weak end on purpose. Grading by name-regex would overclaim -- a name
containing `write` is not thereby grounded in a register map -- and grading
the other way would under-claim, which is its own inaccuracy. So this reads
the bytes, not the name: the footing is whatever the row's own committed
`.asm` shows.

Vocabulary (closed; `ec/annotations/README.md` carries the prose):

  register-map   a decoded SFR/bit identity -- 0x8E is TCON.6 = TR1. Checkable
                 against disasm8051.bit_name() and BIT_SFR.
  ec-register    an XDATA address in registers.yaml carrying a decoded name.
  abi-symbol     a toolchain or ABI symbol rather than the bytes -- the BL51
                 bank-select stubs, EDK II protocol/GUID names. The token has
                 to be in the NAME; a comment's mention of one is a claim
                 about the comment.
  code-shape     only the instruction sequence's shape.
  mixed          the name asserts two things with different footing.
  unresolved     the row is `type: unresolved` and the name is a placeholder.

**What this cannot do, and it is the first thing to say.** A `.c` is one
reading of the bytes and this reads the `.asm`, but neither is a *behavioural*
observation. A row graded `code-shape` is not thereby a wrong name; it is a
name that has been asked to carry no more than the instructions state. And
per CLAUDE.md the whole column is static: a register read back, or named
here, says the code touches a byte -- not that the EC acts on it. No
hardware is reachable from a GitHub-hosted runner, and none of this claims
otherwise.

`--check` re-grades and fails on a disagreement, so the committed column and
the rule cannot drift. `--self-test` pins the vocabulary, the `pd` refusal and
the four cross-field rules on fixture rows, because a grader that has quietly
started accepting everything looks exactly like a grader that is working.

Usage:
    python3 ec/tools/grade_name_basis.py --report
    python3 ec/tools/grade_name_basis.py --apply
    python3 ec/tools/grade_name_basis.py --check
    python3 ec/tools/grade_name_basis.py --self-test
"""
import argparse
import collections
import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)

from disasm8051 import BIT_SFR, bit_name  # noqa: E402

EC_CSV = os.path.join(REPO, "ec", "annotations", "ghidra-functions.csv")
BIOS_CSV = os.path.join(REPO, "bios", "annotations", "ghidra-functions.csv")
REGISTERS_YAML = os.path.join(REPO, "ec", "annotations", "registers.yaml")

# The closed vocabulary, and the order --report prints a distribution in. The
# order is strongest footing first, so a reader scanning the table sees the
# grades that assert the most before the default.
VOCABULARY = ("register-map", "ec-register", "abi-symbol", "mixed",
              "code-shape", "unresolved")

# Scope of the separate ITE8850-PD program. Its XDATA map is its own, so a
# `MOV DPTR,#0x07E2` there is not a reference to the EC register at 0x07E2
# (ec/README.md, ec/annotations/lightbar-bat-flow.md §2). This is the third
# lock on that door, after gen_xdata_symbols.py never emitting pd rows and
# ApplyAnnotations.java refusing to apply one.
PD_SCOPE = "pd"

# `<addr> <bytes> <mnemonic> <operands>`, where each byte column is two hex
# digits or a `-` for a byte the listing does not carry. Anchored on the
# address so a comment line cannot be read as an instruction, and greedy on
# the byte columns so the mnemonic is the first token that is not one.
LISTING = re.compile(r"^\s*([0-9A-Fa-f]{4,8})\s+"
                     r"((?:[0-9a-f]{2}|-)(?:\s+(?:[0-9a-f]{2}|-)){1,5})\s+"
                     r"(\S+)\s*(.*?)\s*$")

# A hex address as it appears in a snake_case name: a whole `_`-delimited
# token, optionally `0x`-prefixed. Whole-token is the point -- `dec` and
# `add` are mnemonics that happen to be valid hex, and matching them would
# invent addresses that are not there. `0x`-prefixed tokens are allowed to
# carry the same 2-4 digits, so `send_0x12_via_f078` and `store_0x14_at_0810`
# parse the same way.
NAME_TOKEN = re.compile(r"^(?:0x)?([0-9a-fA-F]{2,4})$")

# The PC-relative and absolute branch forms whose operand is a target address
# rather than a data operand. A 4-hex operand on one of these is a CODE
# address, which is what keeps a banked call target out of the XDATA set.
BRANCHES = frozenset((
    "lcall", "ljmp", "sjmp", "acall", "ajmp",
    "jc", "jnc", "jz", "jnz", "jb", "jnb", "jbc", "djnz", "cjne",
))

# `mov DPTR,#0xNNNN` is the only 8051 form that puts a 16-bit XDATA address
# into a register, so it is the one that resolves an XDATA citation.
# Case-insensitive because the listing spells the register `DPTR` and the
# operand `0x`, and a case-sensitive pattern matches neither -- which is
# silent, and reads as a column of `ec-register=0` rather than as a bug.
DPTR_IMM = re.compile(r"dptr\s*,\s*#0x([0-9a-fA-F]+)", re.I)

# The toolchain stub names Ghidra recovers for the Keil BL51 bank-select
# trampolines, and the EDK II type/protocol vocabulary the BIOS rows assert.
# Both are symbols the *toolchain* supplies, not the bytes: a name resting on
# one is making a claim about a linker or a calling convention, which is a
# different kind of footing from a register map and is graded as such.
#
# Matched against the **name only**, and that restriction is the rule rather
# than a simplification of it. This column grades what the mechanism *the
# name asserts* rests on, so a token that appears only in the comment is a
# claim about the comment, not about the name: `load_dptr_88f0_tail_jump_1114`
# describes two instructions, and a comment noting the BL51 stub at 0x1114
# does not turn the name into an ABI citation. Grading on the comment would
# also make the grade unfalsifiable, the same objection rule 4 is written
# against -- a prose comment almost always mentions a toolchain somewhere, so
# nearly every row would pick up an `abi-symbol` footing and the column would
# stop distinguishing anything. Measured before this was tightened, 101 of
# 105 `abi-symbol`/`mixed` rows carried their token in the comment alone and
# four in the name (the `bl51_bank_select_N` stubs).
BL51 = re.compile(r"\bbl51_[a-z0-9_]+\b", re.I)
EDK = re.compile(r"\b(EFI_[A-Z0-9_]+|g[A-Z][A-Za-z0-9]*Guid|"
                 r"g[A-Z][A-Za-z0-9]*Protocol[A-Za-z0-9]*)\b")

# 8051 bit and SFR identities a name may assert *in words* rather than by
# address. `timer1_counted_delay_using_0a56` never writes 0x8E, but it says
# "timer1", and that word is a claim about TCON.6 = TR1 -- the decoded
# identity issue #135's worked example turns on, and the reason a
# name-address-only rule would grade it `code-shape` and lose the thing the
# row exists to record.
#
# Each entry is (token, bit address it names), matched against the name's
# `_`-delimited tokens rather than the raw string: a name is snake_case, so
# `timer1` is one token and `\btimer\s*1\b` never matches it.
#
# The match is still corroborated. The listing has to show that address as an
# SFR operand, so a name asserting a timer the bytes never reference gets no
# register-map footing, which is the point.
SFR_WORDS = (
    ("timer1", 0x8E),      # TCON.6 = TR1
    ("tr1", 0x8E),
    ("tf1", 0x8F),         # TCON.7 = TF1
    ("timer0", 0x89),      # TCON.5 = TR0
    ("tr0", 0x89),
    ("tf0", 0x8A),         # TCON.5 = TF0
    ("et1", 0xAB),         # IE.3
    ("et0", 0xA9),         # IE.1
    ("ex1", 0xAC),         # IE.2
    ("ex0", 0xAA),         # IE.0
    ("ea", 0xAF),          # IE.6, the global enable
    ("tcon", 0x88),
    ("acc", 0xE0),
    ("psw", 0xD0),
)


def name_tokens(name):
    """A name's `_`-delimited tokens, lowercased. The unit the address
    patterns and the SFR-word list both match on."""
    return [t.lower() for t in re.split(r"[^A-Za-z0-9]+", name or "") if t]


def sfr_word_cites(name, sfr):
    """Does the name assert a decoded SFR identity *in words*, over a listing
    that shows the bit it names?

    A name may say `timer1` where the listing says `clr 0x8E`. Both are the
    same claim about TCON.6 = TR1, and grading the first as `code-shape`
    because it lacks a hex literal would throw away the decode rather than
    record it. The corroboration is what keeps this honest: the bit has to be
    one the listing actually touches, so a name asserting a timer the bytes
    never reference gets nothing."""
    tokens = set(name_tokens(name))
    return any(word in tokens and bit in sfr for word, bit in SFR_WORDS)


def read_csv(path):
    """Rows of a committed CSV, read strictly.

    `strict=True` because a bad quote ends a row early and every count taken
    from it is then quietly smaller than the file -- the same reason
    build_ec_decompile.py and bios_extract.py read their own this way."""
    with open(path, newline="") as f:
        return list(csv.DictReader(f, strict=True))


def register_addresses(repo=REPO):
    """{address: name} from registers.yaml, across both addr spellings.

    `addr` is a list on the entries that cover a register block
    (`LIGHTBAR_AC_CTRL / RED / GREEN / BLUE` is four bytes), and a plain
    integer elsewhere, so both are read. A name in the resulting map is the
    decode a citation rests on; a value in it is what makes the citation
    `ec-register` rather than a bare address."""
    import yaml

    data = yaml.safe_load(open(os.path.join(repo, "ec", "annotations",
                                            "registers.yaml")))
    out = {}
    for entry in data.get("registers", []):
        addrs = entry["addr"]
        if not isinstance(addrs, list):
            addrs = [addrs]
        for a in addrs:
            if isinstance(a, str):
                a = int(a, 0) if a.startswith("0x") else int(a, 16)
            out[a] = entry["name"]
    return out


def listing_facts(path):
    """What one committed `.asm` shows: SFR bit operands, XDATA addresses,
    CODE branch targets.

    Three sets, because the three are the three things a name can cite and
    they are not interchangeable -- the whole `pd` trap is that a `MOV
    DPTR,#0x07E2` in the PD image is not the EC's 0x07E2. A bit operand is
    0x80-0xFF in a BIT_SFR block; `bit_name()` returning a bare `0xNN.k`
    spelling is not a decode, and is not treated as one here either."""
    sfr, xdata, code = set(), set(), set()
    try:
        text = open(path, errors="replace")
    except OSError:
        return sfr, xdata, code
    with text:
        for line in text:
            if line.lstrip().startswith(";") or not line.strip():
                continue
            m = LISTING.match(line)
            if not m:
                continue
            mnemonic, operands = m.group(3).lower(), m.group(4)
            imm = DPTR_IMM.search(operands)
            if mnemonic == "mov" and imm:
                xdata.add(int(imm.group(1), 16))
                continue
            if mnemonic in BRANCHES:
                target = re.search(r"0x([0-9a-fA-F]{4})", operands)
                if target:
                    code.add(int(target.group(1), 16))
                continue
            for bit in re.finditer(r"0x([0-9a-fA-F]{2})(?![0-9a-fA-F])",
                                   operands):
                value = int(bit.group(1), 16)
                # `bit_name` decodes only inside a BIT_SFR block; a 0xNN.k
                # fallback spelling is the absence of a decode, and counting
                # it as one is how a column that claims a register map ends
                # up asserting one the architecture does not have.
                if bit_name(value) and BIT_SFR.get(value & 0xF8):
                    sfr.add(value)
    return sfr, xdata, code


def name_addresses(name):
    """{address: digit count} for the hex tokens a name cites.

    The digit count is kept because it is what separates the two readings of
    a 2-digit token: `0x8E` is a bit address, while `0x0A` is a small
    immediate. Both are 2 hex digits, and the caller's own `.asm` is what
    decides which one a row meant."""
    out = {}
    for token in name.split("_"):
        m = NAME_TOKEN.match(token)
        if m:
            digits = m.group(1)
            out.setdefault(int(digits, 16), len(digits))
    return out


def grade(row, registers, asm_path=None):
    """The `name_basis` for one annotation row.

    Strongest traceable footing first, `code-shape` otherwise:

      1. `unresolved`  -- `type: unresolved` AND a placeholder name. Both
         halves matter: an `unresolved` row whose name still says something
         true of the bytes (`set_dptr_0a51`) is not a placeholder, and
         grading it `unresolved` would discard a real reading.
      2. `register-map` -- the name cites a bit address the listing shows as
         an SFR bit and `bit_name()` decodes.
      3. `ec-register`  -- the name cites an XDATA address that is in
         registers.yaml, and the listing shows that address in a DPTR
         immediate. Refused outright for a `pd`-scoped row.
      4. `abi-symbol`   -- the name rests on a BL51 stub or an EDK II
         type/protocol symbol. The token has to be in the **name**; a
         comment mentioning one grades this row on what the name says.
      5. `mixed`        -- two of the above with different footing.
      6. `code-shape`   -- everything else, which is the default and the
         point.
    """
    name = (row.get("name") or "").strip()
    if (row.get("type", "").strip() == "unresolved"
            and PLACEHOLDER.fullmatch(name)):
        return "unresolved"

    sfr, xdata, code = listing_facts(asm_path) if asm_path else (set(), set(), set())
    cited = name_addresses(name)

    footing = set()
    if any(v in sfr for v in cited) or sfr_word_cites(name, sfr):
        footing.add("register-map")
    if row.get("scope", "").strip() != PD_SCOPE:
        # Both halves, and the order matters. The address has to be one the
        # listing loads into DPTR -- otherwise 0x0EA2 in a name is a *code*
        # address and grading it from registers.yaml would be a category
        # error -- and it has to be in registers.yaml, or the name is
        # asserting a decoded register that does not exist in the map.
        if any(v in xdata and v in registers for v in cited):
            footing.add("ec-register")
    # The name only, never the comment: the grade is about the mechanism the
    # name asserts, and a comment's `EFI_*` or `bl51_` token is a claim about
    # the comment. See the note on BL51 above.
    if BL51.search(name) or EDK.search(name):
        footing.add("abi-symbol")

    if len(footing) == 1:
        return footing.pop()
    if len(footing) > 1:
        return "mixed"
    return "code-shape"


# Names that assert nothing, so an `unresolved` row carrying one has nothing
# to grade. A `type: unresolved` row whose name still describes the bytes
# (`set_dptr_0a51`, `clr_cy`) is not one of these, and is graded on what it
# does say -- downgrading those to `unresolved` would discard a real reading,
# which is the under-claiming failure this column exists to prevent.
#
# Every form here is an admission that the row names no mechanism: `ret` and
# `nop` say the body is a bare control transfer or a padding byte, and
# `not_a_function` / `filler` / `disassembled_as_code` say the bytes are not
# a function at all. Whole-token anchored, so `ret_stub` matches and
# `store_ret_value` does not.
PLACEHOLDER = re.compile(
    r"(?:"
    r"unresolved(?:_[0-9a-z]+)*"          # unresolved_b38d, unresolved_midstream_bytes
    r"|ret(?:_[0-9a-z]+)*"               # ret_stub, ret_only_cb1e, ret_terminating_89f4
    r"|empty(?:_[0-9a-z]+)*"              # empty_ret_stub, empty_stub_return_zero
    r"|nop(?:_[0-9a-z]+)*"               # nop_stub_c333, nop_no_control_transfer
    r"|bare(?:_[0-9a-z]+)*"              # bare_ret_9040
    r"|[0-9a-z_]*ff_filler[0-9a-z_]*"    # ff_filler_not_a_function_f566
    r"|table_bytes_disassembled_as_code[0-9a-z_]*"
    r"|entry"
    r")")


def asm_for(row, repo=REPO):
    """The row's committed `.asm`, from the first `.asm` path in its evidence.

    The `.asm` first is the repo's evidence convention (the machine code is
    the ground truth and the `.c` is one reading of it), so a row that cites
    a `.c` before an `.asm` still resolves to the bytes. Returns None when
    the row cites no `.asm` -- 67 EC rows cite only prose -- and the grade
    then rests on the name and comment alone, which is why the vocabulary
    points at the weak end."""
    for path in (row.get("evidence") or "").split(";"):
        path = path.strip()
        if path.endswith(".asm"):
            full = os.path.join(repo, path)
            if os.path.isfile(full):
                return full
    return None


def grade_all(repo=REPO):
    """{path: [rows]} graded, in file order.

    Each row carries the computed grade under `name_basis` and the cell the
    CSV actually holds under `committed_name_basis`. The two keys have to be
    separate, and that is the whole reason this function is not a one-liner:
    an earlier version read the CSV, wrote the computed grade straight over
    `name_basis`, and then had `check()` compare that field with itself. The
    drift half of `--check` compared a value with the value it had just
    overwritten it with, so it could never fire -- hand-editing a committed
    grade passed, which is the one thing a re-grading check exists to stop,
    and the failure was silent in the exact way this repository keeps warning
    about. `apply()` writes back the CSV's own fieldnames, so the extra key
    never reaches the file.
    """
    registers = register_addresses(repo)
    out = {}
    for path in (os.path.join(repo, "ec", "annotations", "ghidra-functions.csv"),
                 os.path.join(repo, "bios", "annotations", "ghidra-functions.csv")):
        rows = read_csv(path)
        for row in rows:
            row["committed_name_basis"] = (row.get("name_basis") or "").strip()
            row["name_basis"] = grade(row, registers, asm_for(row, repo))
        out[path] = rows
    return out


# --- the four cross-field rules -----------------------------------------
# Each returns a list of problem strings, empty when the rule holds. Kept as
# four named functions rather than one predicate so a reader can see which
# rule refuses which row, and so build_ec_decompile.py and bios_extract.py
# can call the same code the grader was tested against.

def check_vocabulary(row):
    """Rule 1: non-empty, and in the closed list."""
    value = (row.get("name_basis") or "").strip()
    if not value:
        return ["has an empty name_basis: a name asserts a mechanism, and "
                "nothing here records what that assertion rests on"]
    if value not in VOCABULARY:
        return ["name_basis %r is outside the closed vocabulary (%s)"
                % (value, ", ".join(VOCABULARY))]
    return []


def check_ec_register(row, registers):
    """Rule 2: an `ec-register` row must cite an address in registers.yaml."""
    if (row.get("name_basis") or "").strip() != "ec-register":
        return []
    cited = name_addresses(row.get("name") or "")
    text = (row.get("name") or "") + " " + (row.get("comment") or "")
    for value in cited:
        if value in registers:
            return []
    # A comment citation counts too: the rule is about the claim being
    # traceable, and a name can be short while its comment carries the
    # address the mechanism is really about.
    for value in re.findall(r"0x([0-9a-fA-F]{2,4})", text):
        if int(value, 16) in registers:
            return []
    return ["is graded ec-register but cites no address in registers.yaml, so "
            "it claims register footing the map does not give it"]


def check_pd(row):
    """Rule 3: a `pd`-scoped row may not be graded `ec-register`.

    The PD image is a separate 8051 program with its own XDATA map, so
    borrowing an EC register name there is a first-class overclaim however
    well the address matches."""
    if row.get("scope", "").strip() != PD_SCOPE:
        return []
    if (row.get("name_basis") or "").strip() == "ec-register":
        return ["is a pd-scoped row graded ec-register; the PD image has its "
                "own XDATA map, so an address there is not an EC register"]
    return []


def check_register_map(row):
    """Rule 4: a `register-map` row must name an address `bit_name()` can
    decode, or an SFR in `BIT_SFR`.

    The name, not the comment: a comment may *discuss* a decoded bit while
    the name itself is shape-only, and grading the row on the comment would
    make a register-map grade unfalsifiable -- the comment is prose and
    almost always mentions one somewhere."""
    if (row.get("name_basis") or "").strip() != "register-map":
        return []
    for value in name_addresses(row.get("name") or ""):
        if bit_name(value) and BIT_SFR.get(value & 0xF8):
            return []
    # An SFR named as a word: `clear_tcon_bits` names TCON, `set_tcon_6`
    # names TCON bit 6, `timer1_counted_delay_using_0a56` names TCON.6.
    # Checked without the listing here on purpose: this is the rule a *human*
    # applies when reading a row, and a name saying "timer1" is a register-map
    # claim whether or not this one caller had the `.asm` to hand. The
    # grader's own corroboration is the stricter of the two, and the stricter
    # one is what writes the cell.
    tokens = set(name_tokens(row.get("name") or ""))
    if tokens & set(BIT_SFR.values()):
        return []
    if tokens & {word for word, _bit in SFR_WORDS}:
        return []
    return ["is graded register-map but names no address bit_name() decodes "
            "and no SFR in BIT_SFR, so the decoded identity it claims is not "
            "one the architecture has"]


def row_problems(row, registers):
    """Every cross-field rule, in the order the README lists them."""
    return (check_vocabulary(row) + check_ec_register(row, registers)
            + check_pd(row) + check_register_map(row))


# --- the report, --apply and --check -------------------------------------

def _fmt_table(distribution):
    width = max(len(k) for k in distribution)
    return "\n".join("  %-*s %5d" % (width, k, distribution[k])
                     for k in VOCABULARY if k in distribution)


def report(graded):
    print("name_basis distribution")
    for path, rows in graded.items():
        rel = os.path.relpath(path, REPO)
        by_scope = collections.defaultdict(collections.Counter)
        for row in rows:
            by_scope[row.get("scope", "")][row["name_basis"]] += 1
        print("\n%s -- %d row(s)" % (rel, len(rows)))
        print(_fmt_table(collections.Counter(r["name_basis"] for r in rows)))
        scopes = sorted(by_scope)
        print("  %-8s %s" % ("scope", " ".join("%s=%d" % (k, by_scope[scopes[0]][k])
                                               for k in VOCABULARY)))
        for scope in scopes:
            print("  %-8s %s" % (scope, " ".join(
                "%s=%d" % (k, by_scope[scope][k]) for k in VOCABULARY
                if by_scope[scope][k])))


def apply(graded):
    """Write the graded column into both CSVs, in place.

    Rewritten through `csv.DictWriter` with the original field order plus
    `name_basis` appended, so a re-grade is a no-op on an already-graded file
    and the diff of a changed grade is one cell."""
    for path, rows in graded.items():
        with open(path, newline="") as f:
            fields = list(csv.DictReader(f, strict=True).fieldnames)
        if "name_basis" not in fields:
            fields.append("name_basis")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})


def check(graded, repo=REPO):
    """Fail on a committed cell that disagrees with the rule, or that breaks
    a cross-field rule. A check that has quietly stopped rejecting anything
    looks exactly like a check that is working, so every refusal below is
    exercised by --self-test too."""
    registers = register_addresses(repo)
    problems, drift = [], []
    for path, rows in graded.items():
        rel = os.path.relpath(path, REPO)
        for row in rows:
            # `committed_name_basis` is the cell the CSV holds and
            # `name_basis` is what the rule just derived from the same row.
            # Comparing the cell with itself is what made this check
            # unfalsifiable before the two were separated; see `grade_all`.
            if row.get("committed_name_basis", "") != row["name_basis"]:
                drift.append("%s %s %s (%s): committed name_basis %r, rule "
                             "gives %r" % (rel, row.get("scope"),
                                           row.get("addr"),
                                           row.get("name"),
                                           row.get("committed_name_basis") or "",
                                           row["name_basis"]))
            for problem in row_problems(row, registers):
                problems.append("%s %s %s (%s) %s" % (
                    rel, row.get("scope"), row.get("addr"),
                    row.get("name"), problem))
    for problem in (drift + problems)[:20]:
        print("  FAIL  %s" % problem)
    total = len(drift) + len(problems)
    if total > 20:
        print("  FAIL  ... and %d more" % (total - 20))
    if total:
        print("  FAILURES ABOVE")
        return 1
    n = sum(len(v) for v in graded.values())
    print("  %d row(s) re-graded, every name_basis agrees with the rule and "
          "with the four cross-field rules" % n)
    return 0


# The module-level `check`, bound here so `--self-test` can exercise it: the
# fixture defines a local `check` of its own, which shadows this name for the
# rest of that function.
_run_check = check


def self_test():
    """Pin the vocabulary, the `pd` refusal, and each of the four rules.

    Fixtures, not the committed rows: a rule that is only ever tested against
    data it was derived from is not tested."""
    failures = []

    def check(label, cond, detail=""):
        if not cond:
            failures.append("%s %s" % (label, detail))

    def row(**kw):
        base = {"scope": "bank0", "addr": "0EA2", "name": "x", "type": "delay",
                "comment": "", "evidence": "", "basis": "hand-decoded",
                "name_basis": ""}
        base.update(kw)
        return base

    def fixture_asm(path, lines):
        with open(path, "w") as f:
            f.write("; fixture\n")
            for line in lines:
                f.write(line + "\n")
        return path

    scratch = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                           "grade_name_basis_selftest")
    os.makedirs(scratch, exist_ok=True)
    registers = {0x07C4: "XDATA_07C4", 0x043E: "BAT_VOLT"}

    # --- rule 1: vocabulary ---------------------------------------------
    check("vocabulary accepts every member", all(
        not check_vocabulary(row(name_basis=v)) for v in VOCABULARY))
    check("vocabulary refuses empty", bool(
        check_vocabulary(row(name_basis="  "))), "(an empty cell must fail)")
    check("vocabulary refuses off-list", bool(
        check_vocabulary(row(name_basis="guessed"))),
        "(an invented value must fail)")

    # --- rule 2: ec-register needs a registers.yaml address -------------
    check("ec-register accepts a cited register", not check_ec_register(
        row(name="set_07c4_bit4", name_basis="ec-register"), registers))
    check("ec-register refuses a code address", bool(check_ec_register(
        row(name="call_0ea2", name_basis="ec-register"), registers)),
        "(0x0EA2 is CODE and absent from registers.yaml)")
    check("ec-register accepts a comment citation", not check_ec_register(
        row(name="update_the_block", comment="writes 0x07C4 bit 4",
            name_basis="ec-register"), registers))

    # --- rule 3: pd may not borrow the EC map ---------------------------
    check("pd/ec-register refused", bool(
        check_pd(row(scope="pd", name_basis="ec-register"))))
    check("pd/code-shape allowed", not check_pd(
        row(scope="pd", name_basis="code-shape")))
    check("a bank0 row graded ec-register on a real address is clean",
          not row_problems(row(name="write_07c4", name_basis="ec-register"),
                           registers))

    # --- rule 4: register-map needs a decodeable address ---------------
    check("register-map accepts a bit address", not check_register_map(
        row(name="clr_8e_then_set_8f", name_basis="register-map")))
    check("register-map accepts a bare SFR name", not check_register_map(
        row(name="clear_tcon_bits", name_basis="register-map")))
    check("register-map accepts an SFR named with its bit", not check_register_map(
        row(name="set_tcon_6", name_basis="register-map")))
    check("register-map refuses an undecodable address", bool(check_register_map(
        row(name="clear_00_then_set_01", name_basis="register-map"))))
    check("register-map refuses a comment-only citation", bool(check_register_map(
        row(name="spin_until_flag", comment="the listing shows 0x8E = TR1",
            name_basis="register-map"))),
        "(the name carries the claim, so the name must carry the decode)")

    # --- the grader's own ladder ----------------------------------------
    tr1 = fixture_asm(os.path.join(scratch, "tr1.asm"), [
        "0EA2     c2 8e -  clr      0x8e",
        "0EA4     30 8f fd jnb      0x8f, 0x0ea4",
    ])
    xd = fixture_asm(os.path.join(scratch, "xd.asm"), [
        "163C     90 07 c4 mov      DPTR, #0x07c4",
        "163F     e0 - -   movx     A, @DPTR",
    ])
    code_only = fixture_asm(os.path.join(scratch, "code.asm"), [
        "0EA2     12 0e a8 lcall    0x0ea8",
    ])
    check("grade: bit operand is register-map",
          grade(row(name="clear_8e_spin_on_8f", type="delay"), registers, tr1)
          == "register-map")
    check("grade: an SFR named in words is register-map over a listing that "
          "touches the bit",
          grade(row(name="timer1_counted_delay_using_0a56", type="delay"),
                registers, tr1) == "register-map",
          "(the worked example: 'timer1' is TCON.6 = TR1, and the listing "
          "shows 0x8E/0x8F)")
    check("grade: an SFR named in words is NOT register-map without the bit",
          grade(row(name="timer1_counted_delay_using_0a56", type="delay"),
                registers, None) == "code-shape",
          "(with no committed listing the claim cannot be corroborated, so "
          "the default points at the weak end)")
    check("register-map accepts a word-cited SFR", not check_register_map(
        row(name="timer1_counted_delay", name_basis="register-map")))
    check("grade: DPTR immediate in registers.yaml is ec-register",
          grade(row(name="write_07c4_bit4"), registers, xd) == "ec-register")
    check("grade: a 0x0EA2 citation is CODE, not ec-register",
          grade(row(name="call_0ea2"), registers, code_only) == "code-shape",
          "(0x0EA2 is absent from registers.yaml, so the ec-register rule "
          "must not fire on the address alone)")
    check("grade: an unresolved placeholder",
          grade(row(name="ret_stub", type="unresolved"), registers, None)
          == "unresolved")
    check("grade: an unresolved row that still says something",
          grade(row(name="set_dptr_0a51", type="unresolved"), registers, None)
          == "code-shape",
          "(a name that describes the bytes is not a placeholder)")
    check("grade: a BL51 stub name",
          grade(row(name="bl51_bank_select_1", type="gate"), registers, None)
          == "abi-symbol")
    # The name is the mechanism, so a comment's ABI token cannot supply the
    # footing. Without this the grade is unfalsifiable in the same way rule 4
    # refuses: a prose comment mentions a toolchain almost anywhere, so the
    # column would stop distinguishing anything.
    check("grade: a BL51 token in the comment alone is not abi-symbol",
          grade(row(name="load_dptr_88f0_tail_jump_1114", type="bank-switch",
                    comment="the Keil BL51 stub at 0x1114 is not present in "
                            "this decompiled tree"),
                registers, None) == "code-shape",
          "(the name describes two instructions; the comment's mention of "
          "BL51 is a claim about the comment)")
    check("grade: an EDK token in the comment alone is not abi-symbol",
          grade(row(name="read_modify_write_two_variables", type="writer",
                    comment="returns EFI_SUCCESS per the EDK II calling "
                            "convention"),
                registers, None) == "code-shape")
    check("grade: an EDK token in the name is abi-symbol",
          grade(row(name="gCpuSetupGuid", type="gate"), registers, None)
          == "abi-symbol",
          "(the EDK pattern is the toolchain's own casing, so a name carries "
          "one as `g…Guid` and not as prose 'guid')")
    check("grade: a pd row citing an EC register is not ec-register",
          grade(row(scope="pd", name="write_07c4"), registers, xd)
          != "ec-register")
    check("grade: no .asm falls back to the weak end",
          grade(row(name="store_07c4"), registers, None) == "code-shape",
          "(with no committed listing the address cannot be confirmed as "
          "XDATA, and the default points at the weak end)")
    check("grade: mnemonic-shaped tokens are not addresses",
          grade(row(name="dec_a_then_add_8e", type="math"), registers, None)
          == "code-shape")

    # --check's drift half, on the exact shape that made it dead: a row whose
    # committed cell has been overwritten with the computed grade is compared
    # with itself and can never disagree. A fixture that puts a wrong grade in
    # `committed_name_basis` and asserts check() rejects it is what stops the
    # two keys being collapsed back into one again. Called through
    # `_run_check`, because the local `check` above is this fixture's own
    # recorder and shadows the module-level one.
    def drift_fixture(committed_value, computed_value):
        return {"fixture.csv": [
            {"scope": "bank0", "addr": "0EA2", "name": "x", "type": "logic",
             "comment": "", "evidence": "", "basis": "hand-decoded",
             "committed_name_basis": committed_value,
             "name_basis": computed_value}]}

    # The expected failure prints its own diagnostic; that is the real
    # `check()` writing to stdout, and it is left alone rather than silenced,
    # so a run of --self-test still shows what it is refusing.
    check("check refuses a committed grade that disagrees with the rule",
          _run_check(drift_fixture("abi-symbol", "code-shape")) == 1,
          "(a hand-edited name_basis must not pass --check)")
    check("check accepts a committed grade that agrees with the rule",
          _run_check(drift_fixture("code-shape", "code-shape")) == 0)

    if failures:
        for f in failures:
            print("  FAIL  %s" % f)
        print("  FAILURES ABOVE")
        return 1
    print("  self-test passed")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--report", action="store_true",
                    help="print the graded distribution over both CSVs; no "
                         "file is written")
    ap.add_argument("--apply", action="store_true",
                    help="write the graded column into both CSVs in place")
    ap.add_argument("--check", action="store_true",
                    help="re-grade and fail on any committed name_basis that "
                         "disagrees with the rule, or that breaks a "
                         "cross-field rule")
    ap.add_argument("--self-test", action="store_true",
                    help="pin the vocabulary, the pd refusal and the four "
                         "cross-field rules against fixture rows")
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    graded = grade_all()
    if args.apply:
        apply(graded)
        report(graded)
        print("\napplied")
        return 0
    if args.check:
        return check(graded)
    report(graded)
    return 0


if __name__ == "__main__":
    sys.exit(main())
