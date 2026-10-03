# Four Windows tools bound a Win32 DLL at import, so a grader had to transcribe the watch table, and the DLLs now load on first use (issue #353)

The write-up for [issue
#353](https://github.com/ElDavoo/tongfang-gm7mg7p-re/issues/353), opened by the
follow-ups pass out of #303. #303 worked around a constraint and named it as
one; this is the constraint going away, and what it cost to remove.

**Everything here is a file and a command-line fact**, reproduced from
committed sources on disk. No image is opened, no register is read back, and no
EC, laptop or Windows machine is involved. The tools still need the vendor
stack's driver and elevation to do their actual work; what is established below
is that importing them anywhere is no longer what prevents that from being
attempted.

## What the import-time binding cost, measured

`windows/tools/ecrw.py` began with a module-scope

```python
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
```

and then assigned `argtypes`/`restype` onto `_k32` at module scope too.
`ctypes.WinDLL` exists only on Windows, so on this runner that line raised
`AttributeError` before the module body finished, and every module doing
`from ecrw import ...` died with it. Three more tools had the same shape and
the same effect: `uefi_var.py` (three DLLs), `uniwill_set.py` (which reaches
`uefi_var._k32` at module scope), and `dotnet_dump.py` (three DLLs).

Every non-suite module in `windows/tools/`, imported the way a tool in that
directory would import it — the directory on `sys.path`, each module loaded by
path under its own name:

```console
$ python3 - <<'PY'
import importlib.util, sys, pathlib
TOOLS = pathlib.Path("windows/tools").resolve()
sys.path.insert(0, str(TOOLS))
for f in sorted(TOOLS.glob("*.py")):
    if f.name.startswith("test_") or f.name == "ecrw_fake.py":
        continue
    spec = importlib.util.spec_from_file_location("m_" + f.stem, f)
    m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m); print("OK  ", f.name)
    except Exception as e:
        print("FAIL", f.name, type(e).__name__, e)
PY
```

gave one `AttributeError` per module that reaches a DLL — binding one itself at
module scope, or importing `ecrw` or `uefi_var`, which bound theirs — and an
`OK` line for every module that reaches none. Run against the tree as it
stands, the same loop reports no failure from a DLL bind; on a checkout
without the two packages `.github/actions/project-setup` installs, it also
names `dotnet_bodies.py` and `dotnet_dump.py` wanting `dnfile` and `pefile`,
which is what the suite's third exclusion is for (see "What holds it" below).
Which modules fall on which side is a property of the tree at a given commit
rather than of the method, so the command above is where to read the split.

**The tax the issue named was real and it was not confined to the grader.**
`ecrw_fake.py` exists because a module that could not be imported had to be
replaced before every offline suite could load the tool it exercises.
`ec/tools/grade_gpu_door.py` transcribed `gpu_block_watch.py`'s two window
bounds and its ECMG field-list names, one per watched address, and
`windows/tools/test_gpu_block_watch.py`'s `GraderAgreementTests` existed only
to hold that transcription against the original — the same shape of hold that
caught the procedure's four stale cells in #266.

## Three corrections to the issue's account

The issue's `#353` text is the starting point, and three of its statements do
not survive contact with the tree. They are recorded here because the write-up
rests on what is actually true.

**`from ctypes import wintypes` does not raise on Linux.** Measured on the
CPython `.github/actions/project-setup` installs (3.12.14 here): it imports,
and every name `ecrw.py` uses resolves — `LPCWSTR` → `c_wchar_p`, `DWORD` →
`c_ulong`, `LPVOID`/`HANDLE` → `c_void_p`, `BOOL` → `c_long`.
`windows/tools/test_ecrw.py`'s own `load_modules` docstring had recorded this
already. `WinDLL` is the only name that has to be standing in. The guard is
still in the code, because it costs four lines and the issue asked for it — but
each module's comment says it is belt-and-braces and not the load-bearing
half, so the next reader does not go looking for a `wintypes` failure that
cannot happen.

**The line numbers are stale.** The bind was `ecrw.py:84` and the signature
block `ecrw.py:86-100`, not `:38,50`. Two pins elsewhere had drifted further:
`test_ecrw.py`'s docstring said `ecrw.py:69`, and two write-ups said `:69` and
`:70`. The first of those moved again with this change, so its docstring now
names `_kernel32` rather than a line.

**The issue names one module; three more had the same defect.** `uefi_var.py`,
`uniwill_set.py` and `dotnet_dump.py` bind a DLL at module scope exactly as
`ecrw.py` did. The Done criterion — a suite that imports *every* module under
`windows/tools/` — cannot be met without fixing them, so they are in scope
here, named as a discovery rather than smuggled in. `dotnet_dump.py` is not a
sibling of the EC tools at all: it is `windows/antitamper/README.md`'s
"approach 2" for dumping a running .NET module's decrypted image, and it
carried the identical shape.

## What the fix is

Each of the four tools keeps its handles in a module-level cache initialised to
`None` and loads them in a resolver on first use — `ecrw._kernel32()` for one
DLL, `uefi_var._load()` and `dotnet_dump._load()` for three each. The
`argtypes`/`restype` assignments moved into the resolver with the handle they
are written onto, because they cannot be written before there is something to
write them on. Off Windows the resolver raises rather than importing:
`ecrw.Ec()` raises `ecrw.EcError` naming the platform, which lands in
`main`'s own `except EcError` so the CLI prints it and exits 1, and
`uefi_var`/`dotnet_dump` raise `SystemExit` in the shape those tools already
use for their other failures.

`Ec.__init__` stores the handle it got on `self`, so `close()` and `_ioctl()`
read `self._k32`. That is a deliberate change from reading a module global: a
handle the object was not given is a handle whose provenance is a question
rather than a field.

**Nothing about what any IOCTL does has changed.** The same three codes go on
the wire, the same little-endian marshalling fills the buffer, the same
`CreateFileW` opens `\\.\ACPIDriver`. `test_ecrw.py` still runs `read_dword`
and `readmany` for real against a fake kernel32 and asserts on the bytes that
would have gone out; what moved is *when* the DLL is bound, not what is sent.
That suite's fake window had to widen accordingly: the fake `ctypes.WinDLL` is
now primed inside `load_modules` and cached on the module by the resolver, so
`Ec()` constructions after the window are the same handle.

## The grader states its table by reference

`ec/tools/grade_gpu_door.py` inserts `windows/tools/` on `sys.path` and does a
plain `import gpu_block_watch`, then derives:

```python
WINDOWS = gpu_block_watch.WINDOWS
DS_NAMES = tuple((addr, name) for addr, name, _status, _cite
                 in gpu_block_watch.WATCH)
```

This inverts the direction that already existed:
`windows/tools/test_gpu_block_watch.py` loads the grader by path because a
suite cannot import a tool out of another tree, whereas a tool in `ec/tools`
may insert that tree's directory and import from it. The asymmetry is the
point — the copy that drifted is gone.

**`GraderAgreementTests` is deleted, not weakened.** Holding
`grader.DS_NAMES` against `watch.WATCH` would now be asserting that a value
equals a comprehension over itself, which is a tautology and no coverage at
all. Nothing tautological replaces it. What replaces it is a check with a
subject of its own, in `ec/tools/test_grade_gpu_door.py`: that the grader can
*name* every address its own bounds cover, in both directions. `name_of`
raises `KeyError` rather than returning a blank, so a capture carrying a row
inside the bounds but outside the name table fails the grader's own report
halfway through printing it. That is a real invariant; "these two copies are
equal" was not, once there was one copy.

The chain from the DSDT is unchanged and still closed: `CitationTableTests` in
`test_gpu_block_watch.py` holds `watch.WATCH` against
`evidence/acpi/dsdt.dsl`, so the ECMG field list is read once, in one place,
and the grader's §5 column names it from there.

**One cost, stated.** `ec/tools/scan_mark_collisions.py` imports the grader, so
it now pulls `windows/tools/gpu_block_watch.py` in with it. That is one more
`ctypes`-adjacent module on an offline tool's import path, and it is part of
why the new suite's subject set is the whole directory rather than the four
tools this change touched.
`ec/tools/measure_mark_provenance.py` is unaffected: it loads
`grade_0751_isolation`, which imports nothing but stdlib.

## What holds it

`windows/tools/test_import_off_windows.py` is the Done criterion, and it does
it by importing rather than by mocking. A stand-in for `ctypes.WinDLL` would
prove nothing — it would be satisfied by a module that binds a DLL it never
calls. The module-scope bind raises `AttributeError` out of `exec_module` and
the failure names the module, so the mechanism *is* the assertion. Restoring a
module-scope bind to `ecrw.py` was tried and the suite reported every
affected module by name.

Its subject set is every `*.py` in the directory that is not a `test_*.py`
suite and not `ecrw_fake.py` — by glob, so a new tool joins by being committed
rather than by being listed. Two exclusions rather than none, and both stated
in the module docstring: suites install their own fakes before importing what
they exercise, and `ecrw_fake.py` is the fixture rather than a tool.

**A third exclusion is by failure rather than by name, and it was this
reviewer's doing.** The first run of the suite on a checkout without
`.github/actions/project-setup`'s `pip install pyyaml pefile dnfile` failed, and
the two entries it named were `ModuleNotFoundError` for `dnfile` and `pefile`
— `dotnet_bodies.py` and `dotnet_dump.py`, which import those at module scope.
`windows/README.md` already recorded the dependency, so the tree knew and the
suite did not. It now classifies rather than reports: a `ModuleNotFoundError`
naming something outside the standard library and not provided by this
directory is reported as what it is, a tool that wants a package from pip, and
everything else is a failure. The exception type is what decides, and that is
not a detail — an `AttributeError` from a module-scope `ctypes.WinDLL` carries
`.name == 'WinDLL'`, so a classifier that reads the name off any exception with
one excuses the bind this suite exists to catch and passes on a tree that has
it back. A test holds that against the raised exception rather than a
hand-built one, because a hand-built `AttributeError` has `name=None` and is
satisfied by the classifier that gets this wrong. So the claim is "every
non-suite module here that has no third-party dependency imports off Windows",
and on a checkout without those two packages the two .NET tools are not covered
by this half — they still are by the symtable walk below, which reads source
and never imports, and CI installs the packages.

A second check in that suite exists because moving handles out of module scope
turns a typo in a function body from an `AttributeError` at import into a
`NameError` when the tool is next run — on Windows, against the driver, with
nobody watching. Two such typos were written and caught by hand while making
this change, in `ecrw.Ec.__init__` and in `dotnet_dump.main`. `symtable` walks
each tool's scope tables and reports a name that is read but bound in no
scope, which is a static question a run on this runner cannot answer.

## What is deferred, and why

**`ecrw_fake.py` stays, and the offline suites are not converted off it.**
The issue asks for this too ("have the offline suites import the real modules
and decide from there whether `ecrw_fake.py` still earns its place") and it is
the right follow-up. It is deferred because each of those suites needs its own
decision about how it scripts bytes — patch the tool's `Ec` in its namespace
with a class that answers a fixture, or keep a local fake — and those suites
are the leaf files other open pull requests are most likely to be editing.
Nothing is at risk by waiting: the new suite proves every module that wants no
pip package imports, so the fixture's remaining job is scriptability, not
importability.

A correction to what this defers, because it was checked rather than repeated:
the per-suite fakes that used to lose the `sys.modules.setdefault` race are
gone. Every suite that installs the fixture now calls
`ecrw_fake.install()`, which writes unconditionally, and
`tools/test_windows_tools_shared_interpreter.py` holds both halves of that.
What is left is not an ordering hazard to fix but a shape to decide on: each
suite picks whether its scripted bytes arrive as a class patched over the
tool's `Ec` or as a local fake, and the fixture is what that decision is about.
That is the whole of the remaining work here.

## Two things this does not claim

**No live test ran.** Nothing here was run against the vendor driver, on
Windows, or on the machine. Confirming the lazy resolver against a real
`CreateFileW` — that the handle opens, that the IOCTLs still return the same
registers, that `close()` releases it — is a human's run with the driver
loaded and elevation.

**Importable is not working.** A green run of the new suite says a module's
pure-Python surface loads anywhere. `ecrw.py` still needs `UWACPIDriver.sys`
present and started and the process elevated; `uefi_var.py` and
`dotnet_dump.py` still need the same. Nothing about a register's behaviour, and
no `status:` in `ec/annotations/registers.yaml`, is touched by this.

The correction to `docs/findings/ecrw-fake-one-shape.md`, which said "it is not
#353 … does not touch `ecrw.py`", is in that file's own terms a statement made
before #353 landed; it is left visible rather than edited, per the §4a-4d
pattern in `docs/findings.md`.