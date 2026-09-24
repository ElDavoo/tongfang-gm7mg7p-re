#!/usr/bin/env python3
r"""The offline stand-in for `ecrw.py`, shared by every suite in this directory.

`ecrw.py` binds kernel32 at import time, so it cannot be imported off Windows at
all -- which is why the offline suites have to hand the tools a module of their
own before importing them. There used to be one of those per suite, and they
were not the same shape: whichever installed itself first won the
`sys.modules.setdefault` and the other died on `from ecrw import Ec, EcError`.
That ordering accident, and the rename that trips it, is in
`docs/findings.md` §16; it is no longer a variable because there is now one
shape to install.

This is a test fixture, not a second implementation of `ecrw.py` and not a
substitute for running against the vendor driver. A green offline run here says
the tool's own logic behaves on a fixture -- no EC is opened, no register is
read back. `ecrw.py` is unchanged and stays the only thing that talks to
`\\.\ACPIDriver`.
"""
import sys
import types


class EcError(RuntimeError):
    """The real class's base, which is the only part of it that carries.

    `ec_watch.py` wraps its whole run in `except EcError`, so an exception
    class that were not a RuntimeError would quietly change what that clause
    covers. Matching the base keeps that a non-question.
    """


class Ec:
    """The real signatures and the whole protocol, and no behaviour.

    No suite calls these bodies: both suites that exist replace `Ec` wholesale
    with a class of their own once the tool module is imported, so the defaults
    here only have to keep an import -- or an accidentally unpatched call --
    from failing on a missing attribute. A suite that needs bytes has to say so
    by supplying its own class rather than by finding a default it likes, which
    is why `read` returns 0x00 and nothing else here does anything.
    """

    def __init__(self):
        pass

    def read(self, addr):
        return 0x00

    def write(self, addr, val):
        pass

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def install():
    """Put the fake in `sys.modules` under the name `ecrw`, and return it.

    Assignment rather than `setdefault`, deliberately. Both suites install these
    same two class objects, so nothing can depend on which of them got there
    first, and the unconditional write means a suite can never inherit a stale
    sibling's shape -- which is the whole of what the two per-suite fakes did.
    """
    module = types.ModuleType('ecrw')
    module.Ec = Ec
    module.EcError = EcError
    sys.modules['ecrw'] = module
    return module
