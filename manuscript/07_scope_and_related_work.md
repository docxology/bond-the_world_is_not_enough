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
  attenuation, and the evacuation grid is a 4-connected lattice rather than a
  continuous field.
- **Hostage model.** A phenomenological, bounded ODE system whose parameters
  encode the qualitative conditions catalogued in the literature. It is
  calibrated by construction to reproduce onset behaviour, not fitted to
  individual case data, and is not a clinical diagnostic instrument.

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

**Stockholm syndrome** is documented as an outcome of specific custodial
conditions — perceived threat, small kindnesses, and prolonged contact —
rather than a formal diagnosis. The model synthesises the conditions catalogued
in the forensic review literature [@namnyak; @de_fabrique] into a quantitative
dynamical system; where those sources are qualitative, our parameter choices
are the modelling assumption and are exposed in `manuscript/config.yaml` for
audit.
