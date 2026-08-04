"""the_world_is_not_enough — ELEKTRA, special-agent mission software.

BOND suite film package for *The World Is Not Enough* (1999), mission codename
ELEKTRA. The package models three operational pillars:

* :mod:`~the_world_is_not_enough.pipeline_security` — oil-pipeline security
  graph: choke points, tamper interdiction (max-flow, min-cut, betweenness,
  discrete-event tamper simulation);
* :mod:`~the_world_is_not_enough.sub_defense` — nuclear-submarine defense:
  passive-sonar detection, least-risk evasion routing, bearing triangulation;
* :mod:`~the_world_is_not_enough.hostage_psychology` — hostage-psychology
  influence model: deterministic ODE dynamics of Stockholm syndrome.

The three domain modules (and ``figures``) are pure — standard library plus
numpy/matplotlib only — and importable **without** BOND-API, so the package
surface below stays bond-free. The thin adapter
:mod:`~the_world_is_not_enough.mission` (which does depend on ``bond_api``)
is imported explicitly by discovery and by the phase scripts.
"""

from __future__ import annotations

from the_world_is_not_enough import (
    hostage_psychology,
    pipeline_security,
    sub_defense,
)

__all__ = [
    "hostage_psychology",
    "pipeline_security",
    "sub_defense",
]
