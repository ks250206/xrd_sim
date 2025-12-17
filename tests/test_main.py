from __future__ import annotations

import sys
from pathlib import Path

import pytest

import main


def test_main_creates_png_from_cifs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cif_dir = repo_root / "cif"
    cif_files = [cif_dir / "LiCoO2.cif", cif_dir / "SrTiO3.cif"]
    assert all(path.is_file() for path in cif_files), "cif ディレクトリの CIF が見つかりません"

    output = tmp_path / "xrd.png"

    monkeypatch.setenv("MPLBACKEND", "Agg")
    monkeypatch.setattr(sys, "argv", [
        "xrd-sim",
        str(cif_files[0]),
        str(cif_files[1]),
        "--output",
        str(output),
        "--two-theta-min",
        "5",
        "--two-theta-max",
        "80",
        "--step",
        "0.05",
        "--offset",
        "5.0",
    ])

    main.main()

    assert output.is_file()
    assert output.stat().st_size > 0

