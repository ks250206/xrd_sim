# xrd-sim

複数 CIF から XRD プロファイルを計算し、PNG の可視化から CSV / JSON / Parquet への保存・再変換までを 1 セットで扱えるツール群です。pymatgen による回折パターン計算を簡易 Voigt でブロード化し、matplotlib で ACS 風スタイルの図を描画します。

## できること

- CIF を複数読み込み、2θ 範囲・波長・ステップ幅を指定して回折パターンを計算
- 分率を正規化して合成プロファイル（黒線）を描画／保存、縦オフセットでプロットを見やすく
- PNG だけでなく CSV / JSON / Parquet への保存・再ロードをサポート（convert.py 形式）
- 分率の全探索（`--fractions-auto`）で組成スイープ出力

## 前提とセットアップ

- Python 3.13+
- 主要依存: `pymatgen`, `matplotlib`, `pyarrow`
- 推奨: `uv` での環境管理（`uv.lock` あり）

```bash
uv sync                # runtime 依存のみ
uv sync --extra dev    # 開発用に ruff / ty も入れる
```

## ツール別の使い分け

- `main.py` : PNG 専用。個別プロファイルのみ（合成なし）。入力は CIF か convert.py 形式の csv/json/parquet（複数同時指定可、2θ 軸が一致するものに限る）。
- `mix.py` : CIF から計算して PNG / CSV / JSON / Parquet を生成。`--mode=standard` で各相+合成、`--mode=mix` で合成のみ。`--fractions-auto` で組成全探索が可能。
- `convert.py` : 保存済みプロファイルを他フォーマットへ再出力、または CIF から等分率・offset=0 固定で計算して出力。複数 CIF のときは `--output` をカンマ区切りで入力数と同数指定。

## クイックスタート（付属 CIF を使用）

```bash
# 1) cifファイルをロードしてプロファイルを計算しプロットを作成
uv run main.py \
  cif/LiCoO2.cif cif/SrTiO3.cif cif/LiF.cif \
  --ratios 1 1 1 \
  --offset 120 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --output out/LCO_STO_LiF_all.png

# 2) mix.pyで保存したcsvファイルをロードしてプロファイルを計算しプロットを作成
uv run main.py \
  out/LCO_STO_LiF_mix_auto_*.csv \
  --offset 120 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --figsize 8,20 \
  --output out/LCO_STO_LiF_mix_auto.png

# 2) 7:3 で合成したプロファイルをPNGで出力（元のプロファイルと合成プロファイル両方をプロット）
uv run mix.py \
  cif/LiCoO2.cif cif/SrTiO3.cif \
  --fractions 0.7 0.3 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --offset 120 \
  --mode standard \
  --output out/LCO_STO_7_3_mix.png

# 3) 7:3 で合成したプロファイルをPNGで出力(合成プロファイルのみをプロット)
uv run mix.py \
  cif/LiCoO2.cif cif/SrTiO3.cif \
  --fractions 0.7 0.3 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --offset 120 \
  --mode mix \
  --output out/LCO_STO_7_3_mix_only.png

# 5)7:3 で合成したプロファイルをcsvで出力
uv run mix.py \
  cif/LiCoO2.cif cif/SrTiO3.cif \
  --fractions 0.7 0.3 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --offset 120 \
  --mode mix \
  --output out/LCO_STO_7_3_mix.csv

# 4) 分率を 0.1 刻みで全探索し、各組み合わせを自動命名で保存(合成プロファイルのみをプロット)
uv run mix.py \
  cif/LiCoO2.cif cif/SrTiO3.cif cif/LiF.cif \
  --fractions-auto \
  --fractions-step 0.1 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --offset 120 \
  --mode mix \
  --output out/LCO_STO_LiF_all.png

# 5) 分率を 0.1 刻みで全探索し、各組み合わせを自動命名でcsvに保存(合成プロファイルのみをプロット)
uv run mix.py \
  cif/LiCoO2.cif cif/SrTiO3.cif cif/LiF.cif \
  --fractions-auto \
  --fractions-step 0.1 \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --offset 120 \
  --mode mix \
  --output out/LCO_STO_LiF_mix_auto.csv

# 5) 保存済みプロファイルを別形式へ変換（CSV→Parquet）
uv run convert.py \
  out/LCO_STO_7_3_mix.csv \
  --output out/LCO_STO_7_3_mix.parquet

# 6) CIF から計算して JSON へ保存
uv run convert.py \
  cif/LiCoO2.cif \
  --wavelength-preset CuKa \
  --two-theta-min 10 \
  --two-theta-max 80 \
  --step 0.02 \
  --output out/LiCoO2.json
```

## 使い方の詳細

- 入力の種類

  - CIF を指定すると計算を実行。
  - 保存済みプロファイル（convert.py 形式）を使う場合:
    - `--input-profiles foo.csv bar.parquet ...` または `main.py foo.csv bar.parquet ...`
    - 全ファイルで 2θ 軸が一致している必要あり。mix モードで個別がないファイルは Mixture を 1 系列として扱う。

- 波長

  - 代表値を `--wavelength-preset` (`CuKa`/`CoKa`/`MoKa`, 既定 `CuKa`) で選択。
  - 数値で上書きする場合は `--wavelength 1.5406` のように指定。

- 分率（別名 `--ratios`）

  - `--fractions 0.7 0.3` のように指定。1 つだけ渡すと全相に適用。
  - `--fractions-auto --fractions-step 0.1` で 0.1 刻み全探索。

- モード

  - `main.py`: 個別プロファイルのみ（合成なし）、出力は PNG 固定。
  - `mix.py`: 個別 + 合成 (`--mode standard`) または合成のみ (`--mode mix`) を PNG/CSV/JSON/Parquet で出力。
  - `convert.py`: 保存済みプロファイルの再出力、または CIF から等分率・offset=0 で計算して任意フォーマット出力。

- 出力

  - `--output-format` 未指定なら拡張子で自動判定。`main.py` は PNG のみ。
  - `mix.py` で全探索時は `--output` が 1 つなら自動で組成タグ付きファイル名を展開。

- プロットの凡例とラベル
  - `mix.py` PNG: 個別は分率表示なし、Mixture は分率付きラベル。CSV では分率のカンマをセミコロンに置換。
  - 凡例は描画順を下 → 上の並びで表示されます。

## 主な引数のメモ

- 共通（CIF 計算時）: `--wavelength-preset`（`CuKa`/`CoKa`/`MoKa`、既定 `CuKa`）、`--wavelength`（数値で上書き）、`--two-theta-min` / `--two-theta-max`、`--step`
- 分率: `--fractions 0.7 0.3` など。1 つだけ渡した場合は全相に同じ値を適用。`--fractions-auto --fractions-step 0.1` で全探索。
- オフセット: `--offset` で縦方向に積み上げ。`main.py` は個別プロファイルのみ、`mix.py` は個別をオフセットして Mixture は個別の上に配置。
- 図サイズ: `--figsize 8,6` のように指定可能（main/mix いずれも）。
- 強度正規化: 出力前に最大強度が 100 になるようスケーリング。`mix.py` standard モードでは個別の見た目は分率で減衰しない（Mixture のみ分率反映）。
- モード: `--mode standard`（各相+合成）/ `mix`（合成のみ）。PNG でもデータ出力でも適用。
- 出力フォーマット: `--output-format` で明示、未指定なら拡張子から自動判定。`main.py` は PNG 固定。

CLI 実行後、保存先パスがログに表示されます。

## 保存ファイルの形式

- CSV: `2theta, <label...>, <mixture_label>` の列を持つ。`--mode=mix` の場合は `2theta` と合成列のみ。
- JSON: `{"labels": [...], "mixture_label": "...", "x_axis": [...], "profiles": [...], "mixture": [...], "mode": "standard|mix"}`。
- Parquet: 1 列目が `2theta`、最後の列が合成プロファイル（ラベルは `--mixture-label`、既定は `Mixture`）。

## リポジトリの構成

- `profiles.py` : pymatgen での計算、分率正規化、合成、CSV/JSON/Parquet の入出力を実装
- `plotting.py` / `style.py` : ACS 風スタイルの Matplotlib 図を生成
- `main.py` / `mix.py` / `convert.py` : CLI ワークフロー（引数パースは `cli/*.py`）
- `xrd_utils.py` : 共通ロジック
- `cif/` : サンプル CIF（LiCoO2, SrTiO3）
- `tests/` : pytest ベースの回帰テスト

## 開発と検証

```bash
uv run pytest            # 付属テストを実行
uv run ruff check .      # lint
uv run ruff format .     # 形式修正
uv run ty check -- notebook.py   # 型チェック（notebook.py は除外設定あり）
```

テスト時に Matplotlib の GUI バックエンドが必要な場合は `MPLBACKEND=Agg` を設定してください（例: `pytest` では既に monkeypatch 済み）。
