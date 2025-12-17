"""Plotting utilities for XRD profiles."""
# ruff: noqa: PLR0913

from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAny=false
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from numpy.typing import NDArray

from style import apply_acs_style

Profile = NDArray[np.floating]


def plot_profiles(
    labels: Sequence[str],
    x_axis: Profile,
    profiles: Sequence[Profile],
    mixture: Profile,
    output: Path,
    offset: float,
    mixture_label: str,
    mode: str = "standard",
    figsize: tuple[float, float] | None = None,
) -> None:
    """Plot individual and mixture XRD profiles and save to disk."""
    apply_acs_style()
    fig: Figure
    ax: Axes
    fig, ax = plt.subplots(figsize=figsize)

    if mode != "mix":
        for label, profile in zip(labels, profiles, strict=False):
            ax.plot(x_axis, profile, label=label)

    # Mixture は個別スタックの最上段に配置 (mix モード時はオフセット無し)
    mixture_offset = 0.0 if mode == "mix" else offset * len(profiles)
    ax.plot(x_axis, mixture + mixture_offset, label=mixture_label, color="black")

    ax.set_xlabel(r"2$\theta$ (deg)")
    ax.set_ylabel("Intensity (a.u.)")
    ax.set_xlim(float(np.min(x_axis)), float(np.max(x_axis)))
    handles, labels_ = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels_[::-1])
    fig.tight_layout()
    fig.savefig(output, dpi=300)
    plt.close(fig)


def plot_profiles_without_mixture(  # pylint: disable=too-many-arguments
    labels: Sequence[str],
    x_axis: Profile,
    profiles: Sequence[Profile],
    output: Path,
    offset: float,
    figsize: tuple[float, float] | None = None,
) -> None:
    """Plot only individual XRD profiles (no mixture) and save to disk."""
    apply_acs_style()
    fig: Figure
    ax: Axes
    fig, ax = plt.subplots(figsize=figsize)

    for idx, (label, profile) in enumerate(zip(labels, profiles, strict=False)):
        ax.plot(x_axis, profile + idx * offset, label=label)

    ax.set_xlabel(r"2$\theta$ (deg)")
    ax.set_ylabel("Intensity (a.u.)")
    ax.set_xlim(float(np.min(x_axis)), float(np.max(x_axis)))
    handles, labels_ = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels_[::-1])
    fig.tight_layout()
    fig.savefig(output, dpi=300)
    plt.close(fig)
