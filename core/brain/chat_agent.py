import re

from core.brain.safety_guard import extract_amounts
from core.contracts import ChatDecision, NegotiationState

_COUNTER_STEP = 10
_NEAR_MISS_RATIO = 0.95
_STALLED_ROUND = 3
_R1_KEEP_RATIO = 0.7
_R2_KEEP_RATIO = 0.3

_FIRST_ROUND = 1
_SECOND_ROUND = 2
_LATE_ROUND = 3

_ABOVE = "above"
_IN_RANGE = "in_range"
_NEAR_MISS = "near_miss"
_LOWBALL = "lowball"


def parse_buyer_offer(text: str) -> int | None:
    """解析買家出價，恰為一個金額才回傳（先剔除日期時間）。"""
    amounts = extract_amounts(re.sub(r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}", "", text))
    if len(amounts) != 1:
        return None
    return amounts[0]


def _counter_price(suggested_price: int, floor_price: int, keep_ratio: float) -> int:
    """按保留比例計算還價，捨入至十位數並箝制於底價與建議價之間。"""
    raw = floor_price + (suggested_price - floor_price) * keep_ratio
    rounded = int(round(raw / _COUNTER_STEP) * _COUNTER_STEP)
    return min(suggested_price, max(floor_price, rounded))


def _classify_zone(buyer_offer: int, suggested_price: int, floor_price: int) -> str:
    """將出價歸入高於建議價、區間內、接近底價、明顯偏低四區。"""
    if buyer_offer >= suggested_price:
        return _ABOVE
    if buyer_offer >= floor_price:
        return _IN_RANGE
    if buyer_offer >= floor_price * _NEAR_MISS_RATIO:
        return _NEAR_MISS
    return _LOWBALL


def _round_bucket(negotiation_round: int) -> int:
    """將輪次歸入首輪、次輪、第三輪以上三桶。"""
    if negotiation_round <= _FIRST_ROUND:
        return _FIRST_ROUND
    if negotiation_round == _SECOND_ROUND:
        return _SECOND_ROUND
    return _LATE_ROUND


def _defer_to_human(session_id: str, *_) -> ChatDecision:
    """轉人工，不發送。"""
    return ChatDecision(session_id=session_id, next_state=NegotiationState.NEED_HUMAN)


def _accept(session_id: str, buyer_offer: int, *_) -> ChatDecision:
    """接受出價，引導下單。"""
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.ACCEPT,
        reply_text=f"好的，{buyer_offer} 元沒問題，再麻煩直接下單，謝謝。",
        quoted_price=buyer_offer,
        should_send=True,
    )


def _accept_final(session_id: str, buyer_offer: int, *_) -> ChatDecision:
    """最終輪接受區間內出價。"""
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.FINAL_OFFER,
        reply_text=f"好，那就 {buyer_offer} 元成交，再麻煩直接下單，謝謝。",
        quoted_price=buyer_offer,
        should_send=True,
    )


def _reject_flat(session_id: str, *_) -> ChatDecision:
    """直接拒絕，不揭露數字。"""
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.REJECT,
        reply_text="不好意思，這個價格沒辦法接受，謝謝你的詢問。",
        should_send=True,
    )


def _reject_invite(session_id: str, *_) -> ChatDecision:
    """接近底價時邀請加價，不揭露數字。"""
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.REJECT,
        reply_text="不好意思，這個價格還差一點，你方便再加一點嗎。",
        should_send=True,
    )


def _reject_invite_express(session_id: str, *_) -> ChatDecision:
    """次輪接近底價時以今日可確定為誘因邀請加價。"""
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.REJECT,
        reply_text="不好意思，這個價格還差一點，如果今天能確定的話，我這邊比較好談。",
        should_send=True,
    )


def _counter_first(
    session_id: str, _offer: int, suggested_price: int, floor_price: int
) -> ChatDecision:
    """首輪還價，保留七成差價。"""
    price = _counter_price(suggested_price, floor_price, _R1_KEEP_RATIO)
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.COUNTER_OFFER_1,
        reply_text=f"謝謝出價，我這邊最多讓到 {price} 元，你看可以嗎。",
        quoted_price=price,
        should_send=True,
    )


def _counter_second(
    session_id: str, _offer: int, suggested_price: int, floor_price: int
) -> ChatDecision:
    """次輪還價，保留三成差價並要求今日寄出。"""
    price = _counter_price(suggested_price, floor_price, _R2_KEEP_RATIO)
    return ChatDecision(
        session_id=session_id,
        next_state=NegotiationState.COUNTER_OFFER_2,
        reply_text=f"那我退到底了，{price} 元、今天寄出，你看行不行。",
        quoted_price=price,
        should_send=True,
    )


_ROUTES = {
    (_ABOVE, _FIRST_ROUND): _accept,
    (_ABOVE, _SECOND_ROUND): _accept,
    (_ABOVE, _LATE_ROUND): _accept,
    (_IN_RANGE, _FIRST_ROUND): _counter_first,
    (_IN_RANGE, _SECOND_ROUND): _counter_second,
    (_IN_RANGE, _LATE_ROUND): _accept_final,
    (_NEAR_MISS, _FIRST_ROUND): _reject_invite,
    (_NEAR_MISS, _SECOND_ROUND): _reject_invite_express,
    (_NEAR_MISS, _LATE_ROUND): _defer_to_human,
    (_LOWBALL, _FIRST_ROUND): _reject_flat,
    (_LOWBALL, _SECOND_ROUND): _reject_flat,
    (_LOWBALL, _LATE_ROUND): _defer_to_human,
}


def decide(
    session_id: str,
    buyer_offer: int | None,
    suggested_price: int,
    floor_price: int,
    negotiation_round: int,
) -> ChatDecision:
    """依出價分區與輪次查表派發，空值或非正數出價轉人工。"""
    if buyer_offer is None or buyer_offer <= 0:
        return _defer_to_human(session_id)
    zone = _classify_zone(buyer_offer, suggested_price, floor_price)
    bucket = _round_bucket(negotiation_round)
    return _ROUTES[(zone, bucket)](session_id, buyer_offer, suggested_price, floor_price)
