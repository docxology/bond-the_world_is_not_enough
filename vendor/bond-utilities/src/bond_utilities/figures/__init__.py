"""Figure subpackage: minimal, deterministic matplotlib generators."""

from .plots import (
    DEFAULT_FIGURE_PATH,
    DEFAULT_FREQUENCY_PATH,
    plot_frequency_analysis,
    plot_mission_schedule,
)

__all__ = [
    "DEFAULT_FIGURE_PATH",
    "DEFAULT_FREQUENCY_PATH",
    "plot_mission_schedule",
    "plot_frequency_analysis",
]
