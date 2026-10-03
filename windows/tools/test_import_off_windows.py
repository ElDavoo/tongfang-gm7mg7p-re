#!/usr/bin/env python3
r"""Every non-suite module here that wants no pip package imports off Windows.

These tools are deployed as a directory rather than as a package, and four of
them used to bind a Win32 DLL at module scope -- `ctypes.WinDLL` exists only on
Windows, so importing one raised `AttributeError` before the module body
finished, and took every module that did `from ecrw import ...` down with it.
That is how `ec/tools/grade_gpu_door.py` came to transcribe its own copy of
`gpu_block_watch.py`'s watch table: the grader could not import the tool whose
capture it grades. The DLLs are bound on first use now, and this is the suite
that says so, so the next one to reach for `ctypes.WinDLL` at module scope
fails here by name rather than in a grader's docstring.

**No mocking, and that is the assertion.** A stand-in for `WinDLL` would prove
nothing -- it would be satisfied by a module that binds a DLL it never has to
call. `ctypes.WinDLL` does not exist on this platform, so a module-scope bind
raises `AttributeError` out of `exec_module` and the failure names the module.
The mechanism *is* the check.

**Subject set: every `*.py` here that is not a `test_*.py` suite and not
`ecrw_fake.py`.** Suites are excluded because each imports the tools and
substitutes its own fakes, and `ecrw_fake.py` because it is the fixture that
substitutes for `ecrw` rather than a tool. Both exclusions are by glob, so a
new tool joins this suite by being committed here rather than by being listed.

**A third exclusion, by failure rather than by name: a tool that wants a
package from pip.** `dotnet_dump.py` and `dotnet_bodies.py` import `pefile` and
`dnfile` at module scope, which `.github/actions/project-setup` installs and
`windows/README.md` records, so on a checkout without them those two cannot
import at all. That is a property of the checkout, not a defect to fix here,
and it is reported as its own thing rather than as a bind -- a reader sent to
look for a module-scope `WinDLL` in `dotnet_bodies.py` will not find one.
`_pip_dependency` is what tells the two apart, and it is deliberately narrow:
only a `ModuleNotFoundError` naming something outside the standard library and
not provided by this directory is excused. A missing *stdlib* module is a real
failure, and so is a missing sibling, because `TOOLS` is on `sys.path` and a
name this directory provides is a broken import rather than an uninstalled
one.

What that costs is narrow and worth stating rather than leaving to be
discovered: on a checkout without those two packages, the two .NET tools are
not covered by the import half of this suite. They still are by
`DanglingHandleTests`, which reads source and never imports, and CI installs
the packages, so a bind in either is caught there rather than here.

**What a green run is not.** Importable is all it says. Nothing opens
`\\.\ACPIDriver`, no IOCTL is issued, no register is read back and no vendor
driver is required -- every module here still needs the vendor stack's driver
and elevation to do its actual work. `EcrwContractTests` states the behavioural
half: constructing an `Ec` off Windows fails with `ecrw.EcError` naming the
platform, rather than reaching for a driver.
"""
import builtins
import ctypes
import importlib.util
import pathlib
import symtable
import sys
import unittest

TOOLS = pathlib.Path(__file__).resolve().parent


def modules():
    """Every tool in this directory, by path, in name order.

    A glob over `TOOLS` rather than a list, so this suite's subject set is a
    property of the directory and not a number some later merge has to edit.
    """
    return [p for p in sorted(TOOLS.glob("*.py"))
            if not p.name.startswith("test_") and p.name != "ecrw_fake.py"]


def load(path):
    """Import `path` under a name of its own, and return the module.

    By path with a private module name, not by `import`: a module's own
    siblings are on `sys.path` here, so `import ec_watch` from
    `test_gpu_block_watch` would resolve to that suite's copy -- or, on a
    shared interpreter, to whichever suite installed a fake `ecrw` first,
    which is the `setdefault` accident `docs/findings.md` §16 records. Loading
    by path with a name prefixed here keeps each module's own namespace, and
    any sibling it imports falls through to the real file in this directory
    unless a suite has already put something under that name -- which is why
    `TOOLS` goes on `sys.path` at the front first, before the fake-installing
    suites have a say.
    """
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    name = "_import_off_windows_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # Not left behind: a half-executed module in `sys.modules` is a trap
        # for whatever reads the name next, and this suite would rather fail
        # here than hand a later one a module that never finished importing.
        del sys.modules[name]
        raise
    return module


def _pip_dependency(error):
    """The pip package `error` names, or None if it is not one.

    The exception *type* is the first question, and it has to be asked before
    the name: an `AttributeError` raised by attribute access carries a `.name`
    too -- `ctypes.WinDLL` binds as `AttributeError(name='WinDLL')` -- so a
    classifier that reads the name off any exception with one excuses the
    module-scope bind this suite exists to catch and reports it as a missing
    pip install. Only `ModuleNotFoundError` says a module could not be found.

    Past that, the name decides. Outside `sys.stdlib_module_names` and not
    provided by this directory, it is a package from PyPI that this runner was
    never given. A missing stdlib module is a real failure -- the interpreter
    is broken, or the tool is being run under the wrong Python -- and a
    missing sibling is a real failure too: `TOOLS` is on `sys.path`, so a name
    this directory provides but cannot import is a broken import here, not an
    uninstalled one. The sibling test is by file, which is the same rule
    `modules()` applies to pick its subject set.
    """
    if not isinstance(error, ModuleNotFoundError):
        return None
    name = error.name
    if not name:
        return None
    top = name.split(".")[0]
    if top in sys.stdlib_module_names or (TOOLS / f"{top}.py").exists():
        return None
    return top


class OfflineImportTests(unittest.TestCase):
    def test_every_module_in_this_directory_imports(self):
        # Collected rather than raised, so one failure does not hide the rest:
        # a bind in `ecrw.py` takes ten other modules with it, and a report
        # naming one of them sends the reader looking at that module instead of
        # the one that caused it. `BaseException` because a module that calls
        # `sys.exit()` at import has not imported either, and that is worth
        # reporting rather than letting it abort the suite.
        failed = []
        needs_pip = []
        for path in modules():
            with self.subTest(module=path.name):
                try:
                    load(path)
                except BaseException as e:
                    package = _pip_dependency(e)
                    if package is not None:
                        needs_pip.append(f"{path.name} ({package})")
                        continue
                    failed.append(f"{path.name}: {type(e).__name__}: {e}")
        self.assertEqual(
            failed, [],
            "these modules cannot be imported on this platform:\n  "
            + "\n  ".join(failed)
            + "\nA Win32 DLL bound at module scope raises here, and takes every "
              "module importing it with it. Bind it on first use instead -- "
              "`ecrw.py`'s `_kernel32()` and `uefi_var.py`'s `_load()` are the "
              "shape -- so the pure-Python surface loads anywhere."
            + (("\nNot failures, and reported apart from them: "
                + ", ".join(needs_pip)
                + " wants a package from pip, which "
                  "`.github/actions/project-setup` installs and "
                  "`windows/README.md` records. On a checkout without it those "
                  "modules are not covered by this test; see the module "
                  "docstring.")
               if needs_pip else ""))

    def test_the_directory_is_not_empty_of_tools(self):
        # The vacuity guard. A glob that matched nothing would make the test
        # above pass on a directory that holds no tools at all, which is the
        # silent-pass shape this suite exists to make loud.
        self.assertTrue(modules(),
                        f"no tool found under {TOOLS}; the glob is wrong, not "
                        "the directory")

    def test_only_a_missing_third_party_package_is_excused(self):
        # The classifier decides what the test above is allowed to ignore, and
        # a classifier that excused everything would leave that test passing on
        # a directory it had imported none of. Held against the shapes
        # `exec_module` actually produces, not against invented ones.
        self.assertEqual(
            _pip_dependency(ModuleNotFoundError("No module named 'pefile'",
                                                name="pefile")),
            "pefile")
        # A missing stdlib module is a broken interpreter, not a pip install.
        self.assertIsNone(_pip_dependency(
            ModuleNotFoundError("No module named 'ctypes'", name="ctypes")))
        # A name this directory provides is a broken sibling import: `TOOLS` is
        # on `sys.path`, so it resolved to something and that something failed.
        self.assertIsNone(_pip_dependency(
            ModuleNotFoundError("No module named 'ecrw'", name="ecrw")))
        # A plain `ImportError` names no module, so there is nothing to excuse.
        self.assertIsNone(_pip_dependency(ImportError("cannot import name")))

    def test_the_bind_this_suite_exists_to_catch_is_not_excused(self):
        # Raised, not written out. An `AttributeError` built by hand has
        # `name=None`, so a hand-built one is satisfied by a classifier that
        # never looks at the type -- and the real bind, the one this suite is
        # here to report, arrives from attribute access with
        # `name='WinDLL'` and `obj=<module ctypes>`. A classifier that reads
        # the name off that exception calls it a missing pip package and the
        # suite above passes on a tree with the bind back in it. Which is what
        # it did, until this test held it against the exception that actually
        # occurs.
        if hasattr(ctypes, "WinDLL"):
            self.skipTest("on Windows kernel32 loads, so this is not the "
                          "failure to expect")
        try:
            ctypes.WinDLL("kernel32")
        except AttributeError as e:
            self.assertEqual(e.name, "WinDLL")
            self.assertIsNone(_pip_dependency(e))
        else:
            self.fail("ctypes.WinDLL exists here, so this test is not holding "
                      "the classifier against anything")


class DanglingHandleTests(unittest.TestCase):
    """No tool here names a DLL handle the module no longer binds.

    Moving a handle out of module scope into a resolver turns a typo in the
    body from an `AttributeError` at import into a `NameError` at the moment
    the tool is run -- on Windows, against the vendor driver, with nobody
    watching. `ecrw.Ec.__init__` taking `self._k32` and `dotnet_dump.main`
    calling `_load()[0]` were each written wrong once while this change was
    being made, and both would have passed every suite here.

    `symtable` rather than a regex or an `ast` walk, because it does the scope
    analysis rather than approximating it: a name is reported only where it is
    neither local, a parameter, nor bound in the enclosing scopes -- so a
    local called `k32` is not a hit, and `_k32` read inside a function with no
    module-level binding for it is.
    """

    def test_no_tool_references_a_name_it_does_not_bind(self):
        dangling = []
        for path in modules():
            top = symtable.symtable(path.read_text(encoding="utf-8"),
                                    str(path), "exec")
            for name, scope in _free_names(top):
                if name not in _bound(top) and not hasattr(builtins, name):
                    dangling.append(f"{path.name}: {name} (in {scope})")
        self.assertEqual(
            dangling, [],
            "these names are read but never bound, so they raise NameError when "
            "the tool runs rather than when it imports:\n  "
            + "\n  ".join(dangling))

    def test_the_check_would_notice_a_dangling_name(self):
        # A check that cannot fail is a check that says nothing, and this one
        # walks a scope table by hand. Held against a source that *is* wrong:
        # `_k32` is referenced and never bound. Not a module in this directory,
        # so it cannot be a claim about the tree -- it is a claim about the
        # walker, which is the part that could quietly return an empty set.
        src = "import ctypes\n\n\ndef f():\n    return _k32.OpenProcess(1)\n"
        top = symtable.symtable(src, "dangling.py", "exec")
        free = {name for name, _ in _free_names(top)} - _bound(top)
        self.assertIn("_k32", free)
        # And it stays quiet on the shape it would otherwise over-report: a
        # comprehension variable is bound in the comprehension's own scope, not
        # in the enclosing function's.
        ok = ("import os\n\n\ndef f(p):\n"
              "    return [os.path.basename(x) for x in p]\n")
        ok_top = symtable.symtable(ok, "ok.py", "exec")
        self.assertFalse({n for n, _ in _free_names(ok_top)} - _bound(ok_top))


def _bound(table):
    """Every name this scope table binds anywhere in the module.

    `__file__` is in the seed because `symtable` reports it referenced and
    never assigned, though the interpreter binds it in every module. Naming it
    rather than filtering on the leading underscores: a tool is far likelier to
    want `__file__` for a path than to define it, and the dunder filter would
    have hidden both.
    """
    bound = {"__file__"}
    for sym in table.get_symbols():
        if sym.is_assigned() or sym.is_imported() or sym.is_parameter():
            bound.add(sym.get_name())
    for child in table.get_children():
        bound |= _bound(child)
    return bound


def _free_names(table):
    """(name, enclosing scope) for every name this scope reads and binds not.

    A symbol counts as free when it is referenced and is neither assigned here
    nor a parameter -- so a comprehension variable, which is assigned in the
    comprehension's own table, is bound and does not come back.
    """
    for sym in table.get_symbols():
        if sym.is_referenced() and not (sym.is_assigned() or sym.is_parameter()):
            yield sym.get_name(), table.get_name()
    for child in table.get_children():
        yield from _free_names(child)


class EcrwContractTests(unittest.TestCase):
    """The lazy resolver's contract, stated behaviourally.

    Structural -- "importing performs no IOCTL" -- is not assertable here
    without a driver to intercept, and is true by construction rather than by
    test: nothing in the import path constructs an `Ec`, which is what these
    two check from the other side.
    """

    @classmethod
    def setUpClass(cls):
        cls.ecrw = load(TOOLS / "ecrw.py")

    def test_ecrw_names_its_pure_python_surface_off_windows(self):
        # The part of the module that carries the procedure's own constants, so
        # a tool importing it for `IOCTL_ECRR` or `EC_BASE` gets them without
        # a Windows host. The IOCTL codes are the claim: they are the numbers
        # `windows/native/ACPIDriver.sys.analysis.md` names, and a grader that
        # could not read them here would have to transcribe them too.
        self.assertEqual(self.ecrw.IOCTL_ECRR, 0x9C40A488)
        self.assertEqual(self.ecrw.IOCTL_ECRW, 0x9C40A48C)
        self.assertEqual(self.ecrw.IOCTL_MMRD, 0x9C40A494)
        self.assertEqual(self.ecrw.EC_BASE, 0xFE410000)
        self.assertEqual(self.ecrw.EC_SIZE, 0x10000)

    def test_constructing_an_ec_off_windows_names_the_platform(self):
        # The "opens no EC" half of the Done line, and the failure a user gets
        # instead of the `AttributeError` traceback the module-scope bind
        # produced. `EcError` rather than anything else because `main`'s own
        # `except EcError` turns it into a message and exit 1, and because
        # `ec_watch.py` and `gpu_block_watch.py` wrap their runs in that clause.
        if hasattr(ctypes, "WinDLL"):
            self.skipTest("on Windows, where kernel32 loads and this is not the "
                          "failure to expect")
        with self.assertRaises(self.ecrw.EcError) as caught:
            self.ecrw.Ec()
        self.assertIn("WinDLL", str(caught.exception))

    def test_the_resolver_leaves_the_handle_unbound(self):
        # That nothing loaded it on the way past: the three tests above import
        # the module and the constructor, and a cached handle would mean one of
        # them had. Read through the module rather than `ctypes`, because
        # `_k32` is private and this is the only place its emptiness is a claim
        # rather than an accident.
        if hasattr(ctypes, "WinDLL"):
            self.skipTest("on Windows this is not a claim about loading")
        self.assertIsNone(self.ecrw._k32)


if __name__ == "__main__":
    unittest.main()