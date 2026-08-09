import networkx as nx


CAUSAL_MARKERS = ["يؤدي", "يسبب", "تسبب", "نتج", "نتيجة", "بسبب", "يتسبب", "يجعل",
                  "يضطر", "يتعب", "يضر", "يؤذي", "يخرب", "يتلف", "يتشكل", "تتشكل",
                  "حفز", "نشئ", "ينشأ", "حرض"]


RESOLUTION_MARKERS = ["يخلص", "يعالج", "يمنع", "يقي", "يشفي", "يريح", "يخفف"]

# fraction of nodes with real branching/convergence (in- or out-degree >= 2).
# Below this, the graph is a near-linear path (a process/causal chain) where
# cut-node/cluster-based centrality degenerates
CHAIN_COMPLEXITY_THRESHOLD = 0.25


# a node fed by several independent sources (real convergence — several
# things built INTO one) isn't chain-shaped even if it's surrounded by many
# simple single-fact nodes that dilute the ratio below threshold. High
# out-degree doesn't get the same override: one trigger branching into
# several downstream effects is still a forward-flowing process, not
# structural convergence.
CONVERGENCE_IN_DEGREE_OVERRIDE = 3


def classify_archetype(G):
    total = G.number_of_nodes()
    if total == 0:
        return "hub"
    if any(G.in_degree(n) >= CONVERGENCE_IN_DEGREE_OVERRIDE for n in G.nodes()):
        return "hub"
    complex_nodes = sum(
        1 for n in G.nodes()
        if G.in_degree(n) >= 2 or G.out_degree(n) >= 2
    )
    return "chain" if (complex_nodes / total) < CHAIN_COMPLEXITY_THRESHOLD else "hub"


def _longest_path(G, topo_order, exclude=frozenset(), start=None):
    """
    Longest path by node count. With start=None, searches the whole graph
    (used for the main spine). With start=<node>, restricts the search to
    that node's own descendants (used to trace one independent branch).
    """
    if start is None:
        candidates = set(G.nodes()) - exclude
    else:
        candidates = (nx.descendants(G, start) | {start}) - exclude
    if not candidates:
        return []

    dist = {n: 0 for n in candidates}
    parent = {n: None for n in candidates}
    for n in topo_order:
        if n not in candidates:
            continue
        for _, v in G.out_edges(n):
            if v in candidates and dist[n] + 1 > dist[v]:
                dist[v] = dist[n] + 1
                parent[v] = n

    end = max(dist, key=dist.get)
    path = []
    node = end
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return path


def longest_path_roles(G, id_to_label):

    if G.number_of_nodes() == 0 or not nx.is_directed_acyclic_graph(G):
        return None

    topo = list(nx.topological_sort(G))
    spine = _longest_path(G, topo)
    spine_set = set(spine)

    trigger = spine[0]
    outcome = spine[-1]
    stages = spine[1:-1]

    descendants = {n: nx.descendants(G, n) for n in G.nodes()}

    # branch roots: other true sources, plus any extra child a spine node
    # points to besides the next node on the spine — for the latter, remember
    # the fork edge itself (parent -> root) so it gets styled too, whichever
    # category the root ends up in
    branch_roots = {n for n in G.nodes() if G.in_degree(n)
                    == 0 and n != trigger}
    branch_root_parent = {}
    for i, n in enumerate(spine[:-1]):
        next_on_spine = spine[i + 1]
        for _, v in G.out_edges(n):
            if v != next_on_spine and v not in spine_set:
                branch_roots.add(v)
                branch_root_parent[v] = n

    covered = set(spine_set)
    resolutions, branches, extra_triggers, fork_entry_edges = [], [], [], []
    for root in sorted(branch_roots, key=lambda n: -len(descendants[n])):
        if root in covered:
            continue

        def mark_fork_entry():
            if root in branch_root_parent:
                fork_entry_edges.append(
                    [id_to_label[branch_root_parent[root]], id_to_label[root]])

        reach = descendants[root]
        if reach and reach <= covered:
            # everything this root leads to is already told elsewhere —
            # only a resolution if it actually reads as relief/treatment,
            # otherwise it's just another cause feeding the same effect
            out_relations = [G.edges[root, v].get(
                "label", "") for _, v in G.out_edges(root)]
            if any(any(m in rel for m in RESOLUTION_MARKERS) for rel in out_relations):
                resolutions.append(root)
            else:
                extra_triggers.append(root)
            covered.add(root)
            mark_fork_entry()
            continue
        local_path = _longest_path(G, topo, exclude=covered, start=root)
        if len(local_path) >= 2:
            branches.append(local_path)
            covered.update(local_path)
            mark_fork_entry()
        # else: a single unconnected fact — left as a side effect, its
        # entry edge left unstyled too

    side_effects = [n for n in G.nodes() if n not in covered]

    def edges_of(path):
        return [[id_to_label[path[i]], id_to_label[path[i + 1]]] for i in range(len(path) - 1)]

    def is_resolution_edge(u, v):
        relation = G.edges[u, v].get("label", "")
        return any(m in relation for m in RESOLUTION_MARKERS)

    return {
        "trigger": id_to_label[trigger],
        "outcome": id_to_label[outcome],
        "outcome_is_resolution": len(spine) >= 2 and is_resolution_edge(spine[-2], spine[-1]),
        "stages": [id_to_label[n] for n in stages],
        "resolutions": [id_to_label[n] for n in resolutions],
        "extra_triggers": [id_to_label[n] for n in extra_triggers],
        "side_effects": [id_to_label[n] for n in side_effects],
        "spine": [id_to_label[n] for n in spine],
        "spine_edges": edges_of(spine),
        "resolution_edges": [
            [id_to_label[n], id_to_label[t]]
            for n in resolutions for _, t in G.out_edges(n)
        ],
        "extra_trigger_edges": [
            [id_to_label[n], id_to_label[t]]
            for n in extra_triggers for _, t in G.out_edges(n)
        ],
        "fork_entry_edges": fork_entry_edges,
        "branches": [
            {
                "trigger": id_to_label[path[0]],
                "trigger_is_independent": G.in_degree(path[0]) == 0,
                "stages": [id_to_label[n] for n in path[1:-1]],
                "outcome": id_to_label[path[-1]],
                "outcome_is_resolution": len(path) >= 2 and is_resolution_edge(path[-2], path[-1]),
                "nodes": [id_to_label[n] for n in path],
                "edges": edges_of(path),
            }
            for path in branches
        ],
    }


def classify_chain_subtype(G, label_to_id, chain_info):
    """
    "causal" if the spine reads as cause->effect (يؤدي إلى، يسبب، ...),
    "sequence" if it's just an ordered/positional listing with the same
    linear shape but no actual causal wording.
    """
    spine_edges = chain_info["spine_edges"]
    if not spine_edges:
        return "sequence"
    causal_count = 0
    for s, t in spine_edges:
        relation = G.edges[label_to_id[s], label_to_id[t]].get("label", "")
        if any(marker in relation for marker in CAUSAL_MARKERS):
            causal_count += 1
    # real causal writing usually states the causal link explicitly once
    # (often the first step) and continues with implicit connectives
    # ("then", "leading to", "necessary for") rather than repeating
    # "causes"/"leads to" on every single edge — requiring a majority wrongly
    # called genuinely causal chains "sequence" when only 1 of 4-5 edges
    # used explicit wording. Any real causal marker on the spine is enough.
    return "causal" if causal_count >= 1 else "sequence"
