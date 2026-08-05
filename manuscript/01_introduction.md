# Introduction

*The World Is Not Enough* (1999) pairs Bond's espionage with a set of
operational-economic threats that map cleanly onto computational-science
problems: a transnational oil pipeline that is the target of sabotage, the
power system that pumps it, a nuclear submarine that must be denied to a
hijacker and then re-found, and the psychological dynamics of a hostage crisis
that shape how negotiators bargain. This package — the BOND suite's
*{{MISSION_CODENAME}}* mission — builds deterministic, reproducible mission
software for each.

## Mission context

In the film, industrialist Elektra King's Caspian oil pipeline is threatened
with sabotage, the nuclear submarine *King William* is stolen and must be
recovered before its weapons are used, and Bond himself contends with a captor
whose manipulation of Stockholm-syndrome dynamics clouds every judgment. Each
of these is, at heart, a computational problem:

- a **security graph** whose choke points and tamper exposure determine where a
  small cutting team can inflict maximum harm;
- an **energy network** whose interconnectors decide whether a single cut is a
  local nuisance or a regional blackout;
- a **detection-and-evasion** problem in which acoustic propagation decides
  what is heard and a route planner decides what is risked;
- a **recursive-estimation** problem: once the hull is lost, noisy contacts
  must be fused back into a track good enough for an intercept;
- a **dynamical-systems** model of how fear, small kindnesses, and
  identification produce emotional attachment in captivity;
- a **bargaining game** in which that attachment moves the captor's
  reservation value, not merely the mood in the room.

## Six pillars

Section 2 develops the mathematics of the six pillar models: maximum flow and
minimum cut, edge betweenness, and discrete-event tamper simulation (§2.1); the
passive-sonar equation, detection-probability link, and Dijkstra evasion
routing (§2.2); the hostage-psychology ODE system integrated with a fixed-step
RK4 scheme (§2.3); linearized DC power flow and a deterministic
cascading-outage blackout (§2.4); Rubinstein alternating-offer bargaining under
syndrome-driven patience (§2.5); and a constant-velocity linear Kalman filter
for submarine tracking (§2.6).

The last three pillars are not independent additions. The grid model supplies
the sabotage force multiplier behind the pipeline pillar; the bargaining model
consumes the syndrome state produced by §2.3 as its input; and the Kalman
filter re-acquires the hull that §2.2 routed into the acoustic shadow. Section
3 reports the measured results and renders the four concept figures. Sections
5–6 detail the experimental configuration and the determinism guarantees that
make every number reproducible; §7 states the scope limits of each model.

## Reader's guide

The package is organized as a pure domain core (`src/the_world_is_not_enough/`)
holding the six pillar modules (`pipeline_security`, `sub_defense`,
`hostage_psychology`, `power_grid`, `negotiation_tactics`, `sensor_fusion`), a
thin `mission.py` adapter implementing the frozen BOND-API `MissionProvider`
protocol over all six, thin phase scripts (`scripts/brief.py` …
`scripts/debrief.py`), and a manuscript hydrated entirely from measured model
outputs via `manuscript_variables.py`. Every numeric value in this manuscript
is generated from code — never hand-authored in prose.
