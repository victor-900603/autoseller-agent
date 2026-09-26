import pytest
from pydantic import ValidationError

from core.contracts import ChatDecision, ListingContract, NegotiationState


def _listing(**overrides):
    data = {
        "product_id": "p001",
        "title": "Logitech MX Master 3S 無線滑鼠",
        "category_id": "電腦周邊",
        "condition": "9成新",
        "suggested_price": 2000,
        "floor_price": 1700,
        "description": "功能正常，底部有輕微使用痕跡。",
        "image_paths": ["img1.jpg"],
    }
    data.update(overrides)
    return ListingContract(**data)


def test_valid_listing():
    assert _listing().floor_price == 1700


def test_title_too_long():
    with pytest.raises(ValidationError):
        _listing(title="x" * 61)


def test_invalid_condition():
    with pytest.raises(ValidationError):
        _listing(condition="全新未拆")


def test_floor_above_suggested():
    with pytest.raises(ValidationError):
        _listing(floor_price=2100)


def test_image_paths_empty():
    with pytest.raises(ValidationError):
        _listing(image_paths=[])


def test_image_paths_over_limit():
    with pytest.raises(ValidationError):
        _listing(image_paths=[f"img{i}.jpg" for i in range(11)])


def test_decision_requires_reply_when_sending():
    with pytest.raises(ValidationError):
        ChatDecision(session_id="s1", next_state=NegotiationState.ACCEPT, should_send=True)


def test_silent_decision_allowed():
    decision = ChatDecision(session_id="s1", next_state=NegotiationState.NEED_HUMAN)
    assert decision.should_send is False
