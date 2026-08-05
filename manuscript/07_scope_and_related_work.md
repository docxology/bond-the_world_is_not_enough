# Scope and Related Work

## Scope

The ELEKTRA mission software is a deterministic, illustrative
decision-support suite, not operational equipment. Its scope and limits are
deliberate:

- **Pipeline model.** A single-corridor flow network with a capacity bottleneck
  and dead-end spurs. It does not model multi-path loops, pump-station
  dynamics, transient surge, or geographic routing; those would change the
  choke-point ranking but not the method.
- **Sonar model.** A simplified passive equation (spherical spreading plus
  absorption) with a normal-operator curve. It omits multipath, bottom/
  surface interaction, own-ship noise masking, and frequency-dependent
  attenuation, and the evasion grid is a 4-connected lattice rather than a
  continuous field.
- **Hostage model.** A phenomenological, bounded ODE system whose parameters
  encode the qualitative conditions catalogued in the literature. It is
  calibrated by construction to reproduce onset behaviour, not fitted to
  individual case data, and is not a clinical diagnostic instrument. Because
  the rate constants are chosen rather than estimated, the reported onset day,
  peak and final index are properties *of this parameterisation* — they carry
  no uncertainty interval and should not be read as a prediction about any
  real captivity. The nine rates are listed in §5, Table 2.
- **Tamper accounting.** The tamper simulation charges each undetected event
  its segment's *rated* capacity for one nominal downtime day, so its output
  is a cumulative volume (kbbl) and an upper bound: it prices spur tampering
  above the spur's marginal delivery impact and does not model repair time,
  partial throttling, or re-routing around the damaged segment.
- **Power-grid model.** A lossless DC load flow and a deterministic sequential
  cascade. It omits reactive power, voltage collapse, generator ramping,
  frequency dynamics, and parallel-time-step tripping (all overloaded lines
  tripping simultaneously), so blackout *magnitude* is a conservative lower
  bound and the *sequence* is one deterministic path rather than a probability
  distribution.
- **Bargaining model.** A deterministic Rubinstein equilibrium with a
  concession schedule and a syndrome-to-patience mapping that is a declared
  modelling assumption. It captures the *direction* of syndrome leverage and
  the stalemate threshold, not idiosyncratic negotiator behaviour or
  asymmetric information.
- **Sensor-fusion model.** A linear constant-velocity Kalman filter over
  noisy *position* fixes. It does not fuse true bearing-only measurements from
  a fixed observer (scale-ambiguous — documented), nor multimodal ESM/acoustic
  contacts; it demonstrates the recursive-estimation gain, not a full
  multi-source correlation engine.

## Related work

**Choke-point and flow analysis** rests on the max-flow/min-cut duality of
Ford and Fulkerson [@ford_fulkerson] with the polynomial Edmonds–Karp
augmenting-path implementation [@edmonds_karp], and on Brandes' edge-betweenness
centrality [@brandes]; Dijkstra's algorithm [@dijkstra] underpins the routing
layer, as it does in network shortest-path practice broadly.

**Passive-sonar detection** follows the acoustic propagation and operator
performance-curve treatment standard in the field (e.g. Urick [@urick]): the
transmission-loss law, the signal-excess link, and the probability-of-detection
curve used here.

**Power systems** are analyzed with the linearized DC load-flow formulation
(Stott [@stott]) and the cascading-outage paradigm of the OPA blackout model
(Dobson *et al.* [@dobson_op]), both standard in transmission-security
research.

**Bargaining** uses the subgame-perfect alternating-offer equilibrium of
Rubinstein [@rubinstein] — the canonical unlimited-horizon bargaining result —
as the anchor for the syndrome-driven patience mapping.

**State estimation** uses the linear Kalman filter [@kalman], the classical
recursive minimum-mean-square estimator, generalized by many later nonlinear
variants but fully exercised here in its linear, deterministic form.

**Stockholm syndrome** is documented as an outcome of specific custodial
conditions — perceived threat, small kindnesses, and prolonged contact —
rather than a formal diagnosis. The model synthesises the conditions catalogued
in the forensic review literature [@namnyak; @de_fabrique] into a quantitative
dynamical system. Where those sources are qualitative, our parameter choices
are the modelling assumption: all nine ODE rate constants, the initial state,
and the small-kindness schedule are typed in `manuscript/config.yaml` under
`experiment.hostage`, reproduced in §5 (Table 2), and consumed by the model —
`tests/test_manuscript_variables.py` perturbs each one and asserts the reported
syndrome index moves, so the exposure is auditable rather than decorative. The
*form* of the equations, by contrast, is fixed in
`hostage_psychology.derivatives` and is not configurable.
