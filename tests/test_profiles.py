from __future__ import annotations

from pathlib import Path

import pytest
from pymatgen.core import Lattice, Structure

from profiles import (
    build_profiles,
    export_profiles,
    load_profiles_file,
    normalize_fractions,
)


def _write_cif(path: Path) -> None:
    lattice = Lattice.cubic(5.43)
    structure = Structure(lattice, ["Si", "Si"], [[0, 0, 0], [0.25, 0.25, 0.25]])
    structure.to(fmt="cif", filename=str(path))


def test_normalize_expand_and_normalize() -> None:
    result = normalize_fractions([1.0], 3)
    assert len(result) == 3
    assert pytest.approx(sum(result), rel=0, abs=1e-9) == 1.0
    assert all(pytest.approx(val, rel=0, abs=1e-9) == 1.0 / 3.0 for val in result)


def test_normalize_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        normalize_fractions([0.5, 0.5], 3)


def test_build_profiles_from_cif_files(tmp_path: Path) -> None:
    cif1 = tmp_path / "a.cif"
    cif2 = tmp_path / "b.cif"
    _write_cif(cif1)
    _write_cif(cif2)

    labels, x_axis, profiles, mixture = build_profiles(
        cif_paths=[str(cif1), str(cif2)],
        fractions=[0.4, 0.6],
        wavelength=1.5406,
        two_theta_range=(5.0, 80.0),
        step=0.05,
        offset=10.0,
    )

    assert labels == ["Si", "Si"]
    assert len(profiles) == 2
    assert x_axis.shape[0] == profiles[0].shape[0] == profiles[1].shape[0]
    assert mixture.shape == x_axis.shape
    assert float(mixture.max()) > 0.0


def test_build_profiles_with_repo_cifs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cif_dir = repo_root / "cif"
    cif_files = [cif_dir / "LiCoO2.cif", cif_dir / "SrTiO3.cif"]
    assert all(path.is_file() for path in cif_files), "cif ディレクトリの CIF が見つかりません"

    labels, x_axis, profiles, mixture = build_profiles(
        cif_paths=[str(p) for p in cif_files],
        fractions=[0.5, 0.5],
        wavelength=1.5406,
        two_theta_range=(5.0, 80.0),
        step=0.02,
        offset=5.0,
    )

    assert labels == ["LiCoO2", "SrTiO3"]
    assert len(profiles) == 2
    assert x_axis.shape[0] == profiles[0].shape[0] == profiles[1].shape[0]
    assert mixture.shape == x_axis.shape
    assert float(mixture.max()) > 0.0


def test_export_and_load_profiles_roundtrip_csv(tmp_path: Path) -> None:
    labels = ["A", "B"]
    x_axis = pytest.importorskip("numpy").linspace(0, 10, 5)  # type: ignore[attr-defined]
    profiles = [x_axis * 2, x_axis * 3]
    mixture = x_axis * 5
    out = tmp_path / "out.csv"

    export_profiles(out, labels, x_axis, profiles, mixture, mixture_label="mix")
    loaded_labels, loaded_x, loaded_profiles, loaded_mixture, loaded_mix_label = load_profiles_file(out)

    assert loaded_labels == labels
    assert loaded_mix_label == "mix"
    assert pytest.approx(loaded_x) == x_axis
    assert len(loaded_profiles) == len(profiles)
    for p_loaded, p_orig in zip(loaded_profiles, profiles, strict=False):
        assert pytest.approx(p_loaded) == p_orig
    assert pytest.approx(loaded_mixture) == mixture


def test_export_and_load_profiles_roundtrip_json(tmp_path: Path) -> None:
    labels = ["A"]
    x_axis = pytest.importorskip("numpy").array([1.0, 2.0, 3.0])  # type: ignore[attr-defined]
    profiles = [x_axis + 1]
    mixture = x_axis + 2
    out = tmp_path / "out.json"

    export_profiles(out, labels, x_axis, profiles, mixture, mixture_label="sum")
    loaded_labels, loaded_x, loaded_profiles, loaded_mixture, loaded_mix_label = load_profiles_file(out)

    assert loaded_labels == labels
    assert loaded_mix_label == "sum"
    assert pytest.approx(loaded_x) == x_axis
    assert len(loaded_profiles) == 1
    assert pytest.approx(loaded_profiles[0]) == profiles[0]
    assert pytest.approx(loaded_mixture) == mixture


def test_export_and_load_profiles_roundtrip_parquet(tmp_path: Path) -> None:
    pa = pytest.importorskip("pyarrow")
    _ = pa  # silence lint for unused

    labels = ["A", "B"]
    x_axis = pytest.importorskip("numpy").array([0.0, 1.0])  # type: ignore[attr-defined]
    profiles = [x_axis + 1, x_axis + 2]
    mixture = x_axis + 3
    out = tmp_path / "out.parquet"

    export_profiles(out, labels, x_axis, profiles, mixture)
    loaded_labels, loaded_x, loaded_profiles, loaded_mixture, loaded_mix_label = load_profiles_file(out)

    assert loaded_labels == labels
    assert loaded_mix_label == "Mixture"
    assert pytest.approx(loaded_x) == x_axis
    for p_loaded, p_orig in zip(loaded_profiles, profiles, strict=False):
        assert pytest.approx(p_loaded) == p_orig
    assert pytest.approx(loaded_mixture) == mixture
