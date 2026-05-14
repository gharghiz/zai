import logging
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

WHALE_ALERT_API_URL = "https://api.whale-alert.io/v1/transactions"
# Public demo key (rate limited)
WHALE_ALERT_API_KEY = ""  # User should set WHALE_ALERT_API_KEY env var


class WhaleAlertService:
    def __init__(self):
        self.api_key = WHALE_ALERT_API_KEY
        self.cache = []
        self.cache_time = 0
        self.cache_ttl = 300  # 5 minutes

    def fetch_transactions(self, min_value_usd=500000, limit=20) -> List[Dict[str, Any]]:
        """Fetch recent large crypto transactions (whale alerts)."""
        # If API key is set, use the real API
        if self.api_key:
            return self._fetch_from_api(min_value_usd, limit)
        else:
            # Fallback: generate demo data based on known large transactions
            return self._generate_demo_data(limit)

    def _fetch_from_api(self, min_value, limit):
        try:
            params = {
                "api_key": self.api_key,
                "min_value": min_value,
                "limit": limit,
                "start": int(time.time()) - 86400  # last 24h
            }
            resp = requests.get(WHALE_ALERT_API_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                transactions = []
                for tx in data.get("transactions", []):
                    transactions.append({
                        "id": tx.get("id"),
                        "tx_type": tx.get("type", "transfer"),
                        "blockchain": tx.get("blockchain", "unknown"),
                        "symbol": (tx.get("symbol") or "BTC").upper(),
                        "from_owner": self._truncate_address(tx.get("owner", "")),
                        "from_owner_type": tx.get("owner_type", "unknown"),
                        "to_owner": self._truncate_address(tx.get("to_owner", "")),
                        "to_owner_type": tx.get("to_owner_type", "unknown"),
                        "amount": tx.get("amount", 0),
                        "amount_usd": tx.get("amount_usd", 0),
                        "timestamp": datetime.utcfromtimestamp(tx.get("timestamp", time.time())).isoformat(),
                        "tx_hash": tx.get("hash", ""),
                    })
                return transactions
        except Exception as e:
            logger.error(f"Whale Alert API error: {e}")
        return []

    def _generate_demo_data(self, limit):
        """Generate realistic demo whale transaction data."""
        import random
        chains = ["bitcoin", "ethereum", "tron", "binance", "ripple", "solana"]
        symbols = ["BTC", "ETH", "TRX", "BNB", "XRP", "SOL", "USDT", "USDC", "WBTC", "DOGE"]
        owner_types = ["exchange", "wallet", "unknown"]
        exchanges = ["Binance", "Coinbase", "Kraken", "OKX", "Bitfinex", "Bybit", "Crypto.com", "Gemini"]

        transactions = []
        now = time.time()

        for i in range(limit):
            hours_ago = random.uniform(0, 24)
            symbol = random.choice(symbols)
            # Rough USD values
            usd_map = {"BTC": 68000, "ETH": 3700, "SOL": 170, "BNB": 600, "XRP": 0.55, "TRX": 0.12, "USDT": 1, "USDC": 1, "WBTC": 68000, "DOGE": 0.16}
            price = usd_map.get(symbol, 100)
            amount = random.uniform(100, 10000) if symbol in ["BTC", "ETH", "SOL", "BNB", "WBTC"] else random.uniform(100000, 50000000)
            amount_usd = amount * price

            from_owner = random.choice(exchanges) if random.random() > 0.3 else self._random_addr()
            to_owner = random.choice(exchanges) if random.random() > 0.3 else self._random_addr()

            transactions.append({
                "id": f"demo_{i}_{int(now)}",
                "tx_type": "transfer",
                "blockchain": random.choice(chains),
                "symbol": symbol,
                "from_owner": from_owner,
                "from_owner_type": "exchange" if from_owner in exchanges else "wallet",
                "to_owner": to_owner,
                "to_owner_type": "exchange" if to_owner in exchanges else "wallet",
                "amount": round(amount, 4),
                "amount_usd": round(amount_usd, 2),
                "timestamp": datetime.utcfromtimestamp(now - hours_ago * 3600).isoformat(),
                "tx_hash": f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
            })

        # Sort by value descending
        transactions.sort(key=lambda x: x["amount_usd"], reverse=True)
        return transactions

    def _truncate_address(self, addr):
        if not addr or len(addr) < 12:
            return addr or "Unknown"
        return addr[:6] + "..." + addr[-4:]

    def _random_addr(self):
        import random, string
        return "0x" + "".join(random.choices(string.hexdigits.lower(), k=40))

    def get_cached_transactions(self, min_value_usd=500000, limit=20):
        """Get transactions with caching."""
        now = time.time()
        if now - self.cache_time > self.cache_ttl:
            self.cache = self.fetch_transactions(min_value_usd, limit)
            self.cache_time = now
        return self.cache

    def get_stats(self):
        """Get summary statistics."""
        txs = self.get_cached_transactions(limit=50)
        if not txs:
            return {"total_volume_24h": 0, "total_transactions": 0, "top_blockchain": "N/A", "avg_transaction_usd": 0}

        total_vol = sum(tx["amount_usd"] for tx in txs)
        chain_counts = {}
        for tx in txs:
            chain_counts[tx["blockchain"]] = chain_counts.get(tx["blockchain"], 0) + 1
        top_chain = max(chain_counts, key=chain_counts.get) if chain_counts else "N/A"

        return {
            "total_volume_24h": round(total_vol, 2),
            "total_transactions": len(txs),
            "top_blockchain": top_chain,
            "avg_transaction_usd": round(total_vol / len(txs), 2) if txs else 0,
        }
