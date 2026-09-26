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
        if self.should_send and not self.reply_text.strip():
            raise ValueError("should_send 為真時必須附回覆文字")
        return self
