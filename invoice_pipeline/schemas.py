"""Invoice data contract. Field descriptions are sent to the model as extraction instructions."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = Field(description="Line item description as written on the invoice")
    quantity: float = Field(description="Quantity or hours billed")
    unit_price: float = Field(description="Price per unit or hourly rate")
    total_amount: float = Field(description="Amount charged for this line as printed")


class Adjustment(BaseModel):
    label: str = Field(description="Label as printed, e.g. 'State Tax (6.5%)' or 'Discount'")
    amount: float = Field(
        description="Signed amount: negative for discounts and credits, positive for taxes and fees"
    )


class InvoiceData(BaseModel):
    vendor_name: str = Field(description="Name of the company that issued the invoice")
    invoice_number: str | None = Field(default=None, description="Invoice number or ID")
    invoice_date: str | None = Field(
        default=None, description="Issue date in ISO 8601 format (YYYY-MM-DD)"
    )
    currency: str = Field(description="ISO 4217 currency code, e.g. USD or EUR")
    items: list[LineItem] = Field(description="Every billed line item")
    subtotal: float | None = Field(
        default=None, description="Subtotal before taxes, fees and discounts, if printed"
    )
    adjustments: list[Adjustment] = Field(
        default_factory=list,
        description="Every tax, fee, discount or surcharge between the subtotal and the total",
    )
    total_amount_due: float = Field(description="Final amount due as printed")
