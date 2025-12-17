from __future__ import annotations

import math
from pathlib import Path


def fraction_str(val: float) -> str:
    text = f"{val:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def generate_fraction_combinations(n: int, step: float) -> list[list[float]]:
    """Generate all fraction combinations summing to 1 with the given step."""
    if n < 1:
        raise ValueError("少なくとも 1 つの CIF を指定してください。")
    if step <= 0 or step > 1:
        raise ValueError("--fractions-step は 0 より大きく 1 以下にしてください。")

    inv = 1.0 / step
    inv_rounded = round(inv)
    if not math.isclose(inv, inv_rounded, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("--fractions-step は 1 を割り切れる値にしてください (例: 0.1, 0.05)。")

    total_units = int(inv_rounded)
    combinations: list[list[int]] = []

    def dfs(idx: int, remaining: int, current: list[int]) -> None:
        if idx == n - 1:
            combinations.append([*current, remaining])
            return
        for units in range(remaining + 1):
            dfs(idx + 1, remaining - units, [*current, units])

    dfs(0, total_units, [])
    return [[units * step for units in combo] for combo in combinations]


def resolve_output_paths(
    output: Path,
    fraction_sets: list[list[float]],
    default_format: str,
) -> list[Path]:
    """Resolve output paths for each fraction set."""
    raw = [Path(p) for p in str(output).split(",") if p]
    if not raw:
        raise ValueError("--output は少なくとも 1 つ指定してください。")

    if len(fraction_sets) == 1:
        if len(raw) != 1:
            raise ValueError("単一の分率組み合わせの場合、--output は 1 つにしてください。")
        return raw

    if len(raw) == len(fraction_sets):
        return raw

    if len(raw) == 1:
        base = raw[0]
        stem = base.stem or "xrd_profiles"
        parent = base.parent
        suffix = f".{default_format}"
        resolved: list[Path] = []
        for fracs in fraction_sets:
            tag = "_".join(f"f{idx + 1}-{fraction_str(f)}" for idx, f in enumerate(fracs))
            resolved.append(parent / f"{stem}_{tag}{suffix}")
        return resolved

    raise ValueError("分率組み合わせ数と出力ファイル数が一致しません。")

