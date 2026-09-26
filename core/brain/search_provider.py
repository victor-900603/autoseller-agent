from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SearchResults:
    prices: list[int] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


class SearchProvider(Protocol):
    def search(self, query: str, limit: int = 20) -> SearchResults:
        ...


class MockSearchProvider:
    def __init__(self, prices: list[int], sources: list[str] | None = None) -> None:
        self._prices = prices
        self._sources = sources or []

    def search(self, query: str, limit: int = 20) -> SearchResults:
        """依查詢回傳夾具價格，上限切片。"""
        return SearchResults(prices=self._prices[:limit], sources=self._sources)
