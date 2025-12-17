"""Plot individual XRD profiles to PNG (no mixture).

Input:
  - CIF files (set angle range, wavelength, step, fractions via --fractions/--ratios)
  - Or csv/json/parquet saved by convert.py via --input-profiles
Output:
  - Always PNG (no mixture). Legend = CIF names, vertical offset = --offset.
Use:
  - For mixture/data export use mix.py
  - For converting saved data use convert.py.
"""

from __future__ import annotations

# pyright: reportUndefinedVariable=false, reportMissingTypeStubs=false
# ruff: noqa: I001

import logging
from pathlib import Path

import numpy as np

from cli.main import parse_args
from xrd_utils import resolve_wavelength
from plotting import plot_profiles_without_mixture
from profiles import (
    TwoThetaRange,
    build_profiles,
    load_profiles_file,
    normalize_fractions,
    normalize_profiles,
)


def parse_figsize(value: str | None) -> tuple[float, float] | None:
    """Parse figsize string 'width,height' into a tuple."""
    if not value:
        return None
    try:
        width_str, height_str = value.split(",", maxsplit=1)
        return float(width_str), float(height_str)
    except Exception as exc:
        raise ValueError("--figsize は '幅,高さ' (例: 8,6) で指定してください。") from exc


def main() -> None:  # noqa: C901
    """Run the no-mixture PNG workflow.

    Flow:
    1) Parse args (CIF input or --input-profiles to load saved data).
    2) For CIF, compute profiles with pymatgen (fractions via --fractions/--ratios,
       default even split).
    3) For saved data, validate/parse convert.py format (csv/json/parquet).
    4) Save individual-only profiles to PNG (legend=filename, vertical offset=--offset).

    Notes:
    - Output is PNG only. For mixture/data export use mix.py; for re-export use convert.py.

    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    wavelength = resolve_wavelength(args)
    output_path = Path(args.output)
    output_format = (args.output_format or output_path.suffix.lstrip(".") or "png").lower()
    if output_format != "png":
        raise ValueError(
            "main.py は PNG 出力のみ対応です。mix.py / convert.py を使用してください。"
        )
    figsize = parse_figsize(args.figsize)

    # 入力がCSV/JSON/Parquetの場合は convert.py 形式であることを
    # load_profiles_file で検証しつつロード。
    # --input-profiles だけでなく、positional CIF 引数に単一の profiles ファイルが
    # 渡された場合も受け入れる(後方互換用)。
    profile_suffixes = {".csv", ".json", ".parquet"}

    if args.input_profiles:
        profile_paths = args.input_profiles
    else:
        profile_like = [p for p in args.cifs if Path(p).suffix.lower() in profile_suffixes]
        non_profile_like = [p for p in args.cifs if Path(p).suffix.lower() not in profile_suffixes]
        if profile_like and non_profile_like:
            raise ValueError(
                "CIF と csv/json/parquet を同時に指定できません。どちらかに統一してください。"
            )
        profile_paths = profile_like

    if profile_paths:
        labels: list[str] = []
        profiles: list[np.ndarray] = []
        x_axis: np.ndarray | None = None
        for path in profile_paths:
            lbls, x_axis_loaded, profs, mixture_loaded, mix_label_loaded = load_profiles_file(path)
            if not lbls and not profs:
                # mix モードのファイル (個別なし) の場合は Mixture を単独プロファイルとして扱う
                lbls = [mix_label_loaded]
                profs = [mixture_loaded]
            if x_axis is None:
                x_axis = x_axis_loaded
            elif x_axis.shape != x_axis_loaded.shape or not np.allclose(x_axis, x_axis_loaded):
                raise ValueError("複数のプロファイルで 2theta 軸が一致していません。")
            labels.extend(lbls)
            profiles.extend(profs)
        if not labels or not profiles or x_axis is None:
            raise ValueError("入力プロファイルに有効なデータがありません。")
    elif args.cifs:
        two_theta_range: TwoThetaRange = (
            float(args.two_theta_min),
            float(args.two_theta_max),
        )
        fractions = (
            normalize_fractions(args.fractions, len(args.cifs))
            if args.fractions
            else [1.0] * len(args.cifs)
        )
        labels, x_axis, profiles, _ = build_profiles(
            args.cifs,
            fractions,
            wavelength,
            two_theta_range,
            args.step,
            0.0,
        )
    else:
        raise ValueError("CIF または --input-profiles のいずれかを指定してください。")

    profiles, _, _ = normalize_profiles(profiles, None, target_max=100.0)

    plot_profiles_without_mixture(
        labels=labels,
        x_axis=x_axis,
        profiles=profiles,
        output=output_path,
        offset=args.offset,
        figsize=figsize,
    )

    logging.info("Saved: %s", output_path)


if __name__ == "__main__":
    main()
