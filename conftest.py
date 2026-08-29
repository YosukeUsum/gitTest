"""pytest実行結果をログファイルに記録する (SPEC.md NFR-6)。

pytestを実行するたびに logs/ ディレクトリへ新しい1ファイルを出力し、
成功・失敗にかかわらず各テストの結果(PASS/FAIL/ERROR/SKIP)と
最終サマリ(合計・成功・失敗・スキップ件数、終了ステータス)を記録する。

ログファイル名は `test_run_<実行日時>.log` とし、実行のたびに新規作成する
(上書きしない)ため、1回のテスト実行につき1ファイルが残る。
"""
from __future__ import annotations

import datetime
import os

_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

# モジュールグローバルで状態を保持する(pytest-xdist等の並列実行は対象外)。
_state: dict = {"log_file": None, "log_path": None, "results": []}


def pytest_configure(config) -> None:
    """テストセッション開始時に、実行ごとの新しいログファイルを作成する。"""
    os.makedirs(_LOG_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    log_path = os.path.join(_LOG_DIR, f"test_run_{timestamp}.log")
    log_file = open(log_path, "w", encoding="utf-8")
    _state["log_file"] = log_file
    _state["log_path"] = log_path
    _state["results"] = []

    log_file.write("Tetris CLI - pytest実行ログ\n")
    log_file.write(f"実行開始: {datetime.datetime.now().isoformat()}\n")
    log_file.write("-" * 60 + "\n")
    log_file.flush()


def pytest_runtest_logreport(report) -> None:
    """各テストの結果(成功・失敗・エラー・スキップ)をログに記録する。"""
    log_file = _state.get("log_file")
    if log_file is None:
        return

    if report.when == "call":
        if report.passed:
            outcome = "PASS"
        elif report.failed:
            outcome = "FAIL"
        else:
            outcome = "SKIP"
    elif report.when in ("setup", "teardown") and report.outcome != "passed":
        outcome = "ERROR" if report.failed else "SKIP"
    else:
        return

    _state["results"].append((report.nodeid, outcome, report.duration))
    log_file.write(f"{outcome:<5s} {report.nodeid} ({report.duration:.3f}s)\n")
    if outcome in ("FAIL", "ERROR") and report.longrepr:
        log_file.write(str(report.longrepr) + "\n")
    log_file.flush()


def pytest_sessionfinish(session, exitstatus) -> None:
    """テストセッション終了時に、成功・失敗にかかわらずサマリを記録してログを閉じる。"""
    log_file = _state.get("log_file")
    if log_file is None:
        return

    results = _state["results"]
    passed = sum(1 for _, outcome, _ in results if outcome == "PASS")
    failed = sum(1 for _, outcome, _ in results if outcome in ("FAIL", "ERROR"))
    skipped = sum(1 for _, outcome, _ in results if outcome == "SKIP")

    log_file.write("-" * 60 + "\n")
    log_file.write(
        f"合計: {len(results)}件  成功: {passed}  失敗: {failed}  スキップ: {skipped}\n"
    )
    status = "SUCCESS" if exitstatus == 0 else "FAILURE"
    log_file.write(f"終了ステータス: {status} (exitstatus={int(exitstatus)})\n")
    log_file.write(f"実行終了: {datetime.datetime.now().isoformat()}\n")
    log_file.close()

    print(f"\n[テストログ] {_state['log_path']}")

    _state["log_file"] = None
