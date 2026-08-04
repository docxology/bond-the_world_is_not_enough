# tests/ — patterns

Shared, deterministic, mock-free patterns used across the suite.

## Known-value assertions (preferred)

Assert against analytic or hand-computed values rather than tautologies:

```python
# max-flow equals min-cut capacity (theorem)
assert P.edmonds_karp(net) == pytest.approx(P.min_cut_edges(net)[1])

# Phi(0) == 0.5
assert S.normal_cdf(0.0) == pytest.approx(0.5)

# RK4 against analytic decay dF/dt = -aF
assert result.fear[-1] == pytest.approx(math.exp(-a * t), abs=1e-3)
```

## Determinism

Run the same operation twice with the same seed and assert equality:

```python
assert P.simulate_tamper(net, 200, 1999) == P.simulate_tamper(net, 200, 1999)
```

Seeded randomness is fine when the input is part of the test's fixed
configuration: `np.random.default_rng(seed)`.

## Error / validation branches

Assert `pytest.raises(ValueError)` / `TypeError` for every public dataclass or
function's documented input guards (empty strings, out-of-range values,
negative dims, duplicate edges, etc.).

## Subprocess smoke

Exercise phase CLIs as real subprocesses with `sys.executable` and `cwd=ROOT`:

```python
proc = subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "brief.py")],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
    check=False,
)
assert proc.returncode == 0
assert json.loads(proc.stdout)["__bond_type__"] == "MissionBrief"
```

## Figure tests

Force headless `Agg` (conftest) and render into `tmp_path`; assert the PNG
exists and is non-empty.
