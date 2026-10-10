#!/usr/bin/env python3
"""Measure what holds a call-graph component together by identifying holders.

A holder is a function whose removal would significantly fragment or shrink a
component. This tool measures impact by: for each function in the target
component, removing its out-edges and recomputing the connected component size
and shape. Functions are scored by their impact on component structure.

Usage:
    python3 ec/tools/analyze_callgraph_holders.py \\
        --component callgraph_pd_0003 \\
        --groups ec/annotations/function-groups.csv
"""

import argparse
import collections
import csv
import glob
import os
import sys

# Add parent directory to path for imports from call_graph module
sys.path.insert(0, os.path.dirname(__file__))

from call_graph import scan, parse_listing, norm_addr, load_index

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DECOMPILED = os.path.join(REPO, "decompiled")
ANNOTATIONS = os.path.join(REPO, "annotations")
FUNCTION_GROUPS = os.path.join(ANNOTATIONS, "function-groups.csv")
GHIDRA_FUNCTIONS = os.path.join(ANNOTATIONS, "ghidra-functions.csv")


class CallGraph:
    """Wrapper around call graph edges for holder analysis."""

    def __init__(self):
        self.edges = collections.defaultdict(list)
        self.by_addr = {}
        self.nodes = set()
        self._load_graph()

    def _load_graph(self):
        """Load the call graph from listings."""
        index = load_index()
        edges, _, _, _, _ = scan(index)
        self.edges = edges
        # Extract all nodes (both callers and callees)
        for target, callers in edges.items():
            self.nodes.add(target)
            for scope, caller, _ in callers:
                self.nodes.add((scope, caller))
        # Also need to track annotations by address
        with open(GHIDRA_FUNCTIONS, newline="") as f:
            for row in csv.DictReader(f, strict=True):
                key = (row["scope"], norm_addr(row["addr"]))
                self.by_addr[key] = row

    def get_outgoing(self, node):
        """Get all nodes this function calls (out-edges from this node)."""
        outgoing = set()
        scope, addr = node
        # For each edge in the graph where this node is a caller
        for target, callers in self.edges.items():
            for caller_scope, caller_addr, _ in callers:
                if caller_scope == scope and norm_addr(caller_addr) == addr:
                    outgoing.add(target)
        return outgoing

    def get_inbound(self, node):
        """Get all callers of this function (in-edges to this node)."""
        target = node
        if target in self.edges:
            return self.edges[target]
        return []


def cluster_component(members, graph, exclude_outgoing=None):
    """Build connected component using union-find.

    Args:
        members: set of (scope, addr) tuples to cluster
        graph: CallGraph instance
        exclude_outgoing: set of (scope, addr) to exclude outgoing edges from

    Returns:
        dict mapping representative -> list of members in that component
    """
    if exclude_outgoing is None:
        exclude_outgoing = set()

    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Initialize all members
    for member in members:
        find(member)

    # Build edges between members
    for member in members:
        outgoing = graph.get_outgoing(member)
        for target in outgoing:
            # Skip if this edge should be excluded
            if member in exclude_outgoing:
                continue
            # Join if target is also in members
            if target in members:
                union(member, target)

    # Group by component
    clusters = collections.defaultdict(list)
    for member in members:
        clusters[find(member)].append(member)

    return clusters


def measure_holder_impact(members, graph):
    """Measure impact of removing each function's out-edges.

    Args:
        members: set of (scope, addr) tuples in target component
        graph: CallGraph instance

    Returns:
        list of (node, impact_score, original_size, new_components, new_sizes)
    """
    # Get baseline component structure
    baseline = cluster_component(members, graph)
    baseline_components = len(baseline)
    baseline_size = len(members)

    results = []

    for member in sorted(members):
        # Recompute component with this member's out-edges excluded
        new_clusters = cluster_component(members, graph, exclude_outgoing={member})
        new_components = len(new_clusters)
        new_sizes = sorted([len(c) for c in new_clusters.values()], reverse=True)

        # Score by impact: number of components created and max size change
        if new_components > baseline_components:
            # Fragmentation impact
            impact_score = new_components - baseline_components + 1.0
        elif new_sizes[0] < baseline_size * 0.9:
            # Size reduction impact
            impact_score = (baseline_size - new_sizes[0]) / baseline_size
        else:
            # No significant impact
            impact_score = 0.0

        results.append((member, impact_score, baseline_size, new_components,
                        new_sizes))

    return results


def load_function_annotations(members):
    """Load ghidra-functions.csv annotations for members."""
    annotations = {}
    with open(GHIDRA_FUNCTIONS, newline="") as f:
        for row in csv.DictReader(f, strict=True):
            key = (row["scope"], norm_addr(row["addr"]))
            if key in members:
                annotations[key] = row
    return annotations


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--component", required=True,
                    help="Target component name (e.g., callgraph_pd_0003)")
    ap.add_argument("--groups", default=FUNCTION_GROUPS,
                    help="Path to function-groups.csv")
    ap.add_argument("--output", default=None,
                    help="Output CSV path (default: stdout)")
    args = ap.parse_args()

    # Load component members from function-groups.csv
    members = set()
    with open(args.groups, newline="") as f:
        for row in csv.DictReader(f, strict=True):
            if row["group"] == args.component:
                key = (row["scope"], norm_addr(row["addr"]))
                members.add(key)

    if not members:
        print(f"Component {args.component} not found or empty",
              file=sys.stderr)
        return 1

    print(f"Analyzing {args.component} with {len(members)} members...",
          file=sys.stderr)

    # Load call graph
    graph = CallGraph()

    # Measure holder impact
    results = measure_holder_impact(members, graph)

    # Load annotations
    annotations = load_function_annotations(members)

    # Sort by impact score (descending)
    results.sort(key=lambda x: x[1], reverse=True)

    # Write output
    output = args.output
    if output:
        f = open(output, "w", newline="")
    else:
        f = sys.stdout

    try:
        writer = csv.writer(f)
        writer.writerow([
            "scope", "addr", "name", "type", "impact_score",
            "baseline_size", "new_components", "top_3_sizes"
        ])

        for node, impact_score, baseline_size, new_components, new_sizes in results:
            scope, addr = node
            annotation = annotations.get(node, {})
            name = annotation.get("name", "")
            type_ = annotation.get("type", "")
            top_3 = ",".join(str(s) for s in new_sizes[:3])

            writer.writerow([
                scope, addr, name, type_, f"{impact_score:.4f}",
                baseline_size, new_components, top_3
            ])
    finally:
        if output:
            f.close()
            print(f"Wrote {output}")
        else:
            print("(End of report)", file=sys.stderr)

    # Print summary
    print(f"\nHolder census for {args.component}:", file=sys.stderr)
    print(f"  Total members: {len(members)}", file=sys.stderr)
    print(f"  Members with impact: {sum(1 for _, score, _, _, _ in results if score > 0)}", file=sys.stderr)
    if results and results[0][1] > 0:
        print(f"  Top holder: {results[0][0]} (impact={results[0][1]:.4f})",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
