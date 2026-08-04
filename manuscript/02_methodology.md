# Methodology

This section derives the mathematics of the three ELEKTRA pillar models. All
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
