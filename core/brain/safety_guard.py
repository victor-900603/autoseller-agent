import re

_AMOUNT_RE = re.compile(r"\d[\d,]*")


def extract_amounts(text: str) -> list[int]:
    amounts = []
    for match in _AMOUNT_RE.findall(text):
        try:
            amounts.append(int(match.replace(",", "")))
        except ValueError:
            continue
    return amounts


def max_mentioned_price(text: str) -> int | None:
    amounts = extract_amounts(text)
    return max(amounts) if amounts else None


def reply_passes_guard(reply_text: str, floor_price: int) -> bool:
    mentioned = max_mentioned_price(reply_text)
    if mentioned is None:
        return True
    return mentioned >= floor_price
