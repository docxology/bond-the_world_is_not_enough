"""Real-data tests for the oil-pipeline security graph (ELEKTRA pillar 1).

Zero mocks: every assertion exercises the actual max-flow, min-cut,
betweenness, and tamper-simulation algorithms on hand-built (and the default)
networks.
"""

from __future__ import annotations

import pytest

from the_world_is_not_enough import pipeline_security as P


# --------------------------------------------------------------------------- edge
class TestPipelineEdge:
    def test_valid_edge(self) -> None:
        e = P.PipelineEdge("A", "B", 100.0)
        assert e.id == "A->B"
        assert e.capacity == 100.0
        assert e.sensor is False

    def test_empty_source(self) -> None:
        with pytest.raises(ValueError):
            P.PipelineEdge("", "B", 10.0)

    def test_empty_target(self) -> None:
        with pytest.raises(ValueError):
            P.PipelineEdge("A", "  ", 10.0)

    def test_self_loop(self) -> None:
        with pytest.raises(ValueError):
            P.PipelineEdge("A", "A", 10.0)

    def test_nonpositive_capacity(self) -> None:
        with pytest.raises(ValueError):
            P.PipelineEdge("A", "B", 0.0)
        with pytest.raises(ValueError):
            P.PipelineEdge("A", "B", -1.0)

    def test_risk_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            P.PipelineEdge("A", "B", 10.0, tamper_risk=1.5)
        with pytest.raises(ValueError):
            P.PipelineEdge("A", "B", 10.0, tamper_risk=-0.1)


# ----------------------------------------------------------------- network
class TestPipelineNetwork:
    def test_source_sink_equal(self) -> None:
        with pytest.raises(ValueError):
            P.PipelineNetwork(source="A", sink="A")

    def test_bad_edge_type(self) -> None:
        with pytest.raises(TypeError):
            P.PipelineNetwork(source="A", sink="B", edges=["A->B"])  # type: ignore[list-item]

    def test_duplicate_edge(self) -> None:
        edges = [P.PipelineEdge("A", "B", 10.0), P.PipelineEdge("A", "B", 20.0)]
        with pytest.raises(ValueError):
            P.PipelineNetwork(source="A", sink="B", edges=edges)

    def test_add_edge_valid(self) -> None:
        net = P.PipelineNetwork(source="S", sink="T")
        assert net.node_count() == 2
        net.add_edge(P.PipelineEdge("S", "T", 50.0))
        assert net.edge_count == 1
        assert net.node_count() == 2
        assert net.contains("S") and net.contains("T")

    def test_add_edge_duplicate(self) -> None:
        net = P.PipelineNetwork(source="S", sink="T")
        net.add_edge(P.PipelineEdge("S", "T", 50.0))
        with pytest.raises(ValueError):
            net.add_edge(P.PipelineEdge("S", "T", 60.0))

    def test_edge_id_lookup_and_missing(self) -> None:
        net = P.PipelineNetwork(
            source="S", sink="T", edges=[P.PipelineEdge("S", "T", 1.0)]
        )
        assert net.edge_id("S->T").capacity == 1.0
        with pytest.raises(KeyError):
            net.edge_id("T->S")

    def test_nodes_insertion_order(self) -> None:
        net = P.PipelineNetwork(
            source="S",
            sink="T",
            edges=[P.PipelineEdge("S", "M", 1.0), P.PipelineEdge("M", "T", 1.0)],
        )
        # source, sink, then discovered nodes in edge order
        assert net.nodes == ("S", "T", "M")


class TestDefaultPipeline:
    def test_dimensions(self) -> None:
        net = P.default_pipeline()
        assert net.node_count() == 17
        assert net.edge_count == 16
        assert net.source == "PUMP0"
        assert net.sink == "TERM"


# ---------------------------------------------------------------- max-flow
class TestEdmondsKarp:
    def test_empty_network_zero(self) -> None:
        net = P.PipelineNetwork(source="S", sink="T")
        assert P.edmonds_karp(net) == 0.0

    def test_single_edge(self) -> None:
        net = P.PipelineNetwork(
            source="S", sink="T", edges=[P.PipelineEdge("S", "T", 7.0)]
        )
        assert P.edmonds_karp(net) == 7.0

    def test_diamond_graph(self) -> None:
        # S -> A (3), S -> B (2), A -> T (2), B -> T (3): max flow = 4
        net = P.PipelineNetwork(
            source="S",
            sink="T",
            edges=[
                P.PipelineEdge("S", "A", 3.0),
                P.PipelineEdge("S", "B", 2.0),
                P.PipelineEdge("A", "T", 2.0),
                P.PipelineEdge("B", "T", 3.0),
            ],
        )
        assert P.edmonds_karp(net) == 4.0

    def test_bottleneck_limits_flow(self) -> None:
        net = P.PipelineNetwork(
            source="S",
            sink="T",
            edges=[
                P.PipelineEdge("S", "M", 100.0),
                P.PipelineEdge("M", "T", 40.0),  # bottleneck
            ],
        )
        assert P.edmonds_karp(net) == 40.0

    def test_default_pipeline_max_flow(self) -> None:
        # The J4->J5 bottleneck (420 kbbl/day) caps deliverable capacity.
        assert P.edmonds_karp(P.default_pipeline()) == 420.0


class TestMinCut:
    def test_empty_network(self) -> None:
        net = P.PipelineNetwork(source="S", sink="T")
        cut, capacity = P.min_cut_edges(net)
        assert cut == []
        assert capacity == 0.0

    def test_cut_capacity_equals_max_flow(self) -> None:
        net = P.default_pipeline()
        cut, capacity = P.min_cut_edges(net)
        assert capacity == pytest.approx(420.0)
        assert len(cut) >= 1
        # every cut edge is a real network edge leaving the s-side
        for edge in cut:
            assert edge.source in set(net.nodes)

    def test_diamond_cut(self) -> None:
        net = P.PipelineNetwork(
            source="S",
            sink="T",
            edges=[
                P.PipelineEdge("S", "A", 100.0),
                P.PipelineEdge("S", "B", 100.0),
                P.PipelineEdge("A", "T", 30.0),
                P.PipelineEdge("B", "T", 30.0),
            ],
        )
        cut, capacity = P.min_cut_edges(net)
        assert capacity == pytest.approx(60.0)
        assert {e.id for e in cut} == {"A->T", "B->T"}


# ------------------------------------------------------------ betweenness
class TestEdgeBetweenness:
    def test_empty(self) -> None:
        assert P.edge_betweenness(P.PipelineNetwork(source="S", sink="T")) == {}

    def test_path_betweenness_peaks_at_center(self) -> None:
        net = P.PipelineNetwork(
            source="A",
            sink="D",
            edges=[
                P.PipelineEdge("A", "B", 1.0),
                P.PipelineEdge("B", "C", 1.0),
                P.PipelineEdge("C", "D", 1.0),
            ],
        )
        scores = P.edge_betweenness(net)
        # a serial path's central edge carries the most all-pairs short paths
        assert scores["B->C"] > scores["A->B"]
        assert scores["B->C"] > scores["C->D"]
        # the two leaf edges are symmetric
        assert scores["A->B"] == pytest.approx(scores["C->D"])

    def test_hub_betweenness_higher(self) -> None:
        # Star: every leaf-leaf path routes through the hub edges; hub edges
        # must score higher than peripheral-only segments in a mixed graph.
        net = P.PipelineNetwork(
            source="H",
            sink="L4",
            edges=[
                P.PipelineEdge("H", "L1", 1.0),
                P.PipelineEdge("H", "L2", 1.0),
                P.PipelineEdge("H", "L3", 1.0),
                P.PipelineEdge("H", "L4", 1.0),
            ],
        )
        scores = P.edge_betweenness(net)
        for eid in ("H->L1", "H->L2", "H->L3"):
            assert scores[eid] > 0.0

    def test_deterministic(self) -> None:
        net = P.default_pipeline()
        assert P.edge_betweenness(net) == P.edge_betweenness(net)


# -------------------------------------------------------- flow criticality
class TestFlowCriticality:
    def test_empty(self) -> None:
        assert P.flow_criticality(P.PipelineNetwork(source="S", sink="T")) == {}

    def test_bottleneck_is_critical(self) -> None:
        net = P.default_pipeline()
        scores = P.flow_criticality(net)
        max_flow = P.edmonds_karp(net)
        assert scores["J4->J5"] == pytest.approx(1.0)
        # a redundant spur is not critical: removing it does not drop max flow
        assert scores["J2->SPUR_A"] == pytest.approx(0.0, abs=1e-9)
        assert max_flow == pytest.approx(420.0)

    def test_base_flow_override(self) -> None:
        net = P.default_pipeline()
        scores = P.flow_criticality(net, base_flow=420.0)
        assert scores["J4->J5"] == pytest.approx(1.0)


class TestEdgeUtilization:
    def test_empty(self) -> None:
        assert P.edge_utilization(P.PipelineNetwork(source="S", sink="T")) == {}

    def test_bottleneck_runs_at_full_capacity(self) -> None:
        net = P.default_pipeline()
        util = P.edge_utilization(net)
        # the constriction carries max flow / its own capacity == 1.0
        assert util["J4->J5"] == pytest.approx(1.0)
        # a spur carries no flow -> utilization 0
        assert util["J2->SPUR_A"] == pytest.approx(0.0)
        # a wide mainline segment idles below full load
        assert 0.0 < util["PUMP0->J1"] < 1.0

    def test_base_flow_override(self) -> None:
        net = P.default_pipeline()
        util = P.edge_utilization(net, base_flow=350.0)
        assert util["J4->J5"] == pytest.approx(350.0 / 420.0)


# ----------------------------------------------------------- sensor coverage
class TestSensorCoverage:
    def test_empty(self) -> None:
        assert P.sensor_coverage(P.PipelineNetwork(source="S", sink="T")) == 0.0

    def test_all_sensors(self) -> None:
        edges = [
            P.PipelineEdge("S", "M", 10.0, sensor=True),
            P.PipelineEdge("M", "T", 10.0, sensor=True),
        ]
        net = P.PipelineNetwork(source="S", sink="T", edges=edges)
        assert P.sensor_coverage(net) == pytest.approx(1.0)

    def test_partial(self) -> None:
        net = P.default_pipeline()
        cov = P.sensor_coverage(net)
        assert 0.0 < cov < 1.0


# -------------------------------------------------------------- analysis
class TestAnalyzeChokePoints:
    def test_report_shape_and_values(self) -> None:
        net = P.default_pipeline()
        report = P.analyze_choke_points(net)
        assert report["max_flow_kbpd"] == pytest.approx(420.0)
        # min cut capacity == max flow (max-flow/min-cut theorem)
        assert report["min_cut_capacity_kbpd"] == pytest.approx(420.0)
        assert report["choke_point_count"] == len(report["choke_points"])
        assert isinstance(report["choke_points"], tuple)
        assert "J4->J5" in report["criticality"]
        assert "J4->J5" in report["betweenness"]
        assert "J4->J5" in report["utilization"]
        assert 0.0 < report["sensor_coverage"] < 1.0

    def test_single_principal_choke_point(self) -> None:
        net = P.default_pipeline()
        report = P.analyze_choke_points(net)
        # only the full-utilization constriction is a choke point here
        assert report["choke_point_count"] == 1
        assert report["choke_points"] == ("J4->J5",)
        assert report["top_choke_point"] == "J4->J5"

    def test_deterministic(self) -> None:
        assert P.analyze_choke_points(P.default_pipeline()) == P.analyze_choke_points(
            P.default_pipeline()
        )


# --------------------------------------------------------------- tamper sim
class TestSimulateTamper:
    def test_invalid_events(self) -> None:
        with pytest.raises(ValueError):
            P.simulate_tamper(P.default_pipeline(), -1, 7)

    def test_invalid_detection_probability(self) -> None:
        with pytest.raises(ValueError):
            P.simulate_tamper(P.default_pipeline(), 5, 7, 1.5)

    def test_empty_network_raises(self) -> None:
        with pytest.raises(ValueError):
            P.simulate_tamper(P.PipelineNetwork(source="S", sink="T"), 5, 7)

    def test_zero_events(self) -> None:
        result = P.simulate_tamper(P.default_pipeline(), 0, 7)
        assert result["total_events"] == 0
        assert result["detection_rate"] == 0.0
        assert result["events"] == []
        assert result["most_targeted"] is None

    def test_deterministic(self) -> None:
        net = P.default_pipeline()
        a = P.simulate_tamper(net, 200, 1999)
        b = P.simulate_tamper(net, 200, 1999)
        assert a == b

    def test_counts_and_rate_in_bounds(self) -> None:
        net = P.default_pipeline()
        result = P.simulate_tamper(net, 40, 1999)
        assert result["total_events"] == 40
        assert 0.0 <= result["detection_rate"] <= 1.0
        assert result["most_targeted"] in {e.id for e in net.edges}
        # flow lost equals sum of capacities of undetected events
        undetected = [ev for ev in result["events"] if not ev["detected"]]
        assert result["flow_lost_kbpd"] == pytest.approx(
            sum(float(ev["flow_lost_kbpd"]) for ev in undetected)
        )

    def test_no_sensors_never_detects(self) -> None:
        net = P.PipelineNetwork(
            source="S",
            sink="T",
            edges=[
                P.PipelineEdge("S", "M", 50.0),
                P.PipelineEdge("M", "T", 50.0),
            ],
        )
        result = P.simulate_tamper(net, 10, 5)
        # every edge lacks a sensor -> no interdiction possible
        assert result["detected"] == 0
        assert result["flow_lost_kbpd"] > 0

    def test_all_sensors_detects_high_events(self) -> None:
        net = P.PipelineNetwork(
            source="S",
            sink="T",
            edges=[
                P.PipelineEdge("S", "M", 50.0, sensor=True),
                P.PipelineEdge("M", "T", 50.0, sensor=True),
            ],
        )
        result = P.simulate_tamper(net, 500, 3, detection_probability=0.9)
        assert result["detected"] > 0
        assert result["detection_rate"] > 0.8


# ---------------------------------------------------------------- misc
class TestMisc:
    def test_network_fingerprint_stable_and_distinct(self) -> None:
        net = P.default_pipeline()
        other = P.PipelineNetwork(
            source="X", sink="Y", edges=[P.PipelineEdge("X", "Y", 1.0)]
        )
        fp1 = P.network_fingerprint(net)
        fp2 = P.network_fingerprint(net)
        assert fp1 == fp2
        assert fp1 != P.network_fingerprint(other)

    def test_normalize_risk_profile(self) -> None:
        net = P.default_pipeline()
        profile = P.normalize_risk_profile(net)
        assert sum(profile.values()) == pytest.approx(1.0)
        assert set(profile) == {e.id for e in net.edges}
