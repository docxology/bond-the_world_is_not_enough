# Introduction

The World Is Not Enough (1999) pairs Bond's espionage with three recurring
operational-economic threats that map cleanly onto computational-science
problems: a transnational oil pipeline that is the target of sabotage, a
nuclear submarine that must be denied to a hijacker, and the psychological
dynamics of a hostage crisis that shape how negotiators act. This package — the
BOND suite's *{{MISSION_CODENAME}}* mission — builds deterministic,
reproducible mission software for each.

## Mission context

In the film, industrialist Elektra King's Caspian oil pipeline is threatened
with sabotage, the nuclear submarine *King William* is stolen and must be
recovered before its weapons are used, and Bond himself contends with a captor
whose manipulation of Stockholm-syndrome dynamics clouds every judgment. Each
of these is, at heart, a computational problem:

- a **security graph** whose choke points and tamper exposure determine where a
  small cutting team can inflict maximum harm;
- a **detection-and-evasion** problem in which acoustic propagation decides
  what is heard and a route planner decides what is risked;
- a **dynamical-systems** model of how fear, small kindnesses, and
  identification produce emotional attachment in captivity.

## Three pillars

Section 2 develops the mathematics of the three pillar models: maximum flow and
minimum cut, edge betweenness, and discrete-event tamper simulation
(§2.1); the passive-sonar equation, detection-probability link, and Dijkstra
evasion routing (§2.2); and the hostage-psychology ODE system integrated with a
fixed-step RK4 scheme (§2.3). Section 3 reports measured results and renders the
three concept figures. Sections 5–6 detail the experimental configuration and
the determinism guarantees that make every number reproducible.

## Reader's guide

The package is organized as a pure domain core (`src/the_world_is_not_enough/`)
with the three pillar modules, a thin `mission.py` adapter implementing the
frozen BOND-API `MissionProvider` protocol, thin phase scripts
(`scripts/brief.py` … `scripts/debrief.py`), and a manuscript hydrated entirely
from measured model outputs via `manuscript_variables.py`. Every numeric value
in this manuscript is generated from code — never hand-authored in prose.
