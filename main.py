import logging
import time
import signal
import sys
from datetime import datetime, timezone

from config import SCRAPER_INTERVAL, LOG_LEVEL, LOG_FORMAT, VERSION

from database import Database
from scraper import Scraper
from processor import Processor
from bot import TelegramBot
from ai import AIService

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("crypto_bot.log", encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)


class CryptoNewsBot:
    """Main bot orchestrator."""

    def __init__(self):
        self.running = False
        self.db = None
        self.scraper = None
        self.processor = None
        self.bot = None
        self.ai_service = None

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def initialize(self):
        """Initialize all bot components."""
        logger.info("=" * 60)
        logger.info(f"CryptositNews v{VERSION} - Initializing...")
        logger.info("=" * 60)

        try:
            # Initialize database
            try:
                self.db = Database()
                logger.info("Database: OK")
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise

            # Initialize AI service
            self.ai_service = AIService()
            if self.ai_service.is_available():
                logger.info("AI Service: OK")
            else:
                logger.warning("AI Service: Not available (no API key)")

            # Initialize scraper
            self.scraper = Scraper()
            logger.info(f"Scraper: OK ({len(self.scraper.feeds)} feeds configured)")

            # Initialize processor
            self.processor = Processor(db=self.db, ai_service=self.ai_service)
            logger.info("Processor: OK")

            # Initialize Telegram bot
            self.bot = TelegramBot()
            if self.bot.token and self.bot.channel_id:
                if self.bot.test_connection():
                    logger.info("Telegram Bot: OK")
                else:
                    logger.warning("Telegram Bot: Connection failed")
            else:
                logger.warning("Telegram Bot: Not configured (missing token/channel)")

        except Exception:
            logger.error("Initialization failed. Shutting down gracefully...")
            self.shutdown()
            raise

        logger.info("=" * 60)
        logger.info(f"CryptositNews v{VERSION} - Ready!")
        logger.info("=" * 60)

    def run_worker_loop(self):
        """Main worker loop that scrapes, processes, and posts."""
        self.running = True
        cycle = 0

        while self.running:
            cycle += 1
            logger.info(f"\n--- Cycle #{cycle} started at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC ---")

            try:
                self._run_cycle()
            except Exception as e:
                logger.error(f"Error in cycle #{cycle}: {e}", exc_info=True)

            logger.info(f"--- Cycle #{cycle} completed. Waiting {SCRAPER_INTERVAL}s ---\n")

            # Sleep in small intervals to check for shutdown signal
            for _ in range(SCRAPER_INTERVAL):
                if not self.running:
                    break
                time.sleep(1)

    def _run_cycle(self):
        """Run a single scrape-process-post cycle."""
        # Step 1: Scrape articles
        logger.info("Step 1: Scraping RSS feeds...")
        articles = self.scraper.scrape_all()

        if not articles:
            logger.info("No new articles found")
            return

        # Step 2: Process articles with AI
        logger.info(f"Step 2: Processing {len(articles)} articles with AI...")
        processed = self.processor.process_articles(articles)

        # Step 3: Save to database
        logger.info("Step 3: Saving to database...")
        saved_count = self.processor.save_articles(processed)
        logger.info(f"Saved {saved_count} new articles to database")

        # Step 4: Post to Telegram
        if self.bot.token and self.bot.channel_id:
            logger.info(f"Step 4: Posting to Telegram (channel: {self.bot.channel_id[:4]}***)...")
            unposted = self.db.get_unposted_articles(limit=5)
            if unposted:
                logger.info(f"Found {len(unposted)} unposted articles")
                posted_count = self.bot.post_articles(unposted, db=self.db)
                logger.info(f"Posted {posted_count} articles to Telegram")
            else:
                logger.info("No unposted articles to send")
        else:
            if not self.bot.token:
                logger.info("Step 4: Telegram not configured (missing TELEGRAM_BOT_TOKEN)")
            elif not self.bot.channel_id:
                logger.info("Step 4: Telegram not configured (missing TELEGRAM_CHANNEL_ID)")

    def run_once(self):
        """Run a single cycle (useful for testing)."""
        self.initialize()
        self._run_cycle()
        self.shutdown()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        self.shutdown()

    def shutdown(self):
        """Clean up resources."""
        logger.info("Shutting down CryptositNews...")
        if self.db:
            self.db.close()
        logger.info("CryptositNews stopped.")


def main():
    """Main entry point."""
    bot = CryptoNewsBot()
    try:
        bot.initialize()
        bot.run_worker_loop()
    except KeyboardInterrupt:
        bot.shutdown()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        bot.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
