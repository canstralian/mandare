"""Comprehensive tests for the SQLite WAL storage backend."""

from __future__ import annotations

import json
import threading
from pathlib import Path

from rif_runtime.storage.jsonl import JsonlStore, StorageWriter


class TestAppendAndIterRecords:
    """Append + iter_records roundtrip tests."""

    def test_roundtrip_single(self, tmp_path: Path) -> None:
        """A single appended record is retrieved correctly."""
        store = StorageWriter(tmp_path / "test.jsonl")
        store.append({"name": "alice", "age": 30})
        result = list(store.iter_records())
        assert result == [{"name": "alice", "age": 30}]
        store.close()

    def test_roundtrip_multiple(self, tmp_path: Path) -> None:
        """Multiple appended records are retrieved in order."""
        store = StorageWriter(tmp_path / "test.jsonl")
        records = [
            {"name": "alice", "age": 30},
            {"name": "bob", "age": 25},
            {"name": "charlie", "age": 35},
        ]
        for r in records:
            store.append(r)
        result = list(store.iter_records())
        assert result == records
        store.close()

    def test_empty_store(self, tmp_path: Path) -> None:
        """An empty store yields no records."""
        store = StorageWriter(tmp_path / "empty.jsonl")
        assert list(store.iter_records()) == []
        store.close()


class TestConcurrentWrites:
    """Multi-threaded write safety tests."""

    def test_no_data_loss(self, tmp_path: Path) -> None:
        """Multiple threads writing concurrently produce no data loss."""
        store = StorageWriter(tmp_path / "concurrent.jsonl")
        num_threads = 10
        records_per_thread = 50
        errors: list[Exception] = []

        def writer(thread_id: int) -> None:
            try:
                for i in range(records_per_thread):
                    store.append({"thread": thread_id, "seq": i})
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert store.count() == num_threads * records_per_thread
        store.close()

    def test_concurrent_integrity(self, tmp_path: Path) -> None:
        """All records written concurrently are valid JSON dicts."""
        store = StorageWriter(tmp_path / "integrity.jsonl")
        num_threads = 5
        records_per_thread = 20

        def writer(thread_id: int) -> None:
            for i in range(records_per_thread):
                store.append({"t": thread_id, "i": i})

        threads = [
            threading.Thread(target=writer, args=(t,)) for t in range(num_threads)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        all_records = list(store.iter_records())
        assert len(all_records) == num_threads * records_per_thread
        for rec in all_records:
            assert "t" in rec
            assert "i" in rec
        store.close()


class TestTail:
    """tail() correctness tests."""

    def test_tail_returns_last_n(self, tmp_path: Path) -> None:
        """tail(n) returns the last n records in insertion order."""
        store = StorageWriter(tmp_path / "tail.jsonl")
        for i in range(20):
            store.append({"index": i})

        last_5 = store.tail(5)
        assert last_5 == [{"index": i} for i in range(15, 20)]
        store.close()

    def test_tail_more_than_available(self, tmp_path: Path) -> None:
        """tail(n) with n > count returns all records."""
        store = StorageWriter(tmp_path / "tail2.jsonl")
        for i in range(3):
            store.append({"index": i})

        result = store.tail(10)
        assert result == [{"index": 0}, {"index": 1}, {"index": 2}]
        store.close()

    def test_tail_empty_store(self, tmp_path: Path) -> None:
        """tail(n) on empty store returns empty list."""
        store = StorageWriter(tmp_path / "empty_tail.jsonl")
        assert store.tail(5) == []
        store.close()


class TestCount:
    """count() accuracy tests."""

    def test_count_empty(self, tmp_path: Path) -> None:
        """Empty store has count 0."""
        store = StorageWriter(tmp_path / "count.jsonl")
        assert store.count() == 0
        store.close()

    def test_count_after_inserts(self, tmp_path: Path) -> None:
        """count() reflects the number of appended records."""
        store = StorageWriter(tmp_path / "count.jsonl")
        for i in range(7):
            store.append({"i": i})
        assert store.count() == 7
        store.close()

    def test_count_increments(self, tmp_path: Path) -> None:
        """count() increments after each append."""
        store = StorageWriter(tmp_path / "incr.jsonl")
        for expected in range(1, 6):
            store.append({"n": expected})
            assert store.count() == expected
        store.close()


class TestWALMode:
    """Verify WAL journal mode is active."""

    def test_wal_pragma_set(self, tmp_path: Path) -> None:
        """PRAGMA journal_mode returns 'wal'."""
        store = StorageWriter(tmp_path / "wal.jsonl")
        conn = store._ensure_conn()
        cursor = conn.execute("PRAGMA journal_mode")
        row = cursor.fetchone()
        assert row is not None
        mode: str = row[0]
        assert mode.lower() == "wal"
        store.close()

    def test_synchronous_normal(self, tmp_path: Path) -> None:
        """PRAGMA synchronous is set to NORMAL (1)."""
        store = StorageWriter(tmp_path / "sync.jsonl")
        conn = store._ensure_conn()
        cursor = conn.execute("PRAGMA synchronous")
        row = cursor.fetchone()
        assert row is not None
        # NORMAL = 1
        assert row[0] == 1
        store.close()


class TestContextManager:
    """Context manager lifecycle tests."""

    def test_enter_exit(self, tmp_path: Path) -> None:
        """Context manager opens and closes the connection properly."""
        path = tmp_path / "ctx.jsonl"
        with StorageWriter(path) as store:
            store.append({"key": "value"})
            assert store.count() == 1

        # After exit, connection should be closed
        assert store._conn is None

    def test_usable_within_context(self, tmp_path: Path) -> None:
        """All operations work within a context manager block."""
        path = tmp_path / "ctx2.jsonl"
        with StorageWriter(path) as store:
            store.append({"a": 1})
            store.append({"b": 2})
            assert store.count() == 2
            assert store.tail(1) == [{"b": 2}]
            assert list(store.iter_records()) == [{"a": 1}, {"b": 2}]


class TestPersistence:
    """Data survives re-open tests."""

    def test_data_survives_reopen(self, tmp_path: Path) -> None:
        """Data persists across close and re-open."""
        path = tmp_path / "persist.jsonl"
        with StorageWriter(path) as store:
            store.append({"persisted": True})
            store.append({"persisted": True, "seq": 2})

        with StorageWriter(path) as store2:
            assert store2.count() == 2
            records = list(store2.iter_records())
            assert records[0] == {"persisted": True}
            assert records[1] == {"persisted": True, "seq": 2}

    def test_tail_after_reopen(self, tmp_path: Path) -> None:
        """tail() works correctly after re-opening the store."""
        path = tmp_path / "reopen_tail.jsonl"
        with StorageWriter(path) as store:
            for i in range(10):
                store.append({"i": i})

        with StorageWriter(path) as store2:
            assert store2.tail(3) == [{"i": 7}, {"i": 8}, {"i": 9}]


class TestExportJsonl:
    """JSONL export backwards compatibility tests."""

    def test_export_format(self, tmp_path: Path) -> None:
        """export_jsonl produces valid JSONL output."""
        store = StorageWriter(tmp_path / "export.jsonl")
        store.append({"a": 1})
        store.append({"b": 2})

        output = store.export_jsonl()
        lines = output.strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0]) == {"a": 1}
        assert json.loads(lines[1]) == {"b": 2}
        store.close()

    def test_export_empty(self, tmp_path: Path) -> None:
        """export_jsonl on empty store returns empty string."""
        store = StorageWriter(tmp_path / "empty_export.jsonl")
        assert store.export_jsonl() == ""
        store.close()


class TestBackwardsCompat:
    """Backwards compatibility tests."""

    def test_read_all(self, tmp_path: Path) -> None:
        """read_all() still works as before."""
        store = StorageWriter(tmp_path / "compat.jsonl")
        store.append({"x": 1})
        store.append({"y": 2})
        assert store.read_all() == [{"x": 1}, {"y": 2}]
        store.close()

    def test_count_by(self, tmp_path: Path) -> None:
        """count_by() still works as before."""
        store = StorageWriter(tmp_path / "countby.jsonl")
        store.append({"status": "ok"})
        store.append({"status": "ok"})
        store.append({"status": "error"})
        assert store.count_by("status") == {"ok": 2, "error": 1}
        store.close()

    def test_jsonl_store_alias(self, tmp_path: Path) -> None:
        """JsonlStore alias resolves to StorageWriter."""
        assert JsonlStore is StorageWriter

    def test_jsonl_store_alias_functional(self, tmp_path: Path) -> None:
        """JsonlStore alias works identically."""
        store = JsonlStore(tmp_path / "alias.jsonl")
        store.append({"alias": True})
        assert store.count() == 1
        store.close()

    def test_path_property(self, tmp_path: Path) -> None:
        """path property returns the original public path."""
        original = tmp_path / "myfile.jsonl"
        store = StorageWriter(original)
        assert store.path == original
        store.close()
