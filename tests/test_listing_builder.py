import pytest

from core.brain.listing_builder import (
    LowConfidenceError,
    build_description,
    build_listing,
    build_title,
)
from core.contracts import MarketQuote, VisionResult


def _vision(**overrides):
    data = {
        "detected_brand": "Logitech",
        "detected_model": "MX Master 3S",
        "condition_grade": "9_out_of_10",
        "defects_noted": ["底部腳貼有輕微摩擦痕跡"],
        "inclusions": ["原廠接收器"],
    }
    data.update(overrides)
    return VisionResult(**data)


def _quote(**overrides):
    data = {
        "p25": 1500,
        "p50": 2000,
        "p75": 2500,
        "sample_count": 9,
        "sources": ["s1"],
        "low_confidence": False,
    }
    data.update(overrides)
    return MarketQuote(**data)


def test_title_with_extra():
    title = build_title("Logitech", "MX Master 3S", "原廠接收器")
    assert title == "Logitech MX Master 3S 原廠接收器"


def test_title_drops_extra_when_long():
    title = build_title("Logitech", "MX Master 3S", "x" * 60)
    assert title == "Logitech MX Master 3S"


def test_title_hard_cut():
    title = build_title("B" * 40, "M" * 40)
    assert len(title) == 60


def test_description_sections():
    text = build_description(_vision(), "賣家寄送")
    assert "【成色】9成新" in text
    assert "底部腳貼有輕微摩擦痕跡" in text
    assert "原廠接收器" in text
    assert "【交易方式】賣家寄送" in text


def test_description_empty_lists():
    text = build_description(_vision(defects_noted=[], inclusions=[]), "面交")
    assert "無明顯瑕疵" in text
    assert "僅商品本體" in text


def test_build_listing_wires_price():
    listing = build_listing("p1", "電腦周邊", _vision(), _quote(), ["a.jpg"], 0.85, "賣家寄送")
    assert listing.suggested_price == 1800
    assert listing.floor_price == 1530
    assert listing.condition == "9成新"


def test_build_listing_rejects_low_confidence():
    with pytest.raises(LowConfidenceError):
        build_listing(
            "p1", "電腦周邊", _vision(), _quote(low_confidence=True), ["a.jpg"], 0.85, "寄送"
        )
