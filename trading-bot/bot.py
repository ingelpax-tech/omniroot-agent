"""Spot trading bot for OKX Demo Trading (simulated money only).

Usage:
    python bot.py            # run forever, one decision per closed candle
    python bot.py --once     # evaluate the latest candle and exit
    python bot.py --dry-run  # log orders instead of sending them
"""

import argparse
import logging
import os
import time

import ccxt
from dotenv import load_dotenv

from strategy import crossover_signal

log = logging.getLogger("okx-bot")


def load_config():
    load_dotenv()
    return {
        "api_key": os.environ["OKX_API_KEY"],
        "secret": os.environ["OKX_API_SECRET"],
        "password": os.environ["OKX_API_PASSPHRASE"],
        "symbol": os.getenv("SYMBOL", "BTC/USDT"),
        "timeframe": os.getenv("TIMEFRAME", "5m"),
        "fast": int(os.getenv("SMA_FAST", "9")),
        "slow": int(os.getenv("SMA_SLOW", "21")),
        "order_usdt": float(os.getenv("ORDER_USDT", "100")),
        "min_position_usdt": float(os.getenv("MIN_POSITION_USDT", "5")),
    }


def make_exchange(cfg):
    ex = ccxt.okx({
        "apiKey": cfg["api_key"],
        "secret": cfg["secret"],
        "password": cfg["password"],
        "enableRateLimit": True,
    })
    # Sends the `x-simulated-trading: 1` header: every call hits the demo account.
    ex.set_sandbox_mode(True)
    if ex.headers.get("x-simulated-trading") != "1":
        raise RuntimeError("Demo mode is not active; refusing to trade real funds.")
    return ex


class Bot:
    def __init__(self, exchange, cfg, dry_run=False):
        self.ex = exchange
        self.cfg = cfg
        self.dry_run = dry_run
        self.last_candle_ts = None
        self.base, self.quote = cfg["symbol"].split("/")

    def step(self):
        """Evaluate the latest closed candle once. Returns the action taken."""
        cfg = self.cfg
        ohlcv = self.ex.fetch_ohlcv(cfg["symbol"], cfg["timeframe"], limit=cfg["slow"] + 3)
        closed = ohlcv[:-1]  # last candle is still forming
        if not closed or closed[-1][0] == self.last_candle_ts:
            return None
        self.last_candle_ts = closed[-1][0]

        closes = [c[4] for c in closed]
        price = closes[-1]
        signal = crossover_signal(closes, cfg["fast"], cfg["slow"])

        balance = self.ex.fetch_balance()
        base_free = balance["free"].get(self.base) or 0
        quote_free = balance["free"].get(self.quote) or 0
        in_position = base_free * price >= cfg["min_position_usdt"]
        log.info("price=%.2f signal=%s %s=%.6f %s=%.2f",
                 price, signal, self.base, base_free, self.quote, quote_free)

        if signal == "buy" and not in_position:
            cost = min(cfg["order_usdt"], quote_free)
            if cost < cfg["min_position_usdt"]:
                log.warning("Not enough %s to buy (%.2f)", self.quote, quote_free)
                return None
            return self._order("buy", cost)
        if signal == "sell" and in_position:
            return self._order("sell", float(self.ex.amount_to_precision(cfg["symbol"], base_free)))
        return None

    def _order(self, side, qty):
        symbol = self.cfg["symbol"]
        unit = self.quote if side == "buy" else self.base
        if self.dry_run:
            log.info("[dry-run] %s %s for %s %s", side, symbol, qty, unit)
            return side
        if side == "buy":
            order = self.ex.create_market_buy_order_with_cost(symbol, qty)
        else:
            order = self.ex.create_market_sell_order(symbol, qty)
        log.info("Order sent: %s %s %s %s id=%s", side, symbol, qty, unit, order.get("id"))
        return side

    def run(self):
        period = self.ex.parse_timeframe(self.cfg["timeframe"])
        while True:
            try:
                self.step()
            except ccxt.NetworkError as e:
                log.warning("Network error, retrying next cycle: %s", e)
            except ccxt.ExchangeError as e:
                log.error("Exchange error: %s", e)
            # Wake a few seconds after the next candle closes.
            time.sleep(period - time.time() % period + 5)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--once", action="store_true", help="run a single evaluation and exit")
    parser.add_argument("--dry-run", action="store_true", help="log orders instead of sending them")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config()
    bot = Bot(make_exchange(cfg), cfg, dry_run=args.dry_run)
    log.info("OKX demo bot started: %s %s SMA %d/%d, %.0f %s per trade",
             cfg["symbol"], cfg["timeframe"], cfg["fast"], cfg["slow"], cfg["order_usdt"], bot.quote)
    if args.once:
        bot.step()
    else:
        bot.run()


if __name__ == "__main__":
    main()
