"""Automated verification test suite for Daily Ingestion Scheduler and GitHub Actions Workflow."""

from pathlib import Path
from ingestion.scheduler import run_scheduled_ingestion
from ingestion.freshness import FreshnessEngine


def test_scheduler_execution():
    """Verify that run_scheduled_ingestion executes and returns valid job metrics."""
    engine = FreshnessEngine()
    result = run_scheduled_ingestion(engine=engine)

    assert result.total_sources == 5
    assert result.sources_checked == 5
    assert result.sources_failed == 0
    assert result.unchanged_chunks > 0 or result.updated_chunks > 0
    assert result.duration_seconds >= 0.0


def test_github_actions_workflow_cron():
    """Verify that the GitHub Actions workflow file exists and is configured for 9:30 AM IST (04:00 UTC)."""
    workflow_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "daily_ingestion.yml"
    assert workflow_path.exists(), f"Workflow file not found at {workflow_path}"

    content = workflow_path.read_text(encoding="utf-8")
    assert "cron: '0 4 * * *'" in content or 'cron: "0 4 * * *"' in content, "Cron must be set to 0 4 * * * (04:00 UTC = 09:30 AM IST)"
    assert "workflow_dispatch" in content, "Manual trigger must be enabled"
    assert "python -m ingestion.scheduler" in content, "Workflow must execute ingestion scheduler"
