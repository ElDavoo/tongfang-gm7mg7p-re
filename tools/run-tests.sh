#!/usr/bin/env bash
#
# The repository's offline unittest suites, one command. See tools/README.md
# for what each one covers and what none of them covers.
#
#   bash tools/run-tests.sh                  every test_*.py in the repository
#   bash tools/run-tests.sh windows/tools    just that directory, or a few
#
# A shell script rather than a Python one, for a reason worth keeping: the
# cheap gate's check_shellcheck already runs over every *.sh under the tree,
# so this file is shellchecked with no gate edit at all, while
# check_python_syntax globs only the four component tools/ directories and
# would not have covered a root tools/*.py.
#
# Not called from .github/scripts/agent-gates.sh, and the reason is the
# pipeline file-copy rule rather than an oversight: agent-gates.sh is copied
# from ElDavoo/agent-pipeline, so a gate call is an upstream change and a
# re-copy, not a line here. docs/agent-pipeline.md carries the line, and the
# note this script prints on every run says so the way the cheap tier's does.

set -uo pipefail

here=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$here/.." || exit 1

dirs=("$@")
if [ "${#dirs[@]}" -eq 0 ]; then
  dirs=(.)
fi

suites=0
failed=0

# One interpreter per FILE -- not per directory, and not one for the lot.
# The reason was a live landmine rather than a preference, and the landmine is
# now defused, so read what follows as insurance and not as load-bearing.
#
# Both windows/tools suites used to install a fake ecrw into sys.modules with
# setdefault, and the two fakes were not the same shape:
# test_manual_fan_ctrl_probe.py exported only Ec, test_ec_watch.py exported Ec
# and EcError, and ec_watch.py does `from ecrw import Ec, EcError`. In one
# shared interpreter, whichever suite imported first won that setdefault, and
# the other died on
#   ImportError: cannot import name 'EcError' from 'ecrw' (unknown location)
# It passed only because discovery happened to sort test_ec_watch before
# test_manual_fan_ctrl_probe -- an ordering accident nothing asserted, and a
# rename turned it into a red build. docs/findings.md §16 has the history and
# the reproduction, and it is worth reading before changing this loop.
#
# Both suites install windows/tools/ecrw_fake.py now, one shape through one
# install(), so a single discovery run over windows/tools passes in any
# filename order. What is left to this loop is the cheap half: the next suite
# that reaches for a fake of its own gets an interpreter to itself without
# anyone having to notice the collision first. Per-directory isolation would
# not have helped either way, since both suites share one directory.
#
# Process substitution rather than a pipe, because a pipe would run the loop in
# a subshell and the tally below would not survive back out. `sort -z` because
# the find is NUL-delimited, the shape the gate's check_shellcheck uses, for
# the same reason: a path is not required to be a single clean line.
#
# Per-file `unittest discover` rather than importing the files by name, so the
# suite still gets unittest's own collection and the ordinary way to run one.
while IFS= read -r -d '' path; do
  shown=${path#./}
  out=$(python3 -m unittest discover -s "$(dirname -- "$path")" \
                       -p "$(basename -- "$path")" 2>&1)
  rc=$?
  suites=$((suites + 1))
  n=$(printf '%s\n' "$out" | sed -nE 's/^Ran ([0-9]+) tests? .*/\1/p')

  # The exit code decides pass or fail; the count only decorates it, so a
  # unittest that ever changes its summary line costs a count and not a
  # verdict. The counts are printed, never asserted -- an expected count in a
  # runner turns every added test into a failure, which is the wrong trade.
  if [ "$rc" -ne 0 ]; then
    failed=1
    printf '%s: FAILED\n' "$shown"
    printf '%s\n' "$out"
  elif [ -n "$n" ]; then
    printf '%s: %s tests, passed\n' "$shown" "$n"
  else
    printf '%s: passed\n' "$shown"
  fi
done < <(find "${dirs[@]}" -name 'test_*.py' -not -path './.git/*' -print0 \
         | sort -z)

# A run that found nothing is not a pass. The vacuous check is the failure
# mode agent-gates.sh documents about the listing parse in
# docs/findings.md §14b, and a runner that silently succeeds on an empty
# glob is the same defect one level up: the moment to notice a check has
# stopped running is before it has stopped failing.
if [ "$suites" -eq 0 ]; then
  printf 'run-tests.sh: no test_*.py under %s.\n' "${dirs[*]}" >&2
  printf '  That is not a pass. If that directory should hold a suite, it does\n' >&2
  printf '  not, and the discovery pattern or the path above is wrong.\n' >&2
  exit 1
fi

# What this runner does not run, printed unconditionally including on a
# failing run, for the same reason the cheap tier prints its note: a check
# nobody can see is a check that gets dropped.
printf '\nnote  no gate and no workflow call this. CI runs\n'
printf '      .github/scripts/agent-gates.sh, which is copied from\n'
printf '      ElDavoo/agent-pipeline; docs/agent-pipeline.md has the line\n'
printf '      that wires this in, and why it is not in this repository yet.\n'
printf 'note  and none of this is hardware evidence. The suites mock device\n'
printf '      discovery, file opening and ioctls against hand-built fixtures:\n'
printf '      no EC is opened, no register is read back, and no HID node is\n'
printf '      touched. See linux/lightbar/README.md and the per-tool headers.\n'

if [ "$failed" -ne 0 ]; then
  printf '\n%d suite(s) run; one or more FAILED.\n' "$suites"
  exit 1
fi

printf '\nAll %d suite(s) passed.\n' "$suites"
