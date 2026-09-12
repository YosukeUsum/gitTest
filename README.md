# Tetris CLI

Python標準ライブラリ(curses)で動作する、ターミナル上で遊べるテトリスです。
本プロジェクトは仕様駆動開発(Spec-Driven Development)で実装されており、
詳細な仕様は [SPEC.md](./SPEC.md) を、開発履歴は [CHANGELOG.md](./CHANGELOG.md) を参照してください。

## 必要環境

- Python 3.9 以上
- Windows の場合のみ `windows-curses` が必要です(`requirements.txt` に含まれます)

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **Windows で `SyntaxError: future feature annotations is not defined` が出る場合**
> `python` コマンドが古いPython(3.6以前)を指していることが原因です。本プロジェクトは
> `from __future__ import annotations`(Python 3.9対応/NFR-4)を使用しています。
> `python` の代わりに Python ランチャーで **3.8以上** を明示的に指定してください。
>
> ```bash
> py -3 -m venv .venv
> .venv\Scripts\activate
> py -3 -m pip install -r requirements.txt
> ```

## 実行方法

```bash
python main.py
```

Windowsで上記の `SyntaxError` が出る場合は、`py -3 main.py` のように
Pythonランチャーで3.8以上を明示して実行してください。

## 操作方法

| キー | 動作 |
|---|---|
| ← / → | 左右移動 |
| ↓ | ソフトドロップ |
| ↑ または X | 時計回り回転 |
| Z | 反時計回り回転 |
| Space | ハードドロップ |
| P | 一時停止 / 再開 |
| Q | 終了 |

## テスト

```bash
pytest
```

Windowsで `python`/`pytest` が古いPythonを指す場合は `py -3 -m pytest` を使ってください
(詳細は [CLAUDE.md](./CLAUDE.md))。

テストを実行するたびに、成功・失敗にかかわらず `logs/test_run_<実行日時>.log`
というログファイルが1件作成されます(実行のたびに新規ファイルとして残るため、
過去の実行結果は上書きされません)。各テストの成否と最終サマリが記録されます。

## プロジェクト構成

```
src/tetris_cli/
├── tetromino.py   # テトリミノの形状・回転定義
├── board.py       # 盤面・衝突判定・ライン消去
├── game.py        # ゲームロジック(UI非依存)
├── game_loop.py   # 固定タイムステップ制御・フレームレート制御(UI非依存)
└── ui_curses.py   # curses描画・入力
main.py             # エントリーポイント
tests/               # pytestによる単体テスト
```

## 開発プロセス

本プロジェクトは以下の流れで開発されています(詳細は SPEC.md 11章):

1. `SPEC.md` の要件・方針を変更する場合は、先に設計判断の壁打ちを行い、その要旨を
   `docs/spec-log/` に記録する(NFR-7。運用の詳細は [CLAUDE.md](./CLAUDE.md))
2. `SPEC.md` に要件・受け入れ基準を定義
3. 受け入れ基準に対応するテストを作成
4. テストが通るようロジックを実装
5. curses UIで統合
6. `pytest` で全テストが合格することを確認
