"""main.py 専用のコマンドライン引数定義."""

from __future__ import annotations

import argparse

from xrd_utils import WAVELENGTH_PRESETS


def parse_args() -> argparse.Namespace:
    """main.py 用の引数をパースする."""
    parser = argparse.ArgumentParser(
        description="複数 CIF の XRD プロファイルを計算し、合成なしで PNG に保存します。"
    )
    parser.add_argument("cifs", nargs="*", help="入力する CIF ファイルへのパス")
    parser.add_argument("-o", "--output", default="xrd_profiles.png", help="出力ファイルパス")
    parser.add_argument(
        "--output-format",
        choices=["png"],
        help="出力フォーマット (main.py は PNG のみ対応)",
    )
    parser.add_argument(
        "--input-profiles",
        nargs="+",
        help="保存済みのプロファイル (csv/json/parquet) をロードして PNG に再出力",
    )
    parser.add_argument(
        "--wavelength",
        type=float,
        help="X線波長 (A)。指定が無い場合は --wavelength-preset を使用",
    )
    parser.add_argument(
        "--wavelength-preset",
        choices=sorted(WAVELENGTH_PRESETS.keys()),
        default="CuKa",
        help="代表的な波長プリセット (デフォルト: CuKa)",
    )
    parser.add_argument(
        "--two-theta-min",
        type=float,
        default=10,
        help="2θ 下限 (deg)",
    )
    parser.add_argument(
        "--two-theta-max",
        type=float,
        default=80.0,
        help="2θ 上限 (deg)",
    )
    parser.add_argument(
        "--step",
        type=float,
        default=0.02,
        help="プロファイル計算の 2θ 分解能 (deg)",
    )
    parser.add_argument(
        "--fractions",
        "--ratios",
        dest="fractions",
        nargs="+",
        type=float,
        help="各相の分率 (--ratios は互換エイリアス)。1 つだけ渡した場合は全相に同一値を適用",
    )
    parser.add_argument(
        "--offset",
        type=float,
        default=0.0,
        help="各パターンに積み上げる縦軸オフセット",
    )
    parser.add_argument(
        "--figsize",
        help=(
            "図のサイズを '幅,高さ' (インチ) で指定 (例: 8,6)。未指定なら Matplotlib のデフォルト。"
        ),
    )
    return parser.parse_args()
