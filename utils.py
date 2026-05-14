import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def format_number(num: float, decimals: int = 2, prefix: str = "$") -> str:
    """Format a number with commas and optional prefix."""
    if num is None:
        return "N/A"
    if abs(num) >= 1e12:
        return f"{prefix}{num / 1e12:.{decimals}f}T"
    elif abs(num) >= 1e9:
        return f"{prefix}{num / 1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{prefix}{num / 1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{prefix}{num / 1e3:.{decimals}f}K"
    return f"{prefix}{num:.{decimals}f}"


def format_count(num: float, decimals: int = 1) -> str:
    """Format a count/number without currency prefix."""
    if num is None:
        return "N/A"
    if abs(num) >= 1e12:
        return f"{num / 1e12:.{decimals}f}T"
    elif abs(num) >= 1e9:
        return f"{num / 1e9:.{decimals}f}B"
    elif abs(num) >= 1e6:
        return f"{num / 1e6:.{decimals}f}M"
    elif abs(num) >= 1e3:
        return f"{num / 1e3:.{decimals}f}K"
    return f"{num:.{decimals}f}"


def format_price(price: float) -> str:
    """Format a cryptocurrency price."""
    if price is None:
        return "N/A"
    if price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:,.4f}"
    else:
        return f"${price:,.8f}"


def format_percentage(value: float) -> str:
    """Format a percentage value with sign."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def format_percentage_colored(value: float) -> str:
    """Format a percentage with color indicator."""
    if value is None:
        return "N/A"
    if value > 0:
        return f"🟢 +{value:.2f}%"
    elif value < 0:
        return f"🔴 {value:.2f}%"
    return f"⚪ 0.00%"


def sentiment_to_emoji(label: str) -> str:
    """Convert sentiment label to emoji."""
    mapping = {
        "very_bullish": "🚀",
        "bullish": "📈",
        "neutral": "➡️",
        "bearish": "📉",
        "very_bearish": "💀"
    }
    return mapping.get(label, "➡️")


def sentiment_to_color(label: str) -> str:
    """Convert sentiment label to CSS color class."""
    mapping = {
        "very_bullish": "text-green-400",
        "bullish": "text-green-300",
        "neutral": "text-gray-400",
        "bearish": "text-red-300",
        "very_bearish": "text-red-400"
    }
    return mapping.get(label, "text-gray-400")


def time_ago(dt) -> str:
    """Get a human-readable time ago string."""
    from datetime import datetime, timezone

    if dt is None:
        return "Unknown"

    if isinstance(dt, str):
        try:
            from dateutil import parser as dateparser
            dt = dateparser.parse(dt)
        except Exception:
            return "Unknown"

    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 365:
        return f"{diff.days // 365}y ago"
    elif diff.days > 30:
        return f"{diff.days // 30}mo ago"
    elif diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    return "Just now"


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to a maximum length."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].strip() + suffix


def safe_json_loads(text: str) -> Any:
    """Safely parse JSON string."""
    import json
    try:
        if isinstance(text, str):
            return json.loads(text)
        return text
    except (json.JSONDecodeError, TypeError):
        return []


def extract_domain(url: str) -> str:
    """Extract domain name from URL."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        return domain
    except Exception:
        return ""


def clean_html(html_content: str) -> str:
    """Remove all HTML tags from content."""
    import re
    if not html_content:
        return ""
    clean = re.sub(r'<[^>]+>', '', html_content)
    return clean.strip()


def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes."""
    if not text:
        return 0
    words = len(text.split())
    return max(1, round(words / words_per_minute))


def get_trending_topics(articles: List[Dict[str, Any]], limit: int = 10) -> List[tuple]:
    """Extract trending topics from article keywords."""
    keyword_counts = {}
    for article in articles:
        keywords = article.get("keywords", [])
        if isinstance(keywords, str):
            keywords = safe_json_loads(keywords)
        if isinstance(keywords, list):
            for kw in keywords:
                kw_lower = kw.lower().strip()
                if kw_lower:
                    keyword_counts[kw_lower] = keyword_counts.get(kw_lower, 0) + 1

    sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_keywords[:limit]
