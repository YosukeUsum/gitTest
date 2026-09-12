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

### 機能追加: SPEC.md変更時の壁打ちログ

- 要望: SPEC.mdを更新する際にはClaudeが設計の壁打ち(論点出し・比較検討)を行うべきで、
  その過程をログとして残したい。通常のチャットは残さなくてよい。仕様も含めて決めてほしい。
- 対応:
  1. 本要望自体をNFR-7に関する壁打ちとみなし、
     `docs/spec-log/2026-08-29-spec-brainstorm-logging.md` に議論の要旨・選択肢比較・
     決定と根拠を記録(定義するプロセスを自己適用)。
  2. `SPEC.md` に NFR-7(SPEC.mdの要件・方針変更時は事前に壁打ちし、その要旨を
     `docs/spec-log/` へGit管理下のMarkdownで1テーマ1ファイル記録する。通常のQ&A・
     ツール操作補助・コードのみの作業・チャット逐語は対象外)を追記。11章の開発プロセス、
     6章のモジュールツリー、12章の改訂履歴も更新。
  3. `CLAUDE.md` を新規作成し、壁打ちログの起票・追記・完了手順、記録する/しないの線引き、
     保存先(`docs/spec-log/` はコミット対象、生成物の `logs/` と別)を明記。あわせて
     テスト実行(`py -3 -m pytest`)とNFR-5の注意点も記載。
  4. `docs/spec-log/` を新設。`README.md`(索引)と `TEMPLATE.md`(雛形)を追加。
  5. 機械的強制(フックによるSPEC.md編集ブロック)は誤検知で作業が止まるため初期導入は見送り、
     `CLAUDE.md` の運用ルールで統制する方針とした。

### 変更: CLI画面表示の日本語化(NFR-5の改訂)

- 要望: 操作ヘルプが英語(`Arrows:Move ...`)で表示されている。日本語にしたい。要件としても
  CLI 上に表示されるものは日本語にする。
- 経緯: NFR-5 は 2026-08-29 のバグ修正で「描画文字列は ASCII 限定」としていた
  (windows-curses が全角文字を含む文字列を `addstr` で描画すると桁がずれて重なるため)。
  単純に日本語へ戻すと不具合が再発するため、壁打ちを実施
  (`docs/spec-log/2026-08-29-cli-japanese-display.md`)。
- 対応:
  1. `SPEC.md` NFR-5 を改訂。ASCII 限定をやめ、`ui_curses.py` が各文字の表示幅を
     `unicodedata.east_asian_width` で判定(全角=2桁/半角=1桁)し、確定した桁位置へ
     1文字ずつ描画する方式で重なりを回避すると明文化。12章の改訂履歴も更新。
  2. `src/tetris_cli/ui_curses.py` に幅認識の描画ヘルパ `_draw_text()` / `_char_width()` を追加。
     サイドバー(テトリス/スコア/レベル/ライン/ネクスト)、`-- 一時停止中 --`、
     `ゲームオーバー`、`Q キーで終了`、操作ヘルプ(`矢印キー:移動  上/X:右回転  Z:左回転
     スペース:ハードドロップ  P:一時停止  Q:終了`)を日本語表記に変更。
  3. `main()` で `locale.setlocale(locale.LC_ALL, "")` を実行。
  4. 盤面の罫線(`|` `+` `-`)・セル表現(`[]`)・数値は ASCII のまま維持。
- 補足: 端末フォントが CJK 等幅でない場合に日本語ラベルの桁が1つずれる可能性は残るが、
  ASCII への切替オプションは設けず日本語固定とする(ユーザー判断)。

### 機能追加: ゲームループへの固定タイムステップ方式の導入(ループエンジニアリング)

- 要望: 「このアプリにループエンジニアリングを入れたい。簡単に試せる手順を教えて」。
  用語が曖昧だったため確認したところ、ゲームループ自体の改善(固定タイムステップ化)を
  指すとのことだった(壁打ちログ: `docs/spec-log/2026-08-29-game-loop-engineering.md`)。
- 経緯: 既存の `ui_curses.py` の `run()` は `time.sleep(0.02)` による単純なポーリングで、
  重力の自然落下(`game.tick()`)の呼び出しタイミングが実行環境の処理速度に直接依存し、
  かつcursesの実行関数に埋め込まれていて単体テストができなかった。
- 対応:
  1. `SPEC.md` に NFR-8(ゲームループを「入力処理→固定タイムステップ更新→描画→
     フレームレート制御」に分離。更新頻度はフレームレートに非依存で保証し、極端な
     経過時間はクランプしてスパイラル・オブ・デスを防止)を追記(NFR-7は既存の
     壁打ちログ運用ルールと番号が重複したため、ゲームループ側をNFR-8として採番)。
     AC-10・AC-11も追加。
  2. `src/tetris_cli/game_loop.py` を新規実装(curses非依存)。
     `FixedTimestepLoop`(アキュムレータ方式でtick回数を算出、
     `MAX_FRAME_TIME=0.25`秒でクランプ)と `FrameLimiter`
     (目標FPS=50からsleep時間を算出)を提供。
  3. `ui_curses.py` の `run()` を上記4段階に書き換え、`game.gravity_interval()`
     (レベルアップで短縮)を毎フレーム `timestep.update_interval` へ反映するようにした。
  4. `tests/test_game_loop.py` を新規作成(11件)。アキュムレータの基本動作、
     複数回分の経過時間蓄積、大きな経過時間のクランプ、`update_interval` の動的変更、
     `FrameLimiter` のsleep時間計算を検証。
  5. `docs/spec-log/README.md` の索引を更新。
  6. `CLAUDE.md` のNFR-5に関する記載が、既にコミット済みの日本語表示化(414e183)より
     古い内容(ASCII限定)のままになっていたため、実装に合わせて修正した。

### ドキュメント修正: Windowsでの実行時SyntaxErrorに関する案内を追加

- 事象: `python main.py` を実行すると `SyntaxError: future feature annotations is not defined`
  が発生。原因はWindowsの `python` コマンドが古いPython(3.6以前)を指していたため
  (`from __future__ import annotations` はPython 3.7以降が必要。本プロジェクトは
  NFR-4によりPython 3.9以上を前提としている)。同様の注意は既に `CLAUDE.md` の
  テスト実行の項に記載済みだったが、README.mdのセットアップ・実行・テストの各節には
  未反映だった。
- 対応: `README.md` の「セットアップ」「実行方法」「テスト」の各節に、
  Windowsで `python` が古いPythonを指す場合は `py -3`(Pythonランチャーで3.8以上を
  明示)を使う旨を追記した。SPEC.mdの要件変更を伴わない案内文の修正のため、
  壁打ちログ(docs/spec-log/)の起票は対象外とした(CLAUDE.mdの「記録しない」対象)。

### ドキュメント修正: windows-cursesが見つからないエラーの案内を追加

- 事象: `py -3 main.py` を実行すると `ModuleNotFoundError: No module named '_curses'`
  が発生。Windows版の標準Pythonには `curses` モジュールが含まれておらず、
  `requirements.txt` の `windows-curses`(条件付き依存)が、実行に使うインタプリタ
  (`py -3` = Python 3.8)とは別のインタプリタにインストールされていたことが原因。
- 対応: README.mdに、実行コマンドと同じインタプリタで
  `py -3 -m pip install -r requirements.txt` を実行する旨、および
  `py -3 -c "import curses; print('OK')"` での確認方法を追記した。
  SPEC.md変更を伴わないため壁打ちログの起票は対象外(CLAUDE.md運用どおり)。

### 開発プロセス追加: PM/PL/BA/QAの役割定義(恒常的なロール分担)

- 要望: 一人のエンジニアでも、本物のPJのようにPM/PL/BA/QA等の役割を分担して開発を回せる
  ようにしたい。会話ベースで検討した結果、その場限りではなく恒常的な役割定義として導入する
  ことになった(BUは「ビジネスユーザー(エンドユーザー代表)」の意)。
- 対応:
  1. `.claude/agents/pm.md` / `pl.md` / `ba.md` / `qa.md` を新規作成。各ロールの責務・
     参照ドキュメント・やらないこと・出力形式を定義した。
     - PM: 要望のスコープ確定・優先順位判断・進捗報告
     - PL: アーキテクチャ判断・実装方式の比較検討・壁打ちログ下書き
     - BA: 曖昧な要望のFR/NFR/AC構造化・壁打ちログ起票
     - QA: 受け入れ基準の検証・テスト実行・logs/確認
  2. `CLAUDE.md` に「役割定義(PM/PL/BA/QA)」の節を追加し、通常の(単独エンジニアとして
     の)壁打ちログ運用との使い分けを明記。
  3. SPEC.md(FR/NFR/AC)の変更を伴わない開発プロセス・ツール面の変更のため、
     壁打ちログ(docs/spec-log/)の起票は対象外とした(CLAUDE.mdの「記録しない」対象)。

### 機能追加: ブロックの種類ごとの色分け表示

- 要望: 「ゲーム内でブロックが白と黒しかなく、色がなくてわかりにくいから色分けして」。
  壁打ちログ: `docs/spec-log/2026-09-12-block-color-coding.md`。
- 対応:
  1. `SPEC.md` に FR-14(盤面のブロックをミノの種類ごとに色分け表示。
     I=シアン/O=黄/T=マゼンタ/S=緑/Z=赤/J=青/L=白)と、NFR-9(色非対応端末では
     モノクロにフォールバックしクラッシュしない)を追加。12章の改訂履歴も更新。
  2. `src/tetris_cli/ui_curses.py` に `COLOR_ID_TO_CURSES_COLOR`
     (`tetromino.KIND_TO_COLOR` の色IDをcursesの色定数へ対応付ける辞書)と
     `_init_colors()`(`curses.has_colors()` を確認し、対応していれば
     `curses.start_color()`/`init_pair()` で初期化。非対応なら何もせず `False` を返す)
     を追加。
  3. `_draw_board()` を、行全体をまとめて描画する方式からセル単位で描画する方式に
     変更し、各セルの色ID(落下中ピース or 固定ブロック)に応じて
     `curses.color_pair()` を適用するようにした。色非対応時は従来通りの
     `curses.A_NORMAL` で描画する。
  4. `tests/test_ui_curses_colors.py` を新規作成(3件)。色IDの対応表が7種すべてを
     網羅していること、色の重複がないこと、有効なcurses色定数であることを検証。
     全33件のテストがパス。
  5. 変更範囲は盤面のブロックのみとし、サイドバーのラベル等の色付けは対象外とした
     (壁打ちで見送り)。

### 機能追加: 配色・見た目のモダン化(ぷよぷよ的な今風の表現)

- 要望: 「配色や背景などをもっと今風にして、たとえばぷよぷよとか」。
  壁打ちログ: `docs/spec-log/2026-09-12-modern-color-scheme.md`。
- 対応:
  1. `SPEC.md` に FR-15(ブロックを輪郭表示から塗りつぶし表示に変更し、盤面の枠線・
     タイトル・状態メッセージにアクセントカラーを付ける)、NFR-10(色非対応端末への
     フォールバックの拡張)、AC-12 を追加。12章の改訂履歴も更新。
  2. `src/tetris_cli/ui_curses.py`:
     - `_init_colors()` で、ミノの色(`COLOR_ID_TO_CURSES_COLOR`)を文字色ではなく
       背景色に割り当てるよう変更(`curses.init_pair(color_id, BLACK, fg)` に変更)。
     - 枠線・タイトル・「一時停止中」・「ゲームオーバー」用のアクセントカラー
       `UI_ACCENT_PAIRS`(シアン/マゼンタ/黄/赤、ミノの色ID 1〜7とは別のペア番号
       8〜11)を新設。
     - `_draw_board()` を、色対応端末ではブロックを2文字の空白+背景色で塗りつぶし、
       盤面の枠線にシアン+太字を付けるよう変更。色非対応端末では従来通り `[]` の
       輪郭表示・無配色の枠線にフォールバック。
     - `_draw_text()` に `attr` 引数を追加し、文字色・太字等の表示属性を指定できる
       ようにした(省略時は `curses.A_NORMAL` で後方互換)。
     - `_draw_sidebar()` で、タイトルにマゼンタ+太字、「一時停止中」に黄+太字、
       「ゲームオーバー」に赤+太字を付けるよう変更(`_accent_attr()` を追加)。
  3. `tests/test_ui_curses_colors.py` に9件のテストを追加(計12件)。
     `UI_ACCENT_PAIRS` がミノの色IDと衝突しないこと、4要素(border/title/paused/
     game_over)を網羅すること、`_accent_attr()` が色非対応時にA_NORMALへ
     フォールバックすること・色対応時に太字+color_pair()を返すこと(`curses.color_pair`
     を実端末不要なダミーに差し替えて検証)、`_draw_text()` の `attr` 引数が
     各文字に適用されることを検証。全41件のテストがパス。
  4. 盤面の空セル自体への背景色付け(「盤面背景」)は、標準8色をミノの色で
     使い切っている制約上、視認性低下を理由に見送った。256色/RGB拡張パレットも、
     前回(ブロック色分け)の壁打ちと同じ理由(対応端末の制限、NFR-1との不整合)で
     見送った(詳細は壁打ちログ参照)。
