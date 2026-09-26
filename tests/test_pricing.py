import pytest

from core.brain.pricing_agent import apply_condition_discount, apply_floor, summarize
from core.brain.search_provider import MockSearchProvider


def test_quartiles_without_trimming():
    quote = summarize([100, 200, 300, 400, 500, 600, 700, 800, 900])
    assert (quote.p25, quote.p50, quote.p75) == (250, 500, 750)
    assert quote.sample_count == 9
    assert quote.low_confidence is False


def test_extremes_trimmed():
    quote = summarize([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000])
    assert (quote.p25, quote.p50, quote.p75) == (325, 550, 775)


def test_low_confidence_flagged():
    quote = summarize([1000, 2000, 3000])
    assert quote.low_confidence is True
    assert (quote.p25, quote.p50, quote.p75) == (1000, 2000, 3000)


def test_single_sample_reused():
    quote = summarize([1500])
    assert (quote.p25, quote.p50, quote.p75) == (1500, 1500, 1500)
    assert quote.low_confidence is True


def test_empty_prices_rejected():
    with pytest.raises(ValueError):
        summarize([])


def test_condition_discounts():
    assert apply_condition_discount(2000, "全新") == 2000
    assert apply_condition_discount(2000, "9成新") == 1800
    assert apply_condition_discount(2000, "輕微使用痕跡") == 1500


def test_discount_rounds_to_tens():
    assert apply_condition_discount(1999, "全新") == 2000


def test_floor_ratio():
    assert apply_floor(2000, 0.85) == 1700


def test_mock_search_feeds_pricing():
    provider = MockSearchProvider([1000, 2000, 3000], ["s1"])
    results = provider.search("Logitech MX Master 3S")
    quote = summarize(results.prices, results.sources)
    assert quote.p50 == 2000
    assert quote.sources == ["s1"]
