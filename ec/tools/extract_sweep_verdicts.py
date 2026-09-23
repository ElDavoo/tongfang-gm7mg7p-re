#!/usr/bin/env python3
"""Pull the adversarial verifier's verdicts out of a workflow's journal.

The annotation sweep runs two agents per shard: one that writes rows from the
function's disassembly, and one that re-reads that disassembly and decides
which of those rows are actually supported. The second verdict comes back as
the agent's return value, which lives in the workflow journal rather than in a
file -- so without this step the verification is done and then thrown away,
which is worse than not running it: the rows would look reviewed.

The approved rows are CSV lines, and a CSV line identifies itself. So this
writes them out verbatim and `merge_annotation_shards.py` keeps a row only if
its exact line is in that set. Nothing is matched by shard id, because the
journal keys its entries by an internal hash and the row's own content is the
more reliable join anyway.

    python3 ec/tools/extract_sweep_verdicts.py <workflow-dir> <out.txt>

`<workflow-dir>` is the `subagents/workflows/<run-id>/` directory the workflow
tool reported. Exits non-zero if no verdicts are found, so a run that produced
none cannot be mistaken for a run that approved everything.
"""
import json
import os
import sys


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    src, out = sys.argv[1], sys.argv[2]
    journal = os.path.join(src, "journal.jsonl")
    if not os.path.isfile(journal):
        print("no journal at %s" % journal)
        return 1
    approved, rejected, verdicts = [], [], 0
    for line in open(journal, errors="replace"):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "result":
            continue
        result = entry.get("result")
        if not isinstance(result, dict) or "approved" not in result:
            continue                       # an author agent, not a verifier
        verdicts += 1
        approved.extend(result.get("approved") or [])
        rejected.extend(result.get("rejected") or [])
    if not verdicts:
        print("no verifier verdicts in %s -- the verification stage did not "
              "run, so nothing here has been checked" % journal)
        return 1
    with open(out, "w") as f:
        for row in approved:
            f.write(row.replace("\r", "").rstrip("\n") + "\n")
    with open(out + ".rejected.json", "w") as f:
        json.dump(rejected, f, indent=1)
    print("  %d verifier verdict(s): %d row(s) approved, %d rejected"
          % (verdicts, len(approved), len(rejected)))
    print("  approved rows -> %s" % os.path.relpath(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
