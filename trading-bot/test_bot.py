import pytest

from bot import Bot, make_exchange
from strategy import crossover_signal

CFG = {
    "symbol": "BTC/USDT", "timeframe": "5m", "fast": 2, "slow": 4,
    "order_usdt": 100, "min_position_usdt": 5,
    "api_key": "k", "secret": "s", "password": "p",
}


def test_signal_buy_sell_none():
    assert crossover_signal([10, 10, 10, 10, 20], 2, 4) == "buy"
    assert crossover_signal([10, 10, 10, 10, 1], 2, 4) == "sell"
    assert crossover_signal([10, 11, 12, 13, 14], 2, 4) is None
    assert crossover_signal([10, 20], 2, 4) is None


class FakeExchange:
    def __init__(self, closes, balance):
        self.closes = closes
        self.balance = balance
        self.orders = []

    def fetch_ohlcv(self, symbol, timeframe, limit):
        # Last row is the still-forming candle.
        rows = [[i * 300_000, 0, 0, 0, c, 0] for i, c in enumerate(self.closes)]
        return rows + [[len(rows) * 300_000, 0, 0, 0, 999, 0]]

    def fetch_balance(self):
        return {"free": self.balance}

    def amount_to_precision(self, symbol, amount):
        return f"{amount:.8f}"

    def create_market_buy_order_with_cost(self, symbol, cost):
        self.orders.append(("buy", cost))
        return {"id": "1"}

    def create_market_sell_order(self, symbol, amount):
        self.orders.append(("sell", amount))
        return {"id": "2"}


def test_buys_when_flat():
    ex = FakeExchange([10, 10, 10, 10, 20], {"USDT": 1000, "BTC": 0})
    assert Bot(ex, CFG).step() == "buy"
    assert ex.orders == [("buy", 100)]


def test_does_not_rebuy_when_in_position():
    ex = FakeExchange([10, 10, 10, 10, 20], {"USDT": 1000, "BTC": 1})
    assert Bot(ex, CFG).step() is None
    assert ex.orders == []


def test_sells_whole_position():
    ex = FakeExchange([10, 10, 10, 10, 1], {"USDT": 0, "BTC": 6})
    assert Bot(ex, CFG).step() == "sell"
    assert ex.orders == [("sell", 6.0)]


def test_same_candle_processed_once():
    ex = FakeExchange([10, 10, 10, 10, 20], {"USDT": 1000, "BTC": 0})
    bot = Bot(ex, CFG)
    bot.step()
    assert bot.step() is None
    assert len(ex.orders) == 1


def test_dry_run_sends_nothing():
    ex = FakeExchange([10, 10, 10, 10, 20], {"USDT": 1000, "BTC": 0})
    assert Bot(ex, CFG, dry_run=True).step() == "buy"
    assert ex.orders == []


def test_exchange_is_in_demo_mode():
    ex = make_exchange(CFG)
    assert ex.headers["x-simulated-trading"] == "1"
