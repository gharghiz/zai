import feedparser
import requests
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape

from config import RSS_FEEDS, CRYPTO_KEYWORDS, MAX_ARTICLES_PER_FEED, SCRAPER_TIMEOUT

logger = logging.getLogger(__name__)


class Scraper:
    """RSS Feed scraper for crypto news."""

    def __init__(self):
        self.feeds = RSS_FEEDS
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, text/html",
        })

    def parse_feed(self, feed_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Parse a single RSS feed and return articles."""
        articles = []
        feed_url = feed_info["url"]
        feed_name = feed_info.get("name", "Unknown")
        feed_category = feed_info.get("category", "news")

        try:
            logger.info(f"Fetching feed: {feed_name} ({feed_url})")
            response = self.session.get(feed_url, timeout=SCRAPER_TIMEOUT)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if feed.bozo and not feed.entries:
                logger.debug(f"Feed parse error for {feed_name}: {feed.bozo_exception}")
                return articles

            for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
                article = self._parse_entry(entry, feed_name, feed_category)
                if article and self._is_crypto_related(article):
                    articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from {feed_name}")

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching feed: {feed_name}")
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error fetching feed: {feed_name}")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else '?'
            logger.warning(f"HTTP {status} fetching feed {feed_name}: {feed_url}")
        except Exception as e:
            logger.error(f"Unexpected error fetching feed {feed_name}: {e}")

        return articles

    def _parse_entry(self, entry: Any, source: str, category: str) -> Optional[Dict[str, Any]]:
        """Parse a feed entry into an article dictionary."""
        try:
            # Title
            title = self._clean_text(getattr(entry, "title", ""))
            if not title:
                return None

            # URL
            url = getattr(entry, "link", "")
            if not url:
                url = getattr(entry, "id", "")
            if not url:
                return None

            # Clean URL (remove tracking params)
            url = self._clean_url(url)

            # Content
            content = ""
            if hasattr(entry, "content") and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, "summary"):
                content = entry.summary
            elif hasattr(entry, "description"):
                content = entry.description

            content = self._clean_html(content)

            # Published date
            published_at = None
            for date_field in ["published", "updated", "created", "pubDate"]:
                if hasattr(entry, date_field) and getattr(entry, date_field):
                    try:
                        published_at = datetime.strptime(
                            entry[date_field],
                            "%a, %d %b %Y %H:%M:%S %z"
                        )
                        break
                    except (ValueError, TypeError):
                        try:
                            from dateutil import parser as dateparser
                            published_at = dateparser.parse(entry[date_field])
                            break
                        except Exception:
                            pass

            if published_at and published_at.tzinfo:
                published_at = published_at.astimezone(timezone.utc).replace(tzinfo=None)

            # Image URL
            image_url = self._extract_image(entry, content)

            # Author
            author = getattr(entry, "author", "") or getattr(entry, "dc_creator", "")

            return {
                "title": title,
                "url": url,
                "content": content[:5000] if content else "",
                "summary": None,
                "source": source,
                "category": category,
                "image_url": image_url,
                "published_at": published_at,
                "author": author,
                "language": self._detect_language(title, content),
            }

        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        text = unescape(text)
        text = " ".join(text.split())
        return text.strip()

    def _clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean content."""
        if not html_content:
            return ""
        import re
        # Remove script and style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        html_content = re.sub(r'<[^>]+>', ' ', html_content)
        # Clean whitespace
        html_content = unescape(html_content)
        html_content = " ".join(html_content.split())
        return html_content.strip()

    def _clean_url(self, url: str) -> str:
        """Remove tracking parameters from URL."""
        import re
        url = url.split("?")[0] if "utm_" not in url else url
        url = re.sub(r'[?&]utm_[^&]*', '', url)
        url = re.sub(r'[?&]ref=[^&]*', '', url)
        url = url.rstrip("&?")
        return url

    def _extract_image(self, entry: Any, content: str) -> str:
        """Extract image URL from entry or content."""
        # Check media_thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            return entry.media_thumbnail[0].get("url", "")

        # Check media_content
        if hasattr(entry, "media_content") and entry.media_content:
            return entry.media_content[0].get("url", "")

        # Check enclosures
        if hasattr(entry, "enclosures") and entry.enclosures:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("image/"):
                    return enc.get("href", enc.get("url", ""))

        # Extract from content HTML
        import re
        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if img_match:
            return img_match.group(1)

        # Check for featured image
        if hasattr(entry, "featured_image"):
            return entry.featured_image

        return ""

    def _is_crypto_related(self, article: Dict[str, Any]) -> bool:
        """Check if an article is crypto-related based on keywords."""
        text = f"{article['title']} {article.get('content', '')}".lower()
        return any(keyword.lower() in text for keyword in CRYPTO_KEYWORDS)

    def _detect_language(self, title: str, content: str) -> str:
        """Simple language detection based on Arabic character presence."""
        text = f"{title} {content}"
        arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
        if arabic_chars > len(text) * 0.1:
            return "ar"
        return "en"

    def scrape_all(self, max_workers: int = 10) -> List[Dict[str, Any]]:
        """Scrape all RSS feeds in parallel."""
        all_articles = []
        logger.info(f"Starting to scrape {len(self.feeds)} feeds with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_feed = {
                executor.submit(self.parse_feed, feed): feed
                for feed in self.feeds
            }

            for future in as_completed(future_to_feed):
                feed = future_to_feed[future]
                try:
                    articles = future.result()
                    all_articles.extend(articles)
                except Exception as e:
                    logger.error(f"Error scraping feed {feed['name']}: {e}")

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                unique_articles.append(article)

        logger.info(f"Total scraped: {len(all_articles)}, Unique: {len(unique_articles)}")
        return unique_articles
