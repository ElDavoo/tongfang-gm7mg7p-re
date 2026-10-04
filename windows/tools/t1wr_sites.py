#!/usr/bin/env python3
r"""Which arms of `T1WR` a *committed caller* reaches, searched by call site.

`../tools/t1wr_callers.py` (issue #131) searched for a caller of `T1WR` by
**argument value**, and its `ACPI_ARGS` list says in the source why that stops:
thirteen of `T1WR`'s nineteen `Arg0` values are two hex digits and three
decimal ones, and every one of them was measured against the committed trees
before being left out, because `0x81`-`0x85` collide with
`ECSpec.User_Fan_Level1`..`Level5` and `0x83`-`0x85` with ILSpy's own
`Invalid MethodBodyBlock` markers. A search that cannot tell a `T1WR` argument
from a fan level is not a search.

This is the other direction, and the kernel handler is what makes it possible.
`windows/decompiled/native/ACPIDriver.c`'s `0x9C40A4DC` handler reads the
IRP's `SystemBuffer` and lays out the ACPI call itself: `'AeiC'` at `+0x00`,
the method name `'T1WR'` at `+0x04`, `Length = 0x28`, `ArgumentCount = 3`, and
three arguments each built from `SystemBuffer[0..3]`, `[4..7]` and `[8..11]`.
**So a caller's `Arg0` is the first four bytes of the input buffer it handed
over** -- a fact about the call site, not about a value that could be a fan
level somewhere else in the tree. `parse_handler_layout()` re-derives it from
the decompile rather than asserting it, so a re-export that changes the handler
fails here instead of quietly changing what "Arg0" means.

The search has three layers, and what each can and cannot reach is the point:

* **Managed.** Every `DeviceIoControl` call in the decompiled trees, and every
  call to a method that forwards one. The control-code argument is resolved
  through a const table built from the same trees, so `2621482204u`,
  `IOCTL_GPD_ACPI_TMPWRITE1` and `0x9C40A4DC` are one site rather than three
  spellings of a miss. A code that is *not* a constant is a method parameter,
  and that is the interesting case: `AcpiCtrl.WriteACPI(uint ioctrl, ...)`
  passes `ioctrl` straight through to `kernel32!DeviceIoControl`, so the IOCTL
  is settled by its **callers**, each of which passes a literal. Reading the
  wrapper's callers rather than its body is what puts the code and the `Arg0`
  at the same place -- one call site, one literal each -- and it is why an
  overload pair (`ReadACPI`'s `int` and `byte` forms) needs no overload
  resolution to be read correctly. One hop, by design; see `call_sites()`.
* **Native.** A `disasm.sh` listing per committed PE: every `call` to a
  `TempWrite*` export address, and every `mov $0x9c40a4dc,%edx` before the
  `DeviceIoControl` import thunk. The `Arg0` is read back from the site -- the
  store into the address the `lpInBuffer` `lea` names -- because the value that
  matters is the one the site itself puts in the buffer.
* **Reachability.** `ec/tools/dsdt_ec_fields.py`'s `T1WR_ARMS` intersected with
  the sites, one row per arm. `0x71` appears twice in that table and is *not*
  a duplicate: the arm at `:50657` is matched by any caller passing `0x71` and
  leaves the chain before `:50658`, so a `T1WR(0x71)` caller reaches the first
  and **cannot** reach the second. `T1WR_REDUNDANT` is the pair, and the row
  says so rather than counting two reachable arms.

There is a fourth measurement here that is not a `T1WR` question but is the one
a driver actually needs: `power_limit_route()` resolves which IOCTL carries the
committed writes to `0x0783`-`0x0786`, by walking callees from each writer until
it reaches a `DeviceIoControl`.

Every negative here is **"not found by this method"**. The unreadable inputs
are printed with the result, not buried: the still-encrypted 3.1.6.0/3.9.18.0
bodies, the installer payloads, the 27 MB UWP native core that only
`windows/tools/extract.sh` stages, the managed **P/Invoke** shape
(`[DllImport("ACPIDriverDll.dll")]`, which is how a .NET application would call
`TempWrite1` -- not among the shapes the managed layer reads), and anything in
firmware, which no input in this repository can reach. A native layer that read
nothing is reported as unreadable rather than as a clean tree -- the standing
`PROBES` in `t1wr_callers.py` are the same idea and the reason they exist.

Nothing here claims what the EC *does* with a value. A site that reaches arm
`0x84` is evidence about **who writes `0x0785`**, not about whether writing it
changes anything; that is `ec/annotations/registers.yaml`'s `status:` to say,
and this work moves none of them.

Usage:
  t1wr_sites.py                  the reachability table and the census
  t1wr_sites.py --verbose        ...naming the input behind every row
  t1wr_sites.py --no-native      skip the disassembly (no binutils or radare2)
  t1wr_sites.py --self-check     assert the census the write-up quotes
"""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
EC_TOOLS = os.path.join(REPO, "ec", "tools")
if EC_TOOLS not in sys.path:
    # `dsdt_ec_fields` lives in ec/tools and pulls in two more tools by bare
    # module name, so its directory has to be on the path before it is loaded.
    # The alternative is a second copy of `T1WR_ARMS` here, and two answers to
    # "which arms does T1WR dispatch on" is the failure this tool exists to
    # avoid.
    sys.path.insert(0, EC_TOOLS)

import dsdt_ec_fields  # noqa: E402  (needs the sys.path entry above)

# The IOCTL the export table maps `TempWrite1` onto
# (windows/native/ACPIDriverDll.dll.analysis.md, "The export table"). The
# method name it evaluates is *not* pinned here: `parse_handler_layout()` reads
# it out of the handler's four-byte immediate, so a constant beside this one
# would be a second answer to the same question and could disagree with the
# decompile without anything noticing.
T1WR_IOCTL = 0x9C40A4DC

# Every TempWrite/TempRead code, for the census that says which of the six the
# committed stack actually sends. The reachability table is about T1WR alone;
# the other five are here so "the service sends none of them" is a claim about
# a named set rather than about one number.
ACPI_TMP_IOCTLS = {
    0x9C40A4D0: "T1RD", 0x9C40A4D4: "T2RD", 0x9C40A4D8: "T3RD",
    0x9C40A4DC: "T1WR", 0x9C40A4E0: "T2WR", 0x9C40A4E4: "T3WR",
}

# The exports whose RVA the native layer resolves a `call` target against. Read
# from the PE rather than pinned here: an RVA in a literal is a number this
# repository would have to edit the next time the DLL is re-shipped.
TEMP_EXPORTS = ("TempWrite1", "TempWrite2", "TempWrite3")

# The decompiled trees searched as text. The first is the whole service with
# every method body decrypted, so a negative there is a *closed* result for that
# binary rather than a search miss; the other two are partial and anti-tamper
# damaged, which is a different claim (the readability census prints both).
MANAGED_TREES = [
    ("decompiled/v3.1.39.0 (whole service, decrypted)",
     "windows/decompiled/v3.1.39.0"),
    ("decompiled/v3.1.6.0 (partial, anti-tamper)", "windows/decompiled/v3.1.6.0"),
    ("decompiled/v3.9.18.0 (partial, anti-tamper)", "windows/decompiled/v3.9.18.0"),
]

# The committed Windows PEs the native layer disassembles. Each is a plain file
# under vendor/, which is committed input and never build output; nothing here
# writes under vendor/. The ones `windows/ghidra/native-binaries.csv` records
# with an `extract:` source are named in `UNSTAGED_INPUTS` instead, because
# staging them is `windows/tools/extract.sh`'s job and a scan that silently
# skipped them would read as a negative over a smaller tree than it claims.
NATIVE_INPUTS = [
    ("vendor 3.9.18.0 ACPIDriverDll.dll (defines TempWrite1)",
     "vendor/control-center-3.9.18.0/ACPIDriverDll.dll"),
    ("vendor 3.9.18.0 ACPIDriver.sys (implements 0x9C40A4DC)",
     "vendor/control-center-3.9.18.0/ACPIDriver/ACPIDriver.sys"),
    ("vendor 3.1.39.0 GCUService.exe (shipped, bodies encrypted)",
     "vendor/control-center-3.1.39.0/MyControlCenter/GCUService.exe"),
    ("vendor 3.9.18.0 setup.exe (installer wrapper)",
     "vendor/control-center-3.9.18.0/setup.exe"),
    ("vendor 3.1.6.0 UniwillService_3.1.6.0_STD.exe (installer wrapper)",
     "vendor/control-center-3.1.6.0/UniwillService_3.1.6.0_STD.exe"),
]

# Inputs a caller could be in that no layer above reaches. Printed with the
# result: a negative is only as good as this list.
UNSTAGED_INPUTS = [
    "vendor control-center-3.9.18.0 GamingCenter3_Cross .msixbundle: the UWP\n"
    "    front end's 27 MB native core is staged out of the bundle by\n"
    "    windows/tools/extract.sh and is not a plain file under vendor/. Its\n"
    "    Ghidra decompile (windows/decompiled/native/GamingCenter3_Cross.c) is\n"
    "    not disassembly and carries no IOCTL setup, so this tool does not\n"
    "    count it either way.",
    "vendor control-center-3.9.18.0 GamingCenter3_Cross .appxsym: a PDB name\n"
    "    table, so a name there is not a call site. It is t1wr_callers.py's\n"
    "    input for the by-value question, not this one's.",
    "the Inno payload inside setup.exe and UniwillService_3.1.6.0_STD.exe:\n"
    "    compressed, so the wrapper disassembles to the wrapper's code only.",
    "the still-encrypted method bodies of 3.1.6.0 and 3.9.18.0, and every .cs\n"
    "    file carrying an ILSpy error marker -- see the readability census.",
    "anything in firmware, including an ACPI component that calls T1WR. The\n"
    "    DSDT only declares \\_SB.NPCF External; no input in this repository\n"
    "    can reach a caller there.",
    "the managed P/Invoke shape. The managed layer resolves DeviceIoControl\n"
    "    sites and one hop of forwarding wrappers, so a\n"
    "    [DllImport(\"ACPIDriverDll.dll\")] TempWrite1(...) call -- how a .NET\n"
    "    application would call it -- is not among the shapes it reads. No\n"
    "    committed tree binds one: the only ACPIDriverDll.dll declaration in\n"
    "    windows/decompiled/ is SMAPCTable, which the export table maps to\n"
    "    SMRW rather than to T1WR.",
]

# ---------------------------------------------------------------- managed ---

# `public const uint IOCTL_GPD_ACPI_TMPWRITE1 = 2621482204u;` -- ILSpy's
# spelling. The suffix, the casts and the `0x`/`0X` case are all accepted
# because the same constant is spelled three ways across the trees and a
# const table that understood one of them would silently miss the other two.
CONST_DECL = re.compile(
    r"^\s*(?:public|internal|private|protected|\s)*const\s+"
    r"(?:byte|sbyte|short|ushort|int|uint|long|ulong)\s+"
    r"(?P<name>\w+)\s*=\s*(?P<value>[^;]+);", re.M)

# A method declaration. ILSpy puts one tab before the modifiers and the
# signature, so anchoring on it is what keeps a call to `Write` from being read
# as the declaration of a method called `Write`; the body's braces are matched
# separately because a signature may wrap.
METHOD_DECL = re.compile(
    r"^\t(?:(?:public|private|internal|protected|static|virtual|override|"
    r"sealed|extern|unsafe|async|new|partial)\s+)*"
    r"(?:[\w.<>\[\],?]+\s+)?(?P<name>\w+)\s*\((?P<params>[^;{]*)\)\s*;?\s*$",
    re.M)

DEVICE_IO_CONTROL = re.compile(r"\b(?:[\w.]+\.)?DeviceIoControl\s*\(")


def _int_of(expr):
    """The integer an expression is, or None if it is not one literal.

    `(uint)2621482204` and `0x9c40a4dc` and `2621482204u` are the same number;
    `addr` and `GetType().Name` are not numbers, and are returned as None rather
    than guessed at, which is what puts them in the unresolved bucket.
    """
    text = expr.strip()
    text = re.sub(r"^\(\s*(?:u?int|u?long|u?short|byte|Int32|UInt32)\s*\)\s*", "", text)
    text = text.rstrip("uUlL")
    try:
        if re.fullmatch(r"0[xX][0-9a-fA-F]+", text):
            return int(text, 16)
        if re.fullmatch(r"\d+", text):
            return int(text, 10)
    except ValueError:  # pragma: no cover - unreachable given the two regexps
        return None
    return None


def const_table(texts):
    """{name: value} over every `const` declaration in the given sources."""
    table = {}
    for text in texts:
        for m in CONST_DECL.finditer(text):
            value = _int_of(m.group("value"))
            if value is not None:
                table[m.group("name")] = value
    return table


def _split_args(text):
    """The top-level comma-separated arguments of a call, parens respected."""
    args, depth, current = [], 0, ""
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            args.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        args.append(current)
    return args


def _call_args(text, open_paren):
    """The argument text of the call whose `(` is at `open_paren`."""
    depth, i = 0, open_paren
    while i < len(text):
        if text[i] in "([{":
            depth += 1
        elif text[i] in ")]}":
            depth -= 1
            if depth == 0:
                return text[open_paren + 1:i], i
        i += 1
    return "", len(text)


def _method_body(text, end_of_signature):
    """(body, body_start) for the block after a signature, or ('', end).

    `body_start` is the absolute index into `text` of the body's first
    character, so a match inside the body converts to a line number by one
    `text.count("\\n", 0, body_start + match.start())`. Carrying the index
    rather than a line offset is what makes that exact: counting newlines from
    the signature instead lands a line short, because the `{` and whatever
    follows it on the same line move the count.
    """
    brace = text.find("{", end_of_signature)
    semi = text.find(";", end_of_signature)
    if brace < 0 or (0 <= semi < brace):
        return "", end_of_signature          # an extern declaration, no body
    depth, i = 0, brace
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace:i], brace
        i += 1
    return text[brace:], brace


def methods(text):
    """[(name, params, body, body_start)] for every method in a source.

    `params` is the raw parameter list; `body_start` is the body's absolute
    index in `text`, so a match inside the body converts to a line by
    `text.count("\\n", 0, body_start + match.start()) + 1`. One tab of
    indentation before the modifiers is ILSpy's member shape and is what
    separates a declaration from a call.
    """
    out = []
    for m in METHOD_DECL.finditer(text):
        params = _split_args(m.group("params"))
        body, body_start = _method_body(text, m.end())
        if not body:
            continue
        out.append((m.group("name"), params, body, body_start))
    return out


# A call, however it is spelled: `WriteACPI(...)`, `AcpiModel?.Write(...)`,
# `Win32.DeviceIoControl(...)`. The qualifier is dropped because the question
# is which code this call carries, not which class spelled it -- and because
# `AcpiCtrl` reaches `kernel32!DeviceIoControl` through a `WriteACPI` wrapper
# whose *callers* are the sites that settle the code.
CALL = r"(?:[\w?]+\s*\.\s*)*%s\s*\("


def _param_name(decl):
    """The identifier a parameter declaration binds.

    Greedy, not lazy: `ref byte[] pData` has to lose `ref byte[]` and not just
    the space after `ref`, and a lazy `.*?` would leave `byte[] pData` behind --
    which then matches nothing, and the site it belongs to goes unresolved for a
    reason that has nothing to do with the tree.
    """
    return re.sub(r"^.*\s", "", decl.strip().lstrip("*")).strip()


def _buffer_first_word(body):
    """The expression a method's first `DeviceIoControl` buffer word comes from.

    `int[] source = new int[2] { addr, data };` followed by a `Marshal.Copy`
    into the pointer handed to `DeviceIoControl` -- word 0 of the buffer is
    `addr`, so that is the `Arg0` the handler will read. Only an explicit
    initialiser is read: a buffer filled by a loop or computed elsewhere has no
    word 0 this can name, and returning '' says so instead of guessing.
    """
    m = re.search(r"new\s+(?:int|uint|byte|short|long)\s*\[\s*\d+\s*\]\s*"
                  r"\{\s*(?P<e0>[^,}]+)", body)
    return m.group("e0").strip() if m else ""


def helpers(texts):
    """{(name, params): (code_index, arg0_index)} for the forwarding wrappers.

    `AcpiCtrl.WriteACPI(uint ioctrl, int addr, int data)` does not carry a
    code at all: it passes its own `ioctrl` parameter to `DeviceIoControl`. It
    is still where the code is *decided*, because its callers pass literals.
    So the wrapper is recorded with the two argument positions that matter and
    the sites are then read off the calls **to** it -- which is what makes an
    overload pair (`ReadACPI`'s `int` and `byte` forms) fall out for free: each
    call site carries its own literal, and neither is attributed to the wrong
    one.

    The key is `(name, params)` rather than `(name, ...)`: two overloads are
    two wrappers, and collapsing them would be how a code got attributed to the
    wrong body.
    """
    found = {}
    for _label, text in texts:
        for name, params, body, _off in methods(text):
            call = DEVICE_IO_CONTROL.search(body)
            if not call:
                continue
            args, _end = _call_args(body, call.end() - 1)
            args = _split_args(args)
            if len(args) < 3:
                continue
            names = [_param_name(p) for p in params]
            if args[1].strip() not in names:
                continue                      # a literal here is not a wrapper
            first = _buffer_first_word(body)
            found[(name, tuple(names))] = (
                names.index(args[1].strip()),
                names.index(first) if first in names else None)
    return found


def wrapper_positions(table, name):
    """The (code, arg0) argument positions every overload of `name` agrees on.

    `ReadACPI` is declared twice -- once taking `ref int`, once `ref byte` --
    and both build `new int[1] { addr }`, so both name the same two positions
    and a call to either reads the same way. An overload set that *disagreed*
    would have no single answer, and returns `(None, None)` so the site is
    reported unresolved rather than resolved against whichever body sorted
    first.
    """
    shapes = {(code, first) for (n, _p), (code, first) in table.items()
              if n == name}
    if len(shapes) == 1:
        return shapes.pop()
    return (None, None)


def _resolve(expr, consts):
    """The integer an argument expression carries, or None.

    `2621482204u`, `0x9C40A4DC` and `IOCTL_GPD_ACPI_TMPWRITE1` are one value in
    three spellings and resolve to the same site, which is the whole reason for
    the const table. `addr` is not a number and is never guessed at.
    """
    value = _int_of(expr)
    if value is not None:
        return value
    return consts.get(expr.strip().split(".")[-1])


def call_sites(texts, consts):
    """Every site that sends an ACPI IOCTL, with the IOCTL and the `Arg0`.

    `texts` is `[(label, source)]`. A site is either a `DeviceIoControl` call
    whose control-code argument is a literal or a `const`, or **a call to a
    forwarding wrapper** with a literal at the wrapper's code position. The
    second kind is where every real site in this tree lives, and reading it
    there rather than at the `DeviceIoControl` is what the by-value search
    could not do: `WriteACPI(2621482204u, 0x84, v)` names arm `0x84` at the
    call site, whatever `0x84` means elsewhere in the tree.

    `Arg0` is the argument at the position the wrapper's buffer word 0 came
    from -- read off `new int[2] { addr, data }` in the wrapper's own body. An
    argument that is neither a literal nor a `const` is reported as unresolved
    and never propagated through a second hop: two hops would need a call graph
    and interprocedural constant propagation over ILSpy output, and a partial
    version of that reports sites it has not resolved.
    """
    table = helpers(texts)
    names = {name for name, _params in table}
    sites = []
    for label, text in texts:
        for name, params, body, body_start in methods(text):
            # Both loops can match the same call -- `BatteryInfo` declares its
            # own method named `DeviceIoControl`, which is both a call to
            # `DeviceIoControl` and a call to a wrapper. Deduplicated by
            # position, because a doubled site would read as two callers.
            spans = {}
            for m in DEVICE_IO_CONTROL.finditer(body):
                spans[m.start()] = m
            for other in sorted(names - {name}):
                for m in re.finditer(CALL % re.escape(other), body):
                    spans.setdefault(m.start(), m)
            for m in sorted(spans.values(), key=lambda x: x.start()):
                if m.end() - 1 >= len(body):
                    continue
                args, _end = _call_args(body, m.end() - 1)
                args = _split_args(args)
                line = text.count("\n", 0, body_start + m.start()) + 1
                site = {"input": label, "method": name, "line": line,
                        "file_line": f"{label}:{line}", "ioctl": None,
                        "arg0": None, "arg0_spelling": "", "via": "",
                        "resolved": "unresolved"}
                key = m.group(0).rstrip("( \t\n").split(".")[-1].strip()
                code_index, arg0_index = wrapper_positions(table, key)
                if code_index is not None:
                    if len(args) <= code_index:
                        continue
                    site["via"] = f"{key}(arg {code_index})"
                    site["resolved"] = "caller"
                    site["ioctl"] = _resolve(args[code_index], consts)
                    if arg0_index is not None and len(args) > arg0_index:
                        site["arg0"] = _resolve(args[arg0_index], consts)
                        site["arg0_spelling"] = args[arg0_index].strip()
                else:
                    if len(args) < 3:
                        continue
                    site["ioctl"] = _resolve(args[1], consts)
                    site["arg0_spelling"] = args[1].strip()
                    site["resolved"] = ("literal" if site["ioctl"] is not None
                                        else "forwarded")
                    site["arg0"] = _resolve(_buffer_first_word(body), consts)
                sites.append(site)
    return sites


# ----------------------------------------------------------------- native ---

LISTING_LINE = re.compile(
    r"^\s*([0-9a-fA-F]+):\s*(?:[0-9a-fA-F]{2} )+\s*([a-z][a-z0-9.]*)\s*(.*?)\s*$")


def parse_listing(text):
    """[(va, mnemonic, operands)] for every instruction in a disasm.sh listing.

    Both of `disasm.sh`'s back ends emit `<va>:\t<bytes>\t<mnemonic>\t<rest>`,
    so one parse covers objdump and the reformatted radare2 output alike.

    The objdump `#` comment is **kept** in the operand string rather than
    stripped, because it carries the resolved target address: a
    `mov %ecx,0x278d02(%rip)` only names the address it writes once objdump has
    done the RIP-relative arithmetic, and that address is how a store is matched
    against the buffer the `lea` named. Dropping it here would leave
    `_comment_target()` with nothing to read and every `Arg0` unresolved.
    """
    out = []
    for line in text.splitlines():
        m = LISTING_LINE.match(line)
        if not m:
            continue
        out.append((int(m.group(1), 16), m.group(2), m.group(3).strip()))
    return out


def _comment_target(operands):
    """The `0x...` an objdump `#` comment names, or None.

    None when the comment is absent, which is the radare2 shape: r2 prints the
    displacement and leaves the reader to add the instruction pointer, so a
    listing with no comments yields no resolved address and therefore no matched
    store. That degrades to "Arg0 not resolved at this site", which is the
    honest report rather than a wrong one.
    """
    if "#" not in operands:
        return None
    m = re.search(r"(0x[0-9a-fA-F]+)", operands.split("#", 1)[1])
    return int(m.group(1), 16) if m else None


def _pe_exports(path):
    """{name: rva} from a PE's export directory, via pe_triage's parser."""
    sys.path.insert(0, HERE)
    try:
        import pe_triage
        with open(path, "rb") as fh:
            pe = pe_triage.PE(fh.read())
        return {name: rva for _ord, name, rva in pe.exports() if name}
    except Exception:
        # A PE this parser cannot read is an input the native layer says nothing
        # about, not a crash: `census()` records it as unreadable and the write-up
        # carries that in its list rather than in its answer.
        return {}


def listing_for(path):
    """A disasm.sh listing for a PE, or '' when no disassembler is installed.

    Returning '' rather than raising is what lets `census()` say "this input
    could not be read" instead of aborting the whole run on a machine without
    binutils.
    """
    try:
        out = subprocess.run(["bash", os.path.join(HERE, "disasm.sh"), path],
                             capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout


# objdump spells a store with an immediate operand `movl` and a register store
# `mov`, so a `mov`-only rule would miss exactly the case that carries a
# constant `Arg0` -- the one worth finding. Both are matched as stores.
STORE_MNEMONICS = ("mov", "movl", "movq")


def native_sites(label, path, instructions, image_base, exports):
    """[(va, kind, ioctl, arg0)] for the IOCTL sites in one native program.

    Two shapes are looked for, and they are different claims:

    * `call` to a `TempWrite*` export RVA -- something that *calls* the wrapper.
      Its `Arg0` is whatever that caller passes in `ecx`, which a linear
      listing cannot follow, so it is reported as not resolved.
    * `mov $0x9c40a4dc,%edx` before the `DeviceIoControl` import thunk -- a site
      that issues the IOCTL itself. `lpInBuffer` is the third argument, so it
      arrives in `r8`; the `lea` naming the buffer address is followed back to
      the store into it, and that store's source operand is the `Arg0`.

    A store of a *register* into word 0 means the value is whatever that
    register held -- which is the honest answer for a wrapper that forwards its
    own first parameter, and is reported as unresolved rather than guessed.
    """
    out = []
    export_rvas = {image_base + exports[name]: name
                   for name in TEMP_EXPORTS if name in exports}
    by_va = {va: (m, o) for va, m, o in instructions}
    vas = [va for va, _m, _o in instructions]
    for index, va in enumerate(vas):
        mnemonic, operands = by_va[va]
        if mnemonic == "call":
            m = re.fullmatch(r"0x([0-9a-fA-F]+)", operands.split("#")[0].strip())
            if m and int(m.group(1), 16) in export_rvas:
                out.append((va, "calls " + export_rvas[int(m.group(1), 16)],
                            T1WR_IOCTL, None))
        if not (mnemonic == "mov" and
                re.fullmatch(r"\$0x9c40a4dc,%edx", operands.split("#")[0].strip())):
            continue
        # The IOCTL is in edx, so the issuing call is the first one after it.
        window = vas[index:index + 24]
        if not any(by_va[w][0] == "call" for w in window):
            continue
        # The buffer is filled *before* the code is loaded -- MSVC spills the
        # three arguments into a scratch global at the top of the wrapper and
        # only sets up the call afterwards -- so the setup is read from the whole
        # enclosing function, not from the instructions after the `mov`. Bounded
        # at the preceding `int3` padding, which is what MSVC puts between
        # functions and what stops the search running into the previous one.
        start = _function_start(vas, by_va, index)
        out.append((va, "issues 0x%08X" % T1WR_IOCTL, T1WR_IOCTL,
                    _buffer_arg0(by_va, vas[start:index + 24])))
    return out


def _buffer_arg0(by_va, window):
    """The `Arg0` the enclosing function puts in word 0 of its input buffer.

    Two passes over the window, and the order matters. `DeviceIoControl`'s
    third argument arrives in `r8`, so the `lea` that puts the buffer address
    there names the buffer -- but in `TempWrite1` that `lea` comes *after* the
    stores, so a single forward pass would meet every store before it knew which
    address to match against. Finding the buffer first and then the store
    against it is what makes the read order-independent, which matters because
    MSVC is free to emit either.

    The value is whatever the word-0 store wrote. A register there means the
    value is that register's -- the wrapper forwarding its own first parameter --
    and that is reported as unresolved rather than turned into a number.
    """
    buffer_va = None
    for va in window:
        mnemonic, operands = by_va[va]
        if mnemonic == "lea" and "%r8" in operands:
            buffer_va = _comment_target(operands)
    if buffer_va is None:
        return None
    for va in window:
        mnemonic, operands = by_va[va]
        if mnemonic not in STORE_MNEMONICS or "(%rip)" not in operands:
            continue
        if _comment_target(operands) != buffer_va:
            continue
        source = operands.split("#")[0].strip().split(",")[0].strip()
        return _int_of(source.lstrip("$"))
    return None


def _function_start(vas, by_va, index, window=160):
    """The index of the enclosing function's first instruction.

    Bounded by the run of `int3` padding MSVC emits between functions, and by
    `window` so a listing with no padding -- a stripped or unusual build -- still
    terminates. Falling back to the window edge degrades the answer to "no setup
    found before the `mov`", which is reported as unresolved rather than as a
    wrong `Arg0`.
    """
    low = max(0, index - window)
    i = index
    while i > low:
        if by_va[vas[i]][0] == "int3" and by_va[vas[i - 1]][0] == "int3":
            return i
        i -= 1
    return low


# ----------------------------------------------------------- reachability ---

def reachability(sites, arms=None, redundant=None):
    """One row per `T1WR` arm: is a committed caller reaching it?

    `arms` and `redundant` default to `dsdt_ec_fields`' own tables rather than
    to a copy, so this cannot disagree with the tool that parses the .dsl. The
    redundant `0x71` is folded in the way the ASL folds it: `:50657` shadows
    `:50667`, so a caller passing `0x71` reaches the first arm and cannot reach
    the second, and that second row says so in its own words.
    """
    arms = dsdt_ec_fields.T1WR_ARMS if arms is None else arms
    redundant = dsdt_ec_fields.T1WR_REDUNDANT if redundant is None else redundant
    shadowed = redundant[1] if redundant else None
    reached = {site["arg0"] for site in sites if site.get("arg0") is not None}
    rows = []
    for arg0, line, fields in arms:
        if line == shadowed:
            note = (f"unreachable: the arm at :{redundant[0]} matches the same "
                    "0x71 first and leaves the chain")
        elif arg0 in reached:
            note = "a committed site passes this Arg0"
        else:
            note = "not found by this method"
        rows.append({"arg0": arg0, "line": line, "fields": fields,
                     "reachable": arg0 in reached and line != shadowed,
                     "note": note})
    return rows


# ------------------------------------------------ the layout that keys it ---

HANDLER_FUNC = "FUN_140002614"       # the 0x9C40A4DC handler in ACPIDriver.c


def parse_handler_layout(text, func=HANDLER_FUNC, literal=None):
    """The `SystemBuffer` slices the `0x9C40A4DC` handler reads, from the decompile.

    Everything this tool calls a caller's `Arg0` rests on the handler reading
    the IRP's `SystemBuffer` and copying it into the ACPI evaluation buffer
    verbatim. So the layout is parsed out of
    `windows/decompiled/native/ACPIDriver.c` rather than asserted: a re-export
    that changed which offsets are read would change what "Arg0" means, and the
    suite checks this against the committed file rather than against a constant
    here.

    `literal` is the handler's four-byte method-name immediate. It defaults to
    the one `func` actually contains -- found rather than assumed -- so the same
    parse answers for `TempWrite2`'s and `TempWrite3`'s handlers too, which is
    what lets the suite hold that the three wrappers build their buffer the same
    way instead of only checking the one this tool is about.

    Returns `{'method', 'argument_count', 'buffer_length', 'arg_length',
    'slices'}` where `slices` is `[(first, last)]` per argument, in order.
    """
    body = _function_text(text, func)
    if body is None:
        return None
    if literal is None:
        literal = _method_immediate(body)
    if literal is None:
        return None
    name = struct_pack(literal)
    if f"0x{literal:08x}" not in body.lower() and name not in body:
        return None
    # The first argument is the whole-word load the decompiler emitted as a
    # CONCAT chain: `*puVar1` is word 0's low byte, so `CONCAT14(*puVar1, …)`
    # with `CONCAT15(puVar1[1], …)`, `CONCAT16(puVar1[2], …)` and
    # `CONCAT17(puVar1[3], …)` assembles bytes 0..3 of `SystemBuffer`.
    m = re.search(
        r"= CONCAT17\(puVar1\[(?P<b3>\w+)\],CONCAT16\(puVar1\[(?P<b2>\w+)\],"
        r"CONCAT15\(puVar1\[(?P<b1>\w+)\],CONCAT14\(\*puVar1,"
        r"(?P<len>0x[0-9a-fA-F]+)\)\)\)\)", body)
    slices = []
    arg_length = None
    if m:
        arg_length = _int_of(m.group("len"))
        head = [0] + [_offset(m.group(k)) for k in ("b1", "b2", "b3")]
        slices.append((head[0], head[-1]))
    # The other two are four consecutive byte stores each. The `= 0x40000`
    # Length assignments delimit them: the decompiler emits one Length per
    # argument, immediately before that argument's bytes, and the two runs are
    # *adjacent* indices (`[4..7]` then `[8..11]`), so a run detector that only
    # looked at the numbers would merge them into one eight-byte slice and call
    # it a single argument.
    runs, current = [], []
    for stmt in re.finditer(r"\w+ = (0x[0-9a-fA-F]+|puVar1\[(\w+)\]);", body):
        target = stmt.group(2)
        if target is None:
            if current:
                runs.append((current[0], current[-1]))
                current = []
            continue
        index = _offset(target)
        if index is None:
            continue
        if current and index == current[-1] + 1:
            current.append(index)
        else:
            if current:
                runs.append((current[0], current[-1]))
            current = [index]
    if current:
        runs.append((current[0], current[-1]))
    slices.extend(runs)
    return {"method": struct_pack(literal),
            "argument_count": _int_of(_assign(body, "local_41c")),
            "buffer_length": _int_of(_assign(body, "local_420")),
            "arg_length": arg_length, "slices": slices}


def _assign(body, name):
    m = re.search(rf"{name} = ([^;]+);", body)
    return m.group(1) if m else ""


def _offset(token):
    """`0xb` or `0x0b` as an int; a Ghidra-spun symbol name as None."""
    if token.startswith("0x"):
        return int(token, 16)
    if token.isdigit():
        return int(token)
    return None


def _function_text(text, name):
    """The body of `name` in a Ghidra .c, delimited by the `// ====` banners."""
    m = re.search(rf"^// ==== {re.escape(name)} @ [0-9a-fA-F]+$", text, re.M)
    if not m:
        return None
    nxt = re.search(r"^// ==== ", text[m.end():], re.M)
    return text[m.end(): m.end() + nxt.start()] if nxt else text[m.end():]


def struct_pack(value):
    """A four-byte immediate, as the C spells it and the byte order reads it."""
    return "".join(chr((value >> (8 * i)) & 0xFF) for i in range(4))


def dispatch_table(text):
    """{ioctl: handler function name} from the driver's dispatch chain.

    Read off the `else if (uVar2 == 0x9c40a4dc) { FUN_…( … ); }` chain in the
    decompile rather than from a table written here, so "which handler is
    `0x9C40A4DC`" has one answer in this repository.

    Both shapes Ghidra emits are read, because the chain uses each of them:
    the `==` form for the guarded comparisons, and the fall-through form -- an
    `if (uVar2 != CODE) goto LAB_fatal; }` whose body *is* the handler -- for
    the last one in the chain. A parser that only took the `==` form would
    silently drop `0x9C40A500`, and a dropped code reads as a code the driver
    does not implement.
    """
    out = {}
    for m in re.finditer(
            r"uVar2 == (0x[0-9a-fA-F]+)\)\s*\{\s*(FUN_\w+)\(", text):
        out[int(m.group(1), 16)] = m.group(2)
    for m in re.finditer(
            r"uVar2 != (0x[0-9a-fA-F]+)\)\s*\{[^{}]*goto\s+LAB_\w+;\s*\}"
            r"\s*(FUN_\w+)\(", text, re.S):
        out.setdefault(int(m.group(1), 16), m.group(2))
    return out


def _method_immediate(body):
    """The four-byte method-name immediate a handler body assigns, or None.

    Ghidra renders `'T1WR'` as `0x52573154`; read back little-endian that is
    `T1WR`. The *first* such assignment is taken because a handler can hold
    more than one constant -- `TempWrite3`'s assigns both a method name and a
    field name -- and the method name is the one the dispatch chain selects on.
    """
    m = re.search(r"= (0x[0-9a-fA-F]{8});", body)
    return int(m.group(1), 16) if m else None


def handler_method(text, func):
    """The ACPI method a handler passes, from its four-byte name immediate."""
    body = _function_text(text, func)
    if body is None:
        return None
    literal = _method_immediate(body)
    return struct_pack(literal) if literal is not None else None


# ------------------------------------------------------- the CPU-PL answer ---

# The registers whose committed writer is the question the issue asks about.
# Address, not name: the DSDT and `ec-callsites.csv` both key on it.
POWER_LIMIT_ADDRS = (0x0783, 0x0784, 0x0785, 0x0786)


def power_limit_route(callsites_csv, ioctl_of_method):
    """{addr: {"writers": [...], "ioctl": ..., "resolved": bool}}.

    Whether anything in the committed Windows stack writes `APL1`/`APL2`/
    `APL4`/`APTC`/`APTN` is a question about *writers*, and
    `windows/decompiled/v3.1.39.0/ec-callsites.csv` is the committed census of
    them. Which IOCTL each one routes through is the part this tool can add,
    and it adds it by resolving the method's own call chain rather than by
    assertion -- `SetPL1Value` writes through `EcCtrl.Write`, which is
    `MyEcCtrl.Write`, which is `AcpiCtrl.Write`, which calls
    `WriteACPI(2621482124u, …)`.

    A writer whose IOCTL does not resolve is reported with `resolved: False`
    and no IOCTL. That is the common case for a method several hops up, and it
    is the honest one: the write is a committed fact, its route is not.
    """
    writers = {}
    with open(callsites_csv, encoding="utf-8") as fh:
        header = fh.readline().rstrip("\n").split(",")
        try:
            col = {name: i for i, name in enumerate(header)}
        except ValueError:
            return {}
        for line in fh:
            row = line.rstrip("\n").split(",")
            if len(row) <= max(col.values()):
                continue
            if row[col["op"]] != "write":
                continue
            try:
                addr = int(row[col["addr"]], 16)
            except ValueError:
                continue
            if addr not in POWER_LIMIT_ADDRS:
                continue
            writers.setdefault(addr, []).append(
                (row[col["method"]], row[col["file"]], row[col["line"]]))
    out = {}
    for addr, sites in sorted(writers.items()):
        methods_seen = sorted({m for m, _f, _l in sites})
        routes = {ioctl_of_method(m) for m in methods_seen}
        routes.discard(None)
        # `resolved` is decided before `pop()` consumes the set, so the flag and
        # the value it describes cannot disagree.
        resolved = len(routes) == 1
        out[addr] = {
            "writers": sites,
            "methods": methods_seen,
            "ioctl": routes.pop() if resolved else None,
            "resolved": resolved,
        }
    return out


def ioctl_of_method(method, texts, consts, depth=5):
    """The IOCTL a method reaches within `depth` hops, or None.

    The walk follows **callees**, which is the direction the CPU power-limit
    route runs: `SetPL1Value` calls `EcCtrl.Write`, which is `MyEcCtrl.Write`,
    which calls `AcpiModel.Write`, which calls `WriteACPI(2621482124u, …)`.

    It is bounded because a bounded walk returning None is a reportable state
    and an unbounded one is a hang. A name reached from several classes at once
    does not stop it: every body of that name is walked, and the walk gives up
    only if they disagree about the code -- a chain that resolves to two IOCTLs
    has no single answer, and one that resolves to one is stronger evidence than
    the class that happens to sort first.

    Receiver types are not resolved. `EcCtrl.Write` and `MyEcCtrl.Write` and
    `AcpiCtrl.Write` are three different methods that share one name, and the
    walk treats them as one. That is a real approximation and it is why the
    answer is only reported when every body of the name agrees.
    """
    table = helpers(texts)
    wrapper_names = {name for name, _params in table} | {"DeviceIoControl"}
    bodies = {}
    for _label, text in texts:
        for mname, params, body, _off in methods(text):
            bodies.setdefault(mname, []).append((params, body))

    seen, frontier = set(), {method}
    for _hop in range(depth):
        found, nxt = set(), set()
        for name in frontier:
            for params, body in bodies.get(name, []):
                calls = []
                for other in sorted(wrapper_names):
                    calls.extend(re.finditer(CALL % re.escape(other), body))
                for m in calls:
                    if m.end() - 1 >= len(body):
                        continue
                    args, _end = _call_args(body, m.end() - 1)
                    args = _split_args(args)
                    key = m.group(0).rstrip("( \t\n").split(".")[-1].strip()
                    code_index, _arg0 = wrapper_positions(table, key)
                    if code_index is None:
                        if len(args) >= 3:
                            code = _resolve(args[1], consts)
                            if code is not None:
                                found.add(code)
                            elif key not in seen:
                                nxt.add(key)     # forwards its own parameter
                        continue
                    if len(args) <= code_index:
                        continue
                    code = _resolve(args[code_index], consts)
                    if code is not None:
                        found.add(code)
                    elif key not in seen:
                        nxt.add(key)
                # Every method this one calls is a candidate for the next hop,
                # whatever its name -- `SetPL1Value` reaches the answer through
                # `Write`, which is not a wrapper and would be invisible to a
                # walk that only followed wrapper names.
                for callee in _called_names(body):
                    if callee not in seen:
                        nxt.add(callee)
        if len(found) == 1:
            return found.pop()
        if len(found) > 1:
            return None
        seen.update(frontier)
        frontier = nxt - seen
        if not frontier:
            return None
    return None


# A call in a method body, whether or not it resolves to anything. Deliberately
# loose about what counts as a name: `AcpiModel?.Write(` and `EcCtrl.Write(`
# are both one.
_CALLEE = re.compile(r"(?<![\w])([\w?]+)\s*\.\s*(\w+)\s*\(|"
                     r"(?<![\w.])(\w+)\s*\(")


def _called_names(body):
    """{name} for every call-looking thing in a method body.

    Over-inclusive on purpose -- a `if (` or a cast is picked up as a name and
    simply finds no body -- because the alternative is a pattern tight enough to
    miss the qualified `AcpiModel?.Write(` this route depends on, and a missed
    callee is a silent wrong answer rather than a reported one.
    """
    out = set()
    for m in _CALLEE.finditer(body):
        out.add(m.group(2) or m.group(3))
    return out


# ------------------------------------------------------------- readability ---

DECOMPILER_MARKERS = ("Invalid MethodBodyBlock", "BadImageFormatException")

# (term searched for, what its presence proves, [inputs searched]). A probe
# carries no evidence about callers; it carries evidence about whether the scan
# reached a source at all, which is the whole difference between a zero that
# reads as "not there" and one that reads as "not looked at". The first three
# are the controls a broken input fails: the DSDT names `T1RD`, and the
# committed service names both `WriteACPI` and `SMAPCTable`, so a run that
# reaches none of them reached nothing.
PROBES = [
    ("T1RD", "evidence/acpi/dsdt.dsl defines it, so the text path reaches a "
     "source with an ACPI method name in it",
     ["evidence/acpi/dsdt.dsl"]),
    ("WriteACPI", "the decrypted service declares it, so the managed path "
     "reaches the file every ACPI IOCTL in that binary passes through",
     ["windows/decompiled/v3.1.39.0/GCUService/MyECIO/AcpiCtrl.cs"]),
    ("SMAPCTable", "AcpiCtrl.cs holds a real ACPIDriverDll.dll declaration, so "
     "the file a P/Invoke binding would live in was read rather than skipped. "
     "That is a statement about the file; this tool does not follow the "
     "binding -- UNSTAGED_INPUTS says so",
     ["windows/decompiled/v3.1.39.0/GCUService/MyECIO/AcpiCtrl.cs"]),
    ("TempWrite1", "ACPIDriverDll.dll's own export directory, so the native "
     "path reaches a PE that defines the wrapper",
     ["vendor/control-center-3.9.18.0/ACPIDriverDll.dll"]),
]


def readability(trees):
    """([(tree label, marker count)], [(term, why, hits)]) -- what was searchable.

    Counted per **tree**, not per file and not summed across trees. A damaged
    method body in 3.9.18.0 and one in the fully decrypted 3.1.39.0 are
    different findings: the first is a boundary on the search, the second would
    be a hole in it. Reporting one figure for all three trees would make the
    clean one look as bounded as the damaged ones, which is exactly the
    asymmetry `docs/findings.md` §4o is careful about.
    """
    markers = [(label, sum(sum(text.count(m) for m in DECOMPILER_MARKERS)
                          for _l, text in sources))
               for label, sources in trees]
    probes = []
    for term, why, paths in PROBES:
        hits = 0
        for rel in paths:
            path = os.path.join(REPO, rel)
            if not os.path.exists(path):
                continue
            if rel.endswith((".dll", ".sys", ".exe")):
                with open(path, "rb") as fh:
                    blob = fh.read()
                hits += (blob.count(term.encode())
                         + blob.count(term.encode("utf-16-le")))
            else:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    hits += fh.read().count(term)
        probes.append((term, why, hits))
    return markers, probes


# ------------------------------------------------------------------ census ---

def _read_tree(rel):
    """Every .cs source under a committed tree, as [(label, text)]."""
    root = os.path.join(REPO, rel)
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if name.endswith(".cs"):
                path = os.path.join(dirpath, name)
                label = os.path.relpath(path, REPO).replace(os.sep, "/")
                with open(path, encoding="utf-8", errors="replace") as fh:
                    out.append((label, fh.read()))
    return out


def managed_texts():
    """[(tree label, source)] over every managed tree, for one const table.

    The const table is built across all of them, not per tree, because a
    `const` declared in one file and passed in another is a real C# shape and
    a per-tree table would call it unresolved.
    """
    out = []
    for label, rel in MANAGED_TREES:
        out.append((label, _read_tree(rel)))
    return out


def census(native=True):
    """Everything the write-up quotes, computed from the committed tree."""
    result = {"sites": [], "unreadable": [], "probes": [], "native": [],
              "unresolved": []}
    trees = managed_texts()
    flat = [(label, text) for label, sources in trees for label, text in sources]
    consts = const_table([t for _l, t in flat])
    for label, sources in trees:
        for site in call_sites(sources, consts):
            site["tree"] = label
            result["sites"].append(site)
    result["unresolved"] = [s for s in result["sites"]
                            if s["ioctl"] is None]
    markers, probes = readability(trees)
    for tree, count in markers:
        result["unreadable"].append((tree, count))
    result["probes"] = probes

    handler = os.path.join(REPO, "windows/decompiled/native/ACPIDriver.c")
    with open(handler, encoding="utf-8", errors="replace") as fh:
        driver = fh.read()
    result["layout"] = parse_handler_layout(driver)
    dispatch = dispatch_table(driver)
    result["handler"] = dispatch.get(T1WR_IOCTL)
    result["handler_method"] = handler_method(driver, result["handler"] or "")
    # Every IOCTL the driver implements, with the method its handler evaluates.
    # Read off the decompile rather than from `ACPI_TMP_IOCTLS`, which is only
    # the Temp* subset and exists so the reachability table can name the six
    # the issue is about.
    result["dispatch"] = dispatch
    result["methods"] = {func: handler_method(driver, func)
                         for func in dispatch.values()}

    if native:
        for label, rel in NATIVE_INPUTS:
            path = os.path.join(REPO, rel)
            if not os.path.exists(path):
                result["native"].append((label, rel, [], "missing"))
                continue
            listing = listing_for(path)
            if not listing:
                result["native"].append((label, rel, [], "no disassembler"))
                continue
            instructions = parse_listing(listing)
            exports = _pe_exports(path)
            image_base = _image_base(path)
            sites = native_sites(label, path, instructions, image_base, exports)
            result["native"].append((label, rel, sites, "read"))

    result["power"] = power_limit_route(
        os.path.join(REPO, "windows/decompiled/v3.1.39.0/ec-callsites.csv"),
        lambda m: ioctl_of_method(m, flat, consts))
    result["rows"] = reachability(
        [s for s in result["sites"] if s.get("ioctl") == T1WR_IOCTL])
    return result


def _image_base(path):
    sys.path.insert(0, HERE)
    try:
        import pe_triage
        with open(path, "rb") as fh:
            return pe_triage.PE(fh.read()).image_base
    except Exception:
        return 0


# What the write-up quotes, asserted against the committed tree. Each entry is a
# *claim*, not a count of the repository: the set of ACPI IOCTLs the decrypted
# service can send, the method the `0x9C40A4DC` handler dispatches to, and the
# buffer slices that decide what a caller's `Arg0` is. A figure that moves
# because a legitimate re-export landed is not held here.
EXPECTED_HANDLER = "FUN_140002614"
EXPECTED_HANDLER_METHOD = "T1WR"
EXPECTED_LAYOUT = {
    "argument_count": 3,
    "buffer_length": 0x28,
    "arg_length": 0x40000,
    "slices": [(0, 3), (4, 7), (8, 11)],
}
# The ACPIDriver control codes a committed site in the decrypted service can
# send, as (IOCTL, ACPI method the driver evaluates for it). Stated as the set
# the claim rests on -- "0x9C40A4DC is declared once and passed to nothing"
# is a claim about this set's membership -- rather than as a count of sites,
# which a legitimate re-export moves. Note what is *not* here: none of the six
# Temp* codes. A future dump that binds one is the drift this is written to
# catch, and it is the same assertion `t1wr_callers.py` makes about the
# service's `ACPIDriverDll.dll` P/Invoke.
EXPECTED_SERVICE_IOCTLS = {
    0x9C40A488: "ECRR", 0x9C40A48C: "ECRW",
    0x9C40A4A0: "PCRD", 0x9C40A500: "SMRW",
}
EXPECTED_POWER_IOCTL = 0x9C40A48C      # ECRW, the one the CPU-PL writes use


def self_check(c):
    """The census the write-up quotes, asserted against the committed tree."""
    drift = []
    layout = c["layout"]
    if layout is None:
        drift.append("the 0x9C40A4DC handler layout did not re-derive from "
                     "windows/decompiled/native/ACPIDriver.c")
    else:
        for key, want in EXPECTED_LAYOUT.items():
            if layout.get(key) != want:
                drift.append(f"handler {key}: expected {want}, got {layout.get(key)}")
    if c["handler"] != EXPECTED_HANDLER:
        drift.append(f"0x9C40A4DC dispatches to {c['handler']}, "
                     f"expected {EXPECTED_HANDLER}")
    if c["handler_method"] != EXPECTED_HANDLER_METHOD:
        drift.append(f"the 0x9C40A4DC handler evaluates {c['handler_method']}, "
                     f"expected {EXPECTED_HANDLER_METHOD}")

    # Scoped to the codes `ACPIDriver.sys` actually implements, read off its own
    # dispatch table. The service also issues battery-class (`0x0029xxxx`) and
    # radio (`0x0047C400`) control codes, which go to other drivers entirely and
    # say nothing about the EC; the claim is about the driver's own surface.
    implemented = set(c.get("dispatch") or {})
    sent = {site["ioctl"] for site in c["sites"] if site.get("ioctl")}
    acpi = {code for code in sent if code in implemented}
    temp = {code for code in acpi if code in ACPI_TMP_IOCTLS}
    if temp:
        drift.append(f"a committed managed site now sends a TempWrite/TempRead "
                     f"code: {sorted(hex(x) for x in temp)}")
    if acpi != set(EXPECTED_SERVICE_IOCTLS):
        drift.append("the decrypted service's ACPIDriver IOCTL set changed: "
                     f"expected {sorted(hex(x) for x in EXPECTED_SERVICE_IOCTLS)}, "
                     f"got {sorted(hex(x) for x in acpi)}")
    # The method names beside the codes have to be the ones the driver
    # evaluates, or the table is a second copy of the export directory's
    # claims and would drift from it without anything here noticing.
    methods = c.get("methods") or {}
    for code, want in EXPECTED_SERVICE_IOCTLS.items():
        got = methods.get((c.get("dispatch") or {}).get(code))
        if got != want:
            drift.append(f"0x{code:08X} evaluates {got}, expected {want}")

    for term, why, hits in c["probes"]:
        if not hits:
            drift.append(f"the readability probe {term!r} came back zero, so "
                         f"this run's zeros cannot be trusted ({why})")

    for addr, info in sorted(c["power"].items()):
        if addr not in POWER_LIMIT_ADDRS:
            drift.append(f"power_limit_route returned 0x{addr:04X}, which is "
                         f"not one of the addresses asked about")
        elif not info["resolved"]:
            drift.append(f"the CPU power-limit write to 0x{addr:04X} no longer "
                         f"resolves to one IOCTL; re-derive the route")
        elif info["ioctl"] != EXPECTED_POWER_IOCTL:
            drift.append(f"0x{addr:04X} now routes through "
                         f"0x{info['ioctl']:08X}, expected "
                         f"0x{EXPECTED_POWER_IOCTL:08X}")

    if drift:
        print("t1wr_sites: the census has drifted from the committed tree",
              file=sys.stderr)
        for d in drift:
            print("  " + d, file=sys.stderr)
        print("\nIf a committed input genuinely changed, re-run the census, "
              "re-bake the EXPECTED_* tables here, and record the new figure "
              "in a file under docs/findings/ -- docs/findings.md is frozen, "
              "so it is not a page to edit.", file=sys.stderr)
        return 1
    print(f"t1wr_sites: census matches the committed tree -- 0x{T1WR_IOCTL:08X} "
          f"is dispatched to {c['handler']}, which evaluates "
          f"{c['handler_method']}({layout['argument_count']} args from "
          f"SystemBuffer{layout['slices']}), and no committed site sends it")
    return 0


def render(c, verbose):
    out = sys.stdout.write
    out("T1WR call-site census. Every row is a committed call site, not an\n"
        "estimate, and a zero means 'not found by this method'. What a site\n"
        "reaches is evidence about who writes a byte -- not about what the EC\n"
        "does with it.\n\n")

    out("== the reading key: what the 0x%08X handler does with a buffer ==\n"
        % T1WR_IOCTL)
    layout = c["layout"] or {}
    out(f"  handler        {c['handler']}  (windows/decompiled/native/"
        "ACPIDriver.c)\n")
    out(f"  evaluates      {c['handler_method']}\n")
    out(f"  ArgumentCount  {layout.get('argument_count')}\n")
    out(f"  buffer length  0x{layout.get('buffer_length', 0):X}\n")
    out(f"  arguments      SystemBuffer{', '.join(str(s) for s in layout.get('slices', []))}"
        "  (each with Length 0x%X)\n" % (layout.get("arg_length") or 0))
    out("  so a caller's Arg0 is the first four bytes of the buffer it sent.\n\n")

    out("== reachability, one row per T1WR arm ==\n")
    out("  Arg0   dsdt   reachable   what the arm reaches\n")
    for row in c["rows"]:
        fields = ", ".join(f[0] for f in row["fields"]) or "(nothing)"
        mark = "yes" if row["reachable"] else "no "
        out(f"  0x{row['arg0']:04X}  :{row['line']}  {mark}          {fields}\n")
        if row["reachable"] or "unreachable" in row["note"]:
            out(f"                    {row['note']}\n")

    out("\n== committed sites issuing a driver IOCTL ==\n")
    out("  Every managed site that resolves a control code, and the ACPI\n"
        "  method the driver's own dispatch table evaluates for that code.\n"
        "  A code the driver does not implement has no method and is marked\n"
        "  so rather than left blank.\n")
    found = [s for s in c["sites"] if s.get("ioctl")]
    if not found:
        out("  (no committed managed site issues an IOCTL this tool could "
            "resolve)\n")
    for site in sorted(found, key=lambda s: (s["ioctl"], s["file_line"])):
        handler = (c.get("dispatch") or {}).get(site["ioctl"])
        method = handler and c.get("methods", {}).get(handler)
        out(f"  0x{site['ioctl']:08X} {(method or '(not an ACPIDriver code)'):<22}"
            f" {site['file_line']}"
            f"  [{site['resolved']}{' via ' + site['via'] if site['via'] else ''}]\n")

    out("\n== sites whose code is the caller's parameter, not a literal ==\n")
    out("  These forward a code rather than choosing one. They are the wrapper\n"
        "  bodies; the sites that settle their code are the rows above.\n")
    forwarded = [s for s in c["sites"] if s.get("ioctl") is None]
    if not forwarded:
        out("  none\n")
    for site in sorted(forwarded, key=lambda s: s["file_line"]):
        out(f"  {site['file_line']}  {site['method']}\n")

    out("\n== native layer: disassembly of every committed PE ==\n")
    for label, rel, sites, state in c["native"]:
        if state != "read":
            out(f"  {label}\n    NOT READ ({state}) -- its zero is not evidence\n")
            continue
        if not sites:
            out(f"  {label}\n    (no 0x{T1WR_IOCTL:08X} site and no TempWrite* "
                "call found by this method)\n")
            continue
        out(f"  {label}\n")
        for va, kind, ioctl, arg0 in sites:
            arg = (f"Arg0 0x{arg0:04X}" if arg0 is not None else
                   "Arg0 not resolved at this site")
            out(f"    0x{va:X}  {kind}  ({arg})\n")
        if verbose:
            out(f"    {rel}\n")

    out("\n== the CPU power-limit question ==\n")
    out("  Whether anything in the committed Windows stack writes APL1/APL2/APL4\n"
        "  (0x0783-0x0785) or APTC/APTN (0x0786), and through which IOCTL.\n")
    for addr, info in sorted(c["power"].items()):
        ioctl = (f"0x{info['ioctl']:08X}" if info["resolved"]
                 else "not resolved")
        out(f"  0x{addr:04X}  {len(info['writers']):>3} committed write(s)"
            f"  via {', '.join(info['methods'])}  ->  {ioctl}\n")
    if all(info["ioctl"] == EXPECTED_POWER_IOCTL for info in c["power"].values()):
        out(f"  All of them route through 0x{EXPECTED_POWER_IOCTL:08X}, which is\n"
            "  the ECRW byte write -- not through T1WR. A Linux driver needs no\n"
            "  ACPI method call for this path.\n")
    out("  What the EC does with the value is not claimed here, and is not\n"
        "  what ec/annotations/registers.yaml's status: says either.\n")

    out("\n== readability probes (not caller evidence) ==\n")
    out("  A term this input is known to carry. They are here so that a zero\n"
        "  in the tables above reads as 'the name is not in there' rather than\n"
        "  'the scan did not reach the source'.\n")
    for term, why, hits in c["probes"]:
        out(f"  {hits:>3}  {term}  ({why})\n")
    if all(not hits for _t, _w, hits in c["probes"]):
        out("  every probe is zero: this run read nothing, and its zeros "
            "mean nothing.\n")

    out("\n== readability census: ILSpy error markers, per tree ==\n")
    out("  A marker means the method bodies under it were never decompiled, so\n"
        "  every site in them is unsearched. Counted per tree because a clean\n"
        "  tree and a damaged one are different claims.\n")
    for label, count in c["unreadable"]:
        out(f"  {label}: {count}\n")

    out("\n== unreadable by this method ==\n")
    out("  The negatives above are only as good as this list. Everything named\n"
        "  here is a place the search could not reach, not a place it looked\n"
        "  and found nothing.\n")
    for note in UNSTAGED_INPUTS:
        out(f"  {note}\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", action="store_true",
                    help="name the input behind every row")
    ap.add_argument("--self-check", action="store_true",
                    help="assert the census the write-up quotes")
    ap.add_argument("--no-native", action="store_true",
                    help="skip the disassembly layer (no binutils or radare2)")
    args = ap.parse_args(argv)

    c = census(native=not args.no_native)
    if args.self_check:
        return self_check(c)
    return render(c, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
