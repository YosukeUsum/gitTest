# Tetris CLI

Python標準ライブラリ(curses)で動作する、ターミナル上で遊べるテトリスです。
本プロジェクトは仕様駆動開発(Spec-Driven Development)で実装されており、
詳細な仕様は [SPEC.md](./SPEC.md) を参照してください。

## 必要環境

- Python 3.9 以上
- Windows の場合のみ `windows-curses` が必要です(`requirements.txt` に含まれます)

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 実行方法

```bash
python main.py
```

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

## プロジェクト構成

```
src/tetris_cli/
├── tetromino.py   # テトリミノの形状・回転定義
├── board.py       # 盤面・衝突判定・ライン消去
├── game.py        # ゲームロジック(UI非依存)
└── ui_curses.py   # curses描画・入力
main.py             # エントリーポイント
tests/               # pytestによる単体テスト
```

## 開発プロセス

本プロジェクトは以下の流れで開発されています(詳細は SPEC.md 11章):

1. `SPEC.md` に要件・受け入れ基準を定義
2. 受け入れ基準に対応するテストを作成
3. テストが通るようロジックを実装
4. curses UIで統合
5. `pytest` で全テストが合格することを確認
