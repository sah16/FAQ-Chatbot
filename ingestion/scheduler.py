"""Daily Ingestion Scheduler Runner.
Executes scheduled freshness checks across the 5 approved Groww scheme URLs,
performs incremental SHA-256 change detection, updates vector store records,
and outputs execution logs for CI/CD and monitoring.
"""

import sys
import logging
from datetime import datetime
from typing import Optional

from ingestion.freshness import FreshnessEngine, FreshnessJobResult

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ingestion.scheduler")


def run_scheduled_ingestion(engine: Optional[FreshnessEngine] = None) -> FreshnessJobResult:
    """
    Triggers scheduled ingestion across the 5 fixed Groww scheme URLs:
    - Verifies content changes via section SHA-256 hashes.
    - Re-embeds modified sections only.
    - Bumps last_verified_unchanged_at for unchanged sections.
    - Preserves existing chunk data on network fetch failures.
    """
    logger.info("=" * 60)
    logger.info("Starting scheduled ingestion job (Daily at 9:30 AM IST)...")
    logger.info("=" * 60)

    if engine is None:
        engine = FreshnessEngine()

    result = engine.run_freshness_job()

    logger.info("=" * 60)
    logger.info("Scheduled Ingestion Job Completed Summary:")
    logger.info(f"  • Timestamp:        {result.run_at}")
    logger.info(f"  • Sources Checked:  {result.sources_checked}/{result.total_sources}")
    logger.info(f"  • Sources Failed:   {result.sources_failed}")
    logger.info(f"  • Total Chunks:     {result.total_chunks}")
    logger.info(f"  • Unchanged Chunks: {result.unchanged_chunks}")
    logger.info(f"  • Updated Chunks:   {result.updated_chunks}")
    logger.info(f"  • Duration:         {result.duration_seconds}s")

    if result.failed_sources:
        logger.warning(f"  • Failed Sources:   {', '.join(result.failed_sources)}")
    if result.errors:
        for err in result.errors:
            logger.error(f"  • Error detail:     {err}")
    logger.info("=" * 60)

    return result


if __name__ == "__main__":
    job_result = run_scheduled_ingestion()
    # Exit with code 0 even if some sources fail gracefully, or code 1 if catastrophic failure
    if job_result.sources_checked == 0 and job_result.total_sources > 0:
        logger.error("Catastrophic failure: Zero sources were checked successfully.")
        sys.exit(1)
    sys.exit(0)
