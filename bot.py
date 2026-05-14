import logging
import re
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID,
                    BOT_RETRY_MAX, BOT_RETRY_DELAY, BOT_POST_DELAY,
                    BOT_MAX_MESSAGE_LENGTH, DISCORD_WEBHOOK_URL,
                    DISCORD_USERNAME, DISCORD_AVATAR_URL,
                    NOTIFY_BREAKING_SENTIMENT_THRESHOLD, NOTIFY_BREAKING_KEYWORDS)

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for posting crypto news to a channel."""

    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.channel_id = TELEGRAM_CHANNEL_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""

        self.session = requests.Session()
        retry_strategy = Retry(
            total=BOT_RETRY_MAX,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        if not self.token:
            logger.warning("Telegram bot token not configured")

    def _api_call(self, method: str, data: dict = None, files: dict = None) -> dict:
        """Make an API call to Telegram."""
        if not self.token:
            logger.error("Cannot make API call - no bot token configured")
            return {"ok": False, "error_code": 401, "description": "Bot token not configured"}

        url = f"{self.base_url}/{method}"
        try:
            if files:
                response = self.session.post(url, data=data, files=files, timeout=30)
            else:
                response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                logger.error(f"Telegram API error: {result.get('description')}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram API request failed: {e}")
            return {"ok": False, "error_code": 0, "description": str(e)}

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML",
                     disable_web_page_preview: bool = False) -> dict:
        """Send a text message via Telegram."""
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }
        return self._api_call("sendMessage", data)

    def send_photo(self, chat_id: str, photo_url: str, caption: str = "",
                   parse_mode: str = "HTML") -> dict:
        """Send a photo message via Telegram."""
        data = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption[:BOT_MAX_MESSAGE_LENGTH] if caption else "",
            "parse_mode": parse_mode,
        }
        return self._api_call("sendPhoto", data)

    def send_article(self, article: Dict[str, Any]) -> tuple:
        """Send a formatted article to Telegram channel.

        Returns:
            Tuple of (success: bool, message_id: int)
        """
        if not self.token or not self.channel_id:
            logger.warning("Telegram bot not configured - skipping post")
            return False, 0

        message = self._format_article(article)
        if not message:
            return False, 0

        image_url = article.get("image_url", "")

        for attempt in range(BOT_RETRY_MAX):
            try:
                if image_url:
                    result = self.send_photo(
                        chat_id=self.channel_id,
                        photo_url=image_url,
                        caption=message
                    )
                else:
                    result = self.send_message(
                        chat_id=self.channel_id,
                        text=message,
                        disable_web_page_preview=False
                    )

                if result.get("ok"):
                    message_id = result.get("result", {}).get("message_id", 0)
                    logger.info(f"Article posted to Telegram (ID: {message_id}): {article.get('title', '')[:50]}...")
                    return True, message_id
                else:
                    error = result.get("description", "Unknown error")
                    if "too long" in error.lower():
                        # Try without image if message is too long
                        if image_url:
                            logger.warning("Message too long, retrying without image")
                            image_url = ""
                            continue
                        # Truncate and retry
                        message = self._format_article(article, short=True)
                        if message:
                            result = self.send_message(
                                chat_id=self.channel_id,
                                text=message,
                                disable_web_page_preview=True
                            )
                            if result.get("ok"):
                                return True, 0
                    logger.warning(f"Attempt {attempt + 1} failed: {error}")

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} error: {e}")

            if attempt < BOT_RETRY_MAX - 1:
                time.sleep(BOT_RETRY_DELAY * (attempt + 1))

        return False, 0

    # Article length classification thresholds (word counts)
    SHORT_ARTICLE_MAX = 60       # < 60 words = flash/quick news
    MEDIUM_ARTICLE_MIN = 60      # 60-200 words = standard format
    MEDIUM_ARTICLE_MAX = 200
    # > 200 words = long article (needs smart summarization)

    def _classify_article_length(self, article: Dict[str, Any]) -> str:
        """Classify article as 'short', 'medium', or 'long' based on content length.

        Returns:
            'short' for < 60 words, 'medium' for 60-200 words, 'long' for > 200 words.
        """
        content = article.get("content") or ""
        summary = article.get("summary") or ""
        title = article.get("title") or ""

        # Use content primarily, fall back to summary + title
        text = content if content else f"{title} {summary}"

        # Clean HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        word_count = len(text.split())

        if word_count < self.SHORT_ARTICLE_MAX:
            return "short"
        elif word_count <= self.MEDIUM_ARTICLE_MAX:
            return "medium"
        else:
            return "long"

    def _format_article(self, article: Dict[str, Any], short: bool = False) -> str:
        """Format an article for Telegram posting.

        Smart formatting based on article length:
        - Long articles (>200 words): Summarized with key bullet points
        - Medium articles (60-200 words): Standard full format
        - Short articles (<60 words): Compact flash news format (full content preserved)

        When 'short' is True, always uses emergency truncated format.
        """
        title = article.get("title", "Untitled")
        summary = article.get("summary", "")
        source = article.get("source", "Unknown")
        url = article.get("url", "")
        sentiment_label = article.get("sentiment_label", "neutral")
        keywords = article.get("keywords", [])
        published_at = article.get("published_at")
        content = article.get("content", "")
        insights = article.get("ai_insights", "")

        # Emergency short mode (fallback when message too long)
        if short:
            return self._format_emergency_short(title, summary, source, url, sentiment_label)

        # Smart length-based formatting
        article_length = self._classify_article_length(article)

        if article_length == "long":
            return self._format_long_article(
                title=title, content=content, summary=summary,
                source=source, url=url, sentiment_label=sentiment_label,
                keywords=keywords, published_at=published_at, insights=insights
            )
        elif article_length == "short":
            return self._format_short_article(
                title=title, content=content, summary=summary,
                source=source, url=url, sentiment_label=sentiment_label,
                keywords=keywords, published_at=published_at
            )
        else:
            # Medium - standard full format
            return self._format_medium_article(
                title=title, summary=summary,
                source=source, url=url, sentiment_label=sentiment_label,
                keywords=keywords, published_at=published_at, insights=insights
            )

    def _format_emergency_short(self, title: str, summary: str, source: str,
                                 url: str, sentiment_label: str) -> str:
        """Emergency truncated format when message exceeds Telegram limits."""
        sentiment_emojis = {
            "very_bullish": "🚀🟢", "bullish": "📈🟢", "neutral": "⚪",
            "bearish": "📉🔴", "very_bearish": "💣🔴"
        }
        sentiment_emoji = sentiment_emojis.get(sentiment_label, "⚪")

        message = f"{sentiment_emoji} <b>{self._escape_html(title)}</b>\n\n"
        if summary:
            message += f"{self._escape_html(summary[:200])}\n\n"
        message += f"📰 <b>{self._escape_html(source)}</b>\n"
        message += f"🔗 <a href=\"{url}\">Read more</a>"
        return message

    def _format_long_article(self, title: str, content: str, summary: str,
                              source: str, url: str, sentiment_label: str,
                              keywords: list, published_at, insights: str) -> str:
        """Format a LONG article (>200 words) with smart summarization.

        Uses AI or local NLP to create a concise summary with bullet points,
        preserving the core message without distortion.
        """
        sentiment_emojis = {
            "very_bullish": "🚀🟢", "bullish": "📈🟢", "neutral": "⚪",
            "bearish": "📉🔴", "very_bearish": "💣🔴"
        }
        sentiment_emoji = sentiment_emojis.get(sentiment_label, "⚪")

        # Generate smart summary for the long article
        telegram_summary = self._generate_smart_summary(title, content, summary, insights)

        message = f"{'━━━━━━━━━━━━━━━━━━'}\n\n"
        message += f"{sentiment_emoji} <b>{self._escape_html(title)}</b>\n\n"
        message += f"📄 <b>Detailed Report</b>\n\n"

        # Smart summary: check if it contains bullet points (key points)
        lines = telegram_summary.split('\n')
        summary_text_lines = []
        key_point_lines = []
        in_key_points = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Detect "Key Points:" header
            if 'key points' in stripped.lower() or 'key takeaways' in stripped.lower():
                in_key_points = True
                continue
            if in_key_points and stripped.startswith('▸'):
                key_point_lines.append(stripped)
            elif in_key_points and (stripped.startswith('•') or stripped.startswith('-') or stripped.startswith('*')):
                key_point_lines.append('▸ ' + stripped[1:].strip())
            else:
                summary_text_lines.append(stripped)

        # Main summary text
        if summary_text_lines:
            main_summary = ' '.join(summary_text_lines)
            if len(main_summary) > 500:
                main_summary = main_summary[:497] + '...'
            message += f"💬 <i>{self._escape_html(main_summary)}</i>\n\n"

        # Key points as bullet list
        if key_point_lines:
            message += "🔑 <b>Key Points:</b>\n"
            for point in key_point_lines[:5]:
                clean_point = point.lstrip('▸').strip()
                if len(clean_point) > 120:
                    clean_point = clean_point[:117] + '...'
                message += f"  ▸ {self._escape_html(clean_point)}\n"
            message += "\n"

        # Keywords
        if keywords:
            tags = " ".join(f"#{kw.replace(' ', '_')}" for kw in keywords[:5])
            message += f"🏷 {tags}\n\n"

        # Date and source
        if published_at:
            if isinstance(published_at, str):
                date_str = published_at[:10]
            else:
                date_str = published_at.strftime("%Y-%m-%d")
            message += f"📅 {date_str} | "

        message += f"📰 <b>{self._escape_html(source)}</b>\n\n"
        message += f"🔗 <a href=\"{url}\">Read full article</a>"

        result = message[:BOT_MAX_MESSAGE_LENGTH]
        if len(message) > BOT_MAX_MESSAGE_LENGTH:
            logger.info(f"Long article summary trimmed from {len(message)} to {BOT_MAX_MESSAGE_LENGTH} chars")
        return result

    def _format_medium_article(self, title: str, summary: str,
                               source: str, url: str, sentiment_label: str,
                               keywords: list, published_at, insights: str) -> str:
        """Format a MEDIUM article (60-200 words) with standard full format."""
        sentiment_emojis = {
            "very_bullish": "🚀🟢", "bullish": "📈🟢", "neutral": "⚪",
            "bearish": "📉🔴", "very_bearish": "💣🔴"
        }
        sentiment_emoji = sentiment_emojis.get(sentiment_label, "⚪")

        message = f"{'━━━━━━━━━━━━━━━━━━'}\n\n"
        message += f"{sentiment_emoji} <b>{self._escape_html(title)}</b>\n\n"

        if summary:
            message += f"💬 <i>{self._escape_html(summary)}</i>\n\n"

        # AI Insights
        if insights:
            message += f"🧠 <b>Analysis:</b> {self._escape_html(insights)}\n\n"

        # Keywords
        if keywords:
            tags = " ".join(f"#{kw.replace(' ', '_')}" for kw in keywords[:5])
            message += f"🏷 {tags}\n\n"

        # Date
        if published_at:
            if isinstance(published_at, str):
                date_str = published_at[:10]
            else:
                date_str = published_at.strftime("%Y-%m-%d")
            message += f"📅 {date_str} | "

        message += f"📰 <b>{self._escape_html(source)}</b>\n\n"
        message += f"🔗 <a href=\"{url}\">Read full article</a>"

        return message[:BOT_MAX_MESSAGE_LENGTH]

    def _format_short_article(self, title: str, content: str, summary: str,
                               source: str, url: str, sentiment_label: str,
                               keywords: list, published_at) -> str:
        """Format a SHORT article (<60 words) as flash/quick news.

        Publishes the full content without distortion in a compact format.
        Short articles are displayed as 'Quick News' with the complete content
        preserved since there's no need for summarization.
        """
        sentiment_emojis = {
            "very_bullish": "🚀🟢", "bullish": "📈🟢", "neutral": "⚪",
            "bearish": "📉🔴", "very_bearish": "💣🔴"
        }
        sentiment_emoji = sentiment_emojis.get(sentiment_label, "⚪")

        # Use the full content if available, otherwise use summary
        article_text = content or summary or ""

        # Clean HTML from content
        if article_text:
            article_text = re.sub(r'<[^>]+>', ' ', article_text)
            article_text = re.sub(r'\s+', ' ', article_text).strip()

        message = f"⚡ <b>Quick News</b>\n\n"
        message += f"{sentiment_emoji} <b>{self._escape_html(title)}</b>\n\n"

        # Publish full content (not truncated) for short articles
        if article_text:
            message += f"💬 {self._escape_html(article_text)}\n\n"
        elif summary:
            message += f"💬 {self._escape_html(summary)}\n\n"

        # Keywords (compact)
        if keywords:
            tags = " ".join(f"#{kw.replace(' ', '_')}" for kw in keywords[:4])
            message += f"🏷 {tags}\n\n"

        # Date and source on one line
        date_str = ""
        if published_at:
            if isinstance(published_at, str):
                date_str = published_at[:10]
            else:
                date_str = published_at.strftime("%Y-%m-%d")

        if date_str:
            message += f"📅 {date_str} | 📰 {self._escape_html(source)}\n\n"
        else:
            message += f"📰 <b>{self._escape_html(source)}</b>\n\n"

        message += f"🔗 <a href=\"{url}\">Read more</a>"

        return message[:BOT_MAX_MESSAGE_LENGTH]

    def _generate_smart_summary(self, title: str, content: str,
                                 summary: str, insights: str) -> str:
        """Generate a smart summary for long articles.

        Tries AI-powered summarization first, falls back to local NLP.
        The summary preserves the core message with key bullet points.
        """
        try:
            from ai import AIService
            ai_service = AIService()
            smart_summary = ai_service.summarize_for_telegram(
                title=title,
                content=content,
                summary=summary,
                insights=insights
            )
            if smart_summary:
                # Truncate if too long for Telegram
                if len(smart_summary) > 800:
                    smart_summary = smart_summary[:797] + "..."
                logger.info(f"Smart summary generated: {len(smart_summary)} chars")
                return smart_summary
        except Exception as e:
            logger.error(f"Smart summary generation failed: {e}")

        # Fallback: use existing summary or first sentences
        if summary:
            return summary[:400]

        # Extract first 3 sentences from content
        if content:
            clean_content = re.sub(r'<[^>]+>', ' ', content)
            sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', clean_content)
            sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
            fallback = '. '.join(sentences[:3])
            if len(fallback) > 400:
                fallback = fallback[:397] + '...'
            return fallback

        return title

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def post_articles(self, articles: List[Dict[str, Any]], db=None) -> int:
        """Post multiple articles to Telegram with delay."""
        if not self.token or not self.channel_id:
            logger.warning("Telegram bot not configured")
            return 0

        posted_count = 0
        for article in articles:
            success, message_id = self.send_article(article)
            if success:
                posted_count += 1
                # Mark as posted in database
                if db:
                    db.mark_article_posted(
                        article_id=article["id"],
                        telegram_message_id=message_id
                    )
            # Delay between posts
            if posted_count < len(articles):
                time.sleep(BOT_POST_DELAY)

        if posted_count > 0 and db:
            db.update_bot_stats(posted=posted_count)

        logger.info(f"Posted {posted_count}/{len(articles)} articles to Telegram")
        return posted_count

    def get_bot_info(self) -> dict:
        """Get bot information from Telegram API."""
        return self._api_call("getMe")

    def test_connection(self) -> bool:
        """Test the bot connection."""
        result = self.get_bot_info()
        if result.get("ok"):
            bot_info = result.get("result", {})
            logger.info(f"Bot connected: @{bot_info.get('username', 'unknown')}")
            return True
        return False

    # ---- Discord Webhook Methods ----

    def send_discord_message(self, article: Dict[str, Any]) -> bool:
        """Send an article notification via Discord webhook."""
        if not DISCORD_WEBHOOK_URL:
            return False

        title = article.get("title", "Untitled")
        url = article.get("url", "")
        summary = article.get("summary", "")
        source = article.get("source", "Unknown")
        sentiment_label = article.get("sentiment_label", "neutral")
        image_url = article.get("image_url", "")

        sentiment_colors = {
            "very_bullish": 0x34d399,
            "bullish": 0x22c55e,
            "neutral": 0x94a3b8,
            "bearish": 0xef4444,
            "very_bearish": 0xdc2626,
        }
        color = sentiment_colors.get(sentiment_label, 0x94a3b8)

        embed = {
            "title": title,
            "url": url,
            "description": summary[:300] if summary else "",
            "color": color,
            "footer": {"text": f"Source: {source}"},
        }
        if image_url:
            embed["image"] = {"url": image_url}

        payload = {
            "username": DISCORD_USERNAME,
            "embeds": [embed],
        }
        if DISCORD_AVATAR_URL:
            payload["avatar_url"] = DISCORD_AVATAR_URL

        try:
            resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            if resp.status_code == 204:
                logger.info(f"Discord webhook sent: {title[:50]}...")
                return True
            else:
                logger.warning(f"Discord webhook returned status {resp.status_code}")
                return False
        except Exception as e:
            logger.error(f"Discord webhook error: {e}")
            return False

    # ---- Breaking News Detection ----

    def is_breaking_news(self, article: Dict[str, Any]) -> bool:
        """Detect if an article qualifies as breaking news."""
        title = article.get("title", "").lower()
        content = (article.get("content") or "").lower()
        text = f"{title} {content}"

        # Check sentiment threshold
        sentiment_score = abs(article.get("sentiment_score", 0))
        if sentiment_score >= NOTIFY_BREAKING_SENTIMENT_THRESHOLD:
            return True

        # Check breaking keywords
        for keyword in NOTIFY_BREAKING_KEYWORDS:
            if keyword.lower() in text:
                return True

        return False
