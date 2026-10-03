#!/usr/bin/env python3
"""Whose name a Ghidra project is recorded under, and how to retake it.

A committed `.rep` carries `<STATE NAME="OWNER" TYPE="string" VALUE="dave" />`
in its `project.prp`, and `analyzeHeadless` refuses to open a project owned by
anyone else -- `ghidra.util.NotOwnerException: Project is owned by dave` -- before
it reads a single annotation. That makes the default export path unusable for
every contributor whose username is not that one, on the documented
non-destructive route as much as on a rebuild.

**The owner state is the whole of the gate, and it is measured rather than
assumed.** All three committed projects carry the byte-identical line. The
username also appears inside the `idata/*/~*.db/*.gbf` blobs -- far more often,
as a length-prefixed field in a per-object record, paired with 8051 register
symbols and function symbols alike -- and those records are *provenance baked
into the database* rather than the lock: rewriting `project.prp` alone is what
let a completed export re-derive the committed tree byte for byte.
`docs/findings/ghidra-project-owner.md` carries the measurement and what it
does not establish. So this touches `project.prp` and nothing else, and the
`.gbf` blobs are left alone.

**The rewrite happens in the disposable copy, and the committed tree is never a
target.** `export-only` exists to copy the committed project to scratch and work
there, so the copy is where this belongs; `**/*.rep/**` is `binary -diff -merge`
in `.gitattributes`, which makes a change to a committed `.rep` a hard conflict
for every open branch rather than a reviewable diff. `rewrite_owner()` refuses a
`rep_dir` that is not under a scratch root the caller names, so it cannot
become the thing that writes that file even by accident.

**Rejected, and why:** `JAVA_TOOL_OPTIONS=-Duser.name=<owner>`, which several
write-ups used to get a run through. It makes the JVM assert an identity it does
not have, and the export-only post-scripts *write* to the copy -- every record
they add would then be attributed to an account nobody is logged in as. It is a
way to stop depending on the workaround, not a mechanism to ship. It also does
nothing for a caller that is not a JVM: this module's own `owner_problems()`
has to work without one.

**What this is not.** A claim about Ghidra's internals. Nothing here reads
Ghidra's source; the claim is that rewriting the owner state in a scratch copy
is sufficient for the open, which a full export and this repository's
end-to-end oracle run are the evidence for. Whether Ghidra would also have
objected to something in the database is not established, and no scan finding
nothing here should be reported as one.
"""

import getpass
import os
import re

# The `.rep` directory's own state file. The path is `<project_dir>/<name>.rep`,
# so a caller hands over the `.rep` itself rather than the project directory --
# one level of guessing fewer, and the `.rep` name differs per component
# (`ec.rep`, `bios.rep`, `uniwill_native.rep`) so a caller that derived it would
# have to know the component's project name to write a path.
PRP = "project.prp"

# The one STATE element Ghidra's ownership check reads. Matched on the element
# and the attribute name rather than by substring, so a `VALUE="dave"` sitting
# on some other STATE cannot be mistaken for the owner and rewritten -- which is
# the difference between retaking a project and corrupting one.
_STATE = re.compile(
    r'(<STATE\s+NAME="OWNER"\s+TYPE="string"\s+VALUE=")([^"]*)("\s*/>)')


def within(path, root):
    """Whether `path` is `root` or something under it, both realpath'd.

    realpath on both sides because the answer has to survive a symlinked
    temporary directory: `/tmp` is a symlink on macOS, and comparing the
    unresolved strings would decide that a scratch directory under it is
    outside a root that is itself under it.
    """
    a = os.path.realpath(path)
    b = os.path.realpath(root)
    return a == b or a.startswith(b.rstrip(os.sep) + os.sep)


def project_prp(rep_dir):
    """The `project.prp` inside a `.rep` directory."""
    return os.path.join(rep_dir, PRP)


def read_owner(rep_dir):
    """The user name a `.rep` records as its owner, or None if it records none.

    Returns None for an absent state rather than raising, because "this project
    claims no owner" and "this file does not parse" are different answers and a
    caller has to be able to tell them apart -- the second is a problem to
    report, the first is a layout this module will not guess at. A file that is
    not XML at all, or is XML with no OWNER state, raises; see `owner_problems()`
    for the same facts as strings rather than as an exception.
    """
    prp = project_prp(rep_dir)
    with open(prp) as f:
        text = f.read()
    if "<" not in text:
        raise ValueError("%s is not XML: no element in it at all" % prp)
    m = _STATE.search(text)
    return m.group(2) if m else None


def rewrite_owner(rep_dir, scratch_root, user=None):
    """Point a `.rep`'s owner state at `user` -- the running user by default.

    Returns a one-line report of what it did, `already <user>` or
    `rewrote <old> -> <user>`, so a caller can print the change rather than
    making it silently. The second spelling is what a reviewer looks for in the
    log: it is the difference between a run that took the project over and a
    run that had nothing to do.

    `scratch_root` is not optional. This writes a file `.gitattributes` marks
    `-merge`, so the guard is in the signature where the next caller cannot
    avoid it: a `rep_dir` outside the root is refused before the file is opened,
    not after. That is the invariant that makes the module safe to add at all --
    the failure it prevents is a hand-edited committed `.rep`, which is a hard
    conflict for every open branch and not a reviewable diff.

    `user` defaults to the running user rather than to whatever the file says,
    so the default is the identity Ghidra is about to compare against and not
    the identity already in the file.
    """
    if not within(rep_dir, scratch_root):
        raise SystemExit(
            "error: refusing to rewrite the owner of %s\n"
            "  It is not under the scratch root %s, so this would be writing a\n"
            "  committed .rep -- which .gitattributes marks -merge, so the change\n"
            "  is a hard conflict for every open branch rather than a diff anyone\n"
            "  can read. Point this at a copy." % (rep_dir, scratch_root))
    prp = project_prp(rep_dir)
    with open(prp) as f:
        text = f.read()
    if "<" not in text:
        raise SystemExit("error: %s is not XML; refusing to guess at a Ghidra "
                         "project layout" % prp)
    m = _STATE.search(text)
    if m is None:
        raise SystemExit("error: no OWNER state in %s; refusing to guess at a "
                         "Ghidra project layout" % prp)
    owner = m.group(2)
    me = getpass.getuser() if user is None else user
    if owner == me:
        return "already %s" % me
    # One substitution of the captured prefix and owner, not a whole-file
    # `replace` of VALUE="dave": a second STATE carrying the same value would
    # otherwise be rewritten too, and the only reason to touch this file is the
    # one line Ghidra reads.
    with open(prp, "w") as f:
        f.write(text[:m.start()] + m.group(1) + me + m.group(3)
                + text[m.end():])
    return "rewrote %s -> %s" % (owner, me)


def owner_problems(rep_dir, expect_user=None):
    """What is wrong with a `.rep`'s owner state, as a list of strings. Empty is
    a pass.

    The `*_problems()` shape `structure_problems()` and
    `charge_target_facts_problems()` already use in this repository: a list of
    messages naming the file, empty when nothing is wrong, and never an
    exception for a content fault. A caller that only wants to *report* the
    state -- a check, rather than a fix -- gets every fault it can name rather
    than the first one it trips over.

    `expect_user` is the owner the caller wants; None asks only that the state
    be readable and present. Pure, so a caller can hand it a deliberately broken
    copy and watch it object -- an assertion nobody has seen fail is not an
    assertion.

    Not checked, deliberately: the `.gbf` records in `idata/`, which carry the
    same string as database provenance. They are not the gate
    (`docs/findings/ghidra-project-owner.md`), and reporting them here would
    make every `.rep` in the repository look defective on a check that has
    nothing to do with them.
    """
    prp = project_prp(rep_dir)
    name = os.path.join(os.path.basename(os.path.normpath(rep_dir)), PRP)
    if not os.path.isfile(prp):
        return ["%s: no project.prp; this is not a .rep directory" % name]
    try:
        with open(prp) as f:
            text = f.read()
    except OSError as e:
        return ["%s: does not read: %s" % (name, e)]
    # Not a well-formedness check, only a cheap one: enough to tell this file
    # from a binary, so a `.rep` handed over by mistake is reported rather than
    # searched for a string in.
    if "<" not in text:
        return ["%s: is not XML" % name]
    m = _STATE.search(text)
    if m is None:
        return ["%s: carries no OWNER state, so there is nothing to retake and "
                "this is not the layout Ghidra writes" % name]
    owner = m.group(2)
    if not owner:
        return ["%s: the OWNER state is empty" % name]
    if expect_user is not None and owner != expect_user:
        return ["%s: is owned by %s, not %s, so analyzeHeadless would raise "
                "NotOwnerException before it read an annotation"
                % (name, owner, expect_user)]
    return []