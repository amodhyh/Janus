"""Tests for the Pass 4 decision log."""
import hashlib
import sqlite3
import threading

import pytest

from pipeline.decision_log import DecisionLog


def base_fields(**overrides):
    fields = dict(action="ACTION_ALLOW", decided_by="slm", gray_area=False, judge_failed=False)
    fields.update(overrides)
    return fields


@pytest.fixture
def log(tmp_path):
    decision_log = DecisionLog(tmp_path / "decisions.db", store_prompts=False)
    yield decision_log
    decision_log.close()


def test_records_a_row_with_hash_and_length_but_no_text_by_default(log):
    log.record("my secret prompt", **base_fields(reason="Clean", total_ms=1.5))
    (row,) = log.rows()
    assert row["prompt_sha256"] == hashlib.sha256(b"my secret prompt").hexdigest()
    assert row["prompt_len"] == len("my secret prompt")
    assert row["prompt_text"] is None
    assert row["reason"] == "Clean" and row["total_ms"] == 1.5
    assert row["ts"].endswith("+00:00")


def test_prompt_text_is_stored_only_when_opted_in(tmp_path):
    opted_in = DecisionLog(tmp_path / "opt.db", store_prompts=True)
    opted_in.record("hello", **base_fields())
    assert opted_in.rows()[0]["prompt_text"] == "hello"
    opted_in.close()


def test_missing_optional_fields_are_null(log):
    log.record("x", **base_fields())
    (row,) = log.rows()
    assert row["judge_verdict"] is None and row["slm_injection_prob"] is None


def test_rows_can_be_filtered(log):
    log.record("a", **base_fields(gray_area=True, decided_by="judge"))
    log.record("b", **base_fields())
    assert len(log.rows("gray_area = 1")) == 1
    assert len(log.rows("decided_by = ?", ("slm",))) == 1


def test_log_persists_across_instances(tmp_path):
    first = DecisionLog(tmp_path / "persist.db")
    first.record("a", **base_fields())
    first.close()
    second = DecisionLog(tmp_path / "persist.db")
    assert len(second.rows()) == 1
    second.close()


def test_concurrent_writes_are_all_recorded(log):
    def write(i):
        for j in range(25):
            log.record(f"prompt-{i}-{j}", **base_fields())

    threads = [threading.Thread(target=write, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(log.rows()) == 8 * 25


def test_record_never_raises_when_the_database_is_unusable(tmp_path):
    blocked = tmp_path / "blocker"
    blocked.write_text("a file, not a directory")
    disabled = DecisionLog(blocked / "decisions.db")  # parent is a file, so opening fails
    disabled.record("x", **base_fields())  # must not raise
    assert disabled.rows() == []


def test_record_swallows_write_errors(log):
    log._conn.execute("DROP TABLE decisions")
    log.record("x", **base_fields())  # sqlite3.Error is logged, not raised
    with pytest.raises(sqlite3.Error):
        log.rows()
