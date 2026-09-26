from core.brain.chat_agent import decide, parse_buyer_offer
from core.contracts import NegotiationState


def test_accept_at_suggested():
    decision = decide("s1", 2000, 2000, 1700, 1)
    assert decision.next_state == NegotiationState.ACCEPT
    assert decision.should_send is True
    assert decision.quoted_price == 2000


def test_reject_far_below_floor():
    decision = decide("s1", 1500, 2000, 1700, 1)
    assert decision.next_state == NegotiationState.REJECT
    assert decision.should_send is True
    assert decision.quoted_price is None
    assert "1700" not in decision.reply_text


def test_reject_near_miss_invites_raise():
    decision = decide("s1", 1650, 2000, 1700, 1)
    assert decision.next_state == NegotiationState.REJECT
    assert decision.should_send is True
    assert decision.quoted_price is None
    assert "1650" not in decision.reply_text
    assert "1700" not in decision.reply_text


def test_stalled_below_floor_needs_human():
    decision = decide("s1", 1500, 2000, 1700, 3)
    assert decision.next_state == NegotiationState.NEED_HUMAN
    assert decision.should_send is False


def test_second_round_near_miss_offers_express():
    decision = decide("s1", 1650, 2000, 1700, 2)
    assert decision.next_state == NegotiationState.REJECT
    assert decision.should_send is True
    assert decision.quoted_price is None
    assert "今天" in decision.reply_text
    assert "1650" not in decision.reply_text
    assert "1700" not in decision.reply_text


def test_second_round_lowball_stays_flat():
    decision = decide("s1", 1500, 2000, 1700, 2)
    assert decision.next_state == NegotiationState.REJECT
    assert decision.should_send is True


def test_zero_offer_needs_human():
    decision = decide("s1", 0, 2000, 1700, 1)
    assert decision.next_state == NegotiationState.NEED_HUMAN
    assert decision.should_send is False


def test_round1_counters_near_suggested():
    decision = decide("s1", 1800, 2000, 1700, 1)
    assert decision.next_state == NegotiationState.COUNTER_OFFER_1
    assert decision.quoted_price == 1910


def test_round2_counters_near_floor():
    decision = decide("s1", 1800, 2000, 1700, 2)
    assert decision.next_state == NegotiationState.COUNTER_OFFER_2
    assert decision.quoted_price == 1790
    assert "寄出" in decision.reply_text


def test_round3_accepts_in_range_offer():
    decision = decide("s1", 1800, 2000, 1700, 3)
    assert decision.next_state == NegotiationState.FINAL_OFFER
    assert decision.quoted_price == 1800
    assert decision.should_send is True


def test_unparseable_offer_needs_human():
    decision = decide("s1", None, 2000, 1700, 1)
    assert decision.next_state == NegotiationState.NEED_HUMAN
    assert decision.should_send is False


def test_counter_never_below_floor():
    decision = decide("s1", 1005, 1010, 1000, 1)
    assert decision.quoted_price >= 1000
    assert decision.quoted_price <= 1010


def test_parse_single_amount():
    assert parse_buyer_offer("1800 可以嗎") == 1800
    assert parse_buyer_offer("1,800 元") == 1800


def test_parse_ambiguous_returns_none():
    assert parse_buyer_offer("原本 2000 賣 1800 好嗎") is None
    assert parse_buyer_offer("請問還有嗎") is None
