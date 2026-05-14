"""
CryptositNews - Crypto Facts & Quiz Module
A comprehensive collection of crypto facts, stats, and interactive quizzes.
"""

import random
from datetime import datetime


# ─────────────────────────────────────────────
# CRYPTO FACTS DATABASE
# ─────────────────────────────────────────────

CRYPTO_FACTS = [
    {
        "id": 1,
        "category": "bitcoin",
        "icon": "fab fa-bitcoin",
        "color": "#f7931a",
        "fact": "Bitcoin was created on January 3, 2009, when Satoshi Nakamoto mined the genesis block (Block 0), embedding the headline: 'Chancellor on brink of second bailout for banks.'",
        "detail": "The genesis block contained a single transaction of 50 BTC to Satoshi's wallet. The embedded newspaper headline from The Times referenced the 2008 financial crisis, serving as both a timestamp and a political statement about the flaws in the traditional banking system.",
        "source": "Bitcoin Blockchain",
        "year": 2009
    },
    {
        "id": 2,
        "category": "bitcoin",
        "icon": "fab fa-bitcoin",
        "color": "#f7931a",
        "fact": "The identity of Bitcoin's creator, Satoshi Nakamoto, remains unknown to this day. It is estimated that Satoshi holds approximately 1.1 million BTC worth over $60 billion.",
        "detail": "Satoshi Nakamoto communicated through emails and forum posts from 2008 to 2010 before disappearing. The wallet addresses associated with Satoshi have never moved any Bitcoin. Multiple individuals have been suspected over the years, including Hal Finney, Craig Wright, and Dorian Nakamoto, but none have been definitively proven.",
        "source": "Blockchain Analysis",
        "year": 2008
    },
    {
        "id": 3,
        "category": "bitcoin",
        "icon": "fab fa-bitcoin",
        "color": "#f7931a",
        "fact": "The first real-world Bitcoin transaction was made on May 22, 2010, when Laszlo Hanyecz paid 10,000 BTC for two pizzas. That amount is now worth over $600 million.",
        "detail": "Laszlo Hanyecz posted on the BitcoinTalk forum offering 10,000 BTC to anyone who would order him two large pizzas from Papa John's. A user named 'jercos' accepted and had the pizzas delivered. May 22 is now celebrated annually as 'Bitcoin Pizza Day' by crypto enthusiasts worldwide.",
        "source": "BitcoinTalk Forum",
        "year": 2010
    },
    {
        "id": 4,
        "category": "bitcoin",
        "icon": "fab fa-bitcoin",
        "color": "#f7931a",
        "fact": "There will only ever be 21 million Bitcoins. As of 2024, over 19.5 million BTC have been mined, meaning less than 1.5 million remain to be discovered.",
        "detail": "Bitcoin's supply cap is hardcoded into its protocol. New Bitcoins are created through mining as a block reward, which halves approximately every four years in an event known as the 'halving.' The last Bitcoin is expected to be mined around the year 2140. This scarcity is a fundamental aspect of Bitcoin's value proposition.",
        "source": "Bitcoin Protocol",
        "year": 2008
    },
    {
        "id": 5,
        "category": "ethereum",
        "icon": "fab fa-ethereum",
        "color": "#627eea",
        "fact": "Vitalik Buterin conceived Ethereum when he was just 19 years old. He published the Ethereum white paper in November 2013, and the network went live on July 30, 2015.",
        "detail": "Buterin first described Ethereum in a white paper sent to a group of developers in late 2013, proposing a general-purpose blockchain that could support smart contracts. The Ethereum Foundation was established in Switzerland in 2014, raising over $31,000 in BTC through a crowdfunding campaign. The network launched with 72 million ETH pre-mined for the sale participants.",
        "source": "Ethereum Foundation",
        "year": 2013
    },
    {
        "id": 6,
        "category": "ethereum",
        "icon": "fab fa-ethereum",
        "color": "#627eea",
        "fact": "Ethereum completed 'The Merge' on September 15, 2022, transitioning from Proof of Work to Proof of Stake, reducing its energy consumption by approximately 99.95%.",
        "detail": "The Merge was one of the most significant technological upgrades in blockchain history. It combined the original Ethereum execution layer with the new Beacon Chain consensus layer. Prior to The Merge, Ethereum consumed about 112 TWh per year (comparable to the Netherlands). Post-Merge, it consumes roughly 0.01 TWh, making it one of the most energy-efficient blockchain networks.",
        "source": "Ethereum Foundation",
        "year": 2022
    },
    {
        "id": 7,
        "category": "mining",
        "icon": "fas fa-microchip",
        "color": "#f59e0b",
        "fact": "Bitcoin mining consumes more electricity than many entire countries. In 2024, the Bitcoin network's annual energy consumption was estimated at around 150 TWh, comparable to Argentina.",
        "detail": "Bitcoin's Proof of Work consensus mechanism requires miners to solve complex mathematical puzzles, consuming vast amounts of computational power. However, it's estimated that over 50% of Bitcoin mining uses renewable energy sources. The Cambridge Bitcoin Electricity Consumption Index (CBECI) is the primary tool used to track this energy usage.",
        "source": "Cambridge University",
        "year": 2024
    },
    {
        "id": 8,
        "category": "mining",
        "icon": "fas fa-microchip",
        "color": "#f59e0b",
        "fact": "The first Bitcoin ATM was installed on October 29, 2013, at Waves Coffee House in Vancouver, Canada. Today there are over 40,000 crypto ATMs worldwide.",
        "detail": "The first Bitcoin ATM (BTM) was created by Robocoin and allowed users to exchange cash for Bitcoin and vice versa. By 2024, there are over 40,000 crypto ATMs across more than 80 countries. The United States has the highest number, followed by Canada and Europe. These machines have evolved to support multiple cryptocurrencies and advanced features like QR code scanning.",
        "source": "Coin ATM Radar",
        "year": 2013
    },
    {
        "id": 9,
        "category": "defi",
        "icon": "fas fa-exchange-alt",
        "color": "#10b981",
        "fact": "The Total Value Locked (TVL) in DeFi peaked at over $180 billion in November 2021. As of 2024, DeFi protocols manage tens of billions in assets across multiple blockchains.",
        "detail": "DeFi (Decentralized Finance) refers to financial services built on blockchain technology that operate without traditional intermediaries like banks. The DeFi ecosystem includes lending platforms (Aave, Compound), decentralized exchanges (Uniswap, Curve), yield protocols, and more. Ethereum remains the dominant chain for DeFi, but Layer 2 solutions and alternative chains have gained significant market share.",
        "source": "DeFi Llama",
        "year": 2021
    },
    {
        "id": 10,
        "category": "defi",
        "icon": "fas fa-exchange-alt",
        "color": "#10b981",
        "fact": "Uniswap, the largest decentralized exchange, processes over $1 billion in daily trading volume. It was launched in November 2018 by Hayden Adams, inspired by a Vitalik Buterin Reddit post.",
        "detail": "Uniswap pioneered the Automated Market Maker (AMM) model, replacing traditional order books with liquidity pools. Users can swap tokens directly against smart contract liquidity. Uniswap v2 launched in 2020 with ERC-20 pair support, and v3 in 2021 introduced concentrated liquidity, allowing LPs to allocate capital within specific price ranges for up to 4000x capital efficiency.",
        "source": "Uniswap Labs",
        "year": 2018
    },
    {
        "id": 11,
        "category": "nft",
        "icon": "fas fa-palette",
        "color": "#ec4899",
        "fact": "The most expensive NFT ever sold is 'The Merge' by Pak, which was purchased for $91.8 million in December 2021. Over 28,000 collectors participated in the purchase.",
        "detail": "'The Merge' was sold on the NFT platform Nifty Gateway and consisted of 312,686 units of mass (NFTs) that combined into single NFTs. The work was conceptualized around the idea of merging individual units into a single entity, with the price increasing as more people participated. Beeple's 'Everydays: The First 5000 Days' previously held the record at $69.3 million.",
        "source": "Nifty Gateway",
        "year": 2021
    },
    {
        "id": 12,
        "category": "nft",
        "icon": "fas fa-palette",
        "color": "#ec4899",
        "fact": "The concept of NFTs dates back to 2012 with the creation of 'Colored Coins' on the Bitcoin blockchain. The first modern NFT, 'Quantum,' was minted in 2014 on the Namecoin blockchain.",
        "detail": "Colored Coins were small amounts of Bitcoin that were 'colored' to represent digital assets. Kevin McCoy created 'Quantum' in May 2014, making it the first known NFT linked to a work of art. The modern NFT boom began with the launch of Ethereum's ERC-721 token standard in 2017, popularized by projects like CryptoPunks and CryptoKitties.",
        "source": "Blockchain History",
        "year": 2012
    },
    {
        "id": 13,
        "category": "trading",
        "icon": "fas fa-chart-line",
        "color": "#3b82f6",
        "fact": "Bitcoin's price reached an all-time high of nearly $73,750 in March 2024. Its journey from $0.003 in 2010 represents a growth of over 2.4 billion percent.",
        "detail": "Bitcoin's price history is marked by dramatic boom-and-bust cycles. Key milestones include reaching $1 in February 2011, $1,000 in November 2013, $10,000 in November 2017, $20,000 in December 2017, and $69,000 in November 2021. Each cycle has been followed by a significant correction, but the long-term trend has been consistently upward.",
        "source": "CoinGecko",
        "year": 2024
    },
    {
        "id": 14,
        "category": "trading",
        "icon": "fas fa-chart-line",
        "color": "#3b82f6",
        "fact": "The first regulated Bitcoin futures were launched on December 10, 2017, by CBOE, followed by CME Group on December 17, 2017. This marked Bitcoin's entry into traditional financial markets.",
        "detail": "The launch of Bitcoin futures was a watershed moment for cryptocurrency adoption by institutional investors. By 2024, multiple Bitcoin ETFs (Exchange-Traded Funds) have been approved, including spot Bitcoin ETFs in the United States in January 2024. BlackRock's iShares Bitcoin Trust (IBIT) became one of the most successful ETF launches in history, accumulating over $50 billion in assets within months.",
        "source": "CME Group",
        "year": 2017
    },
    {
        "id": 15,
        "category": "technology",
        "icon": "fas fa-cogs",
        "color": "#06b6d4",
        "fact": "Bitcoin's blockchain has never been hacked since its creation in 2009. However, hundreds of cryptocurrency exchanges and wallets have been compromised, resulting in billions in losses.",
        "detail": "The Bitcoin blockchain itself uses SHA-256 cryptographic hashing and Proof of Work consensus, making it computationally infeasible to alter past transactions. However, third-party services built on top of blockchain technology have been vulnerable. Notable exchange hacks include Mt. Gox ($450M in 2014), Bitfinex ($72M in 2016), and the Ronin Bridge hack ($625M in 2022).",
        "source": "Blockchain Security",
        "year": 2009
    },
    {
        "id": 16,
        "category": "technology",
        "icon": "fas fa-cogs",
        "color": "#06b6d4",
        "fact": "Layer 2 scaling solutions like rollups can process thousands of transactions per second while inheriting the security of the underlying Layer 1 blockchain.",
        "detail": "Optimistic Rollups (Arbitrum, Optimism) and Zero-Knowledge Rollups (zkSync, StarkNet) bundle hundreds of transactions off-chain and submit a single proof to the Layer 1 blockchain. This reduces gas fees by 10-100x while maintaining the security guarantees of Ethereum. Ethereum's L2 ecosystem now processes more transactions than the main chain itself.",
        "source": "L2Beat",
        "year": 2023
    },
    {
        "id": 17,
        "category": "regulation",
        "icon": "fas fa-gavel",
        "color": "#ef4444",
        "fact": "El Salvador became the first country to adopt Bitcoin as legal tender on September 7, 2021. The Central African Republic followed in April 2022, but later reversed its decision.",
        "detail": "El Salvador's Bitcoin Law was proposed by President Nayib Bukele and required all businesses to accept Bitcoin alongside the US Dollar. The government launched the Chivo wallet and gave citizens $30 in Bitcoin for downloading it. While adoption has been mixed, the move sparked a global debate about the role of cryptocurrency in national economies. The IMF has expressed concerns about the risks involved.",
        "source": "Government of El Salvador",
        "year": 2021
    },
    {
        "id": 18,
        "category": "regulation",
        "icon": "fas fa-gavel",
        "color": "#ef4444",
        "fact": "The SEC approved 11 spot Bitcoin ETFs on January 10, 2024, in a historic decision that opened the door for mainstream institutional investment in Bitcoin.",
        "detail": "After years of rejections, the SEC approved spot Bitcoin ETFs from major financial institutions including BlackRock, Fidelity, ARK Invest, and others. On the first day of trading, these ETFs saw over $4.6 billion in volume. This was seen as the most significant regulatory milestone for cryptocurrency, bringing Bitcoin to millions of traditional investors through their existing brokerage accounts.",
        "source": "U.S. SEC",
        "year": 2024
    },
    {
        "id": 19,
        "category": "web3",
        "icon": "fas fa-globe",
        "color": "#8b5cf6",
        "fact": "The term 'Web3' was coined by Ethereum co-founder Gavin Wood in 2014. It describes a vision of a decentralized internet built on blockchain technology.",
        "detail": "Web3 represents the next evolution of the internet, moving from static web pages (Web1) through user-generated content platforms (Web2) to a decentralized, user-owned internet (Web3). Key Web3 concepts include decentralization, token-based economics, and trustless interactions through smart contracts. Critics argue that Web3 is largely hype, while proponents believe it will fundamentally reshape how we interact online.",
        "source": "Web3 Foundation",
        "year": 2014
    },
    {
        "id": 20,
        "category": "web3",
        "icon": "fas fa-globe",
        "color": "#8b5cf6",
        "fact": "There are over 300 million cryptocurrency users worldwide as of 2024, with the number of blockchain wallets exceeding 500 million. Adoption continues to grow rapidly.",
        "detail": "Crypto adoption has accelerated significantly in recent years, driven by institutional investment, regulatory clarity, and improved user experience. Emerging markets in Africa, Southeast Asia, and Latin America lead in grassroots adoption, often driven by economic necessity. Chainalysis publishes an annual Global Crypto Adoption Index, with countries like India, Vietnam, and Nigeria consistently ranking at the top.",
        "source": "Chainalysis",
        "year": 2024
    },
    {
        "id": 21,
        "category": "bitcoin",
        "icon": "fab fa-bitcoin",
        "color": "#f7931a",
        "fact": "A Bitcoin halving occurs approximately every 4 years, reducing the block reward by half. As of 2024, there have been 4 halvings: 2012, 2016, 2020, and 2024. The block reward is now 3.125 BTC.",
        "detail": "Bitcoin halvings are programmed into the protocol to control inflation and enforce scarcity. Historically, halvings have preceded significant price increases, though past performance doesn't guarantee future results. The 2012 halving (50 to 25 BTC) was followed by a surge to $1,000. The 2016 halving (25 to 12.5 BTC) preceded the 2017 bull run to $20,000. The 2020 halving (12.5 to 6.25 BTC) preceded the 2021 all-time high of $69,000.",
        "source": "Bitcoin Protocol",
        "year": 2024
    },
    {
        "id": 22,
        "category": "defi",
        "icon": "fas fa-exchange-alt",
        "color": "#10b981",
        "fact": "Flash loans are one of DeFi's most innovative features. They allow users to borrow millions of dollars without collateral, as long as the loan is repaid within a single blockchain transaction.",
        "detail": "Flash loans were first introduced by Aave in January 2020. They work because blockchain transactions are atomic: either all operations succeed or all fail. A user can borrow $10 million, use it for arbitrage or liquidation, repay the loan with profit, and keep the difference - all in one transaction. If the repayment fails, the entire transaction is reverted. This innovation has spawned both legitimate strategies and exploits.",
        "source": "Aave Protocol",
        "year": 2020
    },
    {
        "id": 23,
        "category": "technology",
        "icon": "fas fa-cogs",
        "color": "#06b6d4",
        "fact": "The Ethereum Virtual Machine (EVM) has become the standard for smart contracts. Over 50 blockchains are now EVM-compatible, creating a large ecosystem of interoperable networks.",
        "detail": "The EVM is a runtime environment that executes smart contract bytecode. Its widespread adoption means that developers can write code once and deploy it across multiple EVM-compatible chains, including Ethereum, BNB Chain, Polygon, Avalanche, Arbitrum, and many others. This interoperability has been a key driver of the multi-chain future, with tools like MetaMask allowing users to seamlessly switch between networks.",
        "source": "Ethereum.org",
        "year": 2015
    },
    {
        "id": 24,
        "category": "trading",
        "icon": "fas fa-chart-line",
        "color": "#3b82f6",
        "fact": "Stablecoins now have a combined market capitalization exceeding $160 billion. USDT (Tether) and USDC (USD Coin) are the largest, with USDT alone exceeding $100 billion.",
        "detail": "Stablecoins are cryptocurrencies designed to maintain a stable value relative to a fiat currency, typically the US Dollar. They serve as the backbone of the crypto economy, enabling trading, lending, and value transfer without exposure to volatility. Despite concerns about Tether's reserves, USDT remains the most traded cryptocurrency after Bitcoin, with daily trading volumes often exceeding Bitcoin's.",
        "source": "CoinGecko",
        "year": 2024
    },
    {
        "id": 25,
        "category": "bitcoin",
        "icon": "fab fa-bitcoin",
        "color": "#f7931a",
        "fact": "The Bitcoin network processes approximately 7 transactions per second, while Visa can handle up to 65,000 TPS. However, Bitcoin's Lightning Network enables instant, low-cost payments at scale.",
        "detail": "Bitcoin's base layer deliberately prioritizes security and decentralization over speed. The Lightning Network, a Layer 2 payment protocol built on top of Bitcoin, enables instant micropayments by opening payment channels between users. As of 2024, the Lightning Network has over 5,000 BTC in capacity and is growing, with major companies like El Salvador's government and various payment processors integrating it for everyday transactions.",
        "source": "Lightning Network",
        "year": 2018
    },
    {
        "id": 26,
        "category": "nft",
        "icon": "fas fa-palette",
        "color": "#ec4899",
        "fact": "CryptoPunks, one of the earliest NFT projects, was launched in June 2017 by Larva Labs. Originally free to claim, some CryptoPunks have sold for over $20 million each.",
        "detail": "CryptoPunks consists of 10,000 unique 24x24 pixel art characters generated algorithmically. They are widely credited with starting the NFT craze. CryptoPunk #5822 sold for $23.7 million in February 2022, and #7523 sold for $11.8 million. Yuga Labs, the creators of Bored Ape Yacht Club, acquired the CryptoPunks IP in March 2022, further cementing their cultural significance.",
        "source": "Larva Labs / Yuga Labs",
        "year": 2017
    },
    {
        "id": 27,
        "category": "web3",
        "icon": "fas fa-globe",
        "color": "#8b5cf6",
        "fact": "DAOs (Decentralized Autonomous Organizations) manage billions in treasury assets. The largest DAO, Arbitrum DAO, controls over $3 billion in ARB tokens for ecosystem governance.",
        "detail": "DAOs are organizations governed by smart contracts rather than traditional management structures. Members vote on proposals using governance tokens, and decisions are executed automatically on-chain. Notable DAOs include MakerDAO ($2B+ in treasury), Uniswap DAO, and Lido DAO. The 2016 Ethereum hard fork that created Ethereum Classic was triggered by the DAO hack, where $60 million was stolen from The DAO.",
        "source": "DeepDAO",
        "year": 2024
    },
    {
        "id": 28,
        "category": "mining",
        "icon": "fas fa-microchip",
        "color": "#f59e0b",
        "fact": "The most powerful Bitcoin mining machine, the Bitmain Antminer S21, delivers 200 TH/s (terahashes per second) while consuming just 3,000 watts of electricity.",
        "detail": "Bitcoin mining hardware has evolved dramatically from CPU mining (2009) to GPU mining (2010) to FPGA mining (2011) and finally to ASIC mining (2013-present). Modern ASIC miners are specialized computers designed solely for SHA-256 hashing. The evolution of mining hardware reflects Bitcoin's growing hash rate, which has increased from millions of hashes per second in 2009 to over 600 exahashes per second in 2024.",
        "source": "Bitmain Technologies",
        "year": 2024
    },
    {
        "id": 29,
        "category": "regulation",
        "icon": "fas fa-gavel",
        "color": "#ef4444",
        "fact": "MiCA (Markets in Crypto-Assets Regulation), the European Union's comprehensive crypto framework, became fully applicable in December 2024, setting the standard for global crypto regulation.",
        "detail": "MiCA is the world's first comprehensive regulatory framework for cryptocurrencies. It covers stablecoins (e--money tokens and asset-referenced tokens), crypto exchanges, custody services, and token issuers. Key requirements include mandatory licensing, capital reserves, disclosure obligations, and consumer protection measures. MiCA is expected to influence regulatory approaches worldwide and has been praised for creating regulatory clarity.",
        "source": "European Commission",
        "year": 2024
    },
    {
        "id": 30,
        "category": "technology",
        "icon": "fas fa-cogs",
        "color": "#06b6d4",
        "fact": "Zero-Knowledge Proofs (ZKPs) allow one party to prove they know something without revealing the actual information. This technology is revolutionizing blockchain privacy and scalability.",
        "detail": "ZK-rollups like zkSync Era, StarkNet, and Polygon zkEVM use zero-knowledge proofs to batch transactions off-chain and submit validity proofs to Ethereum. This achieves both scalability (thousands of TPS) and privacy (shielded transactions). ZK technology is also being applied to identity verification, voting systems, and supply chain management. The field is considered one of the most promising areas of cryptographic research.",
        "source": "ZK Proof Research",
        "year": 2023
    },
]

# ─────────────────────────────────────────────
# QUIZ QUESTIONS DATABASE
# ─────────────────────────────────────────────

QUIZ_QUESTIONS = [
    {
        "id": 1,
        "difficulty": "easy",
        "category": "bitcoin",
        "question": "Who is the mysterious creator of Bitcoin?",
        "options": ["Vitalik Buterin", "Satoshi Nakamoto", "Hal Finney", "Nick Szabo"],
        "correct": 1,
        "explanation": "Satoshi Nakamoto is the pseudonymous creator of Bitcoin. Their true identity remains unknown despite years of speculation."
    },
    {
        "id": 2,
        "difficulty": "easy",
        "category": "bitcoin",
        "question": "What is the maximum supply of Bitcoin that will ever exist?",
        "options": ["10 million", "21 million", "100 million", "1 billion"],
        "correct": 1,
        "explanation": "Bitcoin's protocol hardcodes a maximum supply of 21 million BTC. This scarcity is enforced by the halving mechanism."
    },
    {
        "id": 3,
        "difficulty": "easy",
        "category": "general",
        "question": "What does 'HODL' mean in crypto slang?",
        "options": ["Hold On, Don't Leave", "Hold On for Dear Life", "Hold", "High On Digital Ledger"],
        "correct": 2,
        "explanation": "HODL originated from a misspelled forum post titled 'I AM HODLING' in December 2013. It has become a term for holding cryptocurrency long-term."
    },
    {
        "id": 4,
        "difficulty": "easy",
        "category": "trading",
        "question": "On what date did Laszlo Hanyecz famously buy two pizzas with Bitcoin?",
        "options": ["January 3, 2009", "May 22, 2010", "October 31, 2008", "February 11, 2011"],
        "correct": 1,
        "explanation": "May 22, 2010 is celebrated as 'Bitcoin Pizza Day.' Laszlo paid 10,000 BTC (now worth hundreds of millions) for two Papa John's pizzas."
    },
    {
        "id": 5,
        "difficulty": "easy",
        "category": "ethereum",
        "question": "What is Ethereum's native cryptocurrency called?",
        "options": ["Bitcoin", "Ether (ETH)", "Ripple (XRP)", "Solana (SOL)"],
        "correct": 1,
        "explanation": "Ethereum's native cryptocurrency is called Ether (ETH). It is used to pay for transaction fees (gas) and computational services on the network."
    },
    {
        "id": 6,
        "difficulty": "medium",
        "category": "bitcoin",
        "question": "What happens during a Bitcoin 'halving' event?",
        "options": [
            "Bitcoin's price is cut in half",
            "The block reward for miners is reduced by 50%",
            "The number of transactions is halved",
            "Bitcoin splits into two separate coins"
        ],
        "correct": 1,
        "explanation": "A halving reduces the block reward miners receive by 50%. This occurs approximately every 4 years (every 210,000 blocks) and reduces the rate of new BTC creation."
    },
    {
        "id": 7,
        "difficulty": "medium",
        "category": "ethereum",
        "question": "What major event occurred on Ethereum on September 15, 2022?",
        "options": [
            "Ethereum 2.0 launch",
            "The Merge (transition to Proof of Stake)",
            "Ethereum Classic hard fork",
            "EIP-1559 implementation"
        ],
        "correct": 1,
        "explanation": "'The Merge' transitioned Ethereum from Proof of Work to Proof of Stake, reducing energy consumption by 99.95%. It was the most significant upgrade in Ethereum's history."
    },
    {
        "id": 8,
        "difficulty": "medium",
        "category": "defi",
        "question": "What is a 'flash loan' in DeFi?",
        "options": [
            "A very small loan with low fees",
            "An uncollateralized loan that must be repaid within one transaction",
            "A loan that appears and disappears instantly",
            "A loan backed by flash memory hardware"
        ],
        "correct": 1,
        "explanation": "Flash loans allow borrowing without collateral, provided the loan is repaid within the same blockchain transaction. If repayment fails, the entire transaction is reverted."
    },
    {
        "id": 9,
        "difficulty": "medium",
        "category": "technology",
        "question": "What does EVM stand for?",
        "options": [
            "Exchange Value Machine",
            "Ethereum Virtual Machine",
            "Encrypted Value Module",
            "Electronic Verification Method"
        ],
        "correct": 1,
        "explanation": "The Ethereum Virtual Machine (EVM) is the runtime environment that executes smart contract bytecode. Over 50 blockchains are now EVM-compatible."
    },
    {
        "id": 10,
        "difficulty": "medium",
        "category": "trading",
        "question": "What is a 'stablecoin' designed to maintain?",
        "options": [
            "High volatility for profit",
            "A stable value relative to a fiat currency",
            "Maximum security against hacks",
            "The fastest transaction speed"
        ],
        "correct": 1,
        "explanation": "Stablecoins are cryptocurrencies pegged to stable assets like the US Dollar. Examples include USDT, USDC, and DAI, collectively worth over $160 billion."
    },
    {
        "id": 11,
        "difficulty": "medium",
        "category": "nft",
        "question": "Which NFT project, launched in 2017, is widely credited with starting the NFT craze?",
        "options": ["Bored Ape Yacht Club", "CryptoPunks", "Art Blocks", "Azuki"],
        "correct": 1,
        "explanation": "CryptoPunks by Larva Labs launched in June 2017 with 10,000 unique pixel art characters. Originally free to claim, some have sold for over $20 million."
    },
    {
        "id": 12,
        "difficulty": "medium",
        "category": "regulation",
        "question": "Which was the first country to adopt Bitcoin as legal tender?",
        "options": ["The United States", "Japan", "El Salvador", "Switzerland"],
        "correct": 2,
        "explanation": "El Salvador adopted Bitcoin as legal tender on September 7, 2021, becoming the first country to do so. The government launched the Chivo wallet and gave citizens $30 in Bitcoin."
    },
    {
        "id": 13,
        "difficulty": "hard",
        "category": "technology",
        "question": "What is the SHA-256 algorithm used for in Bitcoin?",
        "options": [
            "Encrypting wallet private keys",
            "Mining (Proof of Work hash function)",
            "Generating Bitcoin addresses",
            "Signing transactions"
        ],
        "correct": 1,
        "explanation": "SHA-256 is used in Bitcoin's Proof of Work consensus mechanism. Miners must find a hash below a target value, requiring enormous computational effort."
    },
    {
        "id": 14,
        "difficulty": "hard",
        "category": "defi",
        "question": "What is an 'impermanent loss' in DeFi liquidity provision?",
        "options": [
            "When a DeFi protocol is hacked",
            "Temporary loss compared to just holding the assets",
            "A permanent loss of funds due to smart contract bugs",
            "The fee charged by liquidity pools"
        ],
        "correct": 1,
        "explanation": "Impermanent loss occurs when providing liquidity to an AMM: if the price ratio of the paired tokens changes, the LP's position may be worth less than simply holding the tokens."
    },
    {
        "id": 15,
        "difficulty": "hard",
        "category": "technology",
        "question": "What type of cryptographic proof allows proving knowledge without revealing the information itself?",
        "options": [
            "Proof of Work",
            "Proof of Stake",
            "Zero-Knowledge Proof",
            "Merkle Proof"
        ],
        "correct": 2,
        "explanation": "Zero-Knowledge Proofs (ZKPs) enable one party to prove knowledge of information without revealing the information itself. ZK-rollups use this for scalable, private transactions."
    },
    {
        "id": 16,
        "difficulty": "hard",
        "category": "ethereum",
        "question": "What was the purpose of EIP-1559, implemented in August 2021?",
        "options": [
            "Enable smart contract creation",
            "Burn a portion of ETH fees, making ETH deflationary",
            "Increase the block size",
            "Enable staking rewards"
        ],
        "correct": 1,
        "explanation": "EIP-1559 introduced a base fee that gets burned with every transaction. This mechanism reduces ETH supply during high-usage periods, potentially making ETH deflationary."
    },
    {
        "id": 17,
        "difficulty": "hard",
        "category": "web3",
        "question": "What historic event in 2016 led to the creation of Ethereum Classic?",
        "options": [
            "The Parity wallet hack",
            "The DAO hack and subsequent hard fork",
            "The ICO bubble burst",
            "The Merge disagreement"
        ],
        "correct": 1,
        "explanation": "In June 2016, The DAO was hacked for $60 million. The Ethereum community voted to hard fork and reverse the hack, but a minority continued the original chain as 'Ethereum Classic.'"
    },
    {
        "id": 18,
        "difficulty": "hard",
        "category": "trading",
        "question": "What does the Fear & Greed Index measure in the crypto market?",
        "options": [
            "Trading volume trends",
            "Market volatility",
            "Market sentiment using multiple data points",
            "Exchange withdrawal rates"
        ],
        "correct": 2,
        "explanation": "The Crypto Fear & Greed Index analyzes market sentiment using volatility, market momentum, social media activity, surveys, and BTC dominance, scoring from 0 (Extreme Fear) to 100 (Extreme Greed)."
    },
    {
        "id": 19,
        "difficulty": "easy",
        "category": "general",
        "question": "What does 'DeFi' stand for?",
        "options": ["Digital Finance", "Decentralized Finance", "Dynamic Finance", "Distributed Finance"],
        "correct": 1,
        "explanation": "DeFi stands for Decentralized Finance, referring to financial services built on blockchain technology that operate without traditional intermediaries."
    },
    {
        "id": 20,
        "difficulty": "easy",
        "category": "general",
        "question": "What blockchain network does the USDC stablecoin primarily operate on?",
        "options": ["Bitcoin", "Solana", "Ethereum", "Cardano"],
        "correct": 2,
        "explanation": "USDC (USD Coin) was created by Circle and Coinbase and primarily operates on Ethereum, though it has expanded to multiple other blockchains including Solana and Avalanche."
    },
]


# ─────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────

FACT_CATEGORIES = [
    {"slug": "all", "name": "All Facts", "icon": "fas fa-globe", "color": "#22d3ee"},
    {"slug": "bitcoin", "name": "Bitcoin", "icon": "fab fa-bitcoin", "color": "#f7931a"},
    {"slug": "ethereum", "name": "Ethereum", "icon": "fab fa-ethereum", "color": "#627eea"},
    {"slug": "defi", "name": "DeFi", "icon": "fas fa-exchange-alt", "color": "#10b981"},
    {"slug": "nft", "name": "NFT", "icon": "fas fa-palette", "color": "#ec4899"},
    {"slug": "trading", "name": "Trading", "icon": "fas fa-chart-line", "color": "#3b82f6"},
    {"slug": "mining", "name": "Mining", "icon": "fas fa-microchip", "color": "#f59e0b"},
    {"slug": "technology", "name": "Technology", "icon": "fas fa-cogs", "color": "#06b6d4"},
    {"slug": "regulation", "name": "Regulation", "icon": "fas fa-gavel", "color": "#ef4444"},
    {"slug": "web3", "name": "Web3", "icon": "fas fa-globe", "color": "#8b5cf6"},
]

QUIZ_DIFFICULTIES = [
    {"slug": "all", "name": "All Levels", "icon": "fas fa-layer-group", "color": "#22d3ee"},
    {"slug": "easy", "name": "Easy", "icon": "fas fa-seedling", "color": "#34d399"},
    {"slug": "medium", "name": "Medium", "icon": "fas fa-bolt", "color": "#fbbf24"},
    {"slug": "hard", "name": "Hard", "icon": "fas fa-fire", "color": "#f87171"},
]


def get_facts(category=None, limit=20):
    """Get crypto facts, optionally filtered by category."""
    facts = CRYPTO_FACTS
    if category and category != "all":
        facts = [f for f in facts if f["category"] == category]
    random.shuffle(facts)
    return facts[:limit]


def get_daily_fact():
    """Get a fact of the day based on the current date."""
    day_of_year = datetime.utcnow().timetuple().tm_yday
    index = (day_of_year - 1) % len(CRYPTO_FACTS)
    return CRYPTO_FACTS[index]


def get_random_fact(category=None):
    """Get a single random fact."""
    facts = CRYPTO_FACTS
    if category and category != "all":
        facts = [f for f in facts if f["category"] == category]
    return random.choice(facts) if facts else None


def get_quiz_questions(difficulty=None, category=None, limit=10):
    """Get quiz questions, optionally filtered by difficulty and category."""
    questions = QUIZ_QUESTIONS
    if difficulty and difficulty != "all":
        questions = [q for q in questions if q["difficulty"] == difficulty]
    if category and category != "all":
        questions = [q for q in questions if q["category"] == category]
    random.shuffle(questions)
    return questions[:limit]


def get_quiz_stats():
    """Get quiz database statistics."""
    categories = set(q["category"] for q in QUIZ_QUESTIONS)
    difficulties = {"easy": 0, "medium": 0, "hard": 0}
    for q in QUIZ_QUESTIONS:
        difficulties[q["difficulty"]] += 1
    return {
        "total_questions": len(QUIZ_QUESTIONS),
        "total_facts": len(CRYPTO_FACTS),
        "categories": len(categories),
        "difficulties": difficulties,
    }


def get_fact_stats():
    """Get facts database statistics."""
    categories = {}
    for f in CRYPTO_FACTS:
        cat = f["category"]
        categories[cat] = categories.get(cat, 0) + 1
    years = set(f["year"] for f in CRYPTO_FACTS)
    return {
        "total_facts": len(CRYPTO_FACTS),
        "categories": categories,
        "year_range": f"{min(years)}-{max(years)}",
    }
