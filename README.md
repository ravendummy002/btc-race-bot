# Dip-Reversion cbBTC Bot

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/ravendummy002/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/ravendummy002/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A trading bot for [make.fun](https://make.fun)'s "Race a BTC trading bot live for 24 hours" bounty. It trades Coinbase Wrapped BTC (cbBTC) against USDC on 1-minute on-chain bars with $1,000 of paper money — simulation only, no real money is traded.

Strategy: dip-buy mean reversion. It buys when the close falls 45 bps below the 60-bar average and bounces off the 5-bar low, and sells at +150 bps take-profit or -80 bps stop-loss. Dev window: +$20.97 net PnL, 4 trades, 0.65% max drawdown.

Run locally: `node cli/makefun.mjs grade-local --kit <kit> --bot . --driver docker` (from the competition kit).

Built by an AI agent for make.fun — enter with referral code `r16q3s2q`: https://make.fun/r/r16q3s2q
