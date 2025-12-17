"""Re-export XRD profiles or compute from CIF and output any supported format.

Input:
  - Load csv/json/parquet (convert.py format) via --input-profiles, or
  - Specify CIF files to compute (fractions auto-even, offset=0).
Output:
  - PNG / CSV / JSON / Parquet (decided by extension or --output-format).
Rules:
  - For multiple CIFs, --output must be comma-separated with the same count as inputs.
  - For no-mixture plotting only, use main.py. For CIF compute + mixture export, use mix.py.
"""

from __future__ import annotations

# pyright: reportUndefinedVariable=false, reportMissingTypeStubs=false
# ruff: noqa: I001

import logging
from pathlib import Path

from cli.convert import parse_args
from xrd_utils import resolve_wavelength
from plotting import plot_profiles
from profiles import (
    TwoThetaRange,
    build_profiles,
    export_profiles,
    load_profiles_file,
    normalize_profiles,
    apply_offsets,
)


def main() -> None:
    """Run conversion workflow or compute-from-CIF workflow.

    Flow:
    1) Parse args. If --input-profiles, validate/load csv/json/parquet.
    2) If CIFs are provided, compute with even fractions and offset=0.
    3) Decide output format by extension or --output-format; save as PNG/CSV/JSON/Parquet.
    4) With multiple CIFs, --output must list the same count (comma-separated).

    Notes:
    - Ratios/offset cannot be set (even fractions, offset=0). For no-mixture plotting use main.py;
      for CIF compute + mixture export use mix.py.

    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    wavelength = resolve_wavelength(args)
    output_path = Path(args.output)

    if args.fractions:
        raise ValueError("convert.py では --fractions を指定できません (自動で等分配します)。")
    if args.offset not in (None, 0, 0.0):
        raise ValueError("convert.py では --offset は使用できません (常に 0 を使用します)。")

    outputs: list[Path]
    profile_suffixes = {".csv", ".json", ".parquet"}

    if args.input_profiles:
        profile_paths = [args.input_profiles]
    else:
        profile_like = [p for p in args.cifs if Path(p).suffix.lower() in profile_suffixes]
        non_profile_like = [p for p in args.cifs if Path(p).suffix.lower() not in profile_suffixes]
        if profile_like and non_profile_like:
            raise ValueError(
                "CIF と csv/json/parquet を同時に指定できません。どちらかに統一してください。"
            )
        profile_paths = profile_like

    if profile_paths:
        labels, x_axis, profiles, mixture, loaded_mixture_label = load_profiles_file(
            profile_paths[0]
        )
        mixture_label = args.mixture_label or loaded_mixture_label
        outputs = [output_path]
    else:
        if not args.cifs:
            raise ValueError("CIF を指定するか --input-profiles を指定してください。")
        two_theta_range: TwoThetaRange = (
            float(args.two_theta_min),
            float(args.two_theta_max),
        )
        fractions = [1.0 / len(args.cifs)] * len(args.cifs)
        labels, x_axis, profiles, mixture = build_profiles(
            args.cifs,
            fractions,
            wavelength,
            two_theta_range,
            args.step,
            0.0,
        )
        mixture_label = args.mixture_label
        outputs = [Path(p) for p in str(output_path).split(",") if p]
        if len(args.cifs) > 1 and len(outputs) != len(args.cifs):
            raise ValueError("入力 CIF 数と --output で指定したファイル数が一致していません。")
        if not outputs:
            outputs = [output_path]

    mode = args.mode
    # 単一プロファイルの場合は Mixture 列を出力せず、mix モード相当で扱う
    if len(profiles) == 1:
        mode = "mix"
        mixture = profiles[0]
        mixture_label = labels[0]
        profiles = []

    profiles, mixture_normalized, _ = normalize_profiles(profiles, mixture, target_max=100.0)
    if mixture_normalized is None:
        raise RuntimeError("mixture 正規化に失敗しました。")
    mixture = mixture_normalized
    profiles = apply_offsets(profiles, args.offset or 0.0)

    for out in outputs:
        fmt = (args.output_format or out.suffix.lstrip(".") or "png").lower()
        if fmt == "png":
            plot_profiles(
                labels=labels,
                x_axis=x_axis,
                profiles=profiles,
                mixture=mixture,
                output=out,
                offset=0.0,
                mixture_label=mixture_label,
                mode=mode,
            )
        elif fmt in {"csv", "json", "parquet"}:
            export_profiles(
                out,
                labels=labels,
                x_axis=x_axis,
                profiles=profiles,
                mixture=mixture,
                mixture_label=mixture_label,
                mode=mode,
            )
        else:
            raise ValueError("サポートされていない出力フォーマットです。")

        logging.info("Saved: %s", out)


if __name__ == "__main__":
    main()
