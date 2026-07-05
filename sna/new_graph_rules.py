import networkx as nx


def find_cycles(G, id_to_label):
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


def agency_score(G, id_to_label, label_to_cluster, label_to_id, label):
    """How many distinct clusters a node's outgoing edges reach (unchanged from the
    original definition — does not exclude the node's own cluster)."""
    node_id = label_to_id[label]
    reached = {label_to_cluster[id_to_label[v]]
               for _, v in G.out_edges(node_id)
               if id_to_label[v] in label_to_cluster}
    return len(reached)


def convergence_score(G, id_to_label, label_to_cluster, label_to_id, label):
    """
    How many distinct clusters *other than its own* a node's incoming edges
    originate from — the mirror of agency_score, but deliberately excluding the
    node's own cluster. A real convergence hub (a genuine "pivot") is reached by
    independent parts of the story, not just by the hero directly or by a single
    upstream branch; excluding same-cluster predecessors is what distinguishes it
    from a node that merely sits mid-chain in one branch and happens to have a
    predecessor or two nearby.
    """
    node_id = label_to_id[label]
    own_cluster = label_to_cluster.get(label)
    reached = {label_to_cluster[id_to_label[u]]
               for u, _ in G.in_edges(node_id)
               if id_to_label[u] in label_to_cluster
               and label_to_cluster[id_to_label[u]] != own_cluster}
    return len(reached)


# old hub-only conflict detection — one narrow pattern (actor -> pivot,
# reactor -> actor) that goes empty or arbitrary on graphs without a real
# convergence hub. Replaced by classify_role_pair_conflicts below, which
# reproduces this same actor/reactor chain when the graph happens to have
# that shape (main->pivot feeding main->main), and produces other role-pair
# categories when it doesn't, instead of hand-picking a rule per shape.
# def detect_hub_conflicts(G, id_to_label, label_to_id, important, hero, pivot):
#     """
#     Hub-convergence conflict detection: important actors with an edge into the pivot,
#     and any important reactors with an edge into that actor.
#     Returns a list of conflict dicts (actor, reactors, narrative_type, action_edge, reaction_edges).
#     """
#     pivot_id = label_to_id[pivot]
#
#     conflict_actors = [
#         X for X in (important - {hero, pivot})
#         if G.has_edge(label_to_id[X], pivot_id)
#     ]
#
#     conflicts = []
#     for X in conflict_actors:
#         X_id = label_to_id[X]
#         reactors = [Y for Y in important if Y != X and G.has_edge(label_to_id[Y], X_id)]
#
#         if hero in reactors:
#             narrative = "فعل_ورد_فعل"
#         elif reactors:
#             narrative = "فعل_ورد_فعل_غير_مباشر"
#         else:
#             narrative = "تنافس"
#
#         conflicts.append({
#             "actor":          X,
#             "reactors":       reactors,
#             "narrative_type": narrative,
#             "action_edge": {
#                 "source": X, "target": pivot, "src_id": X_id, "tgt_id": pivot_id,
#                 "relation": G.edges[X_id, pivot_id].get("label", ""),
#                 "conflict_type": "فعل",
#             },
#             "reaction_edges": [
#                 {"source": Y, "target": X,
#                  "src_id": label_to_id[Y], "tgt_id": X_id,
#                  "relation": G.edges[label_to_id[Y], X_id].get("label", ""),
#                  "conflict_type": "رد فعل"}
#                 for Y in reactors
#             ],
#         })
#
#     return conflicts


# first attempt at generalizing conflicts: tag every edge between two
# significant nodes by the pair of roles it connects. Wrong — it calls a
# protective/supportive edge (e.g. غشاء بلازمي --يحمي--> الخلية, hero
# protecting the pivot) a "confrontation" just because both endpoints are
# significant. Not every relationship between important nodes is adversarial.
# Replaced by classify_narrative_conflicts below.
# ROLE_PAIR_CONFLICT_TYPES = {
#     frozenset({"البطل", "المحور"}):  "مواجهة",
#     frozenset({"البطل", "رئيسية"}):  "صراع_مع_البطل",
#     frozenset({"رئيسية"}):           "صراع_شخصيات",
#     frozenset({"رئيسية", "المحور"}): "صراع_مع_المحور",
# }
#
#
# def classify_role_pair_conflicts(G, id_to_label, label_to_id, roles):
#     significant_roles = {"البطل", "المحور", "رئيسية"}
#     conflict_edges = []
#     for u, v, data in G.edges(data=True):
#         u_label, v_label = id_to_label[u], id_to_label[v]
#         u_role, v_role = roles.get(u_label), roles.get(v_label)
#         if u_role not in significant_roles or v_role not in significant_roles:
#             continue
#         edge_type = ROLE_PAIR_CONFLICT_TYPES.get(frozenset({u_role, v_role}))
#         if edge_type is None:
#             continue
#         conflict_edges.append({
#             "source": u_label, "target": v_label,
#             "src_id": u, "tgt_id": v,
#             "relation": data.get("label", ""),
#             "type": edge_type,
#         })
#     return conflict_edges


# same schema-level relation labels filter_graph.py already treats as
# structural markers rather than content (it drops "مثل" edges outright before
# any of these scripts run) — "نوع"/"نوعه"/"نوعها" is this NLP pipeline's
# consistent way of encoding "X is a subtype/kind of Y" across every sample
# graph. A subtype edge is classification, not one node acting on another, so
# it's excluded here the same way "امتداد" excludes taxonomic cycle-exit
# leaves — kept in the graph (agency/clusters still see it), just not treated
# as a narrative action.
TAXONOMY_RELATIONS = {"نوع", "نوعه", "نوعها"}


def classify_narrative_conflicts(G, id_to_label, label_to_id, roles, hero, pivot):
    """
    The hero doesn't fight the pivot — the hero protects/maintains it, so a direct
    hero<->pivot edge is never classified. Any other direct edge between the hero
    and a main character is always a real conflict ("صراع_مع_البطل") — the hero's
    own stated actions/relationships are inherently significant regardless of what
    that character does downstream. Edges between two non-hero main/pivot nodes are
    kept as context ("فعل"), showing how the plot continues past the hero. Taxonomy
    ("is-a subtype") edges are excluded from both — they're classification, not
    narrative action.
    """
    significant_roles = {"البطل", "المحور", "رئيسية"}

    action_edges = []
    conflict_edges = []
    for u, v, data in G.edges(data=True):
        u_label, v_label = id_to_label[u], id_to_label[v]
        u_role, v_role = roles.get(u_label), roles.get(v_label)
        if u_role not in significant_roles or v_role not in significant_roles:
            continue
        if u_label == v_label or data.get("label", "").strip() in TAXONOMY_RELATIONS:
            continue

        if hero in (u_label, v_label):
            if {u_role, v_role} == {"البطل", "المحور"}:
                continue  # hero<->pivot: protection, not conflict
            conflict_edges.append({
                "source": u_label, "target": v_label,
                "src_id": u, "tgt_id": v,
                "relation": data.get("label", ""),
                "type": "صراع_مع_البطل",
            })
        elif u_role == "رئيسية":
            action_edges.append({
                "source": u_label, "target": v_label,
                "src_id": u, "tgt_id": v,
                "relation": data.get("label", ""),
                "type": "فعل",
            })

    return action_edges + conflict_edges
