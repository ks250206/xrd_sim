"""Generate and export XRD profiles with mixture support.

Input:
  - CIF (one or more). Fractions can be given explicitly, or auto-generated with
    --fractions-auto and --fractions-step.
Output:
  - PNG / CSV / JSON / Parquet. If --mode=standard, output individual + mixture;
    if --mode=mix, output mixture only.

Notes:
  - Conversion of saved profiles is handled by convert.py (this script rejects --input-profiles).
  - To sweep fractions automatically, use --fractions-auto --fractions-step 0.1, etc.

"""

from __future__ import annotations

# pyright: reportUndefinedVariable=false, reportMissingTypeStubs=false
# ruff: noqa: I001

import logging
from pathlib import Path
from cli.mix import parse_args
from xrd_utils import resolve_wavelength
from mix_utils import fraction_str, generate_fraction_combinations, resolve_output_paths
from plotting import plot_profiles
from profiles import (
    TwoThetaRange,
    compute_individual_profiles,
    combine_profiles,
    export_profiles,
    normalize_fractions,
    normalize_profiles,
    apply_offsets,
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


def main() -> None:
    """Run mixture-enabled workflow for PNG/CSV/JSON/Parquet.

    Flow:
    1) Parse args. CIF is required. With --fractions-auto, generate all combinations.
    2) Compute per-phase profiles (shared x-axis) via pymatgen.
    3) For each fraction set, combine and save in chosen format
       (mode=standard: individual + mixture, mode=mix: mixture only).
    4) Output filenames come from --output (comma-separated) or auto-tagged per fraction set.

    Notes:
    - Conversion of saved profiles is handled by convert.py (this rejects --input-profiles).
    - If no fractions are given, even split is used.

    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()
    wavelength = resolve_wavelength(args)
    output_path = Path(args.output)
    default_output_format = (args.output_format or output_path.suffix.lstrip(".") or "png").lower()
    figsize = parse_figsize(args.figsize)

    two_theta_range: TwoThetaRange = (
        float(args.two_theta_min),
        float(args.two_theta_max),
    )

    if args.fractions_auto:
        if args.fractions:
            raise ValueError("--fractions-auto 使用時は --fractions を併用できません。")
        fraction_sets = generate_fraction_combinations(len(args.cifs), float(args.fractions_step))
    else:
        fractions = (
            normalize_fractions(args.fractions, len(args.cifs))
            if args.fractions
            else [1.0 / len(args.cifs)] * len(args.cifs)
        )
        fraction_sets = [fractions]

    labels, x_axis, base_profiles = compute_individual_profiles(
        args.cifs,
        wavelength,
        two_theta_range,
        args.step,
    )
    mixture_label = args.mixture_label

    mode = args.mode

    outputs = resolve_output_paths(output_path, fraction_sets, default_output_format)

    for fracs, out in zip(fraction_sets, outputs, strict=False):
        fractions_normalized = normalize_fractions(fracs, len(args.cifs))
        profiles, mixture = combine_profiles(base_profiles, fractions_normalized, args.offset)
        profiles, mixture_normalized, _ = normalize_profiles(profiles, mixture, target_max=100.0)
        if mixture_normalized is None:
            raise RuntimeError("mixture 正規化に失敗しました。")
        mixture = mixture_normalized
        # standard モードでは個別プロファイルは分率で減衰させず、base を別途正規化して描画に使う
        if mode == "standard":
            display_profiles, _, _ = normalize_profiles(base_profiles, None, target_max=100.0)
        else:
            display_profiles = profiles
        display_profiles = apply_offsets(display_profiles, args.offset)

        mixture_label_with_frac = (
            f"{mixture_label} ({', '.join(f'{f:.3f}' for f in fractions_normalized)})"
        )
        mixture_label_csv = mixture_label_with_frac.replace(",", ";")

        fmt = (args.output_format or out.suffix.lstrip(".") or default_output_format).lower()
        if fmt == "png":
            plot_profiles(
                labels=list(labels),
                x_axis=x_axis,
                profiles=display_profiles,
                mixture=mixture,
                output=out,
                offset=args.offset,
                mixture_label=mixture_label_with_frac,
                mode=mode,
                figsize=figsize,
            )
        elif fmt in {"csv", "json", "parquet"}:
            export_profiles(
                out,
                labels=labels,
                x_axis=x_axis,
                profiles=profiles,
                mixture=mixture,
                mixture_label=mixture_label_csv if fmt == "csv" else mixture_label_with_frac,
                mode=mode,
            )
        else:
            raise ValueError("サポートされていない出力フォーマットです。")

        logging.info("fractions=%s -> Saved: %s", ", ".join(map(fraction_str, fracs)), out)


if __name__ == "__main__":
    main()
