import logging
import json
import re
from typing import Dict, Any, Optional, List

from config import OPENAI_API_KEY, OPENAI_MODEL, AI_SUMMARY_MAX_LENGTH, CRYPTO_KEYWORDS

logger = logging.getLogger(__name__)

# Bullish / Bearish word lists for local sentiment analysis
BULLISH_WORDS = [
    "surge", "soar", "rally", "bullish", "gain", "profit", "growth", "adopt",
    "breakthrough", "upgrade", "launch", "partner", "approval", " ATH ", "all-time high",
    "bull run", "moon", "pump", "recover", "bounce", "accumulate", "institutional",
    "etf approved", "mainnet launch", "positive", "optimistic", "confidence", "innovation",
    "increase", "rise", "jump", "climb", "outperform", "exceed", "beat", "record",
    "success", "milestone", "achievement", "expansion", "integration", "support",
    "buy", "buying", "invest", "investment", "funded", "backed"
]

BEARISH_WORDS = [
    "crash", "drop", "fall", "plunge", "bearish", "loss", "decline", "ban", "hack",
    "exploit", "fraud", "scam", "rug pull", "bankrupt", "collapse", "sell-off",
    "dump", "correction", "recession", "risk", "warning", "fear", "panic",
    "regulation", "sec sue", "lawsuit", "investigation", "fine", "penalty",
    "negative", "pessimistic", "concern", "volatile", "uncertainty", "downturn",
    "decrease", "slump", "slide", "retreat", "underperform", "miss", "fail",
    "shut down", "freeze", "halt", "suspend", "restrict", "prohibit",
    "sell", "selling", "liquidation", "margin call", "bear market"
]


class AIService:
    """Article analysis with OpenAI AI (when available) or local fallback."""

    def __init__(self):
        self.client = None
        self.model = OPENAI_MODEL
        self._openai_disabled_logged = False  # Prevent repeated "unreachable" logs
        if OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                logger.info(f"AI service initialized with OpenAI: {self.model}")
            except TypeError as e:
                logger.warning(f"OpenAI init failed (version/proxy issue), using local analysis")
                self._openai_disabled_logged = True
            except Exception as e:
                logger.warning(f"OpenAI init failed, using local analysis: {e}")
                self._openai_disabled_logged = True
        else:
            logger.info("No OpenAI API key — using local text analysis")

    def analyze_article(self, title: str, content: str) -> Dict[str, Any]:
        """Analyze article: use OpenAI if available, else local analysis."""
        if self.client:
            result = self._analyze_with_openai(title, content)
            if result:
                return result
            # OpenAI failed — client was set to None inside _analyze_with_openai

        return self._analyze_local(title, content)

    def _analyze_with_openai(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """Use OpenAI GPT for analysis."""
        try:
            truncated = content[:3000]
            prompt = f"""Analyze this crypto news article.

Title: {title}
Content: {truncated}

JSON response only:
- "summary": under {AI_SUMMARY_MAX_LENGTH} chars
- "sentiment_score": float -1.0 to 1.0
- "sentiment_label": "very_bearish" / "bearish" / "neutral" / "bullish" / "very_bullish"
- "keywords": array of 3-8 crypto keywords
- "insights": 1-2 sentences"""

            kwargs = dict(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crypto analyst. JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            # Try with response_format first (not all models support it)
            try:
                kwargs["response_format"] = {"type": "json_object"}
                response = self.client.chat.completions.create(**kwargs)
            except Exception:
                kwargs.pop("response_format", None)
                response = self.client.chat.completions.create(**kwargs)

            raw_content = response.choices[0].message.content.strip()
            # Extract JSON from response (handle cases where model wraps in markdown)
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                raw_content = json_match.group(0)
            result = json.loads(raw_content)
            score = max(-1.0, min(1.0, float(result.get("sentiment_score", 0))))
            label = result.get("sentiment_label", "neutral")
            if label not in ["very_bearish", "bearish", "neutral", "bullish", "very_bullish"]:
                label = self._score_to_label(score)
            keywords = result.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",")]

            return {
                "summary": result.get("summary", title)[:AI_SUMMARY_MAX_LENGTH],
                "sentiment_score": score,
                "sentiment_label": label,
                "keywords": keywords[:8],
                "insights": result.get("insights", "")
            }
        except Exception as e:
            err_str = str(e).lower()
            if "connection" in err_str or "timeout" in err_str or "network" in err_str:
                self.client = None
                if not self._openai_disabled_logged:
                    logger.warning("OpenAI unreachable — disabling, using local analysis")
                    self._openai_disabled_logged = True
            else:
                logger.error(f"OpenAI analysis error: {e}")
            return None

    def _analyze_local(self, title: str, content: str) -> Dict[str, Any]:
        """Local keyword-based analysis when OpenAI is not available."""
        text = f"{title} {content}".lower()

        # Sentiment scoring
        bullish_count = sum(1 for w in BULLISH_WORDS if w.lower() in text)
        bearish_count = sum(1 for w in BEARISH_WORDS if w.lower() in text)
        total = bullish_count + bearish_count

        if total > 0:
            score = (bullish_count - bearish_count) / total
        else:
            score = 0.0

        score = round(max(-1.0, min(1.0, score)), 2)
        label = self._score_to_label(score)

        # Keywords extraction
        keywords = []
        text_lower = text
        for kw in CRYPTO_KEYWORDS:
            if kw.lower() in text_lower and kw.lower() not in [k.lower() for k in keywords]:
                keywords.append(kw)
                if len(keywords) >= 6:
                    break

        # Simple summary: use title or first sentence of content
        summary = title
        if content:
            sentences = re.split(r'[.!?]', content)
            for s in sentences:
                s = s.strip()
                if len(s) > 40 and len(s) < AI_SUMMARY_MAX_LENGTH:
                    summary = s
                    break
        summary = summary[:AI_SUMMARY_MAX_LENGTH]

        # Simple insight
        if bullish_count > bearish_count + 1:
            insight = f"Positive sentiment detected — {bullish_count} bullish signals vs {bearish_count} bearish."
        elif bearish_count > bullish_count + 1:
            insight = f"Caution: {bearish_count} bearish signals detected vs {bullish_count} bullish."
        else:
            insight = "Mixed sentiment — no strong directional bias detected."

        return {
            "summary": summary,
            "sentiment_score": score,
            "sentiment_label": label,
            "keywords": keywords,
            "insights": insight
        }

    def _score_to_label(self, score: float) -> str:
        if score < -0.5:
            return "very_bearish"
        elif score < -0.15:
            return "bearish"
        elif score > 0.5:
            return "very_bullish"
        elif score > 0.15:
            return "bullish"
        return "neutral"

    def generate_market_insight(self, articles: list) -> Optional[str]:
        if not self.client:
            return None
        try:
            lines = [f"- [{a.get('source','?')}] {a.get('title','')} ({a.get('sentiment_label','neutral')})" for a in articles[:10]]
            prompt = f"Based on these articles:\n{chr(10).join(lines)}\n\n2-3 sentence market overview."
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "You are a crypto market analyst."}, {"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            if "connection" in err_str or "timeout" in err_str or "network" in err_str:
                self.client = None
                if not self._openai_disabled_logged:
                    logger.warning("OpenAI unreachable — using local analysis")
                    self._openai_disabled_logged = True
            else:
                logger.error(f"Market insight error: {e}")
            return None

    def generate_daily_summary(self, articles: list) -> Optional[str]:
        if not self.client:
            return None
        try:
            bullish = [a for a in articles if a.get("sentiment_label") in ["bullish", "very_bullish"]]
            bearish = [a for a in articles if a.get("sentiment_label") in ["bearish", "very_bearish"]]
            prompt = f"""Daily crypto summary: {len(articles)} articles, {len(bullish)} bullish, {len(bearish)} bearish.
Bearish: {chr(10).join(f'- {a.get("title","")} ({a.get("source","")})' for a in bearish[:5])}
Bullish: {chr(10).join(f'- {a.get("title","")} ({a.get("source","")})' for a in bullish[:5])}
Write 3-4 paragraph summary."""
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": "You are a crypto analyst."}, {"role": "user", "content": prompt}],
                temperature=0.5, max_tokens=800
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            if "connection" in err_str or "timeout" in err_str or "network" in err_str:
                self.client = None
                if not self._openai_disabled_logged:
                    logger.warning("OpenAI unreachable — using local analysis")
                    self._openai_disabled_logged = True
            else:
                logger.error(f"Daily summary error: {e}")
            return None

    def summarize_for_telegram(self, title: str, content: str, summary: str = "",
                                  sentiment_label: str = "neutral", insights: str = "") -> str:
        """Generate a Telegram-optimized summary for long articles.

        For long articles, extracts 3-5 key bullet points and creates a concise
        Telegram-friendly summary that preserves the core message without distortion.

        Returns:
            A formatted summary string optimized for Telegram (HTML).
        """
        # If we already have a good AI summary, use it
        if summary and len(summary) >= 50:
            # Enhance the existing summary with key points from content
            bullet_points = self._extract_key_points(content, title, max_points=4)
            if bullet_points:
                formatted_points = "\n".join(f"  ▸ {p}" for p in bullet_points)
                return f"{summary}\n\n<b>Key Points:</b>\n{formatted_points}"
            return summary

        # Try OpenAI for smart summarization
        if self.client:
            result = self._ai_telegram_summary(title, content)
            if result:
                return result

        # Local fallback: extract key points
        return self._local_telegram_summary(title, content)

    def _ai_telegram_summary(self, title: str, content: str) -> Optional[str]:
        """Use OpenAI to generate a Telegram-optimized summary."""
        try:
            truncated = content[:4000]
            prompt = f"""Summarize this crypto news article for a Telegram channel.

Title: {title}
Content: {truncated}

Requirements:
- Start with a 2-3 sentence summary (under 150 words)
- Then list 3-5 key bullet points with "▸" prefix
- Keep the tone professional and informative
- Do NOT distort or misrepresent the original content
- Focus on facts, numbers, and key developments
- Output in plain text (no markdown, no bold/italic tags)

Format:
[2-3 sentence summary]

Key Points:
▸ [point 1]
▸ [point 2]
▸ [point 3]"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a crypto news editor. Summarize accurately without distortion."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )

            result = response.choices[0].message.content.strip()
            # Clean up any markdown artifacts
            result = result.replace('**', '').replace('##', '').replace('*', '')
            return result

        except Exception as e:
            err_str = str(e).lower()
            if "connection" in err_str or "timeout" in err_str or "network" in err_str:
                self.client = None
                if not self._openai_disabled_logged:
                    logger.warning("OpenAI unreachable — using local summary")
                    self._openai_disabled_logged = True
            else:
                logger.error(f"AI telegram summary error: {e}")
            return None

    def _extract_key_points(self, content: str, title: str, max_points: int = 4) -> List[str]:
        """Extract key bullet points from article content using local NLP."""
        if not content:
            return []

        import re

        # Clean HTML if present
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()

        # Split into sentences (handle decimal numbers properly)
        # Split on period/exclamation/question mark followed by space or end of string
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        if not sentences:
            return []

        # Score sentences by importance
        scored = []
        title_lower = title.lower()

        # Important crypto-specific terms that signal key information
        important_terms = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'price', 'market', 'percent', '%',
            'billion', 'million', 'announced', 'launched', 'approved', 'rejected',
            'partnership', 'acquisition', 'investment', 'funded', 'hack', 'exploit',
            'sec', 'regulation', 'etf', 'halving', 'mainnet', 'upgrade', 'fork',
            'revenue', 'profit', 'loss', 'surge', 'plunge', 'rally', 'crash',
            'record', 'all-time high', 'ath', 'airdrop', 'staking', 'yield',
            'trillion', 'dollar', '$', 'volatility', 'adoption', 'ban', 'legal',
        ]

        for sentence in sentences:
            score = 0
            s_lower = sentence.lower()

            # Position score: first sentences are usually more important
            idx = sentences.index(sentence)
            if idx < 3:
                score += 3
            elif idx < 8:
                score += 1

            # Contains numbers (prices, percentages, dates)
            if re.search(r'\d+\.?\d*%|\$\d+|\d+\s*(billion|million|trillion)', s_lower):
                score += 3

            # Contains important crypto terms
            term_count = sum(1 for term in important_terms if term in s_lower)
            score += term_count * 2

            # Sentence length score (medium sentences are usually best)
            word_count = len(sentence.split())
            if 10 <= word_count <= 30:
                score += 2
            elif 5 <= word_count < 10:
                score += 1

            # Avoid very long sentences for bullet points
            if word_count > 40:
                score -= 1

            # Avoid sentences that start with weak words
            weak_starts = ['however', 'although', 'while', 'despite', 'according to']
            if any(s_lower.startswith(w) for w in weak_starts):
                score -= 1

            scored.append((sentence.strip(), score))

        # Sort by score and pick top points
        scored.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate similar sentences
        selected = []
        for sentence, score in scored:
            if score <= 0:
                break
            # Check if too similar to already selected
            is_similar = False
            for sel in selected:
                common_words = set(sentence.lower().split()) & set(sel.lower().split())
                if len(common_words) > len(sentence.split()) * 0.6:
                    is_similar = True
                    break
            if not is_similar:
                # Truncate long sentences for bullet points
                words = sentence.split()
                if len(words) > 25:
                    sentence = ' '.join(words[:25]) + '...'
                selected.append(sentence)
            if len(selected) >= max_points:
                break

        # Sort selected points by their original order in the article
        selected_with_idx = []
        for sentence in selected:
            for i, orig in enumerate(sentences):
                if sentence.startswith(orig.strip()[:15]):
                    selected_with_idx.append((i, sentence))
                    break
            else:
                selected_with_idx.append((999, sentence))

        selected_with_idx.sort(key=lambda x: x[0])
        return [s for _, s in selected_with_idx]

    def _local_telegram_summary(self, title: str, content: str) -> str:
        """Generate a local Telegram-optimized summary without AI."""
        import re

        # Clean HTML
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()

        # Split into sentences (handle decimal numbers properly)
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        if not sentences:
            return title

        # Take first 2-3 sentences as summary
        summary_sentences = sentences[:3]
        summary = '. '.join(summary_sentences)
        if len(summary) > 300:
            summary = summary[:297] + '...'

        # Extract key points
        key_points = self._extract_key_points(content, title, max_points=3)

        if key_points:
            formatted_points = "\n".join(f"  ▸ {p}" for p in key_points)
            return f"{summary}.\n\n<b>Key Points:</b>\n{formatted_points}"

        return summary + '.'

    def is_available(self) -> bool:
        """Check if the AI service is available (always True due to local fallback)."""
        return True

    def is_openai_available(self) -> bool:
        """Check if OpenAI client is configured and reachable."""
        return self.client is not None
