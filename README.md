# Virgolino: Polymarket Swing Trading Bot 🚀

Virgolino is an automated trading bot designed for Polymarket 15-minute binary markets. It utilizes technical analysis (RSI, Bollinger Bands) and price divergence monitoring to execute swing trades on BTC and ETH markets.

## 🌟 Key Features

- **Strict 15-Minute Filtering:** Targeted execution on 15-minute binary markets only.
- **Golden Window Logic:** Entries restricted to the "Golden Window" (Minute 2 to Minute 12 of the contract) to avoid opening volatility and closing gamma risk.
- **Dynamic Risk Management:** 
  - Automatic 30% Take Profit (TP).
  - Dynamic stake sizing based on portfolio balance.
  - Max positions limited to 2 (one per asset).
- **Auto-Settlement:** Automatic memory cleanup after market resolution and USDC balance synchronization.
- **Transparency:** Comprehensive logging of market questions, entry prices, and execution signals.

## 🛠 Setup

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd virgolino
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration:**
   Create a `.env` file in the root directory and add your credentials:
   ```env
   POLYMARKET_API_KEY=your_api_key
   POLYMARKET_SECRET=your_secret
   POLYMARKET_PASSPHRASE=your_passphrase
   PRIVATE_KEY=your_wallet_private_key
   PROFILE_ADDRESS=your_wallet_address
   ```

## 🚀 Running the Bot

To start the bot in background mode:
```bash
nohup python3 bot.py > bot.log 2>&1 &
```

Monitor logs in real-time:
```bash
tail -f bot.log
```

## 📈 Strategy Overview

The bot monitors **Divergence** between spot prices (Binance) and Polymarket odds:
- **UP Signal:** RSI < 30 (Oversold) + Price near support or Lower Bollinger Band + Odds showing undervaluation.
- **DOWN Signal:** RSI > 70 (Overbought) + Price near resistance or Upper Bollinger Band + Odds showing overvaluation.

## ⚖️ Disclaimer

Trading involves risk. This bot is provided for educational and research purposes. Always trade with caution and capital you can afford to lose.
