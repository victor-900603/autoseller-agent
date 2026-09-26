import re

_AMOUNT_RE = re.compile(r"\d[\d,]*")


def extract_amounts(text: str) -> list[int]:
    """抽取文字中所有金額（支援千分位）。"""
    amounts = []
    for match in _AMOUNT_RE.findall(text):
        try:
            amounts.append(int(match.replace(",", "")))
        except ValueError:
            continue
    return amounts


def max_mentioned_price(text: str) -> int | None:
    """取最大提及金額，無金額回傳空值。"""
    amounts = extract_amounts(text)
    return max(amounts) if amounts else None


def reply_passes_guard(reply_text: str, floor_price: int) -> bool:
    """最大提及金額低於底價則擋下，無金額直接通過。"""
    mentioned = max_mentioned_price(reply_text)
    if mentioned is None:
        return True
    return mentioned >= floor_price
