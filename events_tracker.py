"""
Crypto Events Calendar — Curated events tracker.
Maintains upcoming and past crypto events: network launches, listings,
conferences, hard forks, token unlocks, mainnet launches, etc.
"""

from datetime import datetime, timedelta


class EventsTracker:
    """Manages a curated list of crypto events."""

    def __init__(self):
        self.events = self._load_events()

    def _load_events(self):
        """Load events data with realistic upcoming and past events."""
        today = datetime.utcnow()
        events = [
            # ===== JUNE 2026 =====
            {
                "id": 1, "title": "Ethereum Pectra Upgrade Go-Live",
                "date": "2026-06-20", "time": "14:00 UTC",
                "category": "network_upgrade",
                "coins": ["ETH", "ETC"],
                "description": "Ethereum's Pectra (Prague-Electra) upgrade goes live, bringing account abstraction, EIP-7702 smart contract wallets, and blob throughput improvements to the network.",
                "importance": "high", "status": "upcoming",
                "source": "https://ethereum.org",
                "tags": ["Ethereum", "Upgrade", "EIP-7702", "Account Abstraction"],
            },
            {
                "id": 2, "title": "Bitcoin 2025 Conference - Las Vegas",
                "date": "2026-06-18", "time": "09:00 PST",
                "category": "conference",
                "coins": ["BTC"],
                "description": "The world's largest Bitcoin conference returns to Las Vegas with 15,000+ attendees, featuring keynotes from industry leaders, workshops, and networking events.",
                "importance": "medium", "status": "upcoming",
                "source": "https://bconf.info",
                "tags": ["Bitcoin", "Conference", "Networking"],
            },
            {
                "id": 3, "title": "Solana Breakpoint Conference",
                "date": "2026-06-20", "time": "10:00 UTC",
                "category": "conference",
                "coins": ["SOL"],
                "description": "Solana's flagship developer conference featuring new product announcements, ecosystem updates, and builder grants totaling $10M.",
                "importance": "medium", "status": "upcoming",
                "source": "https://solana.com/breakpoint",
                "tags": ["Solana", "Conference", "DeFi"],
            },
            {
                "id": 4, "title": "Binance Megadrop Season 4 Launch",
                "date": "2026-06-22", "time": "00:00 UTC",
                "category": "airdrop",
                "coins": ["BNB"],
                "description": "Binance launches the 4th season of Megadrop with an estimated $5M reward pool. Users can qualify by staking BNB, completing Web3 quests, and holding listed tokens.",
                "importance": "medium", "status": "upcoming",
                "source": "https://binance.com",
                "tags": ["Binance", "Airdrop", "Megadrop"],
            },
            {
                "id": 5, "title": "SEC Decision on Solana ETF Application",
                "date": "2026-06-25", "time": "—",
                "category": "regulation",
                "coins": ["SOL"],
                "description": "The US SEC is expected to issue a final decision on the Solana Spot ETF application submitted by VanEck and 21Shares, which could open institutional investment in SOL.",
                "importance": "high", "status": "upcoming",
                "source": "https://sec.gov",
                "tags": ["SEC", "ETF", "Solana", "Regulation"],
            },
            {
                "id": 6, "title": "Arbitrum Token Unlock ($120M ARB)",
                "date": "2026-06-28", "time": "00:00 UTC",
                "category": "token_unlock",
                "coins": ["ARB"],
                "description": "A scheduled unlock of 120 million ARB tokens worth approximately $120M will be released to team members and early investors, potentially increasing circulating supply.",
                "importance": "medium", "status": "upcoming",
                "source": "https://token.unlocks.app",
                "tags": ["Arbitrum", "Token Unlock", "ARB"],
            },
            # ===== JULY 2025 =====
            {
                "id": 7, "title": "Bitcoin Halving Aftermath Analysis Report",
                "date": "2026-07-01", "time": "12:00 UTC",
                "category": "milestone",
                "coins": ["BTC"],
                "description": "Major research firms release their 3-month post-halving analysis reports, evaluating hash rate adjustments, miner economics, and price correlation with previous cycles.",
                "importance": "medium", "status": "upcoming",
                "source": "https://glassnode.com",
                "tags": ["Bitcoin", "Halving", "Analysis"],
            },
            {
                "id": 8, "title": "World Blockchain Summit - Dubai",
                "date": "2026-07-05", "time": "09:00 GST",
                "category": "conference",
                "coins": [],
                "description": "Global blockchain and crypto summit in Dubai with 500+ speakers, regulatory roundtables, DeFi showcases, and government blockchain initiative announcements.",
                "importance": "medium", "status": "upcoming",
                "source": "https://worldblockchainsummit.com",
                "tags": ["Blockchain", "Conference", "Dubai", "Regulation"],
            },
            {
                "id": 9, "title": "Chainlink CCIP v2 Mainnet Launch",
                "date": "2026-07-10", "time": "16:00 UTC",
                "category": "mainnet_launch",
                "coins": ["LINK"],
                "description": "Chainlink launches CCIP v2 on mainnet, enabling cross-chain token transfers and generalized messaging across 25+ blockchains with improved security guarantees.",
                "importance": "high", "status": "upcoming",
                "source": "https://chain.link",
                "tags": ["Chainlink", "CCIP", "Cross-chain", "Interoperability"],
            },
            {
                "id": 10, "title": "Uniswap v4 Deployment on Ethereum",
                "date": "2026-07-15", "time": "14:00 UTC",
                "category": "mainnet_launch",
                "coins": ["ETH", "UNI"],
                "description": "Uniswap deploys v4 on Ethereum mainnet with hooks-based architecture, enabling custom AMM logic, dynamic fees, TWAP oracles, and limit orders natively on-chain.",
                "importance": "high", "status": "upcoming",
                "source": "https://uniswap.org",
                "tags": ["Uniswap", "DeFi", "AMM", "Ethereum"],
            },
            {
                "id": 11, "title": "Coinbase International Exchange Launches Perpetual Futures for XRP",
                "date": "2026-07-18", "time": "09:30 UTC",
                "category": "listing",
                "coins": ["XRP"],
                "description": "Coinbase International Exchange lists perpetual futures contracts for XRP with up to 20x leverage, expanding institutional derivative trading options.",
                "importance": "low", "status": "upcoming",
                "source": "https://coinbase.com",
                "tags": ["Coinbase", "XRP", "Futures", "Listing"],
            },
            {
                "id": 12, "title": "US Federal Reserve Crypto Policy Hearing",
                "date": "2026-07-22", "time": "14:00 EST",
                "category": "regulation",
                "coins": [],
                "description": "Congressional hearing on the Federal Reserve's approach to central bank digital currencies (CBDC), stablecoin regulation, and cryptocurrency oversight framework.",
                "importance": "high", "status": "upcoming",
                "source": "https://federalreserve.gov",
                "tags": ["Federal Reserve", "CBDC", "Stablecoin", "Regulation"],
            },
            {
                "id": 13, "title": "Avalanche9000 Network Upgrade",
                "date": "2026-07-25", "time": "15:00 UTC",
                "category": "network_upgrade",
                "coins": ["AVAX"],
                "description": "Avalanche9000 upgrade reduces subnet creation cost by 90%, introduces ephemeral subnets, and improves cross-subnet communication for better scalability.",
                "importance": "medium", "status": "upcoming",
                "source": "https://avax.network",
                "tags": ["Avalanche", "Upgrade", "Subnets"],
            },
            # ===== AUGUST 2025 =====
            {
                "id": 14, "title": "Cardano Chang Hard Fork #2",
                "date": "2026-08-05", "time": "20:00 UTC",
                "category": "hard_fork",
                "coins": ["ADA"],
                "description": "The second major hard fork in the Chang era introduces Plutus V3 enhancements, on-chain governance improvements, and peer-to-peer transaction capabilities.",
                "importance": "medium", "status": "upcoming",
                "source": "https://cardano.org",
                "tags": ["Cardano", "Hard Fork", "Chang", "Governance"],
            },
            {
                "id": 15, "title": "Polygon zkEVM Finality Launch",
                "date": "2026-08-10", "time": "12:00 UTC",
                "category": "mainnet_launch",
                "coins": ["POL", "MATIC"],
                "description": "Polygon launches native zkEVM finality, bringing ZK-proof security to all Polygon chains with sub-second finality and 100x cost reduction for L2 transactions.",
                "importance": "high", "status": "upcoming",
                "source": "https://polygon.technology",
                "tags": ["Polygon", "zkEVM", "Layer2", "ZK-Proofs"],
            },
            {
                "id": 16, "title": "Tether $1B USDT Mint Event",
                "date": "2026-08-12", "time": "—",
                "category": "stablecoin",
                "coins": ["USDT"],
                "description": "Tether mints an additional $1B USDT on Ethereum and Tron networks, signaling increased institutional demand and potential market liquidity injection.",
                "importance": "low", "status": "upcoming",
                "source": "https://tether.to",
                "tags": ["Tether", "USDT", "Stablecoin", "Mint"],
            },
            {
                "id": 17, "title": "Korea Blockchain Week 2025",
                "date": "2026-08-18", "time": "09:00 KST",
                "category": "conference",
                "coins": [],
                "description": "Asia's premier blockchain conference in Seoul featuring 200+ projects, regulatory panels with Korean FSC officials, and DeFi exhibition showcases.",
                "importance": "medium", "status": "upcoming",
                "source": "https://koreablockchainweek.com",
                "tags": ["KBW", "Conference", "Korea", "DeFi"],
            },
            {
                "id": 18, "title": "Optimism Superchain Interop Launch",
                "date": "2026-08-22", "time": "16:00 UTC",
                "category": "network_upgrade",
                "coins": ["OP", "ETH"],
                "description": "Optimism launches full cross-chain interoperability across the Superchain, enabling seamless messaging and asset transfers between OP Mainnet, Base, Zora, and other OP Stack chains.",
                "importance": "high", "status": "upcoming",
                "source": "https://optimism.io",
                "tags": ["Optimism", "Superchain", "Interop", "Layer2"],
            },
            {
                "id": 19, "title": "Sui Mainnet V2 with Object-Centric Parallel Execution",
                "date": "2026-08-28", "time": "14:00 UTC",
                "category": "network_upgrade",
                "coins": ["SUI"],
                "description": "Sui V2 upgrade brings major improvements to parallel execution engine, reducing latency to sub-second and enabling 300K+ TPS for DeFi and gaming applications.",
                "importance": "medium", "status": "upcoming",
                "source": "https://sui.io",
                "tags": ["Sui", "Upgrade", "Parallel Execution", "Gaming"],
            },
            # ===== SEPTEMBER 2025 =====
            {
                "id": 20, "title": "Ethereum Foundation Devcon SEA",
                "date": "2026-09-12", "time": "09:00 ICT",
                "category": "conference",
                "coins": ["ETH"],
                "description": "The Ethereum Foundation's flagship developer conference in Southeast Asia featuring protocol research presentations, layer 2 scaling discussions, and ETH2 roadmap updates.",
                "importance": "high", "status": "upcoming",
                "source": "https://devcon.org",
                "tags": ["Ethereum", "Devcon", "Conference", "Research"],
            },
            {
                "id": 21, "title": "Federal Reserve Interest Rate Decision (Sept)",
                "date": "2026-09-17", "time": "18:00 EST",
                "category": "macro_economic",
                "coins": ["BTC", "ETH"],
                "description": "The FOMC interest rate decision and press conference by the Federal Reserve Chairman, with potential impact on Bitcoin and broader crypto market sentiment.",
                "importance": "high", "status": "upcoming",
                "source": "https://federalreserve.gov",
                "tags": ["Federal Reserve", "Interest Rate", "Macro", "FOMC"],
            },
            {
                "id": 22, "title": "Binance Listing Vote: New DeFi Tokens",
                "date": "2026-09-20", "time": "08:00 UTC",
                "category": "listing",
                "coins": [],
                "description": "Binance Launchpad community voting round for listing 3 new DeFi tokens from emerging ecosystems including Berachain, Monad, and Story Protocol.",
                "importance": "low", "status": "upcoming",
                "source": "https://binance.com",
                "tags": ["Binance", "Listing", "Vote", "DeFi"],
            },
            # ===== OCTOBER 2025 =====
            {
                "id": 23, "title": "Berachain Mainnet Launch",
                "date": "2026-10-01", "time": "14:00 UTC",
                "category": "mainnet_launch",
                "coins": ["BERA"],
                "description": "Berachain officially launches its Proof of Liquidity mainnet, bringing EVM compatibility with a novel consensus mechanism that aligns validator incentives with DeFi liquidity provision.",
                "importance": "high", "status": "upcoming",
                "source": "https://www.berachain.com",
                "tags": ["Berachain", "Mainnet", "Proof of Liquidity", "EVM"],
            },
            {
                "id": 24, "title": "Aptos Token Unlock ($90M APT)",
                "date": "2026-10-12", "time": "00:00 UTC",
                "category": "token_unlock",
                "coins": ["APT"],
                "description": "A scheduled unlock of 9 million APT tokens worth approximately $90M will be released to core contributors, investors, and the community reserve fund.",
                "importance": "medium", "status": "upcoming",
                "source": "https://token.unlocks.app",
                "tags": ["Aptos", "Token Unlock", "APT"],
            },
            {
                "id": 25, "title": "Permissionless III Conference - Salt Lake City",
                "date": "2026-10-15", "time": "09:00 MST",
                "category": "conference",
                "coins": [],
                "description": "The premier DeFi conference returns to Salt Lake City with 5,000+ attendees, featuring protocol launches, liquidity mining announcements, and builder competitions.",
                "importance": "medium", "status": "upcoming",
                "source": "https://permissionless.io",
                "tags": ["DeFi", "Conference", "Permissionless", "Builder"],
            },
            {
                "id": 26, "title": "Monad Mainnet Beta Launch",
                "date": "2026-10-20", "time": "16:00 UTC",
                "category": "mainnet_launch",
                "coins": ["MON"],
                "description": "Monad launches its highly anticipated EVM-compatible Layer 1 mainnet beta, claiming 10,000+ TPS with parallel execution and deferred execution architecture.",
                "importance": "high", "status": "upcoming",
                "source": "https://www.monad.xyz",
                "tags": ["Monad", "Mainnet", "Layer 1", "Parallel Execution"],
            },
            # ===== NOVEMBER 2025 =====
            {
                "id": 27, "title": "Tether Stablecoin Reserve Attestation (Q3)",
                "date": "2026-11-01", "time": "12:00 UTC",
                "category": "stablecoin",
                "coins": ["USDT"],
                "description": "Tether publishes its quarterly independent attestation report detailing the composition of USDT reserves, exceeding $140B in market capitalization.",
                "importance": "medium", "status": "upcoming",
                "source": "https://tether.to",
                "tags": ["Tether", "USDT", "Reserves", "Stablecoin"],
            },
            {
                "id": 28, "title": "Polkadot 2.0 Agile Coretime Launch",
                "date": "2026-11-05", "time": "15:00 UTC",
                "category": "network_upgrade",
                "coins": ["DOT"],
                "description": "Polkadot launches Agile Coretime, allowing parachains to purchase blockspace on-demand instead of auctioning entire lease periods, dramatically lowering entry barriers for developers.",
                "importance": "high", "status": "upcoming",
                "source": "https://polkadot.network",
                "tags": ["Polkadot", "Coretime", "Parachain", "Upgrade"],
            },
            {
                "id": 29, "title": "Kraken Lists Sui Perpetual Futures",
                "date": "2026-11-08", "time": "14:00 UTC",
                "category": "listing",
                "coins": ["SUI"],
                "description": "Kraken exchange launches perpetual futures contracts for SUI with up to 50x leverage, expanding derivatives trading options for the Move-based blockchain ecosystem.",
                "importance": "low", "status": "upcoming",
                "source": "https://kraken.com",
                "tags": ["Kraken", "Sui", "Futures", "Listing"],
            },
            {
                "id": 30, "title": "Ethereum Verkle Trees Testnet Activation",
                "date": "2026-11-15", "time": "12:00 UTC",
                "category": "network_upgrade",
                "coins": ["ETH"],
                "description": "Ethereum activates Verkle Trees on the Holesky testnet, paving the way for stateless clients that enable full node sync with minimal storage requirements.",
                "importance": "medium", "status": "upcoming",
                "source": "https://ethereum.org",
                "tags": ["Ethereum", "Verkle Trees", "Stateless", "Testnet"],
            },
            # ===== DECEMBER 2025 =====
            {
                "id": 31, "title": "Federal Reserve Interest Rate Decision (Dec)",
                "date": "2026-12-17", "time": "18:00 EST",
                "category": "macro_economic",
                "coins": ["BTC", "ETH", "SOL"],
                "description": "The final FOMC meeting of the year with interest rate decision and updated economic projections, traditionally a period of high volatility across crypto markets.",
                "importance": "high", "status": "upcoming",
                "source": "https://federalreserve.gov",
                "tags": ["Federal Reserve", "Interest Rate", "Macro", "FOMC"],
            },
            {
                "id": 32, "title": "Cosmos Hub Interchain Security v2 Upgrade",
                "date": "2026-12-05", "time": "14:00 UTC",
                "category": "network_upgrade",
                "coins": ["ATOM"],
                "description": "Cosmos Hub implements Interchain Security v2, enabling optimal validator scheduling, shared security for consumer chains, and improved rewards distribution across the ecosystem.",
                "importance": "medium", "status": "upcoming",
                "source": "https://cosmos.network",
                "tags": ["Cosmos", "Interchain Security", "ATOM", "Upgrade"],
            },
            # ===== PAST EVENTS (Jan–Apr 2025) =====
            {
                "id": 104, "title": "Bitcoin ETF First Anniversary",
                "date": "2025-01-10", "time": "All Day",
                "category": "milestone",
                "coins": ["BTC"],
                "description": "One year since the SEC approved the first US-listed Bitcoin spot ETFs. The 11 ETFs now hold over 1 million BTC combined, with BlackRock's IBIT leading at $60B+ in AUM.",
                "importance": "medium", "status": "completed",
                "source": "https://sec.gov",
                "tags": ["Bitcoin", "ETF", "Anniversary", "Milestone"],
            },
            {
                "id": 105, "title": "Trump Executive Order on Digital Assets",
                "date": "2025-01-23", "time": "15:00 EST",
                "category": "regulation",
                "coins": ["BTC", "ETH"],
                "description": "President Trump signed a comprehensive executive order establishing a federal cryptocurrency regulatory framework, creating a strategic BTC reserve, and directing agencies to develop crypto-friendly policies.",
                "importance": "high", "status": "completed",
                "source": "https://whitehouse.gov",
                "tags": ["Trump", "Executive Order", "Crypto Regulation", "Policy"],
            },
            {
                "id": 106, "title": "Solana ETF Approval by SEC",
                "date": "2025-02-14", "time": "16:00 EST",
                "category": "regulation",
                "coins": ["SOL"],
                "description": "The SEC granted approval for Solana spot ETF applications from VanEck and 21Shares, making SOL the second cryptocurrency after Bitcoin and Ethereum to receive ETF approval in the US.",
                "importance": "high", "status": "completed",
                "source": "https://sec.gov",
                "tags": ["SEC", "ETF", "Solana", "Approval"],
            },
            {
                "id": 107, "title": "Ethereum Dencun Upgrade Anniversary",
                "date": "2025-03-13", "time": "All Day",
                "category": "milestone",
                "coins": ["ETH"],
                "description": "One year since the Dencun (Cancun-Deneb) upgrade introduced proto-danksharding, reducing L2 transaction fees by 90%+ and kickstarting the rollup-centric scaling roadmap.",
                "importance": "low", "status": "completed",
                "source": "https://ethereum.org",
                "tags": ["Ethereum", "Dencun", "Anniversary", "L2 Scaling"],
            },
            {
                "id": 108, "title": "Bybit $1.5B Hack — Lazarus Group",
                "date": "2025-02-21", "time": "—",
                "category": "milestone",
                "coins": ["ETH"],
                "description": "North Korean Lazarus Group executed one of the largest crypto exchange hacks in history, stealing $1.5B in ETH from Bybit's cold wallet. The incident triggered industry-wide security reviews.",
                "importance": "high", "status": "completed",
                "source": "https://elliptic.co",
                "tags": ["Bybit", "Hack", "Security", "Lazarus Group"],
            },
            {
                "id": 109, "title": "Sui Mainnet V2 Launch",
                "date": "2025-03-25", "time": "14:00 UTC",
                "category": "network_upgrade",
                "coins": ["SUI"],
                "description": "Sui launched its V2 network upgrade introducing object-centric parallel execution improvements, reducing transaction latency to sub-second and enabling 300K+ TPS.",
                "importance": "medium", "status": "completed",
                "source": "https://sui.io",
                "tags": ["Sui", "V2", "Parallel Execution", "Upgrade"],
            },
            {
                "id": 110, "title": "BTC L2 Stacks Nakamoto v3 Hard Fork",
                "date": "2025-04-15", "time": "20:00 UTC",
                "category": "hard_fork",
                "coins": ["BTC", "STX"],
                "description": "Stacks executed the Nakamoto v3 hard fork, enabling faster Bitcoin L2 block times, improved Bitcoin finality, and native BTC support for sBTC on the Stacks network.",
                "importance": "medium", "status": "completed",
                "source": "https://stacks.co",
                "tags": ["Stacks", "Bitcoin L2", "Hard Fork", "sBTC"],
            },
            {
                "id": 111, "title": "Circle Launches EURC Stablecoin on Solana",
                "date": "2025-03-05", "time": "10:00 UTC",
                "category": "stablecoin",
                "coins": ["USDC"],
                "description": "Circle expanded its euro-backed stablecoin EURC to the Solana blockchain, enabling DeFi applications to access EUR-denominated liquidity with sub-cent transaction costs.",
                "importance": "low", "status": "completed",
                "source": "https://circle.com",
                "tags": ["Circle", "EURC", "Stablecoin", "Solana"],
            },
            {
                "id": 112, "title": "Consensus 2025 — Toronto",
                "date": "2025-05-14", "time": "09:00 EST",
                "category": "conference",
                "coins": [],
                "description": "CoinDesk's flagship crypto conference attracted 15,000+ attendees in Toronto with keynotes from central bankers, DeFi founders, and policy makers discussing the evolving crypto landscape.",
                "importance": "medium", "status": "completed",
                "source": "https://consensus.coindesk.com",
                "tags": ["Consensus", "Conference", "CoinDesk", "Toronto"],
            },
            {
                "id": 113, "title": "BNB Chain Opal Upgrade — State Expiry",
                "date": "2025-04-20", "time": "08:00 UTC",
                "category": "network_upgrade",
                "coins": ["BNB"],
                "description": "BNB Chain implemented the Opal upgrade featuring state expiry mechanisms that prune inactive smart contract storage, reducing the chain's state size and improving node performance.",
                "importance": "low", "status": "completed",
                "source": "https://www.bnbchain.org",
                "tags": ["BNB Chain", "Opal Upgrade", "State Expiry", "Scaling"],
            },
            # ===== PAST EVENTS (May 2025) =====
            {
                "id": 101, "title": "Bitcoin Pizza Day",
                "date": "2025-05-22", "time": "All Day",
                "category": "milestone",
                "coins": ["BTC"],
                "description": "Celebrating the 15th anniversary of the famous Bitcoin pizza purchase — Laszlo Hanyecz paid 10,000 BTC for two pizzas in 2010, now worth hundreds of millions.",
                "importance": "low", "status": "completed",
                "source": "https://bitcointalk.org",
                "tags": ["Bitcoin", "Pizza Day", "History", "Milestone"],
            },
            {
                "id": 102, "title": "SEC Approves First Privacy Coin ETF",
                "date": "2025-05-28", "time": "16:00 EST",
                "category": "regulation",
                "coins": [],
                "description": "The SEC issued a landmark decision granting approval for the first privacy coin-related ETF product, signaling a shift in regulatory stance on privacy-focused cryptocurrencies.",
                "importance": "high", "status": "completed",
                "source": "https://sec.gov",
                "tags": ["SEC", "ETF", "Privacy Coin", "Regulation"],
            },
            {
                "id": 103, "title": "Base Onchain Summer 2025 Kickoff",
                "date": "2025-05-30", "time": "00:00 UTC",
                "category": "airdrop",
                "coins": ["ETH"],
                "description": "Coinbase's Layer 2 network Base launches Onchain Summer 2025 with over $2M in incentives for developers and users building and using on-chain applications.",
                "importance": "medium", "status": "completed",
                "source": "https://base.org",
                "tags": ["Base", "Coinbase", "Onchain Summer", "Airdrop"],
            },
        ]

        # Auto-update status based on date
        for event in events:
            event_date = datetime.strptime(event["date"], "%Y-%m-%d")
            if event_date < today:
                event["status"] = "completed"
            elif event_date.date() == today.date():
                event["status"] = "live"
            else:
                event["status"] = "upcoming"

        # Sort by date ascending
        events.sort(key=lambda e: e["date"])
        return events

    def get_events(self, status=None, category=None, month=None, search=None, limit=50):
        """Get filtered events."""
        filtered = self.events[:]

        if status and status != "all":
            filtered = [e for e in filtered if e["status"] == status]

        if category and category != "all":
            filtered = [e for e in filtered if e["category"] == category]

        if month:
            filtered = [e for e in filtered if e["date"][:7] == month]

        if search:
            q = search.lower()
            filtered = [e for e in filtered if
                        q in e["title"].lower() or
                        q in e["description"].lower() or
                        any(q in tag.lower() for tag in e.get("tags", [])) or
                        any(q in coin.lower() for coin in e.get("coins", []))]

        return filtered[:limit]

    def get_upcoming_events(self, limit=10):
        """Get next upcoming events."""
        return [e for e in self.events if e["status"] in ("upcoming", "live")][:limit]

    def get_events_by_month(self, year, month):
        """Get events for a specific month."""
        month_str = f"{year}-{month:02d}"
        return [e for e in self.events if e["date"][:7] == month_str]

    def search_events(self, query):
        """Search events by title, description, tags, or coins."""
        return self.get_events(search=query, limit=20)

    def get_categories(self):
        """Get all event categories with metadata."""
        return {
            "network_upgrade": {"name": "Network Upgrade", "icon": "fas fa-server", "color": "#22d3ee"},
            "conference": {"name": "Conference", "icon": "fas fa-users", "color": "#a78bfa"},
            "airdrop": {"name": "Airdrop / Campaign", "icon": "fas fa-parachute-box", "color": "#34d399"},
            "regulation": {"name": "Regulation", "icon": "fas fa-gavel", "color": "#f87171"},
            "token_unlock": {"name": "Token Unlock", "icon": "fas fa-lock-open", "color": "#fb923c"},
            "mainnet_launch": {"name": "Mainnet Launch", "icon": "fas fa-rocket", "color": "#fbbf24"},
            "hard_fork": {"name": "Hard Fork", "icon": "fas fa-code-branch", "color": "#f472b6"},
            "listing": {"name": "Exchange Listing", "icon": "fas fa-plus-circle", "color": "#60a5fa"},
            "milestone": {"name": "Milestone", "icon": "fas fa-flag", "color": "#c084fc"},
            "macro_economic": {"name": "Macro Economic", "icon": "fas fa-landmark", "color": "#94a3b8"},
            "stablecoin": {"name": "Stablecoin Event", "icon": "fas fa-dollar-sign", "color": "#4ade80"},
        }

    def get_stats(self):
        """Get events statistics."""
        total = len(self.events)
        upcoming = sum(1 for e in self.events if e["status"] == "upcoming")
        live = sum(1 for e in self.events if e["status"] == "live")
        completed = sum(1 for e in self.events if e["status"] == "completed")
        high_importance = sum(1 for e in self.events if e["importance"] == "high" and e["status"] != "completed")

        # Get unique months
        months = set()
        for e in self.events:
            if e["status"] != "completed":
                months.add(e["date"][:7])

        # Get unique coins
        all_coins = set()
        for e in self.events:
            all_coins.update(e.get("coins", []))

        return {
            "total": total,
            "upcoming": upcoming,
            "live": live,
            "completed": completed,
            "high_importance": high_importance,
            "active_months": len(months),
            "coins_involved": len(all_coins),
        }

    def get_calendar_months(self):
        """Get list of months that have events."""
        months = {}
        for e in self.events:
            ym = e["date"][:7]
            if ym not in months:
                month_name = datetime.strptime(ym + "-01", "%Y-%m-%d").strftime("%B %Y")
                months[ym] = {
                    "key": ym,
                    "label": month_name,
                    "year": int(ym[:4]),
                    "month": int(ym[5:7]),
                    "count": 0
                }
            months[ym]["count"] += 1
        return sorted(months.values(), key=lambda m: m["key"], reverse=True)
