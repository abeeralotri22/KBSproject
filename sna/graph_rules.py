import networkx as nx


def find_cycles(G, id_to_label):
    """Return each simple cycle in G as an ordered list of labels."""
    return [[id_to_label[n] for n in cycle] for cycle in nx.simple_cycles(G)]


def cycle_edges_entries_exits(G, id_to_label, cycles):
    """
    cycles: list of label cycles, as returned by find_cycles().
    Returns (cycle_edge_set, entry_edge_set, exit_edge_set), all sets of
    (source_label, target_label).

    - cycle_edge_set: consecutive edges within any cycle — always kept, they
      constitute the loop itself.
    - entry_edge_set: edges from outside a cycle into one of its nodes — what
      triggers the mechanism. Kept only when the source itself has more than
      one connection in the graph (total degree > 1) — i.e. it's a node with
      its own relationships, not a bare single-fact label that exists only to
      feed the loop. Mirrors the exit-edge filter below: a node that connects
      to only this one edge is structurally trivial, regardless of direction.
    - exit_edge_set: edges leaving a cycle's node set toward a node outside
      that same cycle, kept only when the target itself has further outgoing
      edges (out-degree > 0) — i.e. the path actually continues onward.
      Without this filter, exit_edge_set drowns in one-hop "is-a" leaves (a
      cycle node classified into several subtypes that go nowhere), which are
      taxonomic decoration, not a narrative continuation.
    """
    label_to_id = {v: k for k, v in id_to_label.items()}

    cycle_edge_set = set()
    for cycle in cycles:
        n = len(cycle)
        for i in range(n):
            cycle_edge_set.add((cycle[i], cycle[(i + 1) % n]))

    entry_edge_set = set()
    exit_edge_set = set()
    for cycle in cycles:
        cycle_node_set = set(cycle)
        for label in cycle:
            node_id = label_to_id[label]

            for u, _ in G.in_edges(node_id):
                source_label = id_to_label[u]
                if source_label not in cycle_node_set and G.degree(u) > 1:
                    entry_edge_set.add((source_label, label))

            for _, v in G.out_edges(node_id):
                target_label = id_to_label[v]
                if target_label not in cycle_node_set and G.out_degree(v) > 0:
                    exit_edge_set.add((label, target_label))

    return cycle_edge_set, entry_edge_set, exit_edge_set


def structural_core_nodes(cycles, entry_edge_set, exit_edge_set):
    """
    Nodes that are structurally part of a feedback mechanism even though
    they aren't necessarily flagged important by degree/betweenness alone:
    the cycle's own members, whatever triggers it (entry sources), and
    whatever it leads into (exit targets).
    """
    cycle_node_set = {label for cycle in cycles for label in cycle}
    entry_sources = {s for s, _ in entry_edge_set}
    exit_targets = {t for _, t in exit_edge_set}
    return cycle_node_set | entry_sources | exit_targets


def detect_hub_conflicts(G, id_to_label, label_to_id, important, hero, pivot):
    """
    Hub-convergence conflict detection: important actors with an edge into the pivot,
    and any important reactors with an edge into that actor.
    Returns a list of conflict dicts (actor, reactors, narrative_type, action_edge, reaction_edges).
    """
    pivot_id = label_to_id[pivot]

    conflict_actors = [
        X for X in (important - {hero, pivot})
        if G.has_edge(label_to_id[X], pivot_id)
    ]

    conflicts = []
    for X in conflict_actors:
        X_id = label_to_id[X]
        reactors = [Y for Y in important if Y != X and G.has_edge(label_to_id[Y], X_id)]

        if hero in reactors:
            narrative = "فعل_ورد_فعل"
        elif reactors:
            narrative = "فعل_ورد_فعل_غير_مباشر"
        else:
            narrative = "تنافس"

        conflicts.append({
            "actor":          X,
            "reactors":       reactors,
            "narrative_type": narrative,
            "action_edge": {
                "source": X, "target": pivot, "src_id": X_id, "tgt_id": pivot_id,
                "relation": G.edges[X_id, pivot_id].get("label", ""),
                "conflict_type": "فعل",
            },
            "reaction_edges": [
                {"source": Y, "target": X,
                 "src_id": label_to_id[Y], "tgt_id": X_id,
                 "relation": G.edges[label_to_id[Y], X_id].get("label", ""),
                 "conflict_type": "رد فعل"}
                for Y in reactors
            ],
        })

    return conflicts