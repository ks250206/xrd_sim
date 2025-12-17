"""Styling helpers for Matplotlib outputs."""

from __future__ import annotations

import matplotlib.pyplot as plt


def apply_acs_style() -> None:
    """Apply a Matplotlib style approximating ACS journal figures."""
    plt.style.use("default")
    plt.rcParams.update({
        "figure.figsize": (6.5, 4.0),
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8,
        "axes.labelsize": 13,
        "axes.titlesize": 10,
        "axes.linewidth": 0.8,
        "xtick.direction": "in",
        "ytick.direction": "in",
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "lines.linewidth": 1.2,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "figure.dpi": 300,
        "savefig.dpi": 300,
    })
