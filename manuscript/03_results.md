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
({{RESULT_CHOKE_POINT_COUNT}} segment in total above the 90% threshold).
Figure @fig:pipeline_network renders the graph with flow-criticality weighting
and choke-point emphasis [@fig:pipeline_network].

Over **{{RESULT_TAMPER_EVENTS}}** simulated tamper attempts, the sensor mosaic
interdicted **{{RESULT_TAMPER_DETECTION_RATE}}%** of events, losing
**{{RESULT_TAMPER_FLOW_LOST}} kbbl/day** to the undetected remainder; active
sensors cover **{{RESULT_SENSOR_COVERAGE}}%** of installed capacity. Guarding
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
