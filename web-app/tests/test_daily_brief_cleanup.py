from datetime import date

import pytest

import daily_brief_cleanup as cleanup
import daily_briefs


def test_watch_cleans_on_startup_and_date_change_only(tmp_path, monkeypatch):
    today = [date(2026, 10, 4)]
    calls = []
    marker = tmp_path / "healthy"
    monkeypatch.setattr(cleanup, "HEALTH_FILE", marker)
    monkeypatch.setattr(daily_briefs, "_brief_today", lambda: today[0])
    monkeypatch.setattr(
        daily_briefs, "prune_briefs", lambda root: calls.append(root) or 0
    )

    class Stop:
        waits = 0

        def is_set(self):
            return self.waits == 3

        def wait(self, seconds):
            assert seconds == 60
            self.waits += 1
            if self.waits == 2:
                today[0] = date(2026, 10, 5)

    cleanup.watch(tmp_path, Stop())
    assert calls == [tmp_path, tmp_path]
    assert marker.exists()


def test_failed_startup_clears_old_health_marker(tmp_path, monkeypatch):
    marker = tmp_path / "healthy"
    marker.touch()
    monkeypatch.setattr(cleanup, "HEALTH_FILE", marker)

    def fail(directory):
        raise OSError("failed write")

    monkeypatch.setattr(daily_briefs, "prune_briefs", fail)
    with pytest.raises(OSError, match="failed write"):
        cleanup.watch(tmp_path, cleanup.Event())
    assert not marker.exists()


def test_health_requires_recent_success(tmp_path, monkeypatch):
    marker = tmp_path / "healthy"
    monkeypatch.setattr(cleanup, "HEALTH_FILE", marker)
    assert not cleanup.healthy()
    marker.touch()
    written_at = marker.stat().st_mtime
    monkeypatch.setattr(cleanup.time, "time", lambda: written_at + 25 * 60 * 60)
    assert cleanup.healthy()
    monkeypatch.setattr(cleanup.time, "time", lambda: written_at + 26 * 60 * 60)
    assert not cleanup.healthy()
