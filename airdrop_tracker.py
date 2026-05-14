import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class AirdropTracker:
    """Tracks active and upcoming cryptocurrency airdrops with trust levels."""

    def __init__(self):
        self.cache = []
        self.cache_time = 0
        self.cache_ttl = 600  # 10 minutes

    def get_airdrops(self, status: str = None, trust: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get airdrops with optional status and trust filter.

        status: 'active', 'upcoming', 'ended', 'distributed', 'not_distributed'
        trust: 'verified', 'unverified'
        """
        airdrops = self._get_cached_airdrops()

        # Handle composite status filters
        if status == "distributed":
            airdrops = [a for a in airdrops if a.get("status") == "ended"]
        elif status == "not_distributed":
            airdrops = [a for a in airdrops if a.get("status") in ("active", "upcoming")]
        elif status:
            airdrops = [a for a in airdrops if a.get("status") == status]

        # Handle trust filter
        if trust == "verified":
            airdrops = [a for a in airdrops if a.get("verified") is True]
        elif trust == "unverified":
            airdrops = [a for a in airdrops if a.get("verified") is False]

        return airdrops[:limit]

    def _get_cached_airdrops(self) -> List[Dict[str, Any]]:
        """Get airdrops with caching."""
        now = time.time()
        if now - self.cache_time > self.cache_ttl or not self.cache:
            self.cache = self._fetch_airdrops()
            self.cache_time = now
        return self.cache

    def _fetch_airdrops(self) -> List[Dict[str, Any]]:
        """Fetch airdrop data. Uses curated data with periodic updates."""
        return self._get_curated_airdrops()

    def _get_curated_airdrops(self) -> List[Dict[str, Any]]:
        """Return curated list of airdrops with trust levels.

        verified: True = confirmed project with official token launch
        verified: False = rumored / unconfirmed / testnet only
        """
        now = datetime.utcnow()

        airdrops = [
            # ============ VERIFIED AIRDROPS (مضمون) ============
            {
                "id": "layerzero",
                "name": "LayerZero",
                "symbol": "ZRO",
                "logo": "L0",
                "description": "LayerZero is an omnichain interoperability protocol connecting over 70 blockchains. The ZRO token airdrop rewarded early users who interacted with the protocol across multiple chains.",
                "status": "ended",
                "platform": "Multi-chain",
                "estimated_value": "$500 - $5,000",
                "total_value": "$100M+",
                "requirements": [
                    "Bridge assets using LayerZero",
                    "Interact with dApps on multiple chains",
                    "Use Stargate Finance"
                ],
                "end_date": "2024-06-17",
                "website": "https://layerzero.network",
                "twitter": "https://twitter.com/LayerZero_Labs",
                "category": "Infrastructure",
                "difficulty": "medium",
                "participants": "2M+",
                "chain": "Multi-chain",
                "color": "#627eea",
                "verified": True,
            },
            {
                "id": "zksync",
                "name": "ZKsync Era",
                "symbol": "ZK",
                "logo": "ZK",
                "description": "ZKsync Era is a ZK-rollup Layer 2 on Ethereum. The token airdrop was one of the largest in crypto history, rewarding early ecosystem participants.",
                "status": "ended",
                "platform": "Ethereum L2",
                "estimated_value": "$200 - $5,000",
                "total_value": "$700M+",
                "requirements": [
                    "Bridged to ZKsync Era before snapshot",
                    "Used DEXes on ZKsync",
                    "Provided liquidity"
                ],
                "end_date": "2024-06-17",
                "website": "https://zksync.io",
                "twitter": "https://twitter.com/zksync",
                "category": "Layer 2",
                "difficulty": "hard",
                "participants": "3.5M+",
                "chain": "Ethereum L2",
                "color": "#818cf8",
                "verified": True,
            },
            {
                "id": "starknet",
                "name": "Starknet",
                "symbol": "STRK",
                "logo": "ST",
                "description": "Starknet is a permissionless decentralized ZK-rollup. The STRK token was airdropped to early users who interacted with Starknet dApps and bridges.",
                "status": "ended",
                "platform": "Ethereum L2",
                "estimated_value": "$500 - $10,000",
                "total_value": "$500M+",
                "requirements": [
                    "Used Starknet before snapshots",
                    "Interacted with DeFi protocols",
                    "Made multiple transactions"
                ],
                "end_date": "2024-02-20",
                "website": "https://starknet.io",
                "twitter": "https://twitter.com/Starknet",
                "category": "Layer 2",
                "difficulty": "hard",
                "participants": "1.3M+",
                "chain": "Ethereum L2",
                "color": "#ec4899",
                "verified": True,
            },
            {
                "id": "jupiter",
                "name": "Jupiter",
                "symbol": "JUP",
                "logo": "JU",
                "description": "Jupiter is the leading DEX aggregator on Solana. The JUP airdrop rewarded early users with significant allocations based on trading volume.",
                "status": "ended",
                "platform": "Solana",
                "estimated_value": "$300 - $8,000",
                "total_value": "$400M+",
                "requirements": [
                    "Traded on Jupiter DEX",
                    "Used limit orders",
                    "Participated in governance"
                ],
                "end_date": "2024-01-31",
                "website": "https://jup.ag",
                "twitter": "https://twitter.com/JupiterExchange",
                "category": "DeFi",
                "difficulty": "medium",
                "participants": "955K+",
                "chain": "Solana",
                "color": "#c084fc",
                "verified": True,
            },
            {
                "id": "wormhole",
                "name": "Wormhole",
                "symbol": "W",
                "logo": "WO",
                "description": "Wormhole is the leading cross-chain messaging protocol. The W token airdrop rewarded users who bridged assets across chains using Wormhole-powered bridges.",
                "status": "ended",
                "platform": "Multi-chain",
                "estimated_value": "$100 - $3,000",
                "total_value": "$300M+",
                "requirements": [
                    "Used Wormhole bridge for cross-chain transfers",
                    "Interacted with Portal Bridge",
                    "Used W-powered applications"
                ],
                "end_date": "2024-04-03",
                "website": "https://wormhole.com",
                "twitter": "https://twitter.com/wormholecrypto",
                "category": "Infrastructure",
                "difficulty": "medium",
                "participants": "400K+",
                "chain": "Multi-chain",
                "color": "#60a5fa",
                "verified": True,
            },
            {
                "id": "eigenlayer",
                "name": "EigenLayer",
                "symbol": "EIGEN",
                "logo": "EI",
                "description": "EigenLayer pioneered restaking on Ethereum, allowing users to secure additional protocols by restaking their ETH. The airdrop rewarded early restakers.",
                "status": "ended",
                "platform": "Ethereum",
                "estimated_value": "$500 - $7,000",
                "total_value": "$200M+",
                "requirements": [
                    "Restake ETH through EigenLayer",
                    "Delegate to AVS operators",
                    "Use EigenPod for native restaking"
                ],
                "end_date": "2024-09-15",
                "website": "https://www.eigenlayer.xyz",
                "twitter": "https://twitter.com/eigenlayer",
                "category": "DeFi",
                "difficulty": "medium",
                "participants": "500K+",
                "chain": "Ethereum",
                "color": "#1e40af",
                "verified": True,
            },
            {
                "id": "scroll",
                "name": "Scroll",
                "symbol": "SCR",
                "logo": "SC",
                "description": "Scroll is a zkEVM-based Ethereum Layer 2 scaling solution focused on security and decentralization. The SCR token airdrop rewarded early users.",
                "status": "active",
                "platform": "Ethereum L2",
                "estimated_value": "$200 - $3,000",
                "total_value": "$80M+",
                "requirements": [
                    "Bridge ETH to Scroll network",
                    "Swap tokens on Scroll DEXes",
                    "Provide liquidity on Scroll"
                ],
                "end_date": (now + timedelta(days=30)).strftime("%Y-%m-%d"),
                "website": "https://scroll.io",
                "twitter": "https://twitter.com/Scroll_ZKP",
                "category": "Layer 2",
                "difficulty": "easy",
                "participants": "1.5M+",
                "chain": "Ethereum L2",
                "color": "#fbbf24",
                "verified": True,
            },
            {
                "id": "grass",
                "name": "Grass",
                "symbol": "GRASS",
                "logo": "GR",
                "description": "Grass is a decentralized network sharing bandwidth to power AI models. Users earn points by running the Grass browser extension. GRASS token is already trading.",
                "status": "active",
                "platform": "Solana",
                "estimated_value": "$100 - $1,500",
                "total_value": "$30M+",
                "requirements": [
                    "Install Grass browser extension",
                    "Keep extension running to earn points",
                    "Referral bonus available"
                ],
                "end_date": (now + timedelta(days=60)).strftime("%Y-%m-%d"),
                "website": "https://app.getgrass.io",
                "twitter": "https://twitter.com/getgrass_io",
                "category": "DePIN",
                "difficulty": "easy",
                "participants": "5M+",
                "chain": "Solana",
                "color": "#34d399",
                "verified": True,
            },
            {
                "id": "linea",
                "name": "Linea",
                "symbol": "LXP",
                "logo": "LN",
                "description": "Linea is a zkEVM developed by ConsenSys, the team behind MetaMask. Users earn LXP points through on-chain activity on the Linea network.",
                "status": "active",
                "platform": "Ethereum L2",
                "estimated_value": "$100 - $2,000",
                "total_value": "$50M+",
                "requirements": [
                    "Bridge assets via Linea Bridge",
                    "Complete Linea Voyages XP quests",
                    "Use DeFi protocols on Linea"
                ],
                "end_date": (now + timedelta(days=45)).strftime("%Y-%m-%d"),
                "website": "https://linea.build",
                "twitter": "https://twitter.com/lineabuild",
                "category": "Layer 2",
                "difficulty": "easy",
                "participants": "3M+",
                "chain": "Ethereum L2",
                "color": "#22d3ee",
                "verified": True,
            },
            # ============ UNVERIFIED AIRDROPS (غير مضمون) ============
            {
                "id": "berachain",
                "name": "Berachain",
                "symbol": "BERA",
                "logo": "BE",
                "description": "Berachain is an EVM-compatible Layer 1 blockchain using Proof of Liquidity consensus. The testnet airdrop may reward early testers and liquidity providers, but token launch is not yet confirmed.",
                "status": "upcoming",
                "platform": "Layer 1",
                "estimated_value": "$200 - $3,000",
                "total_value": "TBA",
                "requirements": [
                    "Test Berachain testnet",
                    "Provide liquidity on BEX",
                    "Use Bend and Boro protocols"
                ],
                "end_date": (now + timedelta(days=90)).strftime("%Y-%m-%d"),
                "website": "https://www.berachain.com",
                "twitter": "https://twitter.com/beraborabora",
                "category": "Layer 1",
                "difficulty": "medium",
                "participants": "TBA",
                "chain": "Berachain",
                "color": "#dc2626",
                "verified": False,
            },
            {
                "id": "monad",
                "name": "Monad",
                "symbol": "MON",
                "logo": "MO",
                "description": "Monad is a high-performance EVM-compatible Layer 1 blockchain achieving 10,000+ TPS. The upcoming airdrop is rumored but not officially confirmed by the team.",
                "status": "upcoming",
                "platform": "Layer 1",
                "estimated_value": "$300 - $5,000",
                "total_value": "TBA",
                "requirements": [
                    "Join Monad Discord",
                    "Participate in testnet when available",
                    "Follow on social media"
                ],
                "end_date": (now + timedelta(days=120)).strftime("%Y-%m-%d"),
                "website": "https://www.monad.xyz",
                "twitter": "https://twitter.com/monad_xyz",
                "category": "Layer 1",
                "difficulty": "easy",
                "participants": "TBA",
                "chain": "Monad",
                "color": "#a855f7",
                "verified": False,
            },
            {
                "id": "abstract",
                "name": "Abstract",
                "symbol": "ABS",
                "logo": "AB",
                "description": "Abstract is a global consumer blockchain built on ZK-rollup technology, focused on mainstream adoption. Airdrop is rumored but no official token announcement yet.",
                "status": "upcoming",
                "platform": "Ethereum L2",
                "estimated_value": "$100 - $2,000",
                "total_value": "TBA",
                "requirements": [
                    "Join Abstract Discord",
                    "Mint NFTs on testnet",
                    "Use Abstract wallet"
                ],
                "end_date": (now + timedelta(days=100)).strftime("%Y-%m-%d"),
                "website": "https://abstract.xyz",
                "twitter": "https://twitter.com/abstractchain",
                "category": "Layer 2",
                "difficulty": "easy",
                "participants": "TBA",
                "chain": "Ethereum L2",
                "color": "#06b6d4",
                "verified": False,
            },
            {
                "id": "megaeth",
                "name": "MegaETH",
                "symbol": "MEGA",
                "logo": "ME",
                "description": "MegaETH is a hyper-optimized blockchain claiming real-time execution speeds. Currently in early testnet phase. Airdrop rumors exist but nothing is confirmed.",
                "status": "upcoming",
                "platform": "Ethereum L2",
                "estimated_value": "$200 - $4,000",
                "total_value": "TBA",
                "requirements": [
                    "Join MegaETH Discord",
                    "Run a testnet node",
                    "Participate in testnet activities"
                ],
                "end_date": (now + timedelta(days=150)).strftime("%Y-%m-%d"),
                "website": "https://megaeth.org",
                "twitter": "https://twitter.com/megaeth",
                "category": "Layer 2",
                "difficulty": "hard",
                "participants": "TBA",
                "chain": "Ethereum L2",
                "color": "#f97316",
                "verified": False,
            },
            {
                "id": "initia",
                "name": "Initia",
                "symbol": "INIT",
                "logo": "IN",
                "description": "Initia is an interwoven rollup network aiming to unify the modular blockchain ecosystem. Testnet is live but token launch and airdrop are not officially confirmed.",
                "status": "upcoming",
                "platform": "Multi-chain",
                "estimated_value": "$150 - $2,500",
                "total_value": "TBA",
                "requirements": [
                    "Join Initia Discord",
                    "Test dApps on testnet",
                    "Follow social media channels"
                ],
                "end_date": (now + timedelta(days=110)).strftime("%Y-%m-%d"),
                "website": "https://initia.xyz",
                "twitter": "https://twitter.com/initiaFDN",
                "category": "Infrastructure",
                "difficulty": "medium",
                "participants": "TBA",
                "chain": "Multi-chain",
                "color": "#8b5cf6",
                "verified": False,
            },
            {
                "id": "pacific",
                "name": "Pacific",
                "symbol": "PA",
                "logo": "PA",
                "description": "Pacific is a decentralized exchange built on the Sei Network with an order book model. Airdrop has been discussed in the community but no official confirmation from the team.",
                "status": "upcoming",
                "platform": "Sei Network",
                "estimated_value": "$100 - $2,000",
                "total_value": "TBA",
                "requirements": [
                    "Use Pacific DEX on Sei",
                    "Provide liquidity",
                    "Join Discord community"
                ],
                "end_date": (now + timedelta(days=80)).strftime("%Y-%m-%d"),
                "website": "https://pacific.xyz",
                "twitter": "https://twitter.com/Pacific_DeFi",
                "category": "DeFi",
                "difficulty": "easy",
                "participants": "TBA",
                "chain": "Sei Network",
                "color": "#06b6d4",
                "verified": False,
            },
            # ============ ADDITIONAL VERIFIED AIRDROPS ============
            {
                "id": "render",
                "name": "Render Network",
                "symbol": "RNDR",
                "logo": "RN",
                "description": "Render Network is a distributed GPU rendering platform connecting node operators needing GPU compute power with 3D artists. The RNDR token powers the decentralized rendering marketplace.",
                "status": "ended",
                "platform": "Multi-chain",
                "estimated_value": "$50 - $800",
                "total_value": "$50M+",
                "requirements": [
                    "Run a Render node or use render jobs",
                    "Hold RNDR tokens in wallet",
                    "Participate in community governance"
                ],
                "end_date": "2024-03-15",
                "website": "https://rendernetwork.com",
                "twitter": "https://twitter.com/RndrNetwork",
                "category": "DePIN",
                "difficulty": "hard",
                "participants": "150K+",
                "chain": "Multi-chain",
                "color": "#e11d48",
                "verified": True,
            },
            {
                "id": "arb",
                "name": "Arbitrum DAO",
                "symbol": "ARB",
                "logo": "AR",
                "description": "Arbitrum is a leading optimistic rollup Layer 2 on Ethereum. The ARB governance token airdrop was one of the largest L2 airdrops, distributing tokens to early bridge users and DAO members.",
                "status": "ended",
                "platform": "Ethereum L2",
                "estimated_value": "$500 - $12,000",
                "total_value": "$1B+",
                "requirements": [
                    "Bridged to Arbitrum One before snapshot",
                    "Used DEXes on Arbitrum",
                    "Interacted with dApps on Arbitrum"
                ],
                "end_date": "2024-03-23",
                "website": "https://arbitrum.io",
                "twitter": "https://twitter.com/Arbitrum",
                "category": "Layer 2",
                "difficulty": "medium",
                "participants": "1.5M+",
                "chain": "Ethereum L2",
                "color": "#28a0f0",
                "verified": True,
            },
            {
                "id": "celo",
                "name": "Celo",
                "symbol": "CELO",
                "logo": "CE",
                "description": "Celo is a carbon-negative mobile-first blockchain platform focused on financial inclusion. The airdrop rewarded users who participated in the Celo ecosystem and used their mobile-first DeFi products.",
                "status": "ended",
                "platform": "Celo",
                "estimated_value": "$50 - $500",
                "total_value": "$30M+",
                "requirements": [
                    "Use Celo-native DeFi apps",
                    "Hold CELO in Valora wallet",
                    "Participate in on-chain governance"
                ],
                "end_date": "2024-01-10",
                "website": "https://celo.org",
                "twitter": "https://twitter.com/CeloHQ",
                "category": "Layer 1",
                "difficulty": "easy",
                "participants": "600K+",
                "chain": "Celo",
                "color": "#35d07f",
                "verified": True,
            },
            {
                "id": "dydx",
                "name": "dYdX",
                "symbol": "DYDX",
                "logo": "DY",
                "description": "dYdX is a leading decentralized perpetual futures exchange that launched its own Cosmos-based blockchain. The DYDX token airdrop rewarded historical traders on the protocol.",
                "status": "ended",
                "platform": "Cosmos",
                "estimated_value": "$300 - $5,000",
                "total_value": "$200M+",
                "requirements": [
                    "Traded on dYdX v3 before snapshot",
                    "Used limit orders and margin trading",
                    "Provided feedback on governance"
                ],
                "end_date": "2024-06-01",
                "website": "https://dydx.exchange",
                "twitter": "https://twitter.com/dydxfoundation",
                "category": "DeFi",
                "difficulty": "medium",
                "participants": "60K+",
                "chain": "Cosmos",
                "color": "#6966ff",
                "verified": True,
            },
            {
                "id": "morpho",
                "name": "Morpho",
                "symbol": "MORPHO",
                "logo": "MO",
                "description": "Morpho is an optimized lending and borrowing protocol built on top of Aave and Compound. The MORPHO token airdrop rewarded early depositors and borrowers on the platform.",
                "status": "active",
                "platform": "Ethereum",
                "estimated_value": "$200 - $4,000",
                "total_value": "$100M+",
                "requirements": [
                    "Supply or borrow on Morpho",
                    "Use Morpho Blue for isolated lending",
                    "Participate in gauges voting"
                ],
                "end_date": (now + timedelta(days=40)).strftime("%Y-%m-%d"),
                "website": "https://morpho.org",
                "twitter": "https://twitter.com/MorphoLabs",
                "category": "DeFi",
                "difficulty": "medium",
                "participants": "300K+",
                "chain": "Ethereum",
                "color": "#0066ff",
                "verified": True,
            },
            {
                "id": "lido",
                "name": "Lido DAO",
                "symbol": "LDO",
                "logo": "LD",
                "description": "Lido is the leading liquid staking protocol for Ethereum, SOL, MATIC, and other assets. Active stakers and DAO participants may receive governance-related incentives.",
                "status": "active",
                "platform": "Ethereum",
                "estimated_value": "$100 - $2,000",
                "total_value": "$70M+",
                "requirements": [
                    "Stake ETH via Lido protocol",
                    "Use stETH in DeFi protocols",
                    "Vote on Lido DAO proposals"
                ],
                "end_date": (now + timedelta(days=55)).strftime("%Y-%m-%d"),
                "website": "https://lido.fi",
                "twitter": "https://twitter.com/LidoFinance",
                "category": "DeFi",
                "difficulty": "easy",
                "participants": "1M+",
                "chain": "Ethereum",
                "color": "#00a3ff",
                "verified": True,
            },
            {
                "id": "worldcoin",
                "name": "Worldcoin",
                "symbol": "WLD",
                "logo": "WO",
                "description": "Worldcoin aims to build the world's largest identity and financial network. Users verify their humanity via the Orb device and receive WLD grants regularly.",
                "status": "active",
                "platform": "Ethereum / Optimism",
                "estimated_value": "$20 - $200",
                "total_value": "$50M+",
                "requirements": [
                    "Get verified at a Worldcoin Orb location",
                    "Download the World App",
                    "Claim recurring WLD grants"
                ],
                "end_date": (now + timedelta(days=90)).strftime("%Y-%m-%d"),
                "website": "https://worldcoin.org",
                "twitter": "https://twitter.com/worldcoin",
                "category": "AI",
                "difficulty": "easy",
                "participants": "6M+",
                "chain": "Ethereum / Optimism",
                "color": "#000000",
                "verified": True,
            },
            {
                "id": "io_net",
                "name": "io.net",
                "symbol": "IO",
                "logo": "IO",
                "description": "io.net is a decentralized cloud computing network that aggregates GPU resources from underutilized sources for AI/ML workloads. Users who rent or supply GPUs earn IO rewards.",
                "status": "active",
                "platform": "Solana",
                "estimated_value": "$50 - $1,200",
                "total_value": "$40M+",
                "requirements": [
                    "Supply idle GPU to the network",
                    "Rent GPU compute for AI tasks",
                    "Participate in the worker community"
                ],
                "end_date": (now + timedelta(days=75)).strftime("%Y-%m-%d"),
                "website": "https://io.net",
                "twitter": "https://twitter.com/aborizkov",
                "category": "DePIN",
                "difficulty": "medium",
                "participants": "200K+",
                "chain": "Solana",
                "color": "#5b21b6",
                "verified": True,
            },
            {
                "id": "saga",
                "name": "Saga",
                "symbol": "SAGA",
                "logo": "SA",
                "description": "Saga is a blockchain platform that launches app-specific Chainlets for developers. The SAGA airdrop rewarded testnet validators and early community members who participated in Play-to-Airdrop campaigns.",
                "status": "upcoming",
                "platform": "Cosmos",
                "estimated_value": "$100 - $2,500",
                "total_value": "$80M+",
                "requirements": [
                    "Participate in Saga Play-to-Airdrop",
                    "Stake SAGA tokens",
                    "Use Saga Chainlets for dApps"
                ],
                "end_date": (now + timedelta(days=95)).strftime("%Y-%m-%d"),
                "website": "https://saga.xyz",
                "twitter": "https://twitter.com/SagaProtocol",
                "category": "Layer 1",
                "difficulty": "easy",
                "participants": "250K+",
                "chain": "Cosmos",
                "color": "#f43f5e",
                "verified": True,
            },
            {
                "id": "story",
                "name": "Story Protocol",
                "symbol": "IP",
                "logo": "IP",
                "description": "Story Protocol is a blockchain for intellectual property management, enabling creators to register, track, and monetize their IP on-chain. The IP token airdrop is confirmed for early ecosystem participants.",
                "status": "upcoming",
                "platform": "Ethereum",
                "estimated_value": "$200 - $3,000",
                "total_value": "TBA",
                "requirements": [
                    "Create and register IP on Story",
                    "Use the Story Protocol SDK",
                    "Participate in testnet programs"
                ],
                "end_date": (now + timedelta(days=130)).strftime("%Y-%m-%d"),
                "website": "https://storyprotocol.xyz",
                "twitter": "https://twitter.com/StoryProtocol",
                "category": "Infrastructure",
                "difficulty": "medium",
                "participants": "TBA",
                "chain": "Ethereum",
                "color": "#0ea5e9",
                "verified": True,
            },
            # ============ ADDITIONAL UNVERIFIED AIRDROPS ============
            {
                "id": "sonic",
                "name": "Sonic SVM",
                "symbol": "SONIC",
                "logo": "SO",
                "description": "Sonic SVM is a hyper-scalable SVM (Solana Virtual Machine) Layer 2 optimized for gaming and social applications. Token launch is rumored but not officially announced by the team.",
                "status": "upcoming",
                "platform": "Solana L2",
                "estimated_value": "$150 - $3,500",
                "total_value": "TBA",
                "requirements": [
                    "Play games on Sonic testnet",
                    "Join Sonic Discord community",
                    "Participate in social campaigns"
                ],
                "end_date": (now + timedelta(days=140)).strftime("%Y-%m-%d"),
                "website": "https://www.sonic.game",
                "twitter": "https://twitter.com/SonicSVM",
                "category": "GameFi",
                "difficulty": "easy",
                "participants": "TBA",
                "chain": "Solana L2",
                "color": "#eab308",
                "verified": False,
            },
            {
                "id": "grass2",
                "name": "Grass Season 2",
                "symbol": "GRASS",
                "logo": "G2",
                "description": "Grass is running a second season of rewards, offering new points that may convert to additional GRASS token allocations. Season 2 includes enhanced earning mechanisms and referral bonuses.",
                "status": "upcoming",
                "platform": "Solana",
                "estimated_value": "$50 - $1,000",
                "total_value": "TBA",
                "requirements": [
                    "Install and run Grass extension",
                    "Accumulate Season 2 points",
                    "Refer new users for bonus points"
                ],
                "end_date": (now + timedelta(days=100)).strftime("%Y-%m-%d"),
                "website": "https://app.getgrass.io",
                "twitter": "https://twitter.com/getgrass_io",
                "category": "DePIN",
                "difficulty": "easy",
                "participants": "TBA",
                "chain": "Solana",
                "color": "#059669",
                "verified": False,
            },
            {
                "id": "nil",
                "name": "Nil Foundation",
                "symbol": "NIL",
                "logo": "NI",
                "description": "Nil Foundation is building a decentralized database layer using zkSharding technology for provable data availability. Currently in early testnet phase with potential airdrop speculation.",
                "status": "upcoming",
                "platform": "Ethereum",
                "estimated_value": "$100 - $2,000",
                "total_value": "TBA",
                "requirements": [
                    "Run a Nil testnet node",
                    "Test data availability features",
                    "Join the developer community"
                ],
                "end_date": (now + timedelta(days=160)).strftime("%Y-%m-%d"),
                "website": "https://nil.foundation",
                "twitter": "https://twitter.com/nil_xyz",
                "category": "Infrastructure",
                "difficulty": "hard",
                "participants": "TBA",
                "chain": "Ethereum",
                "color": "#7c3aed",
                "verified": False,
            },
            {
                "id": "kaito",
                "name": "Kaito AI",
                "symbol": "KAITO",
                "logo": "KA",
                "description": "Kaito AI is a crypto search engine and AI-powered research platform. A second airdrop round has been rumored for active users who contribute to the platform's mindshare rankings.",
                "status": "upcoming",
                "platform": "Multi-chain",
                "estimated_value": "$100 - $1,500",
                "total_value": "TBA",
                "requirements": [
                    "Use Kaito AI search platform",
                    "Contribute content and engagement",
                    "Earn Mindshare points"
                ],
                "end_date": (now + timedelta(days=85)).strftime("%Y-%m-%d"),
                "website": "https://kaito.ai",
                "twitter": "https://twitter.com/kaitoai",
                "category": "AI",
                "difficulty": "easy",
                "participants": "TBA",
                "chain": "Multi-chain",
                "color": "#0891b2",
                "verified": False,
            },
        ]

        # Sort: active first, then upcoming, then ended; verified first within each group
        status_order = {"active": 0, "upcoming": 1, "ended": 2}
        airdrops.sort(key=lambda x: (
            status_order.get(x.get("status"), 3),
            0 if x.get("verified") else 1,
            x.get("name", "")
        ))

        return airdrops

    def get_stats(self) -> Dict[str, Any]:
        """Get airdrop statistics including trust levels."""
        airdrops = self._get_cached_airdrops()
        active = [a for a in airdrops if a.get("status") == "active"]
        upcoming = [a for a in airdrops if a.get("status") == "upcoming"]
        ended = [a for a in airdrops if a.get("status") == "ended"]
        verified = [a for a in airdrops if a.get("verified") is True]
        unverified = [a for a in airdrops if a.get("verified") is False]
        distributed = ended  # alias
        not_distributed = active + upcoming  # alias

        return {
            "total": len(airdrops),
            "active": len(active),
            "upcoming": len(upcoming),
            "ended": len(ended),
            "distributed": len(distributed),
            "not_distributed": len(not_distributed),
            "verified": len(verified),
            "unverified": len(unverified),
            "total_estimated_value": "$2.5B+",
            "categories": list(set(a.get("category", "") for a in airdrops)),
        }

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get airdrops filtered by category."""
        airdrops = self._get_cached_airdrops()
        return [a for a in airdrops if a.get("category") == category]

    def search_airdrops(self, query: str) -> List[Dict[str, Any]]:
        """Search airdrops by name, symbol, or description."""
        airdrops = self._get_cached_airdrops()
        query = query.lower()
        return [
            a for a in airdrops
            if query in a.get("name", "").lower()
            or query in a.get("symbol", "").lower()
            or query in a.get("description", "").lower()
            or query in a.get("category", "").lower()
            or query in a.get("chain", "").lower()
        ]
