"""SMA crossover strategy: pure functions, no exchange access."""


def sma(values, period):
    return sum(values[-period:]) / period


def crossover_signal(closes, fast, slow):
    """Return 'buy', 'sell' or None based on the last two closed candles.

    'buy'  when the fast SMA crosses above the slow SMA,
    'sell' when it crosses below.
    """
    if fast >= slow:
        raise ValueError("fast period must be smaller than slow period")
    if len(closes) < slow + 1:
        return None
    prev, curr = closes[:-1], closes
    prev_diff = sma(prev, fast) - sma(prev, slow)
    curr_diff = sma(curr, fast) - sma(curr, slow)
    if prev_diff <= 0 < curr_diff:
        return "buy"
    if prev_diff >= 0 > curr_diff:
        return "sell"
    return None
