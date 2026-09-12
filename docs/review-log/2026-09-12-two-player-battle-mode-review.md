# レビュー結果ログ: 2人対戦モード(お邪魔行攻撃)

- 対象要件: FR-17〜FR-22, NFR-14〜NFR-16, AC-14〜AC-19
- 対象実装: `src/tetris_cli/battle.py`, `src/tetris_cli/board.py`(`add_garbage_rows`), `src/tetris_cli/game.py`(`on_locked`/`on_before_spawn`), `src/tetris_cli/ui_curses.py`(`run_battle`)
- 対象テスト: `tests/test_battle.py`
- 関連実装コミット: `03d25e7`
- 関連壁打ちログ: `docs/spec-log/2026-09-12-two-player-battle-mode.md`
- 実行方式: 評価者(reviewer)を独立エージェントとして起動(実装セッションのコンテキストを引き継がせず、要件IDとテスト対象を明示)。指摘があれば実装セッションで修正し、`pytest` 再合格後に再度評価者を起動。最大3ラウンドまで。

## ラウンド1

### カバーできている観点の要約

- AC-14(攻撃力テーブル 1/2/3/4行→0/1/2/4): `test_attack_table_matches_spec` で網羅。
- AC-15(部分相殺・新規攻撃なし)・AC-16(相殺超過分の送信): それぞれ専用テストで境界を確認。
- FR-20の暗黙の仕様(消去0行でも相殺手順自体は適用される)は `test_no_clear_still_runs_cancel_step_as_noop` でカバー。
- AC-17(保留分の盤面反映と0リセット)・AC-18(お邪魔行の形状: 1列だけ空き・残り9マスが `GARBAGE_COLOR`)を個別にテスト。
- AC-19(勝敗判定): 継続中/片方ゲームオーバー/同時ゲームオーバー(引き分け)の3分岐をそれぞれ検証。
- `Game.hard_drop()` 経由で `on_locked` フックが実際に呼ばれることを確認する結合テストが1件ある(配線確認)。

### 不足している観点(深刻度付き)

**必須**

1. お邪魔行反映によるゲームオーバー(FR-22後段/AC-19の派生ケース)が未検証。盤面上部近くまで積んだ状態で `add_garbage_rows()` が呼ばれ、実際に衝突して `game_over=True` になる因果経路がテストされていない。
2. `BattleGame.update()` を経由した、ライン消去エフェクトとFR-20手順3(反映の遅延)の実結合が一切テストされていない(`test_battle.py` に `update()` を呼ぶテストが1件も無い)。
3. `Board.add_garbage_rows(count)` で `count >= board.height` になる境界値が未テスト。実装(`self.grid = self.grid[count:]` の後に `count` 行追加)は `count >= height` のとき盤面の高さ不変条件(`len(grid) == height`)を壊す疑いがある。

**推奨**

4. 攻撃力とちょうど保留数が一致するケース(相殺後に保留0・新規攻撃0)が未テスト。
5. `add_garbage_rows()` の通常ケースでも `len(board.grid) == board.height` を明示的にアサートするテストがない。
6. 相手からの複数回攻撃が `pending_garbage` に単純加算で積み上がることを確認するテストがない。
7. NFR-16(第2プレイヤーのキー割り当てが第1プレイヤー・共通操作と重複しない)を確認する、curses非依存の静的な重複チェックテストがない。
8. FR-18(各プレイヤーが独立したGame/Board等を持つこと)を明示的に確認するテストがない。

**任意**

9. `--2p` 引数によるエントリポイント切替(FR-17)のテスト(UI層のため優先度低)。
10. お邪魔行の空き列の統計的独立性検証は壁打ちログで対象外と明記済みのため見送り。

### 冗長・無効なテストの指摘

- `test_real_line_clear_sends_attack_through_game_hooks` は1行消去(攻撃力0)のケースのみで、フック配線の確認に留まり結合検証としては弱い。2行以上の消去で実際に相手へ攻撃が発生するケースまで拡張すべき。

### 総合判定

**追加テストが必要。** 特に(1)お邪魔行反映によるゲームオーバー経路、(2)`update()`経由のエフェクト遅延との実結合、(3)`add_garbage_rows`の境界値(潜在バグ疑い)の3点は要件の設計根拠に直結するため優先度高。

### 対応方針

- 必須3件(お邪魔行ゲームオーバー経路、update()結合、add_garbage_rows境界値+実装修正)に対応。
- 推奨のうち4, 5, 6, 8(境界値・不変条件・独立性の基本アサーション)を追加。
- 弱いテスト(`test_real_line_clear_sends_attack_through_game_hooks`)を2行消去で攻撃が発生するケースまで拡張。
- 推奨7(NFR-16キー重複チェック)・任意9, 10は今回のスコープでは見送り(任意/UI層のため優先度が相対的に低く、必須修正を優先)。

### 実施した修正(ラウンド1指摘への対応)

- `src/tetris_cli/board.py`: `add_garbage_rows()` で `count` を `min(count, self.height)` にクランプし、`count >= height` でも盤面高さ不変条件(`len(grid) == height`)を保つよう修正(必須3への対応)。
- `tests/test_battle.py` に以下を追加:
  - `test_garbage_reflection_can_cause_game_over_by_collision`(必須1: お邪魔行反映によるゲームオーバー経路)
  - `test_garbage_not_applied_until_line_clear_effect_completes`(必須2: `update()`経由のエフェクト遅延との実結合)
  - `test_add_garbage_rows_preserves_board_height_in_normal_case` / `test_add_garbage_rows_count_exceeding_height_is_clamped`(必須3の回帰テスト)
  - `test_cancel_exact_match_results_in_zero_pending_and_zero_new_attack`(推奨4)
  - `test_pending_garbage_accumulates_across_multiple_opponent_attacks`(推奨6)
  - `test_each_player_has_independent_game_board_and_score`(推奨8)
  - `test_real_two_line_clear_sends_nonzero_attack_through_game_hooks`(弱いテストの補強: 実際に攻撃が発生する経路)
- `pytest`(`tests/test_battle.py`: 19件、全体: 75件)は全件合格を確認。

## ラウンド2

### ラウンド1指摘の解消状況(評価者による検証)

必須1〜3・推奨4・6・8・弱いテストの補強、いずれも「解消」と判定された(具体的なコード変更・テストで裏付けられており、指摘の再現ケースを正しく踏まえている)。

### 新たに識別した不足観点

**必須級**

1. `BattleGame.winner` の3分岐のうち、`PLAYER_2`単独トップアウトのケース(`if p2_over: return PLAYER_1`)が一切未検証。既存テストは「PLAYER_1単独」「両者同時」のみで、AC-19の対称ケースを欠く。PLAYER_1/PLAYER_2の取り違えを検出できないリスクがある。

**推奨**

2. `_on_locked`/`_on_before_spawn`のPLAYER_2側フック配線が実際に機能することを検証する結合テストが無い(既存の実結合テストはいずれも`battle.player1`のみ操作)。対称なラムダ定義のコピペミスを検出できないリスク。
3. 「エフェクト完了→`update()`経由で自動反映→その結果ゲームオーバー」という完全なEnd-to-Endの結合テストは無い(現状は`_on_before_spawn`/`_spawn_next`の手動直列呼び出し)。呼び出し順序自体はコードで裏付けられているため優先度は必須ではない。

**任意**

4. `add_garbage_rows`で`count == board.height`(ちょうど一致)の境界テストが無い(`height+5`のテストと同一分岐を通るため実質リスクは低い)。
5. FR-21の「1行ごとに独立抽選」の統計的検証は壁打ちログで対象外と明記済みのため見送り。

### 冗長・無効なテスト

該当なし。

### 総合判定

追加テストが必要(小規模)。必須級1件・推奨2件が指摘された。

### 対応方針

- 必須級1(`winner`のPLAYER_2単独トップアウト)に対応。
- 推奨2(PLAYER_2側フック配線の結合テスト)に対応。
- 推奨3(update()経由の自動反映→ゲームオーバーの完全E2E)は、盤面遷移の構成が複雑になり実装済みの直接テスト(必須1・必須2)で因果経路自体は既に裏付けられていること、レビュー自身も「優先度は必須ではない」としていることから、費用対効果の観点で今回は見送り。
- 任意4(`count == height`ちょうどの境界)は低コストのため追加。任意5は前回同様見送り。

### 実施した修正(ラウンド2指摘への対応)

`tests/test_battle.py` に以下を追加:
- `test_winner_is_player1_when_player2_tops_out`(必須級: `winner`のPLAYER_2単独トップアウト分岐)
- `test_real_two_line_clear_from_player2_sends_attack_through_game_hooks`(推奨2: PLAYER_2側フック配線の結合テスト)
- `test_add_garbage_rows_count_equal_to_height_fills_whole_board`(任意4: `count == height`ちょうどの境界)

`pytest`(`tests/test_battle.py`: 22件、全体: 78件)は全件合格を確認。

## ラウンド3(最終ラウンド)

### ラウンド2指摘の解消状況(評価者による検証)

必須級(`winner`のPLAYER_2単独トップアウト分岐)・推奨(PLAYER_2側フック配線の結合テスト)・任意(`count == height`ちょうどの境界)のいずれも「解消」と判定された。後退・見落としはない。

### 残っている不足観点(いずれも必須ではない)

**推奨**

1. NFR-16(第2プレイヤーのキー割り当てが第1プレイヤー・共通操作と重複しないこと)を機械的に検証するテストが無い。`ui_curses.py`の`P2_KEYMAP`はcurses実端末不要の純粋なdictであり、キー集合の重複チェックとして追加可能。目視レビューとコメントのみに依存しており、将来のキー変更でNFR-16違反を検出する手段がない。
2. (申し送り事項)ラウンド2で費用対効果の観点により見送った、「実際の`hard_drop()`→ライン消去エフェクト完了→`update()`経由の自動反映→出現位置衝突によるゲームオーバー」の完全E2Eテストは依然として無い。現行テストは準結合(反映タイミングのみ/衝突のみをそれぞれ個別に検証)にとどまる。

**任意**

3. お邪魔行反映による「何行上に押し上げられたか」を、部分的に埋まった通常のスタック内容で明示的に検証する直接的なテストは無い(全埋め行をマーカーにした間接検証のみ)。
4. FR-18独立性テストは`board`/`score`のみで、`lines_cleared`/`level`の独立性までは踏み込んでいない。
5. FR-21「1行ごとに独立抽選」の統計的検証(壁打ちログで対象外と明記済みのため見送り妥当)。

### 冗長・無効なテスト

該当なし。

### 総合判定

**このまま実装完了としてよい。** 必須級だったラウンド2の指摘は妥当に解消されており、AC-14〜AC-19・FR-17〜FR-22・NFR-14の主要経路は単体・結合の両面で検証済み。残存する推奨・任意事項は次回このモジュールに手を入れる際の申し送り事項とする。

### 対応方針(最終)

壁打ちログ・CLAUDE.mdの運用ルールにより評価者レビュー→修正ループは最大3回までと定められており、ラウンド3で「実装完了としてよい」の判定を得たためループを終了する。残存する推奨2件・任意3件(上記)は今回のスコープでは対応せず、次回このモジュール(`src/tetris_cli/battle.py`, `src/tetris_cli/ui_curses.py`のP2キーマップ周り)に手を入れる際の申し送り事項として記録する。

## まとめ

| ラウンド | 必須指摘 | 対応 | 総合判定 |
|---|---|---|---|
| 1 | 3件(ゲームオーバー経路・update()結合・add_garbage_rows境界値バグ) | 対応済み(実装修正1件+テスト7件追加) | 追加テストが必要 |
| 2 | 1件(winnerのPLAYER_2対称ケース) | 対応済み(テスト3件追加) | 追加テストが必要(小規模) |
| 3 | 0件 | - | このまま実装完了としてよい |

最終テスト結果: `tests/test_battle.py` 22件・全体78件、すべて合格。

