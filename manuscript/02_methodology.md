# Methodology

This section derives the mathematics of the six ELEKTRA pillar models. All
algorithms are standard and deterministic; every quantity reported in §3 is
computed by the corresponding code path.

## 2.1 Oil-pipeline security: choke points and tamper

**Network.** A crude pipeline is a capacitated directed graph
$G=(V,E)$ with origin $s$ (pump station), terminal $t$ (port), and segment
capacities $c_e$ (kbbl/day). The canonical ELEKTRA dataset is a 17-node /
16-edge simplex of the film's Caspian corridor: a twelve-segment mainline from
`PUMP0` to `TERM` plus four spurs, with segment `J4->J5` deliberately
under-capacity (the physical constriction the analysis must surface).

**Maximum flow / minimum cut.** The Edmonds–Karp algorithm repeatedly finds a
shortest (fewest-edge) augmenting path in the residual network and pushes its
bottleneck capacity until no augmenting path remains [@edmonds_karp]. By the
max-flow/min-cut theorem [@ford_fulkerson], the value of the maximum flow
equals the capacity of the minimum $s$-$t$ cut — the segment set whose removal
minimizes deliverable throughput. We recover that cut as the edges leaving the
source-reachable set of the final residual network:
$$v(f^*) = c(\delta(S^*)) = \min_{\text{cuts}} c(\delta(S)).$$

**Choke points.** A segment is a *choke point* when it is load-bearing and
running at $\ge 90\%$ of its rated capacity: $u_e = f^*/c_e \ge 0.9$, where
$f^*$ is the max-flow carried along the (unique) flow path. This isolates the
constriction a cut or a tamper event can exploit with maximum throughput loss.
We also report Brandes edge-betweenness centrality [@brandes], the fraction of
all-pairs shortest paths traversing each segment, as a topological (rather than
capacity) view of structural importance.

**Tamper model.** A deterministic discrete-event simulation draws
``{{CONFIG_TAMPER_EVENTS}}`` tamper attempts, each choosing a segment weighted
by its declared risk; a guarded segment interdicts a detected attempt with
per-sensor probability ``{{CONFIG_DETECTION_PROBABILITY}}``, and undetected
events release the segment's capacity as lost flow (§3 reports the realized
detection rate and the resulting flow loss). Sensor coverage is the fraction of
total capacity under active sensors.

## 2.2 Nuclear-submarine defense: sonar detection and evasion

**Passive sonar equation.** A listening sensor at range $r$ metres receives the
target's radiated noise with a signal-to-noise ratio (dB)
$$\mathrm{SNR} = SL - TL(r) - NL + DI, \quad TL(r)=20\log_{10}(r_{\mathrm{km}}) + \alpha\, r_{\mathrm{km}},$$
with $SL$ the target source level, $NL$ ambient/self noise, $DI$ array
directivity, and $\alpha$ the absorption coefficient (dB/km) [@urick]. The
operator's detection probability follows the standard performance curve
$$P_d = \Phi\!\left(\frac{\mathrm{SNR} - DT}{\sigma}\right),\quad
\Phi(x)=\tfrac{1}{2}\bigl(1+\operatorname{erf}(x/\sqrt2)\bigr),$$
where $DT$ is the detection threshold and $\sigma$ the operator variability.

**Risk field.** Combining ${{CONFIG_SUB_SENSORS}}$ sensors by the independent
rule $R = 1-\prod_i(1-P_{d,i})$ over a ${{CONFIG_SUB_GRID}}\times{{CONFIG_SUB_GRID}}$
grid (3 km cells) yields the detection-probability field the submarine must
minimize exposure over.

**Evasion routing.** Dijkstra's algorithm finds the least-cumulative-exposure
path from origin to goal on the 4-connected grid, with per-step cost equal to
the cell's detection risk [@dijkstra]. A greedy 4-connected monotone
line-of-sight path serves as the naive baseline; because both live in the same
search space, the routed exposure is guaranteed not to exceed the baseline.
Bearing-only triangulation closes the loop: two passive bearings intersect
(least-squares) to localize an emitter.

## 2.3 Hostage psychology: Stockholm-syndrome dynamics

The influence model is a deterministic system of four bounded states — fear
$F$, gratitude $G$, identification $I$, and a time-varying threat input
$T(t)$ — each a fraction of 1:

$$\begin{aligned}
\dot F &= -aF + b\,T(1-F),\\
\dot G &= c\,K(t)(1-G) - d\,G,\\
\dot I &= e\,G(1-I) - f\,F\,I,\\
T(t) &= T_\text{floor} + T_0 e^{-\lambda t},
\end{aligned}$$

where $K(t)$ is a Gaussian-smoothed kindness-impulse train (the classic "small
kindness" condition [@namnyak]) and the saturating $(1-\cdot)$ terms keep every
state bounded in $[0,1]$. The composite **syndrome index**
$S=\mathrm{clamp}\big((2I+G-F)/3\big)$ summarizes the state. Integration uses a
fixed-step classical RK4 scheme over ${{CONFIG_HOSTAGE_DAYS}}$ days at
$\Delta t = {{CONFIG_HOSTAGE_DT}}$, giving the onset day where $S$ first
crosses the ${{CONFIG_HOSTAGE_ONSET}}$ threshold and the final/peak values.
The model is phenomenological decision support, grounded in the qualitative
conditions catalogued in the clinical and forensic literature
[@namnyak; @de_fabrique].

## 2.4 Energy infrastructure: DC power flow and cascading blackout

**DC power flow.** The power system is a graph of ${{CONFIG_GRID_BUSES}}$ buses
joined by ${{CONFIG_GRID_LINES}}$ lines with susceptances $b_{ij}$ and thermal
limits $c_{ij}$ (MW). With a slack bus fixing the angle reference and bus
susceptance matrix $B$, the linearized load flow solves $B'\\theta' = P'$ (slack
row/column removed) and the line flow is
$F_{ij} = b_{ij}(\\theta_i - \\theta_j)$ [@stott]. Only the
slack-connected *live* component is solved: islanded buses carry no power and
their load is unserved.

**Cascading failure.** A deterministic outage cascade follows the OPA blackout
paradigm [@dobson_op]: an initial line outage reroutes power; the most
overloaded surviving line (largest $|F_{ij}|/c_{ij}$ ratio) trips; the system
re-solves; the process repeats until no line exceeds its rating. The blackout
is the load islanded from the slack bus. The canonical dataset is a two-area
corridor joined by a strong interconnector
(`{{CONFIG_GRID_INITIAL_OUTAGE}}`, 400 MW) and a weak tie (150 MW): under
intact operation both share the Area-B transfer and stay within limits, but
cutting the strong tie forces the whole transfer onto the weak tie, which
overloads, trips, and islands the entire load area.

## 2.5 Hostage negotiation: bargaining under syndrome-driven patience

**Rubinstein equilibrium.** In the alternating-offer bargaining game with
discount factors $\\delta_c$ (captor) and $\\delta_n$ (negotiator) and the captor
proposing first, the subgame-perfect equilibrium gives the captor
$x_c = (1-\\delta_n)/(1-\\delta_c\\,\\delta_n)$ of the pie [@rubinstein]; a more
patient party captures more.

**Syndrome feedback.** The Stockholm-syndrome state feeds the captor's
patience: as identification grows, the captor values the relationship more and
becomes more patient, so $\\delta_c = \\mathrm{clamp}(\\delta_c^0 + g\\,S)$.
Beyond a threshold the equilibrium shares become disjoint
($x_c > 1 - x_c$) and the negotiation *stalemates*.

**Concession dynamics.** Over a {{CONFIG_NEG_DEADLINE_DAYS}}-day horizon the
captor's demand concedes from its opening toward $x_c$ and the negotiator's
offer rises toward $1-x_c$, both at rate $r$. Settlement is the first day the
offer meets the demand; if the crossing falls after the deadline, the deal
lapses.

## 2.6 Sensor fusion: Kalman tracking of the hijacked submarine

The stolen *King William* is tracked through the patrol box from {{CONFIG_FUSION_STEPS}}
noisy position fixes (fused contacts, measurement std
{{CONFIG_FUSION_MEASUREMENT_NOISE}}). A constant-velocity linear Kalman filter
[@kalman] alternates **predict** and **update** steps:
$$\hat{x}_{k|k-1} = F\\hat{x}_{k-1},\\quad P_{k|k-1} = FP_{k-1}F^T+Q,$$
$$K = P H^T (H P H^T + R)^{-1},\\quad \\hat{x}_k = \\hat{x}_{k|k-1} + K(z_k - H\\hat{x}_{k|k-1}).$$
Measurement noise is drawn from a fixed-seed generator, so the track is
byte-reproducible. The filter's position RMSE is compared against the
raw-measurement RMSE to quantify the gain of fusion. (Bearing-only tracking
from a stationary observer is scale-ambiguous, so the model fuses noisy
*position* fixes — the convergent headline — and documents the limitation.)
