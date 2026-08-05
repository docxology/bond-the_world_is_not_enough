"""Real-data tests for the DC power-flow / cascading-blackout model (ELEKTRA).

Zero mocks: asserts the susceptance-matrix solve, min-cut-style outage
rerouting, and the deterministic cascade against hand-built and canonical
grids.
"""

from __future__ import annotations

import pytest

from the_world_is_not_enough import power_grid as PG


class TestGridLine:
    def test_valid(self) -> None:
        line = PG.GridLine(0, 1, 5.0, 300.0)
        assert line.id == "0->1"

    def test_bad_source(self) -> None:
        with pytest.raises(ValueError):
            PG.GridLine(-1, 1, 5.0, 300.0)

    def test_bad_target(self) -> None:
        with pytest.raises(ValueError):
            PG.GridLine(0, -2, 5.0, 300.0)

    def test_self_loop(self) -> None:
        with pytest.raises(ValueError):
            PG.GridLine(2, 2, 5.0, 300.0)

    def test_bad_susceptance(self) -> None:
        with pytest.raises(ValueError):
            PG.GridLine(0, 1, 0.0, 300.0)

    def test_bad_capacity(self) -> None:
        with pytest.raises(ValueError):
            PG.GridLine(0, 1, 5.0, -1.0)


class TestPowerGrid:
    def _good_two_bus(self) -> PG.PowerGrid:
        return PG.PowerGrid(
            n_buses=2,
            lines=[PG.GridLine(0, 1, 5.0, 100.0)],
            injections=[100.0, -100.0],
            slack_bus=0,
        )

    def test_valid(self) -> None:
        grid = self._good_two_bus()
        assert grid.n_buses == 2
        assert len(grid.lines) == 1

    def test_n_buses_too_small(self) -> None:
        with pytest.raises(ValueError):
            PG.PowerGrid(n_buses=1, lines=[], injections=[0.0])

    def test_slack_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            PG.PowerGrid(n_buses=2, lines=[], injections=[0.0, 0.0], slack_bus=5)

    def test_slack_bad_type(self) -> None:
        with pytest.raises(TypeError):
            PG.PowerGrid(n_buses=2, lines=[], injections=[0.0, 0.0], slack_bus="0")  # type: ignore[arg-type]

    def test_injections_wrong_length(self) -> None:
        with pytest.raises(ValueError):
            PG.PowerGrid(n_buses=3, lines=[], injections=[0.0, 0.0])

    def test_injections_bad_type(self) -> None:
        with pytest.raises(TypeError):
            PG.PowerGrid(n_buses=2, lines=[], injections=[0.0, "x"])  # type: ignore[list-item]

    def test_injections_not_balanced(self) -> None:
        with pytest.raises(ValueError):
            PG.PowerGrid(n_buses=2, lines=[], injections=[10.0, -5.0])

    def test_bad_line_type(self) -> None:
        with pytest.raises(TypeError):
            PG.PowerGrid(n_buses=2, lines=["0->1"], injections=[0.0, 0.0])  # type: ignore[list-item]

    def test_line_bus_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            PG.PowerGrid(
                n_buses=2,
                lines=[PG.GridLine(0, 7, 5.0, 100.0)],
                injections=[0.0, 0.0],
            )

    def test_duplicate_line(self) -> None:
        with pytest.raises(ValueError):
            PG.PowerGrid(
                n_buses=2,
                lines=[PG.GridLine(0, 1, 5.0, 100.0), PG.GridLine(0, 1, 5.0, 200.0)],
                injections=[0.0, 0.0],
            )

    def test_line_id_lookup_and_missing(self) -> None:
        grid = self._good_two_bus()
        assert grid.line_id("0->1").capacity_mw == 100.0
        with pytest.raises(KeyError):
            grid.line_id("9->9")

    def test_with_lines_restricts(self) -> None:
        grid = self._good_two_bus()
        narrowed = grid.with_lines([])
        assert len(narrowed.lines) == 0
        assert narrowed.n_buses == 2


class TestDefaultGrid:
    def test_dimensions(self) -> None:
        grid = PG.default_power_grid()
        assert grid.n_buses == 8
        assert len(grid.lines) == 10
        assert PG.total_load(grid) == pytest.approx(500.0)

    def test_connectivity_full(self) -> None:
        assert PG.grid_connectivity(PG.default_power_grid()) == {0, 1, 2, 3, 4, 5, 6, 7}


class TestDcPowerFlow:
    def test_requires_lines(self) -> None:
        with pytest.raises(ValueError):
            PG.dc_power_flow(PG.PowerGrid(n_buses=2, lines=[], injections=[0.0, 0.0]))

    def test_slack_angle_zero(self) -> None:
        solution = PG.dc_power_flow(PG.default_power_grid())
        assert solution["theta"][0] == pytest.approx(0.0)

    def test_transfer_split_on_interconnectors(self) -> None:
        solution = PG.dc_power_flow(PG.default_power_grid())
        strong = solution["flows"]["3->5"]
        weak = solution["flows"]["4->5"]
        # base case: both ties stay inside their thermal limits
        assert strong < 400.0
        assert weak < 150.0
        assert strong > 0 and weak > 0

    def test_power_balance(self) -> None:
        grid = PG.default_power_grid()
        # the generator buses supply exactly the system load (generation = load)
        total_generation = sum(i for i in grid.injections if i > 0)
        assert total_generation == pytest.approx(500.0)

    def test_island_blackout_returns_no_island_flows(self) -> None:
        # Remove both tie lines -> buses 5,6,7 island; only the A-area component is live.
        grid = PG.default_power_grid()
        reduced = grid.with_lines(
            [line for line in grid.lines if line.id not in {"3->5", "4->5"}]
        )
        solution = PG.dc_power_flow(reduced)
        # island lines (5->6, 5->7, 6->7) carry no power
        assert "5->6" not in solution["flows"]
        assert solution["theta"][5] == 0.0

    def test_only_slack_live_returns_empty(self) -> None:
        # slack bus 0 isolated from lines -> nothing to solve
        grid = PG.PowerGrid(
            n_buses=3,
            lines=[PG.GridLine(1, 2, 5.0, 100.0)],
            injections=[50.0, 50.0, -100.0],
            slack_bus=0,
        )
        solution = PG.dc_power_flow(grid)
        assert solution["flows"] == {}


class TestGridConnectivity:
    def test_island_detection(self) -> None:
        grid = PG.default_power_grid()
        reduced = grid.with_lines(
            [line for line in grid.lines if line.id not in {"3->5", "4->5"}]
        )
        assert PG.grid_connectivity(reduced) == {0, 1, 2, 3, 4}


class TestCascadeFailure:
    def test_invalid_args(self) -> None:
        with pytest.raises(KeyError):
            PG.cascade_failure(PG.default_power_grid(), "does-not-exist")
        with pytest.raises(ValueError):
            PG.cascade_failure(PG.default_power_grid(), "3->5", overload_factor=0.0)
        with pytest.raises(ValueError):
            PG.cascade_failure(PG.default_power_grid(), "3->5", max_steps=0)

    def test_strong_tie_outage_cascades(self) -> None:
        outcome = PG.cascade_failure(PG.default_power_grid(), "3->5")
        assert outcome["tripped"] == ("3->5", "4->5")
        assert outcome["steps"] == 1
        assert outcome["lost_load_mw"] == pytest.approx(220.0)
        assert outcome["blackout_fraction"] == pytest.approx(0.44)
        assert outcome["stable"] is True
        assert len(outcome["surviving_lines"]) == 8

    def test_weak_tie_outage_absorbed(self) -> None:
        outcome = PG.cascade_failure(PG.default_power_grid(), "4->5")
        assert outcome["tripped"] == ("4->5",)
        assert outcome["steps"] == 0
        assert outcome["lost_load_mw"] == pytest.approx(0.0)

    def test_generator_line_outage_rebalances(self) -> None:
        outcome = PG.cascade_failure(PG.default_power_grid(), "0->2")
        assert outcome["steps"] == 0
        assert outcome["lost_load_mw"] == pytest.approx(0.0)

    def test_deterministic(self) -> None:
        a = PG.cascade_failure(PG.default_power_grid(), "3->5")
        b = PG.cascade_failure(PG.default_power_grid(), "3->5")
        assert a == b
        assert a["tripped"] == b["tripped"]


class TestFingerprint:
    def test_stable_and_distinct(self) -> None:
        grid = PG.default_power_grid()
        other = PG.PowerGrid(
            n_buses=2,
            lines=[PG.GridLine(0, 1, 5.0, 300.0)],
            injections=[10.0, -10.0],
        )
        assert PG.grid_fingerprint(grid) == PG.grid_fingerprint(grid)
        assert PG.grid_fingerprint(grid) != PG.grid_fingerprint(other)
