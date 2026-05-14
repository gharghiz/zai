import os
import logging
import sqlite3
import hashlib
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from config import DATABASE_URL, DB_TYPE

logger = logging.getLogger(__name__)


def _import_psycopg2():
    """Lazy import psycopg2 only when PostgreSQL is needed."""
    try:
        import psycopg2
        return psycopg2
    except ImportError:
        logger.error("psycopg2 is not installed or libpq is missing. "
                     "Install with: pip install psycopg2-binary")
        return None


class Database:
    """Database handler with SQLite and PostgreSQL support."""

    def __init__(self):
        self.conn = None
        self.db_type = DB_TYPE
        self._lock = threading.Lock()
        self._connect()
        self._init_tables()

    def _connect(self):
        """Establish database connection."""
        try:
            if self.db_type == "postgresql":
                psycopg2 = _import_psycopg2()
                if not psycopg2:
                    logger.warning("PostgreSQL requested but psycopg2 unavailable. Falling back to SQLite.")
                    self.db_type = "sqlite"
                    db_path = "crypto_news.db"
                    self.conn = sqlite3.connect(db_path, check_same_thread=False)
                    self.conn.row_factory = sqlite3.Row
                    logger.info(f"Fallback to SQLite database: {db_path}")
                    return
                self.conn = psycopg2.connect(DATABASE_URL)
                self.conn.autocommit = True
                logger.info("Connected to PostgreSQL database")
            else:
                db_path = DATABASE_URL.replace("sqlite:///", "")
                self.conn = sqlite3.connect(db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database: {db_path}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def ensure_connection(self):
        """Check if the database connection is alive and reconnect if needed.
        Useful for long-running processes where connections may drop."""
        try:
            if self.db_type == "postgresql":
                psycopg2 = _import_psycopg2()
                if psycopg2 and hasattr(self.conn, 'closed') and self.conn.closed:
                    logger.warning("PostgreSQL connection closed, reconnecting...")
                    self._connect()
            else:
                # SQLite: try a lightweight query to verify the connection
                self.conn.execute("SELECT 1")
        except Exception as e:
            logger.warning(f"Database connection lost ({e}), reconnecting...")
            try:
                self._connect()
            except Exception as reconnect_err:
                logger.error(f"Failed to reconnect: {reconnect_err}")
                raise

    def __enter__(self):
        """Context manager entry."""
        self.ensure_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit. Connection stays open for reuse."""
        pass

    def _execute(self, query, params=None, fetch=False, fetchone=False):
        """Thread-safe execute with optional fetch.

        Args:
            query: SQL query string.
            params: Query parameters (tuple/list/dict).
            fetch: If True, return all rows as list of dicts.
            fetchone: If True, return first row as dict, or None.

        Returns:
            lastrowid (default), list of dicts (fetch=True), or dict/None (fetchone=True).
        """
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            try:
                cursor.execute(query, params or ())
                if self.db_type != "postgresql":
                    self.conn.commit()
                if fetchone:
                    row = cursor.fetchone()
                    return dict(row) if row else None
                if fetch:
                    return [dict(row) for row in cursor.fetchall()]
                return cursor.lastrowid
            except Exception as e:
                if self.db_type != "postgresql":
                    self.conn.rollback()
                raise

    def _init_tables(self):
        """Initialize database tables."""
        cursor = self.conn.cursor()

        if self.db_type == "postgresql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    content TEXT,
                    summary TEXT,
                    source TEXT,
                    category TEXT DEFAULT 'news',
                    image_url TEXT,
                    published_at TIMESTAMP,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment_score FLOAT DEFAULT 0.0,
                    sentiment_label TEXT DEFAULT 'neutral',
                    keywords TEXT DEFAULT '[]',
                    is_posted BOOLEAN DEFAULT FALSE,
                    posted_at TIMESTAMP,
                    telegram_message_id INTEGER,
                    ai_insights TEXT,
                    views INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en'
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
                CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
                CREATE INDEX IF NOT EXISTS idx_articles_posted ON articles(is_posted);
                CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment_score DESC);
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price FLOAT,
                    change_24h FLOAT,
                    change_7d FLOAT,
                    market_cap FLOAT,
                    volume_24h FLOAT,
                    rank INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fear_greed_index (
                    id SERIAL PRIMARY KEY,
                    value INTEGER,
                    classification TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bot_stats (
                    id SERIAL PRIMARY KEY,
                    total_articles_scraped INTEGER DEFAULT 0,
                    total_articles_posted INTEGER DEFAULT 0,
                    total_ai_summaries INTEGER DEFAULT 0,
                    last_scrape_at TIMESTAMP,
                    last_post_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Whale transactions table (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whale_transactions (
                    id SERIAL PRIMARY KEY,
                    tx_hash TEXT UNIQUE,
                    blockchain TEXT,
                    symbol TEXT NOT NULL,
                    from_owner TEXT,
                    from_owner_type TEXT,
                    to_owner TEXT,
                    to_owner_type TEXT,
                    amount FLOAT,
                    amount_usd FLOAT,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_whale_tx_hash ON whale_transactions(tx_hash);
                CREATE INDEX IF NOT EXISTS idx_whale_tx_timestamp ON whale_transactions(timestamp DESC);
            """)
            # Article ratings table (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_ratings (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER REFERENCES articles(id) ON DELETE CASCADE,
                    session_id VARCHAR(64),
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, article_id)
                );
                CREATE INDEX IF NOT EXISTS idx_article_ratings_article ON article_ratings(article_id);
            """)
            # Comment reports table (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comment_reports (
                    id SERIAL PRIMARY KEY,
                    comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
                    session_id VARCHAR(64),
                    reason VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_comment_reports_comment ON comment_reports(comment_id);
                CREATE INDEX IF NOT EXISTS idx_comment_reports_created ON comment_reports(created_at DESC);
            """)
            # Academy lessons table (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS academy_lessons (
                    id SERIAL PRIMARY KEY,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT,
                    category VARCHAR(50) DEFAULT 'bitcoin',
                    difficulty VARCHAR(20) DEFAULT 'beginner',
                    read_time INTEGER DEFAULT 5,
                    topics TEXT DEFAULT '[]',
                    order_index INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_academy_lessons_slug ON academy_lessons(slug);
                CREATE INDEX IF NOT EXISTS idx_academy_lessons_category ON academy_lessons(category);
            """)
            # Quiz questions table (PostgreSQL)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id SERIAL PRIMARY KEY,
                    lesson_id INTEGER REFERENCES academy_lessons(id) ON DELETE CASCADE,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer INTEGER DEFAULT 0,
                    explanation TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_quiz_questions_lesson ON quiz_questions(lesson_id);
            """)
        else:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    content TEXT,
                    summary TEXT,
                    source TEXT,
                    category TEXT DEFAULT 'news',
                    image_url TEXT,
                    published_at TIMESTAMP,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sentiment_score REAL DEFAULT 0.0,
                    sentiment_label TEXT DEFAULT 'neutral',
                    keywords TEXT DEFAULT '[]',
                    is_posted INTEGER DEFAULT 0,
                    posted_at TIMESTAMP,
                    telegram_message_id INTEGER,
                    ai_insights TEXT,
                    views INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en'
                );

                CREATE INDEX IF NOT EXISTS idx_articles_url ON articles(url);
                CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_at DESC);
                CREATE INDEX IF NOT EXISTS idx_articles_source ON articles(source);
                CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
                CREATE INDEX IF NOT EXISTS idx_articles_posted ON articles(is_posted);
                CREATE INDEX IF NOT EXISTS idx_articles_sentiment ON articles(sentiment_score DESC);

                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    name TEXT NOT NULL,
                    price REAL,
                    change_24h REAL,
                    change_7d REAL,
                    market_cap REAL,
                    volume_24h REAL,
                    rank INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol)
                );

                CREATE TABLE IF NOT EXISTS fear_greed_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    value INTEGER,
                    classification TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS bot_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_articles_scraped INTEGER DEFAULT 0,
                    total_articles_posted INTEGER DEFAULT 0,
                    total_ai_summaries INTEGER DEFAULT 0,
                    last_scrape_at TIMESTAMP,
                    last_post_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS whale_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tx_hash TEXT UNIQUE,
                    blockchain TEXT,
                    symbol TEXT NOT NULL,
                    from_owner TEXT,
                    from_owner_type TEXT,
                    to_owner TEXT,
                    to_owner_type TEXT,
                    amount REAL,
                    amount_usd REAL,
                    timestamp TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_whale_tx_hash ON whale_transactions(tx_hash);
                CREATE INDEX IF NOT EXISTS idx_whale_tx_timestamp ON whale_transactions(timestamp DESC);

                CREATE TABLE IF NOT EXISTS article_ratings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    session_id VARCHAR(64),
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, article_id),
                    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_article_ratings_article ON article_ratings(article_id);

                CREATE TABLE IF NOT EXISTS comment_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment_id INTEGER NOT NULL,
                    session_id VARCHAR(64),
                    reason VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_comment_reports_comment ON comment_reports(comment_id);
                CREATE INDEX IF NOT EXISTS idx_comment_reports_created ON comment_reports(created_at DESC);

                CREATE TABLE IF NOT EXISTS academy_lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT,
                    category VARCHAR(50) DEFAULT 'bitcoin',
                    difficulty VARCHAR(20) DEFAULT 'beginner',
                    read_time INTEGER DEFAULT 5,
                    topics TEXT DEFAULT '[]',
                    order_index INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_academy_lessons_slug ON academy_lessons(slug);
                CREATE INDEX IF NOT EXISTS idx_academy_lessons_category ON academy_lessons(category);

                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer INTEGER DEFAULT 0,
                    explanation TEXT,
                    FOREIGN KEY (lesson_id) REFERENCES academy_lessons(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_quiz_questions_lesson ON quiz_questions(lesson_id);
            """)

        # Initialize comments table
        self._init_comments_table()

        # Initialize bookmarks table (separate for clarity)
        self._init_bookmarks_table()

        if self.db_type != "postgresql":
            self.conn.commit()
        logger.info("Database tables initialized successfully")

    # ---- Article Methods ----

    def article_exists(self, url: str) -> bool:
        """Check if an article already exists in the database."""
        query = ("SELECT 1 FROM articles WHERE url = %s LIMIT 1" if self.db_type == "postgresql"
                 else "SELECT 1 FROM articles WHERE url = ? LIMIT 1")
        result = self._execute(query, (url,), fetchone=True)
        return result is not None

    def insert_article(self, article: Dict[str, Any]) -> Optional[int]:
        """Insert a new article into the database."""
        try:
            with self._lock:
                self.ensure_connection()
                cursor = self.conn.cursor()
                if self.db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO articles (title, url, content, summary, source, category, image_url, published_at, language)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING
                        RETURNING id
                    """, (
                        article.get("title"),
                        article.get("url"),
                        article.get("content"),
                        article.get("summary"),
                        article.get("source"),
                        article.get("category", "news"),
                        article.get("image_url"),
                        article.get("published_at"),
                        article.get("language", "en"),
                    ))
                    result = cursor.fetchone()
                    return result[0] if result else None
                else:
                    cursor.execute("""
                        INSERT OR IGNORE INTO articles (title, url, content, summary, source, category, image_url, published_at, language)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article.get("title"),
                        article.get("url"),
                        article.get("content"),
                        article.get("summary"),
                        article.get("source"),
                        article.get("category", "news"),
                        article.get("image_url"),
                        article.get("published_at"),
                        article.get("language", "en"),
                    ))
                    self.conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting article: {e}")
            if self.db_type != "postgresql":
                self.conn.rollback()
            return None

    def update_article_ai(self, article_id: int, summary: str, sentiment_score: float,
                          sentiment_label: str, keywords: List[str], ai_insights: str = None):
        """Update article with AI-generated data."""
        try:
            query = ("""
                UPDATE articles SET summary = %s, sentiment_score = %s, sentiment_label = %s,
                    keywords = %s, ai_insights = %s WHERE id = %s
            """ if self.db_type == "postgresql" else """
                UPDATE articles SET summary = ?, sentiment_score = ?, sentiment_label = ?,
                    keywords = ?, ai_insights = ? WHERE id = ?
            """)
            self._execute(query, (summary, sentiment_score, sentiment_label, str(keywords), ai_insights, article_id))
        except Exception as e:
            logger.error(f"Error updating article AI data: {e}")

    def mark_article_posted(self, article_id: int, telegram_message_id: int):
        """Mark an article as posted to Telegram."""
        try:
            query = ("""
                UPDATE articles SET is_posted = TRUE, posted_at = CURRENT_TIMESTAMP,
                    telegram_message_id = %s WHERE id = %s
            """ if self.db_type == "postgresql" else """
                UPDATE articles SET is_posted = 1, posted_at = CURRENT_TIMESTAMP,
                    telegram_message_id = ? WHERE id = ?
            """)
            self._execute(query, (telegram_message_id, article_id))
        except Exception as e:
            logger.error(f"Error marking article as posted: {e}")

    def get_unposted_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get articles that haven't been posted to Telegram yet."""
        query = ("""
            SELECT * FROM articles WHERE is_posted = FALSE AND summary IS NOT NULL
            ORDER BY published_at DESC LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT * FROM articles WHERE is_posted = 0 AND summary IS NOT NULL
            ORDER BY published_at DESC LIMIT ?
        """)
        return self._execute(query, (limit,), fetch=True)

    def get_telegram_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get articles that were posted to Telegram."""
        query = ("""
            SELECT * FROM articles WHERE is_posted = TRUE
            ORDER BY posted_at DESC LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT * FROM articles WHERE is_posted = 1
            ORDER BY posted_at DESC LIMIT ?
        """)
        return self._execute(query, (limit,), fetch=True)

    def get_latest_articles(self, limit: int = 50, category: str = None, source: str = None) -> List[Dict[str, Any]]:
        """Get the latest articles with optional filters."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            query = "SELECT * FROM articles"
            conditions = []
            params = []

            if category:
                conditions.append("category = %s" if self.db_type == "postgresql" else "category = ?")
                params.append(category)
            if source:
                conditions.append("source = %s" if self.db_type == "postgresql" else "source = ?")
                params.append(source)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY published_at DESC LIMIT %s" if self.db_type == "postgresql" else " ORDER BY published_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            if self.db_type != "postgresql":
                self.conn.commit()
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_article_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Get a single article by ID."""
        query = "SELECT * FROM articles WHERE id = %s" if self.db_type == "postgresql" else "SELECT * FROM articles WHERE id = ?"
        return self._execute(query, (article_id,), fetchone=True)

    def increment_views(self, article_id: int):
        """Increment article view count."""
        query = ("UPDATE articles SET views = views + 1 WHERE id = %s" if self.db_type == "postgresql"
                 else "UPDATE articles SET views = views + 1 WHERE id = ?")
        self._execute(query, (article_id,))

    def get_popular_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular articles sorted by views."""
        query = ("""
            SELECT * FROM articles WHERE views > 0
            ORDER BY views DESC LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT * FROM articles WHERE views > 0
            ORDER BY views DESC LIMIT ?
        """)
        return self._execute(query, (limit,), fetch=True)

    def get_sources(self) -> List[str]:
        """Get all unique article sources."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT source FROM articles ORDER BY source")
            return [row[0] for row in cursor.fetchall()]

    def get_categories(self) -> List[str]:
        """Get all unique article categories."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM articles ORDER BY category")
            return [row[0] for row in cursor.fetchall()]

    def get_article_count(self) -> int:
        """Get total article count."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM articles")
            return cursor.fetchone()[0]

    def get_trending_keywords(self, days: int = 7, limit: int = 20) -> List[tuple]:
        """Get trending keywords from recent articles."""
        from collections import Counter
        import json as _json
        since = datetime.now(timezone.utc) - timedelta(days=days)
        query = ("""
            SELECT keywords FROM articles
            WHERE published_at > %s AND keywords IS NOT NULL AND keywords != '[]'
        """ if self.db_type == "postgresql" else """
            SELECT keywords FROM articles
            WHERE published_at > ? AND keywords IS NOT NULL AND keywords != '[]'
        """)
        rows = self._execute(query, (since,), fetch=True)
        counter = Counter()
        for row_dict in rows:
            kw_text = row_dict["keywords"]
            if isinstance(kw_text, str):
                try:
                    kws = _json.loads(kw_text)
                    if isinstance(kws, list):
                        for kw in kws:
                            kw_lower = str(kw).lower().strip()
                            if kw_lower:
                                counter[kw_lower] += 1
                except (_json.JSONDecodeError, TypeError):
                    pass
        return counter.most_common(limit)

    # Market Data Methods
    def upsert_market_data(self, data: List[Dict[str, Any]]):
        """Insert or update market data."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            for item in data:
                try:
                    if self.db_type == "postgresql":
                        cursor.execute("""
                            INSERT INTO market_data (symbol, name, price, change_24h, change_7d, market_cap, volume_24h, rank, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (symbol) DO UPDATE SET
                                price = EXCLUDED.price, change_24h = EXCLUDED.change_24h,
                                change_7d = EXCLUDED.change_7d, market_cap = EXCLUDED.market_cap,
                                volume_24h = EXCLUDED.volume_24h, rank = EXCLUDED.rank,
                                updated_at = CURRENT_TIMESTAMP
                        """, (item["symbol"], item["name"], item["price"], item.get("change_24h"),
                              item.get("change_7d"), item.get("market_cap"), item.get("volume_24h"), item.get("rank")))
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO market_data (symbol, name, price, change_24h, change_7d, market_cap, volume_24h, rank, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (item["symbol"], item["name"], item["price"], item.get("change_24h"),
                              item.get("change_7d"), item.get("market_cap"), item.get("volume_24h"), item.get("rank")))
                except Exception as e:
                    logger.error(f"Error upserting market data for {item.get('symbol')}: {e}")
            if self.db_type != "postgresql":
                self.conn.commit()

    def get_market_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get latest market data."""
        query = "SELECT * FROM market_data ORDER BY rank ASC LIMIT %s" if self.db_type == "postgresql" else "SELECT * FROM market_data ORDER BY rank ASC LIMIT ?"
        return self._execute(query, (limit,), fetch=True)

    # Fear & Greed Index
    def save_fear_greed(self, value: int, classification: str):
        """Save fear and greed index value."""
        query = ("INSERT INTO fear_greed_index (value, classification) VALUES (%s, %s)" if self.db_type == "postgresql"
                 else "INSERT INTO fear_greed_index (value, classification) VALUES (?, ?)")
        self._execute(query, (value, classification))

    def get_latest_fear_greed(self) -> Optional[Dict[str, Any]]:
        """Get latest fear and greed index value."""
        return self._execute("SELECT * FROM fear_greed_index ORDER BY timestamp DESC LIMIT 1", fetchone=True)

    # Bot Stats
    def update_bot_stats(self, scraped: int = 0, posted: int = 0, ai_summaries: int = 0):
        """Update bot statistics."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            if self.db_type == "postgresql":
                cursor.execute("""
                    INSERT INTO bot_stats (total_articles_scraped, total_articles_posted, total_ai_summaries,
                        last_scrape_at, last_post_at, updated_at)
                    VALUES (
                        (SELECT COALESCE(total_articles_scraped, 0) + %s FROM bot_stats WHERE id = 1),
                        (SELECT COALESCE(total_articles_posted, 0) + %s FROM bot_stats WHERE id = 1),
                        (SELECT COALESCE(total_ai_summaries, 0) + %s FROM bot_stats WHERE id = 1),
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    ON CONFLICT DO NOTHING
                """, (scraped, posted, ai_summaries))
            else:
                cursor.execute("SELECT COUNT(*) FROM bot_stats")
                count = cursor.fetchone()[0]
                if count > 0:
                    cursor.execute("""
                        UPDATE bot_stats SET
                            total_articles_scraped = total_articles_scraped + ?,
                            total_articles_posted = total_articles_posted + ?,
                            total_ai_summaries = total_ai_summaries + ?,
                            last_scrape_at = CASE WHEN ? > 0 THEN CURRENT_TIMESTAMP ELSE last_scrape_at END,
                            last_post_at = CASE WHEN ? > 0 THEN CURRENT_TIMESTAMP ELSE last_post_at END,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = 1
                    """, (scraped, posted, ai_summaries, scraped, posted))
                else:
                    cursor.execute("""
                        INSERT INTO bot_stats (total_articles_scraped, total_articles_posted, total_ai_summaries,
                            last_scrape_at, last_post_at)
                        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (scraped, posted, ai_summaries))
                self.conn.commit()

    def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        row = self._execute("SELECT * FROM bot_stats ORDER BY id DESC LIMIT 1", fetchone=True)
        if row:
            return row
        return {
            "total_articles_scraped": 0,
            "total_articles_posted": 0,
            "total_ai_summaries": 0,
        }

    def get_stats_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive stats for the dashboard."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            stats = {}

            cursor.execute("SELECT COUNT(*) FROM articles")
            stats["total_articles"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM articles WHERE is_posted = 1" if self.db_type == "sqlite" else "SELECT COUNT(*) FROM articles WHERE is_posted = TRUE")
            stats["posted_articles"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM articles WHERE summary IS NOT NULL")
            stats["ai_processed"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT source) FROM articles")
            stats["total_sources"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT category) FROM articles")
            stats["total_categories"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM market_data")
            stats["tracked_coins"] = cursor.fetchone()[0]

        stats["bot_stats"] = self.get_bot_stats()
        stats["fear_greed"] = self.get_latest_fear_greed()

        return stats

    def search_articles(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search articles by title, content, or keywords."""
        search_term = f"%{query}%"
        sql = ("""
            SELECT * FROM articles
            WHERE title ILIKE %s OR content ILIKE %s OR summary ILIKE %s OR keywords ILIKE %s
            ORDER BY published_at DESC LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT * FROM articles
            WHERE title LIKE ? OR content LIKE ? OR summary LIKE ? OR keywords LIKE ?
            ORDER BY published_at DESC LIMIT ?
        """)
        return self._execute(sql, (search_term, search_term, search_term, search_term, limit), fetch=True)

    # ---- Archive Methods ----

    def get_archive_months(self) -> List[tuple]:
        """Get all months that have articles, with count."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            if self.db_type == "postgresql":
                cursor.execute("""
                    SELECT TO_CHAR(published_at, 'YYYY-MM') as month,
                           COUNT(*) as count
                    FROM articles
                    WHERE published_at IS NOT NULL
                    GROUP BY month
                    ORDER BY month DESC
                """)
            else:
                cursor.execute("""
                    SELECT strftime('%Y-%m', published_at) as month,
                           COUNT(*) as count
                    FROM articles
                    WHERE published_at IS NOT NULL
                    GROUP BY month
                    ORDER BY month DESC
                """)
            return cursor.fetchall()

    def get_articles_by_month(self, year: int, month: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get articles for a specific month."""
        prefix = f"{year:04d}-{month:02d}"
        query = ("""
            SELECT * FROM articles
            WHERE published_at >= %s AND published_at < %s
            ORDER BY published_at DESC
            LIMIT %s OFFSET %s
        """ if self.db_type == "postgresql" else """
            SELECT * FROM articles
            WHERE published_at >= ? AND published_at < ?
            ORDER BY published_at DESC
            LIMIT ? OFFSET ?
        """)
        return self._execute(query, (f"{prefix}-01", f"{prefix}-31", limit, offset), fetch=True)

    def get_articles_by_month_count(self, year: int, month: int) -> int:
        """Get total article count for a specific month."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            prefix = f"{year:04d}-{month:02d}"
            if self.db_type == "postgresql":
                cursor.execute("""
                    SELECT COUNT(*) FROM articles
                    WHERE published_at >= %s AND published_at < %s
                """, (f"{prefix}-01", f"{prefix}-31"))
            else:
                cursor.execute("""
                    SELECT COUNT(*) FROM articles
                    WHERE published_at >= ? AND published_at < ?
                """, (f"{prefix}-01", f"{prefix}-31"))
            return cursor.fetchone()[0]

    def get_all_articles_paginated(self, limit: int = 20, offset: int = 0,
                                    category: str = None, source: str = None,
                                    sort: str = "latest") -> tuple:
        """Get paginated articles with total count for proper pagination.
        Returns (articles_list, total_count)."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            query = "SELECT * FROM articles"
            count_query = "SELECT COUNT(*) FROM articles"
            conditions = []
            params = []
            count_params = []

            if category:
                cond = "category = %s" if self.db_type == "postgresql" else "category = ?"
                conditions.append(cond)
                params.append(category)
                count_params.append(category)
            if source:
                cond = "source = %s" if self.db_type == "postgresql" else "source = ?"
                conditions.append(cond)
                params.append(source)
                count_params.append(source)

            if conditions:
                where = " WHERE " + " AND ".join(conditions)
                query += where
                count_query += where

            # Get total count
            cursor.execute(count_query, tuple(count_params))
            total = cursor.fetchone()[0]

            # Order
            order_map = {
                "latest": "published_at DESC",
                "popular": "views DESC",
                "bullish": "sentiment_score DESC",
                "bearish": "sentiment_score ASC",
            }
            order = order_map.get(sort, "published_at DESC")
            query += f" ORDER BY {order}"

            # Paginate
            if self.db_type == "postgresql":
                query += f" LIMIT %s OFFSET %s"
            else:
                query += f" LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, tuple(params))
            if self.db_type != "postgresql":
                self.conn.commit()
            articles = [dict(row) for row in cursor.fetchall()]
            return articles, total

    # ---- Cleanup Methods ----
    # NOTE: Articles are stored PERMANENTLY - no auto-deletion.
    # Only non-critical data (fear_greed_index, bot_stats history) is cleaned up.

    def cleanup_fear_greed_history(self, keep_days: int = 90):
        """Remove old fear & greed entries beyond keep_days."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            if self.db_type == "postgresql":
                cursor.execute("DELETE FROM fear_greed_index WHERE timestamp < NOW() - INTERVAL '%s days'", (keep_days,))
            else:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("DELETE FROM fear_greed_index WHERE timestamp < ?", (cutoff,))
                self.conn.commit()
            deleted = cursor.rowcount
        if deleted:
            logger.info(f"Cleaned up {deleted} old fear_greed entries (kept last {keep_days} days)")
        return deleted

    def get_fear_greed_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get fear & greed index history for the last N days."""
        if self.db_type == "postgresql":
            query = """
                SELECT value, classification, timestamp FROM fear_greed_index
                WHERE timestamp > NOW() - INTERVAL '%s days'
                ORDER BY timestamp ASC
            """
            return self._execute(query, (days,), fetch=True)
        else:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            query = """
                SELECT value, classification, timestamp FROM fear_greed_index
                WHERE timestamp > ?
                ORDER BY timestamp ASC
            """
            return self._execute(query, (cutoff,), fetch=True)

    # ---- Bookmark Methods ----

    # ---- Comments Methods ----

    def _init_comments_table(self):
        """Initialize comments table."""
        cursor = self.conn.cursor()
        if self.db_type == "postgresql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    id SERIAL PRIMARY KEY,
                    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
                    author_name TEXT NOT NULL,
                    author_email TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_comments_article ON comments(article_id DESC);
                CREATE INDEX IF NOT EXISTS idx_comments_created ON comments(created_at DESC);
            """)
        else:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    article_id INTEGER NOT NULL,
                    author_name TEXT NOT NULL,
                    author_email TEXT DEFAULT '',
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    upvotes INTEGER DEFAULT 0,
                    downvotes INTEGER DEFAULT 0,
                    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_comments_article ON comments(article_id DESC);
                CREATE INDEX IF NOT EXISTS idx_comments_created ON comments(created_at DESC);
            """)
            self.conn.commit()

    def add_comment(self, article_id: int, author_name: str, content: str, author_email: str = "") -> Optional[int]:
        """Add a comment to an article."""
        try:
            with self._lock:
                self.ensure_connection()
                cursor = self.conn.cursor()
                if self.db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO comments (article_id, author_name, author_email, content)
                        VALUES (%s, %s, %s, %s) RETURNING id
                    """, (article_id, author_name[:100], author_email[:200], content[:2000]))
                    result = cursor.fetchone()
                    return result[0] if result else None
                else:
                    cursor.execute("""
                        INSERT INTO comments (article_id, author_name, author_email, content)
                        VALUES (?, ?, ?, ?)
                    """, (article_id, author_name[:100], author_email[:200], content[:2000]))
                    self.conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            if self.db_type != "postgresql":
                self.conn.rollback()
            return None

    def get_comments(self, article_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get comments for an article, ordered by newest first."""
        query = ("""
            SELECT * FROM comments WHERE article_id = %s
            ORDER BY created_at DESC LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT * FROM comments WHERE article_id = ?
            ORDER BY created_at DESC LIMIT ?
        """)
        return self._execute(query, (article_id, limit), fetch=True)

    def get_comment_count(self, article_id: int) -> int:
        """Get comment count for an article."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            if self.db_type == "postgresql":
                cursor.execute("SELECT COUNT(*) FROM comments WHERE article_id = %s", (article_id,))
            else:
                cursor.execute("SELECT COUNT(*) FROM comments WHERE article_id = ?", (article_id,))
            return cursor.fetchone()[0]

    def vote_comment(self, comment_id: int, vote_type: str) -> bool:
        """Upvote or downvote a comment."""
        try:
            col = "upvotes" if vote_type == "up" else "downvotes"
            query = (f"UPDATE comments SET {col} = {col} + 1 WHERE id = %s" if self.db_type == "postgresql"
                     else f"UPDATE comments SET {col} = {col} + 1 WHERE id = ?")
            self._execute(query, (comment_id,))
            return True
        except Exception as e:
            logger.error(f"Error voting comment: {e}")
            return False

    def _init_bookmarks_table(self):
        """Initialize bookmarks table."""
        cursor = self.conn.cursor()
        if self.db_type == "postgresql":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    article_id INTEGER NOT NULL REFERENCES articles(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, article_id)
                );
                CREATE INDEX IF NOT EXISTS idx_bookmarks_session ON bookmarks(session_id);
            """)
        else:
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    article_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, article_id),
                    FOREIGN KEY (article_id) REFERENCES articles(id)
                );
                CREATE INDEX IF NOT EXISTS idx_bookmarks_session ON bookmarks(session_id);
            """)
            self.conn.commit()

    def toggle_bookmark(self, session_id: str, article_id: int) -> bool:
        """Toggle a bookmark. Returns True if bookmarked, False if removed."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            # Check if exists
            if self.db_type == "postgresql":
                cursor.execute("SELECT 1 FROM bookmarks WHERE session_id = %s AND article_id = %s", (session_id, article_id))
            else:
                cursor.execute("SELECT 1 FROM bookmarks WHERE session_id = ? AND article_id = ?", (session_id, article_id))
            if cursor.fetchone():
                # Remove
                if self.db_type == "postgresql":
                    cursor.execute("DELETE FROM bookmarks WHERE session_id = %s AND article_id = %s", (session_id, article_id))
                else:
                    cursor.execute("DELETE FROM bookmarks WHERE session_id = ? AND article_id = ?", (session_id, article_id))
                    self.conn.commit()
                return False
            else:
                # Add
                if self.db_type == "postgresql":
                    cursor.execute("INSERT INTO bookmarks (session_id, article_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (session_id, article_id))
                else:
                    cursor.execute("INSERT OR IGNORE INTO bookmarks (session_id, article_id) VALUES (?, ?)", (session_id, article_id))
                    self.conn.commit()
                return True

    def get_bookmarked_articles(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get bookmarked articles for a session."""
        query = ("""
            SELECT a.* FROM articles a
            INNER JOIN bookmarks b ON a.id = b.article_id
            WHERE b.session_id = %s
            ORDER BY b.created_at DESC LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT a.* FROM articles a
            INNER JOIN bookmarks b ON a.id = b.article_id
            WHERE b.session_id = ?
            ORDER BY b.created_at DESC LIMIT ?
        """)
        return self._execute(query, (session_id, limit), fetch=True)

    def is_bookmarked(self, session_id: str, article_id: int) -> bool:
        """Check if an article is bookmarked."""
        query = ("SELECT 1 FROM bookmarks WHERE session_id = %s AND article_id = %s" if self.db_type == "postgresql"
                 else "SELECT 1 FROM bookmarks WHERE session_id = ? AND article_id = ?")
        result = self._execute(query, (session_id, article_id), fetchone=True)
        return result is not None

    # ---- Article Rating Methods ----

    def rate_article(self, article_id: int, session_id: str, rating: int, ip_address: str = '') -> bool:
        """Rate an article (1-5). Returns True if rated, False if already rated."""
        try:
            with self._lock:
                self.ensure_connection()
                cursor = self.conn.cursor()
                # Clamp rating
                rating = max(1, min(5, int(rating)))
                # Check if already rated by this session
                if self.db_type == "postgresql":
                    cursor.execute(
                        "SELECT 1 FROM article_ratings WHERE session_id = %s AND article_id = %s",
                        (session_id, article_id))
                else:
                    cursor.execute(
                        "SELECT 1 FROM article_ratings WHERE session_id = ? AND article_id = ?",
                        (session_id, article_id))
                if cursor.fetchone():
                    # Already rated, update existing
                    if self.db_type == "postgresql":
                        cursor.execute(
                            "UPDATE article_ratings SET rating = %s, ip_address = %s WHERE session_id = %s AND article_id = %s",
                            (rating, ip_address, session_id, article_id))
                    else:
                        cursor.execute(
                            "UPDATE article_ratings SET rating = ?, ip_address = ? WHERE session_id = ? AND article_id = ?",
                            (rating, ip_address, session_id, article_id))
                    if self.db_type != "postgresql":
                        self.conn.commit()
                    logger.debug(f"Updated rating for article {article_id} by session {session_id}: {rating}")
                    return True
                else:
                    # Insert new rating
                    if self.db_type == "postgresql":
                        cursor.execute(
                            "INSERT INTO article_ratings (article_id, session_id, rating, ip_address) VALUES (%s, %s, %s, %s)",
                            (article_id, session_id, rating, ip_address))
                    else:
                        cursor.execute(
                            "INSERT INTO article_ratings (article_id, session_id, rating, ip_address) VALUES (?, ?, ?, ?)",
                            (article_id, session_id, rating, ip_address))
                    if self.db_type != "postgresql":
                        self.conn.commit()
                    logger.debug(f"New rating for article {article_id} by session {session_id}: {rating}")
                    return True
        except Exception as e:
            logger.error(f"Error rating article {article_id}: {e}")
            if self.db_type != "postgresql":
                self.conn.rollback()
            return False

    def get_article_rating(self, article_id: int) -> Dict[str, Any]:
        """Get average rating and count for an article. Returns dict with avg, count, distribution."""
        query = ("SELECT rating, COUNT(*) FROM article_ratings WHERE article_id = %s GROUP BY rating" if self.db_type == "postgresql"
                 else "SELECT rating, COUNT(*) FROM article_ratings WHERE article_id = ? GROUP BY rating")
        rows = self._execute(query, (article_id,), fetch=True)
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total = 0
        total_score = 0
        for row_dict in rows:
            r = row_dict["rating"]
            count = row_dict["count"]
            distribution[int(r)] = int(count)
            total += int(count)
            total_score += int(r) * int(count)
        avg = round(total_score / total, 1) if total > 0 else 0
        return {"avg": avg, "count": total, "distribution": distribution}

    def get_user_article_rating(self, article_id: int, session_id: str) -> Optional[int]:
        """Get the user's rating for a specific article. Returns int or None."""
        query = ("SELECT rating FROM article_ratings WHERE session_id = %s AND article_id = %s" if self.db_type == "postgresql"
                 else "SELECT rating FROM article_ratings WHERE session_id = ? AND article_id = ?")
        row = self._execute(query, (session_id, article_id), fetchone=True)
        return row["rating"] if row else None

    def get_top_rated_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get articles with highest average ratings."""
        query = ("""
            SELECT a.*, COALESCE(ar.avg_rating, 0) as avg_rating, COALESCE(ar.rating_count, 0) as rating_count
            FROM articles a
            LEFT JOIN (
                SELECT article_id, ROUND(AVG(rating), 1) as avg_rating, COUNT(*) as rating_count
                FROM article_ratings GROUP BY article_id
            ) ar ON a.id = ar.article_id
            WHERE ar.rating_count >= 1
            ORDER BY ar.avg_rating DESC, ar.rating_count DESC
            LIMIT %s
        """ if self.db_type == "postgresql" else """
            SELECT a.*, COALESCE(ar.avg_rating, 0) as avg_rating, COALESCE(ar.rating_count, 0) as rating_count
            FROM articles a
            LEFT JOIN (
                SELECT article_id, ROUND(AVG(rating), 1) as avg_rating, COUNT(*) as rating_count
                FROM article_ratings GROUP BY article_id
            ) ar ON a.id = ar.article_id
            WHERE ar.rating_count >= 1
            ORDER BY ar.avg_rating DESC, ar.rating_count DESC
            LIMIT ?
        """)
        return self._execute(query, (limit,), fetch=True)

    # ---- Comment Spam Methods ----

    def check_comment_rate_limit(self, session_id: str, max_comments: int = 3, window_minutes: int = 5) -> bool:
        """Check if session has exceeded comment rate limit. Returns True if rate limited."""
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        query = ("SELECT COUNT(*) FROM comments WHERE author_name = %s AND created_at > %s" if self.db_type == "postgresql"
                 else "SELECT COUNT(*) FROM comments WHERE author_name = ? AND created_at > ?")
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute(query, (session_id, since))
            count = cursor.fetchone()[0]
        if count >= max_comments:
            logger.warning(f"Rate limit exceeded for session {session_id}: {count} comments in {window_minutes} min")
            return True
        return False

    def get_spam_keywords(self) -> List[str]:
        """Return list of common spam keywords to filter comments."""
        return [
            "buy now", "click here", "free money", "crypto giveaway", "send btc",
            "double your", "100% guaranteed", "act now", "limited time", "sign up bonus",
            "earn money", "make money fast", "get rich", "nigerian prince", "lottery winner",
            "viagra", "casino", "poker", "betting", "gambling", "loan approved",
            "cheap viagra", "weight loss", "diet pill", "crypto signal", "pump group",
        ]

    def report_comment(self, comment_id: int, session_id: str, reason: str = 'spam') -> bool:
        """Report a comment as spam/inappropriate."""
        try:
            query = ("INSERT INTO comment_reports (comment_id, session_id, reason) VALUES (%s, %s, %s)" if self.db_type == "postgresql"
                     else "INSERT INTO comment_reports (comment_id, session_id, reason) VALUES (?, ?, ?)")
            self._execute(query, (comment_id, session_id[:64], reason[:50]))
            return True
        except Exception as e:
            logger.error(f"Error reporting comment {comment_id}: {e}")
            return False

    def get_comment_reports(self, min_reports: int = 3) -> List[Dict[str, Any]]:
        """Get comments that have been reported multiple times."""
        query = ("""
            SELECT c.*, COUNT(r.id) as report_count, GROUP_CONCAT(r.reason, ', ') as reasons
            FROM comments c
            INNER JOIN comment_reports r ON c.id = r.comment_id
            GROUP BY c.id
            HAVING COUNT(r.id) >= %s
            ORDER BY report_count DESC
        """ if self.db_type == "postgresql" else """
            SELECT c.*, COUNT(r.id) as report_count, GROUP_CONCAT(r.reason, ', ') as reasons
            FROM comments c
            INNER JOIN comment_reports r ON c.id = r.comment_id
            GROUP BY c.id
            HAVING COUNT(r.id) >= ?
            ORDER BY report_count DESC
        """)
        return self._execute(query, (min_reports,), fetch=True)

    # ---- Academy Methods ----

    def add_academy_lesson(self, slug: str, title: str, description: str = None, content: str = None,
                           category: str = 'bitcoin', difficulty: str = 'beginner',
                           read_time: int = 5, topics: str = '[]', order_index: int = 0) -> Optional[int]:
        """Add or update an academy lesson."""
        try:
            with self._lock:
                self.ensure_connection()
                cursor = self.conn.cursor()
                if self.db_type == "postgresql":
                    cursor.execute("""
                        INSERT INTO academy_lessons (slug, title, description, content, category, difficulty, read_time, topics, order_index)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (slug) DO UPDATE SET
                            title = EXCLUDED.title, description = EXCLUDED.description,
                            content = EXCLUDED.content, category = EXCLUDED.category,
                            difficulty = EXCLUDED.difficulty, read_time = EXCLUDED.read_time,
                            topics = EXCLUDED.topics, order_index = EXCLUDED.order_index
                        RETURNING id
                    """, (slug[:100], title, description, content, category[:50], difficulty[:20], read_time, topics, order_index))
                    result = cursor.fetchone()
                    return result[0] if result else None
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO academy_lessons (slug, title, description, content, category, difficulty, read_time, topics, order_index)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (slug[:100], title, description, content, category[:50], difficulty[:20], read_time, topics, order_index))
                    self.conn.commit()
                    return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding academy lesson '{slug}': {e}")
            if self.db_type != "postgresql":
                self.conn.rollback()
            return None

    def get_academy_lessons(self, category: str = None, difficulty: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get academy lessons with optional filters."""
        with self._lock:
            self.ensure_connection()
            cursor = self.conn.cursor()
            query = "SELECT * FROM academy_lessons"
            conditions = []
            params = []

            if category:
                conditions.append("category = %s" if self.db_type == "postgresql" else "category = ?")
                params.append(category)
            if difficulty:
                conditions.append("difficulty = %s" if self.db_type == "postgresql" else "difficulty = ?")
                params.append(difficulty)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY order_index ASC, created_at DESC"
            query += " LIMIT %s" if self.db_type == "postgresql" else " LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            if self.db_type != "postgresql":
                self.conn.commit()
            return [dict(row) for row in cursor.fetchall()]

    def get_academy_lesson(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get a single lesson by slug."""
        query = "SELECT * FROM academy_lessons WHERE slug = %s" if self.db_type == "postgresql" else "SELECT * FROM academy_lessons WHERE slug = ?"
        return self._execute(query, (slug,), fetchone=True)

    def get_academy_categories(self) -> List[Dict[str, Any]]:
        """Get all academy categories with lesson counts."""
        query = """
            SELECT category, COUNT(*) as lesson_count
            FROM academy_lessons
            GROUP BY category
            ORDER BY lesson_count DESC
        """
        return self._execute(query, fetch=True)

    def increment_lesson_views(self, lesson_id: int):
        """Increment lesson view count."""
        query = ("UPDATE academy_lessons SET views = views + 1 WHERE id = %s" if self.db_type == "postgresql"
                 else "UPDATE academy_lessons SET views = views + 1 WHERE id = ?")
        self._execute(query, (lesson_id,))

    def add_quiz_questions(self, lesson_id: int, questions: List[Dict[str, Any]]) -> bool:
        """Add quiz questions for a lesson. questions is a list of dicts."""
        try:
            import json as _json
            with self._lock:
                self.ensure_connection()
                cursor = self.conn.cursor()
                for q in questions:
                    options_json = _json.dumps(q.get("options", [])) if not isinstance(q.get("options"), str) else q.get("options", "[]")
                    if self.db_type == "postgresql":
                        cursor.execute("""
                            INSERT INTO quiz_questions (lesson_id, question, options, correct_answer, explanation)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (lesson_id, q.get("question", ""), options_json, int(q.get("correct_answer", 0)), q.get("explanation", "")))
                    else:
                        cursor.execute("""
                            INSERT INTO quiz_questions (lesson_id, question, options, correct_answer, explanation)
                            VALUES (?, ?, ?, ?, ?)
                        """, (lesson_id, q.get("question", ""), options_json, int(q.get("correct_answer", 0)), q.get("explanation", "")))
                if self.db_type != "postgresql":
                    self.conn.commit()
            logger.info(f"Added {len(questions)} quiz questions for lesson {lesson_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding quiz questions for lesson {lesson_id}: {e}")
            if self.db_type != "postgresql":
                self.conn.rollback()
            return False

    def get_quiz_questions(self, lesson_id: int) -> List[Dict[str, Any]]:
        """Get all quiz questions for a lesson."""
        query = ("SELECT * FROM quiz_questions WHERE lesson_id = %s ORDER BY id ASC" if self.db_type == "postgresql"
                 else "SELECT * FROM quiz_questions WHERE lesson_id = ? ORDER BY id ASC")
        return self._execute(query, (lesson_id,), fetch=True)

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
