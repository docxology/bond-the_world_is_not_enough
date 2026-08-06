"""Oil-pipeline security graph: choke-point analysis and tamper interdiction.

ELEKTRA's first pillar models a trans-Caspian-style crude-oil trunk line as a
capacitated flow network. Two families of real algorithms operate on it:

* **Choke-point analysis** — Edmonds–Karp max-flow/min-cut identifies the flow
  bottleneck (the edges whose removal most reduces deliverable capacity), and
  Brandes edge-betweenness ranks how central each segment is to the routing
  of every origin-to-terminal product. Together they answer "cut here and the
  pipeline starves".

* **Tamper modeling** — a deterministic discrete-event simulation places
  tamper attempts on segments (weighted by declared risk), resolves sensor
  detection (guarded vs. unguarded), and accounts the throughput lost to
  undetected events, so guarding effort can be allocated to the choke points
  that matter. The loss it accounts is a **volume** (kbbl), not a rate: each
  undetected event is charged its segment's rated capacity (kbbl/day) for one
  nominal downtime period (days). Summing it across events therefore has no
  per-day interpretation and is not comparable to the corridor's max flow.

Everything is deterministic: the network topology is a fixed dataset declared
in this module (reflecting the film's Caspian corridor, abstracted to sealed
node/segment identifiers), no external calls are made, and the tamper
simulation draws only from a caller-supplied fixed seed.

This module is infrastructure-free: it imports only the standard library and
:mod:`dataclasses`, so it remains importable without BOND-API (the adapter
``mission.py`` binds it to the protocol).
"""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

#: A load-bearing segment counts as a *choke point* once its utilization
#: (carried flow / rated capacity) reaches this fraction. Exposed as a named
#: constant so the manuscript can cite it as a token rather than repeating the
#: literal in prose.
CHOKE_UTILIZATION_THRESHOLD = 0.9

__all__ = [
    "CHOKE_UTILIZATION_THRESHOLD",
    "PipelineEdge",
    "PipelineNetwork",
    "analyze_choke_points",
    "default_pipeline",
    "edge_betweenness",
    "edge_utilization",
    "edmonds_karp",
    "flow_criticality",
    "min_cut_edges",
    "network_fingerprint",
    "sensor_coverage",
    "simulate_tamper",
]


@dataclass(frozen=True)
class PipelineEdge:
    """A directed pipeline segment from ``source`` to ``target``.

    ``capacity`` is deliverable throughput (kbbl/day), ``tamper_risk`` is the
    baseline 0..1 probability weight that a tamper event chooses this segment,
    and ``sensor`` marks whether an intrusion/tamper sensor guards it.
    """

    source: str
    target: str
    capacity: float
    tamper_risk: float = 0.1
    sensor: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("PipelineEdge.source must be a non-empty string")
        if not isinstance(self.target, str) or not self.target.strip():
            raise ValueError("PipelineEdge.target must be a non-empty string")
        if self.source == self.target:
            raise ValueError("PipelineEdge cannot be a self-loop")
        if self.capacity <= 0:
            raise ValueError(
                f"PipelineEdge.capacity must be positive, got {self.capacity}"
            )
        if not 0.0 <= self.tamper_risk <= 1.0:
            raise ValueError("PipelineEdge.tamper_risk must be in [0, 1]")

    @property
    def id(self) -> str:
        """Deterministic segment identifier ``source->target``."""
        return f"{self.source}->{self.target}"


@dataclass
class PipelineNetwork:
    """A capacitated directed pipeline network.

    ``source`` and ``sink`` are the flow endpoints; edges may be supplied in
    any order. ``adjacency`` is materialized lazily for max-flow.
    """

    source: str
    sink: str
    edges: list[PipelineEdge] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("PipelineNetwork.source must be a non-empty string")
        if not isinstance(self.sink, str) or not self.sink.strip():
            raise ValueError("PipelineNetwork.sink must be a non-empty string")
        if self.source == self.sink:
            raise ValueError("PipelineNetwork.source and sink must differ")
        self._edge_by_id: dict[str, PipelineEdge] = {}
        # Deterministic discovery order: source, sink, then endpoints in edge order.
        self._node_order: list[str] = [self.source, self.sink]
        self._nodes: set[str] = {self.source, self.sink}
        for edge in self.edges:
            if not isinstance(edge, PipelineEdge):
                raise TypeError(
                    "PipelineNetwork.edges must contain PipelineEdge instances"
                )
            if edge.id in self._edge_by_id:
                raise ValueError(f"duplicate edge {edge.id!r} in pipeline network")
            self._edge_by_id[edge.id] = edge
            self._register_node(edge.source)
            self._register_node(edge.target)

    def _register_node(self, node: str) -> None:
        if node not in self._nodes:
            self._nodes.add(node)
            self._node_order.append(node)

    @property
    def nodes(self) -> tuple[str, ...]:
        """All node identifiers, in deterministic discovery order."""
        return tuple(self._node_order)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    def node_count(self) -> int:
        return len(self._nodes)

    def add_edge(self, edge: PipelineEdge) -> None:
        """Add a segment, validating it against existing topology."""
        if not isinstance(edge, PipelineEdge):
            raise TypeError("add_edge expects a PipelineEdge")
        if edge.id in self._edge_by_id:
            raise ValueError(f"duplicate edge {edge.id!r} in pipeline network")
        self.edges.append(edge)
        self._edge_by_id[edge.id] = edge
        self._register_node(edge.source)
        self._register_node(edge.target)

    def edge_id(self, edge_id: str) -> PipelineEdge:
        """Look up a segment by its ``source->target`` id."""
        try:
            return self._edge_by_id[edge_id]
        except KeyError:
            raise KeyError(f"no pipeline edge {edge_id!r} in network") from None

    def contains(self, node: str) -> bool:
        return node in self._nodes


def default_pipeline() -> PipelineNetwork:
    """The canonical ELEKTRA pipeline dataset.

    A 17-node / 16-edge simplex of the film's Caspian crude corridor: a
    mainline of twelve segments from the origin pump station (``PUMP0``) to
    the terminal, plus four spurs (``SPUR_A``..``SPUR_D``) drawing from
    junction stations. Segment ``J4->J5`` is deliberately under-capacity —
    the physical choke point the analysis must surface. Capacities are in
    kbbl/day and the topology is fixed for reproducibility.
    """
    edges = [
        PipelineEdge("PUMP0", "J1", 500.0, 0.05, sensor=True),
        PipelineEdge("J1", "J2", 500.0, 0.05, sensor=True),
        PipelineEdge("J2", "J3", 500.0, 0.06, sensor=True),
        PipelineEdge("J3", "J4", 500.0, 0.06),
        PipelineEdge("J4", "J5", 420.0, 0.20, sensor=True),  # bottleneck
        PipelineEdge("J5", "J6", 480.0, 0.07),
        PipelineEdge("J6", "J7", 480.0, 0.07),
        PipelineEdge("J7", "J8", 480.0, 0.08),
        PipelineEdge("J8", "J9", 480.0, 0.08),
        PipelineEdge("J9", "J10", 480.0, 0.09),
        PipelineEdge("J10", "J11", 480.0, 0.09),
        PipelineEdge("J11", "TERM", 480.0, 0.10, sensor=True),
        PipelineEdge("J2", "SPUR_A", 150.0, 0.12),
        PipelineEdge("J5", "SPUR_B", 150.0, 0.14),
        PipelineEdge("J8", "SPUR_C", 150.0, 0.16),
        PipelineEdge("J10", "SPUR_D", 150.0, 0.18),
    ]
    return PipelineNetwork(source="PUMP0", sink="TERM", edges=edges)


def _residual_graph(network: PipelineNetwork) -> dict[str, dict[str, float]]:
    """Build the residual-capacity adjacency for max-flow (deterministic BFS)."""
    residual: dict[str, dict[str, float]] = {node: {} for node in network.nodes}
    for edge in network.edges:
        residual[edge.source][edge.target] = (
            residual[edge.source].get(edge.target, 0.0) + edge.capacity
        )
    return residual


def _bfs_path(
    residual: dict[str, dict[str, float]],
    source: str,
    sink: str,
) -> tuple[dict[str, str], float]:
    """Return (parent map, bottleneck) of a shortest augmenting path, or (None, 0)."""
    parent: dict[str, str] = {}
    parent[source] = ""
    caps: dict[str, float] = {source: float("inf")}
    queue: deque[str] = deque([source])
    while queue:
        node = queue.popleft()
        if node == sink:
            break
        for nxt, cap in residual.get(node, {}).items():
            if nxt not in parent and cap > 0:
                parent[nxt] = node
                caps[nxt] = min(caps[node], cap)
                queue.append(nxt)
    if sink not in parent:
        return {}, 0.0
    return parent, caps[sink]


def edmonds_karp(network: PipelineNetwork) -> float:
    """Maximum flow from ``network.source`` to ``network.sink`` (Edmonds–Karp).

    Repeatedly finds the shortest (by edge count) augmenting path in the
    residual network and pushes its bottleneck capacity. Deterministic and
    terminating; returns the max-flow value.
    """
    if not network.edges:
        return 0.0
    residual = _residual_graph(network)
    flow = 0.0
    while True:
        parent, bottleneck = _bfs_path(residual, network.source, network.sink)
        if not parent:
            break
        node = network.sink
        while node != network.source:
            prev = parent[node]
            residual[prev][node] -= bottleneck
            residual[node][prev] = residual[node].get(prev, 0.0) + bottleneck
            node = prev
        flow += bottleneck
    return flow


def min_cut_edges(network: PipelineNetwork) -> tuple[list[PipelineEdge], float]:
    """Return the global minimum s-t cut: the edges crossing it plus its capacity.

    After Edmonds–Karp reaches maximum flow, the s-side reachable set in the
    residual network defines the min cut; every edge leaving that set is a
    cut edge. The cut capacity equals the max-flow value (by the
    max-flow/min-cut theorem).
    """
    if not network.edges:
        return [], 0.0
    residual = _residual_graph(network)
    parent, bottleneck = _bfs_path(residual, network.source, network.sink)
    while parent:
        node = network.sink
        while node != network.source:
            prev = parent[node]
            residual[prev][node] -= bottleneck
            residual[node][prev] = residual[node].get(prev, 0.0) + bottleneck
            node = prev
        parent, bottleneck = _bfs_path(residual, network.source, network.sink)
    # s-side reachable set in the final residual defines the min cut
    reachable: set[str] = set()
    stack = [network.source]
    while stack:
        node = stack.pop()
        if node in reachable:
            continue
        reachable.add(node)
        for nxt, cap in residual.get(node, {}).items():
            if cap > 0 and nxt not in reachable:
                stack.append(nxt)
    cut: list[PipelineEdge] = []
    for edge in network.edges:
        if edge.source in reachable and edge.target not in reachable:
            cut.append(edge)
    cut_capacity = sum(edge.capacity for edge in cut)
    return cut, cut_capacity


def edge_betweenness(network: PipelineNetwork) -> dict[str, float]:
    """Brandes edge-betweenness centrality over unweighted shortest paths.

    For each origin ``s``, a BFS builds the DAG of shortest paths; path counts
    are pushed along that DAG to accumulate, for every edge, the fraction of
    all-pairs shortest paths that traverse it. Deterministic. Returns a map of
    ``edge_id -> score`` (0..1, larger = more segments route through it).
    """
    if not network.edges:
        return {}
    adjacency: dict[str, dict[str, list[str]]] = {n: {} for n in network.nodes}
    for edge in network.edges:
        adjacency[edge.source][edge.target] = adjacency[edge.source].get(
            edge.target, []
        ) + [edge.target]
        adjacency[edge.target][edge.source] = adjacency[edge.target].get(
            edge.source, []
        ) + [edge.source]

    edge_flow: dict[str, float] = {}
    for source in network.nodes:
        # BFS to get order + parents-of-shortest-paths
        order: list[str] = []
        parent: dict[str, list[str]] = {}
        dist: dict[str, int] = {source: 0}
        queue: deque[str] = deque([source])
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in adjacency[node]:
                if nxt not in dist:
                    dist[nxt] = dist[node] + 1
                    parent[nxt] = []
                    queue.append(nxt)
                if dist[nxt] == dist[node] + 1:
                    parent[nxt] = parent.get(nxt, []) + [node]
        sigma: dict[str, float] = {source: 1.0}
        for node in order[1:]:
            sigma[node] = sum(sigma.get(p, 0.0) for p in parent.get(node, []))
        delta: dict[str, float] = {node: 0.0 for node in order}
        for node in reversed(order[1:]):
            for pred in parent.get(node, []):
                contribution = (sigma[pred] / sigma[node]) * (1.0 + delta[node])
                key = _undirected_key(pred, node)
                edge_flow[key] = edge_flow.get(key, 0.0) + contribution
                delta[pred] = delta.get(pred, 0.0) + contribution
    # No `if not edge_flow: return {}` guard here: any network that passed the
    # `if not network.edges: return {}` above has at least one edge, and every
    # edge lies on a length-1 shortest path between its endpoints, so
    # `edge_flow` is always populated — a guard for emptiness would be
    # unreachable dead code (V2).
    n = network.node_count()
    denominator = max(1.0, n * (n - 1))
    return {key: value / denominator for key, value in edge_flow.items()}


def _undirected_key(a: str, b: str) -> str:
    return f"{a}->{b}" if a < b else f"{b}->{a}"


def flow_criticality(
    network: PipelineNetwork, base_flow: float | None = None
) -> dict[str, float]:
    """Per-edge flow impact: fraction of max-flow lost when the edge is removed.

    For each segment the network is re-solved without it; the score is the
    relative max-flow reduction, so true choke points (in the global min cut)
    score 1.0 and redundant segments score 0.0. ``base_flow`` defaults to the
    intact max-flow. Deterministic (edge order is fixed).
    """
    if not network.edges:
        return {}
    base = base_flow if base_flow is not None else edmonds_karp(network)
    scores: dict[str, float] = {}
    for edge in network.edges:
        reduced = PipelineNetwork(
            source=network.source,
            sink=network.sink,
            edges=[e for e in network.edges if e.id != edge.id],
        )
        reduced_flow = edmonds_karp(reduced)
        scores[edge.id] = (base - reduced_flow) / base if base > 0 else 0.0
    return scores


def sensor_coverage(network: PipelineNetwork) -> float:
    """Fraction of total pipeline capacity guarded by an active sensor."""
    total = sum(e.capacity for e in network.edges) or 0.0
    guarded = sum(e.capacity for e in network.edges if e.sensor)
    return (guarded / total) if total > 0 else 0.0


def edge_utilization(
    network: PipelineNetwork, base_flow: float | None = None
) -> dict[str, float]:
    """Fraction of rated capacity each load-bearing segment actually carries.

    An edge that lies on the (unique) flow path carries ``max_flow`` units, so
    its utilization is ``max_flow / capacity``; redundant segments carry 0.
    The segment at 100% utilization is the true choke point — it is running at
    its physical limit and any cut there starves the line entirely.
    """
    if not network.edges:
        return {}
    base = base_flow if base_flow is not None else edmonds_karp(network)
    critical = flow_criticality(network, base_flow=base)
    return {
        e.id: (base / e.capacity if critical[e.id] > 0 else 0.0) for e in network.edges
    }


def analyze_choke_points(network: PipelineNetwork) -> dict[str, object]:
    """Run the full choke-point analysis and return a deterministic report.

    Combines max-flow/min-cut, edge-betweenness, flow-criticality, and
    capacity utilization into a single ranking. A **choke point** is a
    load-bearing segment running at or above
    :data:`CHOKE_UTILIZATION_THRESHOLD` of its rated capacity — the
    constriction a tamper event or a cut would exploit with the greatest
    throughput impact.
    """
    max_flow = edmonds_karp(network)
    cut, cut_capacity = min_cut_edges(network)
    betweenness = edge_betweenness(network)
    criticality = flow_criticality(network, base_flow=max_flow)
    utilization = edge_utilization(network, base_flow=max_flow)

    choke_points = [
        edge
        for edge in network.edges
        if utilization[edge.id] >= CHOKE_UTILIZATION_THRESHOLD
    ]
    choke_points.sort(
        key=lambda e: (utilization[e.id], criticality[e.id], e.id),
        reverse=True,
    )
    return {
        "max_flow_kbpd": max_flow,
        "min_cut_capacity_kbpd": cut_capacity,
        "min_cut_edges": tuple(e.id for e in cut),
        "choke_points": tuple(e.id for e in choke_points),
        "choke_point_count": len(choke_points),
        "top_choke_point": choke_points[0].id if choke_points else "none",
        "criticality": {e.id: criticality[e.id] for e in network.edges},
        "betweenness": {e.id: betweenness.get(e.id, 0.0) for e in network.edges},
        "utilization": {e.id: utilization[e.id] for e in network.edges},
        "sensor_coverage": sensor_coverage(network),
    }


def simulate_tamper(
    network: PipelineNetwork,
    n_events: int,
    seed: int,
    detection_probability: float = 0.85,
    nominal_downtime_days: float = 1.0,
) -> dict[str, object]:
    """Deterministic tamper-event simulation over the pipeline.

    Each of ``n_events`` tamper attempts picks a segment weighted by its
    declared ``tamper_risk``; a guarded segment detects the attempt with
    probability ``detection_probability``, and a detected event is interdicted
    (no throughput lost). Reproducible for a fixed ``seed``.

    **Units.** An undetected event is charged its segment's rated capacity
    (kbbl/day) for ``nominal_downtime_days`` days, so the accounted loss is a
    **volume in kbbl** — reported as ``throughput_lost_kbbl`` — and the sum
    across events is a cumulative volume with no per-day meaning. It is
    deliberately *not* comparable against the corridor max flow (a rate), and
    it may legitimately exceed it: many events over many downtime periods
    accumulate more barrels than the line moves in a single day.

    The accounting is also an **upper bound**, not carried flow: a segment is
    charged its full rating even when the max-flow solution routes less (or
    zero) through it, so spur tampering is priced at spur capacity rather than
    at its marginal delivery impact.
    """
    if n_events < 0:
        raise ValueError("n_events must be non-negative")
    if not 0.0 <= detection_probability <= 1.0:
        raise ValueError("detection_probability must be in [0, 1]")
    if nominal_downtime_days <= 0:
        raise ValueError("nominal_downtime_days must be positive")
    rng = random.Random(seed)
    weights = [e.tamper_risk for e in network.edges]
    if not network.edges or sum(weights) <= 0:
        raise ValueError("cannot simulate tamper on a network with no risky edges")

    events: list[dict[str, object]] = []
    lost_volume = 0.0
    target_counts: dict[str, int] = {}
    detected = 0
    for _ in range(n_events):
        edge = rng.choices(network.edges, weights=weights, k=1)[0]
        is_detected = edge.sensor and rng.random() < detection_probability
        event_loss = 0.0 if is_detected else edge.capacity * nominal_downtime_days
        if is_detected:
            detected += 1
        else:
            lost_volume += event_loss
        target_counts[edge.id] = target_counts.get(edge.id, 0) + 1
        events.append(
            {
                "edge": edge.id,
                "detected": is_detected,
                "interdicted": is_detected,
                "throughput_lost_kbbl": event_loss,
            }
        )
    return {
        "events": events,
        "total_events": n_events,
        "detected": detected,
        "interdicted": detected,
        "detection_rate": detected / n_events if n_events else 0.0,
        "nominal_downtime_days": nominal_downtime_days,
        "throughput_lost_kbbl": lost_volume,
        "most_targeted": max(target_counts, key=lambda k: target_counts[k])
        if target_counts
        else None,
        "target_counts": target_counts,
    }


def network_fingerprint(network: PipelineNetwork) -> str:
    """Stable textual fingerprint of the network topology and capacities."""
    lines = sorted(
        f"{e.source}|{e.target}|{e.capacity:g}|{e.tamper_risk:g}|{int(e.sensor)}"
        for e in network.edges
    )
    return "|".join([network.source, network.sink, *lines])


def normalize_risk_profile(network: PipelineNetwork) -> dict[str, float]:
    """Return each segment's tamper risk normalized to sum 1 (for prioritization)."""
    total = sum(e.tamper_risk for e in network.edges)
    if total <= 0:
        return {e.id: 0.0 for e in network.edges}
    return {e.id: e.tamper_risk / total for e in network.edges}


#: Type alias used by the mission adapter for gadget dispatch.
PipelineAnalyzer = Callable[[PipelineNetwork], dict[str, object]]
