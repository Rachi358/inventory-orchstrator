
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class InventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku: str = Field(min_length=1, max_length=50)
    stock_quantity: int = Field(ge=0)


class ReconciliationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[InventoryItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_skus(self):
        skus = [item.sku for item in self.items]

        if len(skus) != len(set(skus)):
            raise ValueError(
                "Duplicate SKUs are not allowed in a manifest."
            )

        return self


class ReconciliationResponse(BaseModel):
    message: str
    status: Literal["PROCESSING"]
    items_received: int = Field(ge=1)
