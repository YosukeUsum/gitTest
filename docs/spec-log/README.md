# SPEC壁打ちログ 索引

`SPEC.md` の要件・方針を変更するに至った設計判断の壁打ち(論点・選択肢・根拠・決定)を
テーマ単位で記録する。運用ルールは `../../CLAUDE.md` と `SPEC.md` の NFR-7 を参照。

- 1テーマ = 1ファイル。命名は `YYYY-MM-DD-<topic-slug>.md`(起票日)。
- 新規ログは `TEMPLATE.md` を複製して作成する。
- 議論が後日に続く場合は同じファイルへ `## セッション: YYYY-MM-DD` を足して追記する。
- ログの起票・更新時に、この一覧へ必ず反映する。

## 一覧

| 起票日 | テーマ | 関連SPEC項目 | ステータス | ログ |
|---|---|---|---|---|
| 2026-08-29 | SPEC.md 変更時の壁打ちログを残す仕組み | NFR-7(新規), 11章, 12章 | 決定済み | [2026-08-29-spec-brainstorm-logging.md](2026-08-29-spec-brainstorm-logging.md) |
| 2026-08-29 | CLI表示を日本語化する（NFR-5の見直し） | NFR-5(改訂), 12章 | 決定済み | [2026-08-29-cli-japanese-display.md](2026-08-29-cli-japanese-display.md) |
| 2026-08-29 | ゲームループへの固定タイムステップ方式の導入(ループエンジニアリング) | NFR-8(新規), AC-10・AC-11(新規), 6章, 12章 | 決定済み | [2026-08-29-game-loop-engineering.md](2026-08-29-game-loop-engineering.md) |
| 2026-09-12 | ブロックの種類ごとの色分け表示 | FR-14(新規), NFR-9(新規), 12章 | 決定済み | [2026-09-12-block-color-coding.md](2026-09-12-block-color-coding.md) |
| 2026-09-12 | 配色・見た目のモダン化(ぷよぷよ的な今風の表現) | FR-15(新規), NFR-10(新規), AC-12(新規), 12章 | 決定済み | [2026-09-12-modern-color-scheme.md](2026-09-12-modern-color-scheme.md) |
| 2026-09-12 | ライン消去時のエフェクト追加 | FR-16(新規), NFR-11(新規), AC-13(新規), 12章 | 決定済み | [2026-09-12-line-clear-effect.md](2026-09-12-line-clear-effect.md) |
| 2026-09-12 | SPEC.md変更時にdocs/design/の説明資料も同期更新する | NFR-12(新規), 6章, 11章, 12章 | 決定済み | [2026-09-12-design-doc-sync.md](2026-09-12-design-doc-sync.md) |
