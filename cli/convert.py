"""convert.py 専用のコマンドライン引数定義."""

from __future__ import annotations

import argparse

from xrd_utils import WAVELENGTH_PRESETS


def parse_args() -> argparse.Namespace:
    """convert.py 用の引数をパースする."""
    parser = argparse.ArgumentParser(
        description="CIF からの計算または保存済みプロファイルを任意フォーマットへ再出力します。"
    )
    parser.add_argument("cifs", nargs="*", help="入力する CIF ファイルへのパス")
    parser.add_argument(
        "-o",
        "--output",
        default="xrd_profiles.png",
        help="出力ファイルパス (複数 CIF 時はカンマ区切り)",
    )
    parser.add_argument(
        "--output-format",
        choices=["png", "csv", "json", "parquet"],
        help="出力フォーマット (未指定なら拡張子から自動判定)",
    )
    parser.add_argument(
        "--input-profiles",
        help="保存済みのプロファイル (csv/json/parquet) をロードして出力に再利用",
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
        "--offset",
        type=float,
        default=0.0,
        help="各パターンに積み上げる縦軸オフセット",
    )
    parser.add_argument(
        "--fractions",
        "--ratios",
        dest="fractions",
        nargs="+",
        type=float,
        help="convert.py では無効 (エラーメッセージ用に受け付け)",
    )
    parser.add_argument(
        "--mode",
        choices=["standard", "mix"],
        default="standard",
        help="standard=各相+合成, mix=合成のみ (再出力時の構成)",
    )
    parser.add_argument(
        "--mixture-label",
        default="Mixture",
        help="合成プロファイルの凡例ラベル",
    )
    return parser.parse_args()
