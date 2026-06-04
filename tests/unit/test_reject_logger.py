from etl.hr.reject_logger import RejectLogger


def test_reject_logger_buffers_and_flushes(pg_db, run_id):
    reject = RejectLogger(pg_db, run_id)
    reject.log_reject({"source_id": "001"}, "full_name", "???", "Missing required")
    assert len(reject.buffer) == 1
    reject.flush()
    result = pg_db.execute(
        "SELECT COUNT(*) FROM staging.hr_rejects WHERE run_id = :run_id",
        {"run_id": run_id},
    )
    assert result.fetchone()[0] == 1


def test_reject_logger_auto_flush_on_batch(pg_db, run_id):
    reject = RejectLogger(pg_db, run_id)
    reject.batch_size = 2
    reject.log_reject({"id": 1}, "col1", "x", "reason1")
    assert len(reject.buffer) == 1
    reject.log_reject({"id": 2}, "col2", "y", "reason2")
    assert len(reject.buffer) == 0
    result = pg_db.execute(
        "SELECT COUNT(*) FROM staging.hr_rejects WHERE run_id = :run_id",
        {"run_id": run_id},
    )
    assert result.fetchone()[0] == 2


def test_reject_logger_buffer_clear_on_flush(pg_db, run_id):
    reject = RejectLogger(pg_db, run_id)
    reject.log_reject({"id": 1}, "c", "v", "r")
    reject.flush()
    assert len(reject.buffer) == 0
    reject.flush()
