# Results

All numbers below are real outputs of the deterministic domain models
(seed {{CONFIG_SEED}}), hydrated into this manuscript by
`manuscript_variables.py` — none are hand-authored.

## 3.1 Oil-pipeline choke-point security

![The ELEKTRA Caspian trunk as a capacitated flow network; the single
principal choke point ({{RESULT_TOP_CHOKE_POINT}}) is highlighted by its
full-capacity utilization.](../output/figures/pipeline_network.png){#fig:pipeline_network}

The Edmonds–Karp solution sends a maximum flow of **{{RESULT_MAX_FLOW}}
kbbl/day** through the corridor; the minimum cut — the segment set smallest in
capacity whose removal starves the line — also has capacity
**{{RESULT_MIN_CUT_CAPACITY}} kbbl/day**, exactly matching the max flow as the
max-flow/min-cut theorem requires. Utilization analysis isolates a single
principal choke point, segment **{{RESULT_TOP_CHOKE_POINT}}**, which is the
only load-bearing segment running at full rated capacity
({{RESULT_CHOKE_POINT_COUNT}} segment in total at or above the
{{CONFIG_CHOKE_UTILIZATION}}% utilization threshold).
Figure @fig:pipeline_network renders the graph with flow-criticality weighting
and choke-point emphasis [@fig:pipeline_network].

Over **{{RESULT_TAMPER_EVENTS}}** simulated tamper attempts, the sensor mosaic
interdicted **{{RESULT_TAMPER_DETECTION_RATE}}%** of events; active
sensors cover **{{RESULT_SENSOR_COVERAGE}}%** of installed capacity. The
undetected remainder is charged
**{{RESULT_TAMPER_THROUGHPUT_LOST}} kbbl** of throughput — a *cumulative
volume*, obtained by pricing each undetected event at its segment's rated
capacity (kbbl/day) for {{RESULT_TAMPER_DOWNTIME_DAYS}} nominal downtime day.
It is deliberately not comparable with the {{RESULT_MAX_FLOW}} kbbl/day max
flow above and may exceed it, because many events accumulate across many
downtime periods. Two limits of that accounting are worth stating plainly: it
charges a segment's *full rating* rather than the flow the max-flow solution
actually routes through it (so spur tampering is priced above its marginal
delivery impact), and it therefore reports an upper bound on lost barrels
rather than a delivered-volume shortfall. Guarding
the single choke point {{RESULT_TOP_CHOKE_POINT}} protects the entire
throughput ({{RESULT_MAX_FLOW}} kbbl/day), since it is the constriction every
barrel must pass.

## 3.2 Nuclear-submarine defense

![The passive-sonar detection-probability field over the
{{CONFIG_SUB_GRID}}$\times${{CONFIG_SUB_GRID}} km$^2$ patrol box, with the
naive line-of-sight route (dashed) and the least-risk Dijkstra route
(solid).](../output/figures/submarine_detection.png){#fig:submarine_detection}

With {{CONFIG_SUB_SENSORS}} listening sensors, the ship's radiated noise yields
a spatially varying detection field (Figure @fig:submarine_detection). A
straight, 4-connected line-of-sight transit accumulates
**{{RESULT_NAIVE_EXPOSURE}}** total detection probability, while the
least-risk route — the global minimum of the same additive cost — accumulates
**{{RESULT_OPTIMAL_EXPOSURE}}**, a reduction in exposure of
**{{RESULT_EXPOSURE_REDUCTION}}%**. Because the naive path lives in the same
search space as Dijkstra, the routed route is provably no worse; here it hides
in the acoustic shadow of the field rather than crossing the loudest corridor.

## 3.3 Hostage-psychology influence

![The hostage-psychology ODE time series: fear, gratitude, identification,
and the composite syndrome index.](../output/figures/hostage_dynamics.png){#fig:hostage_dynamics}

Integrating the four-state model over {{CONFIG_HOSTAGE_DAYS}} days
(Figure @fig:hostage_dynamics) reproduces the qualitative trajectory reported
for Stockholm-syndrome cases: initial fear dominance, gratitude from small
kindnesses, and a growing identification with the captor. The composite
syndrome index crosses the {{CONFIG_HOSTAGE_ONSET}} onset threshold on day
**{{RESULT_SYNDROME_ONSET_DAY}}**, peaks at **{{RESULT_SYNDROME_PEAK}}**, and
reaches a final value of **{{RESULT_SYNDROME_FINAL}}**; by the end of the
horizon the captive's influence ratio toward the captor is
**{{RESULT_INFLUENCE_RATIO}}**. The model thus provides a principled estimate
of *when* an emotional bond forms — the negotiation window negotiators must
anticipate.

## 3.4 Energy infrastructure: coordinated blackout

In the canonical two-area grid, intact operation keeps both interconnectors
within rating (the strong `{{CONFIG_GRID_INITIAL_OUTAGE}}` tie carries the
larger share; the weak `{{CONFIG_GRID_WEAK_TIE}}` tie stays below its
{{CONFIG_GRID_WEAK_TIE_MW}} MW limit). Cutting the strong
interconnector forces the entire Area-B transfer onto the weak tie, which
overloads and trips. The cascade — **{{RESULT_BLACKOUT_STEPS}}** tripping step
after the initial outage, **{{RESULT_BLACKOUT_LINES_TRIPPED}}** lines tripped
total — islands the whole load area: **{{RESULT_BLACKOUT_LOST_MW}} MW** lost
out of {{CONFIG_GRID_LOAD_MW}} MW of connected load,
**{{RESULT_BLACKOUT_FRACTION}}** of system load. This is the saboteur's force
multiplier: a single well-placed cut cascades into a regional blackout,
crippling the pumped corridor's pumping stations and the hijacked sub's
support base at once.

## 3.5 Hostage negotiation: syndrome-driven leverage

The Stockholm-syndrome model's final state
($S$ = {{RESULT_SYNDROME_FINAL}}) feeds the bargaining layer: it lifts the
captor's patience, raising the captor's equilibrium claim to
**{{RESULT_NEG_CAPTOR_SHARE}}** of the pie, up from the no-syndrome baseline of
**{{RESULT_NEG_BASELINE_SHARE}}** (the equilibrium share at the captor's
un-boosted patience) — a *relative* increase of
**{{RESULT_NEG_CAPTOR_LEVERAGE_PCT}}%**, not an added share of the pie. Under the
symmetric concession schedule the captor and negotiator
still close the deal at parity by day **{{RESULT_NEG_SETTLEMENT_DAY}}**
(split **{{RESULT_NEG_SETTLEMENT_SPLIT}}**), but the syndrome has quietly
raised the captor's *reservation value* — and past a patience threshold the
negotiation would stalemate outright. The lesson for the negotiator: the bond
changes the captor's bottom line, not just the mood in the room.

## 3.6 Sensor fusion: tracking the hijacked hull

![The Kalman-filter track (green) of the hijacked submarine against the noisy
position fixes (gray) and the true constant-velocity trajectory (black).](../output/figures/sensor_fusion_track.png){#fig:sensor_fusion_track}

Fusing {{CONFIG_FUSION_STEPS}} noisy position fixes (measurement std
{{CONFIG_FUSION_MEASUREMENT_NOISE}}) with the constant-velocity Kalman filter
cuts the track's position RMSE from **{{RESULT_TRACK_MEASUREMENT_RMSE}}** (the
raw fixes) to **{{RESULT_TRACK_RMSE}}** — a **{{RESULT_TRACK_GAIN}}%** reduction
— and drives the final position error to **{{RESULT_TRACK_FINAL_ERROR}}**
(Figure @fig:sensor_fusion_track). The filter converges, so an intercept
solution can be generated reliably even while the hull evades through the sonar
shadow.
