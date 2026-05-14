import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from config import MIN_SENTIMENT_SCORE, AI_SUMMARY_MAX_LENGTH
from ai import AIService

logger = logging.getLogger(__name__)


class Processor:
    """Article processor - filtering, deduplication, and AI processing."""

    # Category keywords mapping
    CATEGORY_KEYWORDS = {
        "Bitcoin": ["bitcoin", "btc", "satoshi", "lightning network", "taproot"],
        "Ethereum": ["ethereum", "eth", "vitalik", "solidity", "erc-", "defi", "de-fi", "uniswap", "aave", "lido", "makerdao", "staking"],
        "Altcoins": ["altcoin", "altcoins", "xrp", "ripple", "solana", "sol", "cardano", "ada", "dogecoin", "doge", "shiba", "shib", "polkadot", "dot", "avalanche", "avax", "chainlink", "link", "polygon", "matic", "near protocol", "cosmos", "atom"],
        "DeFi": ["defi", "de-fi", "decentralized finance", "yield farming", "liquidity pool", "amm", "dex", "lending protocol", "borrowing protocol"],
        "NFT": ["nft", "nfts", "non-fungible", "opensea", "digital art", "minting", "collection", "floor price"],
        "Regulation": ["regulation", "regulatory", "sec", "cftc", "compliance", "lawsuit", "sanction", "ban crypto", "crypto ban", "legal", "court", "legislation", "eu crypto", "mia"],
        "Mining": ["mining", "miner", "hash rate", "hashrate", "proof of work", "pow", "asic", "bitcoin mining", "pool", "difficulty"],
        "Trading": ["trading", "trader", "exchange", "binance", "coinbase", "kraken", "futures", "options", "leverage", "margin", "spot", "order book", "whale", "bullish", "bearish", "support", "resistance"],
        "Technology": ["blockchain", "smart contract", "layer 2", "l2", "scaling", "zk-rollup", "rollup", "zk-snark", "sharding", "consensus", "proof of stake", "pos", "node", "protocol", "upgrade", "fork", "hard fork", "soft fork"],
        "Web3": ["web3", "web 3", "metaverse", "dao", "dapp", "dapps", "decentralized", "token", "tokenization", "airdrop", "ido", "ico", "ieo"],
    }

    def __init__(self, db=None, ai_service=None):
        self.db = db
        self.ai_service = ai_service or AIService()

    def process_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of scraped articles."""
        logger.info(f"Processing {len(articles)} articles")

        # Filter and deduplicate
        filtered = self._filter_articles(articles)
        logger.info(f"After filtering: {len(filtered)} articles")

        # AI processing
        processed = []
        for article in filtered:
            try:
                processed_article = self._process_single(article)
                if processed_article:
                    processed.append(processed_article)
            except Exception as e:
                logger.error(f"Error processing article '{article.get('title', '')}': {e}")

        logger.info(f"Successfully processed: {len(processed)} articles")
        return processed

    def _filter_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out duplicates and low-quality articles."""
        unique = []
        seen_urls = set()
        seen_titles = set()

        for article in articles:
            url = article.get("url", "")
            title = article.get("title", "").lower().strip()

            # Skip duplicates by URL
            if url in seen_urls:
                continue

            # Skip very similar titles
            title_hash = self._simple_hash(title)
            if title_hash in seen_titles:
                continue

            # Skip very short titles
            if len(title) < 15:
                continue

            # Skip articles without meaningful content
            if not article.get("content") and not article.get("summary"):
                if len(title) < 50:
                    continue

            seen_urls.add(url)
            seen_titles.add(title_hash)
            unique.append(article)

        return unique

    def _simple_hash(self, text: str) -> str:
        """Create a simple hash for deduplication."""
        import hashlib
        text = "".join(c for c in text if c.isalnum())
        return hashlib.md5(text.encode()).hexdigest()[:12]

    def detect_category(self, title: str, content: str) -> str:
        """Detect article category based on keyword matching."""
        text = f"{title} {content}".lower()
        best_category = "news"
        best_score = 0

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > best_score:
                best_score = score
                best_category = category

        return best_category

    def _process_single(self, article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single article with AI."""
        title = article.get("title", "")
        content = article.get("content", "")

        if not content:
            content = title

        # Detect category
        article["category"] = self.detect_category(title, content)

        # Generate AI summary and sentiment
        ai_result = self.ai_service.analyze_article(title, content)

        if ai_result:
            article["summary"] = ai_result.get("summary", "")
            article["sentiment_score"] = ai_result.get("sentiment_score", 0.0)
            article["sentiment_label"] = ai_result.get("sentiment_label", "neutral")
            article["keywords"] = ai_result.get("keywords", [])
            article["ai_insights"] = ai_result.get("insights", "")

            logger.info(f"AI processed: '{title[:50]}...' | Sentiment: {article['sentiment_label']} ({article['sentiment_score']:.2f})")
            return article

        # Fallback without AI
        article["summary"] = title
        article["sentiment_score"] = 0.0
        article["sentiment_label"] = "neutral"
        article["keywords"] = []
        article["ai_insights"] = ""
        return article

    def save_articles(self, articles: List[Dict[str, Any]]) -> int:
        """Save processed articles to database."""
        if not self.db:
            logger.error("Database not initialized")
            return 0

        saved_count = 0
        for article in articles:
            # Check if already exists
            if self.db.article_exists(article["url"]):
                logger.debug(f"Article already exists: {article['url']}")
                continue

            # Insert article
            article_id = self.db.insert_article(article)
            if article_id:
                # Update with AI data
                self.db.update_article_ai(
                    article_id=article_id,
                    summary=article.get("summary", ""),
                    sentiment_score=article.get("sentiment_score", 0.0),
                    sentiment_label=article.get("sentiment_label", "neutral"),
                    keywords=article.get("keywords", []),
                    ai_insights=article.get("ai_insights", "")
                )
                saved_count += 1

        # Update stats
        if saved_count > 0:
            self.db.update_bot_stats(scraped=saved_count, ai_summaries=saved_count)

        return saved_count

    def get_top_articles(self, articles: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top articles sorted by sentiment score."""
        sorted_articles = sorted(
            articles,
            key=lambda x: x.get("sentiment_score", 0),
            reverse=True
        )
        return sorted_articles[:limit]

    def filter_by_sentiment(self, articles: List[Dict[str, Any]],
                            min_score: float = None) -> List[Dict[str, Any]]:
        """Filter articles by minimum sentiment score."""
        if min_score is None:
            min_score = MIN_SENTIMENT_SCORE

        return [
            article for article in articles
            if article.get("sentiment_score", 0) >= min_score
        ]
