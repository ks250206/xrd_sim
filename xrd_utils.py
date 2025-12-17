from __future__ import annotations

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportAny=false
import argparse
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Final

import matplotlib.pyplot as plt
import numpy as np
from pymatgen.analysis.diffraction.xrd import (  # type: ignore[import-untyped]
    XRDCalculator as _XRDCalculator,
)
from pymatgen.core.structure import Structure as _Structure  # type: ignore[import-untyped]
from scipy import special  # type: ignore[import-untyped]

# pymatgen に公式 stub がないため型チェックでは Any を許容する
PMGXRDCalculator = _XRDCalculator
PMGStructure = _Structure
XRDCalculator = PMGXRDCalculator
Structure = PMGStructure

WAVELENGTH_PRESETS: Final[dict[str, float]] = {
    "CuKa": 1.5406,
    "CoKa": 1.7890,
    "MoKa": 0.7093,
}


def resolve_wavelength(args: argparse.Namespace) -> float:
    """波長を数値指定またはプリセットから解決する."""
    if args.wavelength is not None:
        return float(args.wavelength)
    return WAVELENGTH_PRESETS[args.wavelength_preset]


def apply_acs_style() -> None:
    """Apply a Matplotlib style approximating ACS journal figures."""
    plt.style.use("default")
    plt.rcParams.update({
        "figure.figsize": (6.5, 4.0),
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.labelsize": 10,
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
        "figure.dpi": 300,
    })


def normalize_fractions(fractions: Sequence[float], n: int) -> list[float]:
    if n == 0:
        return []
    if len(fractions) == 1 and n > 1:
        fractions = [fractions[0]] * n
    if len(fractions) != n:
        raise ValueError("分率の数が CIF 数と一致していません。")
    total = sum(fractions)
    if total <= 0:
        raise ValueError("分率の合計は正である必要があります。")
    return [f / total for f in fractions]


def read_bytes(file_obj: Any) -> bytes:
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass
    if hasattr(file_obj, "read"):
        data = file_obj.read()
    elif hasattr(file_obj, "data"):
        data = file_obj.data
    else:
        raise ValueError("未知のファイル型です。")
    if isinstance(data, str):
        return data.encode()
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    if hasattr(data, "getbuffer"):
        return data.getbuffer().tobytes()
    raise ValueError("ファイル内容をバイト列に変換できません。")


def load_structures(files: Iterable[object]) -> tuple[list[Structure], list[str]]:
    structures: list[Structure] = []
    labels: list[str] = []
    for f in files:
        raw = read_bytes(f)
        text = raw.decode(errors="ignore")
        structure = PMGStructure.from_str(text, fmt="cif")
        label = structure.composition.reduced_formula
        if not label:
            name = getattr(f, "name", "") or ""
            label = Path(name).stem if name else "Unknown"
        structures.append(structure)
        labels.append(label)
    return structures, labels


def compute_profile(
    calculator: PMGXRDCalculator | Any,
    structure: PMGStructure | Any,
    two_theta_range: tuple[float, float],
    step: float,
) -> tuple[np.ndarray, np.ndarray]:
    pattern = calculator.get_pattern(structure, two_theta_range=two_theta_range)  # type: ignore[call-arg]
    x_axis = np.arange(two_theta_range[0], two_theta_range[1] + step / 2, step, dtype=float)

    def voigt(x: np.ndarray, center: float, norm: float, gw: float, lw: float) -> np.ndarray:
        g = max(gw, 1e-6)
        l = max(lw, 1e-6)
        z = (x - center + 1j * l) / (g * np.sqrt(2.0))
        w = special.wofz(z)
        return norm * w.real / (g * np.sqrt(2.0 * np.pi))

    # 簡易的に固定幅の Voigt でピークを広げる
    gw = step * 2.0
    lw = step * 2.0
    intensity = np.zeros_like(x_axis)
    for center, norm in zip(pattern.x, pattern.y, strict=False):  # type: ignore[attr-defined]
        intensity += voigt(x_axis, float(center), float(norm), gw, lw)
    return x_axis, intensity


def build_profiles(
    structures: Iterable[Structure],
    labels: Sequence[str],
    fractions: Sequence[float],
    wavelength: float,
    two_theta_range: tuple[float, float],
    step: float,
    offset: float,
) -> tuple[list[str], np.ndarray, list[np.ndarray], np.ndarray]:
    calculator = XRDCalculator(wavelength=wavelength)  # type: ignore[call-arg]
    x_axis: np.ndarray | None = None
    profiles: list[np.ndarray] = []
    mixture: np.ndarray | None = None

    for idx, (structure, frac) in enumerate(zip(structures, fractions)):
        two_theta, intensity = compute_profile(calculator, structure, two_theta_range, step)
        if x_axis is None:
            x_axis = two_theta
            mixture = np.zeros_like(intensity)
        profiles.append(intensity * frac + idx * offset)
        mixture += intensity * frac  # type: ignore[operator]

    assert x_axis is not None and mixture is not None
    return list(labels), x_axis, profiles, mixture
