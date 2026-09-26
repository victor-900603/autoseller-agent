from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, PositiveInt, model_validator

Condition = Literal["全新", "9成新", "輕微使用痕跡"]


class NegotiationState(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    COUNTER_OFFER_1 = "COUNTER_OFFER_1"
    COUNTER_OFFER_2 = "COUNTER_OFFER_2"
    FINAL_OFFER = "FINAL_OFFER"
    NEED_HUMAN = "NEED_HUMAN"


class ListingContract(BaseModel):
    product_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=60)
    category_id: str = Field(min_length=1)
    condition: Condition
    suggested_price: PositiveInt
    floor_price: PositiveInt
    description: str = Field(min_length=1)
    image_paths: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def floor_not_above_suggested(self):
        """底價不得高於建議價，否則契約無效。"""
        if self.floor_price > self.suggested_price:
            raise ValueError("floor_price 不得高於 suggested_price")
        return self


class ChatDecision(BaseModel):
    session_id: str = Field(min_length=1)
    next_state: NegotiationState
    reply_text: str = ""
    quoted_price: PositiveInt | None = None
    should_send: bool = False

    @model_validator(mode="after")
    def sendable_has_reply(self):
        """標記發送時必須附回覆文字。"""
        if self.should_send and not self.reply_text.strip():
            raise ValueError("should_send 為真時必須附回覆文字")
        return self


class MarketQuote(BaseModel):
    p25: PositiveInt
    p50: PositiveInt
    p75: PositiveInt
    sample_count: int = Field(ge=0)
    sources: list[str] = Field(default_factory=list)
    low_confidence: bool = False


ConditionGrade = Literal["10_out_of_10", "9_out_of_10", "8_out_of_10"]


class VisionResult(BaseModel):
    detected_brand: str = Field(min_length=1)
    detected_model: str = Field(min_length=1)
    condition_grade: ConditionGrade
    defects_noted: list[str] = Field(default_factory=list)
    inclusions: list[str] = Field(default_factory=list)
