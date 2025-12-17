# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAny=false, reportMissingTypeStubs=false
# ruff: noqa: I001
"""Profile generation utilities for XRD patterns."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

import csv
import json
import numpy as np
import pyarrow as pa  # type: ignore[import-untyped, import-not-found]
import pyarrow.parquet as pq  # type: ignore[import-untyped, import-not-found]
from numpy.typing import NDArray
from pymatgen.analysis.diffraction.xrd import XRDCalculator as _XRDCalculator  # type: ignore[import-untyped]
from pymatgen.core.structure import Structure as _Structure  # type: ignore[import-untyped]
from scipy import special  # type: ignore[import-untyped]

TwoThetaRange = tuple[float, float]
Profile = NDArray[np.floating]
# pymatgen に公式 stub がないため型チェックでは Any 扱いとする
Structure = Any  # type: ignore[assignment]
PMGXRDCalculator = _XRDCalculator
PMGStructure = _Structure
DEFAULT_MIXTURE_LABEL = "Mixture"
MIN_COLS = 2
MIN_PARQUET_COLS = 2
MIN_PROFILE_COLS = 1
EXPECTED_DIM = 2


def load_structure(path: str | Path) -> Structure:
    """Load a crystal structure from a CIF path."""
    return PMGStructure.from_file(str(path))


def compute_profile(
    calculator: object,
    structure: object,
    two_theta_range: TwoThetaRange,
    step: float,
) -> tuple[Profile, Profile]:
    """Compute two-theta and intensity arrays for a structure."""
    pattern = calculator.get_pattern(structure, two_theta_range=two_theta_range)  # type: ignore[attr-defined]
    x_axis = np.arange(two_theta_range[0], two_theta_range[1] + step / 2, step, dtype=float)

    def voigt(x: np.ndarray, center: float, norm: float, gw: float, lw: float) -> np.ndarray:
        """Compute Voigt profile (Gaussian-Lorentz) via scipy.special.wofz."""
        g = max(gw, 1e-6)
        lorentz_w = max(lw, 1e-6)
        z = (x - center + 1j * lorentz_w) / (g * np.sqrt(2.0))
        w = special.wofz(z)
        return norm * w.real / (g * np.sqrt(2.0 * np.pi))

    # Fixed widths proportional to step for quick broadening
    gw = step * 2.0
    lw = step * 2.0
    intensity = np.zeros_like(x_axis)
    for center, norm in zip(pattern.x, pattern.y, strict=False):  # type: ignore[attr-defined]
        intensity += voigt(x_axis, float(center), float(norm), gw, lw)

    return x_axis, intensity


def normalize_fractions(fractions: Sequence[float], n: int) -> list[float]:
    """Normalize mixture fractions, expanding a single value if necessary."""
    if len(fractions) == 1 and n > 1:
        fractions = [fractions[0]] * n
    if len(fractions) != n:
        raise ValueError("fractions の長さが CIF 数と一致していません")
    total = sum(fractions)
    if total <= 0:
        raise ValueError("fractions の合計は正である必要があります")
    return [f / total for f in fractions]


def compute_individual_profiles(
    cif_paths: Iterable[str],
    wavelength: float,
    two_theta_range: TwoThetaRange,
    step: float,
) -> tuple[list[str], Profile, list[Profile]]:
    """Compute profiles for each CIF once (fractionsは未適用)."""
    calculator = PMGXRDCalculator(wavelength=wavelength)  # type: ignore[arg-type]
    labels: list[str] = []
    x_axis: Profile | None = None
    profiles: list[Profile] = []

    for cif_path in cif_paths:
        structure = load_structure(cif_path)
        label = structure.composition.reduced_formula
        labels.append(label)

        two_theta, intensity = compute_profile(calculator, structure, two_theta_range, step)

        if x_axis is None:
            x_axis = two_theta
        profiles.append(intensity)

    if x_axis is None:
        raise RuntimeError("プロファイルの計算に失敗しました")

    return labels, x_axis, profiles


def build_profiles(  # noqa: PLR0913
    cif_paths: Iterable[str],
    fractions: Sequence[float],
    wavelength: float,
    two_theta_range: TwoThetaRange,
    step: float,
    offset: float,
) -> tuple[list[str], Profile, list[Profile], Profile]:
    """Generate individual and mixture XRD profiles for given CIF files."""
    calculator = PMGXRDCalculator(wavelength=wavelength)  # type: ignore[arg-type]
    labels: list[str] = []
    x_axis: Profile | None = None
    profiles: list[Profile] = []
    mixture: Profile | None = None

    for cif_path, frac in zip(cif_paths, fractions, strict=False):
        structure = load_structure(cif_path)
        label = structure.composition.reduced_formula
        labels.append(label)

        two_theta, intensity = compute_profile(calculator, structure, two_theta_range, step)

        if x_axis is None:
            x_axis = two_theta
            mixture = np.zeros_like(intensity)
        profiles.append(intensity * frac)
        mixture = mixture + intensity * frac if mixture is not None else None

    if x_axis is None or mixture is None:
        raise RuntimeError("プロファイルの生成に失敗しました")
    return labels, x_axis, profiles, mixture


def combine_profiles(
    profiles: Sequence[Profile],
    fractions: Sequence[float],
    offset: float,
) -> tuple[list[Profile], Profile]:
    """Apply fractions/offset to precomputed profiles and build mixture."""
    if len(profiles) != len(fractions):
        raise ValueError("profiles と fractions の長さが一致していません")
    mixture = np.zeros_like(profiles[0])
    scaled_profiles: list[Profile] = []
    for prof, frac in zip(profiles, fractions, strict=False):
        mixture += prof * frac
        scaled_profiles.append(prof * frac)
    return scaled_profiles, mixture


def normalize_profiles(
    profiles: Sequence[Profile],
    mixture: Profile | None,
    target_max: float = 100.0,
) -> tuple[list[Profile], Profile | None, float]:
    """Scale intensities so the global maximum across profiles/mixture becomes target_max."""
    max_profile = max((float(np.max(p)) for p in profiles), default=0.0)
    max_mixture = float(np.max(mixture)) if mixture is not None else 0.0
    current_max = max(max_profile, max_mixture)
    if current_max <= 0:
        return list(profiles), mixture, 1.0
    scale = target_max / current_max
    scaled_profiles = [p * scale for p in profiles]
    scaled_mixture = mixture * scale if mixture is not None else None
    return scaled_profiles, scaled_mixture, scale


def apply_offsets(profiles: Sequence[Profile], offset: float) -> list[Profile]:
    """Add vertical offsets to profiles (mixtureは対象外)."""
    if offset == 0:
        return list(profiles)
    return [prof + idx * offset for idx, prof in enumerate(profiles)]


def export_profiles(  # noqa: PLR0913
    path: str | Path,
    labels: Sequence[str],
    x_axis: Profile,
    profiles: Sequence[Profile],
    mixture: Profile,
    mixture_label: str = DEFAULT_MIXTURE_LABEL,
    mode: str = "standard",
) -> None:
    """Export profiles to csv/json/parquet based on file extension."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in {".csv", ".json", ".parquet"}:
        raise ValueError("サポートされていない拡張子です (csv/json/parquet のいずれか)。")

    if suffix == ".csv":
        if mode == "mix":
            header = ["2theta", mixture_label]
            data = np.column_stack([x_axis, mixture])
        else:
            header = ["2theta", *labels, mixture_label]
            data = np.column_stack([x_axis, *profiles, mixture])
        np.savetxt(path, data, delimiter=",", header=",".join(header), comments="")
        return

    if suffix == ".json":
        payload = {
            "labels": list(labels) if mode != "mix" else [],
            "mixture_label": mixture_label,
            "x_axis": np.asarray(x_axis, dtype=float).tolist(),
            "profiles": [np.asarray(p, dtype=float).tolist() for p in profiles]
            if mode != "mix"
            else [],
            "mixture": np.asarray(mixture, dtype=float).tolist(),
            "mode": mode,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    # parquet
    columns: dict[str, np.ndarray] = {"2theta": np.asarray(x_axis, dtype=float)}
    if mode != "mix":
        for lbl, prof in zip(labels, profiles, strict=False):
            columns[str(lbl)] = np.asarray(prof, dtype=float)
    columns[mixture_label] = np.asarray(mixture, dtype=float)
    table = pa.Table.from_pydict(columns)
    pq.write_table(table, path)


def load_profiles_file(
    path: str | Path,
) -> tuple[list[str], Profile, list[Profile], Profile, str]:
    """Load profiles from csv/json/parquet saved by export_profiles."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        with path.open(newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = [[float(v) for v in row] for row in reader]
        arr = np.asarray(rows, dtype=float)
        if arr.ndim != EXPECTED_DIM or arr.shape[1] < MIN_COLS:
            raise ValueError("CSV の形式が不正です。")
        x_axis = arr[:, 0]
        label_cols = header[1:]
        if len(label_cols) < MIN_PROFILE_COLS:
            raise ValueError("CSV にプロファイル列がありません。")
        *labels_only, mixture_label = label_cols
        profiles = [arr[:, idx + 1] for idx in range(len(labels_only))]
        mixture = arr[:, len(label_cols)]
        return labels_only, x_axis, profiles, mixture, mixture_label

    if suffix == ".json":
        payload = json.loads(path.read_text())
        labels = list(payload["labels"])
        mixture_label = str(payload.get("mixture_label", "Mixture"))
        x_axis = np.asarray(payload["x_axis"], dtype=float)
        profiles = [np.asarray(p, dtype=float) for p in payload["profiles"]]
        mixture = np.asarray(payload["mixture"], dtype=float)
        return labels, x_axis, profiles, mixture, mixture_label

    if suffix == ".parquet":
        table = pq.read_table(path)
        df = table.to_pandas()
        if df.shape[1] < MIN_PARQUET_COLS:
            raise ValueError("Parquet の列数が不足しています。")
        labels_only = list(df.columns[1:-1])
        mixture_label = str(df.columns[-1])
        x_axis = df.iloc[:, 0].to_numpy(dtype=float)
        profiles = [df[lbl].to_numpy(dtype=float) for lbl in labels_only]
        mixture = df.iloc[:, -1].to_numpy(dtype=float)
        return labels_only, x_axis, profiles, mixture, mixture_label

    raise ValueError("サポートされていない拡張子です (csv/json/parquet のいずれか)。")
