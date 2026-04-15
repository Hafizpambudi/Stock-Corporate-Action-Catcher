import asyncio
import json
import logging
import os
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from agents.data_collector import DataCollectorAgent
from agents.financial_expert import FinancialExpertAgent
from config.settings import OUTPUT_DIR, SCHEDULE_HOUR, SCHEDULE_MINUTE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_agents() -> list[dict]:
    """Run both agents sequentially and return combined results."""
    logger.info("=" * 60)
    logger.info("Starting Investor Relation Automation System")
    logger.info("=" * 60)
    
    # Phase 1: Data Collection
    collector = DataCollectorAgent()
    collected_data = await collector.run()
    
    if not collected_data:
        logger.warning("No announcements found for today. Exiting.")
        return []
    
    logger.info(f"Collected {len(collected_data)} announcements")
    
    # Phase 2: Financial Analysis
    expert = FinancialExpertAgent()
    results = expert.analyze_batch(collected_data)
    
    logger.info(f"Analysis complete. Processed {len(results)} announcements")
    
    return results


def save_results(results: list[dict]):
    """Save results to JSON file."""
    if not results:
        return
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    output_file = os.path.join(OUTPUT_DIR, f"results_{today}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Results saved to {output_file}")


async def run_daily_task():
    """Execute the daily automation task."""
    try:
        results = await run_agents()
        save_results(results)
        
        if results:
            logger.info("\n" + "=" * 60)
            logger.info("DAILY SUMMARY")
            logger.info("=" * 60)
            for result in results:
                logger.info(f"\nTicker: {result['Ticker']}")
                logger.info(f"Source: {result['source']}")
                logger.info(f"Analysis: {result['analysis'][:100]}...")
            logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error in daily task execution: {e}", exc_info=True)


def run_scheduler():
    """Set up and run the scheduler for daily execution."""
    logger.info(f"Setting up scheduler to run at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} daily")
    
    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: asyncio.run(run_daily_task()),
        'cron',
        hour=SCHEDULE_HOUR,
        minute=SCHEDULE_MINUTE,
        day_of_week='mon-fri'  # Only run on trading days
    )
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Investor Relation Automation System")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Run the task immediately instead of scheduling"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run in scheduled mode (daily execution)"
    )
    
    args = parser.parse_args()
    
    if args.run_now:
        # Run immediately
        logger.info("Running task immediately...")
        asyncio.run(run_daily_task())
    elif args.schedule:
        # Run in scheduled mode
        run_scheduler()
    else:
        # Default: run immediately
        logger.info("No mode specified. Running immediately...")
        asyncio.run(run_daily_task())
