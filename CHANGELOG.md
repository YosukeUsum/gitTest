# CHANGELOG

本プロジェクトの開発履歴。仕様駆動開発(Spec-Driven Development)の方針に基づき、
仕様(SPEC.md)の変更を伴う対応は、その都度SPEC.mdの更新とあわせて記録する。

## 2026-08-29

### 初期仕様策定・実装

- `SPEC.md` を作成。テトリスCLIアプリの機能要件(FR-1〜13)、非機能要件(NFR-1〜4)、
  アーキテクチャ、受け入れ基準(AC-1〜9)、開発プロセスを定義。
- ロジック層を実装。
  - `src/tetris_cli/tetromino.py`: 7種のテトリミノ形状・回転定義・ウォールキック
  - `src/tetris_cli/board.py`: 盤面の衝突判定・ライン消去
  - `src/tetris_cli/game.py`: 7-bagランダム出現・スコア/レベル管理・ゲームオーバー判定
    (curses非依存)
- UI層を実装。
  - `src/tetris_cli/ui_curses.py`: curses描画・キー入力
  - `main.py`: エントリーポイント
- 受け入れ基準(AC-1〜9)に対応するpytestテストを `tests/` に作成し、20件全件パスを確認。
- VSCode向け設定を追加(`.vscode/settings.json`, `launch.json`, `extensions.json`)。
- gitリポジトリを初期化し、初回コミットを作成。
- GitHubリポジトリ `https://github.com/YosukeUsum/gitTest` にremoteを設定し、`main`
  ブランチをpush。

### バグ修正: windows-curses環境でのCLI画面の文字重なり

- 事象: `python main.py` をWindows上で実行すると、画面下部のキー操作ヘルプ
  (矢印キー案内など)や `Qで終了` の表示で、文字が斜めにずれて重なって表示される
  不具合が発生(スクリーンショットで確認)。
- 原因: windows-cursesは全角文字(日本語など)を含む文字列を `addstr` で描画する際に、
  文字幅の扱いが不正確になり、同一セルに複数文字が重なって描画される問題がある。
- 対応:
  1. `SPEC.md` に NFR-5(curses描画文字列はASCIIのみで構成する)を追記(仕様を先に更新)。
  2. `src/tetris_cli/ui_curses.py` の `KEY_BINDINGS_HELP` および `"Qで終了"` を、
     半角英数字のみの表記(`"Arrows:Move  Up/X:RotateR  Z:RotateL  Space:HardDrop  P:Pause  Q:Quit"`,
     `"Press Q to quit"`)に変更。
  3. ドキュメント(SPEC.md・README.md)やソースコードコメントの日本語表記はそのまま維持
     (画面に直接描画される文字列のみが対象)。

### 機能追加: pytest実行ログの記録

- 要望: テスト実行時に、成功・失敗にかかわらず結果のログを残したい。ログの単位は
  テスト実行ごとに1ファイルとする。
- 対応:
  1. `SPEC.md` に NFR-6(pytest実行のたびに `logs/` へ1ファイルの実行ログを残す)を
     追記(仕様を先に更新)。
  2. `conftest.py` を新規作成。pytestの `pytest_configure` / `pytest_runtest_logreport` /
     `pytest_sessionfinish` フックを利用し、実行開始時刻を含む一意なファイル名
     (`logs/test_run_<日時>.log`)でログファイルを作成。各テストの結果
     (PASS/FAIL/ERROR/SKIP)・失敗時の詳細・最終サマリ(合計/成功/失敗/スキップ件数、
     終了ステータス)を記録する。
  3. `logs/` ディレクトリを追加し、`.gitkeep` で構造のみコミット。生成される
     `*.log` ファイル自体は `.gitignore` でコミット対象外とした。
  4. README.mdにログ出力についての説明を追記。
