import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///crypto_news.db")
DB_TYPE = "postgresql" if "postgresql" in DATABASE_URL or "postgres" in DATABASE_URL else "sqlite"

# Flask
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# Scraper
SCRAPER_INTERVAL = int(os.getenv("SCRAPER_INTERVAL", 60))  # 1 minute
MAX_ARTICLES_PER_FEED = int(os.getenv("MAX_ARTICLES_PER_FEED", 5))
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", 30))

# Processing
MIN_SENTIMENT_SCORE = float(os.getenv("MIN_SENTIMENT_SCORE", 0.3))
AI_SUMMARY_MAX_LENGTH = int(os.getenv("AI_SUMMARY_MAX_LENGTH", 200))

# Keywords for filtering
CRYPTO_KEYWORDS = [
    "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency",
    "blockchain", "defi", "nft", "token", "coin", "altcoin",
    "mining", "wallet", "exchange", "trading", "hodl",
    "binance", "coinbase", "solana", "sol", "cardano", "ada",
    "ripple", "xrp", "polkadot", "dot", "dogecoin", "doge",
    "avalanche", "avax", "polygon", "matic", "chainlink", "link",
    "litecoin", "ltc", "uniswap", "uni", "stablecoin", "tether",
    "usdt", "usdc", "cbdc", "web3", "dapp", "smart contract",
    "ico", "ieo", "ido", "airdrop", "staking", "yield",
    "liquidity", "market cap", "bullish", "bearish", "halving",
    "satoshi", "nakamoto", "decentralized", "fork", "mainnet",
    "testnet", "layer 2", "l2", "rollup", "sidechain",
    "fiat", "regulation", "sec", "cftc", "etf", "spot",
    "futures", "options", "derivative", "leverage", "margin",
    "arbitrage", "flash loan", "mev", "gas fee", "consensus",
    "proof of work", "proof of stake", "pos", "pow",
    "validator", "node", "mining pool", "hash rate",
    "private key", "seed phrase", "cold storage", "hardware wallet",
    "memecoin", "pepe", "shiba", "floki", "bonk",
    "ai", "artificial intelligence", "machine learning",
    "regex", "quantum", "oracle"
]

# RSS Feeds
RSS_FEEDS = [
    # Major Crypto News
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outfeeds/rss/", "category": "news"},
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss", "category": "news"},
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/.rss/full/", "category": "bitcoin"},
    {"name": "Crypto Briefing", "url": "https://cryptobriefing.com/feed/", "category": "news"},
    {"name": "Crypto Briefs", "url": "https://cryptobriefs.com/feed/", "category": "news"},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "category": "news"},
    {"name": "CryptoSlate", "url": "https://cryptoslate.com/feed/", "category": "news"},
    {"name": "Bitcoinist", "url": "https://bitcoinist.com/feed/", "category": "bitcoin"},
    {"name": "NewsBTC", "url": "https://www.newsbtc.com/feed/", "category": "news"},
    {"name": "CryptoPotato", "url": "https://cryptopotato.com/feed/", "category": "news"},
    {"name": "U.Today", "url": "https://u.today/rss", "category": "news"},
    {"name": "BeInCrypto", "url": "https://beincrypto.com/feed/", "category": "news"},
    {"name": "AMB Crypto", "url": "https://ambcrypto.com/feed/", "category": "news"},
    {"name": "CoinJournal", "url": "https://coinjournal.net/feed/", "category": "news"},
    {"name": "Blockworks", "url": "https://blockworks.co/feed", "category": "news"},
    {"name": "Crypto News AU", "url": "https://cryptonews.com.au/feed/", "category": "news"},
    {"name": "CryptoDaily", "url": "https://cryptodaily.co.uk/feed", "category": "news"},

    # Market Data & Analysis
    {"name": "CryptoGlobe", "url": "https://www.cryptoglobe.com/latest/rss.xml", "category": "market"},

    # DeFi
    {"name": "The Defiant", "url": "https://thedefiant.io/feed/", "category": "defi"},
    {"name": "Bankless", "url": "https://bankless.com/feed/", "category": "defi"},

    # Technology
    {"name": "Trustnodes", "url": "https://www.trustnodes.com/feed", "category": "technology"},

    # General Tech (crypto-related)
    {"name": "VentureBeat Crypto", "url": "https://venturebeat.com/category/security/feed/", "category": "tech"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "category": "tech"},
    {"name": "Crypto.news", "url": "https://www.crypto.news/rss/", "category": "news"},
    {"name": "NFT Evening", "url": "https://nftevening.com/feed/", "category": "nft"},
    {"name": "The Crypto Basic", "url": "https://thecryptobasic.com/feed/", "category": "news"},
    {"name": "Metaverse Post", "url": "https://metaversepost.com/feed/", "category": "news"},

    # Reddit
    {"name": "r/cryptocurrency", "url": "https://www.reddit.com/r/cryptocurrency/.rss", "category": "reddit"},
    {"name": "r/bitcoin", "url": "https://www.reddit.com/r/bitcoin/.rss", "category": "reddit"},
    {"name": "r/ethereum", "url": "https://www.reddit.com/r/ethereum/.rss", "category": "reddit"},
    {"name": "r/defi", "url": "https://www.reddit.com/r/defi/.rss", "category": "reddit"},
    {"name": "r/CryptoCurrency", "url": "https://www.reddit.com/r/CryptoCurrency/.rss", "category": "reddit"},

    # Arabic & International
    {"name": "CryptoSalam", "url": "https://cryptosalam.com/feed/", "category": "news"},
]

# Predefined Categories (displayed in navbar and news page)
CATEGORIES = [
    {"slug": "news", "name": "News", "icon": "fas fa-newspaper", "color": "#06b6d4"},
    {"slug": "bitcoin", "name": "Bitcoin", "icon": "fab fa-bitcoin", "color": "#f7931a"},
    {"slug": "ethereum", "name": "Ethereum", "icon": "fab fa-ethereum", "color": "#627eea"},
    {"slug": "altcoins", "name": "Altcoins", "icon": "fas fa-coins", "color": "#8b5cf6"},
    {"slug": "defi", "name": "DeFi", "icon": "fas fa-exchange-alt", "color": "#10b981"},
    {"slug": "nft", "name": "NFT & Gaming", "icon": "fas fa-palette", "color": "#ec4899"},
    {"slug": "trading", "name": "Trading", "icon": "fas fa-chart-line", "color": "#3b82f6"},
    {"slug": "mining", "name": "Mining", "icon": "fas fa-microchip", "color": "#f59e0b"},
    {"slug": "regulation", "name": "Regulation", "icon": "fas fa-gavel", "color": "#ef4444"},
    {"slug": "technology", "name": "Technology", "icon": "fas fa-cogs", "color": "#06b6d4"},
    {"slug": "web3", "name": "Web3 & DAOs", "icon": "fas fa-globe", "color": "#8b5cf6"},
]

# Telegram Bot Settings
BOT_RETRY_MAX = int(os.getenv("BOT_RETRY_MAX", 3))
BOT_RETRY_DELAY = int(os.getenv("BOT_RETRY_DELAY", 5))
BOT_POST_DELAY = int(os.getenv("BOT_POST_DELAY", 2))  # seconds between posts
BOT_MAX_MESSAGE_LENGTH = 4096

# Discord Webhook (optional - for notifications alongside Telegram)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
DISCORD_AVATAR_URL = os.getenv("DISCORD_AVATAR_URL", "")
DISCORD_USERNAME = os.getenv("DISCORD_USERNAME", "CryptositNews Bot")

# Notifications
NOTIFY_BREAKING_SENTIMENT_THRESHOLD = float(os.getenv("NOTIFY_BREAKING_SENTIMENT_THRESHOLD", "0.7"))
NOTIFY_BREAKING_KEYWORDS = ["hack", "exploit", "flash crash", "rug pull", "exchange halts", "sec approves", "etf approved", "bitcoin etf", "ethereum etf"]

# Caching
CACHE_CONTROL_STATIC = int(os.getenv("CACHE_CONTROL_STATIC", "3600"))  # 1 hour for static pages
CACHE_CONTROL_API = int(os.getenv("CACHE_CONTROL_API", "60"))  # 1 minute for API

# Whale Alerts
WHALE_ALERT_API_KEY = os.getenv("WHALE_ALERT_API_KEY", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================================
# New Settings (v7.0 Upgrade)
# ============================================================

# Version
VERSION = "7.0"

# Flask Secret Key (for session signing, CSRF protection, etc.)
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change-me-in-production-use-a-strong-random-string")

# Security Headers (applied to all HTTP responses)
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net; connect-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

# API Rate Limiting
API_RATE_LIMIT = {
    "enabled": os.getenv("API_RATE_LIMIT_ENABLED", "true").lower() == "true",
    "requests_per_minute": int(os.getenv("API_RATE_LIMIT_RPM", 60)),
    "requests_per_hour": int(os.getenv("API_RATE_LIMIT_RPH", 1000)),
    "burst_size": int(os.getenv("API_RATE_LIMIT_BURST", 10)),
}

# CORS Origins (comma-separated list or "*" for all)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# Cache Type (for Flask-Caching, future use)
CACHE_TYPE = os.getenv("CACHE_TYPE", "SimpleCache")

# Admin Dashboard Credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "changeme")

# Request Max Content Length (16 MB default)
REQUEST_MAX_CONTENT_LENGTH = int(os.getenv("REQUEST_MAX_CONTENT_LENGTH", 16 * 1024 * 1024))

# Pagination Defaults
PAGINATION_DEFAULTS = {
    "per_page": int(os.getenv("PAGINATION_PER_PAGE", 20)),
    "max_per_page": int(os.getenv("PAGINATION_MAX_PER_PAGE", 100)),
    "page_param": "page",
    "per_page_param": "per_page",
}
