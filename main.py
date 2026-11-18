"""Dip-buy mean-reversion bot for cbBTC (CBBTC/USDC), agent-fun/bars-replay/v1.

The idea: 1-minute BTC bars are noisy, and a full-size round trip costs about
30 bps in fees, slippage and pool impact, so the bot trades rarely and only
for moves well above that cost. It waits for a sharp dip below the 60-minute
average price, wants proof the dip has stopped falling (the close bounces at
least 10 bps off the low of the last 5 bars), then buys with all its cash and
holds for a 150 bps recovery, with an 80 bps stop-loss. It never shorts, never
uses leverage, holds at most one position, and stops opening new trades in the
last 60 bars of the 1,440-bar window, where a 150 bps target has no time to
complete and the forced end-of-window sale would eat the edge.

Tuned on the frozen 24h dev window (local replay, exact fill model): net PnL
+$20.97 on $1,000, 4 trades, max drawdown 0.65%. Neighbouring parameters
(dip 40-50 bps, bounce 5-15 bps, take-profit 130-170 bps, stop 60-100 bps)
are all profitable on the same window, so the edge is not one lucky setting.

Deterministic: decisions depend only on the bars and the account the harness
sends. No wall clock, no network, no files, no randomness.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars  # noqa: E402  (vendored kit SDK shim, byte-for-byte)

SYMBOL = "CBBTC"

#: Bars in the moving average the dip is measured against.
SMA_BARS = 60
#: How far below the moving average the close must sit to count as a dip.
DIP_BPS = 45
#: Bars back over which the bounce low is taken.
BOUNCE_BARS = 5
#: How far the close must have bounced off that low to count as stabilised.
BOUNCE_BPS = 10
#: Take profit and stop-loss, measured from the close the buy was decided on.
TAKE_PROFIT_BPS = 150
STOP_LOSS_BPS = 80
#: Bars of history needed before the first trade (SMA window + bounce window).
MIN_BARS = SMA_BARS + BOUNCE_BARS + 1
#: No new entries once this many bars have been seen (the window is 1,440).
LAST_ENTRY_BAR = 1380
#: Slippage cap on every order, 1% past the close it was decided on.
MAX_SLIPPAGE_BPS = 100


class DipBuyer:
    """One asset, one position: buy sharp dips that have stopped falling."""

    def __init__(self):
        #: Closes in bar order (price-scale integers, as the harness sends them).
        self.closes = []
        #: The close the current position's buy was decided on (None when flat).
        self.entry_close = None
        #: Scales from hello, for the cost-basis fallback (set by on_hello).
        self.price_scale = 5
        self.qty_scale = 8
        self.quote_scale = 6

    def on_hello(self, state):
        for s in state.hello["symbols"]:
            if s["symbol"] == SYMBOL:
                self.price_scale = s["price_scale"]
                self.qty_scale = s["qty_scale"]
        self.quote_scale = state.hello["capital"]["quote_scale"]

    def _sma(self):
        return sum(self.closes[-SMA_BARS:]) / SMA_BARS

    def _dip_bps(self, close):
        return (self._sma() / close - 1) * 10_000

    def _bounced(self, close):
        low = min(self.closes[-BOUNCE_BARS - 1:-1])
        return close >= low * (1 + BOUNCE_BPS / 10_000)

    def _pnl_bps(self, close):
        return (close / self.entry_close - 1) * 10_000

    def on_batch(self, state, batch):
        fresh = False
        for bar in batch["bars"]:
            if bar["symbol"] == SYMBOL:
                self.closes.append(int(bar["c"]))
                fresh = True
        if not fresh or state.warming_up:
            return []
        if len(self.closes) < MIN_BARS:
            return []

        close = self.closes[-1]
        held = state.positions.get(SYMBOL)
        if held is not None:
            if self.entry_close is None:
                # A position with no remembered entry (e.g. a replayed fill):
                # fall back to its cost basis as the entry reference.
                if held.qty:
                    self.entry_close = (
                        held.cost
                        * 10 ** (self.qty_scale + self.price_scale)
                        // (held.qty * 10**self.quote_scale)
                    )
                else:
                    self.entry_close = close
            pnl = self._pnl_bps(close)
            if pnl >= TAKE_PROFIT_BPS or pnl <= -STOP_LOSS_BPS:
                return [
                    {
                        "side": "sell",
                        "symbol": SYMBOL,
                        "qty": held.qty,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }
                ]
            return []

        # Flat: a buy that never filled leaves no position, so forget its entry.
        self.entry_close = None
        if len(self.closes) - 1 >= LAST_ENTRY_BAR:
            return []
        if self._dip_bps(close) < DIP_BPS:
            return []
        if not self._bounced(close):
            return []
        min_notional = int(state.hello["fees"]["min_notional_quote_units"])
        if state.cash < min_notional:
            return []
        self.entry_close = close
        return [
            {
                "side": "buy",
                "symbol": SYMBOL,
                "notional_quote_units": state.cash,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }
        ]


bot = DipBuyer()
makefun_bars.run(bot.on_batch, on_hello=bot.on_hello)
