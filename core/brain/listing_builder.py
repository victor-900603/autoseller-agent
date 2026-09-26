from core.brain.pricing_agent import apply_condition_discount, apply_floor
from core.brain.vision_agent import grade_to_condition
from core.contracts import ListingContract, MarketQuote, VisionResult

_TITLE_LIMIT = 60


class LowConfidenceError(Exception):
    pass


def build_title(detected_brand: str, detected_model: str, extra: str = "") -> str:
    full = f"{detected_brand} {detected_model} {extra}".strip()
    if len(full) <= _TITLE_LIMIT:
        return full
    short = f"{detected_brand} {detected_model}"
    if len(short) <= _TITLE_LIMIT:
        return short
    return short[:_TITLE_LIMIT]


def build_description(vision: VisionResult, trade_terms: str) -> str:
    defects = "、".join(vision.defects_noted) if vision.defects_noted else "無明顯瑕疵"
    inclusions = "、".join(vision.inclusions) if vision.inclusions else "僅商品本體"
    condition = grade_to_condition(vision.condition_grade)
    return (
        f"【成色】{condition}\n"
        f"【瑕疵】{defects}\n"
        f"【內容物】{inclusions}\n"
        f"【交易方式】{trade_terms}"
    )


def build_listing(
    product_id: str,
    category_id: str,
    vision: VisionResult,
    quote: MarketQuote,
    image_paths: list[str],
    floor_ratio: float,
    trade_terms: str,
    title_extra: str = "",
) -> ListingContract:
    if quote.low_confidence:
        raise LowConfidenceError("行情樣本不足，轉人工審核")
    condition = grade_to_condition(vision.condition_grade)
    suggested_price = apply_condition_discount(quote.p50, condition)
    return ListingContract(
        product_id=product_id,
        title=build_title(vision.detected_brand, vision.detected_model, title_extra),
        category_id=category_id,
        condition=condition,
        suggested_price=suggested_price,
        floor_price=apply_floor(suggested_price, floor_ratio),
        description=build_description(vision, trade_terms),
        image_paths=image_paths,
    )
