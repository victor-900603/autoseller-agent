import statistics

from core.contracts import Condition, MarketQuote

_MIN_CONFIDENT_SAMPLES = 5
_PRICE_STEP = 10

_CONDITION_DISCOUNTS = {
    "全新": 0.0,
    "9成新": 0.10,
    "輕微使用痕跡": 0.25,
}


def summarize(prices: list[int], sources: list[str] | None = None) -> MarketQuote:
    """剔除最高最低各一成後取四分位，零樣本拋錯、不足五筆標低信心。"""
    if not prices:
        raise ValueError("無價格樣本")
    ordered = sorted(prices)
    cut = int(len(ordered) * 0.1)
    trimmed = ordered[cut : len(ordered) - cut] if cut else ordered
    if len(trimmed) < 2:
        only = trimmed[0]
        quartiles = (only, only, only)
    else:
        quartiles = statistics.quantiles(trimmed, n=4)
    return MarketQuote(
        p25=int(round(quartiles[0])),
        p50=int(round(quartiles[1])),
        p75=int(round(quartiles[2])),
        sample_count=len(prices),
        sources=list(sources or []),
        low_confidence=len(prices) < _MIN_CONFIDENT_SAMPLES,
    )


def apply_condition_discount(p50: int, condition: Condition) -> int:
    """按成色折扣計算建議價，捨入至十位數。"""
    discounted = p50 * (1 - _CONDITION_DISCOUNTS[condition])
    return int(round(discounted / _PRICE_STEP) * _PRICE_STEP)


def apply_floor(suggested_price: int, floor_ratio: float) -> int:
    """建議價乘係數得底價，係數由呼叫端傳入。"""
    return int(round(suggested_price * floor_ratio))
