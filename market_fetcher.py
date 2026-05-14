import logging
import time
import threading
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# CoinGecko Free API
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# Rate limiting: 1 request per 15 seconds to stay within CoinGecko free tier limits
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 15
_rate_lock = threading.Lock()


def _rate_limited_get(url: str, params: dict = None, timeout: int = 15) -> Optional[requests.Response]:
    """Make a rate-limited GET request (thread-safe)."""
    global _last_request_time
    with _rate_lock:
        now = time.time()
        elapsed = now - _last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            wait = _MIN_REQUEST_INTERVAL - elapsed
            logger.info(f"Rate limiting: waiting {wait:.0f}s before next CoinGecko request")
            time.sleep(wait)
        _last_request_time = time.time()
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        if resp.status_code == 429:
            logger.warning("CoinGecko rate limited (429). Waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)

        resp.raise_for_status()
        return resp
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 429:
            logger.error("CoinGecko rate limited even after retry. Skipping.")
        else:
            logger.error(f"CoinGecko HTTP error: {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error("CoinGecko API timeout")
        return None
    except Exception as e:
        logger.error(f"CoinGecko request error: {e}")
        return None


def get_coin_prices(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch top coins with live prices from CoinGecko."""
    resp = _rate_limited_get(
        f"{COINGECKO_BASE}/coins/markets",
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": limit,
            "page": 1,
            "sparkline": "false",
            "price_change_percentage": "24h,7d",
        }
    )
    if not resp:
        return []

    try:
        data = resp.json()
        coins = []
        for c in data:
            coins.append({
                "id": c.get("id"),
                "symbol": c.get("symbol", "").upper(),
                "name": c.get("name"),
                "image": c.get("image", ""),
                "price": c.get("current_price", 0),
                "change_24h": c.get("price_change_percentage_24h", 0),
                "change_7d": (c.get("price_change_percentage_7d_in_currency") or
                              c.get("price_change_percentage_7d", 0)),
                "market_cap": c.get("market_cap", 0),
                "volume_24h": c.get("total_volume", 0),
                "rank": c.get("market_cap_rank", 0),
                "high_24h": c.get("high_24h", 0),
                "low_24h": c.get("low_24h", 0),
                "ath": c.get("ath", 0),
                "ath_change_percentage": c.get("ath_change_percentage", 0),
                "circulating_supply": c.get("circulating_supply", 0),
                "total_supply": c.get("total_supply"),
                "max_supply": c.get("max_supply"),
            })
        logger.info(f"Fetched {len(coins)} coin prices from CoinGecko")
        return coins
    except Exception as e:
        logger.error(f"Error parsing coin prices: {e}")
        return []


def get_trending_coins() -> List[Dict[str, Any]]:
    """Fetch trending coins from CoinGecko with USD prices."""
    resp = _rate_limited_get(f"{COINGECKO_BASE}/search/trending", timeout=10)
    if not resp:
        return []

    try:
        data = resp.json()
        trending = []
        coin_ids = []

        for item in data.get("coins", []):
            coin = item.get("item", {})
            coin_id = coin.get("id")
            coin_ids.append(coin_id)
            trending.append({
                "id": coin_id,
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "image": coin.get("small", coin.get("thumb", "")),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc", 0),
                "score": coin.get("score", 0),
                "price": 0,
                "change_24h": 0,
            })

        # Fetch USD prices and 24h change for all trending coins in one call
        if coin_ids:
            price_resp = _rate_limited_get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": ",".join(coin_ids),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                },
                timeout=10
            )
            if price_resp:
                price_data = price_resp.json()
                for t in trending:
                    coin_data = price_data.get(t["id"], {})
                    if coin_data:
                        t["price"] = coin_data.get("usd", 0)
                        t["change_24h"] = coin_data.get("usd_24h_change", 0)

        logger.info(f"Fetched {len(trending)} trending coins with prices from CoinGecko")
        return trending
    except Exception as e:
        logger.error(f"Error parsing trending coins: {e}")
        return []


def get_fear_greed_index() -> Optional[Dict[str, Any]]:
    """Fetch Fear & Greed Index from Alternative.me API (no rate limit issues)."""
    try:
        resp = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data"):
            item = data["data"][0]
            return {
                "value": int(item.get("value", 50)),
                "classification": item.get("value_classification", "Neutral"),
                "timestamp": datetime.utcfromtimestamp(int(item.get("timestamp", 0))),
            }
    except Exception as e:
        logger.error(f"Error fetching fear/greed index: {e}")
    return None


def get_global_crypto_data() -> Optional[Dict[str, Any]]:
    """Fetch global crypto market data."""
    resp = _rate_limited_get(f"{COINGECKO_BASE}/global", timeout=10)
    if not resp:
        return None

    try:
        data = resp.json().get("data", {})
        return {
            "total_market_cap_usd": data.get("total_market_cap", {}).get("usd", 0),
            "total_volume_usd": data.get("total_volume", {}).get("usd", 0),
            "market_cap_change_24h": data.get("market_cap_change_percentage_24h_usd", 0),
            "active_cryptocurrencies": data.get("active_cryptocurrencies", 0),
            "btc_dominance": data.get("market_cap_percentage", {}).get("btc", 0),
            "eth_dominance": data.get("market_cap_percentage", {}).get("eth", 0),
        }
    except Exception as e:
        logger.error(f"Error parsing global data: {e}")
        return None


def search_coins(query: str) -> List[Dict[str, Any]]:
    """Search for coins by name or symbol."""
    resp = _rate_limited_get(f"{COINGECKO_BASE}/search", params={"query": query}, timeout=10)
    if not resp:
        return []

    try:
        data = resp.json()
        coins = []
        for item in data.get("coins", [])[:10]:
            coins.append({
                "id": item.get("id"),
                "symbol": item.get("symbol", "").upper(),
                "name": item.get("name"),
                "image": item.get("thumb", ""),
                "market_cap_rank": item.get("market_cap_rank"),
            })
        return coins
    except Exception as e:
        logger.error(f"Error parsing search results: {e}")
        return []
