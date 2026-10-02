#!/usr/bin/env python3
"""`.gitattributes` covers every committed CSV a tool byte-compares, and the
form it chose matches the file's measured bytes.

The hazard is the one `.gitattributes` already documents for the decompiled
`.c` trees: a tool's `--check` compares the committed file's **bytes** against
a freshly generated table, so a `core.autocrlf=true` Windows checkout turns a
green gate red for a contributor who did nothing wrong. The attribute removes
the cause. It does not remove the detection, and the last case here is the one
that holds that line: a CRLF table is still rejected, because a check softened
to match a new attribute would report a drifted table as clean.

**The rule, not the census.** Nothing below counts the tree. A count is a value
every landing suite and every new table has to edit, which is the same lock
CLAUDE.md's "no totals of the repository's own text" is about -- and here it
would be worse, because the set of byte-compared tables grows whenever a tool
grows a `--check`. So the cases assert properties:

  - every table named below (a tool's `--check` input or output) is *matched*
    by some `.gitattributes` line;
  - no line covering one says `binary`, which the file's own comment above
    rules out in prose and this turns into a check;
  - no path matched by an `eol=lf` line carries a CR today -- the one that stops
    the next agent marking a CRLF-emitting tool's table `eol=lf` and quietly
    turning several green checks red;
  - `git check-attr` agrees with what the file says, when git is present.

The `.gitattributes` parse stands alone in every case, so the suite cannot pass
vacuously on a machine without git -- which is where a "skip if no git" guard
would leave the whole thing resting on the one check most likely to be absent.

Why the covering set is named rather than discovered: deciding which tables are
byte-compared is a reading of each tool's `--check`, and a regex that guessed it
would report a coverage property over a set it invented. Naming them makes the
claim checkable by a reader and makes a *new* byte-compared table a deliberate
addition to this list, which is the moment someone looks at it.
"""

import importlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import call_graph  # noqa: E402

GITATTRIBUTES = os.path.join(REPO, ".gitattributes")

# Every committed CSV a tool byte-compares in --check, with the tool that owns
# the comparison. Read off each tool's --check arm, not off the tree: a file
# nobody --checks is not a coverage obligation, and covering it anyway would
# make this list a census of the annotations directory instead.
#
# The CRLF half of the set is here as well, and not only under `CRLF_EMITTERS`.
# A tool that byte-compares a CRLF table needs the `-text` blanket for exactly
# the reason `call_graph.py`'s LF table needs `eol=lf`, so leaving those tables
# out would leave the coverage case holding a set that skips every table most
# able to need covering.
BYTE_COMPARED = {
    "ec/annotations/call-graph-callees.csv": "call_graph.py",
    "ec/annotations/dsdt-ecmg-fields.csv": "dsdt_ec_fields.py",
    "ec/annotations/task-call-table.csv": "task_call_table.py",
    "ec/annotations/bucket-c-codemap.csv": "bucket_c_codemap.py",
    "ec/annotations/site-resolution.csv": "check_site_resolution.py",
    "ec/annotations/fan-table-defaults.csv": "fan_table_defaults.py",
    "ec/annotations/xdata-registers.csv": "xdata_register_map.py",
    "ec/annotations/xdata-clusters.csv": "xdata_register_map.py",
    "ec/annotations/ghidra-functions.csv": "call_graph.py",
    "ec/decompiled/index.csv": "call_graph.py",
    "ec/ghidra/xdata-symbols.csv": "gen_xdata_symbols.py",
    "ec/ghidra/gap-citation-scan.csv": "citation_gap_scan.py",
    "bios/ifr/charge-questions.csv": "ifr_census.py",
    "windows/ghidra/c-census.csv": "census_native_c.py",
    # The byte-compared CRLF tables. Each is a `--check` input or output like
    # the ones above and is covered by the blanket for the same reason; the
    # `test_a_crlf_emitters_table_is_not_marked_eol_lf` case is what keeps them
    # on the other attribute.
    "ec/annotations/walk-budget-census.csv": "walk_budget_census.py",
    "ec/annotations/xdata-086x-dispatch-sites.csv": "trace_xdata_refs.py",
    "ec/annotations/flow-follow-none-sites.csv": "walk_flow_follow.py",
    "ec/annotations/pd-entry-forms.csv": "pd_entry_forms.py",
    "ec/annotations/pd-image-strings.csv": "pd_image_census.py",
    "ec/annotations/pd-direct-offset-sites.csv": "pd_direct_offset_sites.py",
    "ec/annotations/indirect-xdata-sites.csv": "find_indirect_xdata.py",
    "ec/annotations/xdata-inc-dptr-only.csv": "inc_dptr_sites.py",
    "ec/annotations/manual-fan-ctrl-0751-writers.csv": "census_xdata_writers.py",
    "ec/annotations/code-pointer-sites.csv": "code_pointer_sites.py",
    "ec/annotations/pd-inline-arg-sites.csv": "pd_inline_arg_sites.py",
    "ec/annotations/pd-0x07d0-07cc-clusters.csv": "pd_site_clusters.py",
    # `--check` takes the path as an argument here rather than defaulting to it,
    # so `_compared_table` resolves nothing for this tool and the entry is named
    # rather than derived. The table is the one the tool is pointed at in
    # `docs/findings/pd-xdata-collision-survey.md`.
    "ec/annotations/pd-xdata-span-sites.csv": "xdata_span_survey.py",
}

# The CRLF-emitting tools this suite re-reads. Named because the reason for the
# form is these tools' renderers: each passes a bare `csv.writer()` no
# `lineterminator`, so csv's default `\r\n` is what they write, and marking one
# `eol=lf` would send it out as LF and break a check that is green today.
#
# A named subset of the tools that produce a CRLF table, not a census of them:
# other CRLF tables are written by a tool whose stdout is redirected into the
# file rather than by a `--check` default, and growing this list to name every
# one would be a value every new table has to edit. What holds the ones not
# named here is test_an_eol_lf_line_matches_only_an_LF_table_today, which reads
# the CR bytes of every committed CSV an `eol=lf` line covers.
CRLF_EMITTERS = (
    "walk_budget_census.py",
    "trace_xdata_refs.py",
    "walk_flow_follow.py",
    "pd_entry_forms.py",
    "pd_image_census.py",
    "pd_direct_offset_sites.py",
    "find_indirect_xdata.py",
    "inc_dptr_sites.py",
    "census_xdata_writers.py",
    "code_pointer_sites.py",
    "pd_inline_arg_sites.py",
    "pd_site_clusters.py",
    "xdata_span_survey.py",
)

# A `.gitattributes` line: a pattern, then attributes. Comments and blanks are
# dropped, and a bare `-attr` is kept as written so the `binary` and `-text`
# cases can read the file's own spelling rather than a normalised one.
LINE = re.compile(r"^\s*(\S+)\s+(.*\S)\s*$")

# A `check_table(...)` call, matched by its balanced closing parenthesis rather
# than by the next `)`, because the first argument is a generated table and is
# itself a call in some of these tools.
CALL = re.compile(r"check_table\(((?:[^()]|\([^()]*\))*)\)")


def split_args(text):
    """Top-level comma-separated arguments of a call's argument list.

    Splitting on nesting rather than on every comma, because the first argument
    here is a freshly generated table and is itself a call in some of these
    tools -- `check_table(csv_table(rows), OUT_CSV)`. A plain `split(",")` puts
    `csv_table(rows)` and ` OUT_CSV` in one piece, and the table then looks like
    an expression rather than a name that resolves, so the case silently
    compares nothing. Two of the seven emitters write it that way.
    """
    args, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            args.append(current.strip())
            current = ""
        else:
            current += char
    args.append(current.strip())
    return args


def attributes():
    """`[(pattern, attributes)]` for every non-comment line, in file order.

    File order matters and is preserved because it is the precedence: a later
    line wins, which is how the `ec/annotations/*.csv -text` blanket and the
    `text eol=lf` lines beneath it combine into one answer per path.
    """
    with open(GITATTRIBUTES, encoding="utf-8") as handle:
        out = []
        for raw in handle:
            line = raw.split("#", 1)[0] if not raw.lstrip().startswith("#") else ""
            match = LINE.match(line)
            if match:
                out.append((match.group(1), match.group(2).split()))
    return out


def matched(path, attrs=None):
    """The attribute list the file's last matching line gives `path`."""
    result = None
    for pattern, values in (attrs if attrs is not None else attributes()):
        if _matches(pattern, path):
            result = values
    return result or []


def _matches(pattern, path):
    """Whether a `.gitattributes` pattern covers `path`.

    Deliberately not `fnmatch`: a pattern with no `/` matches a basename at any
    depth and one with a `/` is anchored to the root, and `**` spans
    directories. `fnmatch`'s `*` would cross `/` and quietly match a path the
    file does not cover, which would make a coverage case pass on a line that
    does not exist for it.
    """
    anchored = "/" in pattern
    candidates = [path] if anchored else [path.rsplit("/", 1)[-1]]
    if not anchored:
        candidates.append(path)
    regex = _glob(pattern)
    return any(re.fullmatch(regex, c) for c in candidates)


def _glob(pattern):
    """A pattern translated to a regex, with `**` spanning `/` and `*` not."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return out


def crlf_free(rel):
    """Whether `rel` carries no CR byte in the committed worktree."""
    path = os.path.join(REPO, rel)
    if not os.path.exists(path):
        return True
    with open(path, "rb") as handle:
        return b"\r" not in handle.read()


def staged_blobs(index):
    """`{path: blob}` as the index at `index` currently holds it."""
    env = dict(os.environ, GIT_INDEX_FILE=index)
    out = subprocess.run(["git", "ls-files", "-s"], cwd=REPO, env=env,
                         capture_output=True, text=True, check=True).stdout
    return {line.split("\t", 1)[1]: line.split()[1]
            for line in out.strip().splitlines() if line}


def committed_blobs():
    """`{path: blob}` as HEAD holds it, which is what renormalising must not
    change."""
    out = subprocess.run(["git", "ls-tree", "-r", "HEAD"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return {line.split("\t", 1)[1]: line.split()[2]
            for line in out.strip().splitlines() if line}


def edited_paths():
    """Paths whose *worktree* content differs from HEAD.

    Reported by `git status` rather than diffed here, because the question is
    only ever "is this path mid-edit", and git already has the answer including
    the untracked-file side of it.
    """
    out = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return {line[3:].strip() for line in out.splitlines() if line.strip()}


class Coverage(unittest.TestCase):
    """Every byte-compared table is covered, and covered in a form that holds."""

    def test_every_byte_compared_table_is_matched_by_a_line(self):
        # The failure names the table *and* the tool that --checks it, because
        # a red run saying "coverage problem" sends a reader looking and one
        # naming the pair does not.
        uncovered = [f"{path} ({tool})" for path, tool in sorted(BYTE_COMPARED.items())
                     if not matched(path)]
        self.assertEqual(uncovered, [],
                         "no .gitattributes line covers these byte-compared "
                         "tables: %s" % ", ".join(uncovered))

    def test_the_named_tables_are_the_ones_this_repository_actually_commits(self):
        # A renamed or moved table would leave the coverage cases passing over a
        # path that no longer exists, which is a green suite for a file nothing
        # --checks any more. Same reason
        # test_check_no_conflict_markers.py holds the tree it claims for.
        missing = [path for path in sorted(BYTE_COMPARED) if not os.path.exists(
            os.path.join(REPO, path))]
        self.assertEqual(missing, [],
                         "named byte-compared tables not in the tree: %s"
                         % ", ".join(missing))

    def test_no_line_covering_a_table_says_binary(self):
        # The file's own comment in the block above: `binary` disables CRLF
        # normalisation on the way IN, which is a second way for the same bytes
        # to stop matching. A comment is not a check; this is.
        offenders = []
        for path in sorted(BYTE_COMPARED):
            for pattern, values in attributes():
                if "binary" in values and _matches(pattern, path):
                    offenders.append(f"{path} matched by `{pattern}`")
        self.assertEqual(offenders, [],
                         "`binary` disables the way-in normalisation these "
                         "tables need: %s" % "; ".join(offenders))

    def test_an_eol_lf_line_matches_only_an_LF_table_today(self):
        # The one that stops the mistake this attribute file is most able to
        # cause. `eol=lf` on a CRLF-emitting tool's table sends it out as LF
        # while the tool renders CRLF, so every --check of it goes red at
        # once -- and the attribute is the reason, which is the worst way for a
        # tree to go red.
        offenders = []
        for pattern, values in attributes():
            if "eol=lf" not in values:
                continue
            for path in self._csv_paths(pattern):
                if not crlf_free(path):
                    offenders.append(f"`{pattern}` covers CRLF {path}")
        self.assertEqual(offenders, [],
                         "eol=lf would renormalise these: %s"
                         % "; ".join(sorted(offenders)))

    def test_a_named_crlf_emitter_still_emits_crlf(self):
        # The list above is a claim about *other* files' source, so it can go
        # stale the moment one of those tools is fixed or renamed -- and a stale
        # entry is worse than none, because it keeps the negative case green
        # against a tool that no longer renders CRLF. Each named tool is
        # therefore re-read here and asked for the property it is named for, so
        # the fix that makes one of them emit LF says so instead of quietly
        # leaving a guard pointed at nothing.
        stale = []
        for tool in CRLF_EMITTERS:
            source = self._source(tool)
            writers = re.findall(r"csv\.(?:DictW|w)riter\(([^)]*)\)", source)
            if not writers:
                stale.append(f"{tool}: no csv.writer call found")
            elif any("lineterminator" in call for call in writers):
                stale.append(f"{tool}: now passes lineterminator, so it is no "
                             "longer a CRLF emitter")
        self.assertEqual(stale, [],
                         "CRLF_EMITTERS names tools that are not CRLF emitters "
                         "any more: %s" % "; ".join(stale))

    def test_a_crlf_emitters_table_is_not_marked_eol_lf(self):
        # Named rather than derived, for the reason the file's comment gives:
        # these tools pass a bare `csv.writer()` no `lineterminator`, so their
        # committed output is CRLF *by design* and is green today.
        #
        # Which table is *theirs* is read from the `check_table(...)` call that
        # does the comparing, not from every `.csv` path the module mentions.
        # `pd_image_census.py` is the case that makes the difference: it names
        # three committed CSVs, and only `pd-image-strings.csv` is the one it
        # emits and compares -- the other two are inputs it reads. Asking it for
        # all of them puts `ghidra-functions.csv` in this case, and that file is
        # correctly `eol=lf`, because it is hand-transcribed and its embedded
        # newline is a real thing. A CRLF emitter's *input* being LF is not a
        # contradiction; only its *output* has to stay CRLF.
        checked = 0
        offenders = []
        for tool in CRLF_EMITTERS:
            for path in self._compared_table(tool):
                checked += 1
                if "eol=lf" in matched(path):
                    offenders.append(f"{path} ({tool})")
        # The assertion that matters is not "how many tools" but "did this look
        # at anything at all": a resolver that matched nothing would leave every
        # case above green for the same reason this one first was.
        self.assertGreater(checked, 0,
                           "no CRLF emitter's compared table resolved, so this "
                           "case is not checking the tools it names")
        self.assertEqual(offenders, [],
                         "these tools render CRLF, so eol=lf breaks their "
                         "--check: %s" % ", ".join(offenders))

    def _compared_table(self, basename):
        """Repo-relative path of the committed CSV `basename` byte-compares.

        Two shapes reach `check_table` and both have to be followed, because
        each of these tools writes its table *or* compares one rather than
        both. `pd_entry_forms.py` and `pd_image_census.py` name a module
        constant directly; the rest pass `args.check`, whose default is the
        `const=` of the tool's own `--check` argument -- `walk_budget_census.py`
        declares `--check` as `nargs="?", const=CENSUS_CSV`, so the table it
        compares is named there and nowhere near the call site. Reading both
        off the imported module keeps the answer the tool's own rather than this
        suite's guess at where it keeps its table.
        """
        directory, name = os.path.split(basename)
        if directory not in sys.path:
            sys.path.insert(0, os.path.join(REPO, directory))
        try:
            module = importlib.import_module(os.path.splitext(name)[0])
        except Exception:
            return []
        source = self._source(basename)
        candidates = set()
        for call in CALL.finditer(source):
            args = split_args(call.group(1))
            if args and args[-1].isidentifier():
                candidates.add(args[-1])
        for decl in re.finditer(r'add_argument\(\s*"--check"[^)]*?const=(\w+)',
                                source, re.S):
            candidates.add(decl.group(1))
        paths = []
        for target in sorted(candidates):
            value = getattr(module, target, None)
            if isinstance(value, str) and os.path.isabs(value):
                paths.append(os.path.relpath(value, REPO))
        return sorted(set(paths))

    def test_git_renormalises_nothing_under_these_rules(self):
        # The decisive property, and the reason this change is an attribute and
        # nothing else: `git add --renormalize` over the tree must rewrite no
        # committed blob. Both forms were chosen to be a no-op on today's bytes --
        # `text eol=lf` only on files that are already LF, `-text` on files whose
        # CRLF is their tool's correct output -- so the renormalisation the issue
        # warns about is not smuggled in alongside the attribute. A tree where one
        # of these lines did renormalise would make this change carry a diff, and
        # the write-up would be describing a commit rather than an attribute.
        #
        # Run against a scratch index, never the repository's own: this is the one
        # case here that runs a git command that writes, and writing the real index
        # would leave the working tree mid-operation for whatever runs next.
        if shutil.which("git") is None:
            self.skipTest("git is not on PATH; the parse cases still hold")

        handle, scratch = tempfile.mkstemp(prefix="renorm-idx-", suffix="")
        os.close(handle)
        os.unlink(scratch)  # git wants the path absent, not an empty file
        try:
            env = dict(os.environ, GIT_INDEX_FILE=scratch)
            subprocess.run(["git", "read-tree", "HEAD"], cwd=REPO, env=env,
                           capture_output=True, text=True, check=True)
            subprocess.run(["git", "add", "--renormalize", "."], cwd=REPO,
                           env=env, capture_output=True, text=True, check=True)
            head = committed_blobs()
            staged = staged_blobs(scratch)
            # `--renormalize` stages the *worktree*, so a path being edited in
            # the working tree differs from HEAD for that reason and says
            # nothing about renormalisation. `.gitattributes` is always one of
            # them while this change is in flight. Comparing those would report
            # the edit as a renormalisation, so they are excluded and the
            # exclusion is named in the failure rather than hidden.
            edited = edited_paths()
            moved = sorted(path for path, blob in staged.items()
                           if path in head and path not in edited
                           and head[path] != blob)
            self.assertEqual(
                moved, [],
                "renormalising would rewrite these committed files, so this "
                "attribute change is carrying a diff it does not admit to: %s"
                % ", ".join(moved))
        finally:
            if os.path.exists(scratch):
                os.unlink(scratch)

    def _csv_paths(self, pattern):
        """Committed CSVs a pattern matches, for the `eol=lf` case.

        Walked rather than intersected with `BYTE_COMPARED`, because the rule
        is about every path the line covers -- a CRLF table the line happens to
        cover without being byte-compared today is still one a future --check
        would break.
        """
        found = []
        for root in ("ec", "bios", "windows", "docs"):
            for base, _dirs, files in os.walk(os.path.join(REPO, root)):
                for name in files:
                    if not name.endswith(".csv"):
                        continue
                    rel = os.path.relpath(os.path.join(base, name), REPO)
                    if _matches(pattern, rel):
                        found.append(rel)
        return found

    def _source(self, basename):
        """The committed source of a tool, located by basename across the
        component tools/ directories rather than by a hardcoded directory, so a
        tool that moves does not silently stop being checked."""
        for root in ("ec/tools", "bios/tools", "windows/tools"):
            candidate = os.path.join(REPO, root, basename)
            if os.path.exists(candidate):
                with open(candidate, encoding="utf-8") as handle:
                    return handle.read()
        raise AssertionError("%s is not in any tools/ directory" % basename)


class GitAgrees(unittest.TestCase):
    """`git check-attr` reads the file the way git will, not the way it parses.

    The parse above is this suite's own reading of the pattern language, so it
    could be wrong in the same direction everywhere and pass. This asks git.
    Skipped when git is absent, and that skip is safe *because* the parse stands
    alone -- the cases that hold the rule do not depend on this one.
    """

    def test_git_reports_the_attributes_the_file_writes(self):
        if shutil.which("git") is None:
            self.skipTest("git is not on PATH; the parse cases still hold")
        for path, tool in sorted(BYTE_COMPARED.items()):
            values = matched(path)
            got = self._check_attr(path)
            # `text: set` for `text eol=lf`, `unset` for `-text`. Asking git
            # rather than the parse above, because a parse that misread the
            # pattern language would agree with itself here and prove nothing.
            want = "set" if "text" in values else "unset"
            self.assertEqual(
                got["text"], want,
                "%s (%s): git says text=%s, the file's line says %s"
                % (path, tool, got["text"], values))
            self.assertEqual(
                got["eol"],
                "lf" if "eol=lf" in values else "unspecified",
                "%s: git resolves eol=%s, the file's line says %s"
                % (path, got["eol"], values))

    def _check_attr(self, path):
        """`{attribute: value}` from git, for one path.

        `check-attr` prints `<path>: <attr>: <value>` per attribute. The path is
        everything before the attribute name, so it is stripped off the *right*
        rather than split off the left -- the paths asked about here contain no
        colon, but splitting on the first would silently mis-key the result on
        any path that did.
        """
        out = subprocess.run(
            ["git", "check-attr", "text", "eol", "--", path],
            cwd=REPO, capture_output=True, text=True, check=True).stdout
        got = {}
        for line in out.strip().splitlines():
            _echoed, attr, value = line.rsplit(": ", 2)
            got[attr.strip()] = value.strip()
        return got

    def test_the_two_forms_resolve_as_intended_end_to_end(self):
        # The pairing, checked on git's own answer rather than on the parse: an
        # LF table set and a CRLF table unset. If a future edit inverts either,
        # this is what says so.
        if shutil.which("git") is None:
            self.skipTest("git is not on PATH; the parse cases still hold")
        lf = "ec/annotations/call-graph-callees.csv"
        crlf = "ec/annotations/walk-budget-census.csv"
        self.assertTrue(crlf_free(lf))
        self.assertFalse(crlf_free(crlf),
                         "%s is supposed to be a CRLF table; if the tree has "
                         "renormalised it, the eol=lf/-text split below is "
                         "the wrong argument" % crlf)
        self.assertEqual(matched(lf), ["text", "eol=lf"])
        self.assertEqual(matched(crlf), ["-text"])


class DetectionStillWorks(unittest.TestCase):
    """The attribute removes the cause. It does not soften the detection.

    This is the case the issue is explicit about: the self-test at
    `call_graph.py`'s `--self-test` proves a CRLF table is rejected, and it has
    to keep proving it. A `--check` relaxed to agree with a new `.gitattributes`
    would report a drifted table clean, which is the quiet failure the byte
    comparison exists to prevent.
    """

    def test_a_crlf_table_is_still_rejected_with_a_report(self):
        row = {column: "" for column in call_graph.COLUMNS}
        row.update({"scope": "bank0", "addr": "0EA2", "name": "FUN_0ea2",
                    "inbound": "1", "lcall": "0", "ljmp": "1", "ajmp": "0",
                    "callers": "1", "named_callers": "1"})
        rendered = call_graph.render([row])
        rc, lines = call_graph.check_table(
            rendered.replace("\n", "\r\n"), rendered)
        self.assertEqual(rc, 1, "a CRLF table passed --check")
        self.assertTrue(lines, "a rejected table reported nothing to read")

    def test_the_real_committed_table_still_passes_on_this_checkout(self):
        # The other direction, and the reason the attribute is not a licence to
        # change the writer: on the LF tree the committed table reproduces
        # byte for byte, so nothing here moved a byte.
        rc, lines = call_graph.check_table(self._committed(), self._regenerated())
        self.assertEqual((rc, lines), (0, []),
                         "call-graph-callees.csv no longer reproduces")

    def test_the_committed_table_is_the_one_the_tool_names(self):
        # Ties the case above to the real file rather than to a fixture, so a
        # `--check` pointed somewhere else is not what is being measured here.
        self.assertTrue(os.path.exists(call_graph.CALLEES),
                        "%s does not exist" % call_graph.CALLEES)

    def _committed(self):
        with open(call_graph.CALLEES, newline="") as handle:
            return handle.read()

    def _regenerated(self):
        index = call_graph.load_index()
        edges, _unresolved, _orphans, _total, listings = call_graph.scan(index)
        cited, _rejected, _undecided, _kept = call_graph.citations(index, listings)
        return call_graph.render(call_graph.build(index, edges, cited))


class TheWorkingTreeIsUntouched(unittest.TestCase):
    """Every case here reads the repository; none of it may write to it.

    The file these cases read is one several open agent PRs collide on, so a
    scratch write during a run would be a corruption rather than a mess. The
    same argument `test_gate_arm_coverage.py` makes for `.github/`.
    """

    def test_nothing_under_the_repository_was_written(self):
        def snapshot():
            out = {}
            for base, _dirs, files in os.walk(REPO):
                if os.path.basename(base) in (".git", "__pycache__"):
                    continue
                for name in files:
                    path = os.path.join(base, name)
                    try:
                        st = os.stat(path)
                    except OSError:
                        continue
                    out[path] = (st.st_size, st.st_mtime_ns)
            return out

        before = snapshot()
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(DetectionStillWorks)
        with open(os.devnull, "w") as devnull:
            unittest.TextTestRunner(stream=devnull, verbosity=0).run(suite)
        after = snapshot()
        # A file the run genuinely must not have touched. Comparing the whole
        # tree is what makes the failure legible when one has been.
        changed = [p for p in before if before[p] != after.get(p)]
        self.assertEqual(changed, [],
                         "these cases must not write to the repository: %s"
                         % ", ".join(sorted(changed))[:400])


if __name__ == "__main__":
    unittest.main()