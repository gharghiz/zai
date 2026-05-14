import logging
import os
import random
import threading
import time
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET

from flask import Flask, jsonify, render_template, request, redirect, url_for, Response
from flask_cors import CORS
from flask_talisman import Talisman
from flask_compress import Compress
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database import Database
from scraper import Scraper
from processor import Processor
from ai import AIService
from market_fetcher import (
    get_coin_prices, get_trending_coins, get_fear_greed_index,
    get_global_crypto_data, search_coins
)
from utils import format_number, format_price, format_percentage, sentiment_to_emoji, time_ago, calculate_reading_time
from config import (
    CATEGORIES, CACHE_CONTROL_STATIC, CACHE_CONTROL_API, DISCORD_WEBHOOK_URL,
    VERSION, SECURITY_HEADERS, API_RATE_LIMIT, PAGINATION_DEFAULTS,
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ---- v7: Security Middleware ----
Talisman(app, force_https=False)
Compress(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(32).hex())

# Make site_categories, site_name, site_url, telegram_channel available in all templates
@app.context_processor
def inject_categories():
    return {
        "site_categories": CATEGORIES,
        "site_name": "CryptositNews",
        "site_url": "https://cryptositnews.com",
        "telegram_channel": "https://t.me/CryptositNews",
        "whale_alerts_enabled": True,
    }


# ---- v7: Security Headers ----
@app.after_request
def set_security_headers(response):
    for key, value in SECURITY_HEADERS.items():
        response.headers[key] = value
    return response


# ---- v7: Rate Limiting ----
limiter = Limiter(app=app, key_func=get_remote_address,
                  default_limits=[f"{API_RATE_LIMIT['requests_per_minute']}/minute"],
                  storage_uri="memory://")

# Initialize database
db = Database()

# Initialize AI service
ai_service = AIService()

# Initialize processor
processor = Processor(db=db, ai_service=ai_service)

# ---- Live Data Cache ----
_coin_cache = {"data": [], "updated_at": 0}
_trending_cache = {"data": [], "updated_at": 0}
_fear_greed_cache = {"data": None, "updated_at": 0}
_global_cache = {"data": None, "updated_at": 0}
CACHE_TTL = 300  # 5 minutes
MARKET_CACHE_TTL = 600  # 10 minutes


def refresh_coin_cache():
    """Refresh the live coin prices cache."""
    now = time.time()
    if now - _coin_cache["updated_at"] > CACHE_TTL:
        coins = get_coin_prices(20)
        if coins:
            _coin_cache["data"] = coins
            _coin_cache["updated_at"] = now
            logger.info(f"Coin cache refreshed: {len(coins)} coins")


def refresh_trending_cache():
    """Refresh the trending coins cache."""
    now = time.time()
    if now - _trending_cache["updated_at"] > MARKET_CACHE_TTL:
        trending = get_trending_coins()
        if trending:
            _trending_cache["data"] = trending
            _trending_cache["updated_at"] = now
            logger.info(f"Trending cache refreshed: {len(trending)} coins")


def refresh_fear_greed_cache():
    """Refresh the fear & greed index cache."""
    now = time.time()
    if now - _fear_greed_cache["updated_at"] > MARKET_CACHE_TTL:
        fng = get_fear_greed_index()
        _fear_greed_cache["data"] = fng
        _fear_greed_cache["updated_at"] = now
        if fng:
            db.save_fear_greed(fng["value"], fng["classification"])
            logger.info(f"Fear/Greed updated: {fng['value']} - {fng['classification']}")


def refresh_global_cache():
    """Refresh global market data cache."""
    now = time.time()
    if now - _global_cache["updated_at"] > MARKET_CACHE_TTL:
        gdata = get_global_crypto_data()
        _global_cache["data"] = gdata
        _global_cache["updated_at"] = now


def background_scraper():
    """Background thread that periodically scrapes news and fetches market data."""
    from bot import TelegramBot
    bot = TelegramBot()
    scraper = Scraper()
    scrape_interval = 60   # 1 minute
    market_interval = 300  # 5 minutes
    last_scrape = 0
    last_market = 0

    logger.info("[Background] Scraper thread started")

    while True:
        try:
            now = time.time()

            # Refresh market data (staggered to avoid rate limits)
            if now - last_market > market_interval:
                logger.info("[Background] Refreshing market data...")
                refresh_coin_cache()
                # Trending, fear/greed, global refresh on alternate cycles
                choice = random.choice(["trending", "fear_greed", "global"])
                if choice == "trending":
                    refresh_trending_cache()
                elif choice == "fear_greed":
                    refresh_fear_greed_cache()
                else:
                    refresh_global_cache()
                last_market = now

            # Scrape news
            if now - last_scrape > scrape_interval:
                logger.info("[Background] Scraping news feeds...")
                try:
                    articles = scraper.scrape_all()
                    if articles:
                        processed = processor.process_articles(articles)
                        saved = processor.save_articles(processed)
                        if saved > 0:
                            logger.info(f"[Background] Saved {saved} new articles")

                            # Auto-post to Telegram
                            if bot.token and bot.channel_id:
                                unposted = db.get_unposted_articles(limit=5)
                                if unposted:
                                    posted = bot.post_articles(unposted, db=db)
                                    logger.info(f"[Background] Posted {posted} to Telegram")

                            # Auto-notify Discord for breaking news
                            if DISCORD_WEBHOOK_URL and unposted:
                                for article in unposted:
                                    if bot.is_breaking_news(article):
                                        sent = bot.send_discord_message(article)
                                        if sent:
                                            logger.info(f"[Background] Breaking news sent to Discord: {article.get('title', '')[:50]}")
                                        break  # Only send one breaking notification per cycle
                except Exception as e:
                    logger.error(f"[Background] Scrape error: {e}")
                last_scrape = now

        except Exception as e:
            logger.error(f"[Background] Thread error: {e}")

        time.sleep(30)  # check every 30 seconds


# Start background thread
bg_thread = threading.Thread(target=background_scraper, daemon=True)
bg_thread.start()

# Initial data fetch in background to avoid blocking app startup
def _initial_data_fetch():
    logger.info("[Startup] Performing initial data fetch...")
    refresh_coin_cache()
    refresh_trending_cache()
    refresh_fear_greed_cache()
    refresh_global_cache()

init_thread = threading.Thread(target=_initial_data_fetch, daemon=True)
init_thread.start()

# Initial scrape on startup
logger.info("Performing initial news scrape...")
try:
    scraper = Scraper()
    articles = scraper.scrape_all()
    if articles:
        processed = processor.process_articles(articles)
        saved = processor.save_articles(processed)
        logger.info(f"Initial scrape: {saved} new articles saved")
except Exception as e:
    logger.error(f"Initial scrape failed: {e}")


# ---- API Routes ----

@app.route("/api/news")
def api_news():
    """Get latest news articles."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    category = request.args.get("category")
    source = request.args.get("source")
    search = request.args.get("q")
    sort = request.args.get("sort", "latest")

    offset = (page - 1) * per_page

    if search:
        articles = db.search_articles(search, limit=per_page + offset)
    elif category:
        articles = db.get_latest_articles(limit=per_page + offset, category=category)
    elif source:
        articles = db.get_latest_articles(limit=per_page + offset, source=source)
    else:
        articles = db.get_latest_articles(limit=per_page + offset)
        articles = articles[offset:]

    # Sort articles
    if sort == "popular":
        articles.sort(key=lambda a: a.get("views", 0) or 0, reverse=True)
    elif sort == "bullish":
        articles.sort(key=lambda a: a.get("sentiment_score", 0) or 0, reverse=True)
    elif sort == "bearish":
        articles.sort(key=lambda a: a.get("sentiment_score", 0) or 0)
    # else "latest" - default order from DB

    for article in articles:
        article["time_ago"] = time_ago(article.get("published_at"))
        article["formatted_sentiment"] = sentiment_to_emoji(article.get("sentiment_label", "neutral"))

    return jsonify({
        "success": True,
        "data": articles,
        "page": page,
        "per_page": per_page,
        "total": db.get_article_count()
    })


@app.route("/api/news/<int:article_id>")
def api_article(article_id):
    """Get a single article by ID."""
    article = db.get_article_by_id(article_id)
    if not article:
        return jsonify({"success": False, "error": "Article not found"}), 404

    db.increment_views(article_id)
    article["time_ago"] = time_ago(article.get("published_at"))
    article["formatted_sentiment"] = sentiment_to_emoji(article.get("sentiment_label", "neutral"))

    category = article.get("category")
    related = db.get_latest_articles(limit=5, category=category)
    related = [a for a in related if a["id"] != article_id][:4]
    for r in related:
        r["time_ago"] = time_ago(r.get("published_at"))

    return jsonify({"success": True, "data": article, "related": related})


@app.route("/api/prices")
def api_prices():
    """Get live coin prices from CoinGecko."""
    refresh_coin_cache()
    limit = request.args.get("limit", 20, type=int)
    coins = _coin_cache["data"][:limit]

    for c in coins:
        c["formatted_price"] = format_price(c.get("price"))
        c["formatted_change_24h"] = format_percentage(c.get("change_24h"))
        c["formatted_change_7d"] = format_percentage(c.get("change_7d"))
        c["formatted_market_cap"] = format_number(c.get("market_cap"))
        c["formatted_volume"] = format_number(c.get("volume_24h"))

    return jsonify({
        "success": True,
        "data": coins,
        "updated_at": _coin_cache["updated_at"],
    })


@app.route("/api/trending")
def api_trending():
    """Get trending coins from CoinGecko."""
    refresh_trending_cache()
    trending = _trending_cache["data"]

    # Enrich with price data
    coin_prices = {c["symbol"]: c for c in _coin_cache["data"]}
    for t in trending:
        price_data = coin_prices.get(t["symbol"], {})
        t["price"] = price_data.get("price", 0)
        t["change_24h"] = price_data.get("change_24h", 0)
        t["formatted_price"] = format_price(t.get("price"))
        t["formatted_change_24h"] = format_percentage(t.get("change_24h"))

    return jsonify({
        "success": True,
        "data": trending,
        "updated_at": _trending_cache["updated_at"],
    })


@app.route("/api/fear-greed")
def api_fear_greed():
    """Get fear and greed index."""
    refresh_fear_greed_cache()
    data = _fear_greed_cache["data"] or db.get_latest_fear_greed()
    return jsonify({"success": True, "data": data})


@app.route("/api/global")
def api_global():
    """Get global crypto market data."""
    refresh_global_cache()
    data = _global_cache["data"]
    return jsonify({"success": True, "data": data})


@app.route("/api/search")
def api_search():
    """Search coins and articles."""
    q = request.args.get("q", "")
    results = {"articles": [], "coins": []}

    if q:
        results["articles"] = db.search_articles(q, limit=10)
        results["coins"] = search_coins(q)

    return jsonify({"success": True, "data": results})


@app.route("/api/markets")
def api_markets():
    """Get market data (live from CoinGecko + DB)."""
    refresh_coin_cache()
    coins = _coin_cache["data"]

    for c in coins:
        c["formatted_price"] = format_price(c.get("price"))
        c["formatted_change_24h"] = format_percentage(c.get("change_24h"))
        c["formatted_change_7d"] = format_percentage(c.get("change_7d"))
        c["formatted_market_cap"] = format_number(c.get("market_cap"))
        c["formatted_volume"] = format_number(c.get("volume_24h"))

    return jsonify({"success": True, "data": coins})


@app.route("/api/sources")
def api_sources():
    """Get all available sources."""
    sources = db.get_sources()
    return jsonify({"success": True, "data": sources})


@app.route("/api/categories")
def api_categories():
    """Get all available categories."""
    categories = db.get_categories()
    return jsonify({"success": True, "data": categories})


@app.route("/api/stats")
def api_stats():
    """Get dashboard statistics."""
    stats = db.get_stats_dashboard()
    return jsonify({"success": True, "data": stats})


@app.route("/api/popular")
def api_popular():
    """Get popular/trending articles by views."""
    articles = db.get_popular_articles(limit=10)
    for article in articles:
        article["time_ago"] = time_ago(article.get("published_at"))
        article["formatted_sentiment"] = sentiment_to_emoji(article.get("sentiment_label", "neutral"))
    return jsonify({"success": True, "data": articles})


@app.route("/api/scrape-now", methods=["POST"])
@limiter.limit("100/minute")
def api_scrape_now():
    """Trigger an immediate scrape (admin endpoint - requires API key)."""
    admin_key = os.getenv("ADMIN_API_KEY", "")
    auth_header = request.headers.get("Authorization", "")
    if admin_key and auth_header != f"Bearer {admin_key}":
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    try:
        scraper = Scraper()
        articles = scraper.scrape_all()
        if articles:
            processed = processor.process_articles(articles)
            saved = processor.save_articles(processed)
            return jsonify({"success": True, "message": f"Scraped and saved {saved} new articles"})
        return jsonify({"success": True, "message": "No new articles found"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---- v4 API Endpoints ----

@app.route("/api/search/suggestions")
def api_search_suggestions():
    """Search suggestions endpoint for autocomplete dropdown."""
    q = request.args.get("q", "").strip()
    result = {"articles": [], "coins": []}

    if q and len(q) >= 2:
        articles = db.search_articles(q, limit=5)
        result["articles"] = [
            {"id": a["id"], "title": a["title"]}
            for a in articles
        ]

        coins = search_coins(q)
        result["coins"] = [
            {"id": c["id"], "symbol": c["symbol"], "name": c["name"], "image": c.get("thumb", c.get("image", ""))}
            for c in coins[:3]
        ]

    return jsonify(result)


@app.route("/api/breaking")
def api_breaking():
    """Get latest breaking news articles for the breaking news banner."""
    articles = db.get_latest_articles(limit=5, category="breaking")

    for article in articles:
        article["time_ago"] = time_ago(article.get("published_at"))
        article["formatted_sentiment"] = sentiment_to_emoji(article.get("sentiment_label", "neutral"))

    return jsonify({
        "success": True,
        "data": articles,
    })


@app.route("/api/bookmarks", methods=["GET", "POST"])
def api_bookmarks():
    """Server-side bookmarks API.

    GET: Returns bookmarked articles for the session.
    POST: Accepts {"article_id": int} to toggle bookmark.
    Uses session_id cookie for anonymous identification.
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        article_id = data.get("article_id")
        if article_id is None:
            return jsonify({"success": False, "error": "article_id is required"}), 400
        bookmarked = db.toggle_bookmark(session_id, article_id)
        resp = jsonify({"success": True, "bookmarked": bookmarked})
        if not request.cookies.get("session_id"):
            resp.set_cookie("session_id", session_id, max_age=365 * 24 * 3600, httponly=True)
        return resp

    # GET - return bookmarked articles
    articles = db.get_bookmarked_articles(session_id)
    for a in articles:
        a["time_ago"] = time_ago(a.get("published_at"))
        a["formatted_sentiment"] = sentiment_to_emoji(a.get("sentiment_label", "neutral"))
    resp = jsonify({"success": True, "data": articles})
    if not request.cookies.get("session_id"):
        resp.set_cookie("session_id", session_id, max_age=365 * 24 * 3600, httponly=True)
    return resp


@app.route("/api/bookmarks/check/<int:article_id>")
def api_check_bookmark(article_id):
    """Check if an article is bookmarked for the current session."""
    session_id = request.cookies.get("session_id")
    if not session_id:
        return jsonify({"bookmarked": False})
    bookmarked = db.is_bookmarked(session_id, article_id)
    return jsonify({"bookmarked": bookmarked})


@app.route("/api/convert")
def api_convert():
    """Convert between cryptocurrencies using live prices."""
    from_coin = request.args.get("from", "bitcoin")
    to_coin = request.args.get("to", "tether")
    amount = request.args.get("amount", 1, type=float)

    refresh_coin_cache()
    
    prices = {c["id"]: c["price"] for c in _coin_cache["data"]}
    prices_by_sym = {c["symbol"]: c["price"] for c in _coin_cache["data"]}

    from_price = prices.get(from_coin) or prices_by_sym.get(from_coin, 0)
    to_price = prices.get(to_coin) or prices_by_sym.get(to_coin, 0)

    if from_price and to_price:
        result = (amount * from_price) / to_price
    elif from_price and to_coin in ["tether", "usdt", "usd"]:
        result = amount * from_price
    elif from_coin in ["tether", "usdt", "usd"] and to_price:
        result = amount / to_price
    else:
        result = 0

    return jsonify({
        "success": True,
        "from": from_coin,
        "to": to_coin,
        "amount": amount,
        "result": result,
        "from_price": from_price,
        "to_price": to_price,
    })


# ---- Template Routes ----

@app.route("/")
def index():
    """Home page."""
    # Use cached data (background thread handles refreshes)
    coin_prices = _coin_cache["data"][:10]

    # Trending coins - use cached data, already includes prices from get_trending_coins()
    trending = _trending_cache["data"][:8]
    # Fallback: enrich with coin_prices_map if trending lacks prices
    coin_prices_map = {c["id"]: c for c in _coin_cache["data"]}
    coin_prices_map_by_sym = {c["symbol"]: c for c in _coin_cache["data"]}
    for t in trending:
        if not t.get("price"):
            # Try matching by id first, then by symbol
            price_data = coin_prices_map.get(t.get("id")) or coin_prices_map_by_sym.get(t.get("symbol"), {})
            t["price"] = price_data.get("price", 0)
            t["change_24h"] = price_data.get("change_24h", 0)

    # Articles
    articles = db.get_latest_articles(limit=12)
    for article in articles:
        article["time_ago"] = time_ago(article.get("published_at"))

    # Telegram posted articles
    telegram_articles = db.get_telegram_articles(limit=6)
    for article in telegram_articles:
        article["time_ago"] = time_ago(article.get("posted_at") or article.get("published_at"))

    # Stats
    stats = db.get_stats_dashboard()

    # Fear & Greed (background thread handles refresh)
    fear_greed = _fear_greed_cache["data"] or db.get_latest_fear_greed()

    # Global data (background thread handles refresh)
    global_data = _global_cache["data"]

    return render_template("index.html",
                           coin_prices=coin_prices,
                           trending=trending,
                           articles=articles,
                           telegram_articles=telegram_articles,
                           stats=stats,
                           fear_greed=fear_greed,
                           global_data=global_data)


@app.route("/news")
def news_page():
    """News listing page."""
    page = request.args.get("page", 1, type=int)
    category = request.args.get("category")
    source = request.args.get("source")
    telegram = request.args.get("telegram")
    sort = request.args.get("sort", "latest")
    per_page = 20
    offset = (page - 1) * per_page

    total = 0
    if telegram:
        all_articles = db.get_telegram_articles(limit=per_page + offset + 1)
        articles = all_articles[offset:]
        total = len(all_articles)
        has_next = len(articles) > per_page
        articles = articles[:per_page]
    else:
        articles, total = db.get_all_articles_paginated(
            limit=per_page, offset=offset,
            category=category, source=source, sort=sort
        )
        has_next = total > offset + per_page

    # Sort articles (for telegram posts which don't use DB sort)
    if telegram:
        if sort == "popular":
            articles.sort(key=lambda a: a.get("views", 0) or 0, reverse=True)
        elif sort == "bullish":
            articles.sort(key=lambda a: a.get("sentiment_score", 0) or 0, reverse=True)
        elif sort == "bearish":
            articles.sort(key=lambda a: a.get("sentiment_score", 0) or 0)

    for article in articles:
        article["time_ago"] = time_ago(article.get("published_at"))

    categories = db.get_categories()
    sources = db.get_sources()

    return render_template("news.html",
                           articles=articles,
                           categories=categories,
                           sources=sources,
                           page=page,
                           has_next=has_next,
                           total_articles=total,
                           current_category=category,
                           current_source=source,
                           telegram_filter=telegram,
                           current_sort=sort)


@app.route("/news/<int:article_id>")
def article_page(article_id):
    """Single article page."""
    try:
        article = db.get_article_by_id(article_id)
        if not article:
            return redirect(url_for("news_page"))

        db.increment_views(article_id)
        article["time_ago"] = time_ago(article.get("published_at"))

        related = db.get_latest_articles(limit=5, category=article.get("category"))
        related = [a for a in related if a["id"] != article_id][:4]
        for r in related:
            r["time_ago"] = time_ago(r.get("published_at"))

        # Ensure all fields exist to prevent template errors
        article.setdefault("id", article_id)
        article.setdefault("content", "")
        article.setdefault("summary", "")
        article.setdefault("image_url", "")
        article.setdefault("keywords", "")
        article.setdefault("ai_insights", "")
        article.setdefault("url", "")
        article.setdefault("source", "")
        article.setdefault("category", "")
        article["sentiment_score"] = article.get("sentiment_score") or 0
        article["sentiment_label"] = article.get("sentiment_label") or "neutral"
        article["views"] = article.get("views") or 0
        article["is_posted"] = article.get("is_posted") or 0
        article.setdefault("published_at", "")

        return render_template("article.html", article=article, related=related)
    except Exception as e:
        logger.error(f"Article page error (ID={article_id}): {e}", exc_info=True)
        return redirect(url_for("news_page"))


@app.route("/market")
def market_page():
    """Market data page with live CoinGecko data."""
    market_data = _coin_cache["data"]

    for item in market_data:
        item["formatted_price"] = format_price(item.get("price"))
        item["formatted_change_24h"] = format_percentage(item.get("change_24h"))
        item["formatted_change_7d"] = format_percentage(item.get("change_7d"))
        item["formatted_market_cap"] = format_number(item.get("market_cap"))
        item["formatted_volume"] = format_number(item.get("volume_24h"))

    # Trending - use cached data with prices
    trending = _trending_cache["data"][:10]
    coin_prices_map = {c["id"]: c for c in _coin_cache["data"]}
    coin_prices_map_by_sym = {c["symbol"]: c for c in _coin_cache["data"]}
    for t in trending:
        if not t.get("price"):
            price_data = coin_prices_map.get(t.get("id")) or coin_prices_map_by_sym.get(t.get("symbol"), {})
            t["price"] = price_data.get("price", 0)
            t["change_24h"] = price_data.get("change_24h", 0)
        t["formatted_price"] = format_price(t.get("price"))
        t["formatted_change_24h"] = format_percentage(t.get("change_24h"))

    # Fear & Greed
    fear_greed = _fear_greed_cache["data"] or db.get_latest_fear_greed()

    # Global data
    global_data = _global_cache["data"]

    return render_template("market.html",
                           market_data=market_data,
                           trending=trending,
                           fear_greed=fear_greed,
                           global_data=global_data)


@app.route("/archive")
def archive_page():
    """Archive page - browse all articles by month."""
    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = 30

    archive_months = db.get_archive_months()
    selected_articles = []
    selected_month_label = None
    month_total = 0
    has_next = False

    if year and month:
        month_names = {1: "January", 2: "February", 3: "March", 4: "April",
                       5: "May", 6: "June", 7: "July", 8: "August",
                       9: "September", 10: "October", 11: "November", 12: "December"}
        selected_month_label = f"{month_names.get(month, month)} {year}"
        offset = (page - 1) * per_page
        month_total = db.get_articles_by_month_count(year, month)
        selected_articles = db.get_articles_by_month(year, month, limit=per_page + 1, offset=offset)
        has_next = len(selected_articles) > per_page
        selected_articles = selected_articles[:per_page]

        for article in selected_articles:
            article["time_ago"] = time_ago(article.get("published_at"))

    total_articles = db.get_article_count()

    return render_template("archive.html",
                           archive_months=archive_months,
                           selected_articles=selected_articles,
                           selected_month_label=selected_month_label,
                           year=year, month=month,
                           page=page, has_next=has_next,
                           month_total=month_total,
                           total_articles=total_articles)


@app.route("/bot")
def bot_page():
    """Telegram Bot info page."""
    stats = db.get_stats_dashboard()
    return render_template("bot.html", stats=stats)


@app.route("/about")
def about_page():
    """About page."""
    stats = db.get_stats_dashboard()
    popular = db.get_popular_articles(limit=5)
    for p in popular:
        p["time_ago"] = time_ago(p.get("published_at"))
    return render_template("about.html", stats=stats, popular=popular)


@app.route("/privacy")
def privacy_page():
    """Privacy Policy page."""
    return render_template("privacy.html")


@app.route("/terms")
def terms_page():
    """Terms of Service page."""
    return render_template("terms.html")


@app.route("/contact", methods=["GET", "POST"])
def contact_page():
    """Contact Us page."""
    if request.method == "POST":
        return redirect(url_for("contact_page"))
    return render_template("contact.html")


@app.route("/dmca")
def dmca_page():
    """DMCA Policy page."""
    return render_template("dmca.html")


# ---- v4 Template Routes ----

@app.route("/converter")
def converter_page():
    """Crypto converter page."""
    refresh_coin_cache()
    coins = _coin_cache["data"][:30]
    for c in coins:
        c["formatted_price"] = format_price(c.get("price"))
    return render_template("converter.html", coins=coins)


@app.route("/bookmarks")
def bookmarks_page():
    """Bookmarks page."""
    return render_template("bookmarks.html", site_categories=CATEGORIES, site_name="CryptositNews", telegram_channel="https://t.me/CryptositNews")


# ---- Error Handlers ----

@app.errorhandler(400)
def handle_bad_request(e):
    """Handle 400 Bad Request errors."""
    logger.warning(f"400 Bad Request: {request.path} - {e}")
    return render_template("404.html", error_code=400, error_title="Bad Request",
                          error_message="The request could not be understood. Please check the URL and try again."), 400


@app.errorhandler(403)
def handle_forbidden(e):
    """Handle 403 Forbidden errors."""
    logger.warning(f"403 Forbidden: {request.path} - {e}")
    return render_template("403.html"), 403


@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 Not Found errors."""
    logger.info(f"404 Not Found: {request.path}")
    return render_template("404.html"), 404


@app.errorhandler(429)
def handle_rate_limit(e):
    """Handle 429 Too Many Requests errors."""
    logger.warning(f"429 Rate Limited: {request.path} - {e}")
    return render_template("429.html"), 429


@app.errorhandler(500)
def handle_server_error(e):
    """Handle 500 Internal Server Error."""
    logger.error(f"500 Server Error: {request.path} - {e}", exc_info=True)
    return render_template("500.html"), 500


@app.errorhandler(Exception)
def handle_generic_error(e):
    """Catch-all handler for unhandled exceptions (prevents white-screen crashes)."""
    logger.error(f"Unhandled Exception: {request.path} - {type(e).__name__}: {e}", exc_info=True)
    # If API request, return JSON error
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    return render_template("500.html"), 500


# ---- Health Check ----

@app.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ---- Search Page ----

@app.route("/search")
def search_page():
    """Search page with results."""
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    articles = []
    total = 0
    if q and len(q) >= 2:
        articles = db.search_articles(q, limit=per_page + offset + 1)
        total = len(articles)
        articles = articles[offset:offset + per_page + 1]
        for article in articles:
            article["time_ago"] = time_ago(article.get("published_at"))

    has_next = len(articles) > per_page
    articles = articles[:per_page]

    # Trending keywords for suggestions
    trending_kw = db.get_trending_keywords(days=7, limit=15)

    return render_template("search.html",
                           q=q, articles=articles, page=page,
                           has_next=has_next, total=total,
                           trending_keywords=trending_kw)


# ---- Sitemap & Robots ----

@app.route("/sitemap.xml")
def sitemap():
    """Generate XML sitemap for SEO."""
    articles = db.get_latest_articles(limit=1000)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    # Static pages
    static_pages = [
        ("/", "1.0", "daily"),
        ("/news", "0.9", "hourly"),
        ("/market", "0.8", "hourly"),
        ("/about", "0.5", "monthly"),
        ("/privacy", "0.3", "yearly"),
        ("/terms", "0.3", "yearly"),
        ("/contact", "0.4", "yearly"),
        ("/dmca", "0.3", "yearly"),
        ("/bookmarks", "0.4", "weekly"),
        ("/converter", "0.6", "daily"),
        ("/archive", "0.6", "daily"),
        ("/whale-alerts", "0.6", "daily"),
        ("/airdrops", "0.7", "daily"),
        ("/daily-summary", "0.6", "daily"),
        ("/weekly-report", "0.7", "weekly"),
        ("/academy", "0.7", "weekly"),
        ("/calendar", "0.7", "daily"),
        ("/facts", "0.7", "weekly"),
        ("/rss", "0.8", "hourly"),
        ("/rss/breaking", "0.7", "hourly"),
        ("/rss/popular", "0.7", "hourly"),
    ]
    for path, priority, freq in static_pages:
        xml += f'  <url><loc>https://cryptositnews.com{path}</loc>'
        xml += f'<lastmod>{now}</lastmod><changefreq>{freq}</changefreq>'
        xml += f'<priority>{priority}</priority></url>\n'

    # Article pages
    for article in articles:
        url = f"https://cryptositnews.com/news/{article['id']}"
        published = article.get("published_at", now)
        if published and hasattr(published, 'strftime'):
            published = published.strftime("%Y-%m-%d")
        elif isinstance(published, str):
            published = published[:10]
        else:
            published = now
        xml += f'  <url><loc>{url}</loc><lastmod>{published}</lastmod>'
        xml += f'<changefreq>daily</changefreq><priority>0.7</priority></url>\n'

    xml += '</urlset>'
    return Response(xml, mimetype='application/xml')


@app.route("/robots.txt")
def robots():
    """Generate robots.txt for SEO."""
    txt = "User-agent: *\n"
    txt += "Allow: /\n"
    txt += "Disallow: /api/\n"
    txt += "Disallow: /health\n"
    txt += "Disallow: /scrape-now\n"
    txt += "Disallow: /admin\n"
    txt += f"\nSitemap: https://cryptositnews.com/sitemap.xml\n"
    txt += "\n# RSS Feeds\n"
    txt += "Allow: /rss/\n"
    txt += "Allow: /rss/source/\n"
    return Response(txt, mimetype='text/plain')


# ---- Advanced RSS Feeds ----

@app.route("/rss")
def rss_main():
    """Main RSS feed — latest 50 articles across all categories."""
    return _generate_rss_feed(
        title="CryptositNews - Latest Crypto News",
        description="Real-time cryptocurrency news, analysis, and market insights powered by AI.",
        link="https://cryptositnews.com",
        articles=db.get_latest_articles(limit=50),
    )


@app.route("/rss/<category>")
def rss_category(category):
    """RSS feed filtered by category (e.g., /rss/bitcoin, /rss/defi)."""
    # Validate category exists
    valid_categories = [c["slug"] for c in CATEGORIES]
    if category not in valid_categories:
        return redirect(url_for("rss_main"))

    cat_name = next((c["name"] for c in CATEGORIES if c["slug"] == category), category)
    articles = db.get_latest_articles(limit=50, category=category)
    return _generate_rss_feed(
        title=f"CryptositNews - {cat_name} News",
        description=f"Latest {cat_name} news and analysis from CryptositNews.",
        link=f"https://cryptositnews.com/news?category={category}",
        articles=articles,
        category=category,
    )


@app.route("/rss/source/<source_name>")
def rss_source(source_name):
    """RSS feed filtered by news source (e.g., /rss/source/CoinDesk)."""
    articles = db.get_latest_articles(limit=50, source=source_name)
    if not articles:
        return redirect(url_for("rss_main"))
    return _generate_rss_feed(
        title=f"CryptositNews - {source_name}",
        description=f"Latest articles from {source_name} on CryptositNews.",
        link=f"https://cryptositnews.com/news?source={source_name}",
        articles=articles,
    )


@app.route("/rss/breaking")
def rss_breaking():
    """RSS feed for breaking news only."""
    articles = db.get_latest_articles(limit=30, category="breaking")
    return _generate_rss_feed(
        title="CryptositNews - Breaking News",
        description="Breaking cryptocurrency news alerts from CryptositNews.",
        link="https://cryptositnews.com/news?category=breaking",
        articles=articles,
        category="breaking",
    )


@app.route("/rss/popular")
def rss_popular():
    """RSS feed for most popular/trending articles."""
    articles = db.get_popular_articles(limit=30)
    return _generate_rss_feed(
        title="CryptositNews - Trending News",
        description="Most popular and trending crypto news from CryptositNews.",
        link="https://cryptositnews.com/news?sort=popular",
        articles=articles,
    )


def _generate_rss_feed(title, description, link, articles, category=None):
    """Generate a valid RSS 2.0 XML feed."""
    rss = ET.Element("rss", version="2.0", **{"xmlns:atom": "http://www.w3.org/2005/Atom"})
    channel = ET.SubElement(rss, "channel")

    # Channel metadata
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "copyright").text = f"\u00a9 {datetime.now(timezone.utc).year} CryptositNews"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    ET.SubElement(channel, "generator").text = "CryptositNews RSS Generator"

    # Atom self link
    atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", f"https://cryptositnews.com/rss{f'/{category}' if category else ''}")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Image
    image = ET.SubElement(channel, "image")
    ET.SubElement(image, "url").text = "https://cryptositnews.com/static/favicon.png"
    ET.SubElement(image, "title").text = "CryptositNews"
    ET.SubElement(image, "link").text = "https://cryptositnews.com"

    for article in articles[:50]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article.get("title", "Untitled")
        ET.SubElement(item, "link").text = f"https://cryptositnews.com/news/{article.get('id', '')}"
        ET.SubElement(item, "guid").text = f"https://cryptositnews.com/news/{article.get('id', '')}"
        ET.SubElement(item, "guid").set("isPermaLink", "true")

        # Description (summary or content snippet)
        desc = article.get("summary") or article.get("content", "")
        if desc and len(desc) > 500:
            desc = desc[:497] + "..."
        ET.SubElement(item, "description").text = desc

        # Source
        source_elem = ET.SubElement(item, "source")
        source_elem.text = article.get("source", "CryptositNews")
        source_elem.set("url", article.get("url", ""))

        # Category
        if article.get("category"):
            ET.SubElement(item, "category").text = article.get("category")

        # Pub date
        pub = article.get("published_at", "")
        if pub:
            if hasattr(pub, "strftime"):
                pub_str = pub.strftime("%a, %d %b %Y %H:%M:%S +0000")
            elif isinstance(pub, str):
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00")).replace(tzinfo=None)
                    pub_str = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
                except (ValueError, TypeError):
                    pub_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
            else:
                pub_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
            ET.SubElement(item, "pubDate").text = pub_str

        # Image enclosure
        image_url = article.get("image_url", "")
        if image_url and image_url.startswith("http"):
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.set("url", image_url)
            enclosure.set("type", "image/jpeg")

        # Author
        if article.get("source"):
            ET.SubElement(item, "author").text = article.get("source")

    # Add RSS feeds to robots.txt sitemap
    xml_str = ET.tostring(rss, encoding="unicode", xml_declaration=True)
    return Response(xml_str, mimetype="application/rss+xml")


# ---- Fear & Greed History API ----

@app.route("/api/fear-greed/history")
def api_fear_greed_history():
    """Get fear & greed index history for charting."""
    days = request.args.get("days", 30, type=int)
    days = min(max(days, 7), 365)  # Clamp between 7-365
    history = db.get_fear_greed_history(days=days)
    return jsonify({"success": True, "data": history, "days": days})


# ---- Whale Alerts ----

from whale_alerts import WhaleAlertService
from airdrop_tracker import AirdropTracker

whale_service = WhaleAlertService()
airdrop_tracker = AirdropTracker()

@app.route("/api/whale-alerts")
def api_whale_alerts():
    """Get recent whale transactions."""
    min_value = request.args.get("min_value", 500000, type=float)
    limit = request.args.get("limit", 20, type=int)
    blockchain = request.args.get("blockchain")
    
    transactions = whale_service.get_cached_transactions(min_value_usd=min_value, limit=limit)
    if blockchain:
        transactions = [tx for tx in transactions if tx["blockchain"] == blockchain]
    
    stats = whale_service.get_stats()
    
    return jsonify({
        "success": True,
        "data": transactions,
        "stats": stats,
    })

@app.route("/whale-alerts")
def whale_alerts_page():
    """Whale Alerts page - large crypto transactions tracker."""
    transactions = whale_service.get_cached_transactions(limit=25)
    stats = whale_service.get_stats()
    return render_template("whale.html", transactions=transactions, stats=stats)


# ---- Comments API (v6: with spam protection below) ----

@app.route("/api/comments/<int:comment_id>/vote", methods=["POST"])
def api_vote_comment(comment_id):
    """Vote on a comment (upvote/downvote)."""
    data = request.get_json(silent=True) or {}
    vote_type = data.get("vote", "up")
    if vote_type not in ("up", "down"):
        return jsonify({"success": False, "error": "Invalid vote type"}), 400
    success = db.vote_comment(comment_id, vote_type)
    return jsonify({"success": success})


# ---- Airdrop Tracker ----

@app.route("/api/airdrops")
def api_airdrops():
    """Get airdrop listings with status and trust filters."""
    status = request.args.get("status")      # active, upcoming, ended, distributed, not_distributed
    trust = request.args.get("trust")        # verified, unverified
    category = request.args.get("category")
    q = request.args.get("q")
    limit = request.args.get("limit", 50, type=int)

    if q:
        airdrops = airdrop_tracker.search_airdrops(q)
    elif category:
        airdrops = airdrop_tracker.get_by_category(category)
    else:
        airdrops = airdrop_tracker.get_airdrops(status=status, trust=trust, limit=limit)

    stats = airdrop_tracker.get_stats()
    return jsonify({"success": True, "data": airdrops, "stats": stats})


@app.route("/airdrops")
def airdrops_page():
    """Airdrop Tracker page."""
    airdrops = airdrop_tracker.get_airdrops(limit=50)
    stats = airdrop_tracker.get_stats()
    return render_template("airdrops.html", airdrops=airdrops, stats=stats)


# ---- Daily AI Summary ----

@app.route("/api/daily-summary")
def api_daily_summary():
    """Generate daily AI market summary."""
    articles = db.get_latest_articles(limit=30)
    if not articles:
        return jsonify({"success": False, "message": "No articles available"})

    summary = ai_service.generate_daily_summary(articles)
    if summary:
        return jsonify({"success": True, "data": {"summary": summary, "article_count": len(articles)}})
    else:
        # Fallback: generate a local summary
        bullish = sum(1 for a in articles if a.get("sentiment_label") in ["bullish", "very_bullish"])
        bearish = sum(1 for a in articles if a.get("sentiment_label") in ["bearish", "very_bearish"])
        neutral = len(articles) - bullish - bearish
        sources = len(set(a.get("source", "") for a in articles))
        fallback = (f"Today's crypto market overview: {len(articles)} articles analyzed from {sources} sources. "
                    f"Sentiment breakdown: {bullish} bullish, {bearish} bearish, {neutral} neutral. "
                    f"Visit individual articles for detailed AI analysis.")
        return jsonify({"success": True, "data": {"summary": fallback, "article_count": len(articles), "ai_generated": False}})


@app.route("/api/comment-count/<int:article_id>")
def api_comment_count(article_id):
    """Get comment count for an article (lightweight endpoint)."""
    count = db.get_comment_count(article_id)
    return jsonify({"count": count})


@app.route("/daily-summary")
def daily_summary_page():
    """Daily AI Summary page."""
    articles = db.get_latest_articles(limit=30)
    stats = db.get_stats_dashboard()
    trending_kw = db.get_trending_keywords(days=1, limit=10)

    # Get sentiment breakdown
    bullish = [a for a in articles if a.get("sentiment_label") in ["bullish", "very_bullish"]]
    bearish = [a for a in articles if a.get("sentiment_label") in ["bearish", "very_bearish"]]
    neutral = [a for a in articles if a.get("sentiment_label") == "neutral"]

    summary = ai_service.generate_daily_summary(articles)

    return render_template("daily_summary.html",
                           summary=summary,
                           articles=articles[:10],
                           stats=stats,
                           trending_keywords=trending_kw,
                           bullish_count=len(bullish),
                           bearish_count=len(bearish),
                           neutral_count=len(neutral))


# ---- Crypto Events Calendar ----

from events_tracker import EventsTracker

events_tracker = EventsTracker()

@app.route("/api/events")
def api_events():
    """Get crypto events with optional filters."""
    status = request.args.get("status")
    category = request.args.get("category")
    month = request.args.get("month")
    q = request.args.get("q")
    include_stats = request.args.get("stats")

    events = events_tracker.get_events(
        status=status, category=category, month=month, search=q, limit=100
    )
    result = {"success": True, "data": events}

    if include_stats:
        result["stats"] = events_tracker.get_stats()

    return jsonify(result)


@app.route("/calendar")
def calendar_page():
    """Crypto Events Calendar page."""
    events = events_tracker.get_events(limit=50)
    stats = events_tracker.get_stats()
    categories = events_tracker.get_categories()
    months = events_tracker.get_calendar_months()
    return render_template("calendar.html",
                           events=events, stats=stats,
                           event_categories=categories,
                           calendar_months=months)


@app.route("/api/events/upcoming")
def api_upcoming_events():
    """Get upcoming events for sidebar/widget display."""
    events = events_tracker.get_upcoming_events(limit=5)
    return jsonify({"success": True, "data": events})


@app.route("/api/airdrops/active")
def api_active_airdrops():
    """Get active airdrops for sidebar/widget display."""
    airdrops = airdrop_tracker.get_airdrops(status="active", limit=5)
    stats = airdrop_tracker.get_stats()
    return jsonify({"success": True, "data": airdrops, "total_active": stats.get("active", 0)})


# ---- Crypto Academy ----

# ---- Weekly Report ----

@app.route("/weekly-report")
def weekly_report_page():
    """Weekly AI-powered crypto market report."""
    try:
        # Get articles from the last 7 days
        since = datetime.now(timezone.utc) - timedelta(days=7)
        all_articles = db.get_latest_articles(limit=200)

        # Filter to last 7 days
        week_articles = []
        for a in all_articles:
            pub = a.get("published_at")
            if pub:
                if hasattr(pub, 'strftime'):
                    if pub >= since:
                        week_articles.append(a)
                elif isinstance(pub, str) and pub:
                    try:
                        pub_dt = datetime.fromisoformat(pub.replace('Z', '+00:00')).replace(tzinfo=None)
                        if pub_dt >= since:
                            week_articles.append(a)
                    except (ValueError, TypeError):
                        week_articles.append(a)

        # Top 10 news by views (or most recent if no views)
        week_articles.sort(key=lambda a: a.get("views", 0) or 0, reverse=True)
        top_news = week_articles[:10]

        # For remaining top_news, fill with recent if less than 10
        if len(top_news) < 10:
            seen = {a["id"] for a in top_news}
            for a in week_articles:
                if a["id"] not in seen:
                    top_news.append(a)
                    seen.add(a["id"])
                    if len(top_news) >= 10:
                        break

        # Format top_news
        for a in top_news:
            a["time_ago"] = time_ago(a.get("published_at"))

        # Sort by views for display
        top_news.sort(key=lambda a: a.get("views", 0) or 0, reverse=True)

        # Get coin data for gainers/losers
        refresh_coin_cache()
        all_coins = _coin_cache["data"] if _coin_cache["data"] else []

        # Top gainers by 7d change
        gainers = sorted([c for c in all_coins if c.get("change_7d") is not None],
                         key=lambda c: c.get("change_7d", 0), reverse=True)[:5]
        for c in gainers:
            c["formatted_price"] = format_price(c.get("price"))
            c["formatted_change"] = format_percentage(c.get("change_7d"))
            c["formatted_mcap"] = format_number(c.get("market_cap"))

        # Top losers by 7d change
        losers = sorted([c for c in all_coins if c.get("change_7d") is not None],
                        key=lambda c: c.get("change_7d", 0))[:5]
        for c in losers:
            c["formatted_price"] = format_price(c.get("price"))
            c["formatted_change"] = format_percentage(c.get("change_7d"))
            c["formatted_mcap"] = format_number(c.get("market_cap"))

        # AI weekly summary (safe - catch errors)
        weekly_summary = None
        if week_articles:
            try:
                weekly_summary = ai_service.generate_daily_summary(week_articles[:30])
            except Exception:
                weekly_summary = None

        # Market data
        fear_greed = _fear_greed_cache["data"] or db.get_latest_fear_greed()
        global_data = _global_cache["data"] or {}
        stats = db.get_stats_dashboard() or {}

        return render_template("weekly_report.html",
                               weekly_summary=weekly_summary,
                               top_news=top_news,
                               top_gainers=gainers,
                               top_losers=losers,
                               fear_greed=fear_greed,
                               global_data=global_data,
                               stats=stats,
                               now_utc=datetime.now(timezone.utc),
                               timedelta=timedelta)
    except Exception as e:
        logger.error(f"Weekly report page error: {e}", exc_info=True)
        return redirect(url_for("index"))


# ---- Cache-Control Headers ----

@app.after_request
def add_cache_control(response):
    """Add cache-control headers to responses."""
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = f"public, max-age={CACHE_CONTROL_API}"
    elif request.path in ("/", "/news", "/market"):
        response.headers["Cache-Control"] = f"public, max-age={CACHE_CONTROL_STATIC}"
    elif request.path.startswith(("/static/", "/sitemap.xml", "/robots.txt", "/rss")):
        response.headers["Cache-Control"] = f"public, max-age={CACHE_CONTROL_STATIC}"
    return response


# ---- JSON-LD Structured Data Context Processor ----

@app.context_processor
def inject_json_ld():
    """Provide a helper function for JSON-LD in templates."""
    def generate_article_json_ld(article):
        import json
        if not article:
            return ""
        ld = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": article.get("title", ""),
            "description": (article.get("summary") or "")[:300],
            "url": article.get("url", f"https://cryptositnews.com/news/{article.get('id', '')}"),
            "datePublished": str(article.get("published_at", "")) if article.get("published_at") else "",
            "dateModified": str(article.get("scraped_at", "")) if article.get("scraped_at") else "",
            "author": {
                "@type": "Organization",
                "name": article.get("source", "CryptositNews")
            },
            "publisher": {
                "@type": "Organization",
                "name": "CryptositNews",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://cryptositnews.com/static/img/logo.png"
                }
            },
            "mainEntityOfPage": f"https://cryptositnews.com/news/{article.get('id', '')}"
        }
        if article.get("image_url"):
            ld["image"] = article["image_url"]
        return json.dumps(ld, ensure_ascii=False)
    return {"generate_article_json_ld": generate_article_json_ld}


# ---- Update Sitemap with New Pages ----
# (Already included above - just adding the daily-summary route)

# ---- v6: Article Rating API ----

@app.route("/api/rate", methods=["POST"])
def api_rate_article():
    """Rate an article (1-5 stars)."""
    data = request.get_json(silent=True) or {}
    article_id = data.get("article_id")
    rating = data.get("rating")

    if not article_id or not rating:
        return jsonify({"success": False, "error": "article_id and rating required"}), 400

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            return jsonify({"success": False, "error": "Rating must be 1-5"}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Invalid rating"}), 400

    session_id = request.cookies.get("session_id")
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr or "")[:45]

    rated = db.rate_article(article_id, session_id, rating, ip_address=ip_address)
    rating_data = db.get_article_rating(article_id)

    resp = jsonify({
        "success": True,
        "rated": rated,
        "rating": rating_data,
    })
    if not request.cookies.get("session_id"):
        resp.set_cookie("session_id", session_id, max_age=365 * 24 * 3600, httponly=True)
    return resp


@app.route("/api/rating/<int:article_id>")
def api_get_rating(article_id):
    """Get rating data for an article."""
    rating_data = db.get_article_rating(article_id)
    session_id = request.cookies.get("session_id")
    user_rating = None
    if session_id:
        user_rating = db.get_user_article_rating(article_id, session_id)
    return jsonify({
        "success": True,
        "data": rating_data,
        "user_rating": user_rating,
    })


# ---- v6: Comment Spam Protection ----

# In-memory rate limiter for comments
_comment_rate_store = {}  # {session_id: [timestamp, ...]}

def _check_comment_rate_limit(session_id, max_comments=3, window_minutes=5):
    """Check if session exceeded comment rate limit."""
    now = time.time()
    window = window_minutes * 60
    if session_id not in _comment_rate_store:
        _comment_rate_store[session_id] = []
    # Clean old entries
    _comment_rate_store[session_id] = [t for t in _comment_rate_store[session_id] if now - t < window]
    return len(_comment_rate_store[session_id]) >= max_comments


@app.route("/api/comments/<int:article_id>", methods=["GET", "POST"])
def api_comments(article_id):
    """Get or add comments for an article (with spam protection)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        author_name = (data.get("author_name") or "").strip()
        content = (data.get("content") or "").strip()
        author_email = (data.get("author_email") or "").strip()

        if not author_name or not content:
            return jsonify({"success": False, "error": "Name and content are required"}), 400
        if len(content) < 3:
            return jsonify({"success": False, "error": "Comment is too short"}), 400
        if len(content) > 2000:
            return jsonify({"success": False, "error": "Comment is too long (max 2000 chars)"}), 400

        # Rate limiting
        session_id = request.cookies.get("session_id")
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())

        if _check_comment_rate_limit(session_id, max_comments=3, window_minutes=5):
            return jsonify({"success": False, "error": "Too many comments. Please wait a few minutes."}), 429

        # Spam keyword detection
        spam_keywords = db.get_spam_keywords()
        content_lower = content.lower()
        author_lower = author_name.lower()
        for kw in spam_keywords:
            if kw in content_lower or kw in author_lower:
                logger.warning(f"Spam comment blocked: '{kw}' in comment by '{author_name}'")
                return jsonify({"success": False, "error": "Your comment contains inappropriate content."}), 403

        # Duplicate check (last 5 comments by same author)
        recent = db.get_comments(article_id, limit=5)
        for c in recent:
            if c.get("author_name", "").lower() == author_lower and c.get("content", "").strip().lower() == content_lower:
                return jsonify({"success": False, "error": "Duplicate comment detected."}), 409

        comment_id = db.add_comment(article_id, author_name, content, author_email)
        if comment_id:
            # Record for rate limiting
            if session_id not in _comment_rate_store:
                _comment_rate_store[session_id] = []
            _comment_rate_store[session_id].append(time.time())

            resp = jsonify({"success": True, "comment_id": comment_id})
            if not request.cookies.get("session_id"):
                resp.set_cookie("session_id", session_id, max_age=365 * 24 * 3600, httponly=True)
            return resp
        return jsonify({"success": False, "error": "Failed to add comment"}), 500

    # GET - return comments
    comments = db.get_comments(article_id, limit=100)
    for c in comments:
        ct = c.get("created_at", "")
        if ct:
            if hasattr(ct, 'strftime'):
                c["time_ago"] = time_ago(ct)
                c["formatted_date"] = ct.strftime("%Y-%m-%d %H:%M")
            elif isinstance(ct, str):
                c["formatted_date"] = ct[:16]
                c["time_ago"] = time_ago(ct)
    count = db.get_comment_count(article_id)
    return jsonify({"success": True, "data": comments, "total": count})


# ---- v6: Comment Reporting ----

@app.route("/api/comments/<int:comment_id>/report", methods=["POST"])
def api_report_comment(comment_id):
    """Report a comment as spam/inappropriate."""
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "spam")[:50]
    session_id = request.cookies.get("session_id") or "anonymous"
    db.report_comment(comment_id, session_id, reason)
    return jsonify({"success": True})



# ---- v7: Events RSS Feed ----

@app.route("/rss/events")
def rss_events_feed():
    """Generate RSS feed for crypto events."""
    status = request.args.get("status")
    category = request.args.get("category")
    limit = min(request.args.get("limit", 30, type=int), 100)

    events = events_tracker.get_events(status=status, category=category, limit=limit)

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/Atom">\n'
    xml += '<channel>\n'
    xml += '  <title>CryptositNews - Crypto Events Calendar</title>\n'
    xml += '  <link>https://cryptositnews.com/calendar</link>\n'
    xml += '  <description>Upcoming crypto events, network upgrades, conferences, token unlocks, and more from CryptositNews.</description>\n'
    xml += '  <language>en</language>\n'
    xml += '  <atom:link href="https://cryptositnews.com/rss/events" rel="self" type="application/rss+xml"/>\n'
    xml += f'  <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>\n'

    for event in events:
        title = (event.get("title", "") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        desc = (event.get("description", "") or "")[:500].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        event_date = event.get("date", "")

        xml += '  <item>\n'
        xml += f'    <title>{title}</title>\n'
        xml += f'    <link>https://cryptositnews.com/calendar</link>\n'
        xml += f'    <guid isPermaLink="true">https://cryptositnews.com/calendar#event-{event.get("id", "")}</guid>\n'
        xml += f'    <description>{desc}</description>\n'
        xml += f'    <pubDate>{event_date}T00:00:00 GMT</pubDate>\n'
        if event.get("category"):
            xml += f'    <category>{event["category"].replace("&", "&amp;")}</category>\n'
        if event.get("source"):
            xml += f'    <source url="{event["source"]}">{event.get("source", "")}</source>\n'
        xml += '  </item>\n'

    xml += '</channel>\n</rss>'
    return Response(xml, mimetype='application/xml')


# ---- v7: Airdrops RSS Feed ----

@app.route("/rss/airdrops")
def rss_airdrops_feed():
    """Generate RSS feed for active airdrops."""
    status = request.args.get("status")
    trust = request.args.get("trust")
    limit = min(request.args.get("limit", 30, type=int), 100)

    airdrops = airdrop_tracker.get_airdrops(status=status, trust=trust, limit=limit)

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/Atom">\n'
    xml += '<channel>\n'
    xml += '  <title>CryptositNews - Airdrop Tracker</title>\n'
    xml += '  <link>https://cryptositnews.com/airdrops</link>\n'
    xml += '  <description>Track the latest active and upcoming cryptocurrency airdrops with trust levels from CryptositNews.</description>\n'
    xml += '  <language>en</language>\n'
    xml += '  <atom:link href="https://cryptositnews.com/rss/airdrops" rel="self" type="application/rss+xml"/>\n'
    xml += f'  <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>\n'

    for drop in airdrops:
        title = (drop.get("name", "") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        desc = (drop.get("description", "") or "")[:500].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        full_title = f"{title} ({drop.get('symbol', '')})"

        xml += '  <item>\n'
        xml += f'    <title>{full_title}</title>\n'
        xml += f'    <link>https://cryptositnews.com/airdrops</link>\n'
        xml += f'    <guid isPermaLink="true">https://cryptositnews.com/airdrops#{drop.get("id", "")}</guid>\n'
        xml += f'    <description>{desc}</description>\n'

        # Additional metadata
        if drop.get("estimated_value"):
            xml += f'    <category>Estimated: {drop["estimated_value"]}</category>\n'
        if drop.get("difficulty"):
            xml += f'    <category>Difficulty: {drop["difficulty"]}</category>\n'
        if drop.get("chain"):
            xml += f'    <category>Chain: {drop["chain"]}</category>\n'
        if drop.get("status"):
            xml += f'    <category>Status: {drop["status"]}</category>\n'
        if drop.get("verified"):
            xml += f'    <category>Trust: {"Verified" if drop["verified"] else "Unverified"}</category>\n'

        xml += '  </item>\n'

    xml += '</channel>\n</rss>'
    return Response(xml, mimetype='application/xml')


# ---- v6: Academy Routes ----

@app.route("/academy")
def academy_page():
    """Crypto Academy - Educational hub."""
    return render_template("academy.html")


@app.route("/api/academy")
def api_academy_lessons():
    """Get academy lessons with optional filters."""
    category = request.args.get("category")
    difficulty = request.args.get("difficulty")
    limit = min(request.args.get("limit", 50, type=int), 100)
    lessons = db.get_academy_lessons(category=category, difficulty=difficulty, limit=limit)
    return jsonify({"success": True, "data": lessons})


@app.route("/api/academy/categories")
def api_academy_categories():
    """Get academy categories with lesson counts."""
    cats = db.get_academy_categories()
    return jsonify({"success": True, "data": cats})


# ---- v7: Admin Dashboard ----

@app.route("/admin")
def admin_page():
    """Admin Dashboard - password protected."""
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    # If no password set, allow access (development mode)
    if admin_password:
        session_auth = request.cookies.get("admin_auth")
        if session_auth != admin_password:
            return render_template("admin.html", authenticated=False)
    return render_template("admin.html", authenticated=True)


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    """Verify admin password and set auth cookie."""
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if admin_password and password == admin_password:
        resp = jsonify({"success": True})
        resp.set_cookie("admin_auth", admin_password, max_age=24 * 3600, httponly=True)
        return resp
    return jsonify({"success": False, "error": "Invalid password"}), 401


@app.route("/api/admin/dashboard")
def api_admin_dashboard():
    """Get comprehensive admin dashboard data."""
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if admin_password:
        session_auth = request.cookies.get("admin_auth")
        if session_auth != admin_password:
            return jsonify({"success": False, "error": "Unauthorized"}), 401

    stats = db.get_stats_dashboard()
    sources = db.get_sources()
    categories = db.get_categories()
    recent = db.get_latest_articles(limit=10)
    popular = db.get_popular_articles(limit=10)
    breaking = db.get_latest_articles(limit=5, category="breaking")

    return jsonify({
        "success": True,
        "data": {
            "stats": stats,
            "sources": sources,
            "categories": categories,
            "recent_articles": recent,
            "popular_articles": popular,
            "breaking_count": len(breaking),
        }
    })


# ---- v7: Crypto Facts & Quizzes ----

from crypto_facts import (
    get_facts, get_daily_fact, get_random_fact,
    get_quiz_questions, get_quiz_stats, get_fact_stats,
    FACT_CATEGORIES as FACT_CAT_LIST,
    QUIZ_DIFFICULTIES as QUIZ_DIFF_LIST,
    CRYPTO_FACTS as ALL_FACTS,
    QUIZ_QUESTIONS as ALL_QUIZ,
)


@app.route("/facts")
def facts_page():
    """Crypto Facts & Quizzes page."""
    quiz_cats = list(set(q["category"] for q in ALL_QUIZ))
    quiz_cats.sort()
    quiz_cat_list = [{"slug": "all", "name": "All", "icon": "fas fa-globe", "color": "#22d3ee"}]
    for cat in quiz_cats:
        cat_info = next((c for c in FACT_CAT_LIST if c["slug"] == cat), None)
        quiz_cat_list.append({
            "slug": cat,
            "name": cat_info["name"] if cat_info else cat.capitalize(),
            "icon": cat_info["icon"] if cat_info else "fas fa-tag",
            "color": cat_info["color"] if cat_info else "#94a3b8",
        })

    return render_template("facts.html",
                           fact_categories=FACT_CAT_LIST,
                           quiz_difficulties=QUIZ_DIFF_LIST,
                           quiz_categories=quiz_cat_list)


@app.route("/api/facts")
def api_facts_endpoint():
    """Get crypto facts with optional category filter."""
    category = request.args.get("category")
    limit = min(request.args.get("limit", 20, type=int), 50)
    facts = get_facts(category=category, limit=limit)
    return jsonify({"success": True, "data": facts})


@app.route("/api/facts/daily")
def api_daily_fact():
    """Get the fact of the day."""
    fact = get_daily_fact()
    return jsonify({"success": True, "data": fact})


@app.route("/api/facts/random")
def api_random_fact():
    """Get a random crypto fact."""
    category = request.args.get("category")
    fact = get_random_fact(category=category)
    if fact:
        return jsonify({"success": True, "data": fact})
    return jsonify({"success": False, "error": "No facts found"}), 404


@app.route("/api/facts/quiz")
def api_quiz():
    """Get quiz questions with optional filters."""
    difficulty = request.args.get("difficulty")
    category = request.args.get("category")
    limit = min(request.args.get("limit", 10, type=int), 20)
    questions = get_quiz_questions(difficulty=difficulty, category=category, limit=limit)
    return jsonify({"success": True, "data": questions})


@app.route("/api/facts/stats")
def api_facts_stats():
    """Get facts and quiz database statistics."""
    quiz_stats = get_quiz_stats()
    fact_stats = get_fact_stats()
    return jsonify({
        "success": True,
        "data": {
            "total_facts": fact_stats["total_facts"],
            "total_questions": quiz_stats["total_questions"],
            "categories": fact_stats["categories"],
            "difficulties": quiz_stats["difficulties"],
            "facts_by_category": fact_stats["categories"],
            "year_range": fact_stats["year_range"],
        }
    })


# ---- v6: Simple In-Memory Response Cache ----

_template_cache = {}
TEMPLATE_CACHE_TTL = 120  # 2 minutes for page renders

def cached_template(key_func, ttl=TEMPLATE_CACHE_TTL):
    """Decorator for simple in-memory template caching."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            now = time.time()
            cached = _template_cache.get(cache_key)
            if cached and now - cached[0] < ttl:
                return cached[1]
            result = f(*args, **kwargs)
            _template_cache[cache_key] = (now, result)
            # Limit cache size
            if len(_template_cache) > 500:
                oldest = min(_template_cache, key=lambda k: _template_cache[k][0])
                del _template_cache[oldest]
            return result
        return wrapper
    return decorator


# ---- Periodic Cleanup Thread ----

def _periodic_cleanup():
    """Background thread for periodic database cleanup."""
    logger.info("[Cleanup] Periodic cleanup thread started")
    while True:
        try:
            time.sleep(86400)  # Run once per day
            logger.info("[Cleanup] Running daily cleanup...")
            db.cleanup_fear_greed_history(keep_days=90)
            logger.info("[Cleanup] Daily cleanup completed")
        except Exception as e:
            logger.error(f"[Cleanup] Error: {e}")

cleanup_thread = threading.Thread(target=_periodic_cleanup, daemon=True)
cleanup_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
