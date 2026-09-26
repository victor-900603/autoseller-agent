from core.brain.safety_guard import max_mentioned_price, reply_passes_guard


def test_below_floor_blocked():
    assert reply_passes_guard("那 1500 元賣你", 1700) is False


def test_equal_floor_passes():
    assert reply_passes_guard("底價 1700 元", 1700) is True


def test_multiple_amounts_judged_by_max():
    assert reply_passes_guard("原本 2000，現在 1800 就好", 1700) is True
    assert reply_passes_guard("原本 2000，現在 1600 就好", 1700) is True


def test_no_amount_passes():
    assert reply_passes_guard("謝謝詢問，歡迎直接下單", 1700) is True


def test_comma_amounts_parsed():
    assert max_mentioned_price("1,800 元") == 1800


def test_no_amount_returns_none():
    assert max_mentioned_price("歡迎詢問") is None
