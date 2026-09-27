from pathlib import Path

from app.core.config import (
    Settings,
    get_backtests_dir,
    get_fixtures_dir,
    get_repo_root,
    get_reports_dir,
)


def test_settings_defaults():
    """Verify new settings fields have documented defaults."""
    s = Settings()
    assert s.REPO_ROOT is None
    assert s.BACKTEST_STORAGE_PATH == "data/backtests"
    assert s.MAX_BACKTEST_RUNS == 5
    assert s.MAX_BACKTEST_SWEEPS == 2
    assert s.BACKTEST_RETENTION_ENABLED is True
    assert s.YFINANCE_ENABLED is True


def test_get_repo_root_resolves():
    """Verify get_repo_root returns a valid directory containing backend."""
    root = get_repo_root()
    assert isinstance(root, Path)
    assert root.exists()
    assert (root / "backend").is_dir()


def test_get_repo_root_env_override(monkeypatch):
    """Verify REPO_ROOT environment variable overrides detection."""
    monkeypatch.setenv("REPO_ROOT", "/tmp/equitest_custom_root")
    root = get_repo_root()
    assert root == Path("/tmp/equitest_custom_root")


def test_get_fixtures_dir_resolves():
    """Verify get_fixtures_dir returns a Path under repo root by default."""
    fix_dir = get_fixtures_dir()
    assert isinstance(fix_dir, Path)
    assert fix_dir == (get_repo_root() / "data" / "fixtures").resolve()


def test_get_fixtures_dir_env_override(monkeypatch):
    """Verify FIXTURES_DIR env var overrides resolution."""
    monkeypatch.setenv("FIXTURES_DIR", "/custom/fixtures")
    assert get_fixtures_dir() == Path("/custom/fixtures")

    monkeypatch.setenv("FIXTURES_DIR", "relative/fixtures")
    assert get_fixtures_dir() == (get_repo_root() / "relative" / "fixtures").resolve()


def test_get_backtests_dir_resolves():
    """Verify get_backtests_dir returns a Path under repo root by default."""
    bt_dir = get_backtests_dir()
    assert isinstance(bt_dir, Path)
    assert bt_dir == (get_repo_root() / "data" / "backtests").resolve()


def test_get_backtests_dir_env_override(monkeypatch):
    """Verify BACKTEST_STORAGE_PATH env var overrides resolution."""
    monkeypatch.setenv("BACKTEST_STORAGE_PATH", "/custom/backtests")
    assert get_backtests_dir() == Path("/custom/backtests")

    monkeypatch.setenv("BACKTEST_STORAGE_PATH", "relative/backtests")
    assert get_backtests_dir() == (get_repo_root() / "relative" / "backtests").resolve()


def test_get_reports_dir_resolves():
    """Verify get_reports_dir returns a Path under repo root by default."""
    rep_dir = get_reports_dir()
    assert isinstance(rep_dir, Path)
    assert rep_dir == (get_repo_root() / "data" / "reports").resolve()


def test_get_reports_dir_env_override(monkeypatch):
    """Verify REPORTS_DIR env var overrides resolution."""
    monkeypatch.setenv("REPORTS_DIR", "/custom/reports")
    assert get_reports_dir() == Path("/custom/reports")

    monkeypatch.setenv("REPORTS_DIR", "relative/reports")
    assert get_reports_dir() == (get_repo_root() / "relative" / "reports").resolve()
