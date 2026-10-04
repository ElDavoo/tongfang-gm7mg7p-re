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
tests=0
failed=0
unrecorded=0

# Which `Ran N tests` line is the suite's own, for a suite that runs others.
#
# A suite that *runs* other suites prints their summaries on the same stream,
# so its transcript carries one line per run rather than one per suite. Which
# of those lines is the suite's own run is not a property of the transcript:
# `ec/tools/test_pd_image_census.py` is last because the suites it drives run
# inside its own cases, and a suite that drove them *after* its own summary
# would be first, and nothing in the output would tell the two apart. So the
# choice is recorded per suite, here, and said out loud on every run -- which
# is the whole difference between a decision and a guess. A suite with one
# summary line has nothing to decide and does not come here.
#
# Adding an ordinary suite changes nothing here. Only a suite that starts
# running other suites has to add a row, which is the point: the table is a
# list of decisions, not a census of suites.
ran_line_for() {
  case "$1" in
    ec/tools/test_pd_image_census.py)
      # Its own case calls pd_image_census.self_test() twice, over two
      # throwaway one-case suites the case writes into a TemporaryDirectory,
      # and self_test() runs each with subprocess.call -- so each one's summary
      # lands on this stream inside the case, before the outer run prints its
      # own. Two lines ahead, then its own.
      printf 'last\n' ;;
    *)
      return 1 ;;
  esac
}

# One interpreter per FILE -- not per directory, and not one for the lot.
#
# The reason this was load-bearing is history, not preference: the
# windows/tools suites used to install a fake ecrw into sys.modules with
# setdefault, and the fakes were not the same shape -- ec_validate's exported
# only Ec, while ec_watch.py does `from ecrw import Ec, EcError` -- so in one
# shared interpreter whichever suite imported first won that setdefault and
# the other died on
#   ImportError: cannot import name 'EcError' from 'ecrw' (unknown location)
# Per-directory isolation would not have helped; they all share one directory.
# docs/findings.md §16 has the reproduction.
#
# It is insurance now, not the thing keeping a red build away. Every suite in
# that directory exercising a tool that imports ecrw installs
# windows/tools/ecrw_fake.py, one shape, by assignment, and that is the only
# way a suite there installs the fake -- ecrw_fake.install() installs the names
# the tools bind at import, and a suite with bytes of its own keeps that class
# and patches it over the tool afterwards, as every suite installing it does.
# tools/test_windows_tools_shared_interpreter.py is where that is asserted
# rather than promised: it runs the discovery over windows/tools in one
# interpreter, on a mirror renamed to sort both ways first.
#
# So this loop is NOT being collapsed here, and the reconciliation is not an
# invitation to. Per-file isolation is still worth keeping for reasons that
# have nothing to do with ecrw: any suite that leaves global state behind is
# contained by it, and one discovery run would turn that suite's residue into
# everyone else's failure.
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
  # Every `Ran N tests` line the suite printed, not only the last one: a suite
  # that runs other suites prints their summaries here too, so "the last line"
  # is a choice about which run is the suite's own and has to be made where it
  # can be seen. `sed` on `$out` rather than on the transcript twice, because
  # the second reading is the one that could disagree with the first.
  rands=$(printf '%s\n' "$out" | sed -nE 's/^Ran ([0-9]+) tests? .*/\1/p')
  # `wc -l` counts the numbers, not the lines of $out, so an empty transcript is
  # zero rather than one. Guarded because `printf '%s' ''` is a single empty
  # line and would otherwise read as one summary line printed.
  ran_lines=0
  if [ -n "$rands" ]; then
    ran_lines=$(printf '%s\n' "$rands" | wc -l)
  fi

  n=''
  nests=''
  if [ "$ran_lines" -gt 1 ]; then
    # More than one summary line, so this suite is running other suites and
    # only its own run's count belongs in the tally. Which one that is comes
    # from the record above; the message says so on every run, because the
    # figure below is read off this output and a reader has to be able to see
    # that a total came from a chosen line rather than assume it.
    which=$(ran_line_for "$shown") || which=''
    case "$which" in
      last)  n=$(printf '%s\n' "$rands" | tail -1) ;;
      first) n=$(printf '%s\n' "$rands" | head -1) ;;
      # An answer this loop does not recognise is treated as no answer, rather
      # than as a count of nothing: a record nobody can act on is the same
      # problem as a missing one, and quietly dropping the suite would make
      # the two indistinguishable in the output.
      *) which='' ;;
    esac
    if [ -n "$which" ]; then
      nests="; counted the $which of $ran_lines summary lines"
    else
      # No record, so no guess. Before this loop read every summary line, the
      # count came from one of them by position and the arithmetic died on a
      # multi-line `n`; the `tail -1` that replaced it chose in silence, and
      # the suite's own count went missing from a total nobody could check.
      # A refusal says which suite and what to do; a wrong number says neither.
      unrecorded=$((unrecorded + 1))
      n=''
      nests='; NOT counted'
      printf 'run-tests.sh: %s printed %d summary lines and has no recorded choice of which one is its own.\n' "$shown" "$ran_lines" >&2
      printf '  A summary line is unittest'"'"'s own "Ran N tests"; more than one means the suite ran other\n' >&2
      printf '  suites, so its count is not the number of tests it ran. Add a case to ran_line_for()\n' >&2
      printf '  in tools/run-tests.sh saying whether its own run is the first or the last summary\n' >&2
      printf '  line, and what makes it so.\n' >&2
    fi
  else
    # One line or none, and the one that is there is the suite's own run by
    # the ordinary reading. Nothing extra printed: a suite that did not need
    # a decision should not look like it got one.
    n=$(printf '%s\n' "$rands" | tail -1)
  fi

  # Counted here rather than in the pass branch, and a failing suite
  # included rather than skipped, because the figure this builds is *tests
  # run*: a failure changes the verdict, not how much of the suite ran. The
  # ${n:-0} is for the branch below where there is no n at all -- a unittest
  # that changed its summary line, never printed one, or a suite with no
  # recorded choice, which contributes nothing and is refused above.
  tests=$((tests + ${n:-0}))

  # The exit code decides pass or fail; the count only decorates it, so a
  # unittest that ever changes its summary line costs a count and not a
  # verdict. The counts are printed, never asserted -- an expected count in a
  # runner turns every added test into a failure, which is the wrong trade.
  # That is why the total below is there to be read off a run, and not a gate.
  if [ "$rc" -ne 0 ]; then
    failed=1
    printf '%s: FAILED%s\n' "$shown" "$nests"
    printf '%s\n' "$out"
  elif [ -n "$n" ]; then
    printf '%s: %s tests, passed%s\n' "$shown" "$n" "$nests"
  else
    printf '%s: passed%s\n' "$shown" "$nests"
  fi
# `.claude/` is pruned for the same reason `.git/` always was, and the reason is
# not tidiness: `git worktree add` under `.claude/worktrees/` puts a whole second
# checkout inside this one, so a developer with any worktree open runs three
# suites that do not exist in the committed tree and CI cannot run, and reads a
# total three higher than anyone else's. A figure that depends on whether a
# developer happens to have a worktree open is not a measurement of this tree.
# The same three names are pruned by `ec/tools/census_test_line_pins.py` and by
# `tools/test_readme_suite_table.py`'s `discover()`; the three should be read
# together, because one suite set defined three ways is three answers.
done < <(find "${dirs[@]}" -name 'test_*.py' \
         -not -path './.git/*' \
         -not -path './.claude/*' \
         -not -path './vendor/*' \
         -print0 \
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
printf '\nnote  CI runs this as the tests job in .github/workflows/ci.yml,\n'
printf '      beside the gates job; .github/scripts/agent-gates.sh, which the\n'
printf '      agent stages run every round, does not call it.\n'
printf 'note  and none of this is hardware evidence. The suites mock device\n'
printf '      discovery, file opening and ioctls against hand-built fixtures:\n'
printf '      no EC is opened, no register is read back, and no HID node is\n'
printf '      touched. See linux/lightbar/README.md and the per-tool headers.\n'

if [ "$failed" -ne 0 ] || [ "$unrecorded" -ne 0 ]; then
  printf '\n%d suite(s) run, %d tests' "$suites" "$tests"
  # Two clauses, and never folded into one. `unrecorded` is a shape defect --
  # a total missing a suite -- and reporting it as "one or more FAILED" would
  # be a claim about the red set that is not this run's red set:
  # docs/findings/runner-red-suite-set.md is a write-up about a figure of that
  # kind being misread, and a runner that commits it is one nobody can trust.
  # Each clause names its own tally so either can be read without the other.
  [ "$unrecorded" -ne 0 ] && \
    printf '; %d suite(s) not counted, no recorded choice of summary line' "$unrecorded"
  [ "$failed" -ne 0 ] && printf '; one or more FAILED'
  printf '.\n'
  exit 1
fi

printf '\nAll %d suite(s) passed, %d tests.\n' "$suites" "$tests"
